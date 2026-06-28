# Implementation notes

Random things I learned/decided while writing this:

- **Namespaces:** SCORM packages I've handled in the wild use a wide mix of
  namespace declarations (`imscp_rootv1p1p2`, `imscp_v1p1`, occasionally
  none at all). Trying to use namespace-prefixed XPath was a pain, so I
  ended up iterating with `elem.tag.split("}")[-1]` to match on local name
  only. Not ideal, but robust.

- **`scormtype` attribute:** This lives under the ADLCP namespace and the
  namespace URI changed between SCORM 1.2 and 2004. Same trick as above,
  I just check if any attribute key *ends with* `scormtype`.

- **Why not validate against the official SCORM XSDs?** The XSDs are
  picky, packages in production are often slightly non-conformant, and
  the actual LMS players are forgiving. I'd rather catch the things that
  actually break uploads than chase XSD-perfect packages.

- **`__MACOSX/` directories** in zips are a constant nuisance from macOS
  zipping the package via Finder. Skipped from the dangling-file check.

## Things I'd do differently next time

- Start with `lxml` instead of `ElementTree`. `ElementTree` works but its
  namespace API is awkward.
- Use Click for the CLI instead of argparse. The CLI is tiny but Click
  is friendlier as soon as you add flags.
