"""Call contract and fault isolation; real Redis tests validate Lua semantics."""

from uuid import uuid4

import pytest
from pydantic import ValidationError


def api():
    from feishu import dedup

    return dedup


class Client:
    def __init__(self, reply=1, error=None):
        self.reply, self.error, self.calls, self.closed = reply, error, [], False

    def eval(self, *args):
        self.calls.append(args)
        if self.error:
            raise self.error
        return self.reply

    def close(self):
        self.closed = True
        if self.error:
            raise self.error


IDENTITY = ("cli_test", "message", "om_1")


def test_key_stable_private_and_namespaced():
    d = api()
    a = d.dedup_key(IDENTITY, prefix="test")
    assert a == d.dedup_key(tuple(IDENTITY), prefix="test")
    assert a.startswith("test:v1:") and len(a) == len("test:v1:") + 64
    assert "om_1" not in a and "cli_test" not in a
    others = [
        ("other", "message", "om_1"),
        ("cli_test", "event", "om_1"),
        ("cli_test", "message", "om_2"),
    ]
    assert len({a, *(d.dedup_key(x, prefix="test") for x in others)}) == 4
    assert a != d.dedup_key(IDENTITY, prefix="other")


@pytest.mark.parametrize(
    "identity",
    [
        ("", "message", "om_1"),
        ("cli", "other", "om_1"),
        ("cli", "message", ""),
        ("cli", "message", 3),
        ("cli", "message", "x:y"),
        ("cli", "message"),
        ("cli", "message", "x" * 257),
        ("中文", "event", "x"),
    ],
)
def test_bad_identity_before_io(identity):
    d = api()
    client = Client()
    with pytest.raises(ValidationError):
        d.RedisDeduplicator(client).acquire(identity)
    assert not client.calls


@pytest.mark.parametrize(
    "kwargs",
    [
        {"prefix": ""},
        {"prefix": "bad:prefix"},
        {"prefix": "x" * 129},
        {"lease_ms": 0},
        {"lease_ms": True},
        {"lease_ms": "10"},
        {"lease_ms": 300001},
        {"max_processing_ms": 900001},
        {"lease_ms": 20, "max_processing_ms": 19},
        {"completed_ttl_ms": 0},
        {"completed_ttl_ms": 604800001},
        {"extra": 1},
    ],
)
def test_policy_validation(kwargs):
    with pytest.raises(ValidationError):
        api().DedupPolicy(**kwargs)


@pytest.mark.parametrize(
    "reply,status",
    [
        (1, "acquired"),
        (0, "duplicate"),
        (9, "unavailable"),
        (None, "unavailable"),
        (True, "unavailable"),
    ],
)
def test_acquire_reply(reply, status):
    d = api()
    c = Client(reply)
    result = d.RedisDeduplicator(c).acquire(IDENTITY)
    assert result.status == status
    assert (result.lease is not None) == (status == "acquired")
    assert c.calls[0][1] == 1
    assert c.calls[0][2] == d.dedup_key(IDENTITY)
    assert c.calls[0][3] == "acquire"


def test_owner_unique_and_policy_arguments():
    d = api()
    c = Client()
    service = d.RedisDeduplicator(
        c,
        policy=d.DedupPolicy(
            prefix="test", lease_ms=50, max_processing_ms=200, completed_ttl_ms=1000
        ),
    )
    a, b = service.acquire(IDENTITY).lease, service.acquire(IDENTITY).lease
    assert a.owner != b.owner
    assert a.identity == IDENTITY
    assert c.calls[0][4:] == (str(a.owner), 50, 200, 1000)


@pytest.mark.parametrize("action", ["check", "renew", "complete", "release"])
@pytest.mark.parametrize(
    "reply,expected",
    [(1, "owned"), (0, "lost"), (2, "unavailable"), (None, "unavailable"), (False, "unavailable")],
)
def test_operations(action, reply, expected):
    d = api()
    c = Client(reply)
    lease = d.Lease(identity=IDENTITY, owner=uuid4())
    assert getattr(d.RedisDeduplicator(c), action)(lease) == expected
    assert c.calls[0][3:5] == (action, str(lease.owner))


