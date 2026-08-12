/**
 * ⛔ G-31 (07-UI-SPEC) NING DOM YARMI — HOLAT TO'PLAMI YOPIQ VA U REYESTRDAN.
 *
 * =============================================================================
 * ⛔⛔ NEGA `<option>` LARNI REYESTR BILAN SOLISHTIRAMIZ.
 *
 * `scripts/reconciliation-copy.test.mjs` reyestrning O'ZINI va uning
 * uchala tildagi matnini o'lchaydi. Lekin u ⛔ EKRANGA QARAMAYDI: qo'lda
 * yozilgan `<option>` ro'yxati reyestr o'sganda ⛔ ORTDA QOLARDI va
 * beshinchi holat ⛔ TANLAB BO'LMAYDIGAN bo'lib qolardi — direktor uni
 * ro'yxatda ko'rardi (navbatda), lekin dialogda ⛔ QO'YA OLMASDI.
 *
 * ⛔ DA'VO TO'PLAM TENGLIGI BILAN: «`justified` bormi?» tekshiruvi
 *    ortiqcha `other` a'zosini KO'RMASDI — va aynan o'sha a'zo erkin
 *    matnni qaytarib keltirib, aniqlik ulushining MAXRAJINI
 *    aniqlanmagan qilardi.
 * =============================================================================
 *
 * ⛔⛔ IKKINCHI DA'VO — HUQUQ YO'Q BO'LGANDA YOZUV YUZASI ⛔ UMUMAN YO'Q.
 *
 * ⛔ O'CHIRILGAN TUGMA ⛔ YARAMAYDI: u MAVJUD IMKONIYATNI e'lon qilardi.
 *    Shuning uchun da'vo «o'chirilganmi?» emas, ⛔ «BORMI?» — va u
 *    interaktiv elementlar to'plamining TENGLIGI bilan yoziladi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/reconciliation",
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { CaseDetailDialog } from "@/components/reconciliation/case-detail-dialog";
import { CASE_STATUSES } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const CASE_ID = "22222222-2222-4222-8222-222222222222";
const USER_ID = "33333333-3333-4333-8333-333333333333";
const SNAPSHOT_ID = "44444444-4444-4444-8444-444444444444";
const DAY = "2026-08-11";

function detail(overrides: Record<string, unknown> = {}) {
  return {
    case_id: CASE_ID,
    subject_kind: "occupied_unpaid",
    anomaly_id: null,
    charge_id: CASE_ID,
    service_date: DAY,
    status: "new",
    assignee_user_id: null,
    created_at: `${DAY}T04:25:00Z`,
    resolution_note: null,
    events: [
      {
        from_status: null,
        to_status: "new",
        actor_user_id: null,
        note: null,
        created_at: `${DAY}T04:25:00Z`,
      },
    ],
    evidence_snapshot_ids: [SNAPSHOT_ID],
    ...overrides,
  };
}

/** PATCH chaqiruvlari — «bitta so'rov = bitta qaror» qulfining o'lchovi. */
const patchCalls: unknown[] = [];

function routeFetch(current = detail()) {
  patchCalls.length = 0;

  apiClientMock.apiFetch.mockImplementation(
    (path: string, options?: { method?: string; body?: unknown }) => {
      if (path.startsWith("/reconciliation/cases/")) {
        if (options?.method === "PATCH") {
          patchCalls.push(options.body);
          return Promise.resolve(detail({ status: "in_review" }));
        }
        return Promise.resolve(current);
      }
      if (path.startsWith("/users")) {
        return Promise.resolve({
          items: [
            {
              id: USER_ID,
              phone: "+998900000000",
              full_name: "Test Direktor",
              roles: ["director"],
              is_active: true,
              must_change_password: false,
              locale: "uz-Latn",
              created_at: `${DAY}T00:00:00Z`,
            },
          ],
        });
      }
      return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
    },
  );
}

function session(roles: string[]) {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: USER_ID,
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
}

