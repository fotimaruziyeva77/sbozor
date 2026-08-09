"use client";

import { useEffect, useRef, useState } from "react";
import { TriangleAlert } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { toast } from "sonner";

import { CoverageCard } from "@/components/camera-zones/coverage-card";
import { ZoneCanvas } from "@/components/camera-zones/zone-canvas";
import type { CanvasZone } from "@/components/camera-zones/zone-canvas";
import { invalidZoneIds, ZoneList } from "@/components/camera-zones/zone-list";
import type { ListZone } from "@/components/camera-zones/zone-list";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ApiError } from "@/lib/api-client";
import type { CameraZone } from "@/lib/api-types";
import { useReplaceCameraZones } from "@/lib/camera-zone-queries";
import type { CameraZoneWriteInput } from "@/lib/camera-zone-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { zoneErrorView } from "@/lib/zone-errors";
import {
  insertMidpoint,
  MAX_ZONES_PER_CAMERA,
  moveVertex,
  deleteVertex,
  UNDO_DEPTH,
} from "@/lib/zone-geometry";
import type { Poly, Pt } from "@/lib/zone-geometry";

/*
 * =============================================================================
 * ZONA MUHARRIRI — KADR, RO'YXAT VA SAQLASHNI BOG'LAYDIGAN TASHKILOTCHI.
 *
 * Bu fayl HOLATNI ushlaydi; geometriya `lib/zone-geometry.ts` da, render
 * `zone-canvas.tsx` da, ochiqlik esa `zone-list.tsx` da. Uchtasi ham
 * ATAYIN ajratilgan: D-05 ning chiqish yo'li (Konva'ga o'tish) faqat
 * render faylini o'zgartirishi kerak.
 *
 * -----------------------------------------------------------------------
 * ⛔ SAQLANMAGAN O'ZGARISH: `beforeunload` QO'YILMAYDI
 * -----------------------------------------------------------------------
 * Brauzerning sahifadan chiqish ogohlantirishi LOKALIZATSIYA QILINMAYDI
 * (brauzer o'z matnini ko'rsatadi) va zamonaviy brauzerlar uni
 * foydalanuvchi sahifa bilan ishlamagan bo'lsa umuman bo'g'adi — ya'ni u
 * ba'zan chiqadigan, ba'zan chiqmaydigan kafolat. O'rniga ICHKI
 * navigatsiyada tasdiq: muharrirning O'Z «Kameralarga» boshqaruvi
 * saqlanmagan o'zgarish bo'lsa dialog ochadi.
 *
 * ⚠ CHEGARA HALOL AYTILADI: qobiqning yon menyusidagi havolalar
 *   USHLANMAYDI. Ularni ushlash `app-shell.tsx` ga tegishni talab
 *   qilardi va u bu rejaning fayl to'plamidan TASHQARIDA (navigatsiya
 *   byudjeti, §4.2). Saqlanmagan o'zgarishlar soni `[Zonalarni saqlash]`
 *   yonida DOIM ko'rinadi, ya'ni holat yashirin emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ RASTASIZ ZONA — LOKAL QORALAMA, VA BU KONTRAKTDAN KELIB CHIQADI
 * -----------------------------------------------------------------------
 * §6.3 «rastasiz zona SAQLANADI» deydi, lekin server kontrakti buni
 * IMKONSIZ qiladi: `CameraZoneWrite.stall_id` — MAJBURIY `UUID`
 * (05-06 `schemas.py`). Ya'ni rasta biriktirilmagan zonani yuborish
 * yo'li YO'Q.
 *
 * Shuning uchun: bunday zona muharrirda QOLADI, `PUT` tanasiga
 * TUSHMAYDI, va saqlashdan keyin ham «saqlanmagan» hisoblanadi —
 * hisoblagich nolga tushmaydi. Bu foydalanuvchiga ko'rinadigan, halol
 * signal; muqobil (uni jimgina tashlab yuborish) ma'lumot yo'qotishning
 * eng yomon shakli bo'lardi — «saqlandi» toasti bilan birga.
 * Toast esa sonni AYTADI (`noStallWarning`).
 *
 * -----------------------------------------------------------------------
 * ⚠ SERVER MA'LUMOTI QORALAMANI BOSIB KETMAYDI
 * -----------------------------------------------------------------------
 * Boshlang'ich holat `useState` ning INITIALIZATORIDA bir marta olinadi.
 * `refetchOnWindowFocus` fonda yangi javob keltirsa, u qoralamaga
 * TEGMAYDI: admin tabga qaytganda uning yarim tahrirlangan poligonlari
 * yo'qolib ketardi. Kamera almashganda esa sahifa `key` bilan qayta
 * montaj qilinadi (`page.tsx`), ya'ni holat toza boshlanadi.
 * =============================================================================
 */

