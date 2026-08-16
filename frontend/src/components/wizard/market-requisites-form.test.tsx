/**
 * MarketRequisitesForm — ustaning 1-qadami ISH REJIMINI SO'RAYDIMI (WR-06).
 *
 * =============================================================================
 * NEGA BU TEST BOR VA NEGA U AYNAN `open_weekdays` GA QARAYDI:
 *
 * `0011_weekday_choice` DB tomonida standartni olib tashladi — endi
 * `market_create()` ish rejimini TAXMIN QILMAYDI va tanlanmagan bozor
 * `calendar_missing` bilan to'siladi. Bu tuzatishning IKKINCHI yarmi shu
 * formada: agar u qiymatni yubormasa, HAR BIR yangi bozor 7-qadamda
 * to'silardi va eng ko'p uchraydigan holat (har kuni ishlaydigan bozor)
 * sababsiz og'irlashardi.
 *
 * Ya'ni backend testi "to'siq ishlaydimi?" ni, bu test esa "oddiy
 * foydalanuvchi to'siqqa umuman urilmaydimi?" ni o'lchaydi. Ikkalasi
 * BIRGA tuzatishni tavsiflaydi; bittasi yolg'iz qolsa ikkinchi yarim
 * jimgina yo'qolishi mumkin.
 *
 * Ko'rikning o'zi bu holatni "`market-requisites-form.tsx` bo'yicha
 * `open_weekdays` qidiruvi NOL natija beradi" deb yozgan edi — endi bu
 * fayl o'sha qidiruvni testga aylantiradi.
 * =============================================================================
 *
 * DIQQAT: bosish `fireEvent` bilan qilinadi, `@testing-library/user-event`
 * bilan EMAS — `market-picker.test.tsx` dagi bilan bir xil sabab (tasdiqlangan
 * paket ro'yxatiga kirmaydi).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { MarketRequisitesForm } from "@/components/wizard/market-requisites-form";
import { AuthProvider, clearSession } from "@/lib/auth-store";

const routerMock = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => routerMock,
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

const MARKETS_PATH = "/markets";
const SELECT_MARKET_PATH = "/auth/select-market";

const CREATED_MARKET = {
  id: "55555555-5555-4555-8555-555555555555",
  name: "Karmana markaziy bozori",
  is_active: false,
};

/** uz-Latn kataloglaridagi AYNAN qiymatlar — test shu faylni yuklaydi. */
const SUBMIT_LABEL = "Saqlash va davom etish";
const WEEKDAYS_LEGEND = "Ish kunlari";
const WEEKDAYS_REQUIRED = "Kamida bitta ish kunini belgilang";
const MONDAY_LABEL = "Dushanba";
const SUNDAY_LABEL = "Yakshanba";

/** Yuborish uchun majburiy minimum (qolgan maydonlar ixtiyoriy). */
const MARKET_NAME = "Karmana markaziy bozori";
const OPERATING_SINCE = "2020-03-01";

