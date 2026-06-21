# hermes-gpt v0.2.0 — Operator Mode

## Summary

- Adds tiered Operator / Owner Mode to `hermes-gpt`.
- Default posture remains read-only/dry-run.
- Operator tools are registered, but mutating calls refuse unless explicitly enabled and `dry_run=false`.
- Owner Mode requires exact break-glass acknowledgement.
- Designed for trusted local MCP use, not as a sandbox.

## Highlights

- Operator policy, status, and audit tools
- Cron list, status, run, pause, copy, move
- Skill dry-run, diff, and manager-routed mutations
- Config/env safe tools
- Gateway status and restart
- Workspace scoped read, patch, write, and test tools
- Owner tools behind explicit acknowledgement
- Audit log with hashes and lengths instead of raw prompts/content
- Data-root normalization fix
- Package build includes operator modules
- New user docs for read-only, dry-run, direct operator, and owner postures

## Safety notes

- No `shell=True`
- No secret path access
- `.env`, auth, token, vault, SSH, and cookie paths denied
- Direct skill copy refuses safely in v0.2.0
- Operator Mode is not a sandbox
- Use OS isolation for untrusted input
- Keep tunnel default in dry-run mode

## Verification

- `pytest`: pass
- `py_compile`: pass
- `build`: pass
- Artifact contents: verified for core modules and release docs
- Tunnel / connector: verified against the upgraded 39-tool MCP surface

## Breaking changes

- None known.

## Known limitations

- ChatGPT connector may need a fresh app / connector registration to refresh tool manifests.
- Owner Mode should not be enabled for always-on tunnel mode.
- Direct mutation requires `HERMES_GPT_OPERATOR_APPLY_MODE=direct` plus `dry_run=false` per call.
