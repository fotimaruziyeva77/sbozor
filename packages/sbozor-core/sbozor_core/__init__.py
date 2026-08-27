"""SBOZOR umumiy yadro paketi — uch servis uchun infra primitivlari.

Modullar:

* `enums` — `Role`, `Locale`, `AuditAction`, `AuditSource`, `ActorKind`
* `money` — butun so'm (`Soum`), `MAX_SAFE_SOUM`, formatlash
* `occupancy` — kameralararo bandlik agregatsiyasi (AI-05, D-20/D-22)
* `timeutil` — `MARKET_TZ`, `now_tz()`, `business_date()`
* `phone` — E.164 normalizatsiyasi
* `security` — Argon2id parol + JWT chiqarish/tekshirish
* `db` — async engine va sessiya fabrikalari
* `tenancy` — tenant GUC'lari va `TenantScopedRepository`
* `logging` — JSON logging, sir filtri, so'rov konteksti
* `schema_contract` — meta-testlar uchun jadval reyestrlari

CHEGARA — KIRISH-CHIQISH, «BIZNES LOGIKASI» EMAS.

Bu paketda DB ga, HTTP ga, navbatga yoki omborga tegadigan qoida
yashamaydi: servis kodi servislarda qoladi. SOF, bog'liqliksiz domen
ARIFMETIKASI esa shu yerda — `money` (butun so'm semantikasi), `periods`
(`[)` chegara konventsiyasi) va `occupancy` (kameralararo ustuvorlik)
uchalasi ham aynan shunday va uchalasi ham SHU SABABDAN shu yerda: ular
bir nechta servis va faza tomonidan bir xil javob berishi kerak, ya'ni
ikkinchi nusxa tug'ilsa nosozlik ikki xil TO'G'RI raqam bo'lib chiqardi.

Chegarani o'lchash oson: bu paketdagi modul `sqlalchemy`, `fastapi`,
`httpx` yoki `taskiq` ni import qilsa — u noto'g'ri joyda
(`models` istisno: u ORM ta'rifi, qoida emas).

Submodullar ATAYIN bu yerdan re-export qilinmaydi — import yo'li to'liq
yozilsa (`from sbozor_core.security import ...`), bog'liqlik grafi
o'qilganda ko'rinib turadi.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
