"""Bounded research admission and explicit delivery handoff; no SDK or resource factory."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from math import isfinite
from threading import BoundedSemaphore, Condition, RLock
from time import monotonic
from typing import Annotated, Literal, Protocol, cast

from pydantic import Field, StrictInt

from clinical_agent.command_runtime import ResearchPort
from clinical_agent.domain.models import DTO
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer
from feishu.dedup import AcquireResult, DedupPolicy, Identity, Lease, OperationResult
from feishu.events import MessageEnvelope


class WorkerPolicy(DTO):
    capacity: Annotated[StrictInt, Field(ge=1, le=4)] = 2
    processing_ms: Annotated[StrictInt, Field(ge=1, le=240000)] = 90000
    handoff_ms: Annotated[StrictInt, Field(ge=1, le=30000)] = 15000


class DedupPort(Protocol):
    policy: DedupPolicy

    def acquire(self, identity: Identity) -> AcquireResult: ...
    def check(self, lease: Lease) -> OperationResult: ...
    def release(self, lease: Lease) -> OperationResult: ...


@dataclass(frozen=True)
class Delivery:
    envelope: MessageEnvelope
    lease: Lease
    deadline: float
    answer: ResearchAnswer | None = None
    error_code: Literal["research_failed"] | None = None


class DeliveryPort(Protocol):
    """offer must be bounded/nonblocking; True transfers the lease to the sender."""

    def offer(self, delivery: Delivery) -> bool: ...


@dataclass(frozen=True)
class WorkResult:
    status: Literal[
        "queued", "delivery_failed", "delivery_unknown", "lost", "unavailable", "timed_out"
    ]


@dataclass(frozen=True)
class Submission:
    status: Literal["accepted", "busy", "duplicate", "unavailable", "closed", "submit_failed"]
    future: Future[WorkResult] | None = None


class Dispatcher:
    """Borrows all ports: drain workers, then sender, before closing shared resources."""

    def __init__(
        self,
        *,
        research: ResearchPort,
        dedup: DedupPort,
        sink: DeliveryPort,
        policy: WorkerPolicy | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.policy = WorkerPolicy.model_validate(policy if policy is not None else WorkerPolicy())
        budget = self.policy.processing_ms + self.policy.handoff_ms + 5000
        if min(dedup.policy.lease_ms, dedup.policy.max_processing_ms) < budget:
            raise ValueError("Dedup lease must cover worker and delivery budget")
        self._research, self._dedup, self._sink, self._clock = research, dedup, sink, clock
        self._executor = ThreadPoolExecutor(
            max_workers=self.policy.capacity, thread_name_prefix="clinical-feishu"
        )
        self._slots = BoundedSemaphore(self.policy.capacity)
        self._condition = Condition(RLock())
        self._futures: set[Future[WorkResult]] = set()
        self._closing = False

    def _release(self, lease: Lease) -> None:
        try:
            self._dedup.release(lease)
        except Exception:
            # Unknown Redis result: never retry or delete without the owner.
            pass

    def _check(self, lease: Lease) -> OperationResult:
        try:
            return self._dedup.check(lease)
        except Exception:
            return "unavailable"

    def submit(self, envelope: MessageEnvelope) -> Submission:
        envelope = MessageEnvelope.model_validate(envelope).model_copy(deep=True)
        with self._condition:
            if self._closing:
                return Submission("closed")
            if not self._slots.acquire(blocking=False):
                return Submission("busy")
            deadline = self._clock() + self.policy.processing_ms / 1000
            try:
                acquired = self._dedup.acquire(cast(Identity, envelope.dedup_identity))
            except Exception:
                self._slots.release()
                return Submission("unavailable")
            if acquired.status != "acquired" or acquired.lease is None:
                self._slots.release()
                return Submission("duplicate" if acquired.status == "duplicate" else "unavailable")
            lease = acquired.lease
            try:
                future = self._executor.submit(self._run, envelope, lease, deadline)
            except Exception:
                self._release(lease)
                self._slots.release()
                return Submission("submit_failed")
            self._futures.add(future)
            future.add_done_callback(lambda done: self._finished(done, lease))
            return Submission("accepted", future)

    def _finished(self, future: Future[WorkResult], lease: Lease) -> None:
        if future.cancelled():
            self._release(lease)
        with self._condition:
            self._slots.release()
            self._futures.remove(future)
            self._condition.notify_all()

    def _guard(self, lease: Lease, deadline: float) -> WorkResult | None:
        if self._clock() >= deadline:
            self._release(lease)
            return WorkResult("timed_out")
        ownership = self._check(lease)
        if ownership != "owned":
            return WorkResult(ownership)
        # Redis I/O also consumes the local processing budget.
        if self._clock() >= deadline:
            self._release(lease)
            return WorkResult("timed_out")
        return None

    def _run(self, envelope: MessageEnvelope, lease: Lease, deadline: float) -> WorkResult:
        stopped = self._guard(lease, deadline)
        if stopped is not None:
            return stopped
        answer = None
        error_code: Literal["research_failed"] | None = None
        try:
            request = QuestionRequest(question=envelope.text, request_id=envelope.request_id)
            answer = ResearchAnswer.model_validate(self._research.answer(request)).model_copy(
                deep=True
            )
            if answer.request_id != envelope.request_id:
                raise ValueError("Mismatched request")
        except Exception:
            answer, error_code = None, "research_failed"
        stopped = self._guard(lease, deadline)
        if stopped is not None:
            return stopped
        delivery = Delivery(
            envelope=envelope,
            lease=lease,
            deadline=min(deadline, self._clock()) + self.policy.handoff_ms / 1000,
            answer=answer,
            error_code=error_code,
        )
        try:
            accepted = self._sink.offer(delivery)
        except Exception:
            # The sender may already own this item. Preserve TTL and never retry.
            return WorkResult("delivery_unknown")
        if accepted:
            return WorkResult("queued")
        self._release(lease)
        return WorkResult("delivery_failed")

    def close(self, *, timeout_seconds: float = 5.0) -> bool:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds < 0
        ):
            raise ValueError("Invalid shutdown timeout")
        with self._condition:
            self._closing = True
        self._executor.shutdown(wait=False, cancel_futures=False)
        with self._condition:
            return self._condition.wait_for(lambda: not self._futures, timeout=timeout_seconds)
