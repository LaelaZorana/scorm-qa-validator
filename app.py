"""
Gradio demo for the SCORM QA Validator.

SCORM packages fail *silently* on LMS upload — a missing launch file or a bad
schema version just shows a blank screen to the learner. This tool unzips the
package, parses imsmanifest.xml, and produces a manual-QA-style defect log
(severity, location, recommended fix) before you ever upload to Docebo, Workday,
or Cornerstone.

Upload your own .zip, or click a built-in sample (good + broken) to see it work.
Runs the real package code in scorm_qa/ — the same code the pytest suite covers.

Run locally:   pip install -r requirements.txt && python app.py
On Hugging Face Spaces this file is the entry point (app_file: app.py).
"""
from __future__ import annotations

import zipfile
import tempfile
from html import escape

import gradio as gr

from scorm_qa.checks import validate_package

ACCENT = "#059669"  # green
SEV_COLORS = {"CRITICAL": "#b91c1c", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "LOW": "#2563eb"}

CSS = """
:root { --accent: %s; }
.gradio-container { max-width: 1120px !important; }
#hero { background: linear-gradient(135deg, var(--accent), #0f172a);
        color:#fff; border-radius:18px; padding:26px 30px; margin-bottom:6px; }
#hero h1 { margin:0 0 8px 0; font-size:1.75rem; font-weight:800; letter-spacing:-.01em; }
#hero p { margin:0; opacity:.93; font-size:1.02rem; line-height:1.5; max-width:780px; }
#hero .pill { display:inline-block; background:rgba(255,255,255,.16); border-radius:999px;
        padding:3px 11px; font-size:.74rem; font-weight:700; margin-bottom:12px; letter-spacing:.04em; }
.verdict { border-radius:12px; padding:14px 18px; font-size:1.12rem; font-weight:800; margin:2px 0 14px; }
.verdict.pass { background:#dcfce7; color:#166534; border:1px solid #86efac; }
.verdict.fail { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; }
table.qc { width:100%%; border-collapse:collapse; margin:8px 0; font-size:.92rem; }
table.qc th { text-align:left; padding:7px 10px; border-bottom:2px solid var(--accent); font-weight:700; }
table.qc td { padding:8px 10px; border-bottom:1px solid rgba(128,128,128,.2); vertical-align:top; }
.sev { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.7rem;
        font-weight:800; color:#fff; letter-spacing:.03em; }
.qc code { background:rgba(128,128,128,.16); padding:1px 6px; border-radius:5px; }
.footer { margin-top:20px; padding-top:14px; border-top:1px solid rgba(128,128,128,.25);
        font-size:.88rem; text-align:center; opacity:.92; }
.footer a { text-decoration:none; font-weight:700; color:var(--accent); }
""" % ACCENT

FOOTER = """
<div class="footer">
🧰 Part of an AI evaluation &amp; QC toolkit by <b>Laela Zorana</b> &nbsp;·&nbsp;
🔍 <a href="https://huggingface.co/spaces/LaelaZ/ai-agent-scenario-qc">Scenario QC</a> &nbsp;·&nbsp;
⚖️ <a href="https://huggingface.co/spaces/LaelaZ/rlhf-pairwise-rater">RLHF Rater</a> &nbsp;·&nbsp;
📦 SCORM QA &nbsp;·&nbsp;
<a href="https://github.com/LaelaZorana/scorm-qa-validator">Source on GitHub</a>
</div>
"""

GOOD_MANIFEST = """<?xml version="1.0"?>
<manifest identifier="MANIFEST-1" version="1.0">
  <metadata><schemaversion>1.2</schemaversion></metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>Course</title>
      <item identifier="ITEM-1" identifierref="RES-1"><title>Lesson</title></item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-1" type="webcontent" scormtype="sco" href="lesson.html">
      <file href="lesson.html"/>
    </resource>
  </resources>
</manifest>
"""

