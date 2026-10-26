import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize data deterministically for hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def calculate_event_hash(
    *,
    event_id: int,
    application_id: str,
    event_type: str,
    policy_version: str,
    created_at: datetime,
    details: dict[str, Any],
    previous_hash: str | None = None,
) -> str:
    """Calculate a deterministic SHA-256 hash for an audit event."""
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    payload = {
        "event_id": event_id,
        "application_id": application_id,
        "event_type": event_type,
        "policy_version": policy_version,
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
        "details": details,
        "previous_hash": previous_hash,
    }

    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def verify_event_hash(
    *,
    expected_hash: str,
    event_id: int,
    application_id: str,
    event_type: str,
    policy_version: str,
    created_at: datetime,
    details: dict[str, Any],
    previous_hash: str | None = None,
) -> bool:
    """Verify that an event matches its expected hash."""
    actual_hash = calculate_event_hash(
        event_id=event_id,
        application_id=application_id,
        event_type=event_type,
        policy_version=policy_version,
        created_at=created_at,
        details=details,
        previous_hash=previous_hash,
    )
    return actual_hash == expected_hash
