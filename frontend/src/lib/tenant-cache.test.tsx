/**
 * KLIENT KESHINING TENANT CHEGARASI — CR-01 ning regressiya qulfi.
 *
 * 02-VERIFICATION.md ning 7-haqiqati (so'zma-so'z):
 *
 *   "Klient tomonidagi ma'lumot bozor almashtirilganda yoki chiqishda
 *    boshqa bozorga sizib chiqmaydi (CLAUDE.md: 'hamma jadvalda market_id')"
 *
 * NEGA IKKI YARIM ALOHIDA O'LCHANADI. Bo'shliqning ikkita MUSTAQIL sababi
 * bor va ikkalasi ham alohida yopilgan:
 *
 *   1. DOIRALASH — har bir domen kaliti `["m", marketId, ...]` bilan
 *      boshlanadi (`market-queries.ts`). U yolg'iz o'zi ham qisman ishlaydi:
 *      B bozori A ning kalitini O'QIY olmaydi. Lekin A ning qatorlari
 *      `gcTime` (5 daq) davomida xotirada qolaveradi.
 *   2. TOZALASH — sessiya identifikatori o'zgarganda `client.clear()`
 *      (`auth-store.ts` -> `query-provider.tsx`). U ham yolg'iz o'zi qisman
 *      ishlaydi, lekin doiralashsiz kelajakdagi har qanday kalit poygasida
 *      buzilardi.
 *
 * Agar bitta test ikkalasini BIRGA o'lchasa, biri butunlay olib
 * tashlanganda ham ikkinchisi uni yopib turib testni YASHIL qoldirardi —
 * ya'ni test hech narsani qulflamagan bo'lardi. Shuning uchun:
 *
 *   - "kalit izolyatsiyasi" va "sizib chiqish" testlari TOZALASH
 *     kanalini ATAYIN chetlab o'tadi (`updatePrincipal` — u
 *     `emitSessionReset()` ni chaqirmaydi), ya'ni ular FAQAT doiralashni
 *     o'lchaydi;
 *   - `clearSession` / `applySession` testlari esa kalit TUZILISHI haqida
 *     hech qanday da'vo qilmaydi (o'lchov QIYMAT bo'yicha: "A bozorining
 *     zona nomi keshda qoldimi?"), ya'ni ular FAQAT tozalashni o'lchaydi.
 *
 * `staleTime` ATAYIN standart holicha (`QueryProvider` dagi 30 s):
 * muammoning o'zi aynan shu oynada yashaydi — bozor almashgach eski
 * qatorlar hech qanday so'rovsiz, DARHOL chiziladi. Uni nolga tushirish
 * testni yolg'on-yashil qilardi.
 */
import type { QueryClient } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

import {
  AuthProvider,
  applySession,
  clearSession,
  setSession,
  subscribeSessionReset,
  updatePrincipal,
} from "@/lib/auth-store";
import { useZonesQuery, zonesKey } from "@/lib/market-queries";
import { QueryProvider } from "@/lib/query-provider";
import { useUsersQuery, usersKey } from "@/lib/queries";

const MARKET_A = "11111111-1111-4111-8111-111111111111";
const MARKET_B = "22222222-2222-4222-8222-222222222222";

/** Zona NOMLARI — keshda nimaning qolgani AYNAN shu bo'yicha o'lchanadi. */
const ZONE_A = "A bozori sabzavot qatori";
const ZONE_B = "B bozori go'sht qatori";

/** XODIM ISMLARI — `users` domeni uchun ayni o'lchov (WR-09). */
const STAFF_A = "A bozori nazoratchisi";
const STAFF_B = "B bozori nazoratchisi";

type ZoneList = { items: { id: string; name: string; stall_count: number }[] };
type UserList = { items: { id: string; full_name: string }[] };

/** `GET /zones` javobi — test uni bozor almashishidan OLDIN almashtiradi. */
let currentZones: ZoneList;

/** `GET /users` javobi — AYNI naqsh, boshqa domen. */
let currentUsers: UserList;

let capturedClient: QueryClient | null = null;

/**
 * Sinov komponenti — HAQIQIY `useZonesQuery()` ni ishlatadi.
 *
 * Kalit fabrikasi ham, `enabled` sharti ham asl kod: mock qilinadigan
 * yagona narsa — HTTP qatlami.
 */
function Probe(): ReactElement {
  const client = useQueryClient();
  const zones = useZonesQuery();

  // Render paytida EMAS, effektda: `QueryProvider` klientni o'z ichida
  // quradi va testga uni tashqaridan berish yo'li yo'q.
  useEffect(() => {
    capturedClient = client;
  }, [client]);

  return (
    <div data-testid="zones">
      {(zones.data?.items ?? []).map((item) => item.name).join(", ")}
    </div>
  );
}

