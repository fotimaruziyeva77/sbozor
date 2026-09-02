"use client";

/*
 * =============================================================================
 * PUL OQIMI CHIZIG'I — gero katagining o'ng yarmi.
 *
 * ⛔⛔ NEGA QO'SHILDI (260902, jonli panelda o'lchandi). Gero katakning
 *     o'ng yarmi BUTUNLAY bo'sh edi: chapda halqa, o'ngda ikki raqam va
 *     ekranning eng qimmatli joyi ishlatilmasdan qolardi. Direktor esa
 *     panelga «pul qanday oqyapti?» degan savol bilan qaraydi — javob
 *     shaklda bo'lishi kerak, raqamda emas.
 *
 * ⚠ BU YERDA KUTUBXONA YO'Q va bu ONGLI: `recharts` ~90 KB gzip va u
 *   butun sahifaning birinchi bo'yalish vaqtini surardi. Kerak bo'lgan
 *   narsa — bitta silliq egri va gradient; ular SVG'da o'ttiz qatorga
 *   sig'adi.
 * =============================================================================
 */

/** Bitta nuqta — sana yorlig'i va qiymat. */
export type FlowPoint = { label: string; value: number };

const VIEW_W = 560;
const VIEW_H = 150;
const PAD_TOP = 14;
const PAD_BOTTOM = 22;

/**
 * Catmull-Rom → kubik Bezier: nuqtalar orasidan SILLIQ egri o'tkazadi.
 *
 * ⛔ SINIQ CHIZIQ EMAS — va farq ma'noda. Kunlik tushum tabiatan
 *    tebranadi; siniq chiziq har tebranishni «hodisa» qilib ko'rsatadi va
 *    ko'z shovqinni tendensiya deb o'qiydi. Silliq egri esa yo'nalishni
 *    beradi, aniq qiymat esa yorliqda turadi.
 *
 * ⚠ TARANGLIK 0.5 (standart Catmull-Rom): kattaroq qiymat egrini
 *   nuqtalardan TASHQARIGA chiqaradi va grafik bo'lmagan qiymatni
 *   ko'rsatib qo'yardi — moliyaviy panelda bu yolg'on.
 */
function smoothPath(pts: readonly { x: number; y: number }[]): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;

  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i += 1) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;

    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;

    d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }
  return d;
}

export function FlowSpark({
  points,
  gradientId = "dirFlowFill",
}: {
  points: readonly FlowPoint[];
  /** Bir sahifada ikkita grafik bo'lsa gradient id'lari TO'QNASHMASIN. */
  gradientId?: string;
}) {
  if (points.length < 2) return null;

  const max = Math.max(...points.map((p) => p.value), 1);
  const stepX = VIEW_W / (points.length - 1);
  const usableH = VIEW_H - PAD_TOP - PAD_BOTTOM;

  const coords = points.map((p, i) => ({
    x: i * stepX,
    y: PAD_TOP + usableH * (1 - p.value / max),
  }));

  const line = smoothPath(coords);
  const area = `${line} L ${VIEW_W} ${VIEW_H - PAD_BOTTOM} L 0 ${VIEW_H - PAD_BOTTOM} Z`;

  return (
    <svg
      aria-hidden="true"
      className="dir-flow-svg"
      preserveAspectRatio="none"
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
    >
      <defs>
        {/*
         * ⚠ GRADIENT TOKENDAN OLINADI, literal rangdan EMAS: tun
         *   rejimida aksent boshqa qiymat oladi va literal rang o'sha
         *   yerda fonga singib ketardi.
         */}
        <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
          <stop
            offset="0%"
            stopColor="var(--color-accent)"
            stopOpacity="0.34"
          />
          <stop
            offset="100%"
            stopColor="var(--color-accent)"
            stopOpacity="0.02"
          />
        </linearGradient>
      </defs>

      <path d={area} fill={`url(#${gradientId})`} />
      <path
        className="dir-flow-line"
        d={line}
        fill="none"
        stroke="var(--color-accent)"
        strokeLinecap="round"
        strokeWidth="2.5"
        vectorEffect="non-scaling-stroke"
      />

      {/*
       * ⛔ OXIRGI NUQTA URG'ULANADI: «bugun qayerdamiz» — direktorning
       *    birinchi savoli. Qolgan nuqtalar mayda, chunki ular yo'lni
       *    ko'rsatadi, to'xtash joyini emas.
       */}
      {coords.map((c, i) => (
        <circle
          cx={c.x}
          cy={c.y}
          fill="var(--color-accent)"
          key={points[i].label + String(i)}
          r={i === coords.length - 1 ? 4 : 2.5}
          stroke="var(--color-surface)"
          strokeWidth={i === coords.length - 1 ? 2 : 0}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
