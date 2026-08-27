/**
 * ⛔ G-34 (07-UI-SPEC) NING DOM YARMI — «ISBOTLANGANDAN ORTIQ DA'VO YO'Q».
 *
 * =============================================================================
 * ⛔⛔ NEGA DOM YARMI KERAK, COPY SKANI YETMAYDI.
 *
 * `scripts/reconciliation-copy.test.mjs` ⛔ MATNNI o'lchaydi: «reyestrda
 * nima bo'lsa, uchala tilda matni bor va taqiqlangan leksika yo'q». Bu
 * savol muhim, lekin u ⛔ CHIZILGANINI o'lchamaydi — beshta holatdan
 * to'rttasini chizadigan komponent o'sha darvozani ⛔ MUKAMMAL
 * o'tkazardi (06-fazaning o'lchangan ko'rligi, S-D sinfi).
 *
 * ⛔ VA TESKARISI HAM ROST: bu fayl matnning uchala tilda borligini
 *    ko'rmaydi (u faqat `uz-Latn` ni render qiladi). Ular bir-birini
 *    ⛔ ALMASHTIRMAYDI.
 * =============================================================================
 *
 * ⛔ IKONKA DA'VOSI SINF NOMI BO'YICHA: ikkala ikonka ham `svg` chizadi,
 *    ya'ni «svg bormi?» hech nimani ajratmasdi. Kutubxona ikonka nomini
 *    kebab-case sinf sifatida qo'yadi va ikki belgili variant ⛔ BOSHQA
 *    sinf oladi — shuning uchun da'vo AYNAN o'sha ikki sinf ustidan
 *    yuradi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { DeliveryList } from "@/components/reconciliation/delivery-list";
import { DELIVERY_STATES } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { deliveryListSchema } from "@/lib/reconciliation-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const VENDOR_ID = "33333333-3333-4333-8333-333333333333";
const DAY = "2026-08-12";

/**
 * ⛔ TELEGRAM IDENTIFIKATORI — DOM SKANINING NISHONI.
 *
 * Qiymat javobda UMUMAN yo'q (server uni qaytarmaydi), lekin da'vo
 * ⛔ KELAJAKKA mo'ljallangan: kimdir uni «qulaylik uchun» qo'shsa,
 * quyidagi skan DARHOL qizaradi.
 */
const TELEGRAM_ID = "7600000000";

const FORBIDDEN_DOM_TOKENS = [
  "chat_id",
  "chatId",
  "telegram_user_id",
  "telegramUserId",
  "telegram_username",
  TELEGRAM_ID,
];

function row(status: string, overrides: Record<string, unknown> = {}) {
  return {
    outbox_id: `55555555-5555-4555-8555-55555555000${DELIVERY_STATES.indexOf(
      status as (typeof DELIVERY_STATES)[number],
    )}`,
    kind: "payment_receipt",
    recipient_kind: "vendor",
    vendor_id: VENDOR_ID,
    status,
    attempt_count: 1,
    created_at: `${DAY}T09:15:00Z`,
    updated_at: `${DAY}T09:15:02Z`,
    error_type: null,
    error_status_code: null,
    ...overrides,
  };
}

function envelope(
  rows: ReturnType<typeof row>[],
  nextCursor: string | null = null,
) {
  return {
    day: DAY,
    rows,
    pending_count: rows.filter((r) => r.status === "pending").length,
    sent_count: rows.filter((r) => r.status === "sent").length,
    delivered_count: rows.filter((r) => r.status === "delivered").length,
    failed_count: rows.filter((r) => r.status === "failed").length,
    blocked_count: rows.filter((r) => r.status === "blocked").length,
    next_cursor: nextCursor,
  };
}

function routeFetch(rows: ReturnType<typeof row>[]) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reconciliation/delivery")) {
      return Promise.resolve(envelope(rows));
    }
    if (path.startsWith("/vendors")) {
      return Promise.resolve({ items: [], next_cursor: null });
    }
    return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
  });
}

