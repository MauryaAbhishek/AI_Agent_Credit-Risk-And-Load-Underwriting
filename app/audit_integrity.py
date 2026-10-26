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

def verify_audit_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify event hashes and links in chronological order.

    Each event must contain event_id, application_id, event_type,
    policy_version, created_at, details, previous_hash, and event_hash.

    Events with missing hashes are reported as unverifiable. A chain
    gap is never silently treated as verified history.
    """
    errors: list[dict[str, Any]] = []
    verified_count = 0
    unverifiable_count = 0
    previous_event_hash: str | None = None
    chain_contiguous = True

    for event in events:
        event_id = event.get("event_id")
        stored_hash = event.get("event_hash")
        stored_previous_hash = event.get("previous_hash")

        if not stored_hash:
            unverifiable_count += 1
            chain_contiguous = False
            errors.append({
                "event_id": event_id,
                "error": "missing_event_hash",
            })
            previous_event_hash = None
            continue

        if not chain_contiguous:
            if stored_previous_hash is not None:
                errors.append({
                    "event_id": event_id,
                    "error": "chain_gap",
                })
            else:
                # A new chain segment starts here, but earlier history
                # remains unverifiable.
                chain_contiguous = True

        if stored_previous_hash != previous_event_hash:
            # The first event, or first event in a new segment, should
            # have no previous hash.
            if previous_event_hash is not None or stored_previous_hash is not None:
                errors.append({
                    "event_id": event_id,
                    "error": "previous_hash_mismatch",
                })

        event_payload = {
            "event_id": event_id,
            "application_id": event["application_id"],
            "event_type": event["event_type"],
            "policy_version": event["policy_version"],
            "created_at": event["created_at"],
            "details": event["details"],
            "previous_hash": stored_previous_hash,
        }

        if not verify_event_hash(
            expected_hash=stored_hash,
            **event_payload,
        ):
            errors.append({
                "event_id": event_id,
                "error": "event_hash_mismatch",
            })
        else:
            verified_count += 1

        previous_event_hash = stored_hash

    return {
        "valid": not errors,
        "verified_count": verified_count,
        "unverifiable_count": unverifiable_count,
        "errors": errors,
    }
