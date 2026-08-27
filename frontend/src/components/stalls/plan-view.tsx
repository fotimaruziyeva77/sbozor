"use client";

import { useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";

import { gridSize } from "@/components/stalls/plan-model";
import { StallCell } from "@/components/stalls/stall-cell";
import { StallMapLegend } from "@/components/stalls/stall-map-legend";
import type { StallCell as StallCellData } from "@/components/stalls/stall-map-types";
import { DAY_STATE_KEYS, dayToneOf, toneOf } from "@/components/stalls/stall-tone";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { useStallMapQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * QO'LDA CHIZILGAN PLAN — KO'RISH REJIMI (260820).
 *
 * ⛔⛔ NEGA BU UMUMAN BOR: chizmaning BUTUN QIYMATI shu yerda.
 *
 *     Muharrirda chizilgan shakl faqat muharrirda ko'rinsa, u shunchaki
 *     bajarilgan mashq bo'lardi. Kundalik ekranda esa u savolga javob
 *     beradi: «qarzdor rasta QAYERDA?» — nazoratchi endi qizil katakni
 *     bozordagi haqiqiy joyga bog'lay oladi.
 *
 * =============================================================================
 * ⛔⛔ KATAK — `StallCell`, YANGI KOMPONENT EMAS.
 *
 *     Ton, ikonka, `aria-label`, to'lov qatlami, 44px nishon — bularning
 *     hammasi sxematik xaritada ALLAQACHON o'lchangan va qulflangan.
 *     Plan uchun ikkinchi katak komponenti yozilsa, ular bir kun
 *     jimgina ajralib ketardi: qarzdor rasta bir ko'rinishda qizil,
 *     ikkinchisida neytral bo'lardi.
 *
 *     Bu yerda FAQAT joylashuv boshqacha: `grid-column` / `grid-row`
 *     saqlangan koordinatadan keladi, avtomatik oqimdan emas.
 *
 * ⛔ CHIZILMAGAN RASTA BU YERDA KO'RINMAYDI — va u shuning uchun ham
 *   `/map` da sxematik ko'rinish YO'QOLMAYDI (sahifadagi almashtirgich).
 *   Ular qancha ekani pastda SON bilan aytiladi: jimgina yo'qolgan
 *   rasta — chizmaga bo'lgan ishonchni yo'qotadigan yagona narsa.
 * =============================================================================
 */

const CELL_PX = 44;

export function PlanView({
  focusCode,
  onSelectStall,
}: {
  /** `/map?q=` dagi raqam — sxematik ko'rinishdagi bilan BIR XIL xulq. */
  focusCode: string;
  onSelectStall: (stallId: string) => void;
}) {
  const t = useTranslations();
  const mapQuery = useStallMapQuery();
  const dayLayer = useMapDayStatusQuery();

  /** Koordinatasi bor rastalar — zona nomi bilan birga. */
  const placed = useMemo(() => {
    const items: {
      cell: StallCellData;
      zoneName: string;
      x: number;
      y: number;
    }[] = [];

    for (const zone of mapQuery.data?.zones ?? []) {
      for (const cell of zone.cells) {
        if (cell.plan_x === null || cell.plan_y === null) continue;
        const day = dayLayer.byStallId.get(cell.id);
        items.push({
          cell: {
            id: cell.id,
            code: cell.code,
            tone: toneOf(cell),
            hasVendor: cell.has_vendor,
            dayTone: day === undefined ? null : dayToneOf(day.state),
            dayStateKey: day === undefined ? null : DAY_STATE_KEYS[day.state],
          },
          zoneName: zone.name,
          x: cell.plan_x,
          y: cell.plan_y,
        });
      }
    }
    return items;
  }, [mapQuery.data, dayLayer.byStallId]);

  const totalCells = (mapQuery.data?.zones ?? []).reduce(
    (sum, zone) => sum + zone.cells.length,
    0,
  );
  const missing = totalCells - placed.length;

  const { cols, rows } = useMemo(
    () =>
      gridSize(
        Object.fromEntries(
          placed.map((item) => [item.cell.id, { x: item.x, y: item.y }]),
        ),
      ),
    [placed],
  );

  /*
   * ⛔⛔ UCH HOLAT, IKKI EMAS (260820, Chromeda o'lchandi).
   *
   *   Avval faqat «topildi / topilmadi» bor edi va chizilmagan rasta
   *   qidirilganda ekran «xaritada topilmadi» derdi. Bu YOLG'ON: rasta
   *   bozorda BOR, u shunchaki hali chizilmagan. Odam esa uni yo'q deb
   *   o'ylab, reestrga qarab vaqt sarflardi.
   *
   *   Endi uchinchi holat alohida: «bor, lekin chizilmagan» va u
   *   qayerga qarashni AYTADI.
   */
  const focusState: "none" | "drawn" | "notDrawn" | "missing" =
    focusCode === ""
      ? "none"
      : placed.some((item) => item.cell.code === focusCode)
        ? "drawn"
        : (mapQuery.data?.zones ?? []).some((zone) =>
              zone.cells.some((cell) => cell.code === focusCode),
            )
          ? "notDrawn"
          : "missing";

  /*
   * ⛔⛔ QIDIRUV BU YERDA HAM ISHLASHI SHART (260820, Chromeda o'lchandi).
   *
   *   Qidiruv maydoni ikkala ko'rinish USTIDA turadi, lekin fokus
   *   mantig'i faqat `stall-map.tsx` da edi — ya'ni chizilgan planda
   *   raqam terilganda MUTLAQO hech nima bo'lmasdi. Ko'rinib turgan,
   *   bosiladigan, jim ishlaydigan boshqaruv — eng yomon turi:
   *   foydalanuvchi «men noto'g'ri terdimmi?» deb o'ylaydi.
   *
   * ⚠ Nusxa emas, ZANJIR bir xil: `data-stall-code` atributi `StallCell`
   *   ning O'ZIDA (u ikkala ko'rinishda ham ishlatiladi), shuning uchun
   *   bu effekt sxematik ko'rinishdagi bilan aynan bir xil selektorni
   *   qidiradi. `<details>` bu yerda yo'q — plan yig'ilmaydi.
   */
  useEffect(() => {
    if (focusCode === "") return;
    const target = document.querySelector<HTMLButtonElement>(
      `[data-stall-code="${CSS.escape(focusCode)}"]`,
    );
    if (!target) return;
    target.scrollIntoView({ block: "nearest", inline: "nearest" });
    target.focus();
  }, [focusCode, placed]);

  return (
    <div className="flex flex-col gap-3">
      {/*
       * ⛔⛔ LEGENDA CHIZILGAN PLANDA HAM (260820).
       *
       *   Kataklar sxematik ko'rinish bilan AYNAN bir xil ranglarni
       *   oladi (`StallCell`), lekin legenda faqat u yerda edi — ya'ni
       *   ko'rinish almashtirilganda qizil-ko'k-yashil TUSHUNTIRISHSIZ
       *   qolardi. Rang esa yagona signal bo'lmasligi kerak (WCAG
       *   1.4.1) va legenda aynan o'sha ikkinchi kanal.
       */}
      <StallMapLegend
        showPaymentStates={
          dayLayer.status !== null && dayLayer.status.market_active
        }
      />

      {focusState === "notDrawn" ? (
        <p className="text-sm text-text-muted" role="status">
          {t("plan.notDrawnYet")}
        </p>
      ) : null}
      {focusState === "missing" ? (
        <p className="text-sm text-text-muted" role="status">
          {t("map.notFound")}
        </p>
      ) : null}

      <div className="overflow-auto rounded-lg border border-border bg-surface p-3">
        <div
          className="grid gap-1"
          style={{
            gridTemplateColumns: `repeat(${cols}, ${CELL_PX}px)`,
            gridTemplateRows: `repeat(${rows}, ${CELL_PX}px)`,
            width: "max-content",
          }}
        >
          {placed.map((item) => (
            <div
              key={item.cell.id}
              style={{ gridColumn: item.x + 1, gridRow: item.y + 1 }}
            >
              <StallCell
                categoryName={null}
                cell={item.cell}
                onSelect={onSelectStall}
                tabIndex={0}
                vendorName={null}
                zoneName={item.zoneName}
              />
            </div>
          ))}
        </div>
      </div>

      {missing > 0 ? (
        <p className="text-sm text-text-muted">
          {t("plan.notDrawnNote", { count: missing })}
        </p>
      ) : null}
    </div>
  );
}
