# compat/ — the VERIFIED compatibility matrix

**CI-stamped only. Never hand-edited.**

Every file here (`compat/<module>.yaml`) is written exclusively by
[`.github/workflows/compat-stamp.yml`](../.github/workflows/compat-stamp.yml),
which appends one row per `repository_dispatch` of type `compat-stamp` sent by a
run of trunk's reusable
[`module-system-tests.yml`](https://github.com/castacks/AirStack/blob/main/.github/workflows/module-system-tests.yml)
workflow. Commits land under the `github-actions[bot]` identity. A PR that adds
or edits a compat row by hand is rejected on sight — a compatibility claim that
isn't CI-verified rots (RFC #379, design principles; §5).

The registry entry's `airstack_compat` field is the module author's **DECLARED**
range; this directory is the **VERIFIED** record. Badge semantics (RFC #379 §5):
a compat badge reads "module M @ vM passes marks {…} in a test stack derived
from reference stack S, on AirStack vX" — conformance to a *stack*, demonstrated
by flying it.

## File and row format

`compat/<module>.yaml` — `<module>` matches `modules/<module>.yaml`:

```yaml
# compat/optitrack.yaml — stamped by compat-stamp.yml; do not edit.
rows:
  - module_ref: v0.1.0                       # module tag or full 40-hex SHA that ran
    airstack_ref: v0.19.0                    # trunk ref the run tested against
    marks: "build_packages or liveliness or optitrack"   # pytest marks expression the run executed
    result: pass                             # pass | fail — red rows are recorded too
    run_url: https://github.com/castacks/asm_optitrack/actions/runs/123456789
    stamped_at: "2026-08-21T04:12:55Z"       # added by the stamp workflow (UTC)
    image_digests:                           # optional: the layer chain the badge was earned with
      robot: sha256:abc123...
```

- **Rows are append-only.** History is the point: the matrix shows which
  (module_ref, airstack_ref) pairs were exercised, when, and with what result.
- **Failures are stamped too** (`result: fail`) — the nightly canary's red rows
  are what drive the maintainer-lifecycle clock (see
  [`unmaintained/`](../unmaintained/README.md)).
- `run_url` makes every claim auditable: the row is only a pointer, the CI run
  is the evidence.
- `image_digests` (optional) records the composed image digest chain
  (RFC #379 §6) so a badge can be reproduced bit-for-bit.

The dispatch **sender** wiring (module CI posting the `compat-stamp` payload at
the end of a green/red run) lands trunk-side later; until then this directory
stays empty except this README.
