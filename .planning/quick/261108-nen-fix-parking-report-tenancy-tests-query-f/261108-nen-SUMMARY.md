---
quick_id: 261108-nen
phase: quick
plan: 261108-nen
subsystem: tenancy
tags: [tenancy, personal-data, audit, edge, parking]
status: complete

provides:
  - "`tests/tenancy/test_cross_tenant.py::QUERY_FILLERS` — majburiy query parametrli yo'l-parametr marshrutlari uchun yaroqli qiymatlar; `call_route()` ularni `params=` bilan beradi"
  - "`GET /edge-sites/{site_id}/parking-report.xlsx` — `audit_read(edge_events, reason=report_parking_export)`, huquq `CAMERA_VIEW`"
  - "`/events`, `/parking-summary`, `/parking-report` JSON — `audit_read(edge_events)`; `plate` uchun alohida darvoza (`test_plate_routes_declare_read_audit_and_camera_view`)"

key-files:
  modified:
    - services/core-api/app/api/v1/edge_sites.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_personal_data_coverage.py
    - tests/tenancy/test_route_coverage.py
    - tests/integration/test_edge.py

key-decisions:
  - "`.xlsx` shaxsiy deb tasniflandi: «Mashinalar» varag'ida avtomobil raqami va kirish/chiqish vaqti bor"
  - "`QUERY_PARAM_ROUTES` ga yozilmadi: u «422 kutilgan» istisnosi, bu yerda esa aynan 404 o'lchanadi"
  - "Commit qilinmadi: buyurtmachi sharti (`gsd-executor` atomik commit qilardi, shuning uchun inline bajarildi)"
---

# Quick 261108-nen: natija

| O'lchov | Oldin | Keyin |
|---|---|---|
| Buyurtmachi tanlovi (`-k "parking-report or test_every_binary..."`) | 3 failed, 10 passed | 13 passed |
| `tests/tenancy` + `test_parking_report.py` + `test_edge.py -k "parking or summary"` | — | 945 passed, 3 error |
| O'sha 3 error alohida qayta ishga tushirilganda | — | 3 passed |

3 error test tanasida emas, fixture'ning Postgres'ga ulanishida chiqdi (`host.docker.internal` porti
uzildi) va `parking-report` ga aloqasi yo'q.

Testlar `--no-deps` bilan yugurtirildi: worktree'da `deployment/.env` yo'q va `storage` config-hash
(`2e447aa…`) ishlab turgan `sbozor-storage-1` nikidan (`ede06ab…`) farq qiladi, ya'ni compose uni
qayta yaratgan bo'lardi. Yugurishdan keyin konteyner va uning hash'i o'zgarmagan.

## Davomi: raqam qaytaradigan JSON yuzalar (buyurtmachi tasdig'i bilan)

| Marshrut | `reason` |
|---|---|
| `GET /edge-sites/{id}/events` (xom hodisaning `data` si) | `edge_events_view` |
| `GET /edge-sites/{id}/parking-summary` | `parking_summary` |
| `GET /edge-sites/{id}/parking-report` | `report_parking` |

`plate` `PERSONAL_FIELDS` ga QO'SHILMADI (u yerda `VENDOR_VIEW` talab qilinadi); alohida darvoza
`CAMERA_VIEW` + audit talab qiladi. Darvoza audit qo'shilishidan oldin aynan shu uch marshrutda yiqildi.

| Tekshiruv | Natija |
|---|---|
| `test_personal_data_coverage.py`, `test_route_coverage.py`, `test_camera_route_coverage.py` | 66 passed |
| `test_cross_tenant.py -k edge-sites` | 78 passed |
| `test_edge.py -k "test_plate_surfaces or parking or summary or events or config"` | 9 passed |
| ruff, mypy (o'zgargan fayllar) | toza |

⚠ `parking-summary` panelda 30 soniyada so'raladi (`SITE_POLL_MS`, faqat sahifa ko'rinib turganda),
ya'ni ochiq sahifa soatiga 120 tagacha audit qatori yozadi. `sessions=0` (direktor paneli) ham `regulars`
orqali raqam oladi va audit yozadi.

`/config` dagi `parking.exempt_plates` ga audit qo'yilmadi: bu ro'yxat harakat ma'lumoti emas.