/**
 * O'lchanmagan konteyner uchun zaxira o'lcham (px).
 *
 * ⚠ NEGA ZAXIRA KERAK: `nudgedPoint` nol o'lchamda `null` qaytaradi
 *   (`1/0` = `Infinity` tepani burchakka sakratardi). `ResizeObserver`
 *   birinchi renderdan KEYIN ishlaydi, ya'ni oradagi lahzada klaviatura
 *   umuman javob bermasdi. Zaxira qiymat bilan u ishlaydi va birinchi
 *   o'lchovdan keyin aniq qiymatga o'tadi.
 */
const FALLBACK_RENDER_WIDTH = 960;

/** Yangi zona — kadr MARKAZIDA, kengligi 0,20 va balandligi 0,15 (§13.4). */
const NEW_ZONE_HALF_WIDTH = 0.1;
const NEW_ZONE_HALF_HEIGHT = 0.075;

/** Koordinata e'lonining kechikishi — har piksel e'lon qilinsa skrinrider bo'g'ilardi. */
const ANNOUNCE_DEBOUNCE_MS = 500;

export type EditorZone = {
  id: string;
  polygon: Poly;
  needsReview: boolean;
  stallCode: string | null;
  stallId: string | null;
};

/** Server javobi -> muharrirning boshlang'ich holati. */
export function toEditorZones(
  items: readonly CameraZone[],
): readonly EditorZone[] {
  return items.map((item) => ({
    id: item.id,
    needsReview: item.needs_review,
    polygon: item.polygon.map(([x, y]): Pt => [x, y]),
    stallCode: item.stall_code,
    stallId: item.stall_id,
  }));
}

