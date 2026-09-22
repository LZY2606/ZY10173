import hashlib
import json

from .config import GENESIS_HASH


def canonical(obj) -> bytes:
    """Deterministic canonical JSON bytes (sorted keys, compact separators)."""
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(event: dict) -> str:
    """Hash of the full event content (everything but client transport keys)."""
    core = {k: event.get(k) for k in ("event_id", "event_type", "boot_id", "seq", "ts", "payload")}
    return sha256_hex(canonical(core))


def append_audit(conn, action, entity, entity_id=None, detail=None, input_hash=None):
    """Append an audit entry; returns the new seq. Caller owns the transaction."""
    prev = conn.execute("SELECT entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    prev_hash = prev["entry_hash"] if prev else GENESIS_HASH
    seq = (conn.execute("SELECT COALESCE(MAX(seq),0) AS m FROM audit_log").fetchone()["m"]) + 1
    body = {
        "seq": seq,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "detail": detail,
        "input_hash": input_hash,
        "prev_hash": prev_hash,
    }
    entry_hash = sha256_hex(canonical(body))
    conn.execute(
        "INSERT INTO audit_log(seq, action, entity, entity_id, detail_json, input_hash, entry_hash, prev_hash)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (seq, action, entity, entity_id, json.dumps(detail, ensure_ascii=False),
         input_hash, entry_hash, prev_hash),
    )
    return seq


def verify_chain(conn):
    prev_hash = GENESIS_HASH
    expected_seq = 0
    for row in conn.execute("SELECT * FROM audit_log ORDER BY seq"):
        expected_seq += 1
        if row["seq"] != expected_seq:
            return False, f"audit seq gap at {row['seq']}"
        if row["prev_hash"] != prev_hash:
            return False, f"broken prev link at seq {row['seq']}"
        body = {
            "seq": row["seq"],
            "action": row["action"],
            "entity": row["entity"],
            "entity_id": row["entity_id"],
            "detail": json.loads(row["detail_json"]) if row["detail_json"] else None,
            "input_hash": row["input_hash"],
            "prev_hash": row["prev_hash"],
        }
        if sha256_hex(canonical(body)) != row["entry_hash"]:
            return False, f"entry hash mismatch at seq {row['seq']}"
        prev_hash = row["entry_hash"]
    return True, {"entries": expected_seq, "head": prev_hash}
