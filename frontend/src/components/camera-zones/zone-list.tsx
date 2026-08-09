"use client";

import { ChevronDown, ChevronRight, Trash2, TriangleAlert } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/cn";
import {
  isSelfIntersecting,
  MAX_VERTICES_PER_ZONE,
  MIN_VERTICES,
} from "@/lib/zone-geometry";
import type { Poly, Pt } from "@/lib/zone-geometry";
import { zoneErrorView } from "@/lib/zone-errors";

/*
 * =============================================================================
 * ⛔⛔ OCHIQLIKNING ASOSIY YUZASI — SVG EMAS, SHU RO'YXAT (§13.4).
 *
 * Sabab bitta jumlada: KADR USTIGA BOSISH KLAVIATURA BILAN BAJARILMAYDI.
 * Chizish faqat sichqoncha bilan bo'lsa, klaviatura foydalanuvchisi bu
 * ekrandan BUTUNLAY chiqarib tashlanadi — WCAG 2.1.1 ning to'g'ridan-
 * to'g'ri buzilishi. Shuning uchun ochiqlik daraxti ro'yxatda yashaydi,
 * SVG esa uning ko'zgusi (`aria-hidden="true"`).
 *
 * ⛔ BU RO'YXAT MUQOBIL EMAS, BIRLAMCHI. SVG'dagi tepa nishoni 22 px va
 *   u WCAG 2.5.8 ning 24×24 minimumiga YETMAYDI (ongli chegirma: 44 px
 *   ushlagichlar qo'shni rastalarda ustma-ust tushardi). Kompensatsiya
 *   MAJBURIY va u aynan shu yerda: har tepa tugmasi TO'LIQ 44 px
 *   (`min-h-11 min-w-11`).
 *
 * -----------------------------------------------------------------------
 * ⛔ ROVING TABINDEX — MAJBURIY (WCAG 2.1.2, T-05-41)
 * -----------------------------------------------------------------------
 * 60 zona × (1 + 12 tepa) = 780 gacha fokuslanadigan element. Har biri
 * alohida tab to'xtashi bo'lsa, klaviatura foydalanuvchisi ro'yxatdan
 * CHIQIB KETA OLMAYDI — ta'rif bo'yicha klaviatura tuzog'i. Shuning
 * uchun BUTUN RO'YXAT uchun BITTA to'xtash: faol element `tabIndex={0}`,
 * qolganlari `-1`.
 *
 * ⚠ FAOL ELEMENT ICHKI HOLAT EMAS, PROPLARDAN HOSILA (`selectedZoneId` +
 *   `focusedVertex`). Ikkinchi holat manbai bo'lsa, kadrda tanlangan
 *   poligon bilan ro'yxatdagi fokus bir kun ajralib ketardi va bu faqat
 *   skrinriderda ko'rinardi.
 *
 * ⛔ UMUMIY ARIA KONTEYNER ROLI QO'YILMAYDI. `<ul>`/`<li>`/`<button>`
 *   semantikasi yetadi — `capture-grid.tsx:16-32` ning AYNAN o'sha
 *   qarori: native semantika skrinriderda kuchliroq va u indeks
 *   atributlarini qo'lda yuritishni talab qilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⚠ O'Q TUGMALARI SILJITADI, KO'CHIRMAYDI — VA BU ATAYIN (§13.4)
 * -----------------------------------------------------------------------
 * Ro'yxatda o'qlar odatda fokusni ko'chiradi. Bu yerda SILJITISH asosiy
 * amal: tepa tanlangandan keyin foydalanuvchi 90% vaqt uni KO'CHIRISHGA
 * harakat qiladi. Fokus ko'chirish `PageUp`/`PageDown` va `Home`/`End` ga
 * berilgan, va KO'RINADIGAN ko'rsatma (`cameraZones.moveHint`) ro'yxat
 * tepasida DOIM turadi — `<details>` ichida emas.
 * =============================================================================
 */

/** Bir bosishdagi siljish — RENDER PIKSELI (§6.5). */
export const NUDGE_STEP = 1;

