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
import { ApiError, NetworkError } from "@/lib/api-client";
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

/**
 * Marshrut mocki.
 *
 * ⛔ PATCH SERVERNI HAQIQATAN O'ZGARTIRADI (`served` yangilanadi): usiz
 *    «ketma-ket ikkinchi qaror» da'vosi YOLG'ON-YASHIL bo'lardi. Muvaffaqiyatdan
 *    keyin `invalidateQueries` tafsilotni qayta so'raydi va agar javob ESKI
 *    holatni qaytarsa, `unchanged` hech qachon `true` bo'lmasdi — ya'ni test
 *    real oqimni emas, o'zi qurgan sun'iy holatni o'lchardi.
 *
 * @param initial birinchi GET javobi.
 * @param options.patchRejectsWith PATCH ni yiqitadigan istisno FABRIKASI
 *   (`ApiError` ham, undan TASHQARIDAGI sinf ham bo'lishi mumkin — B-5).
 * @param options.users `GET /users` javobining qatorlari (WR-09).
 */
function routeFetch(
  /* ⛔ `Record<string, unknown>` ATAYIN: `detail()` ning `resolution_note`
     maydoni `null` deb TORAYTIRILADI va PATCH uni satr bilan yangilaydi. */
  initial: Record<string, unknown> = detail(),
  options: {
    patchRejectsWith?: () => unknown;
    users?: Record<string, unknown>[];
  } = {},
) {
  patchCalls.length = 0;
  let served: Record<string, unknown> = initial;

  apiClientMock.apiFetch.mockImplementation(
    (path: string, opts?: { method?: string; body?: unknown }) => {
      if (path.startsWith("/reconciliation/cases/")) {
        if (opts?.method === "PATCH") {
          patchCalls.push(opts.body);
          if (options.patchRejectsWith !== undefined) {
            return Promise.reject(options.patchRejectsWith());
          }
          const body = opts.body as {
            status: string;
            resolution_note: string | null;
          };
          served = {
            ...served,
            status: body.status,
            resolution_note: body.resolution_note,
          };
          return Promise.resolve(served);
        }
        return Promise.resolve(served);
      }
      if (path.startsWith("/users")) {
        return Promise.resolve({
          items: options.users ?? [
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

    /*
     * ⛔ BO'SH `<textarea>` -> ⛔ BO'SH SATR, `null` EMAS (WR-15). Server
     *   `resolution_note = COALESCE(:note, resolution_note)` yozadi, ya'ni
     *   `null` «tegmang» degani va eski matn QOLIB ketardi.
     */
    expect(patchCalls[0]).toEqual({
      status: "in_review",
      resolution_note: "",
      assignee_user_id: null,
    });
  });
});

/* -------------------------------------------------------------------------- */
/* WR-15 — YECHIM MATNINI TOZALASH VA'DASI BAJARILADI                         */
/* -------------------------------------------------------------------------- */

describe("⛔ WR-15: bo'shatilgan yechim matni SAQLANADI", () => {
  test("⛔ mavjud matn o'chirilib saqlanganda serverga BO'SH SATR ketadi", async () => {
    /*
     * ⛔⛔ NOSOZLIKNING MEXANIKASI: forma `null` yuborardi, server esa
     *     `COALESCE(:note, resolution_note)` bilan uni «O'ZGARTIRMA» deb
     *     o'qirdi. Foydalanuvchi matnni o'chirib saqlardi, forma bo'sh
     *     turardi, bazada esa ESKI matn qolardi — va dialog qayta
     *     ochilganda («useState(detail.resolution_note ?? "")») eski matn
     *     ⛔ QAYTIB CHIQARDI. Bu «o'zgarishim yo'qoldi» taassuroti.
     *
     * ⛔ BO'SH SATR `COALESCE` DA `NULL` EMAS, ya'ni u YOZILADI. Server
     *   sxemasi `str | None` va `StringConstraints` da faqat
     *   `max_length` bor — ⛔ `min_length` YO'Q, ya'ni bo'sh satr
     *   422 bermaydi (o'lchandi: `app/schemas.py::CaseUpdate`).
     */
    routeFetch(detail({ status: "in_review", resolution_note: "Eski matn" }));

    const first = await renderDialog();

    const note = within(dialogNode()).getByLabelText(
      messages.recon.resolutionLabel,
    );
    /* Boshlang'ich holat: eski matn maydonda. */
    expect((note as HTMLTextAreaElement).value).toBe("Eski matn");

    /* ⛔ Maydonni TOZALAYMIZ va holatni o'zgartiramiz (nol o'tish to'siladi). */
    fireEvent.change(note, { target: { value: "   " } });
    fireEvent.change(
      within(dialogNode()).getByLabelText(messages.recon.caseStatusLabel),
      { target: { value: "new" } },
    );
    fireEvent.click(within(dialogNode()).getByText(messages.recon.save));

    await waitFor(() => {
      expect(patchCalls).toHaveLength(1);
    });

    /* ⛔ `null` EMAS: aynan u eski matnni saqlab qolardi. */
    expect(patchCalls[0]).toEqual({
      status: "new",
      resolution_note: "",
      assignee_user_id: null,
    });

    /*
     * ⛔⛔ VA'DANING IKKINCHI YARMI — ⛔ QAYTA OCHILGANDA MAYDON BO'SH.
     *
     * ⛔ DIALOG HAQIQATAN YOPILIB QAYTA OCHILADI (`unmount` + qayta
     *    render), chunki forma holati `useState(detail.resolution_note
     *    ?? "")` bilan ⛔ FAQAT MOUNT paytida o'qiladi. Ochiq dialogda
     *    tekshirish foydalanuvchi terganini o'lchardi, ⛔ SERVER
     *    YOZGANINI emas — ya'ni aynan nosozlik yashiringan joyga
     *    qaramasdi.
     *
     * ⚠ Mock `served` ni HAQIQATAN yangilaydi, ya'ni ikkinchi mount
     *   serverdagi YANGI holatni oladi.
     */
    first.unmount();
    await renderDialog();

    expect(
      (
        within(dialogNode()).getByLabelText(
          messages.recon.resolutionLabel,
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("");
  });

  test("⛔ bo'sh satr AUDIT IZIDA bo'sh tugun qoldirmaydi", async () => {
    /*
     * ⛔ Marshrut AYNI maydonni tarix qatorining izohi qilib ham yozadi
     *   (`reconciliation.py` -> `transition(note=...)`), ya'ni bo'sh satr
     *   audit izida BO'SH `<span>` bo'lib chizilardi. «Izoh yo'q» va
     *   «izoh bo'sh» ekranda BIR XIL ko'rinishi kerak: ⛔ hech nima.
     */
    routeFetch(
      detail({
        events: [
          {
            from_status: "new",
            to_status: "in_review",
            actor_user_id: null,
            note: "",
            created_at: `${DAY}T05:00:00Z`,
          },
        ],
      }),
    );

    await renderDialog();

    const trail = within(dialogNode()).getByRole("list");
    const spans = [...trail.querySelectorAll("span")];
    expect(spans.filter((node) => (node.textContent ?? "") === "")).toEqual([]);
  });
});

/* -------------------------------------------------------------------------- */
/* WR-07 — DIALOGDAGI `service_date` XOM ISO EMAS                             */
/* -------------------------------------------------------------------------- */

test("⛔ WR-07: tafsilotdagi kun MAHALLIYLASHTIRILGAN, xom ISO EMAS", async () => {
  /*
   * ⛔ Xom `{detail.service_date}` uchala tilda ham `2026-08-11` bo'lib
   *   chizilardi, qo'shni blok esa AYNI maydonni mahalliylashtirardi —
   *   ya'ni bir fazada bir maydon IKKI XIL o'qilardi (WR-07).
   */
  await renderDialog();

  const dialog = dialogNode();
  const dayTerm = within(dialog).getByText(messages.recon.dayColumn);
  const dayValue = dayTerm.nextElementSibling;

  expect(dayValue?.textContent).not.toBe(DAY);
  expect(dayValue?.textContent ?? "").toContain("2026");
  expect(dayValue?.textContent ?? "").toMatch(/11/u);
});

/* -------------------------------------------------------------------------- */
/* B-5: YIQILGAN HUKM MUVAFFAQIYATLI HUKMDAN FARQ QILADI                      */
/* -------------------------------------------------------------------------- */

/**
 * Holatni tanlab `[Saqlash]` ni bosadi (yechim matni ixtiyoriy).
 *
 * ⛔ Yordamchi ATAYIN QISQA: har testda takrorlanadigan uch qator o'rniga
 *    bitta chaqiruv qolsa, testning O'ZI nima da'vo qilayotgani ko'rinadi.
 */
function decide(status: string, note?: string): void {
  const dialog = dialogNode();

  fireEvent.change(within(dialog).getByLabelText(messages.recon.caseStatusLabel), {
    target: { value: status },
  });

  if (note !== undefined) {
    fireEvent.change(
      within(dialog).getByLabelText(messages.recon.resolutionLabel),
      { target: { value: note } },
    );
  }

  fireEvent.click(within(dialog).getByText(messages.recon.save));
}

describe("⛔ B-5: HAR saqlash xatosi ekranda MATN bilan ko'rinadi", () => {
  /*
   * ⛔⛔ BU SINFNING NARXI ENG QIMMAT. `reconErrorView()` besh kodni biladi
   *    va qolgan HAMMASI `null` qaytaradi. Chizilmagan `null` yiqilgan
   *    hukmni muvaffaqiyatli hukmdan AJRATIB BO'LMAYDIGAN qilardi:
   *    dialog ochiq, tanlangan holat `<Select>` da turibdi, tugma yana
   *    faol — direktor nizo hujjatini (D-02) YOZILGAN deb hisoblardi.
   *
   * ⚠ `reconciliation-errors.ts` ning modul izohi (106-108) shartnomani
   *   ALLAQACHON yozgan: «Xaritada YO'Q kod `null` qaytaradi va
   *   chaqiruvchi `errors.generic` ga tushadi». Bu darvoza aynan o'sha
   *   yozilgan shartnomani O'LCHAYDI.
   */
  test("⛔ TARMOQ uzilganda (`ApiError` EMAS) `errors.generic` chiziladi", async () => {
    routeFetch(detail(), { patchRejectsWith: () => new NetworkError() });
    await renderDialog();

    decide("in_review");

    const alert = await within(dialogNode()).findByRole("alert");
    expect(alert.textContent).toBe(messages.errors.generic);

    /* ⛔ XOM ISTISNO MATNI EKRANDA YO'Q — faqat lokalizatsiya kaliti. */
    expect(dialogNode().textContent).not.toContain("network_error");
  });

  test("⛔ `429` va `500` — AYNI zaxira matn (kod xaritada YO'Q)", async () => {
    for (const status of [429, 500]) {
      routeFetch(detail(), {
        patchRejectsWith: () => new ApiError(status, ""),
      });
      const view = await renderDialog();

      decide("in_review");

      const alert = await within(dialogNode()).findByRole("alert");
      expect(alert.textContent).toBe(messages.errors.generic);

      /* ⛔ STATUS KODI EKRANGA CHIQMAYDI. */
      expect(dialogNode().textContent).not.toContain(String(status));
      expect(dialogNode().textContent).not.toContain("api_error_");

      view.unmount();
    }
  });

  test("⛔ `market_not_selected` (403) ham JIM O'TMAYDI", async () => {
    /*
     * ⚠ `reconciliation.py:212` bu kodni QAYTARADI, `SERVER_CODE_MAP` da esa
     *   u YO'Q — ya'ni u aynan zaxira shoxidan o'tadigan REAL kod.
     */
    routeFetch(detail(), {
      patchRejectsWith: () => new ApiError(403, "market_not_selected"),
    });
    await renderDialog();

    decide("in_review");

    const alert = await within(dialogNode()).findByRole("alert");
    expect(alert.textContent).toBe(messages.errors.generic);
    expect(dialogNode().textContent).not.toContain("market_not_selected");
  });

  test("⛔ NAZORAT: NOMLANGAN kod hamon sabab+tuzatish JUFTLIGINI chizadi", async () => {
    /*
     * ⛔ Zaxira shoxi NOMLANGAN matnni YUTIB YUBORMASLIGI kerak: usiz
     *   «hamma xato ko'rinadi» tuzatishi «hamma xato BIR XIL ko'rinadi»
     *   regressiyasiga aylanardi va D-02 ning «sabab + nima qilish kerak»
     *   kontrakti jimgina yo'qolardi.
     */
    routeFetch(detail(), {
      patchRejectsWith: () => new ApiError(409, "status_unchanged"),
    });
    await renderDialog();

    decide("in_review");

    const alert = await within(dialogNode()).findByRole("alert");
    expect(alert.textContent).toContain(
      messages.recon.errorCause.case_status_conflict,
    );
    expect(alert.textContent).toContain(
      messages.recon.errorFix.case_status_conflict,
    );
    expect(alert.textContent).not.toContain(messages.errors.generic);
  });
});

/* -------------------------------------------------------------------------- */
/* 07-20 CHEGARASI: `422 assignee_not_in_market` KLIENTDA NOMLANGAN            */
/* -------------------------------------------------------------------------- */

describe("⛔ IKKI REJA CHEGARASI: `assignee_not_in_market` uchidan-uchiga", () => {
  test("⛔ begona bozor xodimini biriktirish NOMLANGAN matn beradi", async () => {
    /*
     * ⛔⛔ BU YAGONA BOG'LANISH VA U AYNAN SINOVDAN O'TMAGAN SINF.
     *
     *   07-20 serverda `422 assignee_not_in_market` ni ochdi (`user_market_
     *   _roles` ustidagi ILOVA QATLAMI — sxemada FK YO'Q, ya'ni bu tekshiruv
     *   YAGONA to'siq). Klientda esa kod xaritalanmagan edi, ya'ni juda
     *   ANIQ va TUZATSA bo'ladigan muammo direktorga `errors.generic`
     *   bo'lib chiqardi: «Kutilmagan xato yuz berdi» — u nima qilishni
     *   bilmasdi.
     *
     * ⛔ DA'VO IKKI TOMONLAMA: nomlangan matn BOR va zaxira matn YO'Q.
     *   Faqat birinchisi B-5 ning zaxira shoxi bilan ham yashil bo'lardi.
     */
    routeFetch(detail(), {
      patchRejectsWith: () => new ApiError(422, "assignee_not_in_market"),
    });
    await renderDialog();

    decide("in_review");

    const alert = await within(dialogNode()).findByRole("alert");
    expect(alert.textContent).toContain(
      messages.recon.errorCause.assignee_not_in_market,
    );
    expect(alert.textContent).toContain(
      messages.recon.errorFix.assignee_not_in_market,
    );
    expect(alert.textContent).not.toContain(messages.errors.generic);

    /* ⛔ XOM SERVER KODI EKRANDA YO'Q. */
    expect(dialogNode().textContent).not.toContain("assignee_not_in_market");
  });
});

/* -------------------------------------------------------------------------- */
/* WR-09: MAS'UL YORLIG'I SHAXSIY MA'LUMOT CHIQARMAYDI                        */
/* -------------------------------------------------------------------------- */

describe("⛔ WR-09: yorliq zaxirasi TELEFON RAQAMI EMAS", () => {
  const NAMELESS_ID = "55555555-5555-4555-8555-555555555555";
  const NAMELESS_PHONE = "+998911234567";
  const NAMED_LABEL = "Nazoratchi Alisher";

  /**
   * ⛔ IKKI XODIM — VA IKKINCHISI «RO'YXAT YUKLANDI» DETEKTORI.
   *
   * Ismsiz xodimning to'g'ri yorlig'i (`id.slice(0, 8)`) `ActorLabel` ning
   * ⛔ YUKLANMAGAN holatdagi zaxirasi bilan AYNAN BIR XIL satr. Ya'ni
   * yolg'iz ismsiz xodim bilan test «tuzatildi» ni «ro'yxat hali
   * kelmadi» dan ⛔ AJRATA OLMASDI va sabotajda ham yashil qolardi.
   * Ismli xodim esa ro'yxat kelganini ⛔ ISHONCHLI bildiradi.
   */
  function mixedStaff() {
    return [
      {
        id: USER_ID,
        phone: "+998900000000",
        full_name: NAMED_LABEL,
        roles: ["director"],
        is_active: true,
        must_change_password: false,
        locale: "uz-Latn",
        created_at: `${DAY}T00:00:00Z`,
      },
      {
        id: NAMELESS_ID,
        phone: NAMELESS_PHONE,
        full_name: null,
        roles: ["controller"],
        is_active: true,
        must_change_password: false,
        locale: "uz-Latn",
        created_at: `${DAY}T00:00:00Z`,
      },
    ];
  }

  /** Tanlagich variantlari — ro'yxat KELGANDAN keyin. */
  async function loadedAssigneeLabels(): Promise<(string | null)[]> {
    return waitFor(() => {
      const select = within(dialogNode()).getByLabelText(
        messages.recon.assigneeLabel,
      ) as HTMLSelectElement;
      const labels = [...select.options].map((option) => option.textContent);
      expect(labels).toContain(NAMED_LABEL);
      return labels;
    });
  }

  test("⛔ ismsiz xodim TANLAGICHDA identifikator bilan yorliqlanadi", async () => {
    routeFetch(detail(), { users: mixedStaff() });
    await renderDialog();

    const labels = await loadedAssigneeLabels();

    expect(labels).toContain(NAMELESS_ID.slice(0, 8));

    /*
     * ⛔ TELEFON RAQAMI — O'zR qonuni ostidagi SHAXSIY MA'LUMOT va u UI
     *   bezagi bo'lolmaydi. Da'vo BUTUN hujjat bo'yicha: raqam
     *   tanlagichda ham, audit izida ham, `title` atributida ham
     *   chiqmasligi kerak.
     */
    expect(document.body.textContent).not.toContain(NAMELESS_PHONE);
    expect(document.body.innerHTML).not.toContain(NAMELESS_PHONE);
  });

  test("⛔ AUDIT IZIDAGI aktor ham telefon raqami bilan yorliqlanmaydi", async () => {
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
            actor_user_id: NAMELESS_ID,
            note: null,
            created_at: `${DAY}T09:00:00Z`,
          },
        ],
      }),
      { users: mixedStaff() },
    );
    await renderDialog();

    /* ⛔ Ro'yxat KELGANIGA ishonch — usiz da'vo trivial yashil bo'lardi. */
    await loadedAssigneeLabels();

    expect(document.body.innerHTML).not.toContain(NAMELESS_PHONE);

    /* NAZORAT: aktor qatori chizilgan va u BO'SH emas. */
    expect(dialogNode().textContent).toContain(NAMELESS_ID.slice(0, 8));
  });
});

/* -------------------------------------------------------------------------- */
/* B-7: KETMA-KET IKKINCHI HAQIQIY QAROR SERVERGA YETADI                      */
/* -------------------------------------------------------------------------- */

describe("⛔ B-7: qulf QARORGA bog'lanadi, case'ga EMAS", () => {
  test("⛔ `new→in_review` dan keyin `in_review→justified` HAQIQATAN yuboriladi", async () => {
    await renderDialog();

    decide("in_review");
    await waitFor(() => {
      expect(patchCalls).toHaveLength(1);
    });

    /*
     * ⛔ ORALIQ DA'VO MAJBURIY: muvaffaqiyatdan keyin tafsilot yangilanadi
     *   va tugma NOL O'TISHDA faol EMAS. Usiz keyingi bosish «qulf
     *   bo'shadimi?» emas, «holat o'zgardimi?» degan boshqa savolni
     *   o'lchardi.
     */
    await waitFor(() => {
      expect(
        within(dialogNode())
          .getByText(messages.recon.save)
          .getAttribute("aria-disabled"),
      ).toBe("true");
    });

    decide("justified", "Hujjat tekshirildi");

    await waitFor(() => {
      expect(patchCalls).toHaveLength(2);
    });

    expect(patchCalls[1]).toEqual({
      status: "justified",
      resolution_note: "Hujjat tekshirildi",
      assignee_user_id: null,
    });

    /* ⛔ Muvaffaqiyatli ikkinchi qarordan keyin xato bloki YO'Q. */
    expect(within(dialogNode()).queryByRole("alert")).toBeNull();
  });

  test("⛔ YIQILGAN qarordan keyin AYNI qarorni QAYTA yuborish mumkin", async () => {
    /*
     * `onSettled` ning ikkinchi yarmi: xatodan keyin ham qulf bo'shaydi.
     * Bu ilgari `onError` bilan ishlagan va u REGRESSIYA bo'lmasligi kerak.
     */
    routeFetch(detail(), {
      patchRejectsWith: () => new ApiError(500, ""),
    });
    await renderDialog();

    decide("in_review");
    await waitFor(() => {
      expect(patchCalls).toHaveLength(1);
    });

    fireEvent.click(within(dialogNode()).getByText(messages.recon.save));
    await waitFor(() => {
      expect(patchCalls).toHaveLength(2);
    });
  });
});

/* -------------------------------------------------------------------------- */
/* WR-16: «YECHIM MAJBURIY» QOIDASI ERISHIB BO'LADIGAN                        */
/* -------------------------------------------------------------------------- */

describe("⛔ WR-16: bloklangan tugmaning SABABI o'qiladi", () => {
  test("⛔ sabab+tuzatish CHIZILADI va `aria-describedby` unga ISHORA qiladi", async () => {
    await renderDialog();

    fireEvent.change(
      within(dialogNode()).getByLabelText(messages.recon.caseStatusLabel),
      { target: { value: "justified" } },
    );

    const save = within(dialogNode()).getByText(messages.recon.save);
    expect(save.getAttribute("aria-disabled")).toBe("true");

    const describedBy = save.getAttribute("aria-describedby");
    expect(describedBy).not.toBeNull();

    const reason = document.getElementById(describedBy as string);
    expect(reason).not.toBeNull();
    expect(reason?.textContent).toContain(
      messages.recon.errorCause.case_resolution_required,
    );
    expect(reason?.textContent).toContain(
      messages.recon.errorFix.case_resolution_required,
    );
  });

  test("⛔ sabab JONLI HUDUD EMAS — u XATO emas, BAJARILMAGAN shart", async () => {
    await renderDialog();

    fireEvent.change(
      within(dialogNode()).getByLabelText(messages.recon.caseStatusLabel),
      { target: { value: "unjustified" } },
    );

    /*
     * ⛔ `role="alert"` YARAMAYDI (§14.9 jonli hududlar qatori: `alert` —
     *   FAQAT xato). Foydalanuvchi hech nimani buzmagan: maydon shunchaki
     *   to'ldirilmagan va `RECON_ERROR_TONE` ham buni `neutral` deb yozgan.
     *
     * ⛔ `role="status"` HAM YARAMAYDI: 07-22 ning G-38 darvozasi bu
     *   katalogda `role="status"` ni AYNAN olti joyga va HAR birini
     *   `aria-busy` bilan BIR elementda bo'lishga qulflagan. Yettinchi
     *   jonli hudud o'sha darvozani qizartirardi — va u haqli bo'lardi:
     *   shart RENDER paytida rost, ya'ni e'lon hech kim kutmagan paytda
     *   yangrardi.
     *
     * ⛔ TO'G'RI KANAL — `aria-describedby`: skrinrider foydalanuvchisi
     *    sababni AYNAN tugmaga fokuslanganda, ya'ni SO'RAGANDA eshitadi.
     */
    expect(within(dialogNode()).queryByRole("alert")).toBeNull();

    const save = within(dialogNode()).getByText(messages.recon.save);
    const reason = document.getElementById(
      save.getAttribute("aria-describedby") as string,
    );
    expect(reason).not.toBeNull();
    expect(reason?.getAttribute("role")).toBeNull();
  });

  test("⛔ yechim yozilgach sabab YO'QOLADI va tugma FAOLLASHADI", async () => {
    await renderDialog();

    fireEvent.change(
      within(dialogNode()).getByLabelText(messages.recon.caseStatusLabel),
      { target: { value: "justified" } },
    );

    const describedBy = within(dialogNode())
      .getByText(messages.recon.save)
      .getAttribute("aria-describedby") as string;

    /* ⛔ Boshlang'ich holat MA'NOLI: usiz quyidagi «yo'qoldi» da'vosi
       hech qachon mavjud bo'lmagan elementni «yo'q» deb topardi. */
    expect(describedBy).not.toBeNull();
    expect(document.getElementById(describedBy)).not.toBeNull();

    fireEvent.change(
      within(dialogNode()).getByLabelText(messages.recon.resolutionLabel),
      { target: { value: "Bozor kengashi qarori" } },
    );

    const save = within(dialogNode()).getByText(messages.recon.save);
    expect(save.getAttribute("aria-disabled")).toBe("false");
    expect(save.getAttribute("aria-describedby")).toBeNull();
    expect(document.getElementById(describedBy)).toBeNull();
  });

  test("⛔ NOL O'TISHDA sabab bloki chizilmaydi (u BOSHQA to'siq)", async () => {
    await renderDialog();

    /*
     * ⛔ NAZORAT: `blocked` uch sababdan iborat va matn FAQAT bittasiga
     *   tegishli. Nol o'tishda «yechim matni kerak» YOLG'ON bo'lardi —
     *   §9.4 ning nol o'tish qarori aynan yolg'on matnning oldini olish
     *   uchun yozilgan.
     */
    const save = within(dialogNode()).getByText(messages.recon.save);
    expect(save.getAttribute("aria-disabled")).toBe("true");
    expect(save.getAttribute("aria-describedby")).toBeNull();
    expect(dialogNode().textContent).not.toContain(
      messages.recon.errorCause.case_resolution_required,
    );
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
