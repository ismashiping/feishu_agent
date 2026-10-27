"""Short-lived, owner-checked Redis leases; no SDK or business processing."""

import hashlib
import json
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pydantic import Field, StrictInt, StringConstraints, TypeAdapter, model_validator

from clinical_agent.domain.models import DTO
from feishu.events import Identifier

Identity = tuple[Identifier, Literal["message", "event"], Identifier]
Prefix = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
]
_IDENTITY = TypeAdapter(Identity)
_PREFIX = TypeAdapter(Prefix)
OperationResult = Literal["owned", "lost", "unavailable"]

# All reads, owner checks and mutations happen together on the Redis server.
# ARGV: action, owner, lease_ms, max_processing_ms, completed_ttl_ms.
_SCRIPT = """
local action, owner = ARGV[1], ARGV[2]
local lease, budget, completed = tonumber(ARGV[3]), tonumber(ARGV[4]), tonumber(ARGV[5])
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
if action == 'acquire' then
    local value = cjson.encode({state='processing', owner=owner, deadline_ms=now+budget})
    if redis.call('SET', KEYS[1], value, 'NX', 'PX', lease) then return 1 end
    return 0
end
local raw = redis.call('GET', KEYS[1])
if not raw then return 0 end
local ok, value = pcall(cjson.decode, raw)
if not ok or type(value) ~= 'table' then return -1 end
if value.state == 'completed' then return 0 end
if value.state ~= 'processing' or type(value.owner) ~= 'string'
   or type(value.deadline_ms) ~= 'number' then return -1 end
local ttl = redis.call('PTTL', KEYS[1])
if ttl == -1 then return -1 end
if value.owner ~= owner or ttl <= 0 or now >= value.deadline_ms then return 0 end
if action == 'check' then return 1 end
if action == 'renew' then
    return redis.call('PEXPIRE', KEYS[1], math.min(lease, value.deadline_ms-now))
end
if action == 'release' then return redis.call('DEL', KEYS[1]) end
if action == 'complete' then
    redis.call('SET', KEYS[1], cjson.encode({state='completed'}), 'PX', completed)
    return 1
end
return -1
"""


class DedupPolicy(DTO):
    prefix: Prefix = "clinical-agent-feishu"
    lease_ms: Annotated[StrictInt, Field(ge=1, le=300000)] = 60000
    max_processing_ms: Annotated[StrictInt, Field(ge=1, le=900000)] = 300000
    completed_ttl_ms: Annotated[StrictInt, Field(ge=1, le=604800000)] = 86400000

    @model_validator(mode="after")
    def budget_covers_lease(self) -> "DedupPolicy":
        if self.max_processing_ms < self.lease_ms:
            raise ValueError("Processing budget must cover lease")
        return self


class Lease(DTO):
    identity: Identity
    owner: UUID


@dataclass(frozen=True)
class AcquireResult:
    status: Literal["acquired", "duplicate", "unavailable"]
    lease: Lease | None = None


class RedisClient(Protocol):
    """Injected clients must use bounded I/O and disable automatic retries."""

    def eval(self, script: str, numkeys: int, *args: str | int) -> object: ...
    def close(self) -> None: ...


def dedup_key(identity: Identity, *, prefix: str = "clinical-agent-feishu") -> str:
    identity = _IDENTITY.validate_python(identity)
    prefix = _PREFIX.validate_python(prefix)
    encoded = json.dumps(identity, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return f"{prefix}:v1:{hashlib.sha256(encoded).hexdigest()}"


class RedisDeduplicator:
    """Takes ownership of an injected client. Close after all workers/senders stop."""

    def __init__(self, client: RedisClient, *, policy: DedupPolicy | None = None) -> None:
        self.client = client
        self.policy = DedupPolicy.model_validate(policy if policy is not None else DedupPolicy())
        self._closed = False

    def _execute(self, action: str, lease: Lease) -> int | None:
        from redis.exceptions import RedisError

        if self._closed:
            return None
        try:
            result = self.client.eval(
                _SCRIPT,
                1,
                dedup_key(lease.identity, prefix=self.policy.prefix),
                action,
                str(lease.owner),
                self.policy.lease_ms,
                self.policy.max_processing_ms,
                self.policy.completed_ttl_ms,
            )
        except RedisError:
            # A timed-out write may already have committed: no retry or blind cleanup.
            return None
        return result if type(result) is int and result in (0, 1) else None

    def acquire(self, identity: Identity) -> AcquireResult:
        lease = Lease(identity=identity, owner=uuid4())
        result = self._execute("acquire", lease)
        if result == 1:
            return AcquireResult("acquired", lease)
        return AcquireResult("duplicate" if result == 0 else "unavailable")

    def _operate(self, action: str, lease: Lease) -> OperationResult:
        lease = Lease.model_validate(lease)
        result = self._execute(action, lease)
        return "owned" if result == 1 else "lost" if result == 0 else "unavailable"

    def check(self, lease: Lease) -> OperationResult:
        """Check at the point of use, especially immediately before sending."""
        return self._operate("check", lease)

    def renew(self, lease: Lease) -> OperationResult:
        return self._operate("renew", lease)

    def complete(self, lease: Lease) -> OperationResult:
        """Mark completed only after the caller's successful terminal action."""
        return self._operate("complete", lease)

    def release(self, lease: Lease) -> OperationResult:
        return self._operate("release", lease)

    def close(self) -> bool:
        from redis.exceptions import RedisError

        self._closed = True
        try:
            self.client.close()
        except RedisError:
            return False
        return True


def create_deduplicator(url: str, *, policy: DedupPolicy | None = None) -> RedisDeduplicator:
    """Explicit construction only. URL parameters cannot override timeout/retry policy."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("redis", "rediss") or not parsed.hostname:
            raise ValueError
        if parsed.query or parsed.fragment or "?" in url or "#" in url:
            raise ValueError
        _ = parsed.port
        if parsed.path not in ("", "/"):
            database = parsed.path[1:]
            if not database.isascii() or not database.isdecimal():
                raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid Redis URL") from None

    from redis import Redis
    from redis.backoff import NoBackoff
    from redis.retry import Retry

    checked_policy = DedupPolicy.model_validate(policy if policy is not None else DedupPolicy())
    try:
        client = Redis.from_url(
            url,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            max_connections=16,
            decode_responses=True,
            retry=Retry(NoBackoff(), 0),
        )
    except (ValueError, TypeError):
        raise ValueError("Invalid Redis URL") from None
    return RedisDeduplicator(client, policy=checked_policy)
