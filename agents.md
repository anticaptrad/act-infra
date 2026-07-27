# act-infra agent instructions

## Repository restrictions and infrastructure invariants

- Do not run `git reset`, `git filter-repo`, or `git clean`.
- Do not run `rm` except when explicitly deleting known temporary or scratch files.
- `dotenv` is blacklisted. Do not install or use it; configuration comes from Kubernetes configuration and secret references.
- Never commit secret values. Services that require credentials or shared secrets must receive them through secret references and fail closed when they are absent.
- Preserve non-root execution, disabled privilege escalation, read-only root filesystems, explicit writable volumes, resource controls, probes, and least-privilege network/service exposure.
- The AI publisher may read renders only from the mounted upload directory. Preserve channel ID/handle pinning and private-by-default publishing so swapped credentials or configuration cannot publish elsewhere or publicly.
- Treat pod-local `emptyDir` data as disposable. Use a deliberately reviewed persistent volume before promising durability across restarts.
- Avoid mutable image tags for production promotion; make image and deployment changes explicit, reviewable, and reproducible.

## Instruction discovery

Resolve `$PWD`, walk upward through every parent directory to the filesystem root, read every readable lowercase `agents.md` on that ancestor chain, and apply them root-to-leaf. Do not search siblings. Deduplicate resolved paths/inodes, avoid symlink cycles, and report unreadable files.

## Synchronize with the remote

Before editing, inspect `git status`, current branch, configured remotes, and the default branch. Run `git fetch --all --prune` and create the feature branch from the latest remote default branch, not a stale local branch. Fetch again before pushing and incorporate upstream changes using repository merge policy. Never discard remote commits, force-push, rewrite shared history, bypass review, or bypass required CI.

## Resolve Git conflicts semantically

Resolve conflicts by understanding and combining both sides' intent. Do not mechanically choose `ours`, `theirs`, current, or incoming changes. Produce the conceptually correct merged desired state while preserving compatible secret boundaries, fail-closed behavior, workload hardening, volume semantics, probes, resource/network constraints, channel pins, private publishing defaults, image provenance, tests, documentation, and deployment contracts. If intentions are incompatible, make the smallest explicit design decision and document it in the pull request.

After resolving, reread every affected manifest from the top, render and validate all overlays/manifests, run policy and security checks, and search the entire worktree for conflict markers:

```sh
grep -RInE '^(<<<<<<<|=======|>>>>>>>)' --exclude-dir=.git .
```

If any marker or suspicious partial resolution remains, repeat semantic resolution from the top and rerun validation. A conflict is resolved only when the resulting desired state is conceptually coherent and verified, not merely accepted by Git or YAML tooling.
