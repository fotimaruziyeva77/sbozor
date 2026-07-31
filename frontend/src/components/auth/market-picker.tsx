"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { useRouter } from "@/i18n/navigation";
import { apiFetch, errorMessageKey } from "@/lib/api-client";
import type { MarketSummary } from "@/lib/api-types";
import {
  emptyResponseSchema,
  marketListSchema,
  sessionResponseSchema,
} from "@/lib/api-types";
import { applySession, useAuthStore } from "@/lib/auth-store";

/*
 * D-06: platforma admini bozor TANLAB kiradi — `market_view_all` unga RLS
 * bypass bermaydi, u faqat shu ekranni ochadi. Tanlangan bozor serverda
 * `app.market_id` GUC'iga yoziladi va yangi access token beriladi.
 *
 * Endpointlar: `POST /api/v1/auth/select-market`, `GET /api/v1/markets`.
 *
 * DEFERRED (v2): sessiya ichida bozorni ALMASHTIRISH UI'si bu yerda ham,
 * app shell'da ham ATAYIN yo'q — u alohida qaror va alohida audit talab
 * qiladi.
 */
const SELECT_MARKET_PATH = "/auth/select-market";
const MARKETS_PATH = "/markets";
const LOGOUT_PATH = "/auth/logout";

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
  const marketsQuery = useQuery({
    queryKey: ["markets"],
    queryFn: () => apiFetch(MARKETS_PATH, { schema: marketListSchema }),
    enabled: accessToken !== null && markets.length === 0,
  });

  const options: readonly MarketSummary[] =
    markets.length > 0
      ? markets
      : (marketsQuery.data ?? [])
          .filter((market) => market.is_active)
          .map((market) => ({ id: market.id, name: market.name }));

  const selectMarket = useMutation({
    mutationFn: (marketId: string) =>
      apiFetch(SELECT_MARKET_PATH, {
        method: "POST",
        body: { market_id: marketId },
        schema: sessionResponseSchema,
      }),
    onSuccess: (session) => {
      applySession({
        accessToken: session.access_token,
        roles: session.roles,
        market: session.market,
      });
      router.replace("/dashboard");
    },
    onError: (error) => setFormError(t(errorMessageKey(error))),
  });

  const logout = useMutation({
    mutationFn: () =>
      apiFetch(LOGOUT_PATH, { method: "POST", schema: emptyResponseSchema }),
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
      {/* D-16: bozor nomi DB kontenti — tarjima qilinmaydi. */}
      <ul aria-label={t("auth.selectMarket")} className="flex flex-col gap-2">
        {options.map((market) => (
          <li key={market.id}>
            <button
              className="w-full rounded-md border border-border bg-surface px-4 py-3 text-left text-sm font-medium transition-colors hover:bg-surface-muted disabled:pointer-events-none disabled:opacity-50"
              disabled={isBusy}
              onClick={() => selectMarket.mutate(market.id)}
              type="button"
            >
              {market.name}
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
