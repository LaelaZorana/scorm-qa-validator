"""imsmanifest.xml parsing."""
from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET


@dataclass
class Resource:
    identifier: str
    type: str
    href: str | None
    scormtype: str | None
    files: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    schemaversion: str | None
    resources: list[Resource]
    organizations_count: int


def parse_manifest(xml_bytes: bytes) -> Manifest:
    root = ET.fromstring(xml_bytes)
    schemaversion = None
    organizations_count = 0
    resources: list[Resource] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "schemaversion":
            schemaversion = (elem.text or "").strip()
        elif tag == "organization":
            organizations_count += 1
        elif tag == "resource":
            r = Resource(
                identifier=elem.attrib.get("identifier", ""),
                type=elem.attrib.get("type", ""),
                href=elem.attrib.get("href"),
                scormtype=elem.attrib.get("scormtype"),
            )
            for child in elem.iter():
                if child.tag.split("}")[-1] == "file":
                    href = child.attrib.get("href")
                    if href:
                        r.files.append(href)
            resources.append(r)

    return Manifest(
        schemaversion=schemaversion,
        resources=resources,
        organizations_count=organizations_count,
    )
