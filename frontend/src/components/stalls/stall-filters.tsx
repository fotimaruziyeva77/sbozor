"use client";

import { FilterX } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { STALL_STATUSES } from "@/lib/api-types";
import type { StallFilters } from "@/lib/market-queries";
import {
  useCategoriesQuery,
  useStallsQuery,
  useZonesQuery,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Rasta reestrining filtrlari (UI-SPEC §8.3).
 *
 * HOLAT URL'DA, komponentda emas — `audit-filters.tsx` da o'rnatilgan naqsh.
 * Sabab bu ekranda yanada amaliyroq: bozor admini nazoratchiga "shu filtrga
 * qara" deb havola yuboradi va sahifa yangilanganda filtr yo'qolmaydi.
 *
 * PANEL HAM, RO'YXAT HAM `useStallFilters()` DAN O'QIYDI — holat prop bo'lib
 * uzatilmaydi, ya'ni ikkovi hech qachon ajralib qola olmaydi.
 * =============================================================================
 */

/**
 * URL parametrlari.
 *
 * `q` — YAGONA sekinlashtirilgan parametr. `throttleMs` nuqs'ning O'Z
 * mexanizmi (UI-SPEC §8.3 qarori): maxsus `useDebounce` hooki yozilmaydi
 * (yangi kod + yangi test yuzasi) va lodash qo'shilmaydi (yangi bog'liqlik).
 *
 * ⚠ NIMANI sekinlashtiradi: nuqs holatni DARHOL (optimistik) yangilaydi va
 * faqat BRAUZER TARIXIGA yozishni cheklaydi. Ya'ni natijalar terish bilan
 * birga yangilanadi (§6.9 ning "kod terish + Enter = karta ochiq" mezoni
 * aynan shuni talab qiladi), tarix esa 300 ms dan tez-tez yozilmaydi —
 * brauzerlarning History API chegarasi shu sababdan bor.
 *
 * ⚠ nuqs 2.9.2 `throttleMs` ni `limitUrlUpdates` foydasiga eskirgan deb
 * belgilaydi, lekin u ISHLAYDI va UI-SPEC kontrakti aynan shu nomni beradi.
 * Nom o'zgartirilsa spetsifikatsiya bilan kod ajralib ketardi.
 *
 * Qolgan uch parametr sekinlashtirilmaydi: ular TANLOV, terish emas.
 */
const stallFilterParsers = {
  q: parseAsString.withDefault("").withOptions({ throttleMs: 300 }),
  zone: parseAsString.withDefault(""),
  category: parseAsString.withDefault(""),
  status: parseAsString.withDefault(""),
};

const EMPTY_URL_FILTERS = { q: "", zone: "", category: "", status: "" };

/** Filtrlar + "filtr umuman qo'yilmaganmi?" (UI-SPEC §9.2 ikki bo'sh holati). */
export function useStallFilters(): {
  filters: StallFilters;
  isEmpty: boolean;
} {
  const [urlFilters] = useQueryStates(stallFilterParsers);

  return {
    filters: {
      q: urlFilters.q,
      zone: urlFilters.zone,
      category: urlFilters.category,
      status: urlFilters.status,
    },
    isEmpty: Object.values(urlFilters).every((value) => value === ""),
  };
}

export function StallFiltersPanel({
  onOpenStall,
}: {
  /** Aynan bitta natija topilganda kartani ochadi (§6.9). */
  onOpenStall: (stallId: string) => void;
}) {
  const t = useTranslations();
  const tStatus = useTranslations("stalls.status");
  const [urlFilters, setUrlFilters] = useQueryStates(stallFilterParsers);
  const { filters, isEmpty } = useStallFilters();

  const zonesQuery = useZonesQuery();
  const categoriesQuery = useCategoriesQuery();

  /*
   * ⚠ AYNI `queryKey`, ya'ni AYNI kesh yozuvi: `stall-list.tsx` ham shu
   * hookni shu filtrlar bilan chaqiradi. TanStack Query so'rovni
   * DEDUPLIKATSIYA qiladi — ikkinchi tarmoq so'rovi ketmaydi. Ro'yxatdan
   * natijani prop bilan yuqoriga uzatish esa ikkinchi haqiqat manbai
   * yaratardi.
   */
  const stallsQuery = useStallsQuery(filters);

  /*
   * §6.9 KONTRAKTI: "kod terish + Enter = karta ochiq" — o'lchanadigan
   * mezon; u 6-fazaning "≤3 bosish" kassir oqimidan bitta bosishni oladi.
   *
   * `refetch()` ATAYIN kutiladi va natija UNDAN o'qiladi. Muqobil variant —
   * "niyat" bayrog'ini holatda saqlab, so'rov tinchiganda effektda o'qish —
   * effekt ichida sinxron `setState` chaqirishga majbur qilardi (kaskadli
   * render; `react-hooks/set-state-in-effect`). Bu yerda esa Enter — aniq
   * foydalanuvchi amali, ya'ni bitta qo'shimcha so'rov oqlanadi va u
   * javobning AYNAN joriy `q` ga tegishli ekanini kafolatlaydi.
   */
  async function openSingleMatch() {
    const result = await stallsQuery.refetch();
    const items = result.data?.pages.flatMap((page) => page.items) ?? [];
    // AYNAN BITTA natija — ro'yxat oralig'isiz kartaga o'tiladi. Ikki va
    // undan ko'p natijada tanlovni foydalanuvchi qiladi.
    if (items.length === 1) onOpenStall(items[0].id);
  }

  return (
    <form
      className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void openSingleMatch();
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Field
          className="sm:col-span-2 lg:col-span-1"
          id="stall-q"
          label={t("stalls.searchPlaceholder")}
        >
          {/*
           * Uch atribut, bitta o'lchanadigan mezon (§6.9):
           *   `autoFocus`            — sahifa ochilishi bilan raqam teriladi;
           *   `inputMode="numeric"`  — telefonda raqam klaviaturasi ochiladi;
           *   `enterKeyHint="search"`— Enter tugmasi "qidirish" deb ko'rinadi.
           *
           * `autoFocus` bu yerda oqlanadi: sahifaning YAGONA maqsadi rasta
           * topish va boshqa hech qanday birlamchi kirish maydoni yo'q.
           */}
          <Input
            autoComplete="off"
            autoFocus
            enterKeyHint="search"
            id="stall-q"
            inputMode="numeric"
            onChange={(event) => void setUrlFilters({ q: event.target.value })}
            placeholder={t("stalls.searchPlaceholder")}
            type="search"
            value={urlFilters.q}
          />
        </Field>

        <Field id="stall-zone" label={t("stalls.zoneLabel")}>
          <Select
            id="stall-zone"
            onChange={(event) =>
              void setUrlFilters({ zone: event.target.value })
            }
            value={urlFilters.zone}
          >
            <option value="">{t("stalls.filterZoneAll")}</option>
            {/* D-16: zona nomi DB kontenti — tarjima qilinmaydi. */}
            {(zonesQuery.data?.items ?? []).map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field id="stall-category" label={t("stalls.categoryLabel")}>
          <Select
            id="stall-category"
            onChange={(event) =>
              void setUrlFilters({ category: event.target.value })
            }
            value={urlFilters.category}
          >
            <option value="">{t("stalls.filterCategoryAll")}</option>
            {/* D-16: toifa nomi DB kontenti — tarjima qilinmaydi. */}
            {(categoriesQuery.data?.items ?? []).map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field id="stall-status" label={t("stalls.statusLabel")}>
          <Select
            id="stall-status"
            onChange={(event) =>
              void setUrlFilters({ status: event.target.value })
            }
            value={urlFilters.status}
          >
            <option value="">{t("stalls.filterStatusAll")}</option>
            {/* Holat — enum, ya'ni bu YAGONA joyda tarjima qilinadi. */}
            {STALL_STATUSES.map((status) => (
              <option key={status} value={status}>
                {tStatus(status)}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <div>
        <Button
          disabled={isEmpty}
          onClick={() => void setUrlFilters(EMPTY_URL_FILTERS)}
          size="sm"
          variant="secondary"
        >
          <FilterX aria-hidden="true" />
          {t("stalls.clearFilters")}
        </Button>
      </div>
    </form>
  );
}
