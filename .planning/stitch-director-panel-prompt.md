# Stitch uchun tayyor prompt — SBOZOR direktor boshqaruv paneli

> **Qanday ishlatiladi:** https://stitch.withgoogle.com/ ni oching (Google
> hisobingiz bilan kirasiz), pastdagi ingliz tilidagi matnni to'liq nusxalab
> Stitch'ning kiritish maydoniga qo'ying va yuboring.
>
> **Nega ingliz tilida:** Stitch promptni ingliz tilida eng aniq tushunadi.
> Ekrandagi YOZUVLAR esa o'zbekcha bo'lib qoladi — ular promptda so'zma-so'z
> ko'rsatilgan.
>
> **Fon qiymatlari o'lchangan, taxmin emas:** quyuq rejim ranglari
> `stitch.withgoogle.com` ning o'zidan (`rgb(25,26,31)` + sarlavha ostidagi
> 9 nuqtali erish gradienti), yorug' rejim esa `antigravity.google` dan
> (sof oq, gradientsiz, teksturasiz) — ikkalasi ham Chrome'da
> `getComputedStyle` bilan tekshirilgan.

---

## PROMPT (nusxalang)

```
Design a market administration dashboard for a director. Desktop-first, but it
must also work on a phone. This screen is regularly shown to government
inspectors and city officials, so it must answer their questions at a glance.

PRODUCT CONTEXT
SBOZOR digitizes traditional bazaars in Uzbekistan. Cameras already installed
in the bazaar photograph the stall rows several times a day. The system marks
which stalls were occupied. Cashiers record the daily stall fee (called
"patta"). The dashboard compares the two and reveals stalls that were working
but never paid.

THE ONE QUESTION THE SCREEN MUST ANSWER
"Is the daily stall fee being collected in full from every occupied stall?"

TWO COLOR THEMES — BOTH REQUIRED

Dark theme:
- Page background: flat solid #191A1F. No gradient, no texture, no grid, no
  pattern, no glow, no noise. Completely flat.
- Under the sticky header add a 160px tall fade overlay so scrolling content
  dissolves instead of being cut by a hard edge. Use MANY gradient stops with
  uneven spacing (fast at the start, slow at the end) so no visible banding
  line appears:
  linear-gradient(#000 0%, rgba(0,0,0,.82) 10%, rgba(0,0,0,.58) 24%,
  rgba(0,0,0,.25) 36%, rgba(0,0,0,.12) 45%, rgba(0,0,0,.06) 52%,
  rgba(0,0,0,.02) 60%, rgba(0,0,0,0) 70%, rgba(0,0,0,0) 100%)
- Cards: #212228, 1px border rgba(255,255,255,0.08), radius 14px, no shadow.

Light theme:
- Page background: pure white #FFFFFF. No gradient, no texture, no grid.
  Completely flat.
- Same header fade overlay but in white:
  linear-gradient(#fff 0%, rgba(255,255,255,.94) 6%, rgba(255,255,255,.85) 12%,
  rgba(255,255,255,.72) 18%, rgba(255,255,255,.58) 24%, rgba(255,255,255,.45)
  30%, rgba(255,255,255,.34) 35%, rgba(255,255,255,.24) 40%,
  rgba(255,255,255,.16) 45%, rgba(255,255,255,.1) 50%, rgba(255,255,255,.06)
  55%, rgba(255,255,255,.03) 60%, rgba(255,255,255,.01) 65%,
  rgba(255,255,255,0) 70%, rgba(255,255,255,0) 100%)
- Cards: #FFFFFF, 1px border #E8E8E6, radius 14px, very soft shadow.

NO backdrop blur anywhere. NO animated background. NO particles, no video, no
canvas. The background stays silent; all visual weight belongs to the numbers.

LAYOUT, TOP TO BOTTOM

1. HEADER (sticky)
   Left: market name in small uppercase letter-spaced label
   ("KARMANA TEST BOZORI · DIREKTOR"), below it the page title "Bozor paneli",
   below that a small line: date + "Toshkent vaqti" + a status note.
   Right: a period filter — a segmented control with four buttons
   [Bugun] [Kecha] [7 kun] [30 kun], plus a date-range field with a calendar
   icon showing two dates separated by an em dash. "Bugun" is selected by
   default. Selected button uses the accent color.

2. HERO METRIC — full width, taller than the other cards
   Title: "Patta yig'ilish darajasi"
   A large circular progress ring (donut) on the left showing a percentage in
   very large numerals in its center, e.g. "96.4%". To the right of the ring,
   stacked:
     - a status pill: green "To'liq yig'ilmoqda" (>=95%), amber "Bo'shliq bor"
       (85-95%), red "Jiddiy bo'shliq" (<85%)
     - two figures side by side with small labels above them:
       "Yig'ilgan" 24 180 000 so'm   ·   "Hisoblangan" 25 080 000 so'm
     - one more line in muted color: "Yig'ilmagan: 900 000 so'm"
   Bottom-right of the card: a subtle text link "Kunlar kesimi →".
   Numbers use tabular figures and thin space as the thousands separator
   (24 180 000, never 24,180,000).

3. THREE GROUPS OF CARDS, each with a small uppercase group heading above it

   GROUP "PUL" (money) — 3 cards in a row:
   - "Tushum" — big number in so'm, below it a small green or red delta pill
     ("↑ +12.4%") with muted text "o'tgan hafta shu kuniga nisbatan"
   - "Qarz jami" — big number in so'm, below it "14 sotuvchi" and
     "eng eski qarz: 12-avgust"
   - "Kassirlar" — "4 / 5 smena yopilgan", below it the cash variance with a
     sign that carries meaning: "−12 000 so'm" in red, "+8 000" in amber,
     "0" in green. Never show it as an absolute value.

   GROUP "NAZORAT" (oversight) — 3 cards in a row:
   - "Band, lekin to'lovsiz" — a count in very large numerals with the unit
     "rasta" beside it, then the expected amount in so'm below, then a delta
     pill. This card is the product's core value: give it an amber accent.
   - "Bandlik" — a donut showing occupied vs empty, with
     "215 band · 85 bo'sh" underneath
   - "AI aniqligi" — a percentage with a small note "so'nggi 30 kun,
     nazoratchi tekshiruvi bo'yicha"

   GROUP "TREND" — full width:
   - A line chart of daily revenue. Range tabs in the card header:
     [7 kun] [30 kun] [12 hafta] [12 oy]. Y axis on the left with 4 gridlines,
     x axis labels below. The last segment, if the period is not finished, is
     drawn as a DASHED line ending in a hollow dot, and its axis label is
     amber — because that day is still incomplete.

4. FOOTER LINE, muted, centered:
   "Panelning har bir soni ikki bosishda dalilga olib boradi: katak →
   kun/rasta kesimi → to'lov yozuvi, kamera kadri va audit jurnali."

CARD ANATOMY (identical for every card)
Top row: metric label on the left, a small index number in a circle on the
right. Below: the value. Below that: the supporting line. Bottom of the card:
a muted "Yangilandi: 14:20" timestamp on the left and an action link with an
arrow on the right. Cards are clickable in full.

ICONS
Use thin line icons (1.75px stroke), one per card, in the muted text color —
not colored, not filled. Suggested: banknote for revenue, receipt for debt,
users for cashiers, alert-triangle for unpaid, store for occupancy, scan-line
for AI accuracy, trending-up for the trend.

COLOR MEANING — MUST BE CONSISTENT
Green = collected in full / no problem.
Amber = needs attention, incomplete, or "still being counted".
Red = money missing / action required.
Color is NEVER the only signal: every colored state also carries an icon AND
a text label, so it reads without color.

HONESTY RULES — THESE ARE MANDATORY
- If the day's charges have not been computed yet, the hero percentage must
  NOT show 0% or 100%. Show a dash and the sentence "Bugungi patta hisobi
  hali yakunlanmagan — daraja kun yopilgach aniq bo'ladi."
- When the selected period includes today, the header shows
  "kun tugamagan, raqamlar oshib boradi".
- Never invent a metric that has no data. An empty state says what is missing
  and what will fill it.

TYPOGRAPHY
Hero percentage: ~56px bold. Card values: ~30px semibold. Card labels: 13px
uppercase, letter-spacing 0.08em, muted. Supporting lines: 14px muted.
All numbers use tabular figures so columns do not jitter.

RESPONSIVE
Below 1180px: two cards per row. Below 760px: one card per row, hero ring and
its figures stack vertically, the period filter wraps to its own line and the
four quick buttons stay on one row. Every tap target at least 44px tall.

TONE
Calm, precise, institutional. This is a government-facing accountability
screen, not a consumer analytics product. No decorative illustrations, no
gradients on cards, no glassmorphism.
```

