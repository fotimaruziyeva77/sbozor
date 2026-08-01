"use client";

import { Suspense, useCallback, useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsInteger, useQueryState } from "nuqs";

import { CategoryList } from "@/components/categories/category-list";
import { ExceptionDialog } from "@/components/calendar/exception-dialog";
import { ExceptionList } from "@/components/calendar/exception-list";
import { WeekdayPicker } from "@/components/calendar/weekday-picker";
import { ImportPanel } from "@/components/import/import-panel";
import { StallCardDialog } from "@/components/stalls/stall-card-dialog";
import { StallCategoryDialog } from "@/components/stalls/stall-category-dialog";
import { StallDialog } from "@/components/stalls/stall-dialog";
import { StallList } from "@/components/stalls/stall-list";
import { TariffList } from "@/components/tariffs/tariff-list";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VendorList } from "@/components/vendors/vendor-list";
import { ActivationPanel } from "@/components/wizard/activation-panel";
import {
  DEFAULT_SETUP_STEP,
  fallbackStep,
  isRenderableStep,
} from "@/components/wizard/wizard-steps";
import { WizardShell } from "@/components/wizard/wizard-shell";
import { ZoneList } from "@/components/zones/zone-list";
import { Link } from "@/i18n/navigation";
import type { StallListItem } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCalendarQuery, useSetupStatusQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Ustaning IKKINCHI marshruti — 2–7-qadamlar (UI-SPEC §6.1…§6.6).
 *
 * QADAM RAQAMI URL'DA, BAJARILGANLIK SERVERDA. `?step` — FAQAT KO'RINISH,
 * haqiqat emas (T-02-120): uni qo'lda `?step=7` deb yozish to'liqlik
 * tekshiruvini CHETLAB O'TMAYDI, chunki darvoza serverda (`_blocking()`)
 * va `market_activate()` klientdan hech qanday parametr olmaydi.
 *
 * HAR QADAM MAVJUD KOMPONENTLARDAN YIG'ILADI. Usta uchun ikkinchi nusxa
 * yozilmaydi: nusxa server qoidasidan ajralib ketardi va aynan o'sha
 * joyda qadam bajarilmas bo'lib qolardi (T-02-127a). Eng aniq holat —
 * 4-qadam: u 02-15 dagi tarif dialogini O'ZGARISHSIZ ishlatadi va sana
 * chegarasini FAQAT serverning `min_valid_from` idan oladi.
 *
 * ORQAGA QAYTISH ERKIN, ogohlantirish dialogi YO'Q (§6.4): holat serverda,
 * ya'ni qadamdan chiqishda yo'qoladigan narsa yo'q. Ro'yxat qadamlarida
 * (2–6) har element qo'shilganda darhol saqlanadi; 7-qadamdagi haftalik
 * jadval esa o'z "Saqlash" tugmasiga ega va u o'zgarmagan holatni ham
 * to'sadi (02-15).
 *
 * `Suspense` MAJBURIY — `?step` URL qidiruv parametridan o'qiladi.
 * =============================================================================
 */
export default function MarketSetupPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "market_data_view");

  if (!canView) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <Suspense
      fallback={
        <div aria-busy="true" className="flex flex-col gap-3" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-12 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      }
    >
      <SetupBody />
    </Suspense>
  );
}

