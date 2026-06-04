"""Defect-detection rules for SCORM packages."""
from __future__ import annotations

import zipfile
from xml.etree import ElementTree as ET

from .manifest import Manifest, parse_manifest, SUPPORTED_VERSIONS


def validate_package(zip_path: str) -> tuple[list[dict], Manifest | None]:
    """Open a SCORM .zip, run all QA checks, return defect list + parsed manifest."""
    defects: list[dict] = []
    manifest: Manifest | None = None

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        return [{"severity": "CRITICAL", "category": "package",
                 "location": zip_path,
                 "message": "File is not a valid ZIP archive"}], None

    names = zf.namelist()
    name_set = set(names)

    # Rule: imsmanifest.xml must exist at root
    if "imsmanifest.xml" not in name_set:
        defects.append({
            "severity": "CRITICAL", "category": "package",
            "location": "imsmanifest.xml",
            "message": "imsmanifest.xml is missing from the package root",
        })
        return defects, None

    # Parse manifest
    try:
        manifest = parse_manifest(zf.read("imsmanifest.xml"))
    except ET.ParseError as e:
        defects.append({
            "severity": "CRITICAL", "category": "manifest",
            "location": "imsmanifest.xml",
            "message": f"Manifest XML is malformed: {e}",
        })
        return defects, None

    # Rule: schemaversion supported
    if not manifest.schemaversion:
        defects.append({
            "severity": "HIGH", "category": "manifest",
            "location": "imsmanifest.xml/schemaversion",
            "message": "schemaversion element is missing",
        })
    elif manifest.schemaversion not in SUPPORTED_VERSIONS:
        defects.append({
            "severity": "CRITICAL", "category": "manifest",
            "location": "imsmanifest.xml/schemaversion",
            "message": f"schemaversion '{manifest.schemaversion}' is not supported "
                       f"(expected one of: {sorted(SUPPORTED_VERSIONS)})",
        })

    # Rule: at least one organization
    if manifest.organizations_count == 0:
        defects.append({
            "severity": "HIGH", "category": "manifest",
            "location": "imsmanifest.xml/organizations",
            "message": "No <organization> elements found",
        })

    # Rule: each resource href must reference an existing file
    referenced_files: set[str] = set()
    has_launch = False
    for r in manifest.resources:
        if r.scormtype == "sco":
            has_launch = True
        for file_ref in r.files + ([r.href] if r.href else []):
            if not file_ref:
                continue
            referenced_files.add(file_ref)
            if file_ref not in name_set:
                defects.append({
                    "severity": "HIGH", "category": "resources",
                    "location": file_ref,
                    "message": f"Referenced by manifest but missing from package",
                })

    # Rule: at least one SCO launch resource
    if manifest.resources and not has_launch:
        defects.append({
            "severity": "MEDIUM", "category": "resources",
            "location": "imsmanifest.xml/resources",
            "message": "No resource with scormtype='sco', package has no launchable SCO",
        })

    # Rule: dangling files in package
    for n in names:
        if n.endswith("/") or n == "imsmanifest.xml":
            continue
        if n.startswith("__MACOSX"):
            continue
        if n not in referenced_files:
            defects.append({
                "severity": "LOW", "category": "resources",
                "location": n,
                "message": "File present in package but not referenced by manifest",
            })

    return defects, manifest
