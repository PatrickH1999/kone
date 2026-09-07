---
name: pre-release
description: Run the kone pre-release checklist before a merge into the release branch and a version tag. Use when the user asks for a release check, pre-release, release readiness, or whether development can be merged into release.
---

# Pre-release checks for kone

Run every check, collect all failures, and report a single verdict at the end:
**READY FOR RELEASE** or a numbered list of blockers. Do not stop at the first
failure. Never run git commands that change state (CLAUDE.md hard rule) —
read-only git like `status`, `diff`, `log` is fine.

## 1. Clean tree

`git status --porcelain` must be empty. Untracked or modified files are a
blocker: the release must be built from committed state only.

## 2. Build from scratch

`make clean && make`. Any warning or error is a blocker. Also build the
debug variant compiles: `make debug`, then `make clean && make` again to
leave a release build.

## 3. Formatting

Run `make format`, then `git status --porcelain`. If it reports changes,
formatting was not committed — blocker. (Restore with `git checkout -- .`
is NOT allowed; just report which files changed.)

## 4. Test suites

- `make test` — all three groups (test-kone, test-kasm, test-klib) must pass.
- `make -C logisim test` — the headless Logisim boot of the four programs
  must pass (~90 s).

## 5. Generated artifacts in sync

- `make -C logisim circ` — must succeed; afterwards `git status` must be
  clean (a differing .circ means the generator and the committed circuit
  diverged).
- If kicad/ exists: `make -C logisim kicad` and the DRC/ERC reports must
  show 0 violations. Skip gracefully with a note if KiCad is not installed.

## 6. Examples assemble

`make examples` — every examples/*.kasm must assemble without error.

## 7. Documentation consistency

- README.md is the canonical spec: spot-check that Make targets named in
  README.md and logisim/README.md actually exist in the Makefiles, and that
  klib routines listed in the index exist on disk (and vice versa: no
  undocumented klib file).
- CLAUDE.md must NOT be merged into release (it lives on development only)
  — verify it is absent from the release branch or flag it for the manual
  `git rm` step the author does during the merge.
- ISSUES.md: report items that look resolved so the author can prune.

## 8. Repo hygiene

- No stray build outputs tracked: obj/, bin/ binaries, __pycache__, *.circ
  files must be ignored or intentionally committed per .gitignore.
- Grep the diff since the last tag (`git describe --tags --abbrev=0`) for
  leftover debug prints, commented-out code, TODO/FIXME added since then.
  Report findings; the "no dead code" rule in CLAUDE.md makes them blockers.

## Report format

One line per check: `ok` / `FAIL` / `skipped (<reason>)`, then the verdict.
Keep it terse. List exact commands to reproduce any failure.
