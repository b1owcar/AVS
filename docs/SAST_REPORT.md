# SAST Report — Post Phase 5

**Tool**: Bandit 1.9.x  
**Scope**: `backend/app`  
**Date**: 2026-10-13  
**Trigger**: User request — run SAST after Phase 5  

## Summary

| Severity | Count |
|----------|------:|
| High | 0 |
| Medium | 1 |
| Low | 27 |

**Verdict**: No high-severity findings. Medium finding is a **false positive** (string check for bind warning, not an actual bind). Lows are expected for a local workstation that shells out to FFmpeg / isolated workers with `shell=False`.

## Medium

| ID | Location | Assessment |
|----|----------|------------|
| B104 | `core/config.py` `remote_bind_warning` | False positive. Code detects `0.0.0.0` / `::` to **emit a warning**; default bind remains `127.0.0.1`. |

## Low (accepted / mitigated)

| Theme | IDs | Mitigation |
|-------|-----|------------|
| `subprocess` import / call | B404, B603 | Used with argument lists (`shell=False`) for FFmpeg and env workers. Paths go through upload/path safety where user-controlled. |
| `assert` after tool probe | B101 | Local invariants after `_require_tools()`; not security gates for production web multi-tenant. |
| `try/except/pass` | B110 | Optional CUDA / attention slicing best-effort. |
| Partial executable path | B607 | `ffmpeg` / `ffprobe` resolved via PATH after availability check. |

## Out of scope / residual risk

- ComfyUI and warm workers bind localhost by default scripts; LAN bind is operator choice (`LAVS_HOST`).
- No authentication — intentional for local workstation; do not expose beyond trusted LAN without auth.
- Model weight download is user-triggered (`LAVS_ALLOW_MODEL_DOWNLOAD`).

## Re-run

```bash
source .venv/bin/activate
bandit -r backend/app -f txt
```
