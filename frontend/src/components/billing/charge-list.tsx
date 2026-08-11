"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { ChargeDetailDialog } from "@/components/billing/charge-detail-dialog";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { ChargeRow } from "@/lib/billing-charge-queries";
import { useCharges } from "@/lib/billing-charge-queries";
import { EMPTY_VENDOR_FILTERS, useVendorsQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * C BLOKI — YOZILGAN HISOBLAR VA QOLDIQ (§11.2, BILL-02, BILL-03).
 *
 * -----------------------------------------------------------------------
 * ⛔ O'RAM `{items}` EMAS — `{day, rows, charge_count, charged_soum}`
 * -----------------------------------------------------------------------
 * Server (06-08) va klient sxemasi (06-11) MOS; qatorlar `.rows` dan
 * o'qiladi. `ChargeList["rows"]` tipi mavjud, ya'ni `items` deb yozilgan
 * har qanday murojaat `tsc` da qizaradi — bu band jimgina o'tib keta
 * olmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ G-25 (b) NING YARMI SHU FAYLDA
 * -----------------------------------------------------------------------
 * Eng tashqi element `data-billing-content="charges"` chiqaradi va
 * ⛔ BU ATRIBUTNI `billing/page.tsx` HECH QACHON YOZMAYDI. Sabab
 * o'lchangan: G-25 ning eski shakli faqat `data-billing-block`
 * o'ramining atribut qiymatlarini ko'rardi, ya'ni bo'sh
 * `<div data-billing-block="charges" />` uni MUKAMMAL qondirardi va
 * BILL-02/03 chizilmagan holda faza YASHIL qaytardi.
 *
 * ⛔ ATRIBUT BO'SH HOLATDA HAM CHIQADI: bo'sh natija — NATIJA.
 *
 * -----------------------------------------------------------------------
 * ⛔ DL-3 NI SHU KOMPONENT OCHADI — VA BU SAHIFA EMAS
 * -----------------------------------------------------------------------
 * Dialog holati (`openCharge`) FAQAT ro'yxatga tegishli: u URL'da
 * yashamaydi (§4.4) va sahifaning boshqa bloklariga hech qanday ta'siri
 * yo'q. `occupancy/stall-day-list` + `StallDetailDialog` juftida dialog
 * SAHIFADA turadi, lekin u yerda dialog holati `?nocov=` bilan bir
 * sahifa holatida yashaydi — bu yerda esa uni sahifaga chiqarish
 * kompozitsiya taskining diffini kengaytirardi va `charge-detail-dialog`
 * ⛔ CHIZILMAGAN qolish xavfini tug'dirardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ BILL-03 — SAQLANGAN QOLDIQ NOMI HAM YO'Q
 * -----------------------------------------------------------------------
 * Qoldiq HISOBLANADIGAN ko'rinish (`outstanding_soum`), saqlangan ustun
 * emas. Taqiqlangan nomning O'ZI ham bu faylda uchramaydi: u paydo
 * bo'lgan zahoti keyingi ijrochi uni USTUNGA aylantirardi va hisob-kitob
 * ikki manbadan yashay boshlardi.
 * ⚠ Nom bu izohda LITERAL yozilmaydi — uning yo'qligi `grep` darvozasi
 *   bilan o'lchanadi (kodbaza konvensiyasi, `badge.tsx:24-26`).
 *
 * ⛔ SARALASH SERVERDA (`code_sort` — inson-raqamli: 2 < 10 < 100).
 *    Klientda qayta saralash IKKINCHI tartib qoidasi bo'lardi va uchala
 *    tilda boshqa natija berardi (2-fazadan meros qoida).
 *
 * ⛔ SOTUVCHI ISMI KLIENTDA JOIN QILINADI (§5.5, C-10): `GET /vendors`
 *    mavjud va AUDIT QILINGAN marshrut. Moliyaviy marshrutga ism maydoni
 *    QO'SHILMAYDI — aks holda `PERSONAL_ROUTES` reyestri o'sardi va
 *    keyingi ijrochi shu naqshni ko'chirardi.
 * =============================================================================
 */

/**
 * Ikkinchi summa ustuni KERAKMI — SOF FUNKSIYA (D-09).
 *
 * ⛔ QAROR JADVAL DARAJASIDA, qator darajasida EMAS: ustunlar to'plami
 *    barcha qatorlar uchun bitta bo'lishi shart. Bitta qatorda tuzatish
 *    bo'lsa, IKKALA ustun ham chiziladi va farq KO'RINADI — u tuzatish
 *    bo'lganini aytadi va tafsiloti DL-3 da ochiladi.
 *
 * ⚠ Hech qaysi qatorda farq bo'lmasa, ikkita bir xil ustun direktorni
 *   «nima farqi?» deb o'ylashga majburlardi — shuning uchun bitta ustun
 *   («Summa») qoladi.
 */
export function hasAdjustedRow(rows: readonly ChargeRow[]): boolean {
  return rows.some((row) => row.tariff_amount_soum !== row.amount_soum);
}

export function ChargeList({
  day,
  onGoToAnomalies,
}: {
  day: string;
  /** Bo'sh holat №5 ning keyingi qadami (§13.8). */
  onGoToAnomalies: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const charges = useCharges(day);
  const vendors = useVendorsQuery(EMPTY_VENDOR_FILTERS);

  /*
   * ⛔ DL-3 HOLATI — RO'YXATNIKI. URL'da emas (§4.4): tafsilotni
   *    ulashiladigan havolaga aylantirish uni sahifa holatidan marshrutga
   *    ko'chirardi va «orqaga» tugmasi dialogni qayta ochardi.
   */
  const [openCharge, setOpenCharge] = useState<ChargeRow | null>(null);

  const rows = charges.data?.rows ?? [];
  const showTariffColumn = hasAdjustedRow(rows);

  const vendorNames = new Map(
    (vendors.data?.pages ?? []).flatMap((page) =>
      page.items.map((vendor) => [vendor.id, vendor.full_name] as const),
    ),
  );

  return (
    /*
     * ⛔ G-25 (b): ATRIBUT ENG TASHQI ELEMENTDA va HAR HOLATDA —
     *    yuklanish, xato, bo'sh va to'la shoxlarda.
     */
    <div className="flex flex-col gap-3" data-billing-content="charges">
      <h2 className="text-sm font-semibold">{t("billing.chargesTitle")}</h2>

      {charges.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {charges.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {charges.data !== undefined && rows.length === 0 ? (
        /* ⛔ BO'SH HOLAT №5 (§13.8) — bo'sh `<div>` EMAS, MATN. */
        <EmptyState
          action={
            <Button onClick={onGoToAnomalies} size="sm" variant="secondary">
              {t("billing.goAnomalies")}
            </Button>
          }
          description={t("billing.emptyChargesHint")}
          title={t("billing.emptyCharges")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          {/* Native `table` — semantika tekin keladi (`stall-day-list` qoidasi). */}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("vendors.stallLabel")}
                </th>
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("stalls.vendorLabel")}
                </th>
                {showTariffColumn ? (
                  <th className="py-2 pr-3 font-medium" scope="col">
                    {t("billing.tariffAmount")}
                  </th>
                ) : null}
                <th className="py-2 pr-3 font-medium" scope="col">
                  {showTariffColumn
                    ? t("billing.chargeAmount")
                    : t("billing.amount")}
                </th>
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("billing.outstanding")}
                </th>
                <th className="py-2 font-medium" scope="col">
                  <span className="sr-only">{t("billing.detail")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {/* ⛔ Tartib SERVERDAN — bu yerda `sort()` YO'Q. */}
              {rows.map((row) => (
                <tr className="border-b border-border" key={row.charge_id}>
                  <td className="py-2 pr-3 font-semibold">{row.stall_code}</td>
                  <td className="py-2 pr-3 text-text-muted">
                    {vendorNames.get(row.vendor_id) ?? ""}
                  </td>
                  {showTariffColumn ? (
                    <td className="py-2 pr-3 font-mono tabular-nums">
                      {format.number(row.tariff_amount_soum)}
                    </td>
                  ) : null}
                  <td className="py-2 pr-3 font-mono tabular-nums">
                    {format.number(row.amount_soum)}
                  </td>
                  <td className="py-2 pr-3 font-mono tabular-nums">
                    {format.number(row.outstanding_soum)}
                  </td>
                  <td className="py-2">
                    <Button
                      onClick={() => setOpenCharge(row)}
                      size="sm"
                      variant="ghost"
                    >
                      {t("billing.detail")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/*
       * ⛔ DL-3 SHU YERDA CHIZILADI — sahifa faqat `<ChargeList>` ni
       *    biladi. Shuning uchun `charge-detail-dialog.tsx`
       *    ⛔ CHIZILMAGAN QOLA OLMAYDI.
       */}
      <ChargeDetailDialog
        charge={openCharge}
        onOpenChange={(open) => {
          if (!open) setOpenCharge(null);
        }}
      />
    </div>
  );
}
