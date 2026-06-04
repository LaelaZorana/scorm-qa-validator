"""
Gradio demo for the SCORM QA Validator.

SCORM packages fail silently on LMS upload. A missing launch file or a wrong
schema version does not throw an error, it just shows the learner a blank screen
after the package goes live. This tool unzips the package, parses imsmanifest.xml,
and hands you a pre-flight defect log (severity, location, fix) before it ever
reaches Docebo, Workday, or Cornerstone.

The result is drawn as fully custom HTML into a single gr.HTML panel: a big
verdict card that says whether the package would pass or break, then the defects
as a vertical checklist of cards. All of it is controlled by the Python function,
not themed defaults. Runs the real package code in scorm_qa/.

Run locally:   pip install -r requirements.txt && python app.py
On Hugging Face Spaces this file is the entry point (app_file: app.py).
"""
from __future__ import annotations

import zipfile
import tempfile
from html import escape

import gradio as gr

from scorm_qa.checks import validate_package

ACCENT = "#059669"  # emerald
SEV_COLORS = {"CRITICAL": "#b91c1c", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "LOW": "#2563eb"}
SEV_ICON = {"CRITICAL": "✕", "HIGH": "✕", "MEDIUM": "!", "LOW": "!"}
SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


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
    "Clean package (1.2, all files present)": {
        "imsmanifest.xml": GOOD_MANIFEST, "lesson.html": "<html>Hello</html>",
    },
    "Missing launch file (lesson.html absent)": {
        "imsmanifest.xml": GOOD_MANIFEST,
    },
    "Unsupported schema version (9.9)": {
        "imsmanifest.xml": GOOD_MANIFEST.replace(
            "<schemaversion>1.2</schemaversion>", "<schemaversion>9.9</schemaversion>"),
        "lesson.html": "<html/>",
    },
    "Dangling extra file not in manifest": {
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


def _verdict_card(defects: list, source: str) -> str:
    src = escape(source)
    n = len(defects)
    blocking = any(d["severity"] in ("CRITICAL", "HIGH") for d in defects)
    minor = bool(defects) and not blocking

    if blocking:
        kind = "fail"
        icon = "✕"
        head = "FAIL, would break on LMS upload"
        sub = f"{n} blocking defect(s) found. Fix these before you upload."
    elif minor:
        kind = "warn"
        icon = "!"
        head = "PASS with minor issues"
        sub = f"{n} non-blocking defect(s). The package will load, but tidy these up."
    else:
        kind = "ok"
        icon = "✓"
        head = "PASS, ready to upload"
        sub = "No defects found. This package is well-formed."

    return f"""
    <div class="sc-verdict sc-verdict-{kind}">
      <div class="sc-verdict-badge">{icon}</div>
      <div class="sc-verdict-body">
        <div class="sc-verdict-kicker">PRE-FLIGHT CHECK</div>
        <div class="sc-verdict-head">{head}</div>
        <div class="sc-verdict-sub">{sub}</div>
      </div>
      <div class="sc-verdict-source">{src}</div>
    </div>
    """


def _all_clear() -> str:
    return """
    <div class="sc-clear">
      <div class="sc-clear-icon">✓</div>
      <div class="sc-clear-text">All checks passed</div>
      <div class="sc-clear-sub">Manifest parses, schema version is supported, every
        referenced file is present, and nothing is orphaned. Safe to deploy.</div>
    </div>
    """


def _defect_row(d: dict) -> str:
    sev = d["severity"]
    color = SEV_COLORS.get(sev, "#6b7280")
    icon = SEV_ICON.get(sev, "!")
    location = escape(str(d.get("location", "")))
    message = escape(str(d.get("message", "")))
    return f"""
    <div class="sc-row" style="--sev:{color}">
      <div class="sc-row-icon">{icon}</div>
      <div class="sc-row-main">
        <div class="sc-row-top">
          <span class="sc-chip" style="background:{color}">{escape(sev)}</span>
          <code class="sc-loc">{location}</code>
        </div>
        <div class="sc-row-msg">{message}</div>
      </div>
    </div>
    """


def _result_html(source: str, defects: list) -> str:
    verdict = _verdict_card(defects, source)
    if not defects:
        body = _all_clear()
    else:
        ordered = sorted(defects, key=lambda x: SEV_ORDER.get(x["severity"], 9))
        rows = "".join(_defect_row(d) for d in ordered)
        body = f'<div class="sc-list">{rows}</div>'
    return f'<div class="sc-result">{verdict}{body}</div>'


EMPTY_STATE = """
<div class="sc-empty">
  <div class="sc-empty-icon">📦</div>
  <div class="sc-empty-text">Pick a sample or upload a .zip to run the pre-flight check.</div>
  <div class="sc-empty-sub">Checks manifest, schema version, launch files, and orphaned assets.</div>
</div>
"""


def run_sample(name: str):
    if not name:
        return EMPTY_STATE
    path = _zip_from_files(SAMPLES[name])
    defects, _ = validate_package(path)
    return _result_html(name, defects)


def run_upload(file_obj):
    if file_obj is None:
        return EMPTY_STATE
    defects, _ = validate_package(file_obj.name)
    return _result_html(file_obj.name.split("/")[-1], defects)


CSS = """
:root {
  --sc-accent:#059669; --sc-bg1:#ecfdf5; --sc-bg2:#eff6ff; --sc-ink:#0f1f1a;
  --sc-muted:#5b6b64; --sc-card:#ffffff; --sc-line:rgba(15,31,26,.08);
  --sc-font:'Plus Jakarta Sans','Inter',system-ui,sans-serif;
}

/* Light lock: HF Spaces default to dark mode, but this UI is designed light.
   Override Gradio's dark theme variables so it renders light everywhere. */
:root, .dark, gradio-app.dark {
  color-scheme: light !important;
  --body-background-fill:#ffffff !important;
  --background-fill-primary:#ffffff !important;
  --background-fill-secondary:#f6f6fb !important;
  --block-background-fill:#ffffff !important;
  --block-label-background-fill:#ffffff !important;
  --input-background-fill:#ffffff !important;
  --border-color-primary:rgba(20,16,40,.12) !important;
  --body-text-color:#16131f !important;
  --body-text-color-subdued:#6b6880 !important;
  --block-title-text-color:#16131f !important;
  --block-info-text-color:#6b6880 !important;
}
html, body, gradio-app, .dark { background:#ffffff !important; }

.gradio-container { max-width: 820px !important; background:
  radial-gradient(1200px 500px at 12% -10%, var(--sc-bg1), transparent 60%),
  radial-gradient(1000px 500px at 112% 8%, var(--sc-bg2), transparent 55%) !important; }
.gradio-container, .gradio-container * { font-family: var(--sc-font); }

/* Header */
#sc-head { text-align:center; padding: 18px 8px 4px; }
#sc-head .sc-pill { display:inline-block; background:var(--sc-ink); color:#fff; border-radius:999px;
  padding:5px 13px; font-size:.7rem; font-weight:700; letter-spacing:.08em; margin-bottom:14px; }
#sc-head h1 { margin:0; font-size:2.05rem; font-weight:800; letter-spacing:-.02em; color:var(--sc-ink);
  background:linear-gradient(90deg,#059669,#0ea5a4,#2563eb); -webkit-background-clip:text;
  background-clip:text; -webkit-text-fill-color:transparent; }
#sc-head p { margin:10px auto 0; max-width:600px; color:var(--sc-muted); font-size:1.02rem; line-height:1.55; }
#sc-head code { background:rgba(5,150,105,.10); color:#047857; padding:1px 6px; border-radius:5px; font-size:.9em; }

/* Tabs + controls */
.sc-controls { margin-top:6px; }
#sc-go, #sc-go-up { border-radius:14px !important; font-weight:800 !important; font-size:1rem !important;
  background:linear-gradient(135deg,#059669,#0ea5a4) !important; border:none !important; color:#fff !important;
  box-shadow:0 10px 26px rgba(5,150,105,.32) !important; transition:transform .12s ease, box-shadow .12s ease !important; }
#sc-go:hover, #sc-go-up:hover { transform:translateY(-1px); box-shadow:0 14px 32px rgba(5,150,105,.42) !important; }

/* Result wrapper */
.sc-result { animation: sc-fade .35s ease both; }
@keyframes sc-fade { from{opacity:0; transform:translateY(8px)} to{opacity:1; transform:none} }

/* Verdict card */
.sc-verdict { display:flex; align-items:center; gap:18px; padding:20px 22px; border-radius:20px;
  background:var(--sc-card); border:1px solid var(--sc-line); position:relative; overflow:hidden;
  box-shadow:0 18px 44px rgba(15,31,26,.08); }
.sc-verdict-badge { width:52px; height:52px; border-radius:16px; flex-shrink:0; display:grid; place-items:center;
  font-size:1.6rem; font-weight:900; color:#fff; }
.sc-verdict-ok   { border-left:6px solid #059669; }
.sc-verdict-warn { border-left:6px solid #ca8a04; }
.sc-verdict-fail { border-left:6px solid #b91c1c; }
.sc-verdict-ok   .sc-verdict-badge { background:#059669; }
.sc-verdict-warn .sc-verdict-badge { background:#ca8a04; }
.sc-verdict-fail .sc-verdict-badge { background:#b91c1c; }
.sc-verdict-body { flex:1; min-width:0; }
.sc-verdict-kicker { font-size:.68rem; font-weight:800; letter-spacing:.1em; color:var(--sc-muted); }
.sc-verdict-head { font-size:1.35rem; font-weight:800; color:var(--sc-ink); letter-spacing:-.01em; margin-top:2px; }
.sc-verdict-sub { color:var(--sc-muted); font-size:.96rem; margin-top:3px; line-height:1.45; }
.sc-verdict-source { font-size:.78rem; color:var(--sc-muted); font-weight:700; max-width:150px; text-align:right;
  word-break:break-word; flex-shrink:0; }

/* Defect checklist */
.sc-list { margin-top:14px; display:flex; flex-direction:column; gap:10px; }
.sc-row { display:flex; align-items:flex-start; gap:14px; padding:14px 16px; border-radius:14px;
  background:var(--sc-card); border:1px solid var(--sc-line); border-left:5px solid var(--sev);
  box-shadow:0 8px 24px rgba(15,31,26,.05); animation: sc-fade .35s ease both; }
.sc-row-icon { width:26px; height:26px; border-radius:50%; flex-shrink:0; display:grid; place-items:center;
  font-size:.9rem; font-weight:900; color:#fff; background:var(--sev); margin-top:1px; }
.sc-row-main { flex:1; min-width:0; }
.sc-row-top { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.sc-chip { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.66rem; font-weight:800;
  color:#fff; letter-spacing:.04em; }
.sc-loc { background:rgba(15,31,26,.06); color:var(--sc-ink); padding:2px 8px; border-radius:6px;
  font-family:'SFMono-Regular',ui-monospace,Menlo,Consolas,monospace; font-size:.82rem; }
.sc-row-msg { margin-top:7px; color:var(--sc-ink); font-size:.95rem; line-height:1.5; }

/* All clear */
.sc-clear { margin-top:14px; text-align:center; padding:36px 22px; border-radius:20px; background:var(--sc-card);
  border:1px solid var(--sc-line); box-shadow:0 12px 32px rgba(5,150,105,.10); }
.sc-clear-icon { width:58px; height:58px; margin:0 auto; border-radius:50%; display:grid; place-items:center;
  font-size:1.8rem; font-weight:900; color:#fff; background:#059669; }
.sc-clear-text { margin-top:12px; font-weight:800; color:var(--sc-ink); font-size:1.2rem; }
.sc-clear-sub { margin-top:6px; color:var(--sc-muted); font-size:.95rem; line-height:1.55; max-width:480px;
  margin-left:auto; margin-right:auto; }

/* Empty state */
.sc-empty { text-align:center; padding:42px 20px; border-radius:20px; background:var(--sc-card);
  border:1px dashed var(--sc-line); }
.sc-empty-icon { font-size:2.4rem; }
.sc-empty-text { margin-top:10px; font-weight:700; color:var(--sc-ink); font-size:1.05rem; }
.sc-empty-sub { margin-top:4px; color:var(--sc-muted); font-size:.92rem; }

/* Footer */
.sc-footer { margin-top:22px; padding-top:16px; border-top:1px solid var(--sc-line);
  text-align:center; font-size:.88rem; color:var(--sc-muted); line-height:1.9; }
.sc-footer a { text-decoration:none; font-weight:700; color:var(--sc-accent); }
.sc-meta { text-align:center; color:var(--sc-muted); font-size:.82rem; margin-top:10px; }
.sc-meta code { background:rgba(5,150,105,.10); color:#047857; padding:1px 6px; border-radius:5px; }
"""

FOOTER = """
<div class="sc-footer">
📦 SCORM QA Validator, part of an AI evaluation &amp; QC toolkit by <b>Laela Zorana</b><br>
<a href="https://github.com/LaelaZorana/scorm-qa-validator">Source on GitHub</a> &middot;
<a href="https://huggingface.co/spaces/LaelaZ/ai-agent-scenario-qc">Scenario QC</a> &middot;
<a href="https://huggingface.co/spaces/LaelaZ/rlhf-pairwise-rater">RLHF Rater</a> &middot;
<a href="https://huggingface.co/spaces/LaelaZ/distilbert-emotion">Emotion Classifier</a>
</div>
"""

theme = gr.themes.Soft(
    primary_hue="emerald", neutral_hue="slate",
    font=[gr.themes.GoogleFont("Plus Jakarta Sans"), gr.themes.GoogleFont("Inter"),
          "system-ui", "sans-serif"],
)

with gr.Blocks(title="SCORM QA Validator", theme=theme, css=CSS) as demo:
    gr.HTML(
        '<div id="sc-head"><span class="sc-pill">E-LEARNING QA · PRE-FLIGHT CHECK</span>'
        "<h1>Would this SCORM package break on upload?</h1>"
        "<p>SCORM packages fail silently. A missing launch file or a wrong schema version "
        "does not throw an error, it just shows the learner a blank screen. This tool opens "
        "the package, parses <code>imsmanifest.xml</code>, and hands you a defect log "
        "before it reaches Docebo, Workday, or Cornerstone.</p></div>"
    )

    with gr.Tab("Try a built-in sample"):
        with gr.Group(elem_classes="sc-controls"):
            sample_dd = gr.Dropdown(choices=list(SAMPLES.keys()), value=list(SAMPLES.keys())[0],
                                    label="Sample package")
            sample_btn = gr.Button("Run pre-flight check", elem_id="sc-go", variant="primary")
        s_out = gr.HTML(EMPTY_STATE)
        sample_btn.click(run_sample, inputs=sample_dd, outputs=s_out)
        demo.load(run_sample, inputs=sample_dd, outputs=s_out)

    with gr.Tab("Upload your own .zip"):
        with gr.Group(elem_classes="sc-controls"):
            up = gr.File(label="SCORM package (.zip)", file_types=[".zip"])
            up_btn = gr.Button("Run pre-flight check", elem_id="sc-go-up", variant="primary")
        u_out = gr.HTML(EMPTY_STATE)
        up_btn.click(run_upload, inputs=up, outputs=u_out)

    gr.HTML(FOOTER)
    gr.HTML('<div class="sc-meta">Runs the real package (<code>scorm_qa/</code>), '
            'the same code the 6-case pytest suite covers.</div>')


if __name__ == "__main__":
    demo.launch()
