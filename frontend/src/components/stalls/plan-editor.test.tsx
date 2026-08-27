/**
 * =============================================================================
 * PLAN MUHARRIRI — HODISA SIMLARI DARVOZASI (260820).
 *
 * ⛔⛔ MODEL TESTLARI (`plan-model.test.tsx`) BU YERNI QAMRAMAYDI.
 *
 *   U yerda `cellsBetween` va `placeSequence` sof funksiya sifatida
 *   o'lchangan va ular TO'G'RI ishlaydi. Lekin ular hodisaga ULANMASA
 *   ham hamma model testi yashil qolardi: bosish hech nima qilmasdi,
 *   surish bitta katakda qotardi, «Saqlash» esa bo'sh tana yuborardi —
 *   va bularning HECH BIRI typecheck, lint yoki model testida
 *   ko'rinmasdi.
 *
 *   Aynan shu sinf 260820 da Chromeda IKKI marta ushlandi:
 *     1. kataklar orasidagi 4px oraliq bosishni YUTARDI;
 *     2. tez surishda oraliq kataklar TASHLAB ketilardi.
 *
 *   Ikkalasi ham «ekran ochiladi, chiroyli ko'rinadi, ishlamaydi»
 *   turkumidan. Shuning uchun bu fayl HODISADAN CHIQQUNCHA o'lchaydi.
 *
 * DIQQAT: bosish `fireEvent` bilan — `@testing-library/user-event`
 * tasdiqlangan paketlar ro'yxatida yo'q (`stall-map.test.tsx` naqshi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

import { PlanEditor } from "@/components/stalls/plan-editor";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ZONE_ID = "22222222-2222-4222-8222-222222222222";
const MAP_PATH = "/stalls/map";
const PLAN_PATH = "/stalls/plan";

type MockCell = {
  id: string;
  code: string;
  status: "active";
  has_vendor: boolean;
  plan_x: number | null;
  plan_y: number | null;
};

function cell(code: string, plan: { x: number; y: number } | null = null): MockCell {
  return {
    id: `stall-${code}`,
    code,
    status: "active",
    has_vendor: true,
    plan_x: plan?.x ?? null,
    plan_y: plan?.y ?? null,
  };
}

function mockMap(cells: readonly MockCell[]) {
  apiFetch.mockImplementation((path: string) => {
    if (path === MAP_PATH) {
      return Promise.resolve({
        zones: [{ id: ZONE_ID, name: "A zonasi", cells }],
      });
    }
    if (path === PLAN_PATH) {
      return Promise.resolve({ placed_count: 0, cleared_count: 0 });
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

function seedSession(): void {
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

function renderEditor(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <PlanEditor />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );
  render(tree);
}

/** Katak tugmasi — «1-ustun 1-qator» ekranda 1-DAN boshlanadi. */
function cellAt(col: number, row: number): HTMLButtonElement {
  const empty = screen.queryByLabelText(`Bo'sh katak, ${col}-ustun ${row}-qator`);
  if (empty !== null) return empty as HTMLButtonElement;
  const taken = document.querySelector<HTMLButtonElement>(
    `[aria-label$="${col}-ustun ${row}-qator"]`,
  );
  if (taken === null) throw new Error(`katak topilmadi: ${col}/${row}`);
  return taken;
}

/** Chizmadagi rastalar — `kod -> "ustun/qator"`. */
function drawn(): Record<string, string> {
  const result: Record<string, string> = {};
  for (const node of document.querySelectorAll<HTMLButtonElement>(
    "[aria-label]",
  )) {
    const label = node.getAttribute("aria-label") ?? "";
    const match = /^(.+)-rasta, (\d+)-ustun (\d+)-qator$/.exec(label);
    if (match !== null) result[match[1]!] = `${match[2]}/${match[3]}`;
  }
  return result;
}

/** Bosish — HAQIQIY ketma-ketlik: `pointerdown` + `pointerup`. */
function tap(button: HTMLButtonElement): void {
  fireEvent.pointerDown(button, { pointerId: 1, buttons: 1 });
  fireEvent.pointerUp(button, { pointerId: 1 });
}

beforeEach(() => {
  apiFetch.mockReset();
  seedSession();
});

afterEach(() => {
  clearSession();
});

