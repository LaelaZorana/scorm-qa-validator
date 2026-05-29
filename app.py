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

import io
import zipfile
import tempfile

import gradio as gr

from scorm_qa.checks import validate_package
from scorm_qa import report

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

# Built-in samples: a clean package and three with the defects QA teams actually hit.
SAMPLES = {
    "✅ Clean package (1.2, all files present)": {
        "imsmanifest.xml": GOOD_MANIFEST,
        "lesson.html": "<html>Hello</html>",
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
        "imsmanifest.xml": GOOD_MANIFEST,
        "lesson.html": "<html/>",
        "extras/notes.txt": "orphaned asset",
    },
}


def _zip_from_files(files: dict) -> str:
    """Write an in-memory SCORM package to a temp .zip and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp, "w") as zf:
        for name, contents in files.items():
            zf.writestr(name, contents)
    tmp.close()
    return tmp.name


def _validate_path(zip_path: str, display_name: str):
    defects, _ = validate_package(zip_path)
    md = report.build_markdown(display_name, defects)
    critical = any(d["severity"] in ("CRITICAL", "HIGH") for d in defects)
    verdict = "❌ FAIL — would break on LMS upload" if critical else "✅ PASS"
    headline = f"### {verdict} — {len(defects)} defect(s) found"
    return headline, md


def run_sample(name: str):
    if not name:
        return "Pick a sample above.", ""
    path = _zip_from_files(SAMPLES[name])
    return _validate_path(path, name)


def run_upload(file_obj):
    if file_obj is None:
        return "⚠️ Upload a SCORM .zip, or try a built-in sample.", ""
    return _validate_path(file_obj.name, file_obj.name.split("/")[-1])


with gr.Blocks(title="SCORM QA Validator") as demo:
    gr.Markdown(
        "# 📦 SCORM QA Validator\n"
        "SCORM packages fail **silently** — a missing launch file or a wrong schema "
        "version doesn't error, it just shows the learner a blank screen after upload. "
        "This tool opens the package, parses `imsmanifest.xml`, and hands you a defect log "
        "(severity, location, recommended fix) *before* it ships to Docebo, Workday, or "
        "Cornerstone.\n\n"
        "*Runs the real package (`scorm_qa/`), the same code the 6-case pytest suite covers.*"
    )

    with gr.Tab("Try a built-in sample"):
        sample_dd = gr.Dropdown(choices=list(SAMPLES.keys()),
                                value=list(SAMPLES.keys())[0],
                                label="Sample package")
        sample_btn = gr.Button("Validate sample", variant="primary")
        s_headline = gr.Markdown()
        s_report = gr.Markdown()
        sample_btn.click(run_sample, inputs=sample_dd, outputs=[s_headline, s_report])
        demo.load(run_sample, inputs=sample_dd, outputs=[s_headline, s_report])

    with gr.Tab("Upload your own .zip"):
        up = gr.File(label="SCORM package (.zip)", file_types=[".zip"])
        up_btn = gr.Button("Validate package", variant="primary")
        u_headline = gr.Markdown()
        u_report = gr.Markdown()
        up_btn.click(run_upload, inputs=up, outputs=[u_headline, u_report])


if __name__ == "__main__":
    demo.launch()