@pytest.mark.parametrize("action", ["acquire", "check", "renew", "complete", "release"])
@pytest.mark.parametrize("error_name", ["ConnectionError", "TimeoutError", "ResponseError"])
def test_redis_failure_is_sanitized(action, error_name):
    import redis.exceptions

    d = api()
    c = Client(error=getattr(redis.exceptions, error_name)("SECRET redis://private question"))
    arg = IDENTITY if action == "acquire" else d.Lease(identity=IDENTITY, owner=uuid4())
    result = getattr(d.RedisDeduplicator(c), action)(arg)
    assert (result.status if action == "acquire" else result) == "unavailable"
    assert "SECRET" not in repr(result)


def test_invalid_lease_and_policy_revalidated():
    d = api()
    c = Client()
    lease = d.Lease.model_construct(identity=IDENTITY, owner="broken")
    with pytest.raises(ValidationError):
        d.RedisDeduplicator(c).release(lease)
    policy = d.DedupPolicy.model_construct(lease_ms=-1)
    with pytest.raises(ValidationError):
        d.RedisDeduplicator(c, policy=policy)
    assert not c.calls


def test_close_transfers_client_ownership():
    d = api()
    c = Client()
    assert d.RedisDeduplicator(c).close() is True
    assert c.closed


def test_close_failure_sanitized():
    import redis

    d = api()
    assert d.RedisDeduplicator(Client(error=redis.ConnectionError("SECRET"))).close() is False


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://localhost",
        "redis://localhost?socket_timeout=0",
        "redis://localhost#fragment",
        "redis://",
        "unix:///tmp/redis",
    ],
)
def test_factory_rejects_unsafe_url(url):
    with pytest.raises(ValueError, match="Invalid Redis URL"):
        api().create_deduplicator(url)


def test_factory_fixed_timeouts_no_retries(monkeypatch):
    import redis

    d = api()
    captured = {}
    c = Client()

    def factory(url, **kwargs):
        captured.update(url=url, **kwargs)
        return c

    monkeypatch.setattr(redis.Redis, "from_url", factory)
    service = d.create_deduplicator("redis://localhost:6379/0")
    assert captured["socket_connect_timeout"] == captured["socket_timeout"] == 1.0
    assert captured["max_connections"] == 16
    assert captured["decode_responses"] is True
    assert captured["retry"].get_retries() == 0
    assert service.close() is True


def test_closed_service_never_reopens_connection():
    d = api()
    c = Client()
    service = d.RedisDeduplicator(c)
    lease = service.acquire(IDENTITY).lease
    assert service.close()
    calls = len(c.calls)
    assert service.acquire(IDENTITY).status == "unavailable"
    for action in ["check", "renew", "complete", "release"]:
        assert getattr(service, action)(lease) == "unavailable"
    assert len(c.calls) == calls


def test_invalid_policy_creates_no_client(monkeypatch):
    import redis

    d = api()

    def forbidden(*args, **kwargs):
        pytest.fail("Client created before validation")

    monkeypatch.setattr(redis.Redis, "from_url", forbidden)
    with pytest.raises(ValidationError):
        d.create_deduplicator(
            "redis://localhost", policy=d.DedupPolicy.model_construct(lease_ms=-1)
        )


def test_factory_hides_bad_database_path():
    with pytest.raises(ValueError, match="^Invalid Redis URL$"):
        api().create_deduplicator("redis://user:SECRET@localhost/private")


def test_factory_hides_bad_port():
    with pytest.raises(ValueError, match="^Invalid Redis URL$"):
        api().create_deduplicator("redis://user:SECRET@localhost:private")
