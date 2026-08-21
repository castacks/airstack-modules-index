# unmaintained/ — the shelf

The maintainer-lifecycle backstop from RFC #379 §8. Module authors are grad
students; grad students graduate. Rather than letting a dead module sit
green-badged in the catalog, the registry moves it here — **still listed,
clearly labeled, never green-badged.**

## The rule

The trunk-side **nightly canary** runs every registered module against trunk
`develop` (RFC #379 §5). When a module's canary is **red for N weeks with no
maintainer response** (N set by lab policy; failures are stamped as
`result: fail` rows in [`compat/`](../compat/README.md), so the clock is
auditable), its entry file is **moved** from `modules/<name>.yaml` to
`unmaintained/<name>.yaml` by PR, with a label block appended:

```yaml
# appended on shelving:
unmaintained:
  since: "2027-01-15"
  reason: canary red vs develop since 2026-12-01; maintainer unresponsive 6 weeks
  last_green: v0.19.0        # last airstack_ref with a passing compat row
```

## What shelving means

- The catalog still shows the module, under an explicit **Unmaintained**
  section — its last verified compat rows remain in `compat/` and remain true
  claims about the versions they name.
- `airstack module add <name>` still works but warns.
- The module is dropped from the nightly canary matrix (no more GPU spend on
  it).

## Coming back off the shelf

Any volunteer maintainer can adopt: PR moving the entry back to `modules/`,
with the `maintainer:` field updated and a fresh green run of the module's CI
(`module-system-tests.yml`) linked in the PR — the same quality gate as first
registration.

Nothing is shelved yet.
