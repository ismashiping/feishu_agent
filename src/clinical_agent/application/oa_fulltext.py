"""OA extension of FulltextService; immutable abstract snapshots and bounded indexing."""

import json
import re
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from clinical_agent.domain.fulltext import FulltextPassage, FulltextUnit, paper_key
from clinical_agent.domain.governance import BLOCKED_STATUSES
from clinical_agent.domain.retrieval import retrieval_embedding_info

SIGNATURE = "oa-jats-pdf-llama-v2:" + retrieval_embedding_info().model_dump_json()


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
    lexical = sorted(
        range(len(candidates)),
        key=lambda i: (
            -len(terms & set(re.findall(r"[a-zA-Z]{2,}", candidates[i].text.casefold()))),
            i,
        ),
    )
    lex_rank = {i: rank for rank, i in enumerate(lexical, 1)}
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
    ordering = sorted(
        range(len(candidates)),
        key=lambda i: (
            section_priority(candidates[i].section, question),
            bool(preferred) and candidates[i].section.split(" / ")[0].casefold() not in preferred,
            -(1 / (60 + i + 1) + 4 / (60 + lex_rank[i])),
            i,
        ),
    )
    return [candidates[i] for i in ordering[:3]]


def enrich_openalex(service, question, result, *, deadline):
    from llama_index.core import Document
    from llama_index.core.node_parser import SentenceSplitter

    deadline = min(deadline, service.clock() + 35.0)
    acquisition_deadline = min(deadline, service.clock() + 15.0)
    count, seen, query, downloaded = [0], set(), None, 0
    for hit in result.hits:
        record = hit.document.openalex_record
        if record is None:
            continue
        key = paper_key(record)
        if key in seen:
            continue
        seen.add(key)
        reason = "fulltext_budget"
        if service.clock() >= deadline:
            result.warnings.append(f"{key}:{reason}")
            continue
        try:
            if hit.document.governance.status in BLOCKED_STATUSES:
                raise ValueError("fulltext_governance_blocked")
            payload = service.oa_store.load(key, SIGNATURE)
            if payload is None:
                if downloaded >= 3:
                    raise ValueError("fulltext_budget")
                before = count[0]
                try:
                    license_name, url, raw, units = service.oa_source.fetch_record(
                        record, acquisition_deadline, count
                    )
                finally:
                    # License/URL rejection before HTTP must not exhaust useful slots.
                    downloaded += int(count[0] > before)
                digest = sha256(raw).hexdigest()
                representation = [u.model_dump() for u in units]
                representation_hash = sha256(
                    json.dumps(representation, sort_keys=True).encode()
                ).hexdigest()
                if not service.oa_store.reuse_content(key, SIGNATURE, representation_hash):
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
                            "abstract",
                            "acknowledgments",
                            "acknowledgements",
                        }:
                            continue
                        for node in splitter.get_nodes_from_documents([Document(text=unit.text)]):
                            text = node.get_content()
                            position = node.start_char_idx
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
                            if len(chunks) > 128 or service.clock() >= deadline:
                                raise ValueError("fulltext_processing_budget")
                    if not chunks:
                        raise ValueError("fulltext_empty")
                    vectors = service.embedder.embed_passages(
                        [c["text"] for c in chunks], deadline=deadline
                    )
                    if service.clock() >= deadline:
                        raise ValueError("fulltext_timeout")
                    payload = {
                        "paper_key": key,
                        "passages": chunks,
                        "content_hash": digest,
                        "source_units": representation,
                        "representation_hash": representation_hash,
                    }
                    service.oa_store.publish(key, SIGNATURE, payload, vectors)
                else:
                    payload = service.oa_store.load(key, SIGNATURE)
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
            candidates = [
                FulltextPassage.model_validate(p) for p in service.oa_store.search(key, query, 16)
            ]
            present = {p.chunk_id for p in candidates}
            focused = [
                p for p in payload["passages"] if section_priority(p["section"], question) == 0
            ][:4]
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
                raise ValueError("fulltext_timeout")
            hit.fulltext = rerank_passages(candidates, question)
            reason = "fulltext_available" if hit.fulltext else "fulltext_empty"
        except Exception as error:
            # Enrichment is an optional task boundary: retain the abstract and a safe code.
            message = str(error)
            reason = message if re.fullmatch(r"fulltext_[a-z_]+", message) else "fulltext_failed"
        result.warnings.append(f"{key}:{reason}")
    return result
