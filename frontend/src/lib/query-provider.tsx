"use client";

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "@/lib/api-client";
import { subscribeSessionReset } from "@/lib/auth-store";

/**
 * Server holati keshi.
 *
 * `QueryClient` `useState` initsializatori ichida quriladi: modul darajasida
 * yaratilgan klient SSR paytida barcha so'rovlar orasida bo'lishib ketardi.
 *
 * KESH — TENANT CHEGARASINING BIR QISMI (CR-01). Sessiya identifikatori
 * o'zgarganda (logout, yangi login, boshqa bozor) u to'liq bo'shatiladi —
 * pastdagi `useEffect` ga qarang.
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 30 s — panel ekranlari uchun yetarli; navbatdagi navigatsiya
            // keshdan darhol ochiladi, fon yangilanishi esa jimgina ketadi.
            staleTime: 30_000,
            retry: (failureCount, error) => {
              // 401 — `api-client` allaqachon bir marta refresh qilib ko'rgan.
              // Qayta urinish faqat o'lik sessiyaga navbat yig'adi (T-01-67).
              if (error instanceof ApiError && error.status === 401) {
                return false;
              }
              // 4xx — mijoz xatosi, takrorlash natijani o'zgartirmaydi.
              if (
                error instanceof ApiError &&
                error.status >= 400 &&
                error.status < 500
              ) {
                return false;
              }
              return failureCount < 1;
            },
          },
          mutations: {
            // Yozuv operatsiyalari ATAYIN takrorlanmaydi: to'lov yoki
            // foydalanuvchi yaratish ikki marta ketishi mumkin emas.
            retry: false,
          },
        },
      }),
  );

  /*
   * Sessiya identifikatori o'zgardi -> butun kesh bo'shaydi (CR-01).
   *
   * ⚠ AYNAN `clear()`, TanStack'ning yumshoqroq `reset*` / `remove*`
   * oilasidagi `*Queries` metodlari EMAS: `reset*` variantlari kalitlarni
   * SAQLAB, faol so'rovlarni QAYTA YUKLAYDI — ya'ni B bozori kontekstida
   * A bozorining kalitlari yana serverga borardi. `clear()` esa butun
   * keshni, shu jumladan mutatsiya keshini ham bo'shatadi.
   *
   * ⚠ IKKALA CHORA HAM KERAK va biri ikkinchisining o'rnini BOSMAYDI:
   * kalitlarni `market_id` bilan doiralash (`market-queries.ts`) yolg'iz
   * o'zi eski qatorlarni `gcTime` (5 daq) tugagunicha xotirada qoldirardi
   * va ular devtools yoki orqaga navigatsiya bilan yetib borardi; `clear()`
   * yolg'iz o'zi esa sessiya ichida bozor almashtirish UI'si qo'shilgan
   * zahoti kalitlar poygasida buzilardi.
   *
   * `client` `useState` dan keladi, ya'ni bog'liqlik ro'yxati barqaror va
   * obuna komponent umri davomida bir marta quriladi.
   */
  useEffect(() => subscribeSessionReset(() => client.clear()), [client]);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
