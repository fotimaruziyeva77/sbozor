"""SBOZOR umumiy yadro paketi — uch servis uchun infra primitivlari.

Modullar:

* `enums` — `Role`, `Locale`, `AuditAction`, `AuditSource`, `ActorKind`
* `money` — butun so'm (`Soum`), `MAX_SAFE_SOUM`, formatlash
* `timeutil` — `MARKET_TZ`, `now_tz()`, `business_date()`
* `phone` — E.164 normalizatsiyasi
* `security` — Argon2id parol + JWT chiqarish/tekshirish
* `db` — async engine va sessiya fabrikalari
* `tenancy` — tenant GUC'lari va `TenantScopedRepository`
* `logging` — JSON logging, sir filtri, so'rov konteksti
* `schema_contract` — meta-testlar uchun jadval reyestrlari

Bu paketda BIZNES LOGIKASI yo'q va bo'lmasligi kerak: ORM modellari
(`models`) 01-04 rejasida qo'shiladi, domen qoidalari esa servislarda
yashaydi. Submodullar ATAYIN bu yerdan re-export qilinmaydi — import
yo'li to'liq yozilsa (`from sbozor_core.security import ...`), bog'liqlik
grafi o'qilganda ko'rinib turadi.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
