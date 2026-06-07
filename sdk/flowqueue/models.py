"""Lightweight data models returned by the SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Delivery:
    """A delivery claimed by a consumer via poll()."""

    id: str
    message_id: str
    consumer_id: str
    status: str
    attempt_count: int
    payload: dict
    sequence_num: int
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict) -> "Delivery":
        return cls(
            id=data["id"],
            message_id=data["message_id"],
            consumer_id=data["consumer_id"],
            status=data["status"],
            attempt_count=data["attempt_count"],
            payload=data.get("payload", {}),
            sequence_num=data.get("sequence_num", 0),
            raw=data,
        )
