# rfcs/ — interface-conventions deprecation RFCs

The AirStack **interface conventions spec** (canonical topic names, message
types, QoS profiles, TF frames/units — RFC #379 §4) is public API even though
nothing compiles against it: registered modules' launch-arg *defaults* and the
conformance tests encode it. Changing it silently would teach everyone the
compat badges are meaningless.

Per RFC #379 §8, changing a canonical topic name, type, QoS profile, or frame
convention therefore requires:

1. **semver-major on the spec**,
2. **a coexistence window** (old and new conventions both valid while modules
   migrate),
3. **a short RFC in this directory** — landed *before* the change ships.

The same process gates growing `doctor`'s hard-error list (RFC #379 §4 fixes it
at exactly two gates: dep conflicts at compose time, and control-setpoint /
trajectory-group topics in a `bridge.yaml`).

## Process

- One markdown file per RFC: `NNN-short-slug.md` (numbered in merge order).
- Content: what changes, why, the migration/coexistence plan (window length,
  how conformance tests handle both forms), and which spec version it lands in.
- Opened as a PR to this repo; module maintainers are the review audience —
  they are the ones whose defaults break.
- **Additions** to the spec (a new canonical topic group) take the same route
  but are semver-minor; the discovery mechanism is drift reports across forks
  (RFC #379 §11) — three forks patching the same tap point = a missing
  convention.

None yet.
