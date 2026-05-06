"""Tests build SCORM zips in-memory and validate them."""
from __future__ import annotations

import zipfile
from pathlib import Path

from scorm_qa.checks import validate_package


def _write_zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, contents in files.items():
            zf.writestr(name, contents)


GOOD_MANIFEST = """<?xml version="1.0"?>
<manifest identifier="MANIFEST-1" version="1.0">
  <metadata><schemaversion>1.2</schemaversion></metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1"><title>Course</title></organization>
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
    _write_zip(pkg, {"imsmanifest.xml": GOOD_MANIFEST, "lesson.html": "<html/>"})
    defects, manifest = validate_package(str(pkg))
    assert defects == []


def test_missing_manifest_is_critical(tmp_path):
    pkg = tmp_path / "no_manifest.zip"
    _write_zip(pkg, {"lesson.html": "<html/>"})
    defects, manifest = validate_package(str(pkg))
    assert manifest is None
    assert any(d["severity"] == "CRITICAL" for d in defects)


def test_missing_referenced_file(tmp_path):
    pkg = tmp_path / "missing_file.zip"
    _write_zip(pkg, {"imsmanifest.xml": GOOD_MANIFEST})
    defects, _ = validate_package(str(pkg))
    assert any("lesson.html" in d["location"] for d in defects)
