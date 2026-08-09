"use client";

import { Copy, Plus, Redo2, Rows3, Undo2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { MAX_ZONES_PER_CAMERA } from "@/lib/zone-geometry";

/*
 * =============================================================================
 * ASBOBLAR QATORI — BESH TUGMA, VA UCHALASI HAM SOF GEOMETRIYA.
 *
 * ⛔ HAMMASI `secondary`. Sahifada AKSENT FONLI TUGMA FAQAT BITTA —
 *    `[Zonalarni saqlash]` (§10.3 №6). Asboblardan birortasini aksent
 *    qilish ko'zni saqlashdan chalg'itardi va «bosish kerak bo'lgan
 *    tugma» degan yolg'on ierarxiya yasardi.
 *
 * ⛔ `disabled` ATRIBUTI ISHLATILMAYDI, `aria-disabled` ishlatiladi
 *    (§13.3): `disabled` tugma fokus olmaydi va skrinrider uni umuman
 *    o'qimaydi — «nega bosilmayapti?» savoli javobsiz qolardi. Bosilganda
 *    SABAB e'lon qilinadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ BU YERDA QURILMAYDIGAN TUGMA — VA SABAB TEXNIK EMAS, MANTIQIY
 * -----------------------------------------------------------------------
 * «Tizim topgan qutilarni zona qilish» tugmasi YO'Q va u qo'shilmaydi:
 * bu AYLANMA MANTIQ bo'lardi. Detektorning xatosi zona geometriyasiga
 * aylanardi, keyin o'sha geometriya bo'yicha o'sha detektor baholanardi
 * va aniqlik SOXTA ko'tarilardi — ya'ni AI-04 ning butun maqsadi yo'q
 * bo'lardi (§6.7, §16.2).
 *
 * Shuning uchun uchala yordamchi ham SOF GEOMETRIYA va birortasi
 * kadrga qaramaydi: qator bo'yicha bo'lish — chiziqli interpolyatsiya,
 * nusxalash — siljitish, qisman qamrov esa umuman amal emas (u qonuniy
 * HOLAT).
 * =============================================================================
 */

export function ZoneToolbar({
  canCopy,
  canRedo,
  canRowSplit,
  canUndo,
  onAnnounce,
  onCopyZone,
  onCreateZone,
  onOpenRowSplit,
  onRedo,
  onUndo,
  zoneCount,
}: {
  canCopy: boolean;
  canRedo: boolean;
  /** DL-2 uchun AYNAN ikki zona tanlangan bo'lishi kerak (§6.7). */
  canRowSplit: boolean;
  canUndo: boolean;
  onAnnounce: (message: string) => void;
  onCopyZone: () => void;
  onCreateZone: () => void;
  onOpenRowSplit: () => void;
  onRedo: () => void;
  onUndo: () => void;
  zoneCount: number;
}) {
  const t = useTranslations();
  const atLimit = zoneCount >= MAX_ZONES_PER_CAMERA;

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        aria-disabled={atLimit ? true : undefined}
        className={atLimit ? "opacity-60" : undefined}
        onClick={() => {
          if (atLimit) {
            onAnnounce(t("cameraZones.maxZones", { max: MAX_ZONES_PER_CAMERA }));
            return;
          }
          onCreateZone();
        }}
        size="sm"
        variant="secondary"
      >
        <Plus aria-hidden="true" />
        {t("cameraZones.newZone")}
      </Button>

      <Button
        aria-disabled={canRowSplit ? undefined : true}
        className={canRowSplit ? undefined : "opacity-60"}
        onClick={() => {
          if (!canRowSplit) {
            onAnnounce(t("cameraZones.rowNeedsTwo"));
            return;
          }
          onOpenRowSplit();
        }}
        size="sm"
        variant="secondary"
      >
        <Rows3 aria-hidden="true" />
        {t("cameraZones.rowSplit")}
      </Button>

      <Button
        aria-disabled={canCopy ? undefined : true}
        className={canCopy ? undefined : "opacity-60"}
        onClick={() => {
          if (!canCopy) {
            onAnnounce(t("cameraZones.copyNeedsOne"));
            return;
          }
          onCopyZone();
        }}
        size="sm"
        variant="secondary"
      >
        <Copy aria-hidden="true" />
        {t("cameraZones.copyZone")}
      </Button>

      <Button
        aria-disabled={canUndo ? undefined : true}
        className={canUndo ? undefined : "opacity-60"}
        onClick={onUndo}
        size="sm"
        variant="secondary"
      >
        <Undo2 aria-hidden="true" />
        {t("cameraZones.undo")}
      </Button>

      <Button
        aria-disabled={canRedo ? undefined : true}
        className={canRedo ? undefined : "opacity-60"}
        onClick={onRedo}
        size="sm"
        variant="secondary"
      >
        <Redo2 aria-hidden="true" />
        {t("cameraZones.redo")}
      </Button>
    </div>
  );
}