describe("bosib chizish", () => {
  test("⭐ BO'SH KATAKNI BOSISH — navbatdagi rasta o'sha yerga tushadi", async () => {
    mockMap([cell("A-01"), cell("A-02"), cell("A-03")]);
    renderEditor();

    await screen.findByLabelText("Bo'sh katak, 1-ustun 1-qator");
    tap(cellAt(1, 1));

    await waitFor(() => expect(drawn()).toEqual({ "A-01": "1/1" }));
  });

  test("navbat O'ZI siljiydi — ketma-ket bosish qatorni teradi", async () => {
    /*
     * ⛔ Bu mahsulotning asosiy va'dasi: «bos-bos-bos» bilan qator
     *   chiziladi. Navbat siljimasa har bosishda o'sha rasta
     *   ko'chirilardi va ekranda BITTA katak yurgandek ko'rinardi.
     */
    mockMap([cell("A-01"), cell("A-02"), cell("A-03")]);
    renderEditor();

    await screen.findByLabelText("Bo'sh katak, 1-ustun 1-qator");
    tap(cellAt(1, 1));
    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    tap(cellAt(2, 1));
    await waitFor(() => expect(drawn()["A-02"]).toBe("2/1"));
    tap(cellAt(3, 1));

    await waitFor(() =>
      expect(drawn()).toEqual({ "A-01": "1/1", "A-02": "2/1", "A-03": "3/1" }),
    );
  });

  test("BAND katakni bosish — hech nima o'zgarmaydi", async () => {
    mockMap([cell("A-01", { x: 0, y: 0 }), cell("A-02")]);
    renderEditor();

    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    tap(cellAt(1, 1));

    await waitFor(() => expect(drawn()).toEqual({ "A-01": "1/1" }));
  });
});

describe("surib chizish", () => {
  test("⭐ TEZ SURISH ORALIQ KATAKLARNI TASHLAB KETMAYDI", async () => {
    /*
     * =====================================================================
     * ⛔⛔ 260820 DA CHROMEDA O'LCHANGAN NUQSONNING DARVOZASI.
     *
     *   Brauzer tez surishda oraliq kataklarning `pointerenter` ini
     *   UMUMAN bermaydi — o'lchovda 1, 3 va 10-ustunlar to'lgan,
     *   oradagilari bo'sh qolgan edi. Natija shunchaki «teshik» emas:
     *   navbat siljigani uchun KEYINGI rastalar ham noto'g'ri katakka
     *   tushardi, ya'ni tez harakat chizmani jimgina buzardi.
     *
     *   Shu test AYNAN o'sha hodisa naqshini takrorlaydi: 1-ustundan
     *   TO'G'RIDAN-TO'G'RI 4-ustunga sakrash.
     * =====================================================================
     */
    mockMap([cell("A-01"), cell("A-02"), cell("A-03"), cell("A-04")]);
    renderEditor();

    await screen.findByLabelText("Bo'sh katak, 1-ustun 1-qator");
    fireEvent.pointerDown(cellAt(1, 1), { pointerId: 1, buttons: 1 });
    fireEvent.pointerEnter(cellAt(4, 1), { pointerId: 1, buttons: 1 });
    fireEvent.pointerUp(cellAt(4, 1), { pointerId: 1 });

    await waitFor(() =>
      expect(drawn()).toEqual({
        "A-01": "1/1",
        "A-02": "2/1",
        "A-03": "3/1",
        "A-04": "4/1",
      }),
    );
  });

  test("tugma BOSILMAGAN holda kursor yurishi — chizmaydi", async () => {
    /*
     * ⛔ `buttons === 0` tekshiruvi: sichqoncha shunchaki panjara
     *   ustidan o'tganda rasta qo'yilsa, odam ekranga qarab turib
     *   butun chizmani tasodifan yaratardi.
     */
    mockMap([cell("A-01"), cell("A-02")]);
    renderEditor();

    await screen.findByLabelText("Bo'sh katak, 1-ustun 1-qator");
    fireEvent.pointerEnter(cellAt(1, 1), { pointerId: 1, buttons: 0 });
    fireEvent.pointerEnter(cellAt(2, 1), { pointerId: 1, buttons: 0 });

    await waitFor(() => expect(drawn()).toEqual({}));
  });
});

