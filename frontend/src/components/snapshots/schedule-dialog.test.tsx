/**
 * DL-1 — ⛔ «YUKLANMOQDA» FAQAT YUKLANAYOTGANDA AYTILADI.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (TEST-REPORT 2026-08-14, Topilma №6):
 *
 *   SO'ROV TUGAGACH DIALOG UCH XIL NARSA AYTISHI MUMKIN — VA UCHALASI HAM
 *   «Yuklanmoqda» EMAS.
 *
 *   Nuqson sinfi: interfeys VA'DA beradi, lekin bajarmaydi. `GET
 *   /snapshot-schedules` `200 {"items":[]}` qaytargan, ya'ni yuklanish
 *   TUGAGAN — dialog esa yolg'on gapirardi va admin uni o'z tarmog'i yoki
 *   o'z sabri bilan bog'lardi. Abadiy «Yuklanmoqda» eng yomon yolg'on,
 *   chunki u KUTISHNI taklif qiladi: hech qanday harakat ko'rsatmaydi va
 *   hech qachon tugamaydi.
 *
 *   Shuning uchun uch shox UCH MUSTAQIL da'vo:
 *     T1  bo'sh ro'yxat -> ma'lumot nosozligi FAKT sifatida aytiladi;
 *     T2  so'rov yiqildi -> TARJIMA QILINGAN xato matni chiqadi;
 *     T3  profil bor    -> tahrir formasi O'ZGARISHSIZ (nazorat).
 *   Biri ikkinchisining o'rnini bosmaydi: T1 ni `isPending` shoxiga
 *   bog'lash T2 ni qizartirmaydi va aksincha.
 * =============================================================================
 *
 * ⛔ T1 «JADVAL QO'SHING» CHAQIRIG'INI TALAB QILMAYDI va TALAB QILA
 *    OLMAYDI — 04-UI-SPEC §10.4 uni ATAYIN taqiqlaydi: D-01 bo'yicha
 *    jadvalni bozor sozlash ustasi avtomatik yozadi, ya'ni «qo'shing»
 *    tugmasi adminni o'zi javobgar bo'lmagan ishga chorlardi. Matn
 *    NOSOZLIKNI ta'riflaydi, amal taklif qilmaydi. Assert shu sababdan
 *    ijobiy (matn bor) VA salbiy (tugma yo'q) tomondan yozilgan.
 *
 * ⚠ T4 — CHETLAB O'TISH YO'LI BUZILMAGANIGA kafolat. DL-1 va DL-2 bitta
 *   qobiqda yashaydi (`schedule-dialog.tsx` sarlavhasidagi izoh); DL-1
 *   ning shoxlarini ajratish DL-2 ni jimgina yopib qo'yishi mumkin edi va
 *   o'shanda mavsumiy profil qo'shish yo'li YO'QOLARDI.
 *
 * ⚠ HTTP QATLAMI mock QILINADI (`nvr-form.test.tsx:39-50` naqshi), kesh
 *   EKILMAYDI: bu faylning mavzusi aynan SO'ROV HOLATI (`isPending` /
 *   `isError`), ya'ni keshga tayyor ma'lumot ekish o'lchanadigan
 *   narsaning o'zini yo'q qilardi.
 *
 * DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import messages from "../../../messages/uz-Latn.json";
import { ScheduleDialog } from "@/components/snapshots/schedule-dialog";
import type { ScheduleDialogRequest } from "@/components/snapshots/schedule-dialog";
import type { SnapshotSchedule } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const TIME_ZONE = "Asia/Tashkent";

/** uz-Latn kataloglaridagi AYNAN qiymatlar — literal yozilmaydi. */
const LOADING = messages.common.loading;
const SAVE = messages.common.save;
const SCHEDULE_MISSING = messages.snapshots.scheduleMissing;
const SCHEDULE_MISSING_HINT = messages.snapshots.scheduleMissingHint;
const ADD_SEASONAL = messages.snapshots.addSeasonal;
const EDIT_SCHEDULE = messages.snapshots.editSchedule;
const TIMES_LEGEND = messages.snapshots.times;
const GENERIC_ERROR = messages.errors.generic;

const ACTIVE_PROFILE: SnapshotSchedule = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "Standart",
  starts_on: "2026-08-15",
  ends_on: null,
  mode: "active",
  times: ["06:00:00", "06:30:00"],
};

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

/**
 * ⚠ `retry: false` MAJBURIY: usiz T2 ning rad etilgan so'rovi TanStack'ning
 *   standart qayta urinishlari bilan soniyalarga cho'zilardi va test
 *   xato holatiga umuman yetib bormasdan taymautga tushardi.
 */
function renderDialog(request: ScheduleDialogRequest | null): {
  onOpenChange: ReturnType<typeof vi.fn>;
} {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const onOpenChange = vi.fn();

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone={TIME_ZONE}
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <ScheduleDialog onOpenChange={onOpenChange} request={request} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
  return { onOpenChange };
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
});

