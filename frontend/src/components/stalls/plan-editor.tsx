"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { useTranslations } from "next-intl";
import { Eraser, Pencil, Plus, RotateCcw } from "lucide-react";

import {
  GROW_STEP,
  cellsBetween,
  clearSequence,
  gridSize,
  isEmptyDiff,
  occupancyOf,
  placeSequence,
  placementFromZones,
  planDiff,
  queueOf,
  spotKey,
} from "@/components/stalls/plan-model";
import type { PlanSpot, Placement } from "@/components/stalls/plan-model";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useSaveStallPlan, useStallMapQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * QO'LDA CHIZISH MUHARRIRI — «BOSING, QO'YILADI, KEYINGISI O'ZI TANLANADI».
 *
 * ⛔⛔ ODAM — BOZOR ADMINI, DIZAYNER EMAS. U sichqonchani sudrab
 *     shakl chizmaydi; u bozorni BILADI va uni panjaraga KO'CHIRADI.
 *     Shuning uchun asosiy harakat bitta: BO'SH KATAKNI BOSISH.
 *     Navbatdagi rasta o'sha yerga tushadi va navbat o'zi siljiydi —
 *     ya'ni A qatorini chizish «bos-bos-bos» dan iborat.
 *
 * ⛔ SURISH (drag) — QO'SHIMCHA, MAJBURIY EMAS. Barmoq yoki sichqoncha
 *   bosilgan holda kataklar ustidan yurganda navbat ketma-ket to'kiladi.
 *   Bu tez, lekin uni BILMAGAN odam ham bosish bilan hamma ishni
 *   qila oladi — sirli imo-ishoraga bog'liq funksiya YO'Q.
 *
 * =============================================================================
 * ⛔⛔ CANVAS KUTUBXONASI QO'SHILMADI (`konva`/`react-konva`).
 *
 *     CLAUDE.md ularni aynan shu ish uchun sanab o'tgan, LEKIN
 *     `stall-map.tsx` da o'lchangan sabab bu yerda ham kuchda:
 *     panjara STATIK (kadr-bo'yicha animatsiya yo'q), kataklar esa
 *     haqiqiy `<button>` bo'lishi kerak — klaviatura, fokus,
 *     skrinrider va SSR tekinga keladi. Canvas bularning HAMMASINI
 *     qo'lda qayta yozishni talab qilardi, evaziga esa bizga kerak
 *     bo'lmagan yagona narsani — 60 fps qayta chizishni — berardi.
 *
 *     Ikki yangi bog'liqlik va nol foyda. Shuning uchun DOM.
 * =============================================================================
 */

/** Chizish yoki o'chirish — panjaradagi bosish nimani anglatadi. */
type Mode = "draw" | "erase";

/** Katak o'lchami — `pointer-coarse` da barmoq sig'adigan 44px'dan katta. */
const CELL_PX = 48;

