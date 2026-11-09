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

## Deploy (2026-11-08)

Server `a55503f` da, faqat `core-api` qayta qurildi (`worker`/`scheduler` eski holatda: ularni qurish boshqa
commit'larni ham chiqarardi). Orqaga qaytish nuqtasi: `8755bb5`.

Agent `1.0.30` (`sbozor-agent` `3d10c9a`, tarmoq `claude/agent-1.0.30`) imzolandi va `pilot` + `stable` ga chiqdi.
Sinov obyekti `parking-c951e998be`: agent `1.0.30`, sozlama `v4` qo'llandi, oyna matni haqiqiy sahifada tekshirildi.
Bir martalik skript `PUT /config` yo'lini takrorlaydi; `first_hour_soum`/`next_hour_soum` ataylab qoldirildi
(agent `1.0.29` ga qaytsa mashina bepul chiqmasin). Buyurtmachi «hammasini o'zing qil» dedi, shuning uchun README'dagi
bir kunlik pilot kuzatuvi qisqardi.

## Karmana (2026-11-09)

Buyurtmachi agentni tugma bilan `1.0.30` ga o'tkazdi (09:31). `parking-5f2939163c` `v13` 10:19 da yozildi: agent qabul qildi
(`core.config.applied`), kamera oqimlari qayta ochilmadi (`streamSig` tarifni o'z ichiga olmaydi).

Shu kuni ikkala kamera raqam oqimini uzgan: `alertStream` ga ulanish 0,02 s da javobsiz EOF, `deviceInfo` esa 200. Kirish 08:20 da,
hali `1.0.29` da to'xtagan; `1.0.30` da kamera kodi o'zgarmagan. Kameralar Reboot qilingach (10:12) oqim bir daqiqada tiklandi.
Tiqilish sababi isbotlanmagan (ehtimol HikCentral yoki kameradagi eski sessiya).

⚠ `v13` agent yangilanishidan KEYIN yozilishi shart edi. Avval «`1.0.29` rad etadi» deb yozilgan edi, bu xato:
`applyServerConfig` sxemani struct'dan qayta yig'ilgan hujjat ustida tekshiradi, ya'ni eski agent `steps` ni jimgina tashlab, `v13` ni
o'zida saqlab qolardi va yangilangach uni qayta olmasdi (kod o'qildi, sinov yakunlanmadi).

Agent oynasi sinov obyektida haqiqiy sahifada tekshirildi.
