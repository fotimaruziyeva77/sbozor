---
phase: 1
slug: poydevor-va-tenant-xavfsizligi
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 + testcontainers 4.15.0 (real postgres:18.4) |
| **Config file** | none — Wave 0 installs (services/core-api/pyproject.toml) |
| **Quick run command** | `{quick command — planner fills from Wave 0}` |
| **Full suite command** | `{full command — planner fills from Wave 0}` |
| **Estimated runtime** | ~{N} seconds |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `{full suite command}`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** {N} seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {planner fills from PLAN.md tasks} | | | FOUND-01..05 | | | | | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test infrastructure does not exist yet (greenfield) — Wave 0 must install pytest + testcontainers and RLS meta-test fixtures per RESEARCH.md "Validation Architecture"
- [ ] `tests/conftest.py` — testcontainers postgres:18.4 fixture connecting as non-superuser `sbozor_app` role (NOT postgres — RLS tests are falsely green under superuser)
- [ ] RLS meta-test: assert `NOT rolsuper AND NOT rolbypassrls` for app role

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Til almashtirgich to'liq tarjimada qoladi | FOUND-04 | No frontend test framework in locked stack (Playwright deferred to Phase 8) | `tsc --noEmit` + `next build` + message-parity script + human click-through uz-Latn ↔ uz-Cyrl ↔ ru |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < {N}s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
