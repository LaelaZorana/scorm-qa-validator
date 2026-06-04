"""imsmanifest.xml parsing."""
from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

# NOTE: kept here for reference / future XPath use, but right now we just
# match on local-name (elem.tag.split("}")[-1]). Real-world packages use a
# mix of these namespaces and some omit them entirely. See NOTES.md.
NS = {
    "ims": "http://www.imsproject.org/xsd/imscp_rootv1p1p2",
    "imscp": "http://www.imsglobal.org/xsd/imscp_v1p1",
    "adlcp_12": "http://www.adlnet.org/xsd/adlcp_rootv1p2",
    "adlcp_2004": "http://www.adlnet.org/xsd/adlcp_v1p3",
}

SUPPORTED_VERSIONS = {"1.2", "2004 3rd Edition", "2004 4th Edition", "CAM 1.3"}


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
    """Parse imsmanifest.xml bytes. Raises ET.ParseError on malformed XML."""
    root = ET.fromstring(xml_bytes)

    # schemaversion may live under various namespaces; search all
    schemaversion = None
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "schemaversion":
            schemaversion = (elem.text or "").strip()
            break

    organizations_count = 0
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "organization":
            organizations_count += 1

    resources: list[Resource] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag != "resource":
            continue
        # attributes, scormtype lives in adlcp namespace
        scormtype = None
        for attr_key, attr_val in elem.attrib.items():
            if attr_key.endswith("scormtype") or attr_key == "scormtype":
                scormtype = attr_val
        r = Resource(
            identifier=elem.attrib.get("identifier", ""),
            type=elem.attrib.get("type", ""),
            href=elem.attrib.get("href"),
            scormtype=scormtype,
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
