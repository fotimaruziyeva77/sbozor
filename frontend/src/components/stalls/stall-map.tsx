"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import type { KeyboardEvent as ReactKeyboardEvent, FocusEvent } from "react";
import { useTranslations } from "next-intl";

import { StallCell } from "@/components/stalls/stall-cell";
import { StallMapLegend } from "@/components/stalls/stall-map-legend";
import type { ZoneBlock } from "@/components/stalls/stall-map-types";
import { DAY_STATE_KEYS, dayToneOf, toneOf } from "@/components/stalls/stall-tone";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useStallMapQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * SXEMATIK PLAN-XARITA — CSS Grid + memoizatsiyalangan tugmalar.
 *
 * Canvas kutubxonasi (RESEARCH Pattern 11) O'LCHOV bilan rad etilgan:
 * bu yerda render STATIK (D-19 drag-drop'ni rad etdi, D-20 faqat holat
 * uslubini beradi), ya'ni canvas'ning yagona ustunligi — kadr-bo'yicha
 * qayta chizish — umuman ishlatilmasdi. 1000 elementli React yangilanishi
 * memo bilan ~4 ms; narxi esa haqiqiy bo'lardi: SSR yo'q, a11y yo'q,
 * matn o'lchamlari qo'lda.
 *
 * VIRTUALIZATSIYA KUTUBXONASI HAM QO'SHILMAYDI: `content-visibility: auto`
 * (`.zone-block`, `globals.css`) brauzerga ekrandan tashqaridagi zonalarni
 * render qilmaslikni aytadi — nol bog'liqlik, nol JS.
 * =============================================================================
 */

const DESKTOP_QUERY = "(min-width: 768px)";

/** Yuklanish skeletidagi katak o'rinlari (§7.8: zona sarlavhasi + 24 katak). */
const SKELETON_SLOTS = Array.from({ length: 24 }, (_, slot) => slot);

function subscribeToDesktop(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const list = window.matchMedia(DESKTOP_QUERY);
  list.addEventListener("change", onChange);
  return () => list.removeEventListener("change", onChange);
}

function readIsDesktop(): boolean {
  // jsdom (va eski muhitlar) `matchMedia` ni bermaydi — "desktop" deb
  // hisoblanadi, ya'ni hamma zona ochiq va hech qanday kontent
  // yashirilmaydi. Fail-OPEN: bu joylashuv, xavfsizlik chegarasi emas.
  if (typeof window.matchMedia !== "function") return true;
  return window.matchMedia(DESKTOP_QUERY).matches;
}

/**
 * Ekran kengligi — TASHQI TIZIM, shuning uchun `useSyncExternalStore`.
 *
 * `useEffect` + `setState` varianti gidratatsiya nomuvofiqligini ham,
 * kaskadli renderni ham keltirib chiqarardi. Server surati `true`:
 * JS ishlamaydigan holatda ham barcha zonalar OCHIQ qoladi.
 */
function useIsDesktop(): boolean {
  return useSyncExternalStore(subscribeToDesktop, readIsDesktop, () => true);
}