describe("o'chirish", () => {
  test("«O'chirish» rejimida bosilgan rasta NAVBATGA qaytadi", async () => {
    mockMap([cell("A-01", { x: 0, y: 0 }), cell("A-02")]);
    renderEditor();

    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    fireEvent.click(screen.getByRole("button", { name: "O'chirish" }));
    tap(cellAt(1, 1));

    await waitFor(() => expect(drawn()).toEqual({}));
    expect(screen.getByText("Chizilmagan rastalar: 2")).toBeTruthy();
  });
});

describe("saqlash", () => {
  test("⭐ SERVERGA FAQAT FARQ KETADI — o'zgarmagan rasta tanada YO'Q", async () => {
    /*
     * ⛔⛔ Butun chizmani yuborish auditga 1000 ta soxta «o'zgardi»
     *     yozuvi qoldirardi. Bu yerda A-01 O'Z JOYIDA qoladi va
     *     tanaga TUSHMASLIGI kerak.
     */
    mockMap([cell("A-01", { x: 0, y: 0 }), cell("A-02")]);
    renderEditor();

    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    tap(cellAt(3, 1));
    await waitFor(() => expect(drawn()["A-02"]).toBe("3/1"));

    fireEvent.click(screen.getByRole("button", { name: "Saqlash" }));

    await waitFor(() => {
      const call = apiFetch.mock.calls.find(([path]) => path === PLAN_PATH);
      expect(call).toBeTruthy();
      expect(call?.[1]).toMatchObject({
        method: "PUT",
        body: {
          placed: [{ stall_id: "stall-A-02", plan_x: 2, plan_y: 0 }],
          cleared: [],
        },
      });
    });
  });

  test("o'zgarishsiz «Saqlash» — so'rov UMUMAN ketmaydi", async () => {
    /*
     * ⛔ `aria-disabled` ko'rinadi, lekin bosish hodisasi baribir
     *   keladi (`ui/button.tsx` qarori) — shuning uchun to'siq
     *   MANTIQDA ham bo'lishi shart.
     */
    mockMap([cell("A-01", { x: 0, y: 0 })]);
    renderEditor();

    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    fireEvent.click(screen.getByRole("button", { name: "Saqlash" }));

    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    expect(apiFetch.mock.calls.some(([path]) => path === PLAN_PATH)).toBe(false);
  });

  test("«Bekor qilish» — chizma SERVER holatiga qaytadi", async () => {
    mockMap([cell("A-01", { x: 0, y: 0 }), cell("A-02")]);
    renderEditor();

    await waitFor(() => expect(drawn()["A-01"]).toBe("1/1"));
    tap(cellAt(4, 2));
    await waitFor(() => expect(drawn()["A-02"]).toBe("4/2"));

    fireEvent.click(screen.getByRole("button", { name: "Bekor qilish" }));

    await waitFor(() => expect(drawn()).toEqual({ "A-01": "1/1" }));
  });
});

describe("panjara", () => {
  test("⭐ KATAKLAR ORASIDA O'LIK PIKSEL YO'Q", async () => {
    /*
     * =====================================================================
     * ⛔⛔ 260820 DA CHROMEDA O'LCHANGAN BIRINCHI NUQSON.
     *
     *   Panjara `gap-1` (4px) bilan chizilgan edi va o'sha 4px
     *   BOSISHNI YUTARDI: hodisa katakka emas, konteynerga tushardi va
     *   ekranda MUTLAQO hech nima bo'lmasdi. Sichqonchada bu
     *   «tegmadim» bo'lib tuyulardi; barmoqda esa — har uchinchi urinish.
     *
     *   jsdom joylashuvni hisoblamaydi, shuning uchun da'vo TUZILISH
     *   bo'yicha: panjarada `gap` YO'Q va har tugma o'z trekini
     *   TO'LDIRADI (`size-full`). Oraliq tugmaning ICHIDA.
     * =====================================================================
     */
    mockMap([cell("A-01"), cell("A-02")]);
    renderEditor();

    const grid = await screen.findByRole("group", {
      name: "Bozor plani panjarasi",
    });
    expect(grid.className).not.toMatch(/\bgap-/);

    const first = grid.querySelector("button");
    expect(first?.className).toMatch(/\bsize-full\b/);
  });
});