async function renderList(isToday = true) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <DeliveryList day={DAY} isToday={isToday} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  await waitFor(() => {
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
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
  routeFetch(DELIVERY_STATES.map((state) => row(state)));
});

/* -------------------------------------------------------------------------- */
/* (a) BESHALA HOLAT CHIZILADI — REYESTRDAN ITERATSIYA                        */
/* -------------------------------------------------------------------------- */

describe("⛔ G-34 (a): beshala holat va ularning matni", () => {
  test("⛔ HAR holat REYESTRDAN iteratsiya bilan tekshiriladi", async () => {
    const { container } = await renderList();

    /*
     * ⛔ SIKL REYESTR USTIDAN: qo'lda yozilgan ro'yxat reyestr o'sganda
     *   ORTDA qolardi va oltinchi holat CHIZILMAGAN holda darvoza
     *   yashil qaytardi (D-32).
     */
    for (const state of DELIVERY_STATES) {
      expect(container.textContent).toContain(
        messages.recon.deliveryState[state],
      );
    }

    expect(container.querySelectorAll("tbody tr")).toHaveLength(
      DELIVERY_STATES.length,
    );
  });

  test("⛔ BESHALA HISOBLAGICH nol bo'lganda HAM chiziladi", async () => {
    routeFetch([row("pending")]);

    const { container } = await renderList();

    /*
     * ⛔ «Bugun aloqa uzilmagan» bilan «hisoblagich ishlamayapti» bir
     *   xil ko'rinsa, direktor D-02 nizosida noto'g'ri xulosaga kelardi.
     */
    const counters = container.querySelectorAll("dl > div");
    expect(counters).toHaveLength(DELIVERY_STATES.length);
    for (const state of DELIVERY_STATES) {
      expect(container.textContent).toContain(
        messages.recon.deliveryState[state],
      );
    }
  });
});

/* -------------------------------------------------------------------------- */
/* B-6 — YETKAZILGANLIK RO'YXATI HAM JIM QIRQILMAYDI                          */
/* -------------------------------------------------------------------------- */