export function StallMap({
  focusCode,
  onSelectStall,
}: {
  /** `/map?q=` dagi raqam: mos katak topiladi va fokuslanadi (§6.9). */
  focusCode: string;
  onSelectStall: (stallId: string) => void;
}) {
  const t = useTranslations();
  const mapQuery = useStallMapQuery();
  /*
   * ⛔ TO'LOV QATLAMI XARITANI KUTTIRMAYDI (MARKET-06).
   *
   * `dayLayer.isPending` bo'lganda grid INVENTAR ranglari bilan darhol
   * chiziladi va rang KEYIN qo'shiladi. Ikkinchi so'rovni kutish 1000
   * katakli ekranni ikki marta sekinlashtirardi va nosozlik holatida uni
   * BUTUNLAY bloklardi — holbuki inventar ma'lumoti allaqachon kelgan.
   *
   * ⛔ HUQUQ TEKSHIRUVI HOOK ICHIDA (D-C4): bu komponent «kim ko'radi?»
   *    degan savolga javob bermaydi va rollarni umuman o'qimaydi.
   */
  const dayLayer = useMapDayStatusQuery();
  const isDesktop = useIsDesktop();

  /** Zona -> shu zonadagi yagona `tabIndex={0}` katakning indeksi (§7.7). */
  const [activeIndex, setActiveIndex] = useState<Record<string, number>>({});

  /*
   * API javobi -> render kontrakti.
   *
   * ⚠ QAYTA SARALASH YO'Q (§7.3): zonalar nom bo'yicha, kataklar esa
   * inson-raqamli (`code_sort`) tartibda SERVERDAN keladi. Klient tomonda
   * saralash uchala tilda boshqa natija berardi va — jimgina — xarita
   * bilan reestrni ajratib yuborardi.
   */
  const zones: ZoneBlock[] = useMemo(
    () =>
      (mapQuery.data?.zones ?? []).map((zone) => ({
        id: zone.id,
        name: zone.name,
        cells: zone.cells.map((cell) => {
          /*
           * ⛔ TO'LOV MAYDONLARI KATAK MA'LUMOTINING ICHIDA (Pitfall 8):
           *   ular `StallCell` ga ALOHIDA prop bo'lib chiqmaydi va
           *   `byStallId` BARQAROR havola (`useMapDayStatusQuery`
           *   docstringi), ya'ni bu memo javob o'zgarganda AYNAN BIR
           *   MARTA qayta hisoblanadi.
           *
           * ⛔ QATLAM YO'Q BO'LGANDA INDEKS BO'SH: `dayTone` va
           *   `dayStateKey` `null` bo'lib qoladi va katak inventar
           *   tonida chiziladi — platsholder ham, «kutilmoqda» rangi ham
           *   qo'yilmaydi.
           */
          const day = dayLayer.byStallId.get(cell.id);
          return {
            id: cell.id,
            code: cell.code,
            tone: toneOf(cell),
            hasVendor: cell.has_vendor,
            dayTone: day === undefined ? null : dayToneOf(day.state),
            dayStateKey: day === undefined ? null : DAY_STATE_KEYS[day.state],
          };
        }),
      })),
    [mapQuery.data, dayLayer.byStallId],
  );

  // Barqaror havola — `StallCell` `memo` bilan o'ralgan va har renderda
  // yangi funksiya berilsa memoizatsiya butunlay ma'nosiz bo'lardi.
  const handleSelect = useCallback(
    (stallId: string) => onSelectStall(stallId),
    [onSelectStall],
  );

  const hasFocusMatch = useMemo(
    () =>
      focusCode === "" ||
      zones.some((zone) => zone.cells.some((cell) => cell.code === focusCode)),
    [focusCode, zones],
  );

  /*
   * Qidiruv: raqam terilganda katak topiladi, ochiladi va FOKUSLANADI
   * (§6.9 ning 3-bandi). Bu DOM bilan sinxronlash — effekt uchun to'g'ri
   * ish; hech qanday holat yangilanmaydi.
   */
  useEffect(() => {
    if (focusCode === "") return;
    const target = document.querySelector<HTMLButtonElement>(
      `[data-stall-code="${CSS.escape(focusCode)}"]`,
    );
    if (!target) return;
    // Zona mobil'da yig'ilgan bo'lishi mumkin — fokusdan oldin ochiladi,
    // aks holda `focus()` ko'rinmaydigan elementga tushardi.
    target.closest("details")?.setAttribute("open", "");
    target.scrollIntoView({ block: "nearest" });
    target.focus();
  }, [focusCode, zones]);

  if (mapQuery.isPending) {
    /*
     * Skeleton — zona sarlavhasi + 24 katak shakli (§7.8). Matnli
     * "Yuklanmoqda" layoutni yig'ib, keyin 1000 katak bilan yoyardi
     * (kuchli CLS). E'lon konteynerda BIR MARTA.
     */
    return (
      <div aria-busy="true" className="flex flex-col gap-4" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-6 w-40" />
        <div
          className="grid gap-2"
          style={{
            gridTemplateColumns: "repeat(auto-fill, minmax(2.75rem, 1fr))",
          }}
        >
          {/*
           * Skeletda pozitsiya kalit sifatida ishlatilishi XAVFSIZ: bu
           * ro'yxat qat'iy 24 elementli, o'zgarmaydi va qayta
           * tartiblanmaydi. Haqiqiy kataklarda esa u TAQIQLANGAN
           * (pastga qarang).
           */}
          {SKELETON_SLOTS.map((slot) => (
            <Skeleton className="aspect-square min-h-11 min-w-11" key={slot} />
          ))}
        </div>
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

  if (zones.length === 0) {
    return (
      <EmptyState
        description={t("map.emptyStateHint")}
        title={t("map.emptyState")}
      />
    );
  }

  function handleZoneFocus(zoneId: string, event: FocusEvent<HTMLDivElement>) {
    const buttons = Array.from(
      event.currentTarget.querySelectorAll("button"),
    );
    const focused = (event.target as HTMLElement).closest("button");
    const index = focused ? buttons.indexOf(focused) : -1;
    if (index < 0) return;
    // Funksional yangilanish + o'zgarmagan holatda AYNI obyektni qaytarish:
    // shunda faqat ikkita katak (eskisi va yangisi) qayta render bo'ladi.
    setActiveIndex((previous) =>
      previous[zoneId] === index ? previous : { ...previous, [zoneId]: index },
    );
  }

  /*
   * CHIZIQLI o'qlar, ikki o'lchovli `role="grid"` EMAS (§7.7 qarori):
   * joylashuv `auto-fill` bilan hosil bo'ladi, ya'ni "qator"ning hech
   * qanday ma'nosi yo'q (D-19 — koordinata saqlanmaydi). Yuqoriga/pastga
   * ni "ustundagi keyingi" deb talqin qilish foydalanuvchiga YOLG'ON
   * model berardi va oyna kengligi o'zgarganda javob o'zgarardi.
   */
  function handleZoneKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    const buttons = Array.from(
      event.currentTarget.querySelectorAll("button"),
    );
    const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (current < 0 || buttons.length === 0) return;

    let next = current;
    switch (event.key) {
      case "ArrowLeft":
      case "ArrowUp":
        next = Math.max(0, current - 1);
        break;
      case "ArrowRight":
      case "ArrowDown":
        next = Math.min(buttons.length - 1, current + 1);
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = buttons.length - 1;
        break;
      default:
        return;
    }

    event.preventDefault();
    const target = buttons[next];
    target.focus();
    target.scrollIntoView({ block: "nearest" });
  }

  return (
    <div className="flex flex-col gap-6">
      {/*
       * "Xaritani o'tkazib yuborish" (§7.7): 20 zona = 20 tab-stop va
       * ularning barchasidan o'tish klaviatura foydalanuvchisi uchun
       * jazo bo'lardi. Havola ko'rinmaydi, lekin FOKUS olganda paydo
       * bo'ladi.
       */}
      <a
        className="sr-only rounded-sm bg-surface px-3 py-2 text-sm font-semibold underline focus:not-sr-only"
        href="#stall-map-end"
      >
        {t("map.skipLink")}
      </a>

      {/*
       * TO'LOV QATLAMINING HALOL HOLATLARI — legendadan YUQORIDA.
       *
       * ⛔ UCHALASI HAM BIR-BIRINI ISTISNO QILADI va faqat BITTASI
       *   chiziladi. Ular `role="status"` bilan e'lon qilinadi (xato
       *   emas — `role="alert"` fokusni tortib, inventar ma'lumoti
       *   ko'rinib turgan ekranni «buzilgan» qilib ko'rsatardi).
       *
       * ⛔ HUQUQSIZ KO'RUVCHIDA BIRORTASI HAM YO'Q: `isEnabled` false
       *   bo'lganda xarita INVENTAR rejimida qoladi va u haqda hech nima
       *   AYTILMAYDI — mavjud bo'lmagan imkoniyatni e'lon qilish yolg'on
       *   affordans bo'lardi (D-C4).
       */}
      {dayLayer.isEnabled && dayLayer.isError ? (
        <p className="text-sm text-text-muted" role="status">
          {t("map.dayLayerError")}
        </p>
      ) : null}

      {dayLayer.status !== null && !dayLayer.status.market_active ? (
        <p
          className="rounded-sm bg-surface-muted px-3 py-2 text-sm text-text-muted"
          role="status"
        >
          {t("map.marketDraftNotice")}
        </p>
      ) : null}

      {dayLayer.status !== null &&
      dayLayer.status.market_active &&
      dayLayer.status.market_open === false ? (
        <p
          className="rounded-sm bg-surface-muted px-3 py-2 text-sm text-text-muted"
          role="status"
        >
          {t("map.marketClosedNotice")}
        </p>
      ) : null}

      {/*
       * ⛔ TO'LOV SATRLARI FAQAT QATLAM CHINDAN CHIZILGANDA: javob kelgan
       *   VA bozor qoralama emas. Qoralama bozorda birorta katak rang
       *   olmaydi, ya'ni legenda tushuntiradigan hech nima yo'q.
       */}
      <StallMapLegend
        showPaymentStates={
          dayLayer.status !== null && dayLayer.status.market_active
        }
      />

      {focusCode !== "" && !hasFocusMatch ? (
        <p className="text-sm text-text-muted" role="status">
          {t("map.notFound")}
        </p>
      ) : null}

      {/*
       * Mobil zona-sakrash chiplari (§7.8). Oddiy langar havolalar —
       * nol JS, `min-h-11` barmoq nishoni.
       * D-16: zona nomlari DB kontenti — tarjima qilinmaydi.
       */}
      <nav
        aria-label={t("stalls.zoneLabel")}
        className="sticky top-0 z-10 -mx-1 flex gap-2 overflow-x-auto bg-bg/95 px-1 py-2 md:hidden"
      >
        {zones.map((zone) => (
          <a
            className="inline-flex min-h-11 shrink-0 items-center rounded-md border border-border-ui px-3 text-sm whitespace-nowrap"
            href={`#zone-${zone.id}`}
            key={zone.id}
          >
            {zone.name}
          </a>
        ))}
      </nav>

      {zones.map((zone, zoneIndex) => (
        <section
          aria-label={t("map.zoneLabel", { name: zone.name })}
          className="zone-block"
          id={`zone-${zone.id}`}
          key={zone.id}
          role="group"
        >
          {/*
           * `<details>`: mobil'da faqat BIRINCHI zona ochiq (~8700px
           * skrollning oldini oladi), `>=768px` da hammasi doim ochiq.
           */}
          <details className="flex flex-col gap-3" open={isDesktop || zoneIndex === 0}>
            <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-lg font-semibold">
              {/* D-16: zona nomi DB kontenti — tarjima qilinmaydi. */}
              {zone.name}
              <span className="text-sm font-normal text-text-muted">
                {t("map.zoneStallCount", { count: zone.cells.length })}
              </span>
            </summary>

            <div
              className="mt-3 grid gap-2"
              onFocus={(event) => handleZoneFocus(zone.id, event)}
              onKeyDown={handleZoneKeyDown}
              style={{
                gridTemplateColumns: "repeat(auto-fill, minmax(2.75rem, 1fr))",
              }}
            >
              {zone.cells.map((cell, cellIndex) => (
                <StallCell
                  categoryName={null}
                  cell={cell}
                  /*
                   * Kalit — rastaning O'Z identifikatori. Massivdagi
                   * POZITSIYANI kalit qilish TAQIQLANGAN: kod tartibi
                   * o'zgarganda (yangi rasta qo'shildi, biri yopildi)
                   * React noto'g'ri katakni qayta ishlatardi va fokus
                   * boshqa rastaga sakrardi. Taqiqning literal shakli
                   * bu yerda yozilmaydi — u mexanik grep darvozasi bilan
                   * qulflangan (kodbaza konvensiyasi).
                   */
                  key={cell.id}
                  onSelect={handleSelect}
                  tabIndex={
                    cellIndex === (activeIndex[zone.id] ?? 0) ? 0 : -1
                  }
                  vendorName={null}
                  zoneName={zone.name}
                />
              ))}
            </div>
          </details>
        </section>
      ))}

      <div id="stall-map-end" tabIndex={-1} />
    </div>
  );
}
