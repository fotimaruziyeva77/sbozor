"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRouter } from "@/i18n/navigation";
import { errorMessageKey } from "@/lib/api-client";
import type { MarketSummary } from "@/lib/api-types";
import { useLogout, useSelectMarket } from "@/lib/auth-queries";
import { applySession, useAuthStore } from "@/lib/auth-store";
import {
  fetchFirstIncompleteStep,
  useMarketsQuery,
} from "@/lib/market-queries";

/*
 * D-06: platforma admini bozor TANLAB kiradi — `market_view_all` unga RLS
 * bypass bermaydi, u faqat shu ekranni ochadi. Tanlangan bozor serverda
 * `app.market_id` GUC'iga yoziladi va yangi access token beriladi.
 *
 * Endpointlar: `POST /api/v1/auth/select-market`, `GET /api/v1/markets`,
 * `GET /api/v1/markets/{id}/setup-status`. Ularning HAMMASI so'rov
 * modullarida (`auth-queries.ts`, `market-queries.ts`) — bu komponent HTTP
 * qatlamiga to'g'ridan-to'g'ri tegmaydi.
 *
 * QORALAMA BOZOR (§6.4 — uzilishdan tiklanish): usta 1-qadamda qoralama
 * bozor tug'diradi va foydalanuvchi ishni yarim tashlab ketishi mumkin. U
 * qaytib kelganda AYNAN shu ekranni ko'radi, ya'ni qoralama bu yerda
 * ATAYIN ko'rinadi (butun mahsulotda yagona bunday joy) va bosilganda
 * birinchi tugallanmagan qadamga olib boradi. Ro'yxat SERVERDA
 * filtrlanmaydi — bayroq javobda keladi va qaror shu yerda qabul qilinadi.
 *
 * DEFERRED (v2): sessiya ichida bozorni ALMASHTIRISH UI'si bu yerda ham,
 * app shell'da ham ATAYIN yo'q — u alohida qaror va alohida audit talab
 * qiladi.
 */
const DASHBOARD_PATH = "/dashboard";
const WIZARD_PATH = "/markets/setup";

