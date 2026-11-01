"""OA extension of FulltextService; immutable abstract snapshots and bounded indexing."""

import json
import re
from hashlib import sha256
from typing import cast
from uuid import NAMESPACE_URL, uuid5

from clinical_agent.domain.fulltext import FulltextPassage, FulltextUnit, paper_key
from clinical_agent.domain.governance import BLOCKED_STATUSES
from clinical_agent.domain.retrieval import retrieval_embedding_info
from clinical_agent.integrations.oa_fulltext import Acquisition, AcquisitionError
from clinical_agent.logging_config import log_unexpected

SIGNATURE = "oa-content-tei-pdf-location-v2:" + retrieval_embedding_info().model_dump_json()


def section_priority(section, question):
    """Generic scientific intent; no organ/disease terms or claimed semantic entailment."""
    section = section.casefold()
    if re.search(r"比较|区别|对比|comparisons?|differences?|versus|\bvs\b", question, re.I):
        if "architecture" in section or "model design" in section:
            return 0
    if re.search(
        r"采集|扫描|序列|对比剂|acquisition|scanners?|sequences?|contrast|protocol", question, re.I
    ):
        if re.search(r"acquisition|imaging protocol|scanning|sequence", section):
            return 0
    if re.search(r"架构|网络|模型结构|architecture|network|model structure", question, re.I):
        if re.search(r"architecture|network|model development", section):
            return 0
    if re.search(r"结果|性能|指标|results?|performance", question, re.I) and "results" in section:
        return 0
    if re.search(
        r"局限|不足|讨论|瓶颈|limitations?|discussion|bottlenecks?|challenges", question, re.I
    ):
        if "limitations" in section or "discussion" in section:
            return 0
    return 1


def rerank_passages(candidates, question):
    # Match the actual question, not the broader discovery query. No English
    # terms means lexical ties retain the multilingual vector order.
    terms = set(re.findall(r"[a-zA-Z]{2,}", question.casefold())) - {
        "and",
        "not",
        "the",
        "which",
        "what",
        "were",
        "was",
        "used",
        "are",
        "for",
        "with",
        "from",
    }
    if re.search(r"采集|扫描|序列|对比剂", question):
        terms.update(
            {"acquisition", "protocol", "scanner", "scanners", "sequence", "sequences", "contrast"}
        )
    # Chinese questions are embedded by multilingual E5. These tokens only break
    # lexical ties inside one paper; they do not add papers or medical claims.
    if re.search(r"[\u4e00-\u9fff]", question):
        for word, english in (
            ("分割", "segmentation"),
            ("肝脏", "liver"),
            ("方法", "methods"),
            ("结果", "results"),
            ("局限", "limitations"),
            ("讨论", "discussion"),
            ("网络", "network"),
            ("模型", "model"),
        ):
            if word in question:
                terms.add(english)
    lexical = sorted(
        range(len(candidates)),
        key=lambda i: (
            -len(terms & set(re.findall(r"[a-zA-Z]{2,}", candidates[i].text.casefold()))),
            i,
        ),
    )
    lex_rank = {i: rank for rank, i in enumerate(lexical, 1)}
    preferred = preferred_sections(question)
    ordering = sorted(
        range(len(candidates)),
        key=lambda i: (
            section_priority(candidates[i].section, question),
            bool(preferred) and candidates[i].section.split(" / ")[0].casefold() not in preferred,
            -(1 / (60 + i + 1) + 4 / (60 + lex_rank[i])),
            i,
        ),
    )
    ordered = [candidates[i] for i in ordering]
    if preferred:
        return ordered[:3]
    picked = []
    for label in ("methods", "results", "discussion", "limitations"):
        for passage in ordered:
            if label in passage.section.casefold() and passage not in picked:
                picked.append(passage)
                break
    for passage in ordered:
        if passage not in picked:
            picked.append(passage)
        if len(picked) >= 3:
            break
    return picked[:3]


