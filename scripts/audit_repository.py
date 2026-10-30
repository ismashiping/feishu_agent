"""Read-only repository inventory and local Markdown checks (standard library only)."""

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def files():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted({p for p in result.stdout.splitlines() if (ROOT / p).is_file()})


def anchors(text):
    counts = {}
    result = set(re.findall(r'<a\s+(?:name|id)=["\']([^"\']+)', text))
    fenced = False
    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
        if fenced or not re.match(r"^#{1,6}\s", line):
            continue
        title = re.sub(r"^#+\s+", "", line).strip().lower()
        title = re.sub(r"[^\w\-\s]", "", title).replace(" ", "-")
        count = counts.get(title, 0)
        counts[title] = count + 1
        result.add(title + (f"-{count}" if count else ""))
    return result


def scan():
    inventory, documents, modules, issues = [], [], [], []
    for name in files():
        path = ROOT / name
        data = path.read_bytes()
        inventory.append({"path": name, "sha256": hashlib.sha256(data).hexdigest()})
        if path.suffix == ".py":
            text = data.decode("utf-8-sig")
            tree = ast.parse(text)
            imports = sorted(
                {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
                | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            )
            modules.append(
                {
                    "path": name,
                    "lines": len(text.splitlines()),
                    "imports": imports,
                    "definitions": [
                        n.name
                        for n in tree.body
                        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                    ],
                }
            )
        if path.suffix not in {".md", ".txt", ".rst", ".in"}:
            continue
        text = data.decode("utf-8-sig")
        headings = re.findall(r"^#+\s+(.+)$", text, re.M)
        kind = "操作指南"
        if "/specs/" in name:
            kind = "需求契约/阶段任务快照"
        elif "/learning/" in name:
            kind = "学习材料"
        elif "/research/" in name:
            kind = "历史调研/依赖证据"
        elif "acceptance" in name or "medical-review" in name or name.startswith("evaluation/"):
            kind = "验收/评价原始证据"
        elif "/archive/" in name:
            kind = "历史快照"
        elif "/current/" in name:
            kind = "当前事实"
        elif "plan" in name or "roadmap" in name:
            kind = "规划/时点记录"
        elif name in {"AGENTS.md.txt", "PROJECT.md.txt"}:
            kind = "项目约定"
        local = []
        # Inline links/images and reference definitions; skip fenced examples.
        prose = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
        links = re.findall(r"!?\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+[^)]*)?\)", prose)
        links += re.findall(r"(?m)^\s*\[[^]]+\]:\s*<?([^\s>]+)", prose)
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme or link.startswith("//"):
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            reason = None
            if not target.exists():
                reason = "missing_file"
            elif parsed.fragment and target.suffix in {".md", ".txt"}:
                if unquote(parsed.fragment).lower() not in anchors(
                    target.read_text(encoding="utf-8-sig")
                ):
                    reason = "missing_anchor"
            if reason:
                issue = {"path": name, "link": link, "reason": reason}
                issues.append(issue)
                local.append(issue)
        fences = re.findall(r"(?m)^\s*(`{3,}|~{3,})", text)
        if len(fences) % 2:
            issues.append({"path": name, "reason": "unbalanced_fence"})
        documents.append(
            {
                "path": name,
                "title": headings[0] if headings else path.name,
                "type": kind,
                "headings": headings,
                "lines": len(text.splitlines()),
                "status_mentions": [
                    line
                    for line in text.splitlines()
                    if any(
                        w in line for w in ("未验收", "待签署", "未执行", "passed", "尚未", "延期")
                    )
                ],
                "issues": local,
            }
        )
    domain_violations = [
        {"path": m["path"], "import": i}
        for m in modules
        if m["path"].startswith("src/clinical_agent/domain/")
        for i in m["imports"]
        if i.startswith(
            (
                "clinical_agent.application",
                "clinical_agent.adapters",
                "langgraph",
                "langchain",
                "sqlalchemy",
                "httpx",
                "feishu",
            )
        )
    ]
    return {
        "inventory": inventory,
        "documents": documents,
        "modules": modules,
        "issues": issues,
        "domain_violations": domain_violations,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = scan()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "files": len(report["inventory"]),
                "documents": len(report["documents"]),
                "python": len(report["modules"]),
                "issues": report["issues"],
                "domain_violations": report["domain_violations"],
            },
            ensure_ascii=False,
        )
    )
