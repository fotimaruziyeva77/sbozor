/**
 * Mutatsiyalarning INVALIDATSIYA BOG'LANISHLARI.
 *
 * NEGA AYNAN BU: bu modulning butun mavjudlik sababi — "yozgandan keyin
 * nima eskiradi?" savoliga BITTA joyda javob berish. Bog'lanish uzilganda
 * hech narsa yiqilmaydi: typecheck yashil, lint yashil, ekran ochiladi.
 * Faqat admin yangi rastani ro'yxatda ko'rib turadi-yu, XARITADA ko'rmaydi
 * va ustada "rasta qo'shilmagan" to'sig'i turaveradi. Bunday nosozlikni
 * faqat kalitlarni HAQIQATAN o'lchab ushlash mumkin.
 *
 * O'lchov usuli: `QueryClient.invalidateQueries` josuslanadi va mutatsiya
 * bajarilgandan keyin chaqirilgan kalitlarning BIRINCHI segmenti yig'iladi.
 * Birinchi segment — kalit oilasining ildizi (`["stalls", "list", ...]` ->
 * `stalls`), ya'ni test kalit ichki tuzilishiga bog'lanib qolmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

import {
  useCloseAssignment,
  useCreateAssignment,
  useCreateStall,
  useCreateTariff,
  useCreateZone,
  useImportMutation,
  useSetStallCategory,
  useUpdateWeekdays,
} from "@/lib/market-queries";

let client: QueryClient;
let invalidated: string[];

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.resetAllMocks();
  invalidated = [];
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  vi.spyOn(client, "invalidateQueries").mockImplementation((filters) => {
    const key = filters?.queryKey as readonly unknown[] | undefined;
    if (key && key.length > 0) invalidated.push(String(key[0]));
    return Promise.resolve();
  });
  // Javob shakli bu testda ahamiyatsiz: `apiFetch` mock qilingan, ya'ni
  // sxema tekshiruvi umuman ishga tushmaydi. O'lchanadigan narsa — YON
  // TA'SIRLAR to'plami.
  apiFetch.mockResolvedValue(undefined);
});

afterEach(() => {
  client.clear();
});

/** Mutatsiyani bajaradi va bekor qilingan kalit ildizlarini qaytaradi. */
async function runMutation<TVars>(
  useHook: () => { mutate: (vars: TVars) => void; isSuccess: boolean },
  vars: TVars,
): Promise<Set<string>> {
  const { result } = renderHook(useHook, { wrapper });
  result.current.mutate(vars);
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  return new Set(invalidated);
}

describe("rasta mutatsiyalari", () => {
  test("useCreateStall ro'yxat, xarita va usta holatini bekor qiladi", async () => {
    const keys = await runMutation(useCreateStall, {
      code: "12",
      zone_id: "z",
      category_id: "c",
      status: "active",
      note: null,
    });

    // Rejaning qabul mezoni: uchtasi HAM bo'lishi shart.
    expect(keys).toContain("stalls");
    expect(keys).toContain("map");
    expect(keys).toContain("setup-status");
  });

  test("useCreateStall zona va toifa SANOQLARINI ham bekor qiladi", async () => {
    const keys = await runMutation(useCreateStall, {
      code: "12",
      zone_id: "z",
      category_id: "c",
      status: "active",
      note: null,
    });

    // `ZoneItem.stall_count` va `CategoryItem.stall_count` yangi rasta bilan
    // o'zgaradi; eskirgan sanoq "bu zonani o'chira olamanmi?" savoliga
    // YOLG'ON javob berardi.
    expect(keys).toContain("zones");
    expect(keys).toContain("categories");
  });

  test("useSetStallCategory xarita va usta holatini ham bekor qiladi", async () => {
    const keys = await runMutation(useSetStallCategory, {
      stallId: "s",
      category_id: "c",
      valid_from: "2026-09-01",
    });

    expect(keys).toContain("stalls");
    expect(keys).toContain("map");
    expect(keys).toContain("setup-status");
  });
});

