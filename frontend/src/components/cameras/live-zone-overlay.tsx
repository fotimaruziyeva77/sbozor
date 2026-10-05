"use client";

/**
 * JONLI KADR USTIDAGI RASTA RAQAMLARI (261005, foydalanuvchi talabi).
 *
 * =============================================================================
 * ⛔⛔ NEGA BU KERAK: kadrda o'nlab rasta ko'rinadi va ularning hammasi
 *     bir-biriga o'xshaydi. Nizo chiqqanda operator «bu qaysi rasta?»
 *     degan savolga kadrning O'ZIDAN javob bera olmasdi — u zona
 *     muharririni ochib, ko'pburchaklarni solishtirib chiqishi kerak
 *     edi. Raqam kadr ustida tursa, javob bir qarashda ko'rinadi.
 *
 * ⛔ YANGI MA'LUMOT SO'RALMAYDI: zonalar (`camera_zones`) allaqachon
 *    ko'pburchak + RASTA KODI bilan saqlanadi va `useCameraZones` ularni
 *    beradi. Bu qoplama faqat chizadi.
 *
 * ⛔ KOORDINATA MATEMATIKASI TAKRORLANMAYDI: `VIEW_WIDTH`, `viewHeight`
 *    va `pointsAttr` — `zone-canvas.tsx` dagi AYNI funksiyalar. Ikkinchi
 *    nusxa yozilsa, muharrirda chizilgan zona bilan jonli kadrdagi zona
 *    bir kun bir necha piksel siljib ketardi va qaysi biri rost ekani
 *    aniqlanmasdi.
 * =============================================================================
 */
import { useTranslations } from "next-intl";

import {
  pointsAttr,
  VIEW_WIDTH,
  viewHeight,
} from "@/components/camera-zones/zone-canvas";
import { useCameraZones } from "@/lib/camera-zone-queries";
import { centroidOf } from "@/lib/zone-geometry";

/**
 * Kadr nisbati — `live-view-dialog.tsx` dagi `aspect-video` BILAN BIR XIL.
 *
 * ⚠ `viewBox` nisbati konteynerning `aspect-ratio` si bilan AYNAN teng
 *   bo'lishi SHART (`zone-canvas.viewHeight` izohi): `preserveAspectRatio
 *   ="none"` da farq poligonlarni rasmdan siljitib chizardi.
 */
const ASPECT_W = 16;
const ASPECT_H = 9;

export function LiveZoneOverlay({
  cameraId,
  enabled,
}: {
  cameraId: string;
  /** Oqim ko'rinayotgandagina so'raladi — bo'sh oynada trafik sarflanmasin. */
  enabled: boolean;
}) {
  const t = useTranslations();
  const zones = useCameraZones(cameraId, { enabled });

  const items = zones.data?.items ?? [];
  if (items.length === 0) return null;

  const vh = viewHeight(ASPECT_W, ASPECT_H);

  return (
    <svg
      /*
       * ⛔ `pointer-events-none` — qoplama pleyerning boshqaruvlarini
       *    TO'SMAYDI. Usiz kadr ustiga bosish zonaga tushib, video
       *    boshqaruvi ishlamay qolardi.
       */
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-10 size-full"
      preserveAspectRatio="none"
      viewBox={`0 0 ${VIEW_WIDTH} ${vh}`}
    >
      {items.map((zone) => {
        const markaz = centroidOf(zone.polygon);
        return (
          <g key={zone.id}>
            {/*
              ⚠ TO'LDIRISH JUDA SHAFFOF (8%): zona rastani KO'RSATISH
                uchun emas, CHEGARASINI aytish uchun chiziladi. Quyuq
                to'ldirish kadrning o'zini — ya'ni dalilni — berkitardi.
            */}
            <polygon
              className="fill-accent/8 stroke-accent"
              points={pointsAttr(zone.polygon, vh)}
              strokeWidth={2}
            />
            {markaz === null ? null : (
              <g>
                {/*
                  ⛔ YORLIQ ORQASIDA QORA PLASHKA: bozor kadri oq-qora
                     ham, rang-barang ham bo'lishi mumkin va bitta
                     matn rangi ikkalasida ham o'qilmasdi. Plashka
                     kontrastni kadrdan MUSTAQIL qiladi.
                */}
                <rect
                  className="fill-black/70"
                  height={26}
                  rx={4}
                  width={Math.max(28, zone.stall_code.length * 12 + 12)}
                  x={markaz[0] * VIEW_WIDTH - Math.max(28, zone.stall_code.length * 12 + 12) / 2}
                  y={markaz[1] * vh - 13}
                />
                <text
                  className="fill-white"
                  dominantBaseline="middle"
                  fontSize={16}
                  fontWeight={600}
                  textAnchor="middle"
                  x={markaz[0] * VIEW_WIDTH}
                  y={markaz[1] * vh}
                >
                  {zone.stall_code}
                </text>
              </g>
            )}
          </g>
        );
      })}
      <title>{t("cameras.zoneOverlayTitle", { count: items.length })}</title>
    </svg>
  );
}