export function PlanEditor() {
  const t = useTranslations();
  const mapQuery = useStallMapQuery();
  const save = useSaveStallPlan();

  /*
   * ⛔⛔ SERVER HOLATI VA TAHRIR HOLATI — IKKI ALOHIDA NARSA.
   *
   *   `draft === null` degani «hali hech narsa tahrir qilinmagan», ya'ni
   *   ekranda SERVERNING chizmasi turibdi. Birinchi tahrirda nusxa
   *   olinadi. Bu `useEffect` bilan serverdan holatga ko'chirishdan
   *   ustun: ko'chirish qayta so'rov kelganda (fokus qaytganda,
   *   invalidatsiyadan keyin) odamning YARIM CHIZILGAN ishini
   *   jimgina bosib tashlardi.
   */
  const [draft, setDraft] = useState<Placement | null>(null);
  const [mode, setMode] = useState<Mode>("draw");
  const [extra, setExtra] = useState({ cols: 0, rows: 0 });
  /** Navbatdan tanlab olingan rasta — `null` bo'lsa navbatning boshi. */
  const [pickedId, setPickedId] = useState<string | null>(null);
  const painting = useRef(false);
  /**
   * Surishda OXIRGI tekkan katak — yo'lni to'ldirish uchun.
   *
   * ⛔ `useRef`, `useState` EMAS: bu qiymat renderga ta'sir qilmaydi va
   *   holat sifatida saqlansa har `pointerenter` da qo'shimcha render
   *   tug'dirardi — 1000 katakli panjarada bu sezilarli.
   */
  const lastSpot = useRef<PlanSpot | null>(null);

  const zones = useMemo(() => mapQuery.data?.zones ?? [], [mapQuery.data]);
  const original = useMemo(() => placementFromZones(zones), [zones]);
  const placement = draft ?? original;

  const occupancy = useMemo(() => occupancyOf(placement), [placement]);
  const queue = useMemo(() => queueOf(zones, placement), [zones, placement]);
  const codeById = useMemo(() => {
    const map = new Map<string, string>();
    for (const zone of zones) {
      for (const cell of zone.cells) map.set(cell.id, cell.code);
    }
    return map;
  }, [zones]);

  const diff = useMemo(
    () => planDiff(original, placement),
    [original, placement],
  );
  const { cols, rows } = gridSize(placement, extra.cols, extra.rows);

  /** Navbatdan keyingi rasta: qo'lda tanlangani, bo'lmasa boshi. */
  const nextStall = useMemo(() => {
    if (pickedId !== null) {
      const picked = queue.find((item) => item.id === pickedId);
      if (picked !== undefined) return picked;
    }
    return queue[0];
  }, [queue, pickedId]);

  /**
   * Bitta katakka ta'sir — bosishda ham, surishda ham AYNAN shu yo'l.
   *
   * ⛔ `setDraft` ichida hisoblanadi: surish paytida hodisalar tez
   *   ketma-ket keladi va tashqaridagi `placement` ESKIRGAN bo'lardi —
   *   natijada ikkinchi katak birinchisining ustiga yozilardi.
   */
  /**
   * Bitta katakka ta'sir — bosishda BITTA katak, surishda BUTUN YO'L.
   *
   * ⛔⛔ `setDraft` ICHIDA hisoblanadi: surish paytida hodisalar tez
   *     ketma-ket keladi va tashqaridagi `placement` ESKIRGAN bo'lardi —
   *     natijada ikkinchi katak birinchisining ustiga yozilardi.
   *
   * ⛔ `spots` — yo'ldagi kataklar RO'YXATI, bitta katak emas: tez
   *   surishda brauzer oraliq kataklarni bermaydi va ular
   *   `cellsBetween` bilan TO'LDIRILADI (260820 da Chromeda o'lchangan
   *   nuqson — qatorda teshik qolardi).
   */
  const touchCells = useCallback(
    (spots: readonly PlanSpot[]) => {
      if (spots.length === 0) return;

      setDraft((current) => {
        const base = current ?? original;
        if (mode === "erase") return clearSequence(base, spots);

        /*
         * Navbat: qo'lda tanlangani BIRINCHI, keyin qolganlari server
         * tartibida. Shu bilan «bu rastadan boshlab qatorni chiz»
         * bitta harakatga jamlanadi.
         */
        const pending = queueOf(zones, base).map((item) => item.id);
        const ordered =
          pickedId === null
            ? pending
            : [
                ...pending.filter((id) => id === pickedId),
                ...pending.filter((id) => id !== pickedId),
              ];

        return placeSequence(base, ordered, spots);
      });
      /*
       * Qo'lda tanlangan rasta QO'YILGACH bekor qilinadi — aks holda
       * keyingi bosish O'SHA rastani ko'chirardi va odam «nega faqat
       * bittasi yuryapti?» degan savol bilan qolardi.
       */
      if (mode === "draw") setPickedId(null);
    },
    [mode, original, pickedId, zones],
  );

  const onCellDown = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>, x: number, y: number) => {
      painting.current = true;
      lastSpot.current = { x, y };
      /*
       * ⛔⛔ `releasePointerCapture` MAJBURIY: barmoq bilan bosilganda
       *     brauzer hamma hodisani SHU tugmaga yo'naltiradi (implicit
       *     capture), ya'ni qo'shni kataklarning `pointerenter` i hech
       *     qachon ishlamasdi va surish bitta katakda qotib qolardi.
       *
       * ⛔ LEKIN U QO'YISHDAN KEYIN CHAQIRILADI, oldin EMAS (260820).
       *
       *    Avval teskari tartibda edi va bu butun bosishni yo'q
       *    qilishi mumkin ekan: Pointer Events API'siz muhitda
       *    (`hasPointerCapture` yo'q — jsdom, eski webview) chaqiruv
       *    ISTISNO tashlaydi va undan KEYINGI `touchCells` umuman
       *    ishlamaydi. Ya'ni ekran ochiladi, katak bosiladi, hech
       *    nima bo'lmaydi.
       *
       *    Endi asosiy ish BIRINCHI bajariladi va capture ozod
       *    qilish — ixtiyoriy yaxshilanish.
       */
      touchCells([{ x, y }]);

      const target = event.currentTarget;
      if (
        typeof target.hasPointerCapture === "function" &&
        target.hasPointerCapture(event.pointerId)
      ) {
        target.releasePointerCapture(event.pointerId);
      }
    },
    [touchCells],
  );

  const onCellEnter = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>, x: number, y: number) => {
      if (!painting.current || event.buttons === 0) return;
      const from = lastSpot.current;
      lastSpot.current = { x, y };
      touchCells(from === null ? [{ x, y }] : cellsBetween(from, { x, y }));
    },
    [touchCells],
  );

  if (mapQuery.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-11 w-full max-w-md rounded-lg" />
        <Skeleton className="h-96 rounded-lg" />
      </div>
    );
  }

  if (mapQuery.isError) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(mapQuery.error))}
      </p>
    );
  }

  const totalCells = zones.reduce((sum, zone) => sum + zone.cells.length, 0);
  if (totalCells === 0) {
    return (
      <EmptyState
        description={t("map.emptyStateHint")}
        title={t("map.emptyState")}
      />
    );
  }

  const placedCount = Object.keys(placement).length;

  return (
    <div className="flex flex-col gap-4">
      <PlanToolbar
        canSave={!isEmptyDiff(diff) && !save.isPending}
        isSaving={save.isPending}
        mode={mode}
        onGrowCols={() =>
          setExtra((value) => ({ ...value, cols: value.cols + GROW_STEP }))
        }
        onGrowRows={() =>
          setExtra((value) => ({ ...value, rows: value.rows + GROW_STEP }))
        }
        onModeChange={setMode}
        onReset={() => {
          setDraft(null);
          setPickedId(null);
          save.reset();
        }}
        onSave={() => {
          save.mutate(diff, {
            /*
             * ⛔ Saqlangach `draft` NULLGA qaytariladi: shundan keyin
             *   ekran yana SERVERNING javobiga tayanadi va «saqlanmagan
             *   o'zgarish» belgisi o'z-o'zidan yo'qoladi. Draftni
             *   qoldirish esa serverning javobi bilan jimgina
             *   ajralib ketishi mumkin bo'lgan ikkinchi haqiqat
             *   yaratardi.
             */
            onSuccess: () => {
              setDraft(null);
              setPickedId(null);
            },
          });
        }}
        placedCount={placedCount}
        totalCount={totalCells}
      />

      {save.isError ? (
        <p className="text-sm font-semibold text-danger-text" role="alert">
          {t(marketErrorMessageKey(save.error))}
        </p>
      ) : null}
      {save.isSuccess && draft === null ? (
        <p className="text-sm font-semibold text-success-text" role="status">
          {t("plan.saved", {
            placed: save.data.placed_count,
            cleared: save.data.cleared_count,
          })}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <PlanQueue
          nextId={nextStall?.id ?? null}
          onPick={setPickedId}
          queue={queue}
        />

        <div className="overflow-auto rounded-lg border border-border bg-surface p-3">
          <div
            aria-label={t("plan.gridLabel")}
            /*
             * ⛔⛔ `gap` YO'Q — VA BU DIZAYN EMAS, NUQSON TUZATISHI
             *     (260820, Chromeda o'lchandi).
             *
             *     Avval panjara `gap-1` (4px) bilan chizilgan edi va
             *     o'sha 4px BOSISHNI YUTARDI: hodisa katak tugmasiga
             *     emas, konteynerga tushardi va ekranda MUTLAQO hech
             *     nima bo'lmasdi. Sichqonchada bu «tegmadim» bo'lib
             *     tuyulardi; barmoqda esa — har uchinchi urinish.
             *
             *     Endi oraliq tugmaning ICHIDA (`p-[3px]`): ko'rinish
             *     o'sha-o'sha, lekin o'lik piksel qolmadi.
             */
            className="grid touch-none"
            onPointerLeave={() => {
              painting.current = false;
              lastSpot.current = null;
            }}
            onPointerUp={() => {
              painting.current = false;
              lastSpot.current = null;
            }}
            role="group"
            style={{
              gridAutoRows: `${CELL_PX}px`,
              gridTemplateColumns: `repeat(${cols}, ${CELL_PX}px)`,
              width: "max-content",
            }}
          >
            {Array.from({ length: rows }, (_, y) =>
              Array.from({ length: cols }, (_, x) => {
                const stallId = occupancy.get(spotKey(x, y));
                return (
                  <PlanCell
                    code={stallId === undefined ? null : (codeById.get(stallId) ?? "")}
                    key={spotKey(x, y)}
                    label={
                      stallId === undefined
                        ? t("plan.cellEmpty", { x: x + 1, y: y + 1 })
                        : t("plan.cellTaken", {
                            code: codeById.get(stallId) ?? "",
                            x: x + 1,
                            y: y + 1,
                          })
                    }
                    onPointerDown={onCellDown}
                    onPointerEnter={onCellEnter}
                    x={x}
                    y={y}
                  />
                );
              }),
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Panjaraning bitta katagi — haqiqiy tugma (klaviatura tekinga keladi). */
function PlanCell({
  code,
  label,
  onPointerDown,
  onPointerEnter,
  x,
  y,
}: {
  code: string | null;
  label: string;
  onPointerDown: (
    event: ReactPointerEvent<HTMLButtonElement>,
    x: number,
    y: number,
  ) => void;
  onPointerEnter: (
    event: ReactPointerEvent<HTMLButtonElement>,
    x: number,
    y: number,
  ) => void;
  x: number;
  y: number;
}) {
  return (
    <button
      aria-label={label}
      /*
       * ⛔ TUGMA BUTUN TREKNI TO'LDIRADI (`size-full`), oraliq esa
       *   uning ICHIDA (`p-[3px]`) — panjarada o'lik piksel qolmasin.
       *   Ko'rinadigan quti ichkaridagi `<span>` da.
       */
      className={cn(
        "block size-full p-[3px]",
        "focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent",
      )}
      onPointerDown={(event) => onPointerDown(event, x, y)}
      onPointerEnter={(event) => onPointerEnter(event, x, y)}
      title={code ?? undefined}
      type="button"
    >
      <span
        className={cn(
          "flex size-full items-center justify-center rounded-md border text-sm",
          "transition-colors duration-(--motion-fast)",
          code === null
            ? "border-dashed border-border bg-surface-muted/40 hover:bg-accent/10"
            : "border-border bg-surface font-semibold text-text shadow-card hover:border-accent",
        )}
      >
        {code === null ? "" : <span className="truncate px-1">{code}</span>}
      </span>
    </button>
  );
}

/** Yuqoridagi boshqaruv — rejim, kengaytirish, bekor qilish, saqlash. */
function PlanToolbar({
  canSave,
  isSaving,
  mode,
  onGrowCols,
  onGrowRows,
  onModeChange,
  onReset,
  onSave,
  placedCount,
  totalCount,
}: {
  canSave: boolean;
  isSaving: boolean;
  mode: Mode;
  onGrowCols: () => void;
  onGrowRows: () => void;
  onModeChange: (mode: Mode) => void;
  onReset: () => void;
  onSave: () => void;
  placedCount: number;
  totalCount: number;
}) {
  const t = useTranslations();

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3">
      <div className="flex gap-1" role="group">
        <Button
          aria-pressed={mode === "draw"}
          onClick={() => onModeChange("draw")}
          size="sm"
          variant={mode === "draw" ? "default" : "secondary"}
        >
          <Pencil aria-hidden="true" />
          {t("plan.modeDraw")}
        </Button>
        <Button
          aria-pressed={mode === "erase"}
          onClick={() => onModeChange("erase")}
          size="sm"
          variant={mode === "erase" ? "default" : "secondary"}
        >
          <Eraser aria-hidden="true" />
          {t("plan.modeErase")}
        </Button>
      </div>

      <span className="text-sm text-text-muted">
        {t("plan.progress", { placed: placedCount, total: totalCount })}
      </span>

      <div className="ms-auto flex flex-wrap items-center gap-2">
        <Button onClick={onGrowCols} size="sm" variant="ghost">
          <Plus aria-hidden="true" />
          {t("plan.growCols")}
        </Button>
        <Button onClick={onGrowRows} size="sm" variant="ghost">
          <Plus aria-hidden="true" />
          {t("plan.growRows")}
        </Button>
        <Button onClick={onReset} size="sm" variant="secondary">
          <RotateCcw aria-hidden="true" />
          {t("plan.reset")}
        </Button>
        <Button
          aria-disabled={!canSave}
          onClick={() => {
            if (canSave) onSave();
          }}
          size="sm"
        >
          {isSaving ? t("common.loading") : t("common.save")}
        </Button>
      </div>
    </div>
  );
}

/**
 * Chizilmagan rastalar navbati.
 *
 * ⛔⛔ NAVBAT — MUHARRIRNING «QANCHA QOLDI?» JAVOBI. Usiz odam 300
 *     rastali bozorda qaysi birini unutganini FAQAT ko'z bilan
 *     qidirib topardi. Ro'yxat bo'shashi — ishning tugagani.
 */
function PlanQueue({
  nextId,
  onPick,
  queue,
}: {
  nextId: string | null;
  onPick: (stallId: string) => void;
  queue: readonly { id: string; code: string; zoneName: string }[];
}) {
  const t = useTranslations();

  return (
    <div className="flex max-h-[32rem] flex-col gap-2 overflow-auto rounded-lg border border-border bg-surface p-3">
      <h2 className="text-sm font-semibold text-text">
        {t("plan.queueTitle", { count: queue.length })}
      </h2>

      {queue.length === 0 ? (
        <p className="text-sm text-text-muted">{t("plan.queueEmpty")}</p>
      ) : (
        <p className="text-sm text-text-muted">{t("plan.queueHint")}</p>
      )}

      <ul className="flex flex-col gap-1">
        {queue.map((item) => (
          <li key={item.id}>
            <button
              className={cn(
                "flex w-full items-center justify-between gap-2 rounded-md px-2 py-2",
                "text-start text-sm transition-colors duration-(--motion-fast)",
                "pointer-coarse:min-h-11",
                item.id === nextId
                  ? "bg-accent/10 font-semibold text-accent-text"
                  : "hover:bg-surface-muted",
              )}
              onClick={() => onPick(item.id)}
              type="button"
            >
              <span>{item.code}</span>
              <span className="truncate text-xs text-text-muted">
                {item.zoneName}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
