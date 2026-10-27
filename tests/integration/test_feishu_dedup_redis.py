"""Opt-in real Redis, unique namespace; never flush a shared database."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.redis]
IDENTITY = ("cli_test", "message", "om_1")


@pytest.fixture
def service():
    from feishu.dedup import DedupPolicy, create_deduplicator

    url = os.environ.get("CLINICAL_AGENT_TEST_REDIS_URL")
    if not url:
        pytest.fail("CLINICAL_AGENT_TEST_REDIS_URL required: real Redis not verified")
    prefix = "p113-test-" + uuid4().hex
    service = create_deduplicator(
        url,
        policy=DedupPolicy(
            prefix=prefix, lease_ms=250, max_processing_ms=1200, completed_ttl_ms=400
        ),
    )
    assert service.client.ping()
    yield service
    # Only this fixture's unique namespace; no FLUSHALL/FLUSHDB.
    for key in service.client.scan_iter(match=prefix + ":*"):
        service.client.delete(key)
    assert service.close()


def test_concurrent_clients_acquire_once(service):
    import redis

    from feishu.dedup import RedisDeduplicator

    url = os.environ["CLINICAL_AGENT_TEST_REDIS_URL"]
    clients = [
        redis.Redis.from_url(url, socket_timeout=1, socket_connect_timeout=1) for _ in range(12)
    ]
    try:
        services = [RedisDeduplicator(c, policy=service.policy) for c in clients]
        barrier = Barrier(12)

        def acquire(s):
            barrier.wait(timeout=5)
            return s.acquire(IDENTITY)

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(acquire, services))
        assert [r.status for r in results].count("acquired") == 1
        assert [r.status for r in results].count("duplicate") == 11
        owner = next(r.lease for r in results if r.lease)
        assert service.check(owner) == "owned"
        for identity in [("other", "message", "om_1"), ("cli_test", "event", "om_1")]:
            assert service.acquire(identity).status == "acquired"
    finally:
        for c in clients:
            c.close()


def test_completion_has_separate_ttl_and_cannot_be_deleted(service):
    lease = service.acquire(IDENTITY).lease
    assert service.complete(lease) == "owned"
    for action in ["check", "renew", "release", "complete"]:
        assert getattr(service, action)(lease) == "lost"
    assert service.acquire(IDENTITY).status == "duplicate"
    time.sleep(0.45)
    assert service.acquire(IDENTITY).status == "acquired"


def test_release_then_old_owner_cannot_touch_new_lease(service):
    a = service.acquire(IDENTITY).lease
    assert service.release(a) == "owned"
    b = service.acquire(IDENTITY).lease
    for action in ["check", "renew", "complete", "release"]:
        assert getattr(service, action)(a) == "lost"
        assert service.check(b) == "owned"


def test_expiry_then_old_owner_cannot_touch_new_lease(service):
    a = service.acquire(IDENTITY).lease
    time.sleep(0.3)
    b = service.acquire(IDENTITY).lease
    assert b and b.owner != a.owner
    for action in ["check", "renew", "complete", "release"]:
        assert getattr(service, action)(a) == "lost"
        assert service.check(b) == "owned"


def test_renew_keeps_alive_but_cannot_extend_total_deadline(service):
    lease = service.acquire(IDENTITY).lease
    start = time.monotonic()
    # Renew beyond initial lease but before total deadline.
    while time.monotonic() - start < 0.6:
        time.sleep(0.08)
        assert service.renew(lease) == "owned"
    assert service.check(lease) == "owned"
    while time.monotonic() - start < 1.3:
        time.sleep(0.08)
        result = service.renew(lease)
        if result == "lost":
            break
        assert result == "owned"
    assert service.check(lease) == "lost"
    assert service.acquire(IDENTITY).status == "acquired"


@pytest.mark.parametrize("value", ["broken-json", '{"state":"processing"}'])
def test_corrupt_state_is_unavailable_without_mutation(service, value):
    from feishu.dedup import dedup_key

    lease = service.acquire(IDENTITY).lease
    key = dedup_key(IDENTITY, prefix=service.policy.prefix)
    service.client.set(key, value, px=1000)
    assert service.check(lease) == "unavailable"
    assert service.client.get(key) == value


def test_wrong_key_type_is_unavailable(service):
    from feishu.dedup import dedup_key

    lease = service.acquire(IDENTITY).lease
    key = dedup_key(IDENTITY, prefix=service.policy.prefix)
    service.client.delete(key)
    service.client.lpush(key, "private")
    service.client.pexpire(key, 1000)
    assert service.release(lease) == "unavailable"
    assert service.client.lrange(key, 0, -1) == ["private"]


def test_connection_refused_is_unavailable():
    import socket

    from feishu.dedup import create_deduplicator

    # Occupy without listening, guaranteeing this loopback port refuses TCP.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        service = create_deduplicator(f"redis://127.0.0.1:{reserved.getsockname()[1]}/0")
        try:
            assert service.acquire(IDENTITY).status == "unavailable"
        finally:
            service.close()


def test_response_lost_after_commit_does_not_release_or_retry(service):
    import redis

    from feishu.dedup import RedisDeduplicator

    class LostResponse:
        calls = 0

        def eval(self, *args):
            self.calls += 1
            service.client.eval(*args)
            raise redis.TimeoutError("SECRET response lost")

        def close(self):
            pass

    client = LostResponse()
    uncertain = RedisDeduplicator(client, policy=service.policy)
    result = uncertain.acquire(IDENTITY)
    assert result.status == "unavailable" and result.lease is None
    assert client.calls == 1
    assert service.acquire(IDENTITY).status == "duplicate"
    time.sleep(0.3)
    assert service.acquire(IDENTITY).status == "acquired"


def test_unbounded_corrupt_lease_cannot_be_used(service):
    from feishu.dedup import dedup_key

    lease = service.acquire(IDENTITY).lease
    key = dedup_key(IDENTITY, prefix=service.policy.prefix)
    service.client.persist(key)
    for action in ["check", "renew", "complete", "release"]:
        assert getattr(service, action)(lease) == "unavailable"
    assert service.client.exists(key)


def test_check_does_not_renew_and_completed_ttl_is_independent(service):
    from feishu.dedup import dedup_key

    lease = service.acquire(IDENTITY).lease
    key = dedup_key(IDENTITY, prefix=service.policy.prefix)
    assert service.check(lease) == "owned"
    before = service.client.pttl(key)
    time.sleep(0.06)
    assert service.check(lease) == "owned"
    after = service.client.pttl(key)
    assert 0 < after < before
    assert service.complete(lease) == "owned"
    assert after < service.client.pttl(key) <= service.policy.completed_ttl_ms
    assert service.client.get(key) == '{"state":"completed"}'