/**
 * `users` domeni uchun sinov komponenti — HAQIQIY `useUsersQuery()`.
 *
 * ⛔ ALOHIDA PROBE, `Probe` ga qo'shimcha maydon EMAS: ikki domen bitta
 *    komponentda o'lchansa, zona kalitining sabotaji xodim da'vosini ham
 *    qizartirardi va darvoza qaysi domen buzilganini ⛔ AYTMASDI.
 */
function UsersProbe(): ReactElement {
  const client = useQueryClient();
  const users = useUsersQuery();

  useEffect(() => {
    capturedClient = client;
  }, [client]);

  return (
    <div data-testid="users">
      {(users.data?.items ?? [])
        .map((item) => item.full_name ?? "")
        .join(", ")}
    </div>
  );
}

/** Provayderlar PRODUKSIYADAGI tartibda: `QueryProvider` tashqarida. */
function renderProbe(): ReturnType<typeof render> {
  return render(
    <QueryProvider>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryProvider>,
  );
}

/** AYNI provayderlar, boshqa domen. */
function renderUsersProbe(): ReturnType<typeof render> {
  return render(
    <QueryProvider>
      <AuthProvider>
        <UsersProbe />
      </AuthProvider>
    </QueryProvider>,
  );
}

function seedSession(marketId: string, marketName: string): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId,
      marketName,
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

/**
 * Keshda YASHAYOTGAN barcha zona nomlari.
 *
 * O'lchov QIYMAT bo'yicha, kalit tuzilishi bo'yicha EMAS — shuning uchun
 * tozalash testlari doiralash sabotajida ham yashil qoladi (fayl
 * docstringiga qarang).
 */