function SetupBody() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const [urlStep] = useQueryState(
    "step",
    parseAsInteger.withDefault(DEFAULT_SETUP_STEP),
  );

  const marketId = principal?.marketId ?? null;
  const statusQuery = useSetupStatusQuery(marketId);
  const status = statusQuery.data ?? null;

  /*
   * Diapazondan tashqaridagi `?step` 1-qadamga EMAS, mazmunli qadamga
   * tushadi: chala bozorda birinchi to'siqning qadamiga, to'liq bozorda
   * esa faollashtirish qadamiga.
   *
   * Tuzatish RENDER paytida hisoblanadi, URL'ni qayta yozish bilan EMAS:
   * effekt ichidagi `setState` kaskad render berardi va `?step` baribir
   * faqat ko'rinish — uni "to'g'rilash" hech qanday holatni saqlamaydi.
   */
  const step = isRenderableStep(urlStep) ? urlStep : fallbackStep(status);

  const roles = principal?.roles ?? [];
  const canManageStalls = hasPermission(roles, "stall_manage");
  const canManageTariffs = hasPermission(roles, "tariff_manage");
  const canManageVendors = hasPermission(roles, "vendor_manage");

  return (
    <WizardShell
      currentStep={step}
      marketId={marketId}
      title={t("wizard.title")}
    >
      <StepContent
        canManageStalls={canManageStalls}
        canManageTariffs={canManageTariffs}
        canManageVendors={canManageVendors}
        step={step}
      />
    </WizardShell>
  );
}

function StepContent({
  canManageStalls,
  canManageTariffs,
  canManageVendors,
  step,
}: {
  canManageStalls: boolean;
  canManageTariffs: boolean;
  canManageVendors: boolean;
  step: number;
}) {
  const t = useTranslations();

  const [tariffCreateOpen, setTariffCreateOpen] = useState(false);
  const [vendorCreateOpen, setVendorCreateOpen] = useState(false);

  if (step === 1) return <RequisitesSummary />;
  if (step === 2) return <ZoneList canManage={canManageStalls} />;
  if (step === 3) return <CategoryList canManage={canManageStalls} />;

  if (step === 4) {
    return (
      <div className="flex flex-col gap-4">
        {canManageTariffs ? (
          <Button
            className="self-start"
            onClick={() => setTariffCreateOpen(true)}
          >
            <Plus aria-hidden="true" />
            {t("tariffs.create")}
          </Button>
        ) : null}

        {/*
         * ⚠ 02-15 dagi ro'yxat va dialog O'ZGARISHSIZ. Dialogning sana
         * `min` i `useTariffsQuery()` javobidagi `min_valid_from` dan
         * TO'G'RIDAN-TO'G'RI keladi va bu yerda hech narsa hisoblanmaydi:
         * qoralama bozorda u O'TMISHDAGI sana bo'ladi (server qoidasi
         * 02-09 T-02-70) va boshlang'ich narx aynan o'shanga yoziladi.
         * Ikkinchi, o'z chegarasini hisoblaydigan forma bu qadamni
         * bajarilmas qilardi.
         */}
        <TariffList
          canManage={canManageTariffs}
          categoryFilter=""
          createOpen={tariffCreateOpen}
          onCreateOpenChange={setTariffCreateOpen}
        />
      </div>
    );
  }

  if (step === 5) return <StallsStep canManage={canManageStalls} />;

  if (step === 6) {
    return (
      <div className="flex flex-col gap-4">
        <ImportPanel kind="vendors" />

        {canManageVendors ? (
          <Button
            className="self-start"
            onClick={() => setVendorCreateOpen(true)}
          >
            <Plus aria-hidden="true" />
            {t("vendors.create")}
          </Button>
        ) : null}

        <VendorList
          canManage={canManageVendors}
          createOpen={vendorCreateOpen}
          onCreateOpenChange={setVendorCreateOpen}
        />
      </div>
    );
  }

  return <CalendarStep canManage={canManageStalls} />;
}

/**
 * 1-qadam BU MARSHRUTDA — faqat xulosa.
 *
 * Rekvizitlar bozor bilan BIRGA yoziladi (`market_create()`), ularni
 * keyin o'zgartiradigan endpoint esa 02-11 da ATAYIN ochilmagan
 * (`rename_market()` HTTP iste'molchisisiz qoldirilgan). Bu yerda forma
 * ko'rsatish "Saqlash" tugmasi hech qayerga bormaydigan yolg'on va'da
 * bo'lardi.
 *
 * Qadam baribir CHIZILADI: bozor tanlash ekrani to'liq qoralama uchun
 * `?step=1` yuborishi mumkin (`fetchFirstIncompleteStep` ning fail-safe
 * qiymati) va foydalanuvchi bo'sh ekranga tushmasligi kerak.
 */
