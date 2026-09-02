"use client";

import { Copy, Plus, Redo2, Rows3, Trash2, Undo2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { MAX_ZONES_PER_CAMERA } from "@/lib/zone-geometry";

/*
 * =============================================================================
 * ASBOBLAR QATORI — OLTI TUGMA, VA UCHALA YORDAMCHI HAM SOF GEOMETRIYA.
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
  canDelete,
  canRedo,
  canRowSplit,
  canUndo,
  onAnnounce,
  onCopyZone,
  onCreateZone,
  onDeleteZone,
  onOpenRowSplit,
  onRedo,
  onUndo,
  zoneCount,
}: {
  canCopy: boolean;
  /** O'chirish uchun ham AYNAN bitta zona tanlangan bo'lishi kerak. */
  canDelete: boolean;
  canRedo: boolean;
  /** DL-2 uchun AYNAN ikki zona tanlangan bo'lishi kerak (§6.7). */
  canRowSplit: boolean;
  canUndo: boolean;
  onAnnounce: (message: string) => void;
  onCopyZone: () => void;
  onCreateZone: () => void;
  onDeleteZone: () => void;
  onOpenRowSplit: () => void;
  onRedo: () => void;
  onUndo: () => void;
  zoneCount: number;
}) {
  const t = useTranslations();
  const atLimit = zoneCount >= MAX_ZONES_PER_CAMERA;

  /*
   * ⛔⛔ SABAB KO'RINADIGAN BO'LDI (260820, jonli ko'rildi).
   *
   *     Tugmalar `aria-disabled` bilan o'chiriladi va bosilganda sabab
   *     `onAnnounce` ga uzatiladi — lekin u `sr-only role="status"` ga
   *     tushadi, ya'ni FAQAT SKRINRIDER eshitadi. Ko'zi ko'radigan
   *     foydalanuvchi kulrang «Qator bo'yicha bo'lish» ni bosadi va
   *     HECH NARSA bo'lmaydi: na harakat, na sabab.
   *
   *     Endi shart tugmalar ostida, DOIMIY qatorda turadi — ya'ni u
   *     bosishdan OLDIN o'rgatadi, bosgandan keyin ayblamaydi.
   *
   * ⚠ `onAnnounce` OLIB TASHLANMAYDI: skrinrider uchun bosishga
   *   javob berish baribir kerak — ko'rinadigan qator uni almashtirmaydi.
   */
  const hint = !canCopy
    ? t("cameraZones.copyNeedsOne")
    : !canRowSplit
      ? t("cameraZones.rowNeedsTwo")
      : null;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <Button
          aria-disabled={atLimit ? true : undefined}
          className={atLimit ? "opacity-60" : undefined}
          onClick={() => {
            if (atLimit) {
              onAnnounce(
                t("cameraZones.maxZones", { max: MAX_ZONES_PER_CAMERA }),
              );
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

        {/*
         * ⛔⛔ O'CHIRISH SHU YERDA BO'LISHI KERAK (260902, obyektda
         *    o'lchandi). Amal bor edi, lekin u «Rastani biriktirish»
         *    dialogining ICHIDA yashiringandi — tugmaning nomi o'chirish
         *    borligini aytmaydi va operator uni topa olmadi. Noto'g'ri
         *    chizilgan zonani yo'qotishning yagona yo'li «Qaytarish»
         *    edi, u esa ORALIQDAGI barcha ishni ham qaytarardi.
         *
         * ⚠ TASDIQ DIALOGI SAQLANADI: o'chirish bir bosishda
         *   bajarilmaydi. Zona geometriyasi qo'lda chizilgan ish va uni
         *   tasodifan yo'qotish qimmat.
         */}
        <Button
          aria-disabled={canDelete ? undefined : true}
          className={canDelete ? undefined : "opacity-60"}
          onClick={() => {
            if (!canDelete) {
              onAnnounce(t("cameraZones.deleteNeedsOne"));
              return;
            }
            onDeleteZone();
          }}
          size="sm"
          variant="secondary"
        >
          <Trash2 aria-hidden="true" />
          {t("cameraZones.deleteZone")}
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

      {hint === null ? null : <p className="text-xs text-text-muted">{hint}</p>}
    </div>
  );
}
