# airstack-modules-index

The **module and stack registry** for [AirStack](https://github.com/castacks/AirStack) —
the marketplace index, built on the
**rosdistro pattern**: an index repo of one small YAML per entry, version-pinned
refs, and CI-verified compatibility. `airstack module search|list|add` reads this
repo; the AirStack docs site renders it as the marketplace catalog with badges.

```text
airstack-modules-index/
├── schema/            entry schemas (module-entry, stack-entry)
├── modules/           one YAML per registered module
├── stacks/            one YAML per registered stack (trunk reference stacks + external)
├── compat/            VERIFIED compatibility matrix — CI-stamped ONLY, never hand-edited
├── releases/          release sets: tagged reference-stack pins blessed by one CI run
├── rfcs/              interface-conventions deprecation RFCs
├── unmaintained/      the shelf: entries whose canary went red and stayed red
└── tools/             validate_entry.py — the schema gate CI runs on every PR
```

## How to register a module

**Getting listed = opening a PR to this repo that adds `modules/<name>.yaml`.
The PR review is the quality gate.** Checklist a registration PR must clear:

1. **Schema-valid manifest** — the module repo's `module.yaml` passes trunk's
   [`tools/validate_module.py`](https://github.com/castacks/AirStack/blob/main/tools/validate_module.py)
   against
   [`common/module_schema/module.schema.json`](https://github.com/castacks/AirStack/blob/main/common/module_schema/module.schema.json).
2. **CI green** — the module's CI calls trunk's reusable
   [`module-system-tests.yml`](https://github.com/castacks/AirStack/blob/main/.github/workflows/module-system-tests.yml)
   and passes its declared marks. See
   [docs/development/module_ci.md](https://github.com/castacks/AirStack/blob/main/docs/development/module_ci.md)
   for wiring the ~12-line caller and choosing marks.
3. **README per template** — the module README follows the template
   (scaffolded by the
   [create-module skill](https://github.com/castacks/AirStack/tree/main/.agents/skills/create-module)
   / `airstack module create`); it is embedded on the versioned docs site.
4. **License check** — `license:` is a real SPDX-style license, surfaced here in
   the entry (a GPL module in an overlay chain must be visible, not buried).
5. **Registry entry valid** — `modules/<name>.yaml` passes
   `python3 tools/validate_entry.py` (CI runs it on the PR; maintainer email and
   non-empty license are hard registration gates).

Registered **stacks** get catalog entries too (`stacks/<name>.yaml`): description,
target trunk range, and the docs site embeds the stack's CI-generated `wiring.md`
from its home repo.

### After your entry merges: the trunk sync

Trunk (castacks/AirStack) keeps a mirror of these entries — the contract-test
fixture `tests/meta/fixtures/modules_index/` plus the committed
`docs/modules/` catalog pages — and the docs deploy regenerates the published
catalog from this **live** registry. The trunk mirror updates automatically:
the [`sync-modules-index`](https://github.com/castacks/AirStack/actions/workflows/sync-modules-index.yml)
workflow runs daily (dispatch it manually for an immediate sync) and opens
the trunk sync PR; the develop docs deploy files a `docs-catalog-drift` issue
in AirStack whenever trunk and this registry disagree. You don't need to
hand-edit anything in trunk — just make sure the sync PR gets merged.

## Compatibility: DECLARED vs VERIFIED

An entry's `airstack_compat` is the **DECLARED** range, copied from the module's
`module.yaml`. The **VERIFIED** matrix lives in [`compat/`](compat/), where rows
are stamped exclusively by CI runs of `module-system-tests.yml` (via the
`compat-stamp` repository dispatch — see
[`.github/workflows/compat-stamp.yml`](.github/workflows/compat-stamp.yml)).

**`compat/` is CI-stamped only — never hand-edited.** A PR that hand-writes a
compat row is rejected on sight; a compatibility claim that isn't CI-verified
rots — that is the registry's core design principle.

**Badge semantics**: a compat badge reads
"module M @ vM passes marks {…} in a test stack derived from reference stack S,
on AirStack vX" — conformance to a *stack*, demonstrated by flying it.

## Governance

- **Maintainer lifecycle.** Every entry names a maintainer (email, required).
  The nightly canary runs registered modules against trunk `develop`; a canary
  red **N weeks unanswered** auto-moves the entry to the
  [`unmaintained/`](unmaintained/) shelf — still listed, clearly labeled, never
  green-badged. Maintainers resurface, entries move back.
- **License checks at registration** — the `license` field is a hard gate in
  [`validate.yml`](.github/workflows/validate.yml).
- **Conventions deprecation policy.** The interface conventions spec is public
  API even though nothing compiles against it. Changing a canonical topic name,
  type, QoS profile, or frame convention requires semver-major on the spec, a
  coexistence window, and a short RFC in [`rfcs/`](rfcs/) — landed here *before*
  the change ships.
- **`airstack_msgs` is semver'd ruthlessly** as its own package — ROS 2 type
  hashes make message mismatches fail silently, so message-version discipline is
  what keeps badges meaningful across trunk versions.

## Release sets

A release set is **tagged reference-stack pins, blessed by one CI run** of the
whole stack: "AirStack 0.20 + `full_default` @ tag" — see
[`releases/`](releases/). Individual badges mean "works in a reference stack";
a release-set tag means "this whole stack, these exact pins, passed together."

## Validating locally

```bash
pip install pyyaml
python3 tools/validate_entry.py          # all of modules/ + stacks/
python3 tools/validate_entry.py modules/optitrack.yaml
```

JSON verdict on stdout, human-readable errors on stderr, exit 0/1 — the same
contract as trunk's `validate_module.py`.
