"""Tests build SCORM zips in-memory and validate them."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from scorm_qa.checks import validate_package
from scorm_qa.manifest import parse_manifest


def _write_zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, contents in files.items():
            zf.writestr(name, contents)


GOOD_MANIFEST = """<?xml version="1.0"?>
<manifest identifier="MANIFEST-1" version="1.0">
  <metadata>
    <schemaversion>1.2</schemaversion>
  </metadata>
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


def test_good_package_passes(tmp_path):
    pkg = tmp_path / "good.zip"
    _write_zip(pkg, {
        "imsmanifest.xml": GOOD_MANIFEST,
        "lesson.html": "<html>Hi</html>",
    })
    defects, manifest = validate_package(str(pkg))
    assert defects == []
    assert manifest is not None
    assert manifest.schemaversion == "1.2"


def test_missing_manifest_is_critical(tmp_path):
    pkg = tmp_path / "no_manifest.zip"
    _write_zip(pkg, {"lesson.html": "<html/>"})
    defects, manifest = validate_package(str(pkg))
    assert manifest is None
    assert any(d["severity"] == "CRITICAL" and "imsmanifest" in d["message"] for d in defects)


def test_malformed_xml_is_critical(tmp_path):
    pkg = tmp_path / "bad_xml.zip"
    _write_zip(pkg, {"imsmanifest.xml": "<manifest><unclosed>"})
    defects, manifest = validate_package(str(pkg))
    assert manifest is None
    assert any(d["severity"] == "CRITICAL" and "malformed" in d["message"].lower() for d in defects)


def test_unsupported_schema_version(tmp_path):
    bad = GOOD_MANIFEST.replace("<schemaversion>1.2</schemaversion>",
                                "<schemaversion>9.9</schemaversion>")
    pkg = tmp_path / "badver.zip"
    _write_zip(pkg, {"imsmanifest.xml": bad, "lesson.html": "<html/>"})
    defects, _ = validate_package(str(pkg))
    assert any("9.9" in d["message"] for d in defects)


def test_missing_referenced_file(tmp_path):
    pkg = tmp_path / "missing_file.zip"
    _write_zip(pkg, {"imsmanifest.xml": GOOD_MANIFEST})  # lesson.html absent
    defects, _ = validate_package(str(pkg))
    assert any("lesson.html" in d["location"] and d["severity"] == "HIGH" for d in defects)


def test_dangling_file_flagged_low(tmp_path):
    pkg = tmp_path / "dangling.zip"
    _write_zip(pkg, {
        "imsmanifest.xml": GOOD_MANIFEST,
        "lesson.html": "<html/>",
        "extras/notes.txt": "junk",
    })
    defects, _ = validate_package(str(pkg))
    assert any("extras/notes.txt" in d["location"] and d["severity"] == "LOW" for d in defects)
