---
title: SCORM QA Validator
emoji: 📦
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
license: mit
---

# SCORM QA Validator

SCORM packages fail **silently** — a missing launch file or a wrong schema version
doesn't throw an error, it just shows the learner a blank screen after upload. This
tool opens the package, parses `imsmanifest.xml`, and hands you a manual-QA-style
defect log (severity, location, recommended fix) *before* it ships to Docebo, Workday,
or Cornerstone.

Upload your own `.zip`, or click a built-in sample (clean + broken) to see it work.
This Space runs the actual package (`scorm_qa/`) — the same code covered by the
project's 6-case pytest suite.

**Source & full docs:** https://github.com/LaelaZorana/scorm-qa-validator