describe("⛔ B-6: yetkazilganlik ro'yxati ham sahifalanadi", () => {
  const CURSOR = `${DAY}T09:15:00+00:00|55555555-5555-4555-8555-555555555009`;

  /** Ikki sahifali server — kursor BOR/YO'Q bo'yicha shox tanlanadi. */
  function routeTwoPages() {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.startsWith("/reconciliation/delivery")) {
        return Promise.resolve(
          path.includes("cursor=")
            ? envelope([row("failed")], null)
            : envelope([row("delivered"), row("pending")], CURSOR),
        );
      }
      if (path.startsWith("/vendors")) {
        return Promise.resolve({ items: [], next_cursor: null });
      }
      return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
    });
  }

  test("⛔ `next_cursor` bo'lganda [Yana yuklash] bor va u qator QO'SHADI", async () => {
    routeTwoPages();

    const { container } = await renderList();

    expect(container.querySelectorAll("tbody tr")).toHaveLength(2);

    const more = screen.getByRole("button", { name: messages.recon.loadMore });
    fireEvent.click(more);

    /* ⛔ QO'SHADI, ALMASHTIRMAYDI: kursor kesh kalitida bo'lsa 2 -> 1 bo'lardi. */
    await waitFor(() => {
      expect(container.querySelectorAll("tbody tr")).toHaveLength(3);
    });

    expect(
      screen.queryByRole("button", { name: messages.recon.loadMore }),
    ).toBeNull();
  });

  test("⛔ so'rov `limit=50` ni YUBORADI va sanoq BIRINCHI sahifadan qoladi", async () => {
    routeTwoPages();

    const { container } = await renderList();

    const first = apiClientMock.apiFetch.mock.calls
      .map((call: unknown[]) => call[0] as string)
      .find((path: string) => path.startsWith("/reconciliation/delivery"));
    expect(first).toContain("limit=50");

    const before = (container.querySelector("dl") as HTMLElement).textContent;

    fireEvent.click(screen.getByRole("button", { name: messages.recon.loadMore }));
    await waitFor(() => {
      expect(container.querySelectorAll("tbody tr")).toHaveLength(3);
    });

    /*
     * ⛔ Sanoq SAHIFADAN MUSTAQIL (server kontrakti): ikkinchi sahifada
     *   `failed_count: 1` kelgan bo'lsa ham, ekrandagi sanoq BIRINCHI
     *   sahifaniki bo'lib qoladi. Yig'ish «bugun nechta yuborildi?»
     *   savoliga IKKINCHI javob tug'dirardi.
     */
    expect((container.querySelector("dl") as HTMLElement).textContent).toBe(before);
  });

  test("⛔ `next_cursor === null` da tugma UMUMAN chizilmaydi", async () => {
    routeFetch([row("delivered")]);

    await renderList();

    expect(
      screen.queryByRole("button", { name: messages.recon.loadMore }),
    ).toBeNull();
  });

  test("⛔ keyingi sahifa RAD ETILGANDA nomlangan matn chiqadi (`422`)", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.includes("cursor=")) {
        return Promise.reject(new Error("cursor_invalid"));
      }
      if (path.startsWith("/reconciliation/delivery")) {
        return Promise.resolve(envelope([row("delivered")], CURSOR));
      }
      return Promise.resolve({ items: [], next_cursor: null });
    });

    const { container } = await renderList();

    fireEvent.click(screen.getByRole("button", { name: messages.recon.loadMore }));

    await waitFor(() => {
      expect(container.textContent).toContain(messages.recon.loadMoreFailed);
    });

    /* ⛔ Allaqachon kelgan qator JOYIDA — jim bo'sh sahifa EMAS. */
    expect(container.querySelectorAll("tbody tr")).toHaveLength(1);
  });
});

/* -------------------------------------------------------------------------- */
/* WR-08 — JONLI HUDUD O'RAMDA, `<dl>` SEMANTIKASI SAQLANADI                  */
/* -------------------------------------------------------------------------- */