async function renderDialog() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <CaseDetailDialog caseId={CASE_ID} onOpenChange={vi.fn()} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  /* ⛔ Dialog PORTALGA chiziladi — qidiruv `document.body` bo'ylab. */
  await waitFor(() => {
    expect(screen.getByRole("dialog")).not.toBeNull();
    expect(document.body.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

function dialogNode(): HTMLElement {
  return screen.getByRole("dialog");
}

beforeEach(() => {
  vi.resetAllMocks();
  session(["director"]);
  routeFetch();
});

/* -------------------------------------------------------------------------- */
/* (c) `<option>` QIYMATLARI TO'PLAMI = REYESTR                               */
/* -------------------------------------------------------------------------- */

describe("⛔ G-31 (c): holat to'plami YOPIQ va REYESTRGA TENG", () => {
  test("⛔ `<option>` QIYMATLARI to'plami reyestrga AYNAN TENG", async () => {
    await renderDialog();

    const select = within(dialogNode()).getByLabelText(
      messages.recon.caseStatusLabel,
    ) as HTMLSelectElement;

    const values = [...select.options]
      .map((option) => option.value)
      /* ⛔ Platsholder (`value=""`) reyestr a'zosi EMAS — u tanlov emas. */
      .filter((value) => value !== "");

    expect(new Set(values)).toEqual(new Set(CASE_STATUSES));
  });

  test("⛔ HAR a'zoning matni REYESTRDAN iteratsiya bilan tekshiriladi", async () => {
    await renderDialog();

    const select = within(dialogNode()).getByLabelText(
      messages.recon.caseStatusLabel,
    ) as HTMLSelectElement;

    for (const status of CASE_STATUSES) {
      const option = [...select.options].find((item) => item.value === status);
      expect(option?.textContent).toBe(messages.recon.caseStatus[status]);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* (d) HOLAT UCHUN ERKIN MATNLI MAYDON YO'Q                                   */
/* -------------------------------------------------------------------------- */

describe("⛔ G-31 (d): holat uchun erkin matnli maydon yo'q", () => {
  test("⛔ DL-5 da `type=\"text\"` maydon UMUMAN yo'q", async () => {
    await renderDialog();

    /*
     * ⛔ Erkin matnli holat maydoni beshinchi a'zoni qaytarib keltirardi
     *   va aniqlik ulushining MAXRAJI aniqlanmagan bo'lib qolardi.
     *
     * ⚠ `<textarea>` — BOSHQA element va u QONUNIY (yechim matni,
     *   §9.3 ning ochiq istisnosi). Da'vo AYNAN `input[type=text]` ni
     *   o'lchaydi.
     */
    expect(dialogNode().querySelectorAll('input[type="text"]')).toHaveLength(0);
    expect(
      dialogNode().querySelectorAll("input:not([type])"),
    ).toHaveLength(0);

    /* NAZORAT: yechim maydoni CHIZILGAN, ya'ni forma bo'sh emas. */
    expect(dialogNode().querySelectorAll("textarea")).toHaveLength(1);
  });
});

/* -------------------------------------------------------------------------- */
/* HUQUQ — YOZUV YUZASI UMUMAN CHIZILMAYDI                                    */
/* -------------------------------------------------------------------------- */

describe("⛔ `dispute_decide` yo'q -> yozuv yuzasi AYNAN NOL", () => {
  test("⛔ bozor admini uchun forma UMUMAN yo'q (o'chirilgan tugma ham emas)", async () => {
    session(["market_admin"]);

    await renderDialog();
    const dialog = dialogNode();

    /*
     * ⛔ TO'PLAM TENGLIGI: «saqlash tugmasi yo'qmi?» da'vosi yonidagi
     *   yangi boshqaruvni (masalan `[Biriktirish]`) KO'RMASDI.
     */
    expect(dialog.querySelectorAll("select")).toHaveLength(0);
    expect(dialog.querySelectorAll("textarea")).toHaveLength(0);
    expect(dialog.querySelectorAll("fieldset")).toHaveLength(0);

    const names = within(dialog)
      .queryAllByRole("button")
      .map((node) => node.textContent?.trim() ?? "");

    /* ⛔ Yagona tugma — dialogni YOPISH (yozuv EMAS). */
    expect(new Set(names)).toEqual(new Set([messages.common.close]));

    /* NAZORAT: dialog O'ZI chizilgan — bo'sh ekran emas. */
    expect(dialog.textContent).toContain(messages.recon.auditTrailTitle);
  });

  test("⛔ direktorda forma BOR (nazorat — yuqoridagi da'vo trivial emas)", async () => {
    await renderDialog();

    expect(dialogNode().querySelectorAll("select")).toHaveLength(2);
    expect(
      within(dialogNode()).getByText(messages.recon.save),
    ).not.toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* YOZUV QOIDALARI — §9.4                                                     */
/* -------------------------------------------------------------------------- */

describe("⛔ §9.4: terminal holat YECHIMSIZ saqlanmaydi", () => {
  test("⛔ yechimsiz terminal holatda `[Saqlash]` `aria-disabled`", async () => {
    await renderDialog();

    const select = within(dialogNode()).getByLabelText(
      messages.recon.caseStatusLabel,
    );
    fireEvent.change(select, { target: { value: "justified" } });

    const save = within(dialogNode()).getByText(messages.recon.save);

    /*
     * ⛔ `aria-disabled`, `disabled` EMAS: `disabled` element fokusni
     *   YO'QOTADI va skrinrider foydalanuvchisi sababni umuman
     *   eshitmasdi (05-UI-SPEC §13.3 dan meros).
     */
    expect(save.getAttribute("aria-disabled")).toBe("true");
    expect(save.hasAttribute("disabled")).toBe(false);

    fireEvent.click(save);
    expect(patchCalls).toHaveLength(0);
  });

  test("⛔ NOL O'TISHDA ham tugma faol emas — YOLG'ON xato matnining oldi olinadi", async () => {
    await renderDialog();

    /*
     * ⛔ Server bir xil holatga o'tishni 409 bilan rad etadi va klient
     *   uni «boshqa foydalanuvchi allaqachon o'zgartirgan» matniga
     *   xaritalaydi. Nol o'tishda esa HECH KIM HECH NIMA QILMAGAN —
     *   ya'ni matn YOLG'ON bo'lardi.
     */
    const save = within(dialogNode()).getByText(messages.recon.save);
    expect(save.getAttribute("aria-disabled")).toBe("true");

    fireEvent.click(save);
    expect(patchCalls).toHaveLength(0);
  });

  test("⛔ UCH TEZ BOSISHDA mutatsiya AYNAN BIR MARTA chaqiriladi", async () => {
    await renderDialog();

    const select = within(dialogNode()).getByLabelText(
      messages.recon.caseStatusLabel,
    );
    fireEvent.change(select, { target: { value: "in_review" } });

    const save = within(dialogNode()).getByText(messages.recon.save);

    /*
     * ⛔ QULF BAND IDENTIFIKATORINI saqlaydi, bayroqni EMAS: render
     *   paytida hisoblangan bayroqni bir hodisa oqimidagi uch bosish
     *   UCHALASI ham ESKI qiymatda ko'rardi va ⛔ UCH AUDIT QATORI
     *   yozilardi (D-14 ning butun mazmuni buzilardi).
     */
    fireEvent.click(save);
    fireEvent.click(save);
    fireEvent.click(save);

    await waitFor(() => {
      expect(patchCalls).toHaveLength(1);
    });

    expect(patchCalls[0]).toEqual({
      status: "in_review",
      resolution_note: null,
      assignee_user_id: null,
    });
  });
});

/* -------------------------------------------------------------------------- */
/* AUDIT IZI — O'ZGARMAS                                                      */
/* -------------------------------------------------------------------------- */

describe("⛔ D-14: audit izi TAHRIRLANMAYDI", () => {
  test("⛔ tarixda tahrirlash/o'chirish boshqaruvi YO'Q", async () => {
    routeFetch(
      detail({
        events: [
          {
            from_status: null,
            to_status: "new",
            actor_user_id: null,
            note: null,
            created_at: `${DAY}T04:25:00Z`,
          },
          {
            from_status: "new",
            to_status: "in_review",
            actor_user_id: USER_ID,
            note: "Ko'rilmoqda",
            created_at: `${DAY}T09:00:00Z`,
          },
        ],
      }),
    );

    await renderDialog();
    const dialog = dialogNode();

    /* ⛔ Ikkala bo'g'in ham chizilgan — tarix QISQARTIRILMAYDI. */
    expect(dialog.querySelectorAll("ol > li")).toHaveLength(2);

    /*
     * ⛔ TIZIM — «noma'lum» EMAS: navbatni cron ochadi va unga odam
     *   biriktirish «kim qaror qildi?» savoliga YOLG'ON javob bo'lardi.
     */
    expect(dialog.textContent).toContain(messages.recon.actorSystem);

    /* ⛔ Yozuv yuzasidagi tugmalar to'plami — TENGLIK bilan. */
    const names = within(dialog)
      .queryAllByRole("button")
      .map((node) => node.textContent?.trim() ?? "");

    expect(new Set(names)).toEqual(
      new Set([messages.common.close, messages.recon.save]),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* DESTRUKTIV AMAL — YO'Q (§14.8)                                             */
/* -------------------------------------------------------------------------- */

test("⛔ §14.8: destruktiv tasdiq yuzasi UMUMAN yo'q", async () => {
  await renderDialog();

  /*
   * ⛔ Bu fazada QAYTARIB BO'LMAYDIGAN amal YO'Q: holat o'zgarishi
   *   append-only va ORQAGA QAYTARILADI. Destruktiv tasdiq «bu amalni
   *   qaytarib bo'lmaydi» deb YOLG'ON gapirardi.
   */
  expect(document.body.querySelectorAll('[role="alertdialog"]')).toHaveLength(0);
  expect(dialogNode().innerHTML).not.toContain("bg-danger text-danger-fg");
});
