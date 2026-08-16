/**
 * QARZDORLIK RO'YXATI — ⛔ ISM SERVERDAN, BO'SHLIGI NOMLANGAN (§8.3, §8.4).
 *
 * =============================================================================
 * ⛔⛔ 1. NEGA «BO'SH KATAK» TESTI BITTA TESTDA IKKI DA'VO YURITADI.
 *
 * D-08 ikki narsani BIR VAQTDA talab qiladi va ular bir-birini
 * ALMASHTIRA OLMAYDI:
 *
 *   • ⛔ VIZUAL jihatdan BO'SH — na tire, na to'qilgan nom, na «Sotuvchi
 *     #123». To'qilgan qiymat ⛔ MA'LUMOT BORDEK ko'rinadi va u
 *     ⛔ EKSPORTGA HAM TUSHADI: chop etilgan varaqdagi to'qilgan qator
 *     buxgalter uchun HAQIQIY sotuvchi nomi bo'lib o'qilardi.
 *   • ⛔ SEMANTIK jihatdan NOMLANGAN — bo'sh `<td>` skrinriderda
 *     ⛔ JIMGINA o'tadi, ya'ni foydalanuvchi ustunni butunlay
 *     YO'QOTARDI.
 *
 * ⛔ Ikkisini ikki alohida testga ajratish ularning ZIDDIYATINI
 *    yashirardi: «bo'sh» testi `sr-only` matnni ham bo'shlik deb
 *    o'tkazishi, «nomlangan» testi esa ko'rinadigan matnni ham
 *    nom deb o'tkazishi mumkin edi. Farq ⛔ ASSERT BILAN yoziladi —
 *    bevosita matn tugunlari YO'Q, `sr-only` ichidagi matn BOR.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. IKKINCHI SO'ROV YO'QLIGI YO'L TO'PLAMI BILAN o'lchanadi (D-31).
 *
 * «Sotuvchi reestriga so'rov ketmadi» da'vosini bitta mock'ning
 * chaqirilmaganligi bilan yozish ⛔ MA'NOSIZ bo'lardi: komponent o'sha
 * modulni umuman import qilmasa, mock fabrikasi ham ishga tushmaydi va
 * da'vo ⛔ TRIVIAL ROST bo'lib qolardi — ya'ni ertaga BOSHQA nomdagi
 * ikkinchi so'rov qo'shilsa, test buni KO'RMASDI.
 *
 * Shuning uchun `apiFetch` ga borgan BARCHA yo'llar yig'iladi va to'plam
 * KUTILGAN yagona yo'l bilan solishtiriladi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { DebtorsReport } from "@/components/reports/debtors-report";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SERVED_FROM = "2026-09-01";
const SERVED_TO = "2026-09-30";

function freezeClock(dayIso: string): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${dayIso}T12:00:00+05:00`));
  return new Date();
}

/**
 * ⛔ TARTIB SERVERNIKI — qarz bo'yicha KAMAYISH (§8.3). Klient qayta
 *    saralamaydi: ikkinchi saralash server bilan ajralib ketardi va
 *    «eng kattasi kim?» savoliga IKKI xil javob berardi.
 */
const DEBTOR_ROWS = [
  {
    vendor_id: "44444444-4444-4444-8444-444444444444",
    vendor_name: "Alisher Qodirov",
    stall_codes: ["14-C", "15-C"],
    outstanding_soum: 900_000,
    oldest_debt_date: "2026-09-03",
  },
  {
    /*
     * ⛔ BIRIKTIRILMAGAN / O'CHIRILGAN SOTUVCHI — ism SERVERDA HAM YO'Q.
     *   Bu qator (e) testining butun mazmuni.
     */
    vendor_id: null,
    vendor_name: null,
    stall_codes: ["31-A"],
    outstanding_soum: 120_000,
    oldest_debt_date: "2026-09-11",
  },
];

const DEBTORS_RESPONSE = {
  from_date: SERVED_FROM,
  to_date: SERVED_TO,
  rows: DEBTOR_ROWS,
  total_outstanding_soum: 1_020_000,
  row_count: 2,
  shown_count: 2,
};

function openSession() {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles: ["director"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  openSession();
});

afterEach(() => {
  vi.useRealTimers();
});

/** `apiFetch` ga borgan yo'llar — so'rov satrisiz, TO'PLAM sifatida. */
function requestedPaths(): Set<string> {
  return new Set(
    apiClientMock.apiFetch.mock.calls.map((call) =>
      String(call[0]).split("?")[0],
    ),
  );
}

