# Oltin to'plam — UXLAB YOTGAN aniqlik darvozasi (W0-9, D-01/D-02)

> ⛔ **BIRINCHI VA ENG MUHIM QOIDA — SINTETIK YOZUVNING `true_verdict` I
> FAQAT GEOMETRIYADAN OLINADI.**
>
> «Bu poligon ichida shu koordinatalarda quti bor» — demak `occupied`.
> **Detektorning javobidan HECH QACHON.** Agar yorliq modelning chiqishidan
> olinsa, to'plam modelni o'zi bilan solishtiradi va aniqlik 100% chiqadi —
> model butunlay noto'g'ri bo'lganda ham. Bu o'zini-o'zi tasdiqlash tuzog'i
> va bu loyiha uni ikki marta rad etgan (2-fazaning shablon-import quvuri,
> 3-fazaning «simulyatordan kadr olib tekshiramiz» taklifi).
>
> Shu sababdan sintetik yozuvlarda `labeled_by = "geometry"`: yorliqni NA
> odam, NA model bergan — u nuqta-poligon munosabatidan **hisoblangan** va
> `image_ref` o'sha munosabatni nomida tashiydi (§S-9: nom FIZIK/GEOMETRIK
> FAKT, verdikt aks-sadosi emas).

---

## Bu papka nima va nima EMAS

Bu papka **fazaning haqiqiy mahsuloti** — aniqlik **raqami** emas, uni
chiqaradigan **mashina** (D-01).

`05-VALIDATION.md` validatsiyani ikki qatlamga bo'ladi va ular
aralashtirilmasligi shart:

| Qatlam | Nima isbotlanadi | Bugun mumkinmi |
|---|---|---|
| **Mexanika** | Zona geometriyasi, agregatsiya, navbat, ko'r auditning xolisligi, billing chegarasi | **Ha, to'liq** |
| **Aniqlik** | RF-DETR ning verdikti qanchalik to'g'ri | **Yo'q** — bu papka bo'sh, darvoza **uxlab yotadi** |

⚠ **Ikkinchi qatlamning yo'qligini birinchisining yashilligi bilan yopish
taqiqlanadi.** Sintetik yozuvlar **mexanikani** o'lchaydi — quvur ishlayaptimi,
hisobot shakli to'g'rimi. Ular **modelni o'lchamaydi** va o'lchay olmaydi ham:
sintetik «kadr» da tanib olinadigan hech narsa yo'q.

---

## Darvoza qanday UYG'ONADI — kod o'zgarmasdan

`scripts/eval-golden-set.py` ichida:

```python
karmana = [row for row in rows if row.source == "karmana"]
if len(karmana) >= MIN_N:
    # aniqlikning Wilson quyi chegarasi THRESHOLD dan past bo'lsa — YIQILADI
```

Ya'ni **bugun** `karmana` yozuvlari `0` ta va skript hisobot chiqaradi,
darvoza qo'ymaydi. **Real kadrlar kelgan kuni** ular manifestga
`source="karmana"` bilan qo'shiladi va darvoza **o'zi qurollanadi**.

Bu `sbozor_core.schema_contract.FINANCIAL_TABLES` ning AYNAN mexanizmi
(«jadval mavjud bo'lsa — konstrayt ham shart»): reyestr bugun bo'sh,
darvoza kelajakda avtomatik yopiladi.

⚠ **Keyin tahrirlanishi kerak bo'lgan harness — harness emas.** Agar
uyg'onish uchun kodni o'zgartirish kerak bo'lsa, va'da hujjatdagi niyat
bo'lib qolardi. Shuning uchun `tests/unit/test_golden_harness.py` bugun
`karmana` sonining `0` ekanini **OCHIQ assert qiladi** — jimgina emas.

---

## Manifest sxemasi (`manifest.jsonl`)

Har satr — bitta yaroqli JSON obyekt. **Aynan olti kalit**; noma'lum kalit
yoki yetishmagan maydon `SystemExit(1)` beradi (jimgina o'tkazib yuborish
YO'Q).

| Kalit | Tur | Ma'nosi |
|---|---|---|
| `image_ref` | `str` | Kadrga havola. Sintetik yozuvda — **geometrik faktni tashiydigan nom** (fayl mavjud emas); `karmana` yozuvda — ombordagi obyekt kaliti |
| `polygon` | `[[x, y], ...]` | Kamera zonasining poligoni, **0..1 normallashgan** koordinatalarda, kamida 3 nuqta |
| `true_verdict` | `"occupied"` \| `"empty"` | HAQIQAT. Sintetikda — geometriyadan; `karmana` da — **nazoratchidan** |
| `source` | `"synthetic"` \| `"karmana"` | Darvozaning uyg'onish tetigi aynan shu maydonda |
| `labeled_by` | `str` | Sintetikda `"geometry"`; `karmana` da yorliqlagan odamning identifikatori |
| `labeled_at` | `str` (ISO sana) | Yorliq qo'yilgan kun |

⚠ **Koordinatalar 0..1 da va bu D-05 ning talabi:** poligon kadr
o'lchamiga bog'lanmaydi, ya'ni kamera almashtirilganda yoki oqim
o'lchami o'zgarganda zona qayta chizilmaydi.

---

## Real kadrlar kelganda — OPERATSION TARTIB

⛔ **`karmana` KADRLARI BU REPOGA QO'YILMAYDI.** Ular shaxsiy ma'lumot
tashiydi (bozordagi odamlarning tasviri) va O'zR qonuni ostida turadi.
Rasmlar `ops/` yo'nalishida, repodan tashqarida saqlanadi; manifestdagi
`image_ref` esa ombordagi obyekt kalitiga ishora qiladi (T-05-03).

Repoga tushadigan yagona narsa — **manifest satrlari**: ular koordinata,
verdikt va yorliqlovchi identifikatoridan iborat, tasvir emas.

Yorliqlash tartibi:

1. Nazoratchi ko'r audit navbatida kadrni ko'radi va verdikt beradi
   (`zone_reviews`) — **AI ning javobini KO'RMAGAN holda** (D-17).
2. O'sha javob manifestga `source="karmana"`, `labeled_by=<nazoratchi>`
   bilan ko'chiriladi.
3. `MIN_N` ta yozuv to'plangan kuni darvoza uyg'onadi.

⚠ **`eval`/`train` 70/30 bo'linishi TORTISH PAYTIDA belgilanadi** (D-14):
audit ma'lumoti o'qitishda ishlatilsa ham hisobot aniqligini shishira
olmasligi kerak. Bo'linish keyin, «qulay» tomonga qarab qilinmaydi.

---

## Ishga tushirish

```bash
python scripts/eval-golden-set.py --manifest tests/fixtures/golden_set/manifest.jsonl
```

Bugungi kutilgan chiqish: manifest yaroqli, `karmana` yozuvlari `0`,
**darvoza uxlayapti** va aniqlik foizi **UMUMAN CHOP ETILMAYDI** — o'lchanmagan
raqamni ko'rsatish uni o'lchangan qilib ko'rsatardi (T-05-04).