/** `Shift` bilan — o'n barobar. */
export const NUDGE_FAST_STEP = 10;

export type ListZone = {
  id: string;
  /** Rasta kodi yoki `null` — biriktirilmagan zona (u ham SAQLANADI). */
  stallCode: string | null;
  /** Kadr nisbati o'zgargan — FAKT, avtomatik to'g'rilash YO'Q (§6.8). */
  needsReview: boolean;
  polygon: Poly;
};

/**
 * Saqlashni to'sadigan zonalar — SOF FUNKSIYA.
 *
 * ⛔ O'ZI BILAN KESISHGAN POLIGON SAQLANMAYDI. Sabab `zone-geometry.ts`
 *    da: bunday poligon zona kutubxonasida ANIQLANMAGAN natija beradi,
 *    ya'ni JIMGINA NOTO'G'RI HISOB — xato xabari yo'q, poligon ekranda
 *    ko'rinadi, lekin bandlik boshqa maydondan o'lchanadi va u bevosita
 *    billing'ga o'tadi.
 *
 * ⚠ KLIENTDAGI TEKSHIRUV QULAYLIK, XAVFSIZLIK CHEGARASI EMAS: ishonch
 *   manbai serverda (`validate_polygon()`, 05-06). Bu yerdagisi adminga
 *   xatoni DARHOL, saqlashni kutmasdan ko'rsatadi.
 */
export function invalidZoneIds(
  zones: readonly ListZone[],
): readonly string[] {
  return zones
    .filter((zone) => isSelfIntersecting(zone.polygon))
    .map((zone) => zone.id);
}

/**
 * O'q tugmasi -> yangi tepa joyi. SOF FUNKSIYA.
 *
 * ⚠ QADAM RENDER PIKSELIDA, normalangan birlikda EMAS. `1 / renderHeight`
 *   — ekrandagi aynan bitta piksel; normalangan doimiy qadam esa keng
 *   kadrda katta, tor kadrda kichik siljish berardi va «bir bosish = bir
 *   piksel» va'dasi yolg'on bo'lardi.
 *
 * ⛔ O'LCHAM NOL BO'LSA `null`: `1/0` `Infinity` beradi va tepa
 *    `clamp01` dan keyin BURCHAKKA sakrardi — ya'ni o'lchanmagan
 *    konteynerda bitta tugma bosish poligonni buzardi. Bu holat real:
 *    birinchi renderda `ResizeObserver` hali ishlamagan bo'ladi.
 */
export function nudgedPoint(
  point: Pt,
  key: string,
  shiftKey: boolean,
  renderWidth: number,
  renderHeight: number,
): Pt | null {
  if (renderWidth <= 0 || renderHeight <= 0) return null;

  const step = shiftKey ? NUDGE_FAST_STEP : NUDGE_STEP;
  const dx = step / renderWidth;
  const dy = step / renderHeight;

  switch (key) {
    case "ArrowUp":
      return [point[0], point[1] - dy];
    case "ArrowDown":
      return [point[0], point[1] + dy];
    case "ArrowLeft":
      return [point[0] - dx, point[1]];
    case "ArrowRight":
      return [point[0] + dx, point[1]];
    default:
      return null;
  }
}

