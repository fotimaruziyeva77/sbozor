/**
 * Sotuvchilar ekrani — SHAXSIY MA'LUMOT qarorlarining regressiya darvozasi
 * (UI-SPEC §8.6, T-02-112 / T-02-113).
 *
 * NEGA AYNAN SHU IKKI DA'VO TESTLANADI:
 *
 *   1. AUDIT BILDIRISHI KO'RINADI. D-09 bo'yicha `GET /vendors` ning har
 *      chaqiruvi auditga yoziladi va §8.6 ning butun mazmuni shundaki,
 *      to'siq KO'RINMASA to'sadigan narsa yo'q. Bildirish `<p>` bo'lib
 *      ekran boshida turadi — modal EMAS, tasdiq EMAS. Uni "shovqin" deb
 *      olib tashlash yoki modalga aylantirish typecheck'dan ham,
 *      lint'dan ham, build'dan ham BEMALOL o'tardi.
 *
 *   2. TELEFON MASKALANMAYDI. Bu ATAYIN qilingan tanlov (§8.6 5-sabab):
 *      server raqamni allaqachon yuborgan, ya'ni yulduzcha hech narsani
 *      yashirmaydi — u faqat "biz xavfsizmiz" degan yolg'on his beradi va
 *      admin uchun operatsion zarur ma'lumotni (qo'ng'iroq qilish) bekor
 *      qiladi. "Xavfsizlikni yaxshilash" niyatidagi keyingi ishlovchi
 *      maskalashni qaytarib qo'yishi juda ehtimolli — shuning uchun qaror
 *      test bilan qulflanadi.
 *
 *   3. NAZORAT: rasta kodlari badge bo'lib chiqadi. Usiz yuqoridagi ikki
 *      test "karta umuman render bo'lmadi" holatida ham yashil ko'rinardi.
 *
 * DIQQAT: bosish `fireEvent` bilan, `@testing-library/user-event` bilan
 * EMAS — u tasdiqlangan paketlar ro'yxatiga kirmaydi (01-12 qarori).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import VendorsPage from "@/app/[locale]/(app)/vendors/page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { vendorsKey } from "@/lib/market-queries";

/** `+998` bilan boshlanadigan E.164 — server aynan shu shaklda yuboradi. */
const VENDOR_PHONE = "+998901234567";

/**
 * Sessiyadagi bozor VA kesh kalitidagi bozor — BITTA qiymat (CR-01).
 *
 * Kalit `market_id` bilan doiralangani uchun ekilgan ma'lumot faqat AYNAN
 * shu bozor kontekstida topiladi. Ikkalasi ajralib ketsa, ekran bo'sh
 * holat chiqarib test yiqiladi — ya'ni doiralash bu yerda ham o'lchanadi.
 */
const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const VENDOR = {
  id: "55555555-5555-4555-8555-555555555555",
  full_name: "Aliyev Vali",
  phone: VENDOR_PHONE,
  stall_count: 2,
  stall_codes: ["A-12", "B-7"],
  created_at: "2026-07-01T05:00:00Z",
};

/** `vendors.auditNotice` — uz-Latn qiymati (test AYNAN shu katalogni yuklaydi). */
const AUDIT_NOTICE = messages.vendors.auditNotice;

/**
 * Ro'yxat ma'lumoti KESHGA ekiladi, HTTP qatlami mock QILINMAYDI.
 *
 * Ikki sabab:
 *   1. QAMROV — bu yo'l HAQIQIY `useVendorsQuery` ni ishlatadi: haqiqiy
 *      kalit fabrikasi (`vendorsKey`) va haqiqiy `pages.flatMap` yassilashi.
 *      Kalit bir kun o'zgarsa test JIMGINA yashil qolmaydi — u bo'sh holat
 *      chiqarib, kartani topa olmay yiqiladi.
 *   2. QOIDA — `components/vendors` papkasida HTTP qatlamining nomi
 *      UMUMAN uchramasligi kerak (mexanik darvoza). Test faylining o'zi ham
 *      shu papkada yashaydi, ya'ni u ham istisno emas.
 *
 * `staleTime: Infinity` MAJBURIY: usiz TanStack Query montajdan keyin
 * ekilgan ma'lumotni "eskirgan" deb bilib, haqiqiy so'rov yuborardi.
 */
function renderVendorsPage(): ReturnType<typeof render> {
  // `retry: false` — xato holatida test uch marta qayta urinishni kutmasin.
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });

  queryClient.setQueryData(vendorsKey(MARKET_ID, { q: "" }), {
    pages: [{ items: [VENDOR], next_cursor: null }],
    pageParams: [null],
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <NuqsTestingAdapter>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <VendorsPage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>
  );

  return render(tree);
}

/** Bozor admini — `vendor_view` ham, `vendor_manage` ham bor (D-07). */
function seedMarketAdminSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

beforeEach(() => {
  clearSession();
  seedMarketAdminSession();
});

afterEach(() => {
  clearSession();
});

describe("Sotuvchilar ekrani — shaxsiy ma'lumot kontrakti (§8.6)", () => {
  test("audit bildirishi ekranda ko'rinadi va u DIALOG emas", async () => {
    renderVendorsPage();

    const notice = await screen.findByText(AUDIT_NOTICE);
    expect(notice).toBeInTheDocument();

    /*
     * ANIQ SABAB: §8.6 bildirishni PASSIV `<p>` deb belgilaydi. Modal yoki
     * tasdiq bo'lsa u `role="dialog"` ichida bo'lardi va bozor admini uni
     * kuniga o'nlab marta "OK" bilan yopib, e'tibor bermaydigan bo'lardi.
     */
    expect(notice.tagName).toBe("P");
    expect(notice.closest("[role='dialog']")).toBeNull();
    expect(notice.closest("[role='alertdialog']")).toBeNull();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    // Bildirish ekranga BIR MARTA chiqadi — har qatorda takrorlanmaydi.
    expect(screen.getAllByText(AUDIT_NOTICE)).toHaveLength(1);
  });

  test("telefon `tel:` havolasi bo'lib chiqadi va MASKALANMAYDI", async () => {
    renderVendorsPage();

    const link = await screen.findByRole("link", { name: VENDOR_PHONE });
    expect(link).toHaveAttribute("href", `tel:${VENDOR_PHONE}`);

    /*
     * Maskalash qaytib kelsa raqam o'rnida yulduzcha yoki nuqta turardi.
     * Ikkala da'vo ham kerak: birinchisi to'liq raqamni, ikkinchisi
     * maskalash BELGISINING yo'qligini qulflaydi.
     */
    expect(link).toHaveTextContent(VENDOR_PHONE);
    expect(link.textContent ?? "").not.toMatch(/[*•·…]/u);
  });

  test("NAZORAT: rasta kodlari badge bo'lib ko'rinadi", async () => {
    renderVendorsPage();

    await waitFor(() => {
      expect(screen.getByText(VENDOR.full_name)).toBeInTheDocument();
    });

    for (const code of VENDOR.stall_codes) {
      const badge = screen.getByText(code);
      // `ui/badge` ning barqaror belgisi — u hech qachon `truncate`
      // qilinmaydi (§5.1 qoida 3), ya'ni raqam yarmi kesilmaydi.
      expect(badge).toHaveClass("rounded-full");
    }

    // Sanoq badge'i ham bor: `stall_codes` serverda 20 tada kesiladi,
    // `stall_count` esa to'liq son.
    expect(screen.getByText("2 ta rasta")).toBeInTheDocument();
  });
});
