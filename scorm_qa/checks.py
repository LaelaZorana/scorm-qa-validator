"""Defect-detection rules for SCORM packages."""
from __future__ import annotations

import zipfile
from xml.etree import ElementTree as ET

from .manifest import Manifest, parse_manifest

SUPPORTED_VERSIONS = {"1.2", "2004 3rd Edition", "2004 4th Edition", "CAM 1.3"}


def validate_package(zip_path: str) -> tuple[list[dict], Manifest | None]:
    defects: list[dict] = []
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        return [{"severity": "CRITICAL", "category": "package",
                 "location": zip_path,
                 "message": "File is not a valid ZIP archive"}], None

    names = zf.namelist()
    name_set = set(names)

    if "imsmanifest.xml" not in name_set:
        defects.append({
            "severity": "CRITICAL", "category": "package",
            "location": "imsmanifest.xml",
            "message": "imsmanifest.xml is missing from the package root",
        })
        return defects, None

    try:
        manifest = parse_manifest(zf.read("imsmanifest.xml"))
    except ET.ParseError as e:
        defects.append({
            "severity": "CRITICAL", "category": "manifest",
            "location": "imsmanifest.xml",
            "message": f"Manifest XML is malformed: {e}",
        })
        return defects, None

    if not manifest.schemaversion or manifest.schemaversion not in SUPPORTED_VERSIONS:
        defects.append({
            "severity": "CRITICAL", "category": "manifest",
            "location": "imsmanifest.xml/schemaversion",
            "message": f"schemaversion '{manifest.schemaversion}' is not supported",
        })

    return defects, manifest