export function ZoneEditor({
  cameraId,
  frameHeight,
  frameHref,
  frameTakenAt,
  frameWidth,
  initialZones,
  onLeave,
}: {
  cameraId: string;
  /** Kadr NISBATINING maxraji (`snapshots.height` — piksel EMAS). */
  frameHeight: number;
  frameHref: string | null;
  /** Kadr olingan vaqt — admin qaysi kadr ustida chizayotganini ko'radi. */
  frameTakenAt: string | null;
  /** Kadr NISBATINING surati (`snapshots.width` — piksel EMAS). */
  frameWidth: number;
  initialZones: readonly CameraZone[];
  /** Kameralar ro'yxatiga qaytish — marshrutlash SAHIFADA (§ router-siz komponent). */
  onLeave: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const replace = useReplaceCameraZones(cameraId);

  const [zones, setZones] = useState<readonly EditorZone[]>(() =>
    toEditorZones(initialZones),
  );
  const [undoStack, setUndoStack] = useState<readonly (readonly EditorZone[])[]>(
    [],
  );
  const [redoStack, setRedoStack] = useState<readonly (readonly EditorZone[])[]>(
    [],
  );
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [focusedVertex, setFocusedVertex] = useState<number | null>(null);
  const [announcement, setAnnouncement] = useState("");
  /** Saqlash xatosi — SABAB + NIMA QILISH KERAK juftligi (D-02). */
  const [saveError, setSaveError] = useState<{
    cause: string;
    fix: string | null;
  } | null>(null);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [renderSize, setRenderSize] = useState(() => ({
    height: (FALLBACK_RENDER_WIDTH * frameHeight) / frameWidth,
    width: FALLBACK_RENDER_WIDTH,
  }));

  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const announceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const nextLocalId = useRef(0);

  /*
   * Kadr yuzasining EKRANDAGI o'lchami — nudge qadamining maxraji.
   * `ResizeObserver` jsdom'da yo'q, shuning uchun mavjudligi tekshiriladi
   * (`stall-map.tsx::subscribeToDesktop` naqshi): o'lchov bo'lmasa zaxira
   * qiymat qoladi va klaviatura baribir ishlaydi.
   */
  useEffect(() => {
    const node = surfaceRef.current;
    if (node === null || typeof ResizeObserver !== "function") return;

    const observer = new ResizeObserver((entries) => {
      const box = entries[0]?.contentRect;
      if (box === undefined || box.width <= 0 || box.height <= 0) return;
      setRenderSize({ height: box.height, width: box.width });
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(
    () => () => {
      if (announceTimer.current !== null) clearTimeout(announceTimer.current);
    },
    [],
  );

  /** Har o'zgarish — undo stekiga (chuqurlik 50, sessiyaga bog'liq). */
  function commit(next: readonly EditorZone[]): void {
    setUndoStack((stack) => [...stack, zones].slice(-UNDO_DEPTH));
    setRedoStack([]);
    setZones(next);
  }

  function announce(message: string): void {
    if (announceTimer.current !== null) clearTimeout(announceTimer.current);
    setAnnouncement(message);
  }

  /**
   * Koordinata e'loni — KECHIKTIRILGAN (§13.4).
   *
   * Har `pointermove` yoki har o'q bosilishida e'lon qilinsa skrinrider
   * bo'g'ilardi va foydalanuvchi hech nimani eshitmasdi.
   */
  function announceVertexLater(index: number, point: Pt): void {
    if (announceTimer.current !== null) clearTimeout(announceTimer.current);
    announceTimer.current = setTimeout(() => {
      setAnnouncement(
        t("cameraZones.vertexAnnounce", {
          index: index + 1,
          x: format.number(point[0], { maximumFractionDigits: 3 }),
          y: format.number(point[1], { maximumFractionDigits: 3 }),
        }),
      );
    }, ANNOUNCE_DEBOUNCE_MS);
  }

  function updatePolygon(zoneId: string, next: Poly): void {
    const current = zones.find((zone) => zone.id === zoneId);
    /*
     * ⚠ RAD ETILGAN AMAL — AYNAN O'SHA HAVOLA (05-03 kontrakti), ya'ni
     *   undo stekiga «hech nima qilmaydigan» qadam TUSHMAYDI.
     */
    if (current === undefined || Object.is(current.polygon, next)) return;
    commit(
      zones.map((zone) =>
        zone.id === zoneId ? { ...zone, polygon: next } : zone,
      ),
    );
  }

  function createZone(): void {
    if (zones.length >= MAX_ZONES_PER_CAMERA) {
      announce(t("cameraZones.maxZones", { max: MAX_ZONES_PER_CAMERA }));
      return;
    }

    /*
     * ⛔ MARKAZDAGI TO'RTBURCHAK — KLAVIATURA YO'LI (§13.4). «Bosib
     *    chizing» rejimi klaviatura foydalanuvchisiga taklif
     *    QILINMAYDI, ya'ni u YAGONA yaratish yo'li bo'lishi kerak —
     *    sichqonchali foydalanuvchi ham shu yo'ldan yuradi.
     */
    const polygon: Poly = [
      [0.5 - NEW_ZONE_HALF_WIDTH, 0.5 - NEW_ZONE_HALF_HEIGHT],
      [0.5 + NEW_ZONE_HALF_WIDTH, 0.5 - NEW_ZONE_HALF_HEIGHT],
      [0.5 + NEW_ZONE_HALF_WIDTH, 0.5 + NEW_ZONE_HALF_HEIGHT],
      [0.5 - NEW_ZONE_HALF_WIDTH, 0.5 + NEW_ZONE_HALF_HEIGHT],
    ];
    /*
     * ⚠ HISOBLAGICH, `crypto.randomUUID()` EMAS: identifikator faqat
     *   muharrir ichida yashaydi (`PUT` tanasiga TUSHMAYDI — versiya va
     *   `id` serverda hisoblanadi), ya'ni global noyoblik kerak emas va
     *   uni talab qilish testni muhit imkoniyatiga bog'lab qo'yardi.
     */
    nextLocalId.current += 1;
    const id = `new:${nextLocalId.current}`;
    commit([
      ...zones,
      { id, needsReview: false, polygon, stallCode: null, stallId: null },
    ]);
    setSelectedZoneId(id);
    setFocusedVertex(0);
    announce(t("cameraZones.zoneAdded"));
  }

  function undo(): void {
    if (undoStack.length === 0) return;
    const previous = undoStack[undoStack.length - 1];
    setUndoStack((stack) => stack.slice(0, -1));
    setRedoStack((stack) => [...stack, zones].slice(-UNDO_DEPTH));
    setZones(previous);
  }

  function redo(): void {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setRedoStack((stack) => stack.slice(0, -1));
    setUndoStack((stack) => [...stack, zones].slice(-UNDO_DEPTH));
    setZones(next);
  }

  const blocking = invalidZoneIds(
    zones.map(
      (zone): ListZone => ({
        id: zone.id,
        needsReview: zone.needsReview,
        polygon: zone.polygon,
        stallCode: zone.stallCode,
      }),
    ),
  );
  const withoutStall = zones.filter((zone) => zone.stallId === null);
  const unsavedCount = undoStack.length;
  const needsReview = zones.some((zone) => zone.needsReview);
  const saveBlocked = blocking.length > 0 || replace.isPending;

  async function save(): Promise<void> {
    if (saveBlocked) return;
    setSaveError(null);

    const payload: CameraZoneWriteInput[] = zones
      .filter(
        (zone): zone is EditorZone & { stallId: string } =>
          zone.stallId !== null,
      )
      .map((zone) => ({
        polygon: zone.polygon,
        sourceHeight: frameHeight,
        sourceWidth: frameWidth,
        stallId: zone.stallId,
      }));

    try {
      await replace.mutateAsync(payload);
      setUndoStack([]);
      setRedoStack([]);
      toast.success(t("cameraZones.toastSaved"));
      if (withoutStall.length > 0) {
        toast.warning(
          t("cameraZones.noStallWarning", { count: withoutStall.length }),
        );
      }
    } catch (cause) {
      /*
       * ⛔ Z-7: O'ZGARISHLAR YO'QOLMAYDI. Xato bloki chiqadi, qoralama
       *    holat esa TEGILMAYDI — admin tuzatib qayta bosishi mumkin.
       *
       * ⚠ XOM `detail` HECH QACHON EKRANGA CHIQMAYDI (T-05-13): u
       *   reyestrdan o'tkaziladi va noma'lum kod umumiy xabarga tushadi.
       */
      const view = zoneErrorView(
        cause instanceof ApiError ? cause.detail : null,
      );
      setSaveError(
        view === null
          ? { cause: t(marketErrorMessageKey(cause)), fix: null }
          : { cause: t(view.causeKey), fix: t(view.fixKey) },
      );
    }
  }

  const canvasZones: readonly CanvasZone[] = zones.map((zone) => ({
    id: zone.id,
    invalid: blocking.includes(zone.id),
    label: zone.stallCode ?? t("cameraZones.noStall"),
    polygon: zone.polygon,
  }));

  const listZones: readonly ListZone[] = zones.map((zone) => ({
    id: zone.id,
    needsReview: zone.needsReview,
    polygon: zone.polygon,
    stallCode: zone.stallCode,
  }));

  const selected = zones.find((zone) => zone.id === selectedZoneId) ?? null;

  return (
    <div className="flex flex-col gap-6">
      {/* --- Sarlavha va saqlash ---------------------------------------- */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          onClick={() => {
            if (unsavedCount > 0) {
              setLeaveOpen(true);
              return;
            }
            onLeave();
          }}
          size="sm"
          variant="ghost"
        >
          {t("cameraZones.backToCameras")}
        </Button>

        <div className="flex items-center gap-2">
          {unsavedCount > 0 ? (
            <span className="text-xs text-text-muted">
              {t("cameraZones.unsaved", { count: unsavedCount })}
            </span>
          ) : null}

          {/*
           * ⛔ SAHIFADAGI YAGONA AKSENT FONLI TUGMA (§10.3 №6).
           *
           * ⚠ `aria-disabled`, `disabled` EMAS (§13.3): `disabled` tugma
           *   fokus olmaydi va skrinrider uni o'qimaydi — «nega
           *   saqlanmayapti?» savoli javobsiz qolardi. Sabab esa
           *   ro'yxat ustidagi `role="alert"` blokida turadi.
           */}
          <Button
            aria-disabled={saveBlocked ? true : undefined}
            className={saveBlocked ? "opacity-60" : undefined}
            onClick={() => void save()}
            variant="default"
          >
            {replace.isPending
              ? t("cameraZones.saving")
              : t("cameraZones.saveZones")}
          </Button>
        </div>
      </div>

      {/*
       * ⚠ NISBAT LENTASI — `role="status"`, va u AVTOMATIK TO'G'RILAMAYDI
       *   (§6.8). Cho'zilganmi yoki kesilganmi — bilib bo'lmaydi;
       *   noto'g'ri tuzatish JIMGINA noto'g'ri hisob berardi. UI faqat
       *   ogohlantiradi.
       */}
      {needsReview ? (
        <p
          className="flex items-center gap-2 rounded-md bg-warning/20 p-3 text-sm text-text"
          role="status"
        >
          <TriangleAlert aria-hidden="true" className="size-4 shrink-0" />
          {t("cameraZones.aspectChanged")}
        </p>
      ) : null}

      {saveError === null ? null : (
        <div
          className="flex flex-col gap-1 rounded-md bg-danger/10 p-3 text-sm text-danger-text"
          role="alert"
        >
          <p className="text-xs font-semibold">
            {t("cameraZones.errorCauseLabel")}
          </p>
          <p>{saveError.cause}</p>
          {saveError.fix === null ? null : (
            <>
              <p className="text-xs font-semibold">
                {t("cameraZones.errorFixLabel")}
              </p>
              <p>{saveError.fix}</p>
            </>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        {/* --- (A) Kadr yuzasi ----------------------------------------- */}
        <div className="flex flex-col gap-2">
          <div ref={surfaceRef}>
            <ZoneCanvas
              aspectHeight={frameHeight}
              aspectWidth={frameWidth}
              focusedVertex={focusedVertex}
              frameHref={frameHref}
              onBackgroundPress={() => {
                setSelectedZoneId(null);
                setFocusedVertex(null);
              }}
              onInsertMidpoint={(edgeIndex) => {
                if (selected === null) return;
                updatePolygon(
                  selected.id,
                  insertMidpoint(selected.polygon, edgeIndex),
                );
                setFocusedVertex(edgeIndex + 1);
              }}
              onMoveVertex={(index, point) => {
                if (selected === null) return;
                updatePolygon(
                  selected.id,
                  moveVertex(selected.polygon, index, point),
                );
              }}
              onSelectZone={(zoneId) => {
                setSelectedZoneId(zoneId);
                setFocusedVertex(null);
              }}
              preview={[]}
              selectedZoneId={selectedZoneId}
              zones={canvasZones}
            />
          </div>

          {frameTakenAt === null ? null : (
            <p className="text-xs text-text-muted">
              {t("cameraZones.frameAt", {
                time: format.dateTime(new Date(frameTakenAt), {
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                  month: "2-digit",
                }),
              })}
            </p>
          )}

          {/*
           * ⛔ YAGONA DINAMIK JONLI HUDUD (§13.6). Ro'yxat unga MATN
           *    beradi (`onAnnounce`), o'zining hududini ochmaydi — aks
           *    holda bir vaqtda uchta faol hudud bo'lardi.
           */}
          <p className="sr-only" role="status">
            {announcement}
          </p>
        </div>

        {/* --- (B) Zonalar ro'yxati — OCHIQLIKNING ASOSIY YUZASI --------- */}
        <div className="flex flex-col gap-4">
          <ZoneList
            focusedVertex={focusedVertex}
            maxZones={MAX_ZONES_PER_CAMERA}
            onAnnounce={announce}
            onCreateZone={createZone}
            onDeleteVertex={(index) => {
              if (selected === null) return;
              updatePolygon(selected.id, deleteVertex(selected.polygon, index));
              setFocusedVertex(null);
            }}
            onFocusVertex={(index) => {
              setFocusedVertex(index);
              if (index !== null && selected !== null) {
                announceVertexLater(index, selected.polygon[index]);
              }
            }}
            onInsertVertex={(index) => {
              if (selected === null) return;
              updatePolygon(selected.id, insertMidpoint(selected.polygon, index));
              setFocusedVertex(index + 1);
            }}
            onMoveVertex={(index, point) => {
              if (selected === null) return;
              updatePolygon(
                selected.id,
                moveVertex(selected.polygon, index, point),
              );
              announceVertexLater(index, point);
            }}
            onSelectZone={(zoneId) => {
              setSelectedZoneId(zoneId);
              setFocusedVertex(null);
            }}
            renderHeight={renderSize.height}
            renderWidth={renderSize.width}
            selectedZoneId={selectedZoneId}
            zones={listZones}
          />

          {/*
           * ⚠ HAMMASI `secondary` — sahifadagi yagona aksent fonli tugma
           *   `[Zonalarni saqlash]` (§10.3 №6). 3-vazifada bu ikkita
           *   tugma `zone-toolbar.tsx` ga ko'chadi va yoniga qator
           *   yordamchilari qo'shiladi.
           */}
          <div className="flex gap-2">
            <Button
              aria-disabled={undoStack.length === 0 ? true : undefined}
              onClick={undo}
              size="sm"
              variant="secondary"
            >
              {t("cameraZones.undo")}
            </Button>
            <Button
              aria-disabled={redoStack.length === 0 ? true : undefined}
              onClick={redo}
              size="sm"
              variant="secondary"
            >
              {t("cameraZones.redo")}
            </Button>
          </div>
        </div>
      </div>

      {/* --- (D) Qamrov kartasi ----------------------------------------- */}
      <CoverageCard />

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("cameraZones.leaveAnyway")}
        description={t("cameraZones.unsavedBody", { count: unsavedCount })}
        onConfirm={() => {
          setLeaveOpen(false);
          onLeave();
        }}
        onOpenChange={setLeaveOpen}
        open={leaveOpen}
        title={t("cameraZones.unsavedTitle")}
      />
    </div>
  );
}