describe("tarif mutatsiyalari", () => {
  test("useCreateTariff TOIFA ro'yxatini ham bekor qiladi", async () => {
    const keys = await runMutation(useCreateTariff, {
      category_id: "c",
      amount_soum: 7000,
      valid_from: "2026-09-01",
    });

    // `CategoryItem.current_tariff_soum` shu mutatsiyadan keyin o'zgaradi:
    // usiz "tarif kiritilmagan" ogohlantirishi narx qo'shilgandan keyin
    // ham ekranda turaverardi.
    expect(keys).toContain("tariffs");
    expect(keys).toContain("categories");
    expect(keys).toContain("setup-status");
  });
});

describe("biriktirish mutatsiyalari", () => {
  test("useCreateAssignment sotuvchi, rasta va xaritani bekor qiladi", async () => {
    const keys = await runMutation(useCreateAssignment, {
      stall_id: "s",
      vendor_id: "v",
      from_date: "2026-08-01",
      to_date: null,
    });

    // Xaritadagi `has_vendor` eskirsa, "band, lekin sotuvchisiz" belgisi
    // jimgina yolg'on bo'lardi — bu 6-fazadagi anomaliya hisobining asosi.
    expect(keys).toContain("vendors");
    expect(keys).toContain("stalls");
    expect(keys).toContain("map");
  });

  test("useCloseAssignment ham xuddi shu to'plamni bekor qiladi", async () => {
    const keys = await runMutation(useCloseAssignment, {
      id: "a",
      to_date: "2026-08-31",
    });

    expect(keys).toContain("vendors");
    expect(keys).toContain("stalls");
    expect(keys).toContain("map");
  });
});

describe("import va kalendar", () => {
  test("rasta importi ro'yxat, xarita va usta holatini bekor qiladi", async () => {
    const { result } = renderHook(() => useImportMutation("stalls"), {
      wrapper,
    });
    result.current.mutate(new File(["x"], "rastalar.xlsx"));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const keys = new Set(invalidated);
    expect(keys).toContain("stalls");
    expect(keys).toContain("map");
    expect(keys).toContain("setup-status");
  });

  test("sotuvchi importi RASTA ro'yxatini emas, sotuvchini bekor qiladi", async () => {
    const { result } = renderHook(() => useImportMutation("vendors"), {
      wrapper,
    });
    result.current.mutate(new File(["x"], "sotuvchilar.xlsx"));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // NAZORAT: `kind` tarmog'i haqiqatan ishlaydi. Ikkalasi ham bir xil
    // to'plamni bekor qilsa, test hech narsani ajratmagan bo'lardi.
    const keys = new Set(invalidated);
    expect(keys).toContain("vendors");
    expect(keys).not.toContain("stalls");
  });

  test("ish kunlari usta holatini bekor qiladi", async () => {
    const keys = await runMutation(useUpdateWeekdays, [1, 2, 3, 4, 5, 6]);

    expect(keys).toContain("calendar");
    expect(keys).toContain("setup-status");
  });
});

describe("NAZORAT: o'lchov usuli haqiqiy", () => {
  test("zona yaratish XARITANI bekor QILMAYDI", async () => {
    const keys = await runMutation(useCreateZone, { name: "Sabzavot" });

    // Agar josus har qanday kalitni yozib olayotgan bo'lsa (masalan
    // `invalidateQueries` ni umuman ushlamayotgan bo'lsa), bu da'vo ham
    // yiqilardi — ya'ni yuqoridagi ijobiy testlar ma'noli.
    expect(keys).toContain("zones");
    expect(keys).not.toContain("map");
  });

  test("FormData yuborilganda tana JSON ga aylantirilmaydi", async () => {
    const { result } = renderHook(() => useImportMutation("stalls"), {
      wrapper,
    });
    result.current.mutate(new File(["x"], "rastalar.xlsx"));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const options = apiFetch.mock.calls[0][1] as { body: unknown };
    expect(options.body).toBeInstanceOf(FormData);
  });
});