---

## Prompt qaysi talablardan qurilgan

| Sizning talabingiz | Promptda qayerda |
|---|---|
| Bugungi real vaqtdagi ma'lumot + filtr (kecha, kalendar oralig'i) | HEADER bo'limi — segmentli tugmalar + sana oralig'i |
| «Hokim/prezidentga ko'rsatiladi, bir qarashda javob olsin» | HERO METRIC — yig'ilish darajasi butun kenglikda, birinchi |
| «Statistikalar aniq va chiroyli» | Guruhlar: PUL · NAZORAT · TREND; har kartada bir xil anatomiya |
| «Psixologik yordam beradigan ikonka va ranglar» | COLOR MEANING — yashil/sariq/qizil ma'nosi qat'iy, rang yolg'iz signal emas |
| «Soatday ishlashi kerak» | Har kartada `Yangilandi: HH:MM`, tugamagan davr uchun uzuq chiziq |
| Quyuq fon — Stitch'niki | Dark theme: `#191A1F` + 9 nuqtali erish gradienti (o'lchangan) |
| Yorug' fon — Antigravity'niki | Light theme: sof oq, gradientsiz, teksturasiz (o'lchangan) |

## Nima ATAYIN taqiqlangan (va nega)

- **Blur, zarrachalar, video, animatsion fon** — Antigravity 10.3 MB, WebGL
  ishlatadi; Karmana sharoitida (arzon telefon, sekin internet) bu ishlamaydi.
  Stitch esa umuman ishlatmaydi va u to'g'ri qaror.
- **Soxta foiz** — hisoblangan patta nol bo'lsa 0% yoki 100% chizish hokimga
  ko'rsatiladigan ekranda eng qimmat xato bo'lardi.
- **`abs()` bilan farq** — kassir kamomadi bilan ortiqchasi bir xil
  ko'rsatilsa, ortiqcha naqdni jimgina yutish kamomadni yashirish bilan teng.
