"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { MapZone } from "@/lib/api-types";
import { interpolateRow } from "@/lib/zone-geometry";
import type { Poly } from "@/lib/zone-geometry";

/*
 * =============================================================================
 * DL-2 — QATOR BO'YICHA BO'LISH. 300–1000 RASTA UCHUN HALOL JAVOB (§6.7).
 *
 * Ish hajmining arifmetikasi: yordamchisiz ~2–5 soat, qator yordamchisi
 * bilan ~0,5–1 soat. Farq shundan: qatorda 10–20 rasta bor va admin
 * ikkitasini chizadi, qolganini chiziqli interpolyatsiya to'ldiradi.
 *
 * ⛔ BU YORDAMCHI SOF GEOMETRIYA VA U HECH QANDAY CV DA'VOSI QILMAYDI.
 *    Bozor rastalari qator-qator va bir xil o'lchamda — bu KUZATILGAN
 *    haqiqat, model taxmini emas. Har rasta baribir O'Z poligonini oladi
 *    va admin uni keyin alohida to'g'rilaydi.
 *
 * ⛔ RAD ETILGAN YO'L: «detektor topgan qutilarni zona qilish». U AYLANMA
 *    MANTIQ — detektorning xatosi zona geometriyasiga aylanardi, keyin
 *    o'sha geometriya bo'yicha o'sha detektor baholanardi va aniqlik
 *    SOXTA ko'tarilardi (§6.7, §16.2).
 *
 * -----------------------------------------------------------------------
 * ⛔ NOMUVOFIQLIKDA HECH NIMA QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * 4-fazadagi «qisman to'ldirish yo'q» qoidasi: qisman natija «qaysilari
 * qo'shildi?» savolini tug'dirardi va uni faqat kadrni sanab tekshirish
 * bilan hal qilib bo'lardi. Shuning uchun `planRowSplit()` YOKI to'liq
 * ro'yxat, YOKI sababli rad etish qaytaradi — oraliq holat YO'Q.
 *
 * ⛔ NATIJA DARHOL SAQLANMAYDI — u muharrirga qo'shiladi va `[Saqlash]`
 *    ni kutadi. Avtomatik saqlash operatorni «bajarildi» deb
 *    ishontirardi, holbuki u har poligonni ko'zi bilan tekshirishi kerak.
 * =============================================================================
 */

export type RowSplitPlan =
  | { ok: true; polygons: readonly Poly[]; stallIds: readonly string[] }
  | {
      ok: false;
      reason: "no-targets" | "vertex-mismatch" | "count-mismatch";
    };

export type RowTarget = { code: string; id: string };

/** Barqaror bo'sh havola — effekt bog'liqligi bo'lgani uchun MODUL darajasida. */
const NO_PREVIEW: readonly Poly[] = [];

/**
 * Qatorning ORASIDAGI rastalar — SOF FUNKSIYA.
 *
 * ⚠ TARTIB MANBAI — BOZOR ZONASI ICHIDAGI `code_sort`. Bu 2-fazadan
 *   qolgan YAGONA mavjud tartib (`GET /stalls/map` kataklarni aynan shu
 *   tartibda qaytaradi). Operator uni oldindan ko'rishda KO'ZI BILAN
 *   tekshiradi — shuning uchun tartibni «aqlli» qilishga urinilmaydi.
 *
 * ⚠ ALLAQACHON ZONASI BOR RASTA CHIQARILADI va SANALADI: jimgina ustiga
 *   yozish avvalgi tahrirlarni yo'q qilardi.
 */
export function rowTargets(input: {
  /** Qatorning birinchi rastasi. */
  firstStallId: string;
  /** Qatorning oxirgi rastasi. */
  lastStallId: string;
  /** Bu kamerada ALLAQACHON zonasi bor rastalar. */
  occupiedStallIds: readonly string[];
  zones: readonly MapZone[];
}): { skipped: number; targets: readonly RowTarget[] } {
  const zone = input.zones.find((candidate) =>
    candidate.cells.some((cell) => cell.id === input.firstStallId),
  );
  if (zone === undefined) return { skipped: 0, targets: [] };

  const first = zone.cells.findIndex((cell) => cell.id === input.firstStallId);
  const last = zone.cells.findIndex((cell) => cell.id === input.lastStallId);
  if (first < 0 || last < 0) return { skipped: 0, targets: [] };

  const [from, to] = first <= last ? [first, last] : [last, first];
  const between = zone.cells.slice(from + 1, to);

  const occupied = new Set(input.occupiedStallIds);
  const targets = between
    .filter((cell) => !occupied.has(cell.id))
    .map((cell): RowTarget => ({ code: cell.code, id: cell.id }));

  return { skipped: between.length - targets.length, targets };
}

