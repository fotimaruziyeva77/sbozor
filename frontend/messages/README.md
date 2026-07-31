# Tarjima fayllari — mas'uliyat va copy qoidalari

| Fayl | Kim yozadi | Izoh |
|------|-----------|------|
| `uz-Latn.json` | **Qo'lda — MANBA** | Barcha yangi kalit shu yerdan boshlanadi |
| `ru.json` | **Qo'lda** | Kalitlar `uz-Latn.json` bilan aynan mos bo'lishi shart |
| `uz-Cyrl.json` | **AVTOMATIK** (`npm --prefix frontend run i18n:gen`) | **Qo'l tegizilmaydi** — har tahrir keyingi generatsiyada yo'qoladi |
| `uz-Cyrl.overrides.json` | **Qo'lda** | Transliterator ustidan yozadigan yagona joy |

Darvozalar:

```bash
npm --prefix frontend run i18n:check   # kalit-parity + ICU-parity + drift
npm --prefix frontend test             # transliteratsiya SIFATI (quyidagi qoidalar)
```

> `i18n:check` transliteratsiya **sifatini tekshirmaydi** — u faqat kalitlar
> mos kelishini va `uz-Cyrl.json` generatsiya natijasidan farq qilmasligini
> tekshiradi. Sifat darvozasi — `scripts/gen-cyrillic.test.mjs`.

---

## Qoida 1 — `Excel` hech qachon apostrofli qo'shimcha bilan yozilmaydi

Transliteratorda `Excel` va `xlsx` uchun override bor
(`uz-Cyrl.overrides.json` → `words`), lekin **override apostrofli shaklni
qutqara olmaydi**: `Excel'dan` — bu boshqa token va apostrof `ъ` ga
aylanadi.

O'lchangan natija:

| uz-Latn | uz-Cyrl (hosila) | |
|---------|------------------|---|
| `Excel'dan yuklash` | `Эхcэлъдан юклаш` | ❌ buzuq — ichida lotin `c` qolgan |
| `Excel fayldan yuklash` | `Excel файлдан юклаш` | ✅ |
| `.xlsx fayl` | `.хлсх файл` | ❌ |
| `xlsx fayl` | `xlsx файл` | ✅ |

Shuning uchun matn yozishda:

- ❌ `Excel'dan yuklash` → ✅ **`Excel fayldan yuklash`**
- ❌ `Excel'ga eksport` → ✅ **`Excel faylga eksport`**
- ❌ `.xlsx fayl` → ✅ **`xlsx fayl`**

Bu qoida `gen-cyrillic.test.mjs` da qulflangan: `uz-Latn.json` yoki
`ru.json` ichida apostrofli `Excel'` shakli paydo bo'lsa test qizaradi.

---

## Qoida 2 — o'zbekcha agglyutinativ: har qo'shimchali shakl alohida yozuv

Lug'at **butun so'zni** (token) qidiradi, o'zakni emas. Ya'ni `filtr`
yozuvi `filtrga` ni **qamramaydi**:

| uz-Latn | Overridesiz | Override bilan |
|---------|-------------|----------------|
| `Filtrga` | `Филтрга` ❌ | `Фильтрга` ✅ |
| `Filtrni` | `Филтрни` ❌ | `Фильтрни` ✅ |
| `filtrdan` | `филтрдан` ❌ | `фильтрдан` ✅ |

**Yangi kalit qo'shganda:** agar matnda lug'atdagi so'zning yangi
qo'shimchali shakli bo'lsa, uni `uz-Cyrl.overrides.json` → `words` ga
qo'shing va `npm --prefix frontend test` bilan tekshiring.

Hozir qamralgan o'zaklar: `filtr`, `protsent`, `protsess`, `litsenziya`,
`aktsiya`, `sertifikat`, `terminal`, `Excel`, `xlsx`, `SBOZOR`,
`Karmana`, `Navoiy`.

---

## Qoida 3 — DB kontenti tarjima QILINMAYDI

Zona nomi, toifa nomi, sotuvchi F.I.Sh., bozor nomi, rasta izohi — bular
foydalanuvchi kiritgan matn va ular qanday kiritilgan bo'lsa shunday
ko'rinadi (1-faza D-16). Har bunday joyda kod izohi majburiy.

---

## Qoida 4 — ICU platsholderlari daxlsiz

Transliterator `{count, plural, one {...} other {...}}` strukturasini,
branch nomlarini (`one`, `other`, `few`, `=0`) va `#` belgisini
o'zgartirmaydi — faqat branch **matnini** o'giradi. Bu xulq test bilan
qulflangan.

`overrides.messages` orqali butun xabarni qo'lda yozsangiz, ICU
platsholderlarini **o'zingiz** to'g'ri ko'chirasiz — transliterator u
yerda umuman chaqirilmaydi.