export function MarketPicker() {
  const t = useTranslations();
  const router = useRouter();
  const { accessToken, markets, clearSession } = useAuthStore();
  const [formError, setFormError] = useState<string | null>(null);

  // Tokensiz bu ekranning ma'nosi yo'q: bozor tanlanmagan sessiyaga refresh
  // cookie BERILMAYDI (01-06), ya'ni sahifa yangilangan bo'lsa qaytadan
  // login qilish kerak.
  useEffect(() => {
    if (!accessToken) router.replace("/login");
  }, [accessToken, router]);

  /*
   * Asosiy manba — login javobidagi `markets`. `GET /markets` faqat ZAXIRA:
   * ro'yxat bo'sh bo'lsa (masalan klient tomonda navigatsiya bilan kelingan
   * bo'lsa) serverdan so'raladi.
   */
  const marketsQuery = useMarketsQuery({
    enabled: accessToken !== null && markets.length === 0,
  });

  /*
   * FILTR YO'Q — qoralama bozor ham ro'yxatga tushadi (§12.1.1 6-band).
   * Ilgari bu yerda bayroq bo'yicha kesuvchi `.filter(...)` turardi, lekin
   * u O'LIK yo'lda edi: `GET /markets` faqat zaxira manba va bu ekranda u
   * baribir 409 oladi (bozor tanlanmagan sessiya `TenantSessionDep` dan
   * o'tmaydi). Ya'ni faqat shu filtrni olib tashlash HECH NARSANI
   * o'zgartirmasdi — haqiqiy tuzatish serverda va javob shaklida edi.
   */
  const options: readonly MarketSummary[] =
    markets.length > 0
      ? markets
      : (marketsQuery.data ?? []).map((market) => ({
          id: market.id,
          name: market.name,
          is_active: market.is_active,
        }));

  const selectMarket = useSelectMarket({
    /*
     * Marshrut qarori SERVER javobidan olinadi (`session.market.is_active`),
     * bosilgan ro'yxat elementidan EMAS: ro'yxat login paytida olingan va
     * eskirgan bo'lishi mumkin — bozor shu orada faollashtirilgan bo'lsa
     * foydalanuvchi tugallangan ustaga qaytib tushardi.
     */
    onSuccess: async (session) => {
      applySession({
        accessToken: session.access_token,
        roles: session.roles,
        market: session.market,
      });
      if (session.market.is_active) {
        router.replace(DASHBOARD_PATH);
        return;
      }
      const step = await fetchFirstIncompleteStep(session.market.id);
      router.replace(`${WIZARD_PATH}?step=${step}`);
    },
    onError: (error) => setFormError(t(errorMessageKey(error))),
  });

  const logout = useLogout({
    // Sessiya har qanday holatda tozalanadi: server javobi kelmasa ham
    // brauzerda o'lik token qolib ketmasligi kerak.
    onSettled: () => {
      clearSession();
      router.replace("/login");
    },
  });

  /*
   * DIQQAT — `isLoading`, `isPending` EMAS (CR-02).
   *
   * TanStack Query v5 da `isPending` = "keshda ma'lumot YO'Q", ya'ni
   * O'CHIRILGAN so'rov (`enabled: false`) uchun u ABADIY `true` bo'lib
   * qoladi — hech qachon so'rov ketmagani uchun ma'lumot ham paydo
   * bo'lmaydi. Asosiy yo'lda `markets` login javobidan to'ladi, ya'ni
   * `enabled === false`, ya'ni `isPending === true`, ya'ni har bir bozor
   * tugmasi `disabled` bo'lib qolardi va D-06 oqimi UMUMAN yakunlanmasdi.
   *
   * `isLoading` = `isPending && isFetching` — o'chirilgan so'rovda `false`,
   * chunki hech narsa yuklanmayapti. Aynan shu "hozir so'rov ketyaptimi?"
   * degan savolga javob beradi va tugmani faqat HAQIQIY kutish paytida
   * bloklaydi.
   */
  const isBusy = selectMarket.isPending || marketsQuery.isLoading;

  if (marketsQuery.isLoading) {
    return (
      <p className="text-sm text-text-muted" role="status">
        {t("common.loading")}
      </p>
    );
  }

  if (options.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-text-muted">{t("auth.noMarkets")}</p>
        <Button
          variant="secondary"
          size="lg"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
        >
          {t("nav.logout")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <ul aria-label={t("auth.selectMarket")} className="flex flex-col gap-2">
        {options.map((market) => (
          <li key={market.id}>
            <button
              className="flex w-full items-center gap-2 rounded-md border border-border bg-surface px-4 py-3 text-left text-sm font-semibold transition-colors hover:bg-surface-muted disabled:pointer-events-none disabled:opacity-50"
              disabled={isBusy}
              onClick={() => selectMarket.mutate(market.id)}
              type="button"
            >
              {/*
               * IKKI XIL MATN, IKKI XIL QOIDA — chalkashtirilmasin:
               *   `market.name` — DB KONTENTI, tarjima QILINMAYDI (D-16).
               *     U qanday kiritilgan bo'lsa shunday ko'rinadi.
               *   `auth.marketDraft` — INTERFEYS matni, `next-intl` orqali
               *     uchala tilda keladi.
               * Badge tugma ICHIDA: u tugmaning hisoblangan nomiga qo'shiladi
               * va skrinrider "<nom> Qoralama" deb o'qiydi, ya'ni holat rang
               * bilan emas, MATN bilan ham beriladi (WCAG 1.4.1).
               *
               * `{" "}` KERAK va u `gap-2` ning takrori EMAS: bo'shliq
               * VIZUAL emas, MATNLI. Ikki qo'shni inline element orasida
               * bo'sh matn tuguni bo'lmasa, hisoblangan nom
               * "<nom><belgi>" bo'lib qo'shilib ketadi va skrinrider uni
               * bitta so'z sifatida o'qiydi (accname algoritmi inline
               * elementlar orasiga bo'shliq QO'SHMAYDI).
               */}
              <span>{market.name}</span>
              {market.is_active ? null : (
                <>
                  {" "}
                  <Badge tone="muted">{t("auth.marketDraft")}</Badge>
                </>
              )}
            </button>
          </li>
        ))}
      </ul>

      {formError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {formError}
        </p>
      ) : null}
    </div>
  );
}