/**
 * Oraliq poligonlar — YOKI HAMMASI, YOKI HECH NIMA.
 *
 * ⚠ IKKI RAD ETISH SABABI ALOHIDA NOMLANADI va bu ataylab:
 *
 *   `vertex-mismatch`  — ikkala poligonda tepalar soni har xil.
 *                        `interpolateRow` bunday holatda `[]` qaytaradi
 *                        («eng yaqin tepani topish» ATAYIN yozilmagan:
 *                        u ba'zan ishlab, ba'zan aralashib ketgan
 *                        poligon chizardi).
 *   `count-mismatch`   — hosil bo'lgan poligonlar soni rastalar soniga
 *                        teng emas. Bu ikkinchi qatlam: geometriya
 *                        funksiyasi bir kun boshqacha ishlasa, dialog
 *                        JIMGINA noto'g'ri sonni qo'shmasligi kerak.
 *
 * Ikkalasi bir xil xabar bersa, admin nima qilishni bilmasdi: birinchisi
 * TEPALARNI tenglashtirishni, ikkinchisi esa umuman boshqa tekshiruvni
 * talab qiladi.
 *
 * =========================================================================
 * ⚠⚠ NEGA GEOMETRIYA FUNKSIYASI ARGUMENT — VA BU SABOTAJ BILAN O'LCHANDI.
 *
 *   Birinchi yozuvda `interpolateRow` to'g'ridan-to'g'ri chaqirilardi va
 *   `count-mismatch` tarmog'i BUGUNGI kontrakt ostida YETIB BO'LMAYDIGAN
 *   bo'lib qolgan edi: `interpolateRow` tepa soni teng bo'lmaganda `[]`
 *   qaytaradi, lekin u holat YUQORIDA allaqachon ushlanadi, qolgan
 *   hollarda esa u AYNAN `n` ta poligon qaytaradi.
 *
 *   O'lchov: o'sha tarmoqni butunlay o'chirib tashlash HECH BIR TESTNI
 *   qizartirmadi. Ya'ni «ikkinchi qatlam» degan da'vo o'lchanmagan
 *   bo'lardi — 05-06 ning S4 sabotaji fosh qilgan sinfning aynan o'zi.
 *
 *   Shuning uchun interpolyator INJEKSIYA qilinadi: standart qiymat
 *   ishlab chiqarishda ishlatiladi, test esa ATAYIN kam poligon
 *   qaytaradigan funksiya berib, himoyaning HAQIQATAN ishlashini
 *   o'lchaydi. Bu — kelajakda `zone-geometry.ts` o'zgarsa, DL-2 jimgina
 *   noto'g'ri sonda zona qo'shmasligining kafolati.
 * =========================================================================
 */
export function planRowSplit(
  input: {
    firstPolygon: Poly;
    lastPolygon: Poly;
    targets: readonly RowTarget[];
  },
  interpolate: (first: Poly, last: Poly, n: number) => readonly Poly[] =
    interpolateRow,
): RowSplitPlan {
  if (input.targets.length === 0) return { ok: false, reason: "no-targets" };

  if (input.firstPolygon.length !== input.lastPolygon.length) {
    return { ok: false, reason: "vertex-mismatch" };
  }

  const polygons = interpolate(
    input.firstPolygon,
    input.lastPolygon,
    input.targets.length,
  );

  if (polygons.length !== input.targets.length) {
    return { ok: false, reason: "count-mismatch" };
  }

  return {
    ok: true,
    polygons,
    stallIds: input.targets.map((target) => target.id),
  };
}

