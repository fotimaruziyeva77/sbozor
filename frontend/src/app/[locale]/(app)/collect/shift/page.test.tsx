/**
 * ⛔⛔ CR-05 — §10.3 NING NATIJA EKRANI OTA-ONA TOMONIDAN O'CHIRILMAYDI.
 *
 * =============================================================================
 * ⛔ 1. NEGA SAHIFA DARAJASIDA, `ShiftCloseForm` DARAJASIDA EMAS.
 *
 *   `shift-close-form.test.tsx` komponentni TO'G'RIDAN-TO'G'RI chizadi,
 *   ya'ni unda ota-ona UMUMAN yo'q va uning `unmount` qarori o'lchovga
 *   KIRMAYDI (WR-09 nomlagan sinf).
 *
 *   Eski shart: `closing && openShift !== null`. `useCloseShift()` ning
 *   `onSuccess` i `removeQueries({ queryKey: shiftPrefix(marketId) })`
 *   chaqiradi va `shiftPrefix` — `openShiftKey` ning PREFIKSI, ya'ni
 *   ochiq smena yozuvi keshdan CHIQADI.
 *
 * ⛔ 2. MEXANIZM ⛔ O'LCHANDI, TAXMIN QILINMADI — VA U «DARHOL UNMOUNT»
 *      EMAS.
 *
 *   react-query v5 da `removeQueries()` mount holatidagi kuzatuvchiga
 *   XABAR BERMAYDI va qayta so'rov ham yubormaydi. Shuning uchun
 *   yopilgan zahoti sahifa hali ESKI `data` ni ushlab turadi va natija
 *   ekrani KO'RINADI. Nuqson KEYINGI QAYTA CHIZISHDA otiladi: o'shanda
 *   `useQuery` o'chirilgan yozuvga qayta obuna bo'ladi, `data`
 *   `undefined` bo'ladi, `openShift` `null` ga tushadi va forma
 *   UNMOUNT bo'lib, lokal `result` holati YO'Q BO'LADI.
 *
 *   ⛔ AYNAN SHU UNI XAVFLI QILADI: natija ekranining yashashi «sahifa
 *      qayta chizilmaydi» degan KAFOLATLANMAGAN shartga tayanardi.
 *      Sabablar ro'yxati yopiq emas — `AuthProvider`, locale/tema
 *      konteksti, brauzer fokusi, React ning dev rejimidagi ikki marta
 *      chizishi, kelajakda qo'shiladigan har qanday holat. Ya'ni kassir
 *      moliyaviy deklaratsiya yozib, natija ekranini KO'RMASLIGI —
 *      taxminiy emas, KUTILADIGAN oqibat, faqat vaqti aniq emas.
 *
 * ⛔ 3. DA'VO — TO'PLAM TENGLIGI, «biror narsa ko'rindi» EMAS (D-31).
 *      Ikki yuza (`result` / `open-card`) ham NOMLANADI va §10.3 ning
 *      AYNAN uchta bolasi `data-shift-result` bilan o'lchanadi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

import messages from "../../../../../../messages/uz-Latn.json";
import CollectShiftPage from "./page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { openShiftKey } from "@/lib/shift-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SHIFT_ID = "22222222-2222-4222-8222-222222222222";
const DECLARED = 980_000;

const OPEN_SHIFT = {
  id: SHIFT_ID,
  status: "open",
  opened_at: "2026-09-14T02:00:00Z",
};

const CLOSED = {
  id: SHIFT_ID,
  status: "closed",
  declared_soum: DECLARED,
  closed_at: "2026-09-14T13:00:00Z",
};

let client: QueryClient;
/** ⛔ NAZORAT: yopilgandan KEYIN `GET /shifts/open` `null` qaytaradi. */
let shiftClosed = false;

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000000",
      fullName: "Test Cashier",
      roles: ["cashier"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function tree() {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <NextIntlClientProvider
          locale="uz-Latn"
          messages={messages}
          timeZone="Asia/Tashkent"
        >
          <CollectShiftPage />
        </NextIntlClientProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function renderPage() {
  return render(tree());
}

/**
 * ⛔ EKRANDA QAYSI YUZA MOUNT — IKKALASI HAM NOMLANADI (D-31).
 *
 * `not.toContain(...)` shaklidagi tasdiq faqat AYNAN o'sha matnni
 * ushlardi; ikki yuzaning TO'PLAMI esa «forma o'chdi va uning o'rniga
 * karta keldi» almashuvini TO'LIQ ko'rsatadi va nosozlik xabari
 * to'g'ridan-to'g'ri sababni aytadi.
 */
function mountedSurfaces(): string[] {
  const surfaces: string[] = [];
  if (document.body.querySelector("[data-shift-result-region]") !== null) {
    surfaces.push("result");
  }
  if (
    screen.queryByRole("button", { name: messages.collect.shiftOpen }) !== null
  ) {
    surfaces.push("open-card");
  }
  return surfaces;
}

/**
 * ⛔ TIZIM TINCHLANGUNCHA KUTADI — «birinchi mos kelgan lahza» EMAS.
 *
 * `waitFor` MUVAFFAQIYAT bilan to'xtaydi, ya'ni u tasdiqni ENG ERTA
 * mos keladigan nuqtada bajaradi. CR-05 esa KEYINROQ sodir bo'ladi:
 * `removeQueries()` yozuvni darhol o'chiradi, LEKIN React qayta chizishi
 * va `ShiftCloseForm` ning unmount bo'lishi keyingi flushda yuz beradi.
 * O'sha oraliqda yozilgan tasdiq ESKI kod bilan ham yashil qolardi — bu
 * shu faylning birinchi yozilishida O'LCHANGAN.
 */
async function settle(): Promise<void> {
  await waitFor(() => {
    expect(client.isMutating()).toBe(0);
    expect(client.isFetching()).toBe(0);
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 60));
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
  shiftClosed = false;
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  apiClientMock.apiFetch.mockImplementation(
    (path: string, options?: { method?: string }) => {
      if (path === "/shifts/open") {
        return Promise.resolve(shiftClosed ? null : OPEN_SHIFT);
      }
      if (path.endsWith("/close") && options?.method === "POST") {
        /* ⛔ Server holati HAQIQATAN o'zgaradi — smena endi yopiq. */
        shiftClosed = true;
        return Promise.resolve({ ...CLOSED });
      }
      return Promise.reject(new Error(`mock'lanmagan yo'l: ${path}`));
    },
  );
});

afterEach(() => {
  client.clear();
  clearSession();
});

describe("CR-05 (06-UI-SPEC §10.3): yopilgandan keyingi natija ekrani", () => {
  test("⛔ kesh evikatsiyasi UCHTA natija bolasini O'CHIRMAYDI", async () => {
    const view = renderPage();

    /* 1-QADAM: [Smenani yopish] — karta ochiq smenani ko'rgach chiziladi. */
    const requestClose = await screen.findByRole("button", {
      name: messages.collect.shiftClose,
    });
    fireEvent.click(requestClose);

    /* 2-QADAM: sanalgan naqd (ko'r — tizim summasi ekranda YO'Q). */
    const input = await screen.findByLabelText(messages.collect.declaredLabel);
    fireEvent.change(input, { target: { value: String(DECLARED) } });
    fireEvent.click(screen.getByRole("button", { name: messages.common.close }));

    /* 3-QADAM: DL-4 tasdig'i. */
    const confirm = await screen.findAllByRole("button", {
      name: messages.collect.shiftClose,
    });
    /*
     * ⛔ NAZORATNING BIRINCHI YARMI: kalit TO'G'RI va qiymat HOZIR BOR.
     *   Usiz pastdagi «endi yo'q» da'vosi noto'g'ri kalitdan ham rost
     *   chiqardi va butun nazorat yolg'on-yashil bo'lardi.
     */
    expect(client.getQueryData(openShiftKey(MARKET_ID))).toEqual(OPEN_SHIFT);

    fireEvent.click(confirm[confirm.length - 1]);
    await settle();

    /*
     * ⛔ NAZORATNING IKKINCHI YARMI — SABOTAJ TIZIMGA YETIB BORDIMI (D-30).
     *
     *   (a) yopish so'rovi HAQIQATAN ketdi;
     *   (b) `useCloseShift().onSuccess` -> `removeQueries(shiftPrefix)`
     *       ishladi va `openShiftKey` (uning BOLASI) keshda QOLMADI —
     *       ya'ni `openShift = data ?? null` `null` ga tushgan, bu esa
     *       ESKI shartning (`closing && openShift !== null`) `false`
     *       bo'lishi uchun ZARUR VA YETARLI holat.
     *
     *   Bu ikkisisiz test «evikatsiya umuman bo'lmagan» holatda ham
     *   yashil qolardi — o'shanda eski kod ham o'tardi.
     */
    expect(shiftClosed).toBe(true);
    expect(client.getQueryData(openShiftKey(MARKET_ID)) ?? null).toBeNull();

    /*
     * ⛔ ASOSIY DA'VO: forma MOUNT holatda qoldi va natijaning UCHTA
     *    bolasi joyida — evikatsiya O'TIB BO'LGANIDAN KEYIN o'lchanadi.
     */
    /*
     * =====================================================================
     * ⛔⛔ QAYTA CHIZISH — TESTNING QO'SHIMCHASI EMAS, NUQSONNING TETIGI.
     *
     * O'LCHANGAN XULQ (react-query v5): `removeQueries()` yozuvni keshdan
     * o'chiradi, LEKIN mount holatidagi kuzatuvchiga XABAR BERMAYDI va
     * qayta so'rov ham YUBORMAYDI. Ya'ni yopilgan zahoti sahifa hali
     * ESKI `data` ni ushlab turadi va natija ekrani KO'RINADI.
     *
     * Nuqson KEYINGI qayta chizishda otiladi: o'shanda `useQuery`
     * o'chirilgan yozuvga qayta obuna bo'ladi, `data` `undefined` bo'ladi,
     * `openShift` `null` ga tushadi va ESKI shart (`closing && openShift
     * !== null`) `false` beradi — `ShiftCloseForm` UNMOUNT bo'lib, uning
     * lokal `result` holati YO'Q BO'LADI.
     *
     * ⛔ SABABLAR RO'YXATI YOPIQ EMAS va aynan shuning uchun bu xavf:
     *    `AuthProvider` yangilanishi, locale/tema konteksti, brauzer
     *    fokusi, React ning dev rejimidagi ikki marta chizishi yoki
     *    kelajakda sahifaga qo'shiladigan HAR QANDAY holat. Natija
     *    ekranining yashashi «sahifa qayta chizilmaydi» degan
     *    KAFOLATLANMAGAN shartga tayanardi.
     *
     * ⚠ TETIK ATAYIN ENG SODDA SHAKLDA: bitta `rerender` — u yuqoridagi
     *   sabablarning HAMMASINI bitta determinlashtirilgan hodisa bilan
     *   almashtiradi. Konkret sababni tanlash (masalan sessiya
     *   yangilanishi) testni o'sha sababning mexanizmiga bog'lab
     *   qo'yardi, da'vo esa undan MUSTAQIL.
     * =====================================================================
     */
    expect(mountedSurfaces()).toEqual(["result"]);
    view.rerender(tree());
    await settle();

    expect(mountedSurfaces()).toEqual(["result"]);

    const region = document.body.querySelector(
      "[data-shift-result-region]",
    ) as HTMLElement;
    const parts = Array.from(
      region.querySelectorAll<HTMLElement>("[data-shift-result]"),
    ).map((el) => el.dataset.shiftResult);

    expect(new Set(parts)).toEqual(new Set(["badge", "figure", "action"]));
    expect(region.children).toHaveLength(3);
    expect(region.textContent).toContain(messages.collect.shiftNew);
  });

  test("⛔ [Yangi smena ochish] sahifani BIRINCHI holatiga qaytaradi", async () => {
    renderPage();

    fireEvent.click(
      await screen.findByRole("button", { name: messages.collect.shiftClose }),
    );
    const input = await screen.findByLabelText(messages.collect.declaredLabel);
    fireEvent.change(input, { target: { value: String(DECLARED) } });
    fireEvent.click(screen.getByRole("button", { name: messages.common.close }));

    const confirm = await screen.findAllByRole("button", {
      name: messages.collect.shiftClose,
    });
    fireEvent.click(confirm[confirm.length - 1]);
    await settle();

    const reopen = screen.getByRole("button", {
      name: messages.collect.shiftNew,
    });
    fireEvent.click(reopen);
    await settle();

    /*
     * ⛔ `EmptyState` + [Smenani ochish] — §10.1 ning BIRINCHI holati.
     *   Natija bloki esa DOM'dan CHIQADI (almashtirish, qo'shish emas):
     *   aks holda ekranda §10.3 ning uchtasi o'rniga BESHTA bo'lardi.
     *
     * ⚠ BU TEST TUZATISHNING TESKARI CHEKKASINI QO'RIQLAYDI: forma endi
     *   so'rov natijasiga bog'liq EMAS, ya'ni uni HECH NIMA yopmasligi
     *   xavfi tug'iladi. `onReopen` yagona chiqish yo'li va u
     *   O'LCHANADI — usiz kassir natija ekranida QAMALIB qolardi.
     */
    expect(mountedSurfaces()).toEqual(["open-card"]);
  });
});
