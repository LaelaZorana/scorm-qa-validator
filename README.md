# scorm-qa-validator

**🔗 Live demo:** [try it on Hugging Face Spaces](https://huggingface.co/spaces/LaelaZ/scorm-qa-validator). Upload a `.zip` or click a built-in sample and see the defect log.

Validates SCORM 1.2 / 2004 packages from the command line. Made because I got tired of uploading a `.zip` to an LMS staging environment, waiting two minutes, and only then finding out the manifest pointed at a file that wasn't actually in the package.

## What it checks

- The `.zip` is actually a valid zip
- `imsmanifest.xml` is present at the root
- The manifest XML parses (no malformed tags)
- `<schemaversion>` is one we support: `1.2`, `2004 3rd Edition`, `2004 4th Edition`, `CAM 1.3`
- At least one `<organization>` exists
- Every `href` referenced by a `<resource>` actually exists in the package
- At least one resource has `scormtype="sco"` (otherwise nothing's launchable)
- Files in the zip that the manifest never references (dangling assets, usually leftover working files)

Severity tags: **CRITICAL** (won't even load), **HIGH** (will load but break), **MEDIUM** (loads, missing features), **LOW** (cosmetic, e.g. dead files).

## Install

Requires Python 3.9+. The validator itself runs on the standard library alone, with `xml.etree.ElementTree` for manifest parsing. The packages in `requirements.txt` cover the test suite (`pytest`) and the local Gradio demo (`app.py`), so one install covers everything.

```bash
pip install -r requirements.txt
```

## Use

```bash
python -m scorm_qa validate path/to/package.zip
```

Outputs a single line to stdout (`PASS  package.zip  defects=0  -> reports/package_report.md`) and writes a Markdown + JSON report to `reports/`.

Example output for a broken package:

```
FAIL  bad_package.zip  defects=3  -> reports/bad_package_report.md
```

And the report:

```markdown
# SCORM QA Report: `bad_package.zip`

**Verdict:** FAIL
**Defects:** 3

## Defects
- **[CRITICAL]** `imsmanifest.xml/schemaversion`: schemaversion '1.1' is not supported
- **[HIGH]** `resources/lesson.htm`: referenced by manifest but missing from package
- **[LOW]** `extras/notes.txt`: present in package but not referenced by manifest
```

## Tests

```bash
pytest -v
```

The test suite builds SCORM packages in `tmp_path` (using `zipfile` and the standard "good" manifest as a base) and asserts that each defect class is detected. No real `.zip` files are checked in, because the fixtures build them on the fly so the test directory stays small.

## Why I made this

My background is L&D and LMS administration (Docebo, Workday), and SCORM packages fail in really annoying ways: silent failures, "course loaded but tracking doesn't work," and so on. I wanted a quick smoke test I could run locally before uploading anything, but most of the open-source SCORM tools I found were either authoring tools (Articulate-adjacent) or full LMS engines, nothing as small as "tell me what's wrong with this zip."

Treat it as a quick sanity check, and run the SCORM ADL conformance suites when you need a full conformance result.

## Layout

```
scorm_qa/
  __main__.py      CLI entrypoint
  manifest.py      imsmanifest.xml parsing
  checks.py        defect rules
  report.py        markdown + json output
tests/
  test_validation.py
```

## License

MIT.

**Links:** [GitHub](https://github.com/LaelaZorana) · [HuggingFace](https://huggingface.co/LaelaZ) · [Kaggle](https://www.kaggle.com/laelazorana)