describe("⛔ WR-08: e'lon O'RAMDA, `<dl>` ning rolida EMAS", () => {
  test("⛔ `<dl>` da `role` YO'Q; jonli hudud O'RAMDA va AYNAN BITTA", async () => {
    const { container } = await renderList();

    const dl = container.querySelector("dl") as HTMLElement;

    /*
     * ⛔ `role="status"` `<dl>` ning implicit rolini ALMASHTIRARDI va
     *   `<dt>`/`<dd>` juftligi atama–qiymat bog'lanishini yo'qotardi.
     */
    expect(dl.hasAttribute("role")).toBe(false);
    expect(dl.querySelectorAll("dt")).toHaveLength(DELIVERY_STATES.length);
    expect(dl.querySelectorAll("dd")).toHaveLength(DELIVERY_STATES.length);

    /* ⛔ E'LON SAQLANADI — `[Yangilash]` foydalanuvchining OCHIQ NIYATI. */
    const live = container.querySelectorAll('[aria-live="polite"]');
    expect(live).toHaveLength(1);
    expect(live[0].contains(dl)).toBe(true);

    /* ⛔ Doimiy `role="status"` hududi YO'Q (platsholder allaqachon ketgan). */
    expect(container.querySelectorAll('[role="status"]')).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* (c) IKONKA — MATNDAN BOSHQA NARSA AYTMAYDI                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-34 (c): ikonka MATN bilan bir narsani aytadi", () => {
  test("⛔ ikki belgili tasdiq glifi DOM'da 0, bitta belgili BOR", async () => {
    const { container } = await renderList();

    /*
     * ⛔ IKKI BELGI — MESSENJERLARNING «O'QILDI» GLIFI. Matn rost
     *   gapirib turib ⛔ IKONKA YOLG'ON GAPIRARDI va ikonka kanali
     *   WCAG 1.4.1 bo'yicha matn bilan TENG OG'IRLIKDA o'qiladi.
     */
    expect(container.querySelectorAll(".lucide-check-check")).toHaveLength(0);

    /*
     * ⚠ QAMROV `tbody` GA TORAYTIRILADI: holat matni hisoblagichlar
     *   ro'yxatida HAM uchraydi (u yerda ikonka yo'q va bo'lmasligi ham
     *   kerak) — qidiruvni butun blokda yugurtirish IKKI element topib,
     *   da'voni noaniq qilardi.
     */
    const body = container.querySelector("tbody");
    const delivered = within(body as HTMLElement)
      .getByText(messages.recon.deliveryState.delivered)
      .closest("span");

    expect(delivered?.querySelector(".lucide-check")).not.toBeNull();
    expect(delivered?.querySelector(".lucide-check-check")).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* (d) `blocked` — MA'LUMOT, XATO EMAS (D-22)                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-34 (d): `blocked` xato sifatida ko'rsatilmaydi", () => {
  test("⛔ `blocked` qatorida shoshilinch-xato e'loni YO'Q", async () => {
    routeFetch([row("blocked")]);

    const { container } = await renderList();

    /*
     * ⛔ `role="alert"` skrinrider foydalanuvchisiga uni SHOSHILINCH
     *   xato deb e'lon qilardi. Blok esa sotuvchining HUQUQI va qarz
     *   undirish jarayonining bir qismi.
     *
     * ⚠ `role="status"` (hisoblagichlar) — BOSHQA narsa va u qoladi.
     */
    expect(container.querySelectorAll('[role="alert"]')).toHaveLength(0);

    /* ⛔ Qizil tint ham yo'q: `danger` foni «tizim buzildi» deb o'qilardi. */
    expect(container.innerHTML).not.toContain("bg-danger");
  });

  test("⛔ TO'LIQ JUMLA va KEYINGI QADAM matn sifatida bor", async () => {
    routeFetch([row("blocked")]);

    const { container } = await renderList();

    /*
     * ⛔ Yolg'iz nishon TEXNIK NOSOZLIK deb o'qilardi — shuning uchun
     *   to'liq jumla MAJBURIY, keyingi qadam esa u bilan JUFT.
     */
    expect(container.textContent).toContain(messages.recon.blockedBody);
    expect(container.textContent).toContain(messages.recon.blockedFix);
  });

  test("⛔ INTERAKTIV ELEMENTLAR TO'PLAMI CHEKLANGAN — to'plam TENGLIGI", async () => {
    routeFetch([row("blocked"), row("failed")]);

    const { container } = await renderList();

    /*
     * ⛔ TO'PLAM TENGLIGI, «qayta yuborish yo'qmi?» EMAS: nomga qadalgan
     *   da'vo yonidagi YANGI tugmani («Bloklashni yechish») KO'RMASDI.
     *   Bu shakl esa nomi qanday bo'lishidan qat'i nazar HAR QANDAY
     *   yangi boshqaruvda qizaradi.
     */
    const names = [
      ...within(container).queryAllByRole("button"),
      ...within(container).queryAllByRole("link"),
    ].map((node) => node.textContent?.trim() ?? "");

    expect(new Set(names)).toEqual(new Set([messages.recon.deliveryRefresh]));
  });

  test("⛔ O'TGAN KUNDA `[Yangilash]` ham chizilmaydi", async () => {
    routeFetch([row("delivered")]);

    const { container } = await renderList(false);

    /* O'tgan kunning yetkazilganligi O'ZGARMAS — tugma hech nima qilmasdi. */
    expect(within(container).queryAllByRole("button")).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* (e) TELEGRAM IDENTIFIKATORI VA XABAR MATNI DOM'DA YO'Q                     */
/* -------------------------------------------------------------------------- */

describe("⛔ G-34 (e): tashqi tizim identifikatori va xabar tanasi", () => {
  test("⛔ DOM'da Telegram identifikatorining BIRORTA izi yo'q", async () => {
    const { container } = await renderList();

    const leaked = FORBIDDEN_DOM_TOKENS.filter((token) =>
      container.innerHTML.includes(token),
    );

    expect(leaked).toEqual([]);
  });

  test("⛔ XABAR TANASI SXEMA CHEGARASIDA rad etiladi", () => {
    /*
     * ⛔ DA'VO SXEMA USTIDAN VA U DOM DA'VOSIDAN KUCHLIROQ: DOM
     *   tekshiruvi «bugun chizilmadi» deydi, bu esa «kelganda ham
     *   O'TMAYDI» deydi. Server bir kun «qulaylik uchun» qo'shsa,
     *   klient PARSE chegarasida qizaradi.
     */
    const valid = envelope([row("delivered")]);
    expect(deliveryListSchema.safeParse(valid).success).toBe(true);

    const withBody = envelope([
      row("delivered", { payload: { amount_soum: 30_000, stall_code: "14-C" } }),
    ]);
    expect(deliveryListSchema.safeParse(withBody).success).toBe(false);
  });

  test("⛔ BIRORTA KADR CHIZILMAYDI", async () => {
    const { container } = await renderList();

    /*
     * ⛔ IKKI KANAL: rol bo'yicha VA teg bo'yicha. Rol bo'yicha da'vo
     *   `alt=""` bilan chizilgan kadrni KO'RMASDI.
     */
    expect(screen.queryAllByRole("img")).toHaveLength(0);
    expect(container.querySelectorAll("img")).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* XATO TURI — XOM SINF NOMI EKRANGA CHIQMAYDI (D-04)                         */
/* -------------------------------------------------------------------------- */

describe("⛔ xato TURI yopiq to'plamdan", () => {
  test("⛔ `pending` qatori SABABINI ko'rsatadi (Topilma №I)", async () => {
    /*
     * ⛔⛔ MANZILSIZ SHOX `pending` VA `last_error_type` NI BIRGA
     *     QOLDIRADI — VA ESKI SHART AYNAN SHUNI YASHIRARDI.
     *
     * `outbox_repo.defer_unresolved()` holatni `pending` da qoldiradi,
     * sabab turini esa YOZADI va urinishlar sonini UMUMAN oshirmaydi.
     * Ya'ni «Navbatda · Urinishlar: 0» qatori 18 soat turib, nima uchun
     * turganini AYTMASDI — direktor uchun bu «tizim ishlayapti shekilli»
     * degani edi.
     */
    routeFetch([
      row("pending", {
        error_type: "UnresolvedRecipient",
        error_status_code: null,
        attempt_count: 0,
      }),
    ]);

    const { container } = await renderList();

    expect(container.textContent).toContain(
      messages.recon.deliveryError.chat_not_found,
    );

    /* ⛔ Va xom sinf nomi baribir EKRANGA CHIQMAYDI (D-04 kuchda). */
    expect(container.textContent).not.toContain("UnresolvedRecipient");
  });

  test("⛔ `delivered` qatorida eski xato TIRILMAYDI", async () => {
    /*
     * ⛔ Xabar YETIB BORGAN; oldingi urinishdagi xato — TARIX. Uni
     *   ko'rsatish muvaffaqiyatni NOSOZLIKKA aylantirardi va direktor
     *   yetkazilgan kvitansiyani muammoli deb o'qirdi.
     */
    routeFetch([
      row("delivered", {
        error_type: "RemoteProtocolError",
        error_status_code: 502,
      }),
    ]);

    const { container } = await renderList();

    for (const value of Object.values(messages.recon.deliveryError)) {
      expect(container.textContent).not.toContain(value);
    }
  });

  test("⛔ xom istisno sinfining nomi DOM'da YO'Q", async () => {
    routeFetch([
      row("failed", { error_type: "RemoteProtocolError", error_status_code: 502 }),
    ]);

    const { container } = await renderList();

    /*
     * ⛔ `RemoteProtocolError` direktorga HECH NIMA aytmaydi va u
     *   istisno matnining bir bo'lagiga o'xshaydi — ekranda yopiq
     *   to'plamning jumlasi turadi.
     */
    expect(container.textContent).not.toContain("RemoteProtocolError");
    expect(container.textContent).toContain(
      messages.recon.deliveryError.telegram_unreachable,
    );
  });

  test("⛔ sabab `blocked` qatorida CHIZILMAYDI (yopiq to'plamdan tashqarida)", async () => {
    routeFetch([
      row("blocked", { error_type: "Forbidden", error_status_code: 403 }),
    ]);

    const { container } = await renderList();

    /*
     * ⛔ SABAB YUZASI — YOPIQ TO'PLAM: `pending` / `sent` / `failed`.
     *   `blocked` undan ATAYIN tashqarida: sabab ALLAQACHON to'liq jumla
     *   bilan aytilgan (blok sotuvchining HUQUQI) va ikkinchi sabab uni
     *   texnik NOSOZLIK kabi ko'rsatardi (D-22).
     */
    for (const value of Object.values(messages.recon.deliveryError)) {
      expect(container.textContent).not.toContain(value);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* VAQT KATAGI — HARFSIZLIK DARVOZASI VA KUN ANIQLIGI (Kamchilik №1, №I)      */
/* -------------------------------------------------------------------------- */

/**
 * ⛔⛔ FAQAT RAQAM VA AJRATGICH — HARF YO'Q.
 *
 * Kamchilik №1 («2026 M08 15») ning mexanikasi shu edi: `dateStyle` CLDR
 * SKELETINI tanlaydi va locale yechilmaganda ILDIZ (root) namunasiga
 * tushadi — o'shanda oy `M08` shaklidagi NOM bo'lib chiqadi. Bu regex
 * «M08», «avg», «сен» va `AM`/`PM` sinflarini BIRVARAKAYIGA bloklaydi.
 */
const DIGITS_ONLY = /^[\d\s.,:/-]+$/u;

/** Birinchi qatorning BIRINCHI katagi — vaqt ustuni. */
function firstTimeCell(container: HTMLElement): string {
  const cell = container.querySelector("tbody tr td");
  expect(cell).not.toBeNull();
  return (cell as HTMLElement).textContent ?? "";
}

describe("⛔ vaqt katagi: harf yo'q, o'tgan kunda sana bor", () => {
  test("⛔ NAZORAT: detektor sun'iy ijobiyni USHLAYDI", () => {
    /*
     * ⛔ NAZORATSIZ QUYIDAGI DA'VO HAR DOIM YASHIL BO'LISHI MUMKIN EDI:
     *   regex xato yozilsa (masalan `u` bayrog'i bilan `[\s\S]+`) u har
     *   qanday matnga mos kelardi va darvoza hech nimani o'lchamasdi.
     */
    expect(DIGITS_ONLY.test("2026 M08 15 12:36")).toBe(false);
    expect(DIGITS_ONLY.test("12.08, 14:15")).toBe(true);
  });

  test("⛔ o'tgan kun katagida HARF YO'Q", async () => {
    const { container } = await renderList(false);

    const text = firstTimeCell(container);

    expect(text.trim()).not.toBe("");
    expect(DIGITS_ONLY.test(text)).toBe(true);
  });

  test("⛔ o'tgan kunda SANA bor, bugungi sahifada YO'Q", async () => {
    /*
     * ⛔ RAQAMLAR `DAY` DAN HISOBLANADI, literal to'qilmaydi: qo'lda
     *   yozilgan «12» seed sanasi o'zgargan kuni JIMGINA yolg'on
     *   gapirardi (05-14 ning «to'qilgan qiymat» darsi).
     */
    const [, month, dayOfMonth] = DAY.split("-");

    const past = firstTimeCell((await renderList(false)).container);
    const today = firstTimeCell((await renderList(true)).container);

    /* ⛔ O'tgan kun sahifasida SANA — YAGONA aniqlovchi. */
    expect(past).toContain(dayOfMonth);
    expect(past).toContain(month);

    /*
     * ⛔ Bugungi sahifada sana ORTIQCHA SHOVQIN: jadval `created_at`
     *   bo'yicha KUN FILTRIDA (`outbox_repo._DELIVERY_ROWS`), ya'ni har
     *   qator bugungi va kun noaniqligi TUG'ILMAYDI.
     */
    expect(today).not.toContain(month);

    /* ⛔ IKKALA variantda ham soat:daqiqa BOR — vaqt yo'qolmaydi. */
    for (const text of [past, today]) {
      expect(text).toMatch(/\d{1,2}:\d{2}/u);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* IN-04 — `[Yangilash]` FOKUSNI YO'QOTMAYDI                                  */
/* -------------------------------------------------------------------------- */

describe("⛔ IN-04: `aria-disabled`, `disabled` EMAS", () => {
  test("⛔ tugma HECH QACHON `disabled` atributini olmaydi", async () => {
    /*
     * ⛔⛔ BIR FAZADA BIR SAVOLGA IKKI JAVOB EDI: `case-detail-dialog.tsx`
     *     `disabled` ni ochiq TAQIQLAYDI («fokusni yo'qotadi va
     *     skrinrider foydalanuvchisi sababni umuman eshitmasdi»), bu
     *     blok esa uni ISHLATARDI. Yangilanish paytida brauzer fokusni
     *     `<body>` ga qaytaradi va klaviatura foydalanuvchisi tugmadan
     *     ⛔ TUSHIB QOLADI — u so'rov tugagach sahifa boshiga otiladi.
     */
    const { container } = await renderList(true);

    const refresh = within(container).getByRole("button", {
      name: messages.recon.deliveryRefresh,
    });

    expect(refresh.hasAttribute("disabled")).toBe(false);
    /* ⛔ Va holat E'LON QILINADI — jim tugma ham yaramaydi. */
    expect(refresh.hasAttribute("aria-disabled")).toBe(true);
  });

  test("⛔ MANBA SKANI: katalogda `disabled=` 0 marta", async () => {
    /*
     * ⛔ DOM da'vosi FAQAT chizilgan holatni ko'radi: `isFetching`
     *   rost bo'lgan lahzada `disabled` qaytib kelsa, yuqoridagi test
     *   uni ⛔ KO'RMASDI (u tinch holatda o'lchaydi). Manba skani esa
     *   shartdan MUSTAQIL.
     */
    const { existsSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");

    const file = join(
      process.cwd(),
      "src",
      "components",
      "reconciliation",
      "delivery-list.tsx",
    );
    if (!existsSync(file)) throw new Error(`komponent topilmadi: ${file}`);

    const source = readFileSync(file, "utf8");
    expect(source).not.toContain(" disabled=");
    expect(source).toContain("aria-disabled");
  });
});

/* -------------------------------------------------------------------------- */
/* IN-08 — BOZORSIZ SESSIYADA CHEKSIZ SKELET YO'Q                             */
/* -------------------------------------------------------------------------- */

test("⛔ IN-08: `marketId === null` da skelet EMAS, NOMLANGAN holat", () => {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Platforma admini",
      roles: ["director"],
      marketId: null,
      marketName: null,
      isPlatformAdmin: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const { container } = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <DeliveryList day={DAY} isToday />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );

  expect(container.querySelectorAll('[aria-busy="true"]')).toHaveLength(0);
  expect(
    within(container).getByText(messages.recon.marketMissing),
  ).toBeInTheDocument();
  expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
});
