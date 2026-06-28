# Changelog

## Unreleased

- Switch XML parsing from stdlib `ElementTree` to `lxml` (better namespace handling on real packages)
- Add a `--strict` mode that treats MEDIUM/LOW as failures too
- Detect `prerequisites` references to non-existent items in `<organization>`

## 0.2.0: 2026-05-16

- Added "dangling files" detection (files in zip but not referenced by manifest)
- Schema-version check now lists supported values when failing
- Verdict line in report changed: `PASS WITH WARNINGS` when only LOW defects present

## 0.1.1: 2026-05-10

- Fix: `manifest.py` crashed when `<schemaversion>` lived under an unexpected namespace.
  Now searches by local-name across all namespaces.

## 0.1.0: 2026-05-05

- First version. Checks: zip validity, manifest presence, manifest parses, schemaversion
  supported, at least one organization, referenced files exist.
