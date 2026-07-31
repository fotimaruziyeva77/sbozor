"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { CalendarPlus, Ellipsis, Pencil, UserMinus } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { AssignmentDialog } from "@/components/vendors/assignment-dialog";
import type { AssignmentMode } from "@/components/vendors/assignment-dialog";
import { VendorDialog } from "@/components/vendors/vendor-dialog";
import type { VendorListItem } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useVendorsQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * Sotuvchilar reestri — zich karta qatori (UI-SPEC §8.1), jadval EMAS.
 *
 * AUDIT BILDIRISHI BU YERDA TAKRORLANMAYDI (§8.6). U ekran boshida, bitta
 * `<p>` bo'lib `vendors/page.tsx` da chiqadi va `vendors.auditNotice`
 * kalitining YAGONA render joyi o'sha. Sabab: audit RO'YXAT O'QISHINI
 * yozadi, har qatorni emas — qator-bo'yicha belgi mexanizmni noto'g'ri
 * tasvirlardi va takroriy bildirish shovqinga aylanardi. Keyingi ishlovchi
 * uni kartaga ko'chirmasin.
 *
 * TELEFON MASKALANMAYDI (§8.6 5-sabab). Server raqamni ALLAQACHON yuborgan,
 * ya'ni klientdagi yulduzcha hech kimdan hech narsani yashirmaydi —
 * xavfsizlik teatri. Haqiqiy himoya uch qatlamda: RLS, `VENDOR_VIEW`
 * huquqi va o'qish auditi. Ustiga raqam operatsion jihatdan zarur (admin
 * sotuvchiga qo'ng'iroq qiladi), shuning uchun u `tel:` havolasi.
 * Bu qaror `vendor-list.test.tsx` da regressiya testi bilan qulflangan.
 *
 * SO'ROV QATLAMI: faqat `market-queries.ts` (02-13). Bu komponent HTTP
 * qatlamiga TO'G'RIDAN-TO'G'RI tegmaydi: biriktirish mutatsiyasi bir vaqtda
 * beshta keshni eskirtiradi (`ASSIGNMENT_SIDE_EFFECTS`) va o'sha bog'lanish
 * grafigi bitta modulda turishi kerak — aks holda "bittasini unutish"
 * xatosi kafolatlanadi.
 *
 * ⚠ Bu qoida MEXANIK grep darvozasi bilan qulflangan, shuning uchun
 * taqiqlangan funksiyaning NOMI bu izohda ham literal yozilmaydi (02-08 da
 * o'rnatilgan konvensiya — darvoza o'z-o'ziga qarshi turmasin).
 * =============================================================================
 */

/**
 * Qidiruv satri URL'da (`?q=`).
 *
 * `throttleMs: 300` — nuqs'ning O'Z mexanizmi (UI-SPEC §8.3 qarori): maxsus
 * `useDebounce` hooki yozilmaydi (yangi kod, yangi test yuzasi) va lodash
 * qo'shilmaydi (yangi bog'liqlik). Holat URL'da bo'lgani uchun filtrlangan
 * ko'rinishni havola sifatida yuborish mumkin va sahifa yangilanganda
 * qidiruv yo'qolmaydi.
 */
const vendorFilterParsers = {
  q: parseAsString.withDefault("").withOptions({ throttleMs: 300 }),
};

/** Skeleton qatorlari — ro'yxatning haqiqiy shakliga yaqin (§9.1). */
const SKELETON_ROWS = [0, 1, 2, 3, 4];

type PendingAssignment = { mode: AssignmentMode; vendor: VendorListItem };

export function VendorList({
  canManage,
  createOpen,
  onCreateOpenChange,
}: {
  canManage: boolean;
  /**
   * Yaratish dialogining holati sahifada yashaydi (birlamchi CTA sarlavha
   * yonida turadi), dialogning O'ZI esa shu yerda — §8.6 bildirishi
   * sahifada dialogsiz qolishi uchun.
   */
  createOpen: boolean;
  onCreateOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations();
  const [urlFilters, setUrlFilters] = useQueryStates(vendorFilterParsers);
  const vendorsQuery = useVendorsQuery({ q: urlFilters.q });

  const [editing, setEditing] = useState<VendorListItem | null>(null);
  const [assignment, setAssignment] = useState<PendingAssignment | null>(null);

  const isFiltered = urlFilters.q !== "";
  const items = vendorsQuery.data?.pages.flatMap((page) => page.items) ?? [];

  let content: ReactNode;

  if (vendorsQuery.isPending) {
    /*
     * `aria-busy` va e'lon KONTEYNERDA bir marta beriladi — `Skeleton`
     * bloklarining o'zi `aria-hidden` (§9.1), aks holda skrinrider
     * "Yuklanmoqda" ni besh marta o'qirdi.
     */
    content = (
      <div aria-busy="true" className="flex flex-col gap-3" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {SKELETON_ROWS.map((row) => (
          <Skeleton className="h-20 rounded-lg" key={row} />
        ))}
      </div>
    );
  } else if (vendorsQuery.isError) {
    content = (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(vendorsQuery.error))}
      </p>
    );
  } else if (items.length === 0) {
    /*
     * IKKI XIL BO'SH HOLAT AJRATILADI (§9.2): "hech kim yo'q" ning keyingi
     * qadami — sotuvchi qo'shish, "filtr topmadi" niki — qidiruvni
     * tozalash. Bitta matn ikkalasiga ham xizmat qila olmasdi.
     */
    content = isFiltered ? (
      <EmptyState
        action={
          <Button
            onClick={() => void setUrlFilters({ q: "" })}
            variant="secondary"
          >
            {t("vendors.clearSearch")}
          </Button>
        }
        description={t("vendors.emptyFilteredHint")}
        title={t("vendors.emptyFiltered")}
      />
    ) : (
      <EmptyState
        action={
          canManage ? (
            <Button onClick={() => onCreateOpenChange(true)}>
              {t("vendors.create")}
            </Button>
          ) : null
        }
        description={t("vendors.emptyStateHint")}
        title={t("vendors.emptyState")}
      />
    );
  } else {
    content = (
      <div className="flex flex-col gap-4">
        {/*
         * Natija soni + yangi sahifa e'loni (§8.3). `aria-live="polite"` —
         * "Ko'proq yuklash" dan keyin skrinrider "hech narsa o'zgarmadi"
         * deb o'ylamasligi uchun.
         */}
        <p
          aria-live="polite"
          className="text-sm text-text-muted"
          role="status"
        >
          {t("vendors.resultCount", { count: items.length })}
        </p>

        <ul aria-label={t("vendors.title")} className="flex flex-col gap-3">
          {items.map((vendor) => (
            <li key={vendor.id}>
              <VendorCard
                canManage={canManage}
                onAssign={(mode) => setAssignment({ mode, vendor })}
                onEdit={() => setEditing(vendor)}
                vendor={vendor}
              />
            </li>
          ))}
        </ul>

        {/*
         * KEYSET — "Ko'proq yuklash", sahifa RAQAMLARI yo'q (§8.3).
         * "Oldingi" tugmasi ham yo'q: `useInfiniteQuery` sahifalarni
         * QO'SHIB boradi, ya'ni "oldingi" — yuqoriga skroll.
         */}
        {vendorsQuery.hasNextPage ? (
          <div>
            <Button
              disabled={vendorsQuery.isFetchingNextPage}
              onClick={() => void vendorsQuery.fetchNextPage()}
              variant="secondary"
            >
              {vendorsQuery.isFetchingNextPage
                ? t("common.loading")
                : t("vendors.loadMore")}
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Field
        className="max-w-sm"
        id="vendor-search"
        label={t("vendors.searchLabel")}
      >
        <Input
          id="vendor-search"
          onChange={(event) => void setUrlFilters({ q: event.target.value })}
          placeholder={t("vendors.searchPlaceholder")}
          type="search"
          value={urlFilters.q}
        />
      </Field>

      {content}

      {canManage ? (
        <>
          <VendorDialog
            onOpenChange={onCreateOpenChange}
            open={createOpen}
            vendor={null}
          />
          <VendorDialog
            onOpenChange={(next) => {
              if (!next) setEditing(null);
            }}
            open={editing !== null}
            vendor={editing}
          />
          {/*
           * Biriktirish dialogi FAQAT ochilganda montaj qilinadi: uning
           * ichidagi rasta qidiruvi va biriktirish tarixi so'rovlari
           * ekran ochilishi bilan emas, foydalanuvchi so'raganda ketsin.
           */}
          {assignment ? (
            <AssignmentDialog
              mode={assignment.mode}
              onOpenChange={(next) => {
                if (!next) setAssignment(null);
              }}
              open
              vendor={assignment.vendor}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function VendorCard({
  canManage,
  onAssign,
  onEdit,
  vendor,
}: {
  canManage: boolean;
  onAssign: (mode: AssignmentMode) => void;
  onEdit: () => void;
  vendor: VendorListItem;
}) {
  const t = useTranslations();

  return (
    // §8.1: reestr kartasi ZICH — `px-4 py-3`, 10 foydalanuvchi emas,
    // yuzlab sotuvchi ko'riladi.
    <Card className="px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          {/* D-16: ism DB kontenti — tarjima qilinmaydi. */}
          <p className="truncate font-semibold" title={vendor.full_name}>
            {vendor.full_name}
          </p>

          {/*
           * D-16: telefon ham DB kontenti. §8.6: MASKALANMAYDI va
           * "ko'rsatish" tugmasi ostiga yashirilmaydi — u operatsion
           * ma'lumot, admin shu yerdan qo'ng'iroq qiladi.
           */}
          <a
            className="w-fit text-sm text-accent-text underline-offset-2 hover:underline"
            href={`tel:${vendor.phone}`}
          >
            {vendor.phone}
          </a>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Badge tone="muted">
            {t("vendors.stallCount", { count: vendor.stall_count })}
          </Badge>

          {canManage ? (
            <VendorActions
              hasStalls={vendor.stall_count > 0}
              onAssign={onAssign}
              onEdit={onEdit}
              vendorLabel={vendor.full_name}
            />
          ) : null}
        </div>
      </div>

      {/*
       * Rasta kodlari — FAQAT `≥640px` (§8.2 ustun ustuvorligi). Telefon
       * ekranida sanoq badge'i yetadi; kodlar qatorni uch marta uzaytirardi.
       *
       * `stall_codes` serverda 20 tagacha kesiladi, `stall_count` esa to'liq
       * son — ya'ni ro'yxat kesilganda ham "nechta?" javobi yo'qolmaydi.
       * Har kod ALOHIDA badge: badge hech qachon `truncate` qilinmaydi
       * (§5.1 qoida 3), ya'ni raqam yarmi kesilgan holda ko'rinmaydi.
       */}
      {vendor.stall_codes.length > 0 ? (
        <div className="mt-2 hidden flex-wrap items-center gap-1 sm:flex">
          <span className="sr-only">{t("vendors.stallCodesLabel")}: </span>
          {vendor.stall_codes.map((code) => (
            <Badge className="font-mono tabular-nums" key={code}>
              {code}
            </Badge>
          ))}
        </div>
      ) : null}
    </Card>
  );
}

const MENU_ITEM_CLASS =
  "flex min-h-11 cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted";

function VendorActions({
  hasStalls,
  onAssign,
  onEdit,
  vendorLabel,
}: {
  hasStalls: boolean;
  onAssign: (mode: AssignmentMode) => void;
  onEdit: () => void;
  vendorLabel: string;
}) {
  const t = useTranslations();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={`${t("vendors.actions")}: ${vendorLabel}`}
        className="inline-flex size-11 shrink-0 items-center justify-center rounded-md border border-border-ui bg-surface transition-colors hover:bg-surface-muted"
      >
        {/*
         * `Ellipsis` — lucide-react 1.27 dagi KANONIK nom; `MoreHorizontal`
         * faqat uning taxallusi (02-13 o'lchovi).
         */}
        <Ellipsis aria-hidden="true" className="size-4" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          className="z-50 mt-1 min-w-56 rounded-md border border-border bg-surface p-1 shadow-raised"
          sideOffset={4}
        >
          <DropdownMenu.Item className={MENU_ITEM_CLASS} onSelect={onEdit}>
            <Pencil aria-hidden="true" className="size-4" />
            {t("vendors.edit")}
          </DropdownMenu.Item>

          <DropdownMenu.Item
            className={MENU_ITEM_CLASS}
            onSelect={() => onAssign("open")}
          >
            <CalendarPlus aria-hidden="true" className="size-4" />
            {t("vendors.assignStall")}
          </DropdownMenu.Item>

          {/*
           * ALMASHINUV IKKI QADAM va u BITTA tugmaga birlashtirilmaydi
           * (D-10): backend ham qulaylik endpointini bermaydi va sabab bir
           * xil — ikki alohida audit yozuvi "kim qachon nima qildi"
           * savolining javobini saqlaydi.
           */}
          {hasStalls ? (
            <DropdownMenu.Item
              className={MENU_ITEM_CLASS}
              onSelect={() => onAssign("close")}
            >
              <UserMinus aria-hidden="true" className="size-4" />
              {t("vendors.closeAssignment")}
            </DropdownMenu.Item>
          ) : null}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