afterEach(() => {
  clearSession();
});

/* ---------------------------------------------------------------------------
 * ⛔ T1 — BO'SH RO'YXAT «YUKLANMOQDA» EMAS
 * ------------------------------------------------------------------------ */

describe("DL-1: jadval profili topilmaganda", () => {
  test("⛔ so'rov tugagach «Yuklanmoqda» EKRANDAN CHIQADI", async () => {
    apiFetch.mockResolvedValue({ items: [] });

    renderDialog({ kind: "edit", scheduleId: null });

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    // ⛔ MARKAZIY ASSERT: yuklanish TUGAGAN, ya'ni bu matn yolg'on bo'lardi.
    await waitFor(() => {
      expect(screen.queryByText(LOADING)).toBeNull();
    });
  });

  test("nosozlik FAKT sifatida aytiladi — sarlavha va izoh bilan", async () => {
    apiFetch.mockResolvedValue({ items: [] });

    renderDialog({ kind: "edit", scheduleId: null });

    expect(await screen.findByText(SCHEDULE_MISSING)).toBeInTheDocument();
    expect(screen.getByText(SCHEDULE_MISSING_HINT)).toBeInTheDocument();
  });

  test("⛔ «qo'shing» chaqirig'i BERILMAYDI (§10.4)", async () => {
    apiFetch.mockResolvedValue({ items: [] });

    renderDialog({ kind: "edit", scheduleId: null });

    await screen.findByText(SCHEDULE_MISSING);

    // Jadval usta tomonidan AVTOMATIK yoziladi (D-01) — bu holatda
    // adminning qo'lidan keladigan amal YO'Q va uni taklif qilish
    // javobgarlikni noto'g'ri odamga yuklardi.
    expect(screen.queryByRole("button", { name: ADD_SEASONAL })).toBeNull();
    expect(screen.queryByRole("button", { name: SAVE })).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * T2 — XATO HAM «YUKLANMOQDA» GA AYLANMAYDI
 * ------------------------------------------------------------------------ */

describe("DL-1: so'rov yiqilganda", () => {
  test("tarjima qilingan xato matni ko'rinadi, «Yuklanmoqda» YO'Q", async () => {
    apiFetch.mockRejectedValue(new Error("network down"));

    renderDialog({ kind: "edit", scheduleId: null });

    /*
     * Noma'lum xato `marketErrorMessageKey` zanjiri orqali `errors.generic`
     * ga tushadi (T-02-99: xom `detail` HECH QACHON ko'rsatilmaydi).
     */
    expect(await screen.findByText(GENERIC_ERROR)).toBeInTheDocument();
    expect(screen.queryByText(LOADING)).toBeNull();

    // Xato ma'lumot nosozligi EMAS — ikkala matn bir vaqtda chiqmaydi.
    expect(screen.queryByText(SCHEDULE_MISSING)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * T3 — NAZORAT: PROFIL BOR BO'LSA HECH NIMA O'ZGARMAYDI
 * ------------------------------------------------------------------------ */

describe("DL-1: amaldagi profil bo'lganda (nazorat)", () => {
  test("tahrir formasi vaqtlar va «Saqlash» bilan chiziladi", async () => {
    apiFetch.mockResolvedValue({ items: [ACTIVE_PROFILE] });

    renderDialog({ kind: "edit", scheduleId: null });

    expect(await screen.findByText(TIMES_LEGEND)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SAVE })).toBeInTheDocument();

    // `06:00:00` -> `06:00` (§13.4) — chip o'chirish tugmasining nomida.
    expect(
      screen.getByRole("button", {
        name: `${messages.snapshots.removeTime} 06:00`,
      }),
    ).toBeInTheDocument();

    expect(screen.queryByText(SCHEDULE_MISSING)).toBeNull();
    expect(screen.queryByText(LOADING)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * T4 — DL-2 CHETLAB O'TISH YO'LI BUZILMAGAN
 * ------------------------------------------------------------------------ */

describe("DL-2: mavsumiy profil formasi", () => {
  test("`kind: create` da forma chiziladi — DL-1 shoxlari unga tegmaydi", async () => {
    apiFetch.mockResolvedValue({ items: [] });

    renderDialog({ kind: "create" });

    // Dialog sarlavhasi ham, yuborish tugmasi ham AYNI kalitni ishlatadi.
    expect(
      await screen.findByRole("button", { name: ADD_SEASONAL }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(messages.snapshots.scheduleName)).toBeInTheDocument();

    // DL-1 ning holat matnlari bu shoxda UMUMAN chizilmaydi.
    expect(screen.queryByText(SCHEDULE_MISSING)).toBeNull();
    expect(screen.queryByText(EDIT_SCHEDULE)).toBeNull();
  });
});