def preferred_sections(question):
    preferred = set()
    if re.search(
        r"methods?|architecture|acquisition|scanners?|sequences?|方法|架构|采集|参数",
        question,
        re.I,
    ):
        preferred.update({"methods", "materials and methods", "methodology"})
    if re.search(r"results?|performance|结果|性能|指标", question, re.I):
        preferred.update({"results", "experimental results"})
    if re.search(
        r"limitations?|discussion|bottlenecks?|challenges|局限|不足|讨论|瓶颈", question, re.I
    ):
        preferred.update({"limitations", "discussion"})
    return preferred


def _nearest(passages, vectors, query, limit):
    def score(vector):
        dot = sum(left * right for left, right in zip(query, vector, strict=False))
        left = sum(item * item for item in query) ** 0.5
        right = sum(item * item for item in vector) ** 0.5
        if left == 0 or right == 0:
            return 0.0
        return dot / (left * right)

    order = sorted(range(len(passages)), key=lambda index: (-score(vectors[index]), index))
    return [passages[index] for index in order[:limit]]


def enrich_openalex(service, question, result, *, deadline):
    from llama_index.core import Document
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.core.schema import TextNode

    deadline = min(deadline, service.clock() + 60.0)
    acquisition_deadline = min(deadline, service.clock() + 50.0)
    count, seen, query, downloaded = [0], set(), None, 0
    for hit in result.hits:
        record = hit.document.openalex_record
        if record is None:
            continue
        key = paper_key(record)
        if key in seen:
            continue
        seen.add(key)
        reason = "fulltext_budget;stage_deadline"
        if service.clock() >= deadline:
            result.warnings.append(f"{key}:{reason}")
            continue
        try:
            if hit.document.governance.status in BLOCKED_STATUSES:
                raise ValueError("fulltext_governance_blocked")
            payload = service.oa_store.load(key, SIGNATURE)
            held_vectors = None
            if payload is None:
                if downloaded >= 6:
                    raise AcquisitionError("fulltext_budget", "paper_limit")
                before = count[0]
                try:
                    fetched = service.oa_source.fetch_record(record, acquisition_deadline, count)
                finally:
                    # License/URL rejection before HTTP must not exhaust useful slots.
                    downloaded += int(count[0] > before)
                if isinstance(fetched, Acquisition):
                    license_name, url, raw, units = fetched
                    persist = fetched.persist
                else:
                    license_name, url, raw, units = fetched
                    persist = True
                digest = sha256(raw).hexdigest()
                representation = [u.model_dump() for u in units]
                representation_hash = sha256(
                    json.dumps(representation, sort_keys=True).encode()
                ).hexdigest()
                if persist and service.oa_store.reuse_content(key, SIGNATURE, representation_hash):
                    payload = service.oa_store.load(key, SIGNATURE)
                else:
                    chunks = []
                    splitter = SentenceSplitter(
                        chunk_size=300,
                        chunk_overlap=30,
                        tokenizer=lambda s: (
                            list(range(service.embedder.count_tokens(s))) if s.strip() else []
                        ),
                        include_metadata=False,
                    )
                    for unit in units:
                        if unit.section.split(" / ")[0].casefold() in {
                            "references",
                            "bibliography",
                            "abstract",
                            "acknowledgments",
                            "acknowledgements",
                        }:
                            continue
                        for node in splitter.get_nodes_from_documents([Document(text=unit.text)]):
                            text = node.get_content()
                            position = cast(TextNode, node).start_char_idx
                            if (
                                position is None
                                or unit.text[position : position + len(text)] != text
                            ):
                                raise ValueError("fulltext_unlocatable_chunk")
                            start = unit.start + position
                            passage = FulltextPassage(
                                chunk_id=uuid5(
                                    NAMESPACE_URL, f"{key}:{digest}:{start}:{SIGNATURE}"
                                ),
                                paper_key=key,
                                openalex_id=record.openalex_id,
                                title=record.title,
                                doi=record.doi,
                                section=unit.section,
                                page=unit.page,
                                start=start,
                                end=start + len(text),
                                text=text,
                                content_hash=digest,
                                representation_hash=representation_hash,
                                source_url=url,
                                license=license_name,
                            )
                            chunks.append(passage.model_dump(mode="json"))
                            if len(chunks) > 128:
                                raise AcquisitionError("fulltext_processing_budget", "chunk_limit")
                            if service.clock() >= deadline:
                                raise AcquisitionError(
                                    "fulltext_processing_budget", "stage_deadline"
                                )
                    if not chunks:
                        raise ValueError("fulltext_empty")
                    try:
                        vectors = service.embedder.embed_passages(
                            [c["text"] for c in chunks], deadline=deadline
                        )
                    except ValueError as error:
                        if str(error).startswith("embedding_"):
                            raise ValueError("fulltext_embedding_failed") from None
                        raise
                    if service.clock() >= deadline:
                        raise AcquisitionError("fulltext_timeout", "stage_deadline")
                    payload = {
                        "paper_key": key,
                        "passages": chunks,
                        "content_hash": digest,
                        "source_units": representation,
                        "representation_hash": representation_hash,
                    }
                    if persist:
                        service.oa_store.publish(key, SIGNATURE, payload, vectors)
                    else:
                        held_vectors = vectors
            if payload["paper_key"] != key:
                raise ValueError("fulltext_cache_identity_mismatch")
            units = [FulltextUnit.model_validate(u) for u in payload["source_units"]]
            if (
                sha256(json.dumps(payload["source_units"], sort_keys=True).encode()).hexdigest()
                != payload["representation_hash"]
            ):
                raise ValueError("fulltext_cache_representation_mismatch")
            if query is None:
                query = service.embedder.embed_query(question).vector
            rows = (
                _nearest(payload["passages"], held_vectors, query, 16)
                if held_vectors is not None
                else service.oa_store.search(key, query, 16)
            )
            candidates = [
                FulltextPassage.model_validate(p)
                for p in rows
                if "reference" not in p["section"].casefold()
                and "bibliograph" not in p["section"].casefold()
            ]
            present = {p.chunk_id for p in candidates}
            focused = [
                p for p in payload["passages"] if section_priority(p["section"], question) == 0
            ][:4]
            if not preferred_sections(question):
                for label in ("methods", "results", "discussion", "limitations"):
                    for item in payload["passages"]:
                        if (
                            label in item["section"].casefold()
                            and "reference" not in item["section"].casefold()
                        ):
                            focused.append(item)
                            break
            for item in focused:
                passage = FulltextPassage.model_validate(item)
                if passage.chunk_id not in present:
                    candidates.append(passage)
                    present.add(passage.chunk_id)
            for passage in candidates:
                if (
                    passage.paper_key != key
                    or passage.content_hash != payload["content_hash"]
                    or passage.representation_hash != payload["representation_hash"]
                ):
                    raise ValueError("fulltext_cache_identity_mismatch")
                if not any(
                    passage.page == u.page
                    and passage.section == u.section
                    and passage.start >= u.start
                    and passage.end <= u.start + len(u.text)
                    and u.text[passage.start - u.start : passage.end - u.start] == passage.text
                    for u in units
                ):
                    raise ValueError("fulltext_cache_location_mismatch")
            if service.clock() >= deadline:
                raise AcquisitionError("fulltext_timeout", "stage_deadline")
            hit.fulltext = rerank_passages(candidates, question)
            reason = "fulltext_available" if hit.fulltext else "fulltext_empty"
        except Exception as error:
            # Record a safe reason. The abstract hit stays for discovery display only;
            # OpenAlex answer generation does not use it as evidence.
            message = str(error)
            reason = message if re.fullmatch(r"fulltext_[a-z_]+", message) else "fulltext_failed"
            if reason == "fulltext_failed":
                log_unexpected("fulltext", error)
            detail = getattr(error, "basis", "")
            if isinstance(detail, str) and re.fullmatch(r"[a-z0-9_.:-]{1,80}", detail):
                reason = f"{reason};{detail}"
        result.warnings.append(f"{key}:{reason}")
    loaded = {}
    for hit in result.hits:
        record = hit.document.openalex_record
        if record is not None and hit.fulltext:
            loaded[paper_key(record)] = hit.fulltext
    for hit in result.hits:
        record = hit.document.openalex_record
        if record is not None and not hit.fulltext and paper_key(record) in loaded:
            hit.fulltext = list(loaded[paper_key(record)])
    return result
