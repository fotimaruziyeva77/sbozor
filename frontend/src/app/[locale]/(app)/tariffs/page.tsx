"use client";

import { Suspense, useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ReadOnlyNote } from "@/components/auth/read-only-note";
import { CategoryList } from "@/components/categories/category-list";
import { ServiceFeeCard } from "@/components/tariffs/service-fee-card";
import { TariffList } from "@/components/tariffs/tariff-list";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { ZoneList } from "@/components/zones/zone-list";
import { useAuthStore } from "@/lib/auth-store";
import { useCategoriesQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Tariflar ekrani (MARKET-03) — narx tarixi + zona/toifa reestrlari.
 *
 * NEGA UCHTASI BITTA EKRANDA: tarif TOIFAGA bog'lanadi (D-05), toifa esa
 * rastaga. Ularni uch alohida sahifaga bo'lish adminni "toifa qo'shish ->
 * boshqa sahifa -> narx qo'shish -> qaytish" tsikliga majburlardi. Zona
 * bu yerda tarifga bog'liq emas, lekin u ham kichik reestr va usta
 * qadamlarida (02-16) toifa bilan yonma-yon turadi.
 *
 * IKKI HUQUQ:
 *   `MARKET_DATA_VIEW` — ko'rish (direktor ham ko'radi, D-07)
 *   `TARIFF_MANAGE`    — narx yozish; direktorda YO'Q, ya'ni u tarix
 *                        ko'radi-yu, tugmalarni umuman ko'rmaydi
 *
 * `Suspense` MAJBURIY — toifa filtri URL'dan o'qiladi (`nuqs`).
 * =============================================================================
 */
export default function TariffsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "market_data_view");
  const canManage = hasPermission(roles, "tariff_manage");

  if (!canView) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("tariffs.title")}
        </h1>

        {canManage ? null : <ReadOnlyNote />}
      </div>

      <Suspense
        fallback={
          <BrandLoader />
        }
      >
        <TariffsBody canManage={canManage} />
      </Suspense>
    </div>
  );
}

/** Toifa filtri URL'da — filtrlangan ko'rinish havola bo'lib yuboriladi. */
const tariffFilterParsers = {
  category: parseAsString.withDefault(""),
};

function TariffsBody({ canManage }: { canManage: boolean }) {
  const t = useTranslations();
  const [urlFilters, setUrlFilters] = useQueryStates(tariffFilterParsers);
  const categoriesQuery = useCategoriesQuery();
  const [createOpen, setCreateOpen] = useState(false);
  /* №2 (2026-08-26): toifa kartasidagi «Narx» tugmasi shu toifa bilan ochadi. */
  const [presetCategoryId, setPresetCategoryId] = useState<string | null>(null);

  return (
    /*
     * Ustunlar KETMA-KET: tor ekranda yon panel ham, tarix ham yarim
     * kenglikda o'qib bo'lmas edi. Reestrlar TEPADA turadi, chunki tarif
     * ular ustiga quriladi (avval toifa, keyin narx).
     *
     * ⛔⛔ CHEGARA `md` EMAS, `lg` — VA BU O'LCHOVDAN KELIB CHIQQAN
     *     TUZATMA (260819).
     *
     *     `md` (768px) da ilova QOBIG'INING yon paneli ham ochiladi
     *     (`w-52` = 208px). Ya'ni 768px ekranda: qobiq to'ldirmasi 32 +
     *     yon panel 208 + oraliq 24 = 264px yo'qoladi, asosiy ustunga
     *     504px qoladi. Bu sahifa esa o'sha 504px ni yana ikkiga
     *     bo'lardi: 320 + 24 = 344, o'ng ustunga 160px. Filtr maydoni
     *     `min-w-48` (192px) unga SIG'MAYDI va sahifa 784px ga
     *     cho'zilardi (Xromda o'lchandi: 784 > 768).
     *
     *     `lg` (1024px) da esa asosiy ustun 760px — ikkiga bo'linishi
     *     bemalol. 768–1023px oralig'ida sahifa bir ustunli bo'ladi va
     *     bu o'qish uchun ham yaxshiroq.
     */
    <div className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
      <div className="flex flex-col gap-4">
        <ZoneList canManage={canManage} />
        <CategoryList
            onChangePrice={
              canManage
                ? (categoryId) => {
                    setPresetCategoryId(categoryId);
                    setCreateOpen(true);
                  }
                : undefined
            } canManage={canManage} />
      </div>

      <div className="flex flex-col gap-4">
        {/*
         * ⛔ XIZMAT HAQI (tarozi) TARIF RO'YXATIDAN YUQORIDA (0027).
         *
         *   U HAR toifaga tegadi, ya'ni tarif jadvalining USTIDAGI
         *   qatlam. Pastga qo'yilsa «bu ham bitta tarif turi» degan
         *   yolg'on model berardi — holbuki u bozor darajasidagi
         *   ALOHIDA narx (`market_service_fees`).
         *
         * ⚠ Foydalanuvchi talabi shu joyni nomma-nom belgilagan:
         *   «Ta'riflarda qushiladi u uzgarsa u yerda ko'rinsin».
         */}
        <ServiceFeeCard canManage={canManage} />

        <div className="flex flex-wrap items-end justify-between gap-3">
          <Field
            className="min-w-48"
            id="tariff-filter-category"
            label={t("tariffs.filterLabel")}
          >
            <Select
              id="tariff-filter-category"
              onChange={(event) =>
                void setUrlFilters({ category: event.target.value })
              }
              value={urlFilters.category}
            >
              <option value="">{t("tariffs.filterAll")}</option>
              {/* D-16: toifa nomi DB kontenti — tarjima qilinmaydi. */}
              {(categoriesQuery.data?.items ?? []).map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </Select>
          </Field>

          {canManage ? (
            <Button
              className="mb-0.5"
              onClick={() => {
                setPresetCategoryId(null);
                setCreateOpen(true);
              }}
            >
              <Plus aria-hidden="true" />
              {t("tariffs.create")}
            </Button>
          ) : null}
        </div>

        <h2 className="sr-only">{t("tariffs.historyTitle")}</h2>

        <TariffList
          canManage={canManage}
          categoryFilter={urlFilters.category}
          createOpen={createOpen}
          onCreateOpenChange={setCreateOpen}
          presetCategoryId={presetCategoryId}
        />
      </div>
    </div>
  );
}
