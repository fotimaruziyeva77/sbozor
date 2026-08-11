/**
 * DL-3 — ⛔ G-28: DALIL KADRI MAVJUD YAGONA MARSHRUTDAN (§11.3, M-8).
 *
 * =============================================================================
 * ⛔⛔ 1. MARSHRUT DA'VOSI DOM'DAGI `src` MATNIDAN EMAS, TARMOQ
 *    YUZASIDAN O'LCHANADI — VA SABAB MEXANIK.
 *
 *   `GET /snapshots/{id}/image` sessiya tokenini talab qiladi, `<img>`
 *   esa sarlavha qo'sha olmaydi. Shuning uchun baytlar `apiRequest`
 *   bilan olinadi va brauzer ichidagi VAQTINCHALIK havolaga aylanadi —
 *   ya'ni DOM'dagi `src` HAR DOIM o'sha havola bo'ladi, marshrut emas.
 *
 *   `src` ni marshrut MATNIGA tenglashtiradigan da'vo ikki yo'ldan
 *   birini majburlardi: (a) tokensiz `<img src>` — ishlab turgan
 *   ekranda 401 beradigan SINGAN kod; (b) sessiya tokenini URL'ga
 *   qo'yish — oldindan avtorizatsiyalangan havolaning aynan o'zi
 *   (§14.2 taqiqlaydi). Ikkalasi ham darvozani qondirib, MAHSULOTNI
 *   buzardi.
 *
 *   Shuning uchun da'vo `apiRequest` GA BERILGAN YO'LLAR TO'PLAMIGA
 *   qo'yiladi — `review-session.test.tsx:339-350` ning aynan naqshi.
 *   ⛔ Bu KUCHAYTIRISH, yumshatish emas: yo'l to'plami tengligi ikkinchi
 *   manbani ham (imzolangan havola, `s3`, boshqa proxy) qizartiradi,
 *   holbuki `src` regeksi faqat BITTA elementning matnini ko'rardi.
 *
 * ⛔ 2. `snapshot_id === null` -> `img` SONI AYNAN 0.
 *
 *   Bu 05-14 ning darsi: marshrut bermagan qatorni to'qish (stub) ham,
 *   «yuklanmadi» platsholderi ham RAD ETILGAN. Ikkala shox ham BITTA
 *   testda o'lchanadi — bittasi yolg'iz qolsa, «dalil bo'limi umuman
 *   chizilmadi» holatida ham yashil bo'lardi.
 *
 * ⛔ 3. IDENTIFIKATORLAR TO'PLAMI TENGLIGI (D-31) — `tariff_id` ning
 *   yo'qligi bitta nomni inkor qilish bilan emas, KO'RINADIGAN
 *   identifikatorlar to'plamining tengligi bilan o'lchanadi. Inkor
 *   matcher faqat O'SHA nomni ushlardi va yonidagi yangi identifikatorni
 *   ko'rmasdi.
 *   ⚠ Matcher nomi bu izohda LITERAL yozilmaydi (kodbaza konvensiyasi,
 *     `badge.tsx:24-26`): qabul mezoni uni `grep` bilan sanaydi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiRequest: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: apiClientMock.apiFetch,
    apiRequest: apiClientMock.apiRequest,
  };
});

import messages from "../../../messages/uz-Latn.json";
import {
  ChargeDetailDialog,
  shortChargeId,
} from "@/components/billing/charge-detail-dialog";
import type { ChargeDetail, ChargeRow } from "@/lib/billing-charge-queries";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const CHARGE_ID = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa";
const TARIFF_ID = "dddddddd-4444-4444-8444-dddddddddddd";
const SNAPSHOT_A = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb";
const SNAPSHOT_B = "cccccccc-3333-4333-8333-cccccccccccc";
const ACTOR_ID = "eeeeeeee-5555-4555-8555-eeeeeeeeeeee";

const CHARGE: ChargeRow = {
  charge_id: CHARGE_ID,
  stall_code: "14-C",
  vendor_id: "ffffffff-6666-4666-8666-ffffffffffff",
  service_date: "2026-08-09",
  tariff_amount_soum: 15_000,
  amount_soum: 15_000,
  outstanding_soum: 0,
};

function detail(overrides: Partial<ChargeDetail> = {}): ChargeDetail {
  return {
    charge_id: CHARGE_ID,
    service_date: "2026-08-09",
    stall_code: "14-C",
    tariff_amount_soum: 15_000,
    amount_soum: 15_000,
    adjustments: [],
    evidence: [],
    ...overrides,
  };
}

/** Kadr baytlari — `apiRequest` `Response` qaytaradi. */
function imageOk(): void {
  apiClientMock.apiRequest.mockResolvedValue({
    blob: () => Promise.resolve(new Blob(["x"], { type: "image/jpeg" })),
  });
}