SAMPLES = {
    "✅ Clean package (1.2, all files present)": {
        "imsmanifest.xml": GOOD_MANIFEST, "lesson.html": "<html>Hello</html>",
    },
    "❌ Missing launch file (lesson.html absent)": {
        "imsmanifest.xml": GOOD_MANIFEST,
    },
    "❌ Unsupported schema version (9.9)": {
        "imsmanifest.xml": GOOD_MANIFEST.replace(
            "<schemaversion>1.2</schemaversion>", "<schemaversion>9.9</schemaversion>"),
        "lesson.html": "<html/>",
    },
    "⚠️ Dangling extra file not in manifest": {
        "imsmanifest.xml": GOOD_MANIFEST, "lesson.html": "<html/>",
        "extras/notes.txt": "orphaned asset",
    },
}


def _zip_from_files(files: dict) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp, "w") as zf:
        for name, contents in files.items():
            zf.writestr(name, contents)
    tmp.close()
    return tmp.name


def _result_html(display_name: str, defects: list) -> str:
    critical = any(d["severity"] in ("CRITICAL", "HIGH") for d in defects)
    if critical:
        banner = ('<div class="verdict fail">❌ FAIL — would break on LMS upload &nbsp;·&nbsp; '
                  f"{len(defects)} defect(s)</div>")
    elif defects:
        banner = ('<div class="verdict pass">⚠️ PASS with minor issues &nbsp;·&nbsp; '
                  f"{len(defects)} defect(s)</div>")
    else:
        banner = '<div class="verdict pass">✅ PASS — no defects found</div>'

    if not defects:
        return banner + "<p>Package is well-formed and ready to upload.</p>"

    rows = ['<table class="qc"><tr><th>Severity</th><th>Location</th><th>Issue</th></tr>']
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    for d in sorted(defects, key=lambda x: order.get(x["severity"], 9)):
        color = SEV_COLORS.get(d["severity"], "#6b7280")
        rows.append(
            f'<tr><td><span class="sev" style="background:{color}">{escape(d["severity"])}</span></td>'
            f'<td><code>{escape(str(d.get("location", "")))}</code></td>'
            f'<td>{escape(str(d.get("message", "")))}</td></tr>'
        )
    rows.append("</table>")
    return banner + "\n".join(rows)


def run_sample(name: str):
    if not name:
        return '<div class="verdict fail">Pick a sample above.</div>'
    path = _zip_from_files(SAMPLES[name])
    defects, _ = validate_package(path)
    return _result_html(name, defects)


def run_upload(file_obj):
    if file_obj is None:
        return '<div class="verdict fail">⚠️ Upload a SCORM .zip, or try a built-in sample.</div>'
    defects, _ = validate_package(file_obj.name)
    return _result_html(file_obj.name.split("/")[-1], defects)


theme = gr.themes.Soft(primary_hue="emerald", neutral_hue="slate",
                       font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"])

with gr.Blocks(title="SCORM QA Validator", theme=theme, css=CSS) as demo:
    gr.HTML(
        '<div id="hero"><span class="pill">E-LEARNING QA</span>'
        "<h1>📦 SCORM QA Validator</h1>"
        "<p>SCORM packages fail <b>silently</b> — a missing launch file or a wrong schema version "
        "doesn't error, it just shows the learner a blank screen after upload. This tool opens the "
        "package, parses <code>imsmanifest.xml</code>, and hands you a defect log (severity, location, "
        "fix) <i>before</i> it ships to Docebo, Workday, or Cornerstone.</p></div>"
    )

    with gr.Tab("Try a built-in sample"):
        sample_dd = gr.Dropdown(choices=list(SAMPLES.keys()), value=list(SAMPLES.keys())[0],
                                label="Sample package")
        sample_btn = gr.Button("Validate sample ▶", variant="primary", size="lg")
        s_out = gr.HTML()
        sample_btn.click(run_sample, inputs=sample_dd, outputs=s_out)
        demo.load(run_sample, inputs=sample_dd, outputs=s_out)

    with gr.Tab("Upload your own .zip"):
        up = gr.File(label="SCORM package (.zip)", file_types=[".zip"])
        up_btn = gr.Button("Validate package ▶", variant="primary", size="lg")
        u_out = gr.HTML()
        up_btn.click(run_upload, inputs=up, outputs=u_out)

    gr.HTML(FOOTER)
    gr.Markdown("*Runs the actual package (`scorm_qa/`) — the same code the 6-case pytest suite covers.*")


if __name__ == "__main__":
    demo.launch()