function mockCreateFlow(): void {
  apiFetch.mockImplementation((path: string) => {
    if (path === MARKETS_PATH) return Promise.resolve(CREATED_MARKET);
    if (path === SELECT_MARKET_PATH) {
      return Promise.resolve({
        access_token: "new-token",
        token_type: "bearer",
        expires_in: 900,
        roles: ["platform_admin"],
        market: { id: CREATED_MARKET.id, name: CREATED_MARKET.name },
      });
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

function renderForm(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MarketRequisitesForm />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
}

/** Yuborish uchun zarur maydonlarni to'ldiradi (ish rejimiga TEGMAYDI). */
function fillRequiredFields(): void {
  fireEvent.change(screen.getByLabelText("Bozor nomi"), {
    target: { value: MARKET_NAME },
  });
  fireEvent.change(screen.getByLabelText("Bozor ish boshlagan sana"), {
    target: { value: OPERATING_SINCE },
  });
}

function weekdayBox(label: string): HTMLInputElement {
  return screen.getByLabelText(label) as HTMLInputElement;
}

/**
 * `POST /markets` tanasi — MOCKDAN olinadi, test tomonidan qayta qurilmaydi.
 *
 * Aynan shu narsa tarmoqqa ketadi, ya'ni assert forma holatini emas,
 * SO'ROVNI o'lchaydi: `values.openWeekdays` to'g'ri bo'lib, `onSubmit`
 * uni payload'ga qo'shishni unutgan holat (WR-06 ning o'zi) faqat shu
 * yerda ushlanadi.
 */
function createdBody(): Record<string, unknown> {
  const call = apiFetch.mock.calls.find(
    (args: unknown[]) => args[0] === MARKETS_PATH,
  );
  expect(call, "`POST /markets` umuman chaqirilmadi").toBeDefined();
  const options = (call as unknown[])[1] as { body: Record<string, unknown> };
  return options.body;
}

describe("MarketRequisitesForm — haftalik ish rejimi", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    routerMock.replace.mockReset();
    clearSession();
  });

  afterEach(() => {
    clearSession();
  });

  test("guruh `fieldset`/`legend` bilan keladi va yettala kun BELGILANGAN", () => {
    renderForm();

    /*
     * `getByRole("group")` — `fieldset` ning ARIA roli, `legend` esa uning
     * ochiq nomi (UI-SPEC §11). Test sinf nomiga emas, AYNAN shu semantikaga
     * qaraydi: razmetka o'zgarsa ham a11y shartnomasi qolishi kerak.
     */
    expect(
      screen.getByRole("group", { name: WEEKDAYS_LEGEND }),
    ).toBeInTheDocument();

    for (const label of [
      MONDAY_LABEL,
      "Seshanba",
      "Chorshanba",
      "Payshanba",
      "Juma",
      "Shanba",
      SUNDAY_LABEL,
    ]) {
      expect(weekdayBox(label).checked, `${label} belgilanmagan`).toBe(true);
    }
  });

  test("kun belgisi olib tashlanadi va tanlov saqlanib turadi", () => {
    renderForm();

    fireEvent.click(weekdayBox(MONDAY_LABEL));

    expect(weekdayBox(MONDAY_LABEL).checked).toBe(false);
    // NAZORAT: bitta kunni olib tashlash qolganlariga tegmaydi.
    expect(weekdayBox(SUNDAY_LABEL).checked).toBe(true);
  });

  test("yuborilgan tanlov `open_weekdays` bo'lib payload'ga tushadi", async () => {
    mockCreateFlow();
    renderForm();
    fillRequiredFields();

    // Karmana holati: dushanba yopiq (`0011` docstringidagi misolning o'zi).
    fireEvent.click(weekdayBox(MONDAY_LABEL));
    fireEvent.click(screen.getByRole("button", { name: SUBMIT_LABEL }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        MARKETS_PATH,
        expect.objectContaining({ method: "POST" }),
      );
    });

    /*
     * ⚠ BU ASSERT TUZATISHNING O'ZI: ilgari `open_weekdays` payload'da
     * UMUMAN yo'q edi va `market_create()` uni jimgina `{1..7}` bilan
     * to'ldirardi. `[2,3,4,5,6,7]` — dushanbasiz, ya'ni qiymat HAQIQATAN
     * foydalanuvchi tanlovidan keladi, standartdan emas.
     */
    expect(createdBody().open_weekdays).toEqual([2, 3, 4, 5, 6, 7]);
  });

  test("hamma kun olib tashlanganda forma YUBORILMAYDI va sabab ko'rinadi", async () => {
    mockCreateFlow();
    renderForm();
    fillRequiredFields();

    for (const label of [
      MONDAY_LABEL,
      "Seshanba",
      "Chorshanba",
      "Payshanba",
      "Juma",
      "Shanba",
      SUNDAY_LABEL,
    ]) {
      fireEvent.click(weekdayBox(label));
    }
    fireEvent.click(screen.getByRole("button", { name: SUBMIT_LABEL }));

    expect(await screen.findByText(WEEKDAYS_REQUIRED)).toBeInTheDocument();
    /*
     * Bo'sh to'plam "bozor hech qachon ochilmaydi" degani va u `NULL`
     * ("hali tanlanmagan") dan BOSHQA nosozlik: DB'dagi CHECK uni rad
     * etadi. Klient qatlami esa so'rovni UMUMAN yubormasligi kerak —
     * aks holda foydalanuvchi 422 ni forma xatosi sifatida emas, server
     * xatosi sifatida ko'rardi (§6.8).
     */
    expect(apiFetch).not.toHaveBeenCalledWith(
      MARKETS_PATH,
      expect.anything(),
    );
  });

  test("standart holat: hech nima o'zgartirilmasa yettala kun yuboriladi", async () => {
    mockCreateFlow();
    renderForm();
    fillRequiredFields();

    fireEvent.click(screen.getByRole("button", { name: SUBMIT_LABEL }));

    await waitFor(() => {
      expect(createdBody().open_weekdays).toEqual([1, 2, 3, 4, 5, 6, 7]);
    });
    /*
     * NAZORAT HOLATI: har kuni ishlaydigan bozor BITTA bosishda o'tadi.
     * Usiz "qiymat yuboriladi" da'vosi foydalanuvchini yettala katakchani
     * qo'lda belgilashga majburlaydigan variantdan ham qanoatlanardi — va
     * o'sha variant 1-qadamni sababsiz og'irlashtirardi.
     */
    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalled();
    });
  });

  /* -------------------------------------------------------------------------
   * ⛔ T6 — XATO TUZATILGANDA EKRANDAN CHIQADI (AYNAN 0 -> 1 O'TISHI)
   * ---------------------------------------------------------------------- */

  test("⛔ birinchi kun qayta belgilanganda xato EKRANDAN CHIQADI", async () => {
    mockCreateFlow();
    renderForm();
    fillRequiredFields();

    for (const label of [
      MONDAY_LABEL,
      "Seshanba",
      "Chorshanba",
      "Payshanba",
      "Juma",
      "Shanba",
      SUNDAY_LABEL,
    ]) {
      fireEvent.click(weekdayBox(label));
    }
    fireEvent.click(screen.getByRole("button", { name: SUBMIT_LABEL }));

    await screen.findByText(WEEKDAYS_REQUIRED);

    /*
     * ⛔ AYNAN 0 -> 1 O'TISHI. Eski shart `selectedWeekdays.length > 0`
     *   (toggle'DAN OLDINGI uzunlik) shu yagona o'tishda qayta
     *   validatsiya QILMASDI: foydalanuvchi xatoni tuzatgan lahzada
     *   qizil matn ekranda QOLARDI va u «tuzatdim, lekin hech nima
     *   o'zgarmadi» holatiga tushardi — boshlang'ich nuqsondan ham
     *   chalg'ituvchiroq. Etalon: `create-user-dialog.test.tsx:230-244`.
     */
    fireEvent.click(weekdayBox(MONDAY_LABEL));

    await waitFor(() => {
      expect(screen.queryByText(WEEKDAYS_REQUIRED)).toBeNull();
    });
  });
});
