"""Traveler lifecycle statuses (DES-0002-G)."""

from __future__ import annotations

from enum import Enum


class TravelerStatus(str, Enum):
    ACCEPTED = "accepted"
    ASSEMBLING = "assembling"
    QUALITY_CHECK = "quality_check"
    REWORK = "rework"
    PACKAGING = "packaging"
    SHIPPED = "shipped"
    ESCALATED = "escalated"
    DENIED = "denied"


class RoutingDecision(str, Enum):
    ENTER = "enter"
    PASS = "pass"
    FAIL = "fail"
    REWORK = "rework"
    ESCALATE = "escalate"
    SHIP = "ship"
    DENY = "deny"
    ACCEPT = "accept"


class QualityResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
