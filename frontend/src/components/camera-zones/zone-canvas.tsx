"use client";

import { useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

import { centroid, insertMidpoint } from "@/lib/zone-geometry";
import type { Poly, Pt } from "@/lib/zone-geometry";

/*
 * =============================================================================
 * KADR YUZASI — SOF SVG, CANVAS KUTUBXONASI EMAS (D-05).
 *
 * -----------------------------------------------------------------------
 * QAROR: NEGA SVG — VA UNING CHIQISH YO'LI OCHIQ
 * -----------------------------------------------------------------------
 * 2-faza canvasni O'LCHOV bilan rad etgan (`stall-map.tsx:22-37`): 1000
 * element memo bilan ~4 ms. ⚠ LEKIN O'SHA O'LCHOV BU YERGA TO'LIQ
 * KO'CHMAYDI va farq ochiq yozilishi kerak: u render STATIK bo'lgan holat
 * edi (bir marta chizildi va turdi). Bu yerda esa TEPA SUDRALADI, ya'ni
 * `pointermove` har kadrda qayta render qo'zg'atadi — bu BOSHQA profil va
 * u hali O'LCHANMAGAN.
 *
 * Hal qiluvchi omil — TEST: `vitest` + `jsdom` da canvas YO'Q va
 * Playwright loyihada yo'q (8-fazaga qoldirilgan), ya'ni canvas'ni
 * sinaydigan IKKINCHI YO'L ham yo'q edi. SVG — 0 ta yangi paket.
 *
 * ⚠⚠ CHIQISH YO'LI VA UNING O'LCHOV TETIGI:
 *
 *     60 poligonli fixture'da tepani sudrash — `pointermove`
 *     ishlovchisining 100 harakat bo'yicha O'RTACHASI > 16 ms bo'lsa,
 *     render qatlami Konva'ga almashtiriladi.
 *
 *   Almashish FAQAT SHU FAYLNI o'zgartiradi, chunki geometriya
 *   `lib/zone-geometry.ts` da — sof funksiyalarda — yashaydi va bu fayl
 *   uni faqat CHAQIRADI.
 *   ⚠ Bu UAT BANDI, DARVOZA EMAS: qiymat brauzer va qurilmaga bog'liq,
 *     ya'ni uni CI'da o'lchash yolg'on signal berardi (05-UI-SPEC §6.1).
 *
 * -----------------------------------------------------------------------
 * ⛔ OCHIQLIK DARAXTIDA BU KOMPONENT YO'Q — U RO'YXATNING KO'ZGUSI
 * -----------------------------------------------------------------------
 * Konteyner `aria-hidden="true"`. Butun ochiqlik `zone-list.tsx` da
 * yashaydi (§13.4). Sabab: ikkalasi ham ochiq bo'lsa skrinrider har
 * poligonni IKKI MARTA e'lon qilardi va foydalanuvchi qaysi biri
 * «haqiqiy» ekanini bilmasdi.
 * ⚠ `aria-hidden` faqat OCHIQLIK DARAXTIGA ta'sir qiladi, hodisalarga
 *   emas — sichqonchali foydalanuvchi hech nima yo'qotmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ KADR BAYTLARI: `<image href>` — VA BOSHQA HECH QANDAY YO'L
 * -----------------------------------------------------------------------
 * `href` `GET /api/v1/snapshots/{id}/image` proxysidan olingan sessiya
 * ichidagi vaqtinchalik havola bo'ladi (baytlarni `zone-editor.tsx`
 * oladi — `snapshot-dialog.tsx:441-470` naqshi). Boshqa manba YO'Q,
 * shuning uchun `crossOrigin` ATRIBUTI QO'YILMAYDI: u boshqa manba
 * borligini anglatardi.
 *
 * ⚠ KADRNI RASTR YUZAGA CHIZIB EKSPORT QILADIGAN YO'L BU YERDA
 *   QURILMAYDI (T-05-39). SVG'da bunday yo'l yo'q va bu D-05 ning
 *   QO'SHIMCHA foydasi: rastr yuza bo'lganda kadrni fayl sifatida
 *   olish mumkin bo'lardi va u `audit_read` chegarasini chetlab
 *   o'tardi. ⚠ Taqiqlangan API nomi bu izohda ATAYIN yozilmagan —
 *   03-07 qoidasi: skanerlanadigan faylning izohidagi taqiqlangan token
 *   darvozani o'zi qizartiradi. To'liq sabab rejada va SUMMARY da.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ `frame_width`/`frame_height` PIKSEL O'LCHAMI SIFATIDA
 *      ISHLATILMAYDI
 * -----------------------------------------------------------------------
 * Ular `snapshots.width`/`height`, ya'ni `draft()` ning KICHRAYTIRILGAN
 * dekodi (1280×720 kadr uchun taxminan 320×180). Ulardan olinadigan
 * yagona fakt — NISBAT. Shuning uchun `viewBox` ning kengligi DOIMIY
 * `VIEW_WIDTH` (1000 shartli birlik), balandligi esa NISBATdan
 * hisoblanadi. Koordinatalarni `frame_width` ga ko'paytirish har
 * koordinatada TO'RT BAROBAR xato berardi (05-06 SUMMARY).
 *
 * ⚠ SHU SABABDAN `denormalize()` BU YERDA CHAQIRILMAYDI. U butun
 *   piksellarga yaxlitlaydi va uning YAXLITLASH SHARTI serverning
 *   `_round_half_up()` i bilan juftlashtirilgan — ya'ni u KADR
 *   PIKSELLARI uchun, render birliklari uchun emas. Muharrir
 *   koordinatani umuman yaxlitlamaydi (sabab `camera-zone-queries.ts`
 *   da), yaxlitlash faqat serverda, aniqlash paytida bo'ladi.
 * =============================================================================
 */

/**
 * `viewBox` ning kengligi — SHARTLI BIRLIK, piksel EMAS.
 *
 * Qiymat 1000 tanlandi, chunki u koordinatalarni o'qish oson qiladi
 * (0,318 -> 318) va SVG'da kasrli qiymatlar baribir qo'llab-quvvatlanadi,
 * ya'ni aniqlik yo'qolmaydi.
 */
export const VIEW_WIDTH = 1000;

/**
 * `viewBox` ning balandligi — FAQAT NISBATdan.
 *
 * ⚠ YAXLITLANMAYDI: `viewBox` ning nisbati konteynerning `aspect-ratio`
 *   si bilan AYNAN teng bo'lishi kerak, aks holda `preserveAspectRatio`
 *   «none» bilan kadr sezilmas darajada cho'ziladi va poligonlar rasm
 *   bilan bir necha piksel siljib chizilardi.
 */
export function viewHeight(frameWidth: number, frameHeight: number): number {
  return (VIEW_WIDTH * frameHeight) / frameWidth;
}

/** Normalangan poligon -> `points` atributi. */
export function pointsAttr(poly: Poly, vh: number): string {
  return poly.map(([x, y]) => `${x * VIEW_WIDTH},${y * vh}`).join(" ");
}

/**
 * Ekran koordinatasi -> normalangan (0..1).
 *
 * SOF FUNKSIYA va bu ATAYIN: `getBoundingClientRect()` jsdom'da har doim
 * nol qaytaradi, ya'ni sudrash matematikasini komponent ichida qoldirish
 * uni umuman o'lchanmaydigan qilardi (`stall-map.tsx` ning
 * `readIsDesktop` bilan bir xil qaror).
 *
 * ⚠ NOL KENGLIKDAGI TO'RTBURCHAK — `null`, nol emas: hali joylashtirilmagan
 *   element ustida sudrash boshlanmaydi, lekin `0/0` `NaN` berib,
 *   `clamp01` ni `RangeError` bilan yiqitardi.
 */
export function clientToNormalized(
  rect: { height: number; left: number; top: number; width: number },
  clientX: number,
  clientY: number,
): Pt | null {
  if (rect.width <= 0 || rect.height <= 0) return null;
  return [(clientX - rect.left) / rect.width, (clientY - rect.top) / rect.height];
}

/**
 * Qirra o'rtasidagi ushlagichning joyi — `insertMidpoint` DAN HOSILA.
 *
 * ⚠ FORMULA TAKRORLANMAYDI. Ushlagich AYNAN o'sha nuqtada chiziladi,
 *   qayerga bosilganda tepa qo'yiladi; ikkinchi nusxa ular bir kun
 *   ajralib ketishiga yo'l ochardi.
 *
 * ⚠ `null` — amal RAD ETILGAN (tepalar chegarasi to'lgan). 05-03 ning
 *   havola kontrakti: rad etilgan amal AYNAN o'sha havolani qaytaradi,
 *   ya'ni chegaraga yetgan poligonda ushlagich UMUMAN chizilmaydi va
 *   foydalanuvchi bosib bo'lmaydigan nishonni ko'rmaydi.
 */
export function midpointOf(poly: Poly, edgeIndex: number): Pt | null {
  const next = insertMidpoint(poly, edgeIndex);
  if (next === poly) return null;
  return next[edgeIndex + 1];
}

export type CanvasZone = {
  /** Muharrirdagi lokal identifikator (server `id` si yoki qoralama). */
  id: string;
  /** ⛔ O'zi bilan kesishgan — saqlashni to'sadi (§10.4: punktir + rang). */
  invalid: boolean;
  /** Kadrdagi yorliq: rasta kodi yoki `(rastasiz)`. */
  label: string;
  polygon: Poly;
};

export function ZoneCanvas({
  aspectHeight,
  aspectWidth,
  focusedVertex,
  frameHref,
  onBackgroundPress,
  onInsertMidpoint,
  onMoveVertex,
  onSelectZone,
  preview,
  selectedZoneId,
  zones,
}: {
  /** Kadr NISBATINING maxraji — piksel o'lchami EMAS. */
  aspectHeight: number;
  /** Kadr NISBATINING surati — piksel o'lchami EMAS. */
  aspectWidth: number;
  /** Tanlangan zonadagi fokusdagi tepa — ro'yxat bilan BIR XIL indeks. */
  focusedVertex: number | null;
  /** `GET /api/v1/snapshots/{id}/image` dan olingan vaqtinchalik havola. */
  frameHref: string | null;
  /**
   * Bo'sh joyga bosish — tanlovni bekor qiladi.
   *
   * ⛔ «BOSIB CHIZISH» REJIMI BU FAZADA QURILMAYDI va sabab §13.4 dan
   *    kelib chiqadi: u KLAVIATURA foydalanuvchisiga taklif
   *    QILINMAYDIGAN yo'l, ya'ni ikkinchi (faqat sichqonchali) yaratish
   *    modeli bo'lardi — o'z rejimi, yopish/bekor qilish semantikasi va
   *    `Esc` xulqi bilan. Majburiy yo'l — markazdagi to'rtburchak
   *    (`[+ Yangi zona]`), va u to'liq: rasta amalda to'rtburchak
   *    (§6.5), qolgan shakl esa qirra o'rtasidagi ushlagich bilan
   *    quriladi.
   */
  onBackgroundPress: () => void;
  onInsertMidpoint: (edgeIndex: number) => void;
  onMoveVertex: (index: number, point: Pt) => void;
  onSelectZone: (zoneId: string) => void;
  /** DL-2 ning oldindan ko'rishi — punktir, hali MAVJUD EMAS (§10.5). */
  preview: readonly Poly[];
  selectedZoneId: string | null;
  zones: readonly CanvasZone[];
}) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const vh = viewHeight(aspectWidth, aspectHeight);
  const selected = zones.find((zone) => zone.id === selectedZoneId) ?? null;

  function normalizedFromEvent(event: {
    clientX: number;
    clientY: number;
  }): Pt | null {
    const node = svgRef.current;
    if (node === null) return null;
    return clientToNormalized(
      node.getBoundingClientRect(),
      event.clientX,
      event.clientY,
    );
  }

  /**
   * Tepani sudrash — `setPointerCapture` bilan.
   *
   * ⚠ USHLASH MAJBURIY: usiz kursor tez harakatda SVG'dan chiqib
   *   ketganda `pointermove` boshqa elementga tushardi va tepa
   *   yarim yo'lda «tushib qolardi» — sudrash uzilgani esa faqat
   *   qo'yib yuborilgandan keyin ko'rinardi.
   *
   * ⚠ FAQAT TANLANGAN poligonning tepalari sudraladi (§6.4). Ushlagichlar
   *   ham faqat o'sha poligon uchun chiziladi, ya'ni bu ikkinchi qatlam.
   */
  function beginVertexDrag(event: ReactPointerEvent<SVGCircleElement>): void {
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function dragVertex(
    event: ReactPointerEvent<SVGCircleElement>,
    index: number,
  ): void {
    if (!event.currentTarget.hasPointerCapture?.(event.pointerId)) return;
    const point = normalizedFromEvent(event);
    if (point !== null) onMoveVertex(index, point);
  }

  return (
    /*
     * ⛔ `aria-hidden="true"` — OCHIQLIK DARAXTIDA YO'Q (§13.4).
     *
     * ⚠ KONTEYNERNING NISBATI KADRNIKI BILAN AYNAN TENG va bu ikki
     *   narsani bir vaqtda beradi: (a) `preserveAspectRatio="none"`
     *   bilan cho'zilish YO'Q, chunki nisbatlar teng; (b)
     *   `getBoundingClientRect()` to'g'ridan-to'g'ri normalangan
     *   koordinataga aylanadi — letterbox yo'q, ya'ni sudrash
     *   matematikasida qora chiziqlar uchun tuzatish ham kerak emas.
     *   §6.3 ning `aspect-video` eskizidan farqi shu: qat'iy 16:9
     *   konteynerda 4:3 kadr letterbox olardi va har `pointermove` da
     *   o'sha bo'shliqni hisobdan chiqarish kerak bo'lardi — jimgina
     *   siljish uchun ideal joy.
     */
    <div
      aria-hidden="true"
      className="overflow-hidden rounded-md bg-text"
      style={{ aspectRatio: `${aspectWidth} / ${aspectHeight}` }}
    >
      <svg
        className="block size-full touch-none"
        onPointerDown={onBackgroundPress}
        preserveAspectRatio="none"
        ref={svgRef}
        viewBox={`0 0 ${VIEW_WIDTH} ${vh}`}
      >
        {frameHref === null ? null : (
          /*
           * ⚠ `crossOrigin` QO'YILMAYDI (§14.2) — boshqa manba yo'q va
           *   atribut uning borligini anglatardi.
           */
          <image
            height={vh}
            href={frameHref}
            preserveAspectRatio="none"
            width={VIEW_WIDTH}
            x={0}
            y={0}
          />
        )}

        {/*
         * ⚠ HAR ZONA UCHUN AYNAN BITTA `<polygon>`. §10.5 ikki qatlamli
         *   kontur (qora ostida, oq ustida) taklif qiladi; u bu yerda
         *   `drop-shadow` bilan bajariladi, chunki ikkinchi element
         *   «poligon soni = zona soni» invariantini buzardi va o'sha
         *   invariant «bir zona jimgina chizilmay qoldi» sinfini
         *   ushlaydigan yagona arzon test.
         */}
        {zones.map((zone) => {
          const isSelected = zone.id === selectedZoneId;
          return (
            <polygon
              className={
                zone.invalid
                  ? "[stroke-dasharray:6_3] [filter:drop-shadow(0_0_1px_rgb(0_0_0/0.9))]"
                  : "[filter:drop-shadow(0_0_1px_rgb(0_0_0/0.9))]"
              }
              fill={
                isSelected
                  ? "color-mix(in oklch, var(--color-accent) 25%, transparent)"
                  : "none"
              }
              key={zone.id}
              onPointerDown={(event) => {
                event.stopPropagation();
                onSelectZone(zone.id);
              }}
              points={pointsAttr(zone.polygon, vh)}
              stroke={
                zone.invalid
                  ? "var(--color-danger)"
                  : isSelected
                    ? "var(--color-accent)"
                    : "var(--color-surface)"
              }
              strokeWidth={isSelected ? 3 : 2}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}

        {/*
         * DL-2 oldindan ko'rishi — punktir va `fill: none` (§10.5):
         * punktir «bu HALI MAVJUD EMAS» deydi va rang yagona signal
         * bo'lib qolmaydi.
         */}
        {preview.map((poly, index) => (
          <polyline
            fill="none"
            key={`preview-${index}`}
            points={`${pointsAttr(poly, vh)} ${pointsAttr(poly.slice(0, 1), vh)}`}
            stroke="var(--color-text-muted)"
            strokeDasharray="4 4"
            vectorEffect="non-scaling-stroke"
          />
        ))}

        {/* Yorliqlar — matn konturi bilan (§10.5): har qanday fonda o'qiladi. */}
        {zones.map((zone) => {
          const [cx, cy] = centroid(zone.polygon);
          return (
            <text
              fill="var(--color-bg)"
              fontSize={24}
              key={`label-${zone.id}`}
              paintOrder="stroke"
              stroke="var(--color-text)"
              strokeWidth={3}
              textAnchor="middle"
              x={cx * VIEW_WIDTH}
              y={cy * vh}
            >
              {zone.label}
            </text>
          );
        })}

        {/* Ushlagichlar — FAQAT tanlangan poligonda (§6.4). */}
        {selected === null
          ? null
          : selected.polygon.map((point, index) => {
              const mid = midpointOf(selected.polygon, index);
              return (
                <g key={`handles-${index}`}>
                  {mid === null ? null : (
                    /*
                     * Qirra o'rtasi — shaffof, punktir kontur. `null`
                     * bo'lsa (chegara to'lgan) UMUMAN chizilmaydi:
                     * bosib bo'lmaydigan nishon yolg'on va'da bo'lardi.
                     */
                    <circle
                      cx={mid[0] * VIEW_WIDTH}
                      cy={mid[1] * vh}
                      data-testid="midpoint-handle"
                      fill="transparent"
                      onPointerDown={(event) => {
                        event.stopPropagation();
                        onInsertMidpoint(index);
                      }}
                      r={4}
                      stroke="var(--color-surface)"
                      strokeDasharray="2 2"
                      vectorEffect="non-scaling-stroke"
                    />
                  )}

                  {/*
                   * ⚠ IKKI DOIRA: ko'rinadigani `r=5`, nishoni `r=11`
                   *   (22 px diametr). Bu WCAG 2.5.8 ning 24×24
                   *   minimumiga YETMAYDI va bu ONGLI CHEGIRMA — 44 px
                   *   ushlagichlar qo'shni rastalarda ustma-ust tushib,
                   *   chizishni imkonsiz qilardi.
                   *   ⛔ KOMPENSATSIYA MAJBURIY va u `zone-list.tsx`
                   *      dagi TO'LIQ 44 px tugmalar — ular BIRLAMCHI
                   *      yuza, muqobil emas (§6.4 oxirgi xatboshi).
                   */}
                  <circle
                    cx={point[0] * VIEW_WIDTH}
                    cy={point[1] * vh}
                    data-testid="vertex-target"
                    fill="transparent"
                    onPointerDown={beginVertexDrag}
                    onPointerMove={(event) => dragVertex(event, index)}
                    r={11}
                  />
                  <circle
                    cx={point[0] * VIEW_WIDTH}
                    cy={point[1] * vh}
                    data-testid="vertex-dot"
                    fill="var(--color-surface)"
                    r={5}
                    stroke={
                      focusedVertex === index
                        ? "var(--color-accent)"
                        : "var(--color-text)"
                    }
                    strokeWidth={focusedVertex === index ? 3 : 1}
                    vectorEffect="non-scaling-stroke"
                  />
                </g>
              );
            })}
      </svg>
    </div>
  );
}
