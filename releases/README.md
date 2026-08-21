# releases/ — release sets

A **release set is tagged reference-stack pins, blessed by one CI run** of the
whole stack (RFC #379 §7). Since a stack's pinned `modules.repos` already *is* a
tested-together set ("these modules at these versions, tested together" — RFC
#379 §3), a release set needs no machinery of its own: it records "AirStack X +
reference stack S @ tag", verified by a single full-conformance CI run of that
exact combination.

Semantics ladder:

- an individual compat badge ([`compat/`](../compat/README.md)) means
  "this module works in a reference stack";
- a **release-set file here** means "this whole stack, these exact pins, passed
  together."

Most users start from a tagged reference stack (`airstack init --release <X>`);
à-la-carte module picking is for developers. Release sets also drive the
versioned docs site: the site for version X embeds each module at X's
reference-stack pins (RFC #379 §9).

## File format

One file per trunk release, named after it — **`0.20.yaml` arrives at the first
release**; none exists yet (trunk is at `0.19.0-alpha.*`). Expected shape:

```yaml
# releases/0.20.yaml
airstack: v0.20.0                  # trunk tag
stacks:
  full_default:
    ref: v0.20.0                   # tag of the stack folder's repo at blessing time
    blessing_run: https://github.com/castacks/AirStack/actions/runs/...
  full_macvo:
    ref: v0.20.0
    modules:                       # the stack's modules.repos pins, recorded verbatim
      macvo: v0.1.0
    blessing_run: https://github.com/castacks/AirStack/actions/runs/...
```

A release-set file is added by PR from the release process, with each
`blessing_run` pointing at the one green CI run of the whole stack at those
pins.