export function RowAssistDialog({
  firstLabel,
  firstPolygon,
  firstStallId,
  lastLabel,
  lastPolygon,
  lastStallId,
  occupiedStallIds,
  onApply,
  onOpenChange,
  onPreview,
  open,
  zones,
}: {
  firstLabel: string;
  firstPolygon: Poly;
  firstStallId: string | null;
  lastLabel: string;
  lastPolygon: Poly;
  lastStallId: string | null;
  occupiedStallIds: readonly string[];
  onApply: (result: {
    polygons: readonly Poly[];
    stallIds: readonly string[];
  }) => void;
  onOpenChange: (open: boolean) => void;
  /** Kadrdagi punktir ko'rinish — dialog ochilganda yoqiladi. */
  onPreview: (polygons: readonly Poly[]) => void;
  open: boolean;
  zones: readonly MapZone[];
}) {
  const t = useTranslations();
  const [applied, setApplied] = useState(false);

  const { skipped, targets } = useMemo(
    () =>
      firstStallId === null || lastStallId === null
        ? { skipped: 0, targets: [] as readonly RowTarget[] }
        : rowTargets({ firstStallId, lastStallId, occupiedStallIds, zones }),
    [firstStallId, lastStallId, occupiedStallIds, zones],
  );

  const plan = useMemo(
    () => planRowSplit({ firstPolygon, lastPolygon, targets }),
    [firstPolygon, lastPolygon, targets],
  );

  const previewPolygons = plan.ok ? plan.polygons : NO_PREVIEW;

  /*
   * ⚠ OLDINDAN KO'RISH — EFFEKTDA, render paytida emas. Renderda
   *   `onPreview` chaqirish ota komponentni yangilab, uni qayta
   *   renderga tushirardi va sikl yopilmasdi. Bog'liqliklar
   *   BARQAROR havolalar: `plan` `useMemo` dan, `NO_PREVIEW` esa modul
   *   konstantasi — har renderda yangi `[]` yasash effektni cheksiz
   *   qayta ishga tushirardi.
   */
  useEffect(() => {
    onPreview(open ? previewPolygons : NO_PREVIEW);
  }, [onPreview, open, previewPolygons]);

  const errorKey =
    plan.ok || plan.reason === "no-targets"
      ? null
      : plan.reason === "vertex-mismatch"
        ? "cameraZones.rowVertexMismatch"
        : "cameraZones.rowCountMismatch";

  return (
    <Dialog.Root
      onOpenChange={(next) => {
        if (!next) {
          onPreview([]);
          setApplied(false);
        }
        onOpenChange(next);
      }}
      open={open}
    >
      <Dialog.Content
        description={t("cameraZones.rowNeedsTwo")}
        size="sm"
        srOnlyDescription
        title={t("cameraZones.rowSplit")}
      >
        <div className="flex flex-col gap-3">
          <dl className="flex flex-col gap-1 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-text-muted">{t("cameraZones.rowFirst")}</dt>
              <dd className="font-semibold">{firstLabel}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-text-muted">{t("cameraZones.rowLast")}</dt>
              <dd className="font-semibold">{lastLabel}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-text-muted">{t("cameraZones.rowBetween")}</dt>
              <dd className="font-mono font-semibold">{targets.length}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-text-muted">{t("cameraZones.rowPreview")}</dt>
              <dd className="font-mono font-semibold">
                {previewPolygons.length}
              </dd>
            </div>
          </dl>

          {skipped > 0 ? (
            <p className="rounded-sm bg-warning/20 px-3 py-2 text-sm text-text">
              {t("cameraZones.rowSkipped", { count: skipped })}
            </p>
          ) : null}

          {errorKey === null ? null : (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              role="alert"
            >
              {t(errorKey)}
            </p>
          )}

          <Dialog.Footer>
            <Button
              aria-disabled={plan.ok && !applied ? undefined : true}
              className={plan.ok && !applied ? "sm:flex-1" : "opacity-60 sm:flex-1"}
              onClick={() => {
                /*
                 * ⛔ RAD ETILGAN REJADA TUGMA HECH NIMA QILMAYDI —
                 *    qisman qo'shish yo'li kod darajasida MAVJUD EMAS.
                 */
                if (!plan.ok || applied) return;
                setApplied(true);
                onApply({ polygons: plan.polygons, stallIds: plan.stallIds });
              }}
              variant="secondary"
            >
              {t("cameraZones.rowApply")}
            </Button>
            <Dialog.Close asChild>
              <Button className="sm:flex-1" variant="secondary">
                {t("common.cancel")}
              </Button>
            </Dialog.Close>
          </Dialog.Footer>
        </div>
      </Dialog.Content>
    </Dialog.Root>
  );
}