function cachedZoneNames(): string[] {
  const cache = capturedClient?.getQueryCache().getAll() ?? [];
  return cache.flatMap((query) => {
    const data = query.state.data as ZoneList | undefined;
    return (data?.items ?? []).map((item) => item.name);
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  capturedClient = null;
  clearSession();
  currentZones = {
    items: [{ id: "zone-a", name: ZONE_A, stall_count: 3 }],
  };
  currentUsers = { items: [{ id: "user-a", full_name: STAFF_A }] };
  // Javob HAR CHAQIRUVDA joriy qiymatdan olinadi: test bozor almashishidan
  // oldin uni almashtiradi va shu bilan "eski qatormi yoki yangimi?"
  // savolini o'lchay oladi.
  //
  // ⛔ YO'L BO'YICHA AJRATILADI: ikkala domen bir xil javob olsa, xodim
  //   probe'i zona ma'lumotini chizardi va "sizib chiqish" da'vosi
  //   o'lchamoqchi bo'lgan narsani UMUMAN o'lchamasdi.
  apiFetch.mockImplementation((path: string) =>
    Promise.resolve(String(path).startsWith("/users") ? currentUsers : currentZones),
  );
});

afterEach(() => {
  clearSession();
});

describe("kalit izolyatsiyasi (doiralash yarmi)", () => {
  test("ikki bozorning `zones` kaliti TENG EMAS", () => {
    const keyA = zonesKey(MARKET_A);
    const keyB = zonesKey(MARKET_B);

    expect(keyA).not.toEqual(keyB);

    /*
     * Faqat "teng emas" YETMAYDI: kalitlar tasodifan farq qilishi ham
     * mumkin edi. Bu yerda prefiksning O'ZI tekshiriladi — `market_id`
     * kalitning ikkinchi segmentida turibdi.
     */
    expect(keyA[0]).toBe("m");
    expect(keyB[0]).toBe("m");
    expect(keyA[1]).toBe(MARKET_A);
    expect(keyB[1]).toBe(MARKET_B);
  });
});

describe("sizib chiqish (doiralash yarmi)", () => {
  test("A bozorining zonalari B kontekstida KO'RINMAYDI", async () => {
    seedSession(MARKET_A, "A bozori");
    renderProbe();

    await waitFor(() =>
      expect(screen.getByTestId("zones")).toHaveTextContent(ZONE_A),
    );

    // Server endi B bozorining zonalarini qaytaradi.
    currentZones = { items: [{ id: "zone-b", name: ZONE_B, stall_count: 1 }] };

    /*
     * ⚠ `updatePrincipal` ATAYIN, `applySession` EMAS: u sessiya-tozalash
     * kanalini ISHGA TUSHIRMAYDI. Ya'ni bu test uchun `client.clear()`
     * umuman yo'q — himoyaning YAGONA qatlami kalit doiralashi. Doiralash
     * olib tashlansa, kalit ikkala bozorda ham bir xil bo'lib qoladi va
     * quyidagi da'vo qizaradi.
     */
    act(() => {
      updatePrincipal({ marketId: MARKET_B, marketName: "B bozori" });
    });

    /*
     * DARHOLGI da'vo eng muhimi: 30 soniyalik `staleTime` ichida
     * doiralanmagan kalit hech qanday so'rovsiz ESKI qatorni chizardi —
     * aynan CR-01 da tasvirlangan "usta 2-qadamda A bozorining zonalarini
     * ko'rsatdi" holati.
     */
    expect(screen.getByTestId("zones")).not.toHaveTextContent(ZONE_A);

    // Va yangi kontekst o'z ma'lumotini haqiqatan olib keladi.
    await waitFor(() =>
      expect(screen.getByTestId("zones")).toHaveTextContent(ZONE_B),
    );
  });
});

/*
 * ---------------------------------------------------------------------------
 * `users` DOMENI — WR-09 ning doiralash yarmi.
 *
 * ⛔⛔ NEGA BU YERGA QO'SHILDI VA NEGA ALOHIDA FAYL OCHILMADI.
 *
 * `USERS_QUERY_KEY = ["users"]` bu faylning butun mantiqidan ⛔ ISTISNO edi:
 * qolgan har bir domen `["m", marketId, ...]` bilan boshlanadi, xodimlar
 * ro'yxati esa GLOBAL kalitda yashardi. Ikki oqibat o'lchanadi:
 *
 *   1. bozor almashtirilganda oldingi bozorning xodimlar ro'yxati keshda
 *      qolardi va audit izidagi aktor ⛔ BEGONA BOZOR xodimining nomi
 *      bilan yorliqlanardi (`vendor-labels.ts::useAssigneeLabels`);
 *   2. `domainKey(marketId)` prefiksi bo'yicha bekor qilish bu kalitga
 *      ⛔ YETIB BORMASDI.
 *
 * ⛔ ISTISNO SHU FAYLDA O'LCHANADI, chunki bu faylning O'ZI doiralash
 *    konvensiyasining darvozasi. Ikkinchi fayl ochish «qaysi domen qayerda
 *    qulflangan?» degan ikkinchi savolni tug'dirardi.
 * ------------------------------------------------------------------------- */

describe("kalit izolyatsiyasi: `users` domeni (WR-09)", () => {
  test("ikki bozorning `users` kaliti TENG EMAS va `market_id` PREFIKSDA", () => {
    const keyA = usersKey(MARKET_A);
    const keyB = usersKey(MARKET_B);

    expect(keyA).not.toEqual(keyB);

    /* ⛔ AYNI da'vo shakli, ayni sabab: tasodifiy farq YETARLI EMAS. */
    expect(keyA[0]).toBe("m");
    expect(keyB[0]).toBe("m");
    expect(keyA[1]).toBe(MARKET_A);
    expect(keyB[1]).toBe(MARKET_B);
  });
});

describe("sizib chiqish: `users` domeni (WR-09)", () => {
  test("A bozorining xodimlari B kontekstida KO'RINMAYDI", async () => {
    seedSession(MARKET_A, "A bozori");
    renderUsersProbe();

    await waitFor(() =>
      expect(screen.getByTestId("users")).toHaveTextContent(STAFF_A),
    );

    currentUsers = { items: [{ id: "user-b", full_name: STAFF_B }] };

    /*
     * ⚠ `updatePrincipal` ATAYIN (fayl docstringi): sessiya-tozalash
     *   kanali ISHGA TUSHMAYDI, ya'ni himoyaning YAGONA qatlami — kalit
     *   doiralashi. Doiralanmagan kalitda 30 soniyalik `staleTime` ichida
     *   ekran hech qanday so'rovsiz A bozorining xodimini chizardi.
     */
    act(() => {
      updatePrincipal({ marketId: MARKET_B, marketName: "B bozori" });
    });

    expect(screen.getByTestId("users")).not.toHaveTextContent(STAFF_A);

    await waitFor(() =>
      expect(screen.getByTestId("users")).toHaveTextContent(STAFF_B),
    );
  });

  test("bozorsiz sessiyada `GET /users` UMUMAN yuborilmaydi", async () => {
    /*
     * ⛔ `marketId === null` da kalit `["m", null, "users"]` bo'lardi va
     *   u BOZORSIZ javobni keshga yozardi — keyingi bozor o'sha yozuvni
     *   ko'rmasa ham, kesh «kimningdir xodimlari» qatorini saqlab
     *   qolardi. `enabled` sharti buni ILDIZIDAN kesadi.
     */
    clearSession();
    renderUsersProbe();

    await waitFor(() => {
      expect(screen.getByTestId("users")).toBeInTheDocument();
    });

    expect(apiFetch).not.toHaveBeenCalled();
  });
});

describe("kesh tozalash (tozalash yarmi)", () => {
  test("`clearSession()` A bozorining qatorlarini keshda QOLDIRMAYDI", async () => {
    seedSession(MARKET_A, "A bozori");
    renderProbe();

    await waitFor(() =>
      expect(screen.getByTestId("zones")).toHaveTextContent(ZONE_A),
    );
    // Boshlang'ich holat MA'NOLI: keshda haqiqatan ma'lumot bor.
    expect(cachedZoneNames()).toContain(ZONE_A);

    act(() => {
      clearSession();
    });

    /*
     * `getAll()` ning UZUNLIGI tekshirilmaydi: tozalashdan keyin React
     * qayta render qiladi va bozorsiz sessiyada `enabled: false` kuzatuvchi
     * BO'SH yozuvni qayta ro'yxatdan o'tkazadi. O'lchanadigan narsa —
     * MA'LUMOTNING yo'qligi, yozuv sonining emas.
     */
    expect(cachedZoneNames()).not.toContain(ZONE_A);
    expect(cachedZoneNames()).toHaveLength(0);
  });

  test("`applySession()` boshqa bozor bilan chaqirilganda kesh bo'shaydi", async () => {
    seedSession(MARKET_A, "A bozori");
    renderProbe();

    await waitFor(() =>
      expect(screen.getByTestId("zones")).toHaveTextContent(ZONE_A),
    );
    expect(cachedZoneNames()).toContain(ZONE_A);

    currentZones = { items: [{ id: "zone-b", name: ZONE_B, stall_count: 1 }] };

    act(() => {
      applySession({
        accessToken: "new-token",
        roles: ["market_admin"],
        market: { id: MARKET_B, name: "B bozori", is_active: true },
      });
    });

    // A bozorining nomi keshning HECH BIR yozuvida qolmagan.
    expect(cachedZoneNames()).not.toContain(ZONE_A);
  });
});

describe("NAZORAT: tozalash haddan tashqari keng EMAS", () => {
  test("token yangilash (BIR XIL bozor) keshni SAQLAYDI", async () => {
    seedSession(MARKET_A, "A bozori");
    renderProbe();

    await waitFor(() =>
      expect(screen.getByTestId("zones")).toHaveTextContent(ZONE_A),
    );

    /*
     * Javob ATAYIN almashtiriladi: agar tozalash noto'g'ri ishga tushsa,
     * kuzatuvchi qayta so'rov yuborib BOSHQA ma'lumot olardi va quyidagi
     * da'vo qizarardi. Javobni o'zgartirmasak, sabotaj ham yashil
     * ko'rinishi mumkin edi.
     */
    currentZones = { items: [{ id: "zone-b", name: ZONE_B, stall_count: 1 }] };

    act(() => {
      applySession({
        accessToken: "refreshed-token",
        roles: ["market_admin"],
        market: { id: MARKET_A, name: "A bozori", is_active: true },
      });
    });

    /*
     * NAZORAT HOLATI MAJBURIY: usiz "kesh tozalanadi" da'vosi "kesh DOIM
     * tozalanadi" holatidan ajralmasdi. `applySession` `/auth/refresh`
     * javobida ham chaqiriladi (`api-client.ts:164`) va u yerda bozor
     * o'zgarmaydi — har 15 daqiqada butun keshni yo'q qilish foydalanuvchi
     * ishlab turgan ekranni sababsiz qayta yuklardi.
     */
    expect(cachedZoneNames()).toContain(ZONE_A);
  });

  test("obuna bekor qilingandan keyin tinglovchi CHAQIRILMAYDI", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeSessionReset(listener);

    clearSession();
    // AYNAN bir marta — ikki kanal chalkashib ketmagan.
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    clearSession();

    /*
     * Bekor qilish ishlamasa, `QueryProvider` har montajda yangi tinglovchi
     * qoldirib, vaqt o'tgani sari bir xil `clear()` ni o'nlab marta
     * chaqiradigan sizib chiquvchi reyestr yig'ilardi.
     */
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
