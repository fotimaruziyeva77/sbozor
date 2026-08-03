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

## Qoida 1 — lotin so'z/akronim hech qachon apostrofli qo'shimcha bilan yozilmaydi

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

**3-faza kengaytmasi — NVR domenining akronimlari** (o'lchandi: 03-UI-SPEC
§0.2, 53 ta nomzod matn):

| uz-Latn | uz-Cyrl (hosila) | |
|---------|------------------|---|
| `NVR'ga ulanmadi` | `НВРъга уланмади` | ❌ override BOR bo'lsa ham buziladi |
| `NVR qurilmasiga ulanib bo'lmadi` | `NVR қурилмасига уланиб бўлмади` | ✅ |
| `NTP'ni yoqing` | `НТПъни ёқинг` | ❌ |
| `NTP xizmatini yoqing` | `NTP хизматини ёқинг` | ✅ |
| `RTSP'ni tekshiring` | `РТСПъни текширинг` | ❌ |
| `RTSP portini tekshiring` | `RTSP портини текширинг` | ✅ |

Qoida bitta jumlada: **akronimdan keyin apostrof emas, SO'Z qo'ying**
(`qurilmasiga`, `xizmatini`, `portini`, `sozlamalarida`).

Bu qoida `gen-cyrillic.test.mjs` da qulflangan: `uz-Latn.json` yoki
`ru.json` ichida apostrofli `Excel'`, `NVR'`, `NTP'`, `RTSP'`, `ISAPI'`,
`VPN'` yoki `GMT'` shakli paydo bo'lsa test qizaradi.

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
`Karmana`, `Navoiy`, `autentifikatsiya` (3-faza).

---

## Qoida 5 — sof kirill chiqish ham NOTO'G'RI bo'lishi mumkin (semantik defekt)

Yuqoridagi qoidalar **ko'rinadigan** defektlar haqida: matnda lotin harfi
yoki tutuq belgisi qolib ketadi va uni skript ushlaydi. **Uchinchi sinf
esa ko'rinmaydi** — chiqish sof kirill bo'ladi, lekin ma'nosi buziladi
(o'lchandi: 03-UI-SPEC §0.2 (3)):

| uz-Latn | uz-Cyrl (hosila) | |
|---------|------------------|---|
| `Asia/Tashkent` | `Асиа/Ташкент` | ❌ IANA identifikatori buzildi |
| `Toshkent` | `Тошкент` | ✅ |
| `autentifikatsiya` (overridesiz) | `аутентификатсия` | ❌ to'g'risi `аутентификация` |
| `autentifikatsiya` (override bilan) | `аутентификация` | ✅ |

Ikkala natijada ham na lotin harfi, na `ъ` bor — ya'ni **mavjud skript
darvozasi ularni ko'rmaydi**. Shuning uchun ikkita qoida:

1. **IANA vaqt mintaqasi identifikatori matnga umuman kiritilmaydi.**
   `Asia/Tashkent` o'rniga shahar nomi — `Toshkent`. (Identifikatorning
   o'zi kerak bo'lsa u DB kontenti yoki texnik qiymat, tarjima matni
   emas.)
2. **`ts` birikmasi bo'lgan har o'zlashma override talab qiladi**
   (`ts` → `ц`, `тс` emas). Lug'atda `protsent`, `protsess`, `litsenziya`,
   `aktsiya` shu sababdan bor; 3-faza `autentifikatsiya` bilan ro'yxatni
   davom ettirdi.

Darvoza: `gen-cyrillic.test.mjs` — buzuq shakllar ro'yxati
(`Асиа`, `аутентификатсия`) va `Asia/` ning tarjima fayllarida
bo'lmasligi. Ikkalasi ham **matn** darajasidagi tekshiruv, chunki
transliteratorni tuzatish bu sinfni yopmaydi.

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
