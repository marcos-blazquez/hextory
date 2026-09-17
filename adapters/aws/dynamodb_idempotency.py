"""DynamoDB-backed IdempotencyStore (DES-0005 adapter concern)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

DEFAULT_TABLE = "hextory"


def table_name_from_env() -> str:
    return os.environ.get("HEXTORY_DYNAMODB_TABLE", "").strip() or DEFAULT_TABLE


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamoDbIdempotencyStore:
    """Persist idempotency_key → traveler_id in DynamoDB (first write wins)."""

    def __init__(
        self,
        *,
        table_name: Optional[str] = None,
        client: Any = None,
        endpoint_url: Optional[str] = None,
        region_name: str = "us-east-1",
        checkpointer: Any = None,
    ) -> None:
        """
        Prefer sharing a ``DynamoDbCheckpointer`` so the same table/client is
        reused; otherwise pass ``client`` / env like the checkpointer.
        """
        self._table = table_name or table_name_from_env()
        self._endpoint = endpoint_url or os.environ.get("HEXTORY_AWS_ENDPOINT", "").strip() or None
        self._region = (
            os.environ.get("AWS_DEFAULT_REGION", "").strip()
            or os.environ.get("AWS_REGION", "").strip()
            or region_name
        )
        self._client = client
        self._checkpointer = checkpointer
        self._table_ready = False

    def _boto(self) -> Any:
        if self._checkpointer is not None:
            # Ensure table exists via checkpointer path, then reuse its client.
            self._checkpointer.ensure_table()
            return self._checkpointer._boto()
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for DynamoDbIdempotencyStore; "
                'install with: pip install -e ".[aws]"'
            ) from exc
        kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint:
            kwargs["endpoint_url"] = self._endpoint
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
        if self._table_ready:
            return
        if self._checkpointer is not None:
            self._checkpointer.ensure_table()
            self._table_ready = True
            return
        client = self._boto()
        existing = client.list_tables().get("TableNames", [])
        if self._table not in existing:
            client.create_table(
                TableName=self._table,
                AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST",
            )
        self._table_ready = True

    def _pk(self, key: str) -> str:
        return f"idem#{key}"

    def get(self, key: str) -> Optional[str]:
        self.ensure_table()
        resp = self._boto().get_item(
            TableName=self._table,
            Key={"pk": {"S": self._pk(key)}},
        )
        item = resp.get("Item")
        if not item:
            return None
        return str(item["traveler_id"]["S"])

    def put(self, key: str, traveler_id: str) -> None:
        self.ensure_table()
        # Conditional put — first write wins.
        try:
            self._boto().put_item(
                TableName=self._table,
                Item={
                    "pk": {"S": self._pk(key)},
                    "entity_type": {"S": "idempotency"},
                    "traveler_id": {"S": traveler_id},
                    "updated_at": {"S": _utcnow()},
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
        except Exception as exc:
            # ConditionalCheckFailedException → already present; ignore.
            name = type(exc).__name__
            if "ConditionalCheckFailed" in name or "ConditionalCheckFailedException" in str(exc):
                return
            # boto3 ClientError code path
            error = getattr(exc, "response", {}) or {}
            code = (error.get("Error") or {}).get("Code", "")
            if code == "ConditionalCheckFailedException":
                return
            raise

    def delete(self, key: str) -> None:
        self.ensure_table()
        self._boto().delete_item(
            TableName=self._table,
            Key={"pk": {"S": self._pk(key)}},
        )
