"""Report generation."""
from __future__ import annotations

import json
from pathlib import Path

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def build_markdown(zip_path: str, defects: list[dict]) -> str:
    sorted_d = sorted(defects, key=lambda d: SEVERITY_ORDER.get(d["severity"], 99))
    critical = any(d["severity"] in ("CRITICAL", "HIGH") for d in defects)
    verdict = "FAIL" if critical else ("PASS WITH WARNINGS" if defects else "PASS")

    lines: list[str] = []
    lines.append(f"# SCORM QA Report: `{Path(zip_path).name}`")
    lines.append("")
    lines.append(f"**Verdict:** {verdict}")
    lines.append(f"**Defects:** {len(defects)}")
    lines.append("")
    lines.append("## Defects")
    if not defects:
        lines.append("_No defects detected._")
    else:
        for d in sorted_d:
            lines.append(f"- **[{d['severity']}]** `{d['location']}`: {d['message']}")
    lines.append("")
    return "\n".join(lines)


def write_reports(out_dir: str | Path, zip_path: str, defects: list[dict]) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(zip_path).stem
    md = out / f"{stem}_report.md"
    js = out / f"{stem}_report.json"
    md.write_text(build_markdown(zip_path, defects), encoding="utf-8")
    js.write_text(json.dumps({"source": zip_path, "defects": defects}, indent=2), encoding="utf-8")
    return md, js
