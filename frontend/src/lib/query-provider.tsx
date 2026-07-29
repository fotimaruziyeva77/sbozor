"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "@/lib/api-client";

/**
 * Server holati keshi.
 *
 * `QueryClient` `useState` initsializatori ichida quriladi: modul darajasida
 * yaratilgan klient SSR paytida barcha so'rovlar orasida bo'lishib ketardi.
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

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
