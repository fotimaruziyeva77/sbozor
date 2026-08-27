# Stitch eksporti — ajratib olingan dizayn tokenlari va ko'chirish rejasi

> Manba: `stitch.withgoogle.com` loyihasi **SBOZOR Director Dashboard**
> (5 ekran: Dashboard Dark/Light Desktop, Dark Mobile, Printable ×2).
> Kod foydalanuvchi tomonidan eksport qilib berildi, 2026-08-19.

---

## 1. Rang tokenlari (eksportdan AYNAN)

### Quyuq tema

| Rol | Qiymat | Izoh |
|---|---|---|
| Sahifa foni | `#191A1F` | CSS'da MAJBURAN o'rnatilgan (`body{background-color}`), konfigdagi `#121318` ni yengadi |
| Karta foni | `#212228` | |
| Karta chegarasi | `rgba(255,255,255,0.08)` | 1px |
| Karta radiusi | `14px` | soya YO'Q |
| Asosiy (yashil) | `#4edea3` | `primary` |
| Asosiy to'liq | `#10b981` | `primary-container` |
| Ikkilamchi (sariq) | `#ffb95f` | `secondary` |
| Xato (qizil) | `#ffb4ab` | `error` |
| Matn | `#e3e2e9` | `on-surface` |
| Xira matn | `#bbcabf` | `on-surface-variant` |
| Chegara | `#3c4a42` | `outline-variant` |
| Yuza (baland) | `#292a2f` | `surface-container-high` |

### Yorug' tema

| Rol | Qiymat |
|---|---|
| Sahifa foni | `#ffffff` |
| Karta foni | `#ffffff` |
| Karta chegarasi | `#E8E8E6` |
| Karta soyasi | `0 2px 4px rgba(0,0,0,0.04)` |
| Asosiy | `#10b981` |
| Ikkilamchi | `#f59e0b` |
| Xato | `#ef4444` |
| Matn | `#121318` |
| Xira matn | `#6b7280` |

### Sarlavha ostidagi erish qatlami (Stitch'dan tasdiqlangan)

```css
/* quyuq — 9 to'xtash */
linear-gradient(#000 0%, rgba(0,0,0,.82) 10%, rgba(0,0,0,.58) 24%,
  rgba(0,0,0,.25) 36%, rgba(0,0,0,.12) 45%, rgba(0,0,0,.06) 52%,
  rgba(0,0,0,.02) 60%, rgba(0,0,0,0) 70%, rgba(0,0,0,0) 100%)

/* yorug' — 15 to'xtash */
linear-gradient(#fff 0%, rgba(255,255,255,.94) 6%, rgba(255,255,255,.85) 12%,
  rgba(255,255,255,.72) 18%, rgba(255,255,255,.58) 24%, rgba(255,255,255,.45) 30%,
  rgba(255,255,255,.34) 35%, rgba(255,255,255,.24) 40%, rgba(255,255,255,.16) 45%,
  rgba(255,255,255,.1) 50%, rgba(255,255,255,.06) 55%, rgba(255,255,255,.03) 60%,
  rgba(255,255,255,.01) 65%, rgba(255,255,255,0) 70%, rgba(255,255,255,0) 100%)
```

Balandligi `160px`, `position: absolute; top: 0; left/right: 0`, `pointer-events: none`.

---

## 2. Tipografiya shkalasi (Inter)

| Nom | O'lcham | Satr | Harf oralig'i | Og'irlik |
|---|---|---|---|---|
| `hero-stat` | **56px** | 1.1 | −0.02em | 700 |
| `headline-lg-mobile` | 32px | 40px | — | 700 |
| `card-value` | **30px** | 36px | −0.01em | 600 |
| `label-caps` | **13px** | 16px | **+0.08em** | 600 |
| `body-muted` | 14px | 20px | — | 400 |

Barcha raqamlar `font-variant-numeric: tabular-nums`.

## 3. Bo'shliq va radius

```
base 4px · gutter 16px · card-gap 20px · container-padding 24px · section-margin 32px
radius: DEFAULT 4px · lg 8px · xl 12px · karta 14px · full 9999px
```

## 4. Halqa diagrammasi (bosh ko'rsatkich) — aniq matematika

```html
<!-- 96.4% uchun -->
<svg viewBox="0 0 100 100" class="-rotate-90">
  <circle cx="50" cy="50" r="44" fill="none" stroke="#E8E8E6" stroke-width="12"/>
  <circle cx="50" cy="50" r="44" fill="none" stroke="#10b981" stroke-width="12"
          stroke-dasharray="276.46" stroke-dashoffset="9.95" stroke-linecap="round"/>
</svg>
```

`dasharray = 2πr = 2π·44 = 276.46` · `dashoffset = 276.46 × (1 − 0.964) = 9.95`

Kichik halqa (bandlik 72%): `r=40, stroke-width=12, dasharray=251.2, dashoffset=70.3`

## 5. Chop etiladigan varaq

