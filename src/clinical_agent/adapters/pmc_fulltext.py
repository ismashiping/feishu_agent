"""Licensed PMC OA acquisition. No scraping, redirects or automatic retries."""

import re
from time import monotonic

from defusedxml import ElementTree as ET

from clinical_agent.adapters.pubmed_online import _GATE


def parse_bioc(raw: bytes, pmcid: str) -> list[tuple[str, int, str]]:
    root = ET.fromstring(raw)
    documents = root.findall(".//document")
    if len(documents) != 1 or documents[0].findtext("id") not in (pmcid, pmcid[3:]):
        raise ValueError("fulltext_identity_mismatch")
    passages = []
    headings = {}
    for passage in documents[0].findall("passage"):
        text = passage.findtext("text", "")
        if not text.strip():
            continue
        section = (
            next(
                (i.text for i in passage.findall("infon") if i.get("key") == "section_type"),
                "UNKNOWN",
            )
            or "UNKNOWN"
        )
        passage_type = next(
            (i.text or "" for i in passage.findall("infon") if i.get("key") == "type"), ""
        )
        if passage_type.startswith("title"):
            headings[section] = text
            continue
        if section in headings:
            section = section + " / " + headings[section]
        offset = int(passage.findtext("offset", "-1"))
        if offset < 0:
            raise ValueError("fulltext_invalid_offset")
        passages.append((section, offset, text))
    if not passages:
        raise ValueError("fulltext_empty")
    return passages


class PMCSource:
    def __init__(self, client):
        self.client = client

    def _get(self, url, deadline, params=None):
        with _GATE.slot(deadline):
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("fulltext_timeout")
            with self.client.stream(
                "GET", url, params=params, timeout=min(5.0, remaining), follow_redirects=False
            ) as response:
                response.raise_for_status()
                data = bytearray()
                for block in response.iter_bytes():
                    data.extend(block)
                    if len(data) > 5 * 1024 * 1024 or monotonic() >= deadline:
                        raise ValueError("fulltext_budget")
                return bytes(data)

    def fetch(self, pmid, deadline):
        import json

        raw = self._get(
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/",
            deadline,
            {"ids": pmid, "format": "json"},
        )
        records = json.loads(raw).get("records", [])
        record = next((r for r in records if str(r.get("pmid")) == pmid), {})
        pmcid = record.get("pmcid", "")
        if not re.fullmatch(r"PMC[1-9][0-9]*", pmcid):
            raise ValueError("fulltext_no_verified_pmcid")
        oa = ET.fromstring(
            self._get(
                "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/",
                deadline,
                {
                    "verb": "GetRecord",
                    "identifier": f"oai:pubmedcentral.nih.gov:{pmcid[3:]}",
                    "metadataPrefix": "pmc",
                },
            )
        )
        licenses = [e for e in oa.iter() if e.tag.split("}")[-1] == "license"]
        license_name = ""
        for element in licenses:
            for value in element.attrib.values():
                if re.fullmatch(r"https?://creativecommons.org/licenses/by/4\.0/?", value):
                    license_name = "CC BY"
                elif re.fullmatch(r"https?://creativecommons.org/publicdomain/zero/1\.0/?", value):
                    license_name = "CC0"
        if not license_name:
            raise ValueError("fulltext_license_not_allowed")
        url = (
            "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
            f"BioC_xml/{pmcid}/unicode"
        )
        raw = self._get(url, deadline)
        return pmcid, license_name, url, raw, parse_bioc(raw, pmcid)