function RequisitesSummary() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">
        {t("wizard.requisitesSavedTitle")}
      </h2>
      {/* D-16: bozor nomi — DB kontenti, tarjima QILINMAYDI. */}
      <p className="text-sm">{principal?.marketName ?? ""}</p>
      <p className="text-sm text-text-muted">
        {t("wizard.requisitesSavedHint")}
      </p>
      <Link
        className="inline-flex min-h-11 items-center self-start rounded-md bg-accent px-6 text-sm font-semibold text-accent-fg"
        href="/markets/setup?step=2"
      >
        {t("wizard.continue")}
      </Link>
    </div>
  );
}

/** 5-qadam: import + reestr; tahrir dialoglari reestr bilan BIR XIL. */
function StallsStep({ canManage }: { canManage: boolean }) {
  const [selectedStallId, setSelectedStallId] = useState<string | null>(null);
  const [editStallId, setEditStallId] = useState<string | null>(null);
  const [categoryStall, setCategoryStall] = useState<StallListItem | null>(
    null,
  );

  const openStall = useCallback((stallId: string) => {
    setSelectedStallId(stallId);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <ImportPanel kind="stalls" />

      <StallList
        canManage={canManage}
        onChangeCategory={setCategoryStall}
        onEditStall={(stall) => setEditStallId(stall.id)}
        onOpenStall={openStall}
      />

      <StallCardDialog
        canManage={canManage}
        onClose={() => setSelectedStallId(null)}
        onEdit={(stallId) => {
          setSelectedStallId(null);
          setEditStallId(stallId);
        }}
        stallId={selectedStallId}
      />

      {canManage ? (
        <>
          <StallDialog
            mode="edit"
            onOpenChange={(next) => {
              if (!next) setEditStallId(null);
            }}
            open={editStallId !== null}
            stallId={editStallId}
          />

          <StallCategoryDialog
            onOpenChange={(next) => {
              if (!next) setCategoryStall(null);
            }}
            open={categoryStall !== null}
            stall={categoryStall}
          />
        </>
      ) : null}
    </div>
  );
}

/** 7-qadam: ish kunlari + istisnolar + faollashtirish paneli. */
function CalendarStep({ canManage }: { canManage: boolean }) {
  const t = useTranslations();
  const calendarQuery = useCalendarQuery();
  const [addOpen, setAddOpen] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      {calendarQuery.isPending ? (
        <div aria-busy="true" className="flex flex-col gap-3" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-40 rounded-lg" />
        </div>
      ) : calendarQuery.isError ? (
        <p className="text-sm text-text-muted" role="status">
          {t(marketErrorMessageKey(calendarQuery.error))}
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold">
              {t("calendar.weekdaysLabel")}
            </h2>
            {/*
             * `key` — server jadvali o'zgarganda tanlagich YANGIDAN montaj
             * qilinadi (02-15 naqshi): effekt ichida `setState` qilinmaydi.
             */}
            <WeekdayPicker
              canManage={canManage}
              key={calendarQuery.data.open_weekdays.join("-")}
              openWeekdays={calendarQuery.data.open_weekdays}
            />
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">
                {t("calendar.exceptionsTitle")}
              </h2>
              {canManage ? (
                <Button onClick={() => setAddOpen(true)}>
                  <Plus aria-hidden="true" />
                  {t("calendar.addException")}
                </Button>
              ) : null}
            </div>

            <ExceptionList
              canManage={canManage}
              exceptions={calendarQuery.data.exceptions}
            />
          </div>

          {canManage ? (
            <ExceptionDialog onOpenChange={setAddOpen} open={addOpen} />
          ) : null}
        </>
      )}

      <ActivationPanel />
    </div>
  );
}