/** `GET /billing/charges/{id}` va `GET /users` — yo'l bo'yicha marshrutlash. */
function routeFetch(data: ChargeDetail): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/billing/charges/")) return Promise.resolve(data);
    if (path.startsWith("/users")) {
      return Promise.resolve({
        items: [
          {
            id: ACTOR_ID,
            phone: "+998900000001",
            full_name: "Nazorat Aliyev",
            roles: ["director"],
            is_active: true,
            must_change_password: false,
            locale: "uz-Latn",
            created_at: "2026-08-01T05:00:00Z",
          },
        ],
      });
    }
    return Promise.resolve({ items: [] });
  });
}

let client: QueryClient;

function renderDialog() {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <ChargeDetailDialog charge={CHARGE} onOpenChange={() => {}} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/** `apiRequest` ga berilgan YO'LLAR to'plami — tarmoq yuzasining o'zi. */
function requestedPaths(): Set<string> {
  return new Set(
    (apiClientMock.apiRequest.mock.calls as [string][]).map(([path]) => path),
  );
}

/**
 * ⛔ DIALOG ILDIZI — `render()` NING `container` I EMAS.
 *
 * Radix `Dialog.Content` ni PORTAL bilan `document.body` ga chiqaradi,
 * ya'ni `container.querySelectorAll(...)` dialog ichidagi hech narsani
 * KO'RMAYDI va har qanday «... soni 0» da'vosi JIMGINA rost bo'lardi.
 * Bu aynan 05-15 ning S-D sinfi: sabotaj sistemaga yetib boradi, lekin
 * tanlangan YUZA ikkala shoxda ham bir xil javob beradi. Shuning uchun
 * hamma DOM da'vosi SHU ildizdan o'lchanadi.
 */
function dialogRoot(): HTMLElement {
  return screen.getByRole("dialog");
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  setSession({
    accessToken: "test-access-token",
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
  // jsdom `createObjectURL` ni bilmaydi.
  globalThis.URL.createObjectURL = vi.fn(() => "blob:evidence");
  globalThis.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* 1. G-28 — DALIL KADRI                                                      */
/* -------------------------------------------------------------------------- */

describe("⛔ G-28: dalil kadri MAVJUD YAGONA marshrutdan", () => {
  test("⛔ so'ralgan yo'llar to'plami AYNAN `/snapshots/{id}/image` — HAR BIRI", async () => {
    imageOk();
    routeFetch(
      detail({
        evidence: [
          { snapshot_id: SNAPSHOT_A, slot_time: "2026-08-09T06:30:00Z" },
          { snapshot_id: SNAPSHOT_B, slot_time: "2026-08-09T09:30:00Z" },
        ],
      }),
    );
    renderDialog();

    await waitFor(() => expect(screen.getAllByRole("img").length).toBe(2));

    /*
     * ⛔ TO'PLAM TENGLIGI: ikkinchi manba (imzolangan havola, boshqa
     *   proxy, obyekt ombori) bu yerda DARHOL qizaradi.
     */
    expect(requestedPaths()).toEqual(
      new Set([
        `/snapshots/${SNAPSHOT_A}/image`,
        `/snapshots/${SNAPSHOT_B}/image`,
      ]),
    );

    /* Har bir yo'l shablonga MOS — regeks bilan, har biri alohida. */
    for (const path of requestedPaths()) {
      expect(
        /^\/snapshots\/[0-9a-f-]{36}\/image$/u.test(path),
      ).toBe(true);
    }
  });

  test("⛔ `snapshot_id` YO'Q element uchun `img` soni 0 — kadri BOR element bilan BIR TESTDA", async () => {
    imageOk();
    routeFetch(
      detail({
        evidence: [
          { snapshot_id: null, slot_time: "2026-08-09T06:30:00Z" },
          { snapshot_id: SNAPSHOT_A, slot_time: "2026-08-09T09:30:00Z" },
        ],
      }),
    );
    renderDialog();

    /*
     * ⛔ IKKI ELEMENT, BITTA KADR. Yolg'iz `null` bilan yozilgan test
     *   «dalil bo'limi umuman chizilmadi» holatida ham yashil bo'lardi —
     *   farq shu yerda O'LCHANADI.
     */
    await waitFor(() => expect(screen.getAllByRole("img").length).toBe(1));
    expect(requestedPaths()).toEqual(
      new Set([`/snapshots/${SNAPSHOT_A}/image`]),
    );
  });

  test("⛔ hamma element dalilsiz bo'lsa `img` AYNAN 0 (platsholder ham yo'q)", async () => {
    imageOk();
    routeFetch(
      detail({
        evidence: [{ snapshot_id: null, slot_time: "2026-08-09T06:30:00Z" }],
      }),
    );
    renderDialog();

    /* NAZORAT: bo'lim CHIZILDI — ya'ni «0 kadr» da'vosi bo'sh ekranni emas. */
    await screen.findByText(messages.billing.evidenceTitle);
    expect(dialogRoot().querySelectorAll("img").length).toBe(0);
    expect(requestedPaths()).toEqual(new Set());
  });

  test("⛔ kadrda `crossOrigin` atributi YO'Q", async () => {
    imageOk();
    routeFetch(
      detail({
        evidence: [
          { snapshot_id: SNAPSHOT_A, slot_time: "2026-08-09T06:30:00Z" },
        ],
      }),
    );
    renderDialog();

    const image = await screen.findByRole("img");
    expect(image.hasAttribute("crossorigin")).toBe(false);
    /* Havola brauzer ichida — sahifadan tashqariga chiqmaydi. */
    expect(image.getAttribute("src")).toBe("blob:evidence");
    /*
     * ⛔ TASHQARIGA CHIQADIGAN HAVOLA TO'PLAMI BO'SH — bu «yuklab olish
     *   atributi yo'q» dan KUCHLIROQ: atributsiz havola ham kadrni yangi
     *   tabda ochib, manzilni ko'rsatib qo'yardi. Kanvas ham yo'q, ya'ni
     *   piksellardan nusxa olish yo'li umuman qurilmagan (§14.2).
     *   ⚠ Taqiqlangan atribut nomi bu yerda LITERAL yozilmaydi — qabul
     *     mezoni uni `grep` bilan sanaydi (kodbaza konvensiyasi).
     */
    expect(dialogRoot().querySelectorAll("a").length).toBe(0);
    expect(dialogRoot().querySelectorAll("canvas").length).toBe(0);
  });
});

/* -------------------------------------------------------------------------- */
/* 2. D-07 — O'ZGARMASLIK JUMLASI HAR DOIM                                    */
/* -------------------------------------------------------------------------- */

describe("⛔ D-07: «Bu hisob o'zgartirilmaydi» — SHARTSIZ", () => {
  test("⛔ tuzatish YO'Q holatda ham jumla ko'rinadi", async () => {
    imageOk();
    routeFetch(detail({ adjustments: [] }));
    renderDialog();

    expect(
      await screen.findByText(messages.billing.immutableNotice),
    ).toBeInTheDocument();
  });

  test("tuzatish BOR holatda ham jumla ko'rinadi", async () => {
    imageOk();
    routeFetch(
      detail({
        amount_soum: 12_000,
        adjustments: [
          {
            adjustment_id: "99999999-9999-4999-8999-999999999999",
            direction: "decrease",
            amount_soum: 3_000,
            reason_code: "partial_day",
            actor_user_id: ACTOR_ID,
            created_at: "2026-08-10T05:00:00Z",
          },
        ],
      }),
    );
    renderDialog();

    expect(
      await screen.findByText(messages.billing.immutableNotice),
    ).toBeInTheDocument();
  });

  test("⛔ tuzatish bo'lmaganda «Tuzatish yo'q» jumlasi KO'RINADI (nol — natija)", async () => {
    imageOk();
    routeFetch(detail({ adjustments: [] }));
    renderDialog();

    expect(
      await screen.findByText(messages.billing.noAdjustments),
    ).toBeInTheDocument();
  });

  test("tuzatish sabab-kodi TARJIMA qilinadi — xom kod ekranga chiqmaydi", async () => {
    imageOk();
    routeFetch(
      detail({
        amount_soum: 12_000,
        adjustments: [
          {
            adjustment_id: "99999999-9999-4999-8999-999999999999",
            direction: "decrease",
            amount_soum: 3_000,
            reason_code: "partial_day",
            actor_user_id: ACTOR_ID,
            created_at: "2026-08-10T05:00:00Z",
          },
        ],
      }),
    );
    renderDialog();

    expect(
      await screen.findByText(
        messages.collect.adjustmentReason.partial_day,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(messages.billing.decrease)).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 3. KO'RINADIGAN IDENTIFIKATORLAR — TO'PLAM TENGLIGI (D-31)                 */
/* -------------------------------------------------------------------------- */

describe("⛔ ko'rinadigan identifikator AYNAN BITTA", () => {
  test("⛔ `font-mono` identifikatorlari to'plami = {charge_id qisqa shakli}", async () => {
    imageOk();
    routeFetch(detail());
    renderDialog();

    await screen.findByText(shortChargeId(CHARGE_ID));

    /*
     * ⛔ TO'PLAM TENGLIGI, inkor EMAS: `tariff_id` ham, boshqa har qanday
     *   ⛔ YANGI identifikator ham shu yerda qizaradi. Filtr — 8+ belgili
     *   olti-o'nlik bo'laklar, ya'ni pul va vaqt qiymatlari tushmaydi.
     */
    const idLike = new Set(
      [...dialogRoot().querySelectorAll("*")]
        .filter((node) => node.children.length === 0)
        .map((node) => (node.textContent ?? "").trim())
        .filter((text) => /^[0-9a-f]{8}(-[0-9a-f]{4})*$/u.test(text)),
    );

    expect(idLike).toEqual(new Set([shortChargeId(CHARGE_ID)]));
    /* NAZORAT: to'liq tarif identifikatori DOM matnida umuman yo'q. */
    expect((dialogRoot().textContent ?? "").includes(TARIFF_ID)).toBe(false);
  });
});

/* -------------------------------------------------------------------------- */
/* 4. D-09 — IKKI SUMMA USTUNI FAQAT FARQ BO'LGANDA                           */
/* -------------------------------------------------------------------------- */

describe("⛔ D-09: tarif va hisob summasi", () => {
  test("TENG bo'lganda «Tarif summasi» yorlig'i CHIZILMAYDI", async () => {
    imageOk();
    routeFetch(detail({ tariff_amount_soum: 15_000, amount_soum: 15_000 }));
    renderDialog();

    await screen.findByText(messages.billing.immutableNotice);

    const labels = new Set(
      [...dialogRoot().querySelectorAll("p.text-xs")].map(
        (node) => node.textContent ?? "",
      ),
    );
    expect(labels.has(messages.billing.tariffAmount)).toBe(false);
    expect(labels.has(messages.billing.amount)).toBe(true);
  });

  test("⛔ FARQ bo'lganda IKKALASI ham ko'rinadi — tuzatish borligini aytadi", async () => {
    imageOk();
    routeFetch(detail({ tariff_amount_soum: 15_000, amount_soum: 12_000 }));
    renderDialog();

    expect(
      await screen.findByText(messages.billing.tariffAmount),
    ).toBeInTheDocument();
    expect(screen.getByText(messages.billing.chargeAmount)).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 5. YOZUV YUZASI — TUGMALAR TO'PLAMI TENGLIGI                               */
/* -------------------------------------------------------------------------- */

describe("⛔ D-07: tahrirlash/o'chirish yo'li YO'Q", () => {
  test("⛔ dialogdagi tugmalar to'plami AYNAN {Yopish}", async () => {
    imageOk();
    routeFetch(detail());
    renderDialog();

    await screen.findByText(messages.billing.immutableNotice);

    const dialog = screen.getByRole("dialog");
    const labels = new Set(
      within(dialog)
        .getAllByRole("button")
        .map((node) => (node.textContent ?? "").trim())
        .filter((text) => text.length > 0),
    );

    /*
     * ⛔ Radix `Dialog.Content` o'z yopish tugmasini QO'SHMAYDI (bu
     *   qobiqda `Close` FAQAT footerda), shuning uchun to'plam aynan
     *   bitta. Yangi tugma qo'shilsa darvoza O'ZI qizaradi (D-32).
     */
    expect(labels).toEqual(new Set([messages.common.close]));
  });
});
