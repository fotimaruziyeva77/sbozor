---
quick_id: 261108-nen
type: quick
mode: quick (orchestrator inline — rejalash va bajarish bitta kontekstda)
created: 2026-11-08
status: complete
---

# Quick 261108-nen: parking-report tenancy testlari — query filler va `.xlsx` tasnifi

2fdd94c dan beri 3 ta tenancy testi qizil. Commit va deploy FAQAT buyurtmachi aytganda
(`git add -A` taqiq), shuning uchun `gsd-executor` (atomik commit + worktree merge) ishlatilmaydi.

## Kontekst

- `GET /edge-sites/{site_id}/parking-report[.xlsx]` da `from`/`to` MAJBURIY. `call_route()` query
  bermaydi, ya'ni `test_cross_tenant_object_returns_404` 422 da to'xtaydi va tenant chegarasi
  umuman o'lchanmaydi.
- `.xlsx` ning «Mashinalar» varag'ida har seansning avtomobil raqami bor
  (`parking_report.py::_write_sessions_sheet`, `row.plate`) — bayt-shaxsiy ma'lumot, kadrlar bilan
  bir sinf. Marshrutda `CAMERA_VIEW` bor (`ViewerDep`), `audit_read` YO'Q.

## Vazifalar

1. `tests/tenancy/test_cross_tenant.py` — `QUERY_FILLERS` (yaroqli, o'tmishdagi davr) va
   `call_route()` undan `params=` beradi; eskirish darvozasi. `QUERY_PARAM_ROUTES` ga QO'SHILMAYDI:
   u «422 kutilgan» degan istisno, bizga esa aynan 404 kerak.
2. `services/core-api/app/api/v1/edge_sites.py` — `.xlsx` ga `audit_read(edge_events,
   reason="report_parking_export")`; tartib huquq -> niyat -> ma'lumot; niyat hujjatdan oldin.
3. `tests/tenancy/test_personal_data_coverage.py` — `BINARY_PERSONAL_ROUTES` va
   `BINARY_PERSONAL_ALLOWED` (`{CAMERA_VIEW}`).
4. `tests/integration/test_edge.py` — eksport AYNAN bitta audit qatori yozadi, begona bozor (404)
   iz qoldirmaydi: darvoza faqat E'LONni ko'radi, yozuv esa fon vazifasida.

## Tekshiruv

`docker compose ... --profile test run --rm --no-deps tests pytest ...`

⚠ `--no-deps` MAJBURIY: worktree'da `deployment/.env` yo'q va `storage` config-hash ishlab turgan
`sbozor-storage-1` nikidan farq qiladi — compose uni qayta yaratardi.