export function ZoneList({
  focusedVertex,
  maxZones,
  onAnnounce,
  onCreateZone,
  onDeleteVertex,
  onFocusVertex,
  onInsertVertex,
  onMoveVertex,
  onSelectZone,
  renderHeight,
  renderWidth,
  selectedZoneId,
  zones,
}: {
  focusedVertex: number | null;
  maxZones: number;
  /** Yagona jonli hudud muharrirda — ro'yxat unga MATN beradi (§13.6). */
  onAnnounce: (message: string) => void;
  onCreateZone: () => void;
  onDeleteVertex: (index: number) => void;
  onFocusVertex: (index: number | null) => void;
  /** Fokusdagi tepadan KEYIN yangi tepa (qirra o'rtasiga). */
  onInsertVertex: (index: number) => void;
  onMoveVertex: (index: number, point: Pt) => void;
  onSelectZone: (zoneId: string | null) => void;
  /** Kadr yuzasining EKRANDAGI balandligi (px) — nudge qadamining maxraji. */
  renderHeight: number;
  /** Kadr yuzasining EKRANDAGI kengligi (px). */
  renderWidth: number;
  selectedZoneId: string | null;
  zones: readonly ListZone[];
}) {
  const t = useTranslations();
  const format = useFormatter();

  const blocking = new Set(invalidZoneIds(zones));
  const selected = zones.find((zone) => zone.id === selectedZoneId) ?? null;

  /*
   * ⚠ FAOL ELEMENT PROPLARDAN HOSILA (yuqoridagi izoh). Tanlangan zona
   *   bo'lmasa birinchi zona to'xtashni oladi, ya'ni ro'yxat HAR DOIM
   *   aynan bitta tab to'xtashiga ega — hatto hech nima tanlanmaganda
   *   ham.
   */
  const activeKey =
    selected !== null && focusedVertex !== null
      ? `v:${selected.id}:${focusedVertex}`
      : selected !== null
        ? `z:${selected.id}`
        : zones.length > 0
          ? `z:${zones[0].id}`
          : "";

  function zoneLabel(zone: ListZone): string {
    const name = zone.stallCode ?? t("cameraZones.noStall");
    return `${name} · ${t("cameraZones.vertices")}: ${zone.polygon.length}`;
  }

  function coordinate(value: number): string {
    return format.number(value, {
      maximumFractionDigits: 3,
      minimumFractionDigits: 3,
    });
  }

  function vertexLabel(index: number, point: Pt): string {
    return `${t("cameraZones.vertex", { index: index + 1 })} · ${coordinate(
      point[0],
    )} · ${coordinate(point[1])}`;
  }

  function handleVertexKeyDown(
    event: ReactKeyboardEvent<HTMLButtonElement>,
    index: number,
    polygon: Poly,
  ): void {
    const moved = nudgedPoint(
      polygon[index],
      event.key,
      event.shiftKey,
      renderWidth,
      renderHeight,
    );
    if (moved !== null) {
      event.preventDefault();
      onMoveVertex(index, moved);
      return;
    }

    switch (event.key) {
      case "Home":
        event.preventDefault();
        onFocusVertex(0);
        return;
      case "End":
        event.preventDefault();
        onFocusVertex(polygon.length - 1);
        return;
      case "PageUp":
        event.preventDefault();
        onFocusVertex(Math.max(0, index - 1));
        return;
      case "PageDown":
        event.preventDefault();
        onFocusVertex(Math.min(polygon.length - 1, index + 1));
        return;
      case "Enter":
        /*
         * Qirra o'rtasiga tepa — sichqonchadagi «qirra doirasini bosish»
         * ning klaviatura yo'li. Chegara to'lgan bo'lsa sabab AYTILADI:
         * jim rad etish «tugma buzuq» taassurotini berardi.
         */
        event.preventDefault();
        if (polygon.length >= MAX_VERTICES_PER_ZONE) {
          onAnnounce(
            t("cameraZones.maxVertices", { max: MAX_VERTICES_PER_ZONE }),
          );
          return;
        }
        onInsertVertex(index);
        return;
      case "Delete":
      case "Backspace":
        event.preventDefault();
        if (polygon.length <= MIN_VERTICES) {
          onAnnounce(t("cameraZones.minVertices"));
          return;
        }
        onDeleteVertex(index);
        return;
      case "Escape":
        event.preventDefault();
        onFocusVertex(null);
        return;
      default:
    }
  }

  const blockingView = zoneErrorView("zone_polygon_self_intersecting");
  const blockingId = "camera-zones-blocking-reason";

  return (
    <section className="flex flex-col gap-3" aria-label={t("cameraZones.zones")}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{t("cameraZones.zones")}</h2>
        {/* `7 / 12` naqshi — 4-fazadagi `slot-editor.tsx` hisoblagichi. */}
        <Badge className="font-mono" tone="muted">
          {t("cameraZones.zonesUsage", { max: maxZones, used: zones.length })}
        </Badge>
      </div>

      {/*
       * ⚠ KO'RSATMA DOIM KO'RINADI va `<details>` ichida EMAS (§13.4):
       *   o'q tugmalarining odatdagidan boshqa vazifasi bor, ya'ni uni
       *   yashirish foydalanuvchini taxmin qilishga majburlardi.
       */}
      <p className="text-xs text-text-muted">{t("cameraZones.moveHint")}</p>

      {/*
       * ⛔ SAQLASHNI TO'SUVCHI SABAB — `role="alert"`, chunki u
       *    foydalanuvchining amalidan KEYIN paydo bo'ladigan YANGI
       *    hodisa (§13.6). Sabab + nima qilish kerak juftligi — D-02.
       */}
      {blocking.size > 0 && blockingView !== null ? (
        <div
          className="flex flex-col gap-2 rounded-md bg-danger/10 p-3 text-danger-text"
          id={blockingId}
          role="alert"
        >
          <p className="text-xs font-semibold">
            {t("cameraZones.errorCauseLabel")}
          </p>
          <p className="text-sm">{t(blockingView.causeKey)}</p>
          <p className="text-xs font-semibold">
            {t("cameraZones.errorFixLabel")}
          </p>
          <p className="text-sm">{t(blockingView.fixKey)}</p>
        </div>
      ) : null}

      {zones.length === 0 ? (
        /*
         * Z-3 — bo'sh holat RO'YXAT ICHIDA, kadr yuzasi o'rnida emas:
         * kadr bo'sh emas, u kadrni ko'rsatadi (§8.2).
         */
        <EmptyState
          action={
            <button
              className="min-h-11 rounded-md border border-border bg-surface px-4 text-sm font-semibold hover:bg-surface-muted"
              onClick={onCreateZone}
              type="button"
            >
              {t("cameraZones.newZone")}
            </button>
          }
          description={t("cameraZones.emptyNoZonesHint")}
          title={t("cameraZones.emptyNoZones")}
        />
      ) : (
        <ul className="flex flex-col gap-1">
          {zones.map((zone) => {
            const isSelected = zone.id === selectedZoneId;
            const isBlocking = blocking.has(zone.id);
            return (
              <li key={zone.id}>
                <button
                  aria-current={isSelected ? "true" : undefined}
                  /*
                   * ⚠ `aria-selected` ISHLATILMAYDI: u faqat `option`,
                   *   `tab`, `row`, `gridcell` rollarida yaroqli va
                   *   oddiy tugmada u NOTO'G'RI ARIA bo'lardi. Umumiy
                   *   konteyner roli esa ATAYIN qo'yilmagan (yuqoridagi
                   *   izoh), ya'ni to'g'ri atribut — `aria-current`.
                   */
                  aria-expanded={isSelected}
                  /*
                   * ⚠⚠ `aria-invalid` ISHLATILMAYDI — VA BU O'LCHANGAN.
                   *
                   *   §6.6 aynan shu atributni ko'rsatadi, lekin ARIA
                   *   spetsifikatsiyasi uni `button` rolida
                   *   QO'LLAB-QUVVATLAMAYDI (u kiritma vidjetlari
                   *   uchun) va `jsx-a11y/role-supports-aria-props`
                   *   buni ogohlantirish bilan fosh qildi. Yaroqsiz
                   *   ARIA — «bor, lekin ishlamaydigan» himoya: kod
                   *   ko'rikda to'g'ri ko'rinardi, skrinrider esa uni
                   *   umuman e'lon qilmasdi.
                   *
                   *   To'g'ri shakl — `aria-describedby`: fokus
                   *   ayblanuvchi zonaga tushganda SABAB o'qiladi.
                   *   Rang (§10.4) esa yagona signal emas — kadrda
                   *   punktir, ro'yxatda esa shu tavsif bor.
                   */
                  aria-describedby={isBlocking ? blockingId : undefined}
                  aria-label={zoneLabel(zone)}
                  className={cn(
                    "flex min-h-11 w-full items-center gap-2 rounded-md px-2 text-left text-sm",
                    isSelected ? "bg-surface-muted" : "hover:bg-surface-muted",
                    isBlocking ? "text-danger-text" : null,
                  )}
                  onClick={() => onSelectZone(isSelected ? null : zone.id)}
                  tabIndex={activeKey === `z:${zone.id}` ? 0 : -1}
                  type="button"
                >
                  {isSelected ? (
                    <ChevronDown aria-hidden="true" className="size-4 shrink-0" />
                  ) : (
                    <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
                  )}
                  <span className="min-w-0 flex-1 truncate">
                    {zone.stallCode ?? t("cameraZones.noStall")}
                  </span>
                  {zone.stallCode === null ? (
                    <Badge tone="warning">{t("cameraZones.noStall")}</Badge>
                  ) : null}
                  {zone.needsReview ? (
                    <Badge tone="warning">
                      <TriangleAlert aria-hidden="true" className="mr-1 size-3" />
                      {t("cameraZones.needsReview")}
                    </Badge>
                  ) : null}
                </button>

                {isSelected ? (
                  <ul className="mt-1 flex flex-col gap-1 border-l border-border pl-3">
                    {zone.polygon.map((point, index) => {
                      const atMinimum = zone.polygon.length <= MIN_VERTICES;
                      return (
                        <li className="flex items-center gap-1" key={index}>
                          {/*
                           * ⛔ TO'LIQ 44 px — SVG dagi 22 px nishonning
                           *    KOMPENSATSIYASI (§6.4). Bu o'lcham
                           *    muzokara qilinmaydi.
                           */}
                          <button
                            aria-label={vertexLabel(index, point)}
                            className={cn(
                              "flex min-h-11 min-w-11 flex-1 items-center rounded-md px-2 text-left font-mono text-xs",
                              focusedVertex === index
                                ? "bg-surface-muted"
                                : "hover:bg-surface-muted",
                            )}
                            onClick={() => onFocusVertex(index)}
                            onFocus={() => onFocusVertex(index)}
                            onKeyDown={(event) =>
                              handleVertexKeyDown(event, index, zone.polygon)
                            }
                            tabIndex={
                              activeKey === `v:${zone.id}:${index}` ? 0 : -1
                            }
                            type="button"
                          >
                            {t("cameraZones.vertex", { index: index + 1 })}
                          </button>

                          {/*
                           * ⚠ `aria-disabled`, `disabled` EMAS (§13.3):
                           *   `disabled` tugma fokus olmaydi va
                           *   skrinrider uni umuman o'qimaydi — «nega
                           *   bosilmayapti?» javobsiz qolardi.
                           *
                           * ⚠ `tabIndex={-1}` ATAYIN: bu tugma tepani
                           *   o'chirishning SICHQONCHA yo'li;
                           *   KLAVIATURA yo'li — fokusdagi tepada
                           *   `Delete`. Ikkalasi ham mavjud, ya'ni
                           *   WCAG 2.1.1 bajariladi, lekin tab
                           *   to'xtashi bittaligicha qoladi (2.1.2).
                           */}
                          <button
                            aria-disabled={atMinimum ? true : undefined}
                            aria-label={`${t("cameraZones.removeVertex")}: ${t(
                              "cameraZones.vertex",
                              { index: index + 1 },
                            )}`}
                            className={cn(
                              "flex size-11 shrink-0 items-center justify-center rounded-md hover:bg-surface-muted",
                              atMinimum ? "opacity-60" : null,
                            )}
                            onClick={() => {
                              if (atMinimum) {
                                onAnnounce(t("cameraZones.minVertices"));
                                return;
                              }
                              onDeleteVertex(index);
                            }}
                            tabIndex={-1}
                            type="button"
                          >
                            <Trash2 aria-hidden="true" className="size-4" />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