```
.a4-container { width: 794px; min-height: 1123px; padding: 18mm;
                font-size: 11pt; line-height: 1.4; color: #000; background: #fff }
chiziqlar: 1px #CCCCCC · bosh raqam: 64px/1.1 bold · bo'lim sarlavhasi: 9pt uppercase
@media print { -webkit-print-color-adjust: exact }
```

---

## 6. ⛔ KO'CHIRISHDA HAL QILINISHI SHART BO'LGAN TO'RT MASALA

### (a) RANG — eng katta qaror

Stitch **yashil** (`#10b981` / `#4edea3`) tanladi. Bizning tizim **ko'k**
aksentda (`--color-accent`) va u landing, kirish sahifasi, kassir va
nazoratchi yuzalarida ham ishlatiladi.

- Yashilga o'tish = **butun mahsulot kimligini** o'zgartirish
- Faqat direktor panelini yashil qilish = ikki xil mahsulot taassuroti

⛔ Bu **mahsulot qarori**, texnik emas — foydalanuvchi hal qiladi.

### (b) IKONKA — Material Symbols → lucide

Stitch `Material Symbols Outlined` shriftini Google CDN'dan yuklaydi.
Bizda `lucide-react` bor va tashqi so'rov qilmaydi. Mos keluvchilar:

| Stitch | lucide |
|---|---|
| `payments` | `Banknote` |
| `receipt_long` | `ReceiptText` |
| `group` / `point_of_sale` | `Users` / `Wallet` |
| `warning` | `TriangleAlert` |
| `storefront` / `store` | `Store` |
| `document_scanner` / `memory` | `ScanLine` |
| `trending_up` | `TrendingUp` |
| `calendar_month` | `CalendarRange` |
| `dashboard` | `LayoutDashboard` |

### (c) DARVOZALAR — xom ko'chirish bir nechtasini buzadi

| Darvoza | Nima buziladi |
|---|---|
| `text-[` = 0 | Eksportda `text-[22px]`, `text-[13px]`, `text-[10px]` … o'nlab marta |
| `text-base` ≤ 7 | — |
| `@keyframes` yopiq reyestri | `transition-all`, `hover:r-3` va h.k. |
| `.landing-*` transition allowlist | `transition-all` TAQIQ (faqat transform/opacity/rang) |
| G-land-5(d) ixtiyoriy o'lcham | Butun eksport ixtiyoriy qiymatlarda |

⛔ Ya'ni **tokenlarga tarjima qilinadi**, HTML ko'chirilmaydi.

### (d) MAZMUN — mobil ekran boshqa ma'lumot ko'rsatadi

Mobil versiyada bizda **yo'q** ko'rsatkichlar bor: `Naqd pullar / Terminal`
bo'linishi, `Inspektorlar 4 nafar`, `Faol obyektlar 142/150`,
`Band lekin to'lovsiz 48 nuqta` (desktopda 12 rasta), `So'nggi tushumlar`
ro'yxati inspektor ismlari bilan.

Quyuq desktop sarlavhasida ham eski o'ylab topilgan menyu qolgan
(`Sektorlar`, `Tushumlar`, `Inspektorlar`) — yorug' versiyada tuzatilgan.

⛔ Olinadigan ekran — **quyuq desktop (tuzilma) + yorug' desktop (tuzatilgan
menyu)**. Mobil qayta chiziladi: desktopning bir ustunli varianti sifatida.

---

## 7. KO'CHIRISH REJASI (tasdiq kutmoqda)

| # | Ish | Fayl |
|---|---|---|
| 1 | Tipografiya shkalasi `@theme` ga: `--text-hero-stat`, `--text-card-value`, `--text-label-caps` | `globals.css` |
| 2 | Karta anatomiyasi: 14px radius, hairline chegara, soyasiz (quyuq) / yumshoq soya (yorug') | `.dir-tile` |
| 3 | Sarlavha ostidagi **erish qatlami** — ikkala temada | `globals.css` + `app-shell.tsx` |
| 4 | Bosh katakni halqa bilan qayta qurish (aniq SVG matematikasi §4) | `six-tiles.tsx` |
| 5 | Kataklarni **GURUH: PUL / NAZORAT / TREND** ga bo'lish | `six-tiles.tsx` → `kpi-groups.tsx` |
| 6 | Har guruhga `label-caps` sarlavha | " |
| 7 | Ikonkalarni lucide bilan almashtirish (§6b jadvali) | " |
| 8 | Mobil: bir ustun, bosh katak birinchi | " |
| 9 | Chop etiladigan varaqni Stitch tuzilmasiga keltirish | `audit-sheet.tsx` |
| 10 | Barcha darvozalarni yashil holatda ushlab qolish | — |

**Rang bo'yicha qaror kutilmoqda** (§6a): yashilga o'tamizmi yoki ko'k
qoladimi. Qolgan hamma narsa rangdan mustaqil va darhol boshlanishi mumkin.
