"""core-api xavfsizlik qatlami — RBAC, tokenlar, rate-limit, app-audit.

Bu paket `sbozor_core.security` (parol + JWT primitivlari) USTIDA turadi va
unga HTTP kontekstini qo'shadi: cookie atributlari, Valkey sanagichlari,
`audit_log` ga app-qatlam yozuvi va kodda qat'iy rol-huquq matritsasi.

Kriptografiya bu yerda YOZILMAYDI — u `sbozor_core.security` da, u ham
faqat `pwdlib` va `PyJWT` ni chaqiradi.
"""
