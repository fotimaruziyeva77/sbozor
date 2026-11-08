---
quick_id: 261108-o0e
phase: quick
plan: 261108-o0e
subsystem: edge-agent
tags: [parking, tariff, edge, contract, agent]
status: complete

provides:
  - "Kontrakt: `tariff.rules[].steps[] = {up_to_minutes, amount_soum}` (ixtiyoriy, ikki repoda bir xil)"
  - "`sbozor-agent`: `parking.Price` bosqichli narxni hisoblaydi, agent oynasi uni ko'rsatadi (uz/ru)"
  - "`default_doc`: yangi obyektlar uchun 4 000 / 6 000 / 10 000 so'm shkalasi"

key-files:
  modified:
    - services/core-api/app/edge_contract/schemas/config.schema.json
    - services/core-api/app/services/edge_config.py
    - "sbozor-agent: contract/schemas/config.schema.json"
    - "sbozor-agent: internal/config/config.go"
    - "sbozor-agent: internal/parking/tariff.go"
    - "sbozor-agent: internal/parking/parking_test.go"
    - "sbozor-agent: internal/ui/static/app.js"
    - "sbozor-agent: internal/ui/static/i18n.js"
  created:
    - tests/fixtures/edge_contract/valid/config-parking-steps.json
    - tests/fixtures/edge_contract/invalid/config-tariff-step-zero-minutes.json
    - "sbozor-agent: contract/testdata/valid/config-parking-steps.json"
    - "sbozor-agent: contract/testdata/invalid/config-tariff-step-zero-minutes.json"

key-decisions:
  - "Yangi ixtiyoriy maydon: eski sozlamalar o'zgarishsiz ishlaydi, `steps` bo'lsa soatlik maydonlar hisobga olinmaydi"
  - "24 soatdan oshsa hozirgi qoida: har to'liq sutka alohida, qoldiq shkala bo'yicha (25 soat = 14 000)"
  - "15 daqiqa bepul vaqt o'zgarmaydi; yengil va yuk toifasiga bir xil narx"
  - "Agentning `Default()` i o'zgarmadi: u mahalliy namuna, bosqichli qoida faqat paneldan keladi"
---

# Quick 261108-o0e: natija

| Tekshiruv | Natija |
|---|---|
| `go test ./...` (`sbozor-agent`, `golang:1.25-alpine`) | o'tdi, status 0 |
| gofmt (o'zgargan Go fayllar), `go build ./...` | toza |
| `node scripts/i18n-check.mjs`, `node --check` | OK |
| `ruleText` haqiqiy kod bilan (bosqichli, shiftli, eski soatlik, bepul) | to'g'ri matn |
| `test_edge_contract.py` + `test_edge.py -k "config or parking or summary"` | 32 passed |
| ruff, mypy (`edge_config.py`) | toza |
| Sxema va namunalar ikki repoda | aynan bir xil |

## Bajarilmagan (buyurtmachi aytganda)

Commit, agent relizi, deploy va mavjud obyektlarning `edge_configs` i. Tartib: server sxemasi -> agent
relizi -> obyekt sozlamasiga `steps`. Eski agent noma'lum maydonli sozlamani rad etadi; server deploy
bo'lgach yangi obyektlar `steps` bilan yaratiladi, shuning uchun reliz server bilan birga chiqishi kerak.

Agent oynasi haqiqiy brauzerda ko'rilmadi: `ruleText` matni kod darajasida tekshirildi.