async function renderDebtors(response: unknown): Promise<RenderResult> {
  const now = freezeClock("2026-10-15");

  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reports/debtors")) return Promise.resolve(response);
    /*
     * ⚠ BOSHQA MARSHRUT RAD ETILMAYDI, JAVOB BERILADI: rad etish (f)
     *   testini «so'rov yiqildi» sababidan yashil qilardi, holbuki da'vo
     *   so'rovning UMUMAN YUBORILMAGANI haqida.
     */
    return Promise.resolve({ items: [], next_cursor: null });
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={now}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams={`?from=${SERVED_FROM}&to=${SERVED_TO}`}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <DebtorsReport />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );

  await waitFor(() => {
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

/* -------------------------------------------------------------------------- */
/* (e) TOPILMAGAN ISM — BO'SH, LEKIN NOMLANGAN (§8.4, D-08)                   */
/* -------------------------------------------------------------------------- */

describe("⛔ topilmagan ism — BO'SH KATAK, LEKIN NOMLANGAN", () => {
  test("katakda ko'rinadigan matn YO'Q, `sr-only` nomi esa BOR", async () => {
    const view = await renderDebtors(DEBTORS_RESPONSE);

    const rows = [...view.container.querySelectorAll("tbody tr")];
    expect(rows).toHaveLength(DEBTOR_ROWS.length);

    /* Ism — birinchi ustun: sotuvchi · rasta(lar) · qarz · eng eski qarz. */
    const namedCell = rows[0].querySelectorAll("td")[0];
    const unknownCell = rows[1].querySelectorAll("td")[0];

    /*
     * ⛔ NAZORAT: ism BOR bo'lgan katak HAQIQATAN chiziladi. Busiz
     *   pastdagi «bo'sh» da'vosi «ustun umuman chizilmagan» holatida
     *   ham yashil qolardi.
     */
    expect(namedCell.textContent).toContain("Alisher Qodirov");

    /*
     * ⛔ BIRINCHI YARIM — VIZUAL BO'SHLIK: katakda skrinriderga
     *   YASHIRILMAGAN biror matn ⛔ YO'Q.
     *
     * ⚠⚠ BU ASSERT SABOTAJ BILAN QAYTA YOZILDI (o'lchov, 08-13 Task 3).
     *   Dastlabki shakli katakning BEVOSITA matn tugunlarini sanardi va
     *   u ⛔ YOLG'ON-YASHIL edi: `<span>` ichiga o'ralgan to'qilgan
     *   qiymat bevosita tugun EMAS, ya'ni «tire qo'shildi» sabotaji bu
     *   yarmini UMUMAN qizartirmasdi (o'lchandi). Haqiqiy da'vo esa
     *   ⛔ KO'RINADIGAN matn haqida, razmetka chuqurligi haqida emas —
     *   shuning uchun `sr-only` shajaralari AYIRILADI.
     */
    const hiddenText = [...unknownCell.querySelectorAll(".sr-only")]
      .map((node) => node.textContent ?? "")
      .join("");
    const visibleText = (unknownCell.textContent ?? "")
      .replace(hiddenText, "")
      .trim();
    expect(visibleText).toBe("");

    /*
     * ⛔ IKKINCHI YARIM — SEMANTIK NOM: bo'sh `<td>` skrinriderda
     *   jimgina o'tardi. Farq AYNAN shu ikki assert orasida.
     */
    const screenReaderOnly = unknownCell.querySelector(".sr-only");
    expect(screenReaderOnly?.textContent).toBe(messages.reports.vendorUnknown);

    /* ⛔ Va bu nom EKRANDA KO'RINMAYDI — `sr-only` sinfi bilan. */
    expect(unknownCell.textContent?.trim()).toBe(
      messages.reports.vendorUnknown,
    );
  });
});

/* -------------------------------------------------------------------------- */
/* (f) IKKINCHI SO'ROV YO'Q — ISM SERVERDA JOINLANADI (D-07)                  */
/* -------------------------------------------------------------------------- */

describe("⛔ ism SERVERDAN keladi", () => {
  test("faqat BITTA marshrutga so'rov ketadi — sotuvchi reestriga EMAS", async () => {
    await renderDebtors(DEBTORS_RESPONSE);

    /*
     * ⛔ TO'PLAM TENGLIGI: «/vendors chaqirilmadi» shaklidagi inkor
     *   da'vo ertaga qo'shilgan BOSHQA nomdagi ikkinchi so'rovni
     *   ko'rmasdi. Bu shakl esa har qanday qo'shimcha yo'lda qizaradi.
     *
     * ⛔ Sabab MEXANIK, tejamkorlik emas: har hisobot so'rovi AYNAN
     *   BITTA `audit_read` yozadi (D-07). Ikkinchi so'rov auditni
     *   sotuvchi boshiga yozardi va hisobot marshrutining butun
     *   ajratilishi ma'nosiz bo'lardi.
     */
    expect(requestedPaths()).toEqual(new Set(["/reports/debtors"]));
  });
});

/* -------------------------------------------------------------------------- */
/* (g) JAMI QARZ — ⛔ Display OLMAYDI (§7.2)                                  */
/* -------------------------------------------------------------------------- */

describe("⛔ jami qarz Display OLMAYDI", () => {
  test("yig'indi `text-lg` oladi, ⛔ `text-2xl` OLMAYDI", async () => {
    const view = await renderDebtors(DEBTORS_RESPONSE);

    const term = screen.getByText(messages.reports.debtorsTotal);
    const value = term.parentElement?.querySelector("dd");
    expect(value).not.toBeNull();

    /*
     * ⛔ QARZ — SALBIY ko'rsatkich. Uni tushum bilan TENG kattalikda
     *   chizish sahifani «ikki katta raqam, qaysi biri yaxshi?» qilardi
     *   (§7.2). Display sahifada AYNAN BITTA va u davr tushuminiki.
     */
    expect(value?.className).toContain("text-lg");
    expect(value?.className).not.toContain("text-2xl");

    /* Rang kanali + ustun sarlavhasi «Qarz» — ikkinchi kanal (§13.4). */
    expect(value?.className).toContain("text-danger-text");
    expect(screen.getByText(messages.reports.debtColumn)).toBeInTheDocument();
  });
});
