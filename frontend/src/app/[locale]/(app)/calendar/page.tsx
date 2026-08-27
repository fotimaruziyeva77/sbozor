"use client";

import { Suspense, useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ReadOnlyNote } from "@/components/auth/read-only-note";
import { ExceptionDialog } from "@/components/calendar/exception-dialog";
import { ExceptionList } from "@/components/calendar/exception-list";
import { WeekdayPicker } from "@/components/calendar/weekday-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useAuthStore } from "@/lib/auth-store";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCalendarQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Ish kunlari kalendari (MARKET-05, D-17/D-18).
 *
 * IKKI BO'LIM, IKKI XIL DOIRA:
 *   Haftalik rejim — takrorlanadigan qoida (`open_weekdays`)
 *   Istisno kunlar — alohida sanalar; ular haftalik jadvaldan USTUN turadi
 *
 * Ikkalasi ham FAQAT bozor darajasida (D-18): zona yoki toifa bo'yicha
 * kalendar YO'Q va qo'shilmaydi.
 *
 * IKKI HUQUQ: `MARKET_DATA_VIEW` — ko'rish (direktor ham ko'radi),
 * `STALL_MANAGE` — o'zgartirish (direktorda YO'Q, D-07).
 *
 * `Suspense` — bu sahifada URL holati YO'Q, lekin chegara baribir qo'yiladi:
 * navigatsiya paytida `useSearchParams` daraxtning boshqa qismidan kelishi
 * mumkin va chegarasiz butun sahifa statik prerender ro'yxatidan tushardi.
 * =============================================================================
 */
export default function CalendarPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "market_data_view");
  const canManage = hasPermission(roles, "stall_manage");

  if (!canView) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("calendar.title")}
        </h1>

        {canManage ? null : <ReadOnlyNote />}
      </div>

      <Suspense
        fallback={
          <BrandLoader />
        }
      >
        <CalendarBody canManage={canManage} />
      </Suspense>
    </div>
  );
}

function CalendarBody({ canManage }: { canManage: boolean }) {
  const t = useTranslations();
  const calendarQuery = useCalendarQuery();
  const [addOpen, setAddOpen] = useState(false);

  if (calendarQuery.isPending) {
    return (
      <BrandLoader />
    );
  }

  if (calendarQuery.isError) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(calendarQuery.error))}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader className="pb-2">
          <h2 className="text-lg font-semibold">
            {t("calendar.weekdaysLabel")}
          </h2>
        </CardHeader>
        <CardContent>
          {/*
           * `key` — server jadvali o'zgarganda tanlagich YANGIDAN montaj
           * qilinadi va lokal holat serverdagi haqiqatdan boshlanadi.
           * Effekt ichida `setState` qilishning (kaskad renderlar) o'rniga
           * shu yo'l tanlandi.
           */}
          <WeekdayPicker
            canManage={canManage}
            key={calendarQuery.data.open_weekdays.join("-")}
            openWeekdays={calendarQuery.data.open_weekdays}
          />
        </CardContent>
      </Card>

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
    </div>
  );
}
