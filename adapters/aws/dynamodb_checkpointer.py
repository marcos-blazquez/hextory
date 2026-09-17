"""DynamoDB-backed Checkpointer (DES-0005-C).

Implements the existing Checkpointer port — traveler snapshots + optional raw
graph-state blobs. Table is created lazily when ``ensure_table`` is called
(moto / LocalStack first slice). ``src/`` never imports this module.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from src.domain.traveler import DigitalTraveler

DEFAULT_TABLE = "hextory-aws-smoke"


def table_name_from_env() -> str:
    return os.environ.get("HEXTORY_DYNAMODB_TABLE", "").strip() or DEFAULT_TABLE


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_resource_not_found(exc: BaseException) -> bool:
    """True when DynamoDB reports the table does not exist."""
    error = getattr(exc, "response", {}) or {}
    code = (error.get("Error") or {}).get("Code", "")
    if code == "ResourceNotFoundException":
        return True
    name = type(exc).__name__
    return "ResourceNotFoundException" in name


class DynamoDbCheckpointer:
    """Persist travelers as DynamoDB items keyed by traveler_id / checkpoint key."""

    def __init__(
        self,
        *,
        table_name: Optional[str] = None,
        client: Any = None,
        endpoint_url: Optional[str] = None,
        region_name: str = "us-east-1",
    ) -> None:
        """
        Pass an explicit boto3 ``client`` (moto / injected) for tests.
        Otherwise builds a client from env (LocalStack via ``HEXTORY_AWS_ENDPOINT``).
        """
        self._table = table_name or table_name_from_env()
        self._endpoint = endpoint_url or os.environ.get("HEXTORY_AWS_ENDPOINT", "").strip() or None
        self._region = (
            os.environ.get("AWS_DEFAULT_REGION", "").strip()
            or os.environ.get("AWS_REGION", "").strip()
            or region_name
        )
        self._client = client
        self._table_ready = False

    def _boto(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for DynamoDbCheckpointer; "
                'install with: pip install -e ".[aws]"'
            ) from exc
        kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint:
            kwargs["endpoint_url"] = self._endpoint
        # LocalStack / moto-friendly dummy credentials when endpoint is set.
        if self._endpoint:
            kwargs.setdefault(
                "aws_access_key_id",
                os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            )
            kwargs.setdefault(
                "aws_secret_access_key",
                os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
            )
        self._client = boto3.client("dynamodb", **kwargs)
        return self._client

    def ensure_table(self) -> None:
        """Ensure the table exists without calling ``list_tables``.

        Uses ``describe_table`` (covered by SAM ``DynamoDBCrudPolicy`` on the
        single table). ``ResourceNotFoundException`` means create for moto /
        LocalStack; a live SAM stack already has the table so only describe runs.
        """
        if self._table_ready:
            return
        client = self._boto()
        try:
            client.describe_table(TableName=self._table)
        except Exception as exc:
            if not _is_resource_not_found(exc):
                raise
            client.create_table(
                TableName=self._table,
                AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST",
            )
            # moto creates synchronously; LocalStack may need a waiter in smoke.
            waiter = getattr(client, "get_waiter", None)
            if callable(waiter):
                try:
                    client.get_waiter("table_exists").wait(
                        TableName=self._table,
                        WaiterConfig={"Delay": 0.1, "MaxAttempts": 20},
                    )
                except Exception:  # pragma: no cover — moto usually ready immediately
                    pass
        self._table_ready = True

    def _pk_traveler(self, key: str) -> str:
        return f"traveler#{key}"

    def _pk_raw(self, key: str) -> str:
        return f"raw#{key}"

    def save(self, key: str, traveler: DigitalTraveler) -> str:
        self.ensure_table()
        snapshot = traveler.model_dump(mode="json")
        ref = f"dynamodb://{self._table}/travelers/{key}"
        traveler.checkpoint_ref = ref
        snapshot["checkpoint_ref"] = ref
        self._boto().put_item(
            TableName=self._table,
            Item={
                "pk": {"S": self._pk_traveler(key)},
                "entity_type": {"S": "traveler"},
                "payload": {"S": json.dumps(snapshot)},
                "updated_at": {"S": _utcnow()},
            },
        )
        return ref

    def load(self, key: str) -> Optional[DigitalTraveler]:
        self.ensure_table()
        resp = self._boto().get_item(
            TableName=self._table,
            Key={"pk": {"S": self._pk_traveler(key)}},
        )
        item = resp.get("Item")
        if not item:
            return None
        data = json.loads(item["payload"]["S"])
        return DigitalTraveler.model_validate(data)

    def save_raw(self, key: str, state: dict[str, Any]) -> str:
        self.ensure_table()
        ref = f"dynamodb://{self._table}/raw/{key}"
        self._boto().put_item(
            TableName=self._table,
            Item={
                "pk": {"S": self._pk_raw(key)},
                "entity_type": {"S": "raw"},
                "payload": {"S": json.dumps(state)},
                "updated_at": {"S": _utcnow()},
            },
        )
        return ref

    def load_raw(self, key: str) -> Optional[dict[str, Any]]:
        self.ensure_table()
        resp = self._boto().get_item(
            TableName=self._table,
            Key={"pk": {"S": self._pk_raw(key)}},
        )
        item = resp.get("Item")
        if not item:
            return None
        data = json.loads(item["payload"]["S"])
        return dict(data) if isinstance(data, dict) else None
