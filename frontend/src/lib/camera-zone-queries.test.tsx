/**
 * ZONA SO'ROV QATLAMINING TO'RT DA'VOSI.
 *
 * =============================================================================
 * ⚠ 1. NEGA TIP TIZIMI YOLG'IZ YETARLI EMAS — O'LCHANGAN (04-02).
 *
 *     domainKey(marketId, "camera-zones", cameraId)   ✅ to'g'ri
 *     domainKey("camera-zones", cameraId)             ✅ TIP JIHATIDAN YAROQLI
 *
 *   Ikkinchi shakl ham kompilyatsiyadan o'tadi — `domainKey` ning birinchi
 *   parametri `string`, ya'ni domen nomi ham unga tushadi. Natija jimgina
 *   falokat: kalit BARCHA bozorlar uchun bir xil bo'lib qoladi, ekran
 *   ochiladi, typecheck yashil, faqat A bozorining zonalari B bozorining
 *   sessiyasida ko'rinadi (CR-01 ning aynan o'zi). Shuning uchun kalitning
 *   SHAKLI shu yerda, QIYMAT bo'yicha qulflanadi.
 *
 * ⛔ 2. POLL YO'Q (§8.5). Zonalar faqat foydalanuvchining o'z tahriridan
 *      o'zgaradi. Poll chiziq sudrayotgan paytda javob kelib, tugallanmagan
 *      poligonni bosib ketish yo'lini ochardi.
 *
 * ⛔ 3. Z-2 QAT'IY: kadr yo'q -> muharrir OCHILMAYDI. Bu qaror SOF
 *      FUNKSIYADA yashaydi va shu yerda literal qulflanadi — ekran uni
 *      faqat CHAQIRADI (`camera-page-state.ts` da o'rnatilgan naqsh).
 *
 * ⚠ 4. KOORDINATA KLIENTDA QAYTA YAXLITLANMAYDI. 05-06 ning S6 sabotaji
 *      o'lchagan dars: «aylanma yo'qotishsiz» va «server bilan bir xil
 *      yaxlitlaydi» IKKI MUSTAQIL xususiyat. Klientda ikkinchi yaxlitlash
 *      nuqtasi ochilsa, u serverning `_round_half_up()` i bilan bir kun
 *      ajralib ketardi — shuning uchun bu yerda yaxlitlash UMUMAN YO'Q va
 *      test buni bit darajasida tekshiradi.
 * =============================================================================
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

import type { CaptureRun } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  cameraFrameKey,
  cameraZonesKey,
  latestOkFrame,
  useCameraZones,
  useReplaceCameraZones,
  useZoneCoverage,
  zoneCoverageKey,
  zoneEditorState,
} from "@/lib/camera-zone-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_MARKET_ID = "99999999-9999-4999-8999-999999999999";
const CAMERA_ID = "77777777-7777-4777-8777-777777777777";
const OTHER_CAMERA_ID = "88888888-8888-4888-8888-888888888888";
const STALL_ID = "44444444-4444-4444-8444-444444444444";
const TODAY = "2026-09-01";

let client: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

function seedSession(marketId: string | null): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function makeRun(overrides: Partial<CaptureRun> = {}): CaptureRun {
  return {
    run_id: "66666666-6666-4666-8666-666666666666",
    camera_id: CAMERA_ID,
    channel_no: 3,
    camera_name: "Kiyim qatori",
    slot_time: "06:30:00",
    scheduled_at: "2026-09-01T01:30:00Z",
    status: "succeeded",
    attempts: 1,
    error_code: null,
    quality_verdict: "ok",
    snapshot_id: "55555555-5555-4555-8555-555555555555",
    ...overrides,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  apiClientMock.apiFetch.mockResolvedValue({
    items: [],
    frame_width: null,
    frame_height: null,
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* ---------------------------------------------------------------------------
 * 1. KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4)
 * ------------------------------------------------------------------------ */

describe("kalitlar TUG'ILISHIDANOQ doiralangan (§5.4)", () => {
  test("har fabrika ['m', marketId, ...] shaklida boshlanadi", () => {
    expect(cameraZonesKey(MARKET_ID, CAMERA_ID)).toEqual([
      "m",
      MARKET_ID,
      "camera-zones",
      CAMERA_ID,
    ]);
    expect(zoneCoverageKey(MARKET_ID)).toEqual([
      "m",
      MARKET_ID,
      "zone-coverage",
    ]);

    // BIRINCHI element — bozor, ikkinchisi — uning identifikatori.
    expect(cameraZonesKey(MARKET_ID, CAMERA_ID)[0]).toBe("m");
    expect(cameraZonesKey(MARKET_ID, CAMERA_ID)[1]).toBe(MARKET_ID);
  });

  test("boshqa bozor kaliti BOSHQA — prefiks bo'yicha kesishmaydi", () => {
    expect(cameraZonesKey(MARKET_ID, CAMERA_ID)).not.toEqual(
      cameraZonesKey(OTHER_MARKET_ID, CAMERA_ID),
    );
    expect(zoneCoverageKey(MARKET_ID)).not.toEqual(
      zoneCoverageKey(OTHER_MARKET_ID),
    );

    for (const key of [
      cameraZonesKey(MARKET_ID, CAMERA_ID),
      zoneCoverageKey(MARKET_ID),
      cameraFrameKey(MARKET_ID, CAMERA_ID, TODAY),
    ]) {
      expect(key.slice(0, 2)).toEqual(["m", MARKET_ID]);
    }
  });

  test("kamera kalitning bir qismi — kamera almashsa kesh yozuvi ham almashadi", () => {
    expect(cameraZonesKey(MARKET_ID, CAMERA_ID)).not.toEqual(
      cameraZonesKey(MARKET_ID, OTHER_CAMERA_ID),
    );
  });

  test("kadr kaliti — zona kalitining BOLASI, mustaqil fabrika emas", () => {
    /*
     * Bola kalit doiralashni MEROS oladi va ota kalitning bekor
     * qilinishi uni ham qamraydi (TanStack prefiks bo'yicha
     * solishtiradi). Yangi global fabrika ikkinchi doiralash yuzasini
     * ochardi — `snapshot-dialog.tsx::snapshotImageKey` naqshi.
     */
    const parent = cameraZonesKey(MARKET_ID, CAMERA_ID);
    const child = cameraFrameKey(MARKET_ID, CAMERA_ID, TODAY);
    expect(child.slice(0, parent.length)).toEqual([...parent]);
    expect(child).toEqual([...parent, "frame", TODAY]);
  });

  test("bozorsiz sessiyada so'rov YUBORILMAYDI (`enabled` kontrakti)", () => {
    seedSession(null);

    const zones = renderHook(() => useCameraZones(CAMERA_ID), { wrapper });
    const coverage = renderHook(() => useZoneCoverage(), { wrapper });

    expect(zones.result.current.fetchStatus).toBe("idle");
    expect(coverage.result.current.fetchStatus).toBe("idle");
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });

  test("kamerasiz (`null`) so'rov ham YUBORILMAYDI", () => {
    seedSession(MARKET_ID);

    const { result } = renderHook(() => useCameraZones(null), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });

  test("bozor bor sessiyada so'rov ketadi va `camera_id` yo'lda (nazorat)", () => {
    seedSession(MARKET_ID);

    renderHook(() => useCameraZones(CAMERA_ID), { wrapper });

    expect(apiClientMock.apiFetch).toHaveBeenCalledTimes(1);
    expect(apiClientMock.apiFetch.mock.calls[0][0]).toBe(
      `/camera-zones?camera_id=${CAMERA_ID}`,
    );
  });

  test("qamrov `/coverage` yo'liga boradi (nazorat)", () => {
    seedSession(MARKET_ID);
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 0,
      uncovered: 0,
      cameras_without_zones: 0,
    });

    renderHook(() => useZoneCoverage(), { wrapper });

    expect(apiClientMock.apiFetch.mock.calls[0][0]).toBe(
      "/camera-zones/coverage",
    );
  });
});

/* ---------------------------------------------------------------------------
 * 2. ⛔ POLL YO'Q (§8.5)
 * ------------------------------------------------------------------------ */

describe("poll kontrakti — Y-1 da poll UMUMAN yo'q (§8.5)", () => {
  test("zonalar so'rovida `refetchInterval` QO'YILMAGAN", async () => {
    seedSession(MARKET_ID);
    renderHook(() => useCameraZones(CAMERA_ID), { wrapper });

    await waitFor(() =>
      expect(
        client.getQueryCache().find({
          queryKey: cameraZonesKey(MARKET_ID, CAMERA_ID),
        }),
      ).toBeDefined(),
    );

    /*
     * ⚠ Bu YAGONA joy TanStack ning saqlangan sozlamasini o'qiydi va u
     *   ATAYIN (`snapshot-queries.test.tsx:318-331` naqshi): poll —
     *   kutubxonaning O'Z xulqi, ya'ni uni sof funksiyaga ko'chirib
     *   bo'lmaydi. Tip qo'lda ochiladi, chunki `QueryOptions` bu
     *   observer-darajasidagi maydonni e'lon qilmaydi.
     */
    const entry = client
      .getQueryCache()
      .find({ queryKey: cameraZonesKey(MARKET_ID, CAMERA_ID) });
    const options = entry?.options as { refetchInterval?: unknown } | undefined;

    expect(options?.refetchInterval).toBeUndefined();
  });

  test("qamrov so'rovida ham `refetchInterval` QO'YILMAGAN", async () => {
    seedSession(MARKET_ID);
    apiClientMock.apiFetch.mockResolvedValue({
      covered: 1,
      uncovered: 0,
      cameras_without_zones: 0,
    });
    renderHook(() => useZoneCoverage(), { wrapper });

    await waitFor(() =>
      expect(
        client.getQueryCache().find({ queryKey: zoneCoverageKey(MARKET_ID) }),
      ).toBeDefined(),
    );

    const entry = client
      .getQueryCache()
      .find({ queryKey: zoneCoverageKey(MARKET_ID) });
    const options = entry?.options as { refetchInterval?: unknown } | undefined;

    expect(options?.refetchInterval).toBeUndefined();
  });
});

/* ---------------------------------------------------------------------------
 * 3. ⛔ Z-2 — KADRSIZ MUHARRIR OCHILMAYDI (§8.2)
 * ------------------------------------------------------------------------ */

describe("zoneEditorState — Z-1…Z-8 ning darvozasi", () => {
  const ready = {
    isError: false,
    isPending: false,
    frameWidth: 480,
    frameSnapshotId: "55555555-5555-4555-8555-555555555555",
  };

  test("⛔ serverda kadr yo'q (`frame_width === null`) -> muharrir OCHILMAYDI", () => {
    expect(zoneEditorState({ ...ready, frameWidth: null })).toBe("no-frame");
  });

  test("⛔ klient kadr topa olmadi (`frameSnapshotId === null`) -> ham OCHILMAYDI", () => {
    /*
     * Ikki shart YOKI bilan bog'langan va bu ataylab: ikkalasining ham
     * oqibati bir xil — hozir chizib bo'lmaydi — va keyingi qadami
     * bitta: kadr olish bo'limi.
     */
    expect(zoneEditorState({ ...ready, frameSnapshotId: null })).toBe(
      "no-frame",
    );
  });

  test("kadr ham, zonalar ham bor -> `ready` (nazorat)", () => {
    expect(zoneEditorState(ready)).toBe("ready");
  });

  test("yuklanish `no-frame` DAN USTUN — aks holda har ochilishda E-1 miltillardi", () => {
    expect(
      zoneEditorState({ ...ready, isPending: true, frameWidth: null }),
    ).toBe("loading");
  });

  test("⛔ XATO HAMMASIDAN USTUN — u «kadr yo'q» bilan ALMASHTIRILMAYDI", () => {
    /*
     * Tartib pastga tushsa, yiqilgan so'rov «kadr yo'q» bo'lib
     * ko'rinardi va admin nosozlikni kadr olish bo'limidan qidirardi —
     * holbuki muammo tarmoqda. Ikki holatning KEYINGI QADAMI boshqa:
     * «Qayta urinish» va «Kadr olishga o'tish».
     */
    expect(
      zoneEditorState({
        isError: true,
        isPending: true,
        frameWidth: null,
        frameSnapshotId: null,
      }),
    ).toBe("load-failed");
  });

  test("`undefined` kadr kengligi ham `no-frame` (javob hali kelmagan holat emas)", () => {
    expect(
      zoneEditorState({ ...ready, frameWidth: undefined, isPending: false }),
    ).toBe("no-frame");
  });
});

/* ---------------------------------------------------------------------------
 * KADR TANLASH QOIDASI — SERVERNIKI BILAN BIR XIL SHART
 * ------------------------------------------------------------------------ */

describe("latestOkFrame", () => {
  test("kun ichidagi ENG KECHKI yaroqli kadr tanlanadi", () => {
    const rows = [
      makeRun({ slot_time: "06:00:00", run_id: "a" }),
      makeRun({ slot_time: "18:00:00", run_id: "b" }),
      makeRun({ slot_time: "12:00:00", run_id: "c" }),
    ];
    expect(latestOkFrame(rows, CAMERA_ID)?.run_id).toBe("b");
  });

  test("⛔ FAQAT `ok` — qorong'i yoki buzuq kadr OLINMAYDI", () => {
    /*
     * Serverning `latest_frame_size()` i ham aynan shu shartni qo'yadi.
     * Ikki tomon bu yerda ajralsa, ekranda ko'rinadigan kadr nisbat
     * lentasi hisoblagan kadrdan boshqa bo'lardi.
     */
    const rows = [
      makeRun({ slot_time: "18:00:00", quality_verdict: "dark", run_id: "b" }),
      makeRun({ slot_time: "06:00:00", run_id: "a" }),
    ];
    expect(latestOkFrame(rows, CAMERA_ID)?.run_id).toBe("a");
  });

  test("`snapshot_id === null` qator TASHLAB YUBORILADI", () => {
    // Sifat hukmi `ok` bo'lsa ham kadr arxivdan chiqarilgan bo'lishi
    // mumkin — u holda rasm marshruti hech qachon bayt bermasdi.
    const rows = [
      makeRun({ slot_time: "18:00:00", snapshot_id: null, run_id: "b" }),
      makeRun({ slot_time: "06:00:00", run_id: "a" }),
    ];
    expect(latestOkFrame(rows, CAMERA_ID)?.run_id).toBe("a");
  });

  test("boshqa kameraning qatori olinmaydi", () => {
    const rows = [makeRun({ camera_id: OTHER_CAMERA_ID, slot_time: "18:00:00" })];
    expect(latestOkFrame(rows, CAMERA_ID)).toBeNull();
  });

  test("javob kelmagan (`undefined`) va bo'sh kun — ikkalasi ham `null`", () => {
    expect(latestOkFrame(undefined, CAMERA_ID)).toBeNull();
    expect(latestOkFrame([], CAMERA_ID)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * 4. ⚠ SAQLASHDA KOORDINATA QAYTA YAXLITLANMAYDI
 * ------------------------------------------------------------------------ */

describe("useReplaceCameraZones — tana kontrakti", () => {
  test("⚠ koordinata BIT DARAJASIDA o'zgarmasdan yuboriladi", async () => {
    seedSession(MARKET_ID);

    /*
     * ⛔ FIXTURE HAQIQIYLIGI ALOHIDA TEKSHIRILADI (05-03 ning S2 darsi):
     *   agar tanlangan sonlar tasodifan «yaxlit» bo'lsa, yaxlitlash
     *   qo'shilgan taqdirda ham test YASHIL qolardi va u o'z farazini
     *   tasdiqlardi. Shuning uchun har koordinata yaxlitlanganda
     *   HAQIQATAN o'zgarishi oldindan isbotlanadi.
     */
    const polygon = [
      [0.123456789, 0.987654321],
      [0.5000000000000001, 0.49999999999999994],
      [0.3333333333333333, 0.6180339887498949],
    ] as const;

    for (const [x, y] of polygon) {
      expect(Math.round(x * 1280) / 1280).not.toBe(x);
      expect(Math.round(y * 720) / 720).not.toBe(y);
    }

    apiClientMock.apiFetch.mockResolvedValue({
      items: [],
      frame_width: 480,
      frame_height: 270,
    });

    const { result } = renderHook(() => useReplaceCameraZones(CAMERA_ID), {
      wrapper,
    });

    await result.current.mutateAsync([
      {
        stallId: STALL_ID,
        polygon,
        sourceWidth: 480,
        sourceHeight: 270,
      },
    ]);

    const [path, options] = apiClientMock.apiFetch.mock.calls[0];
    expect(path).toBe(`/camera-zones?camera_id=${CAMERA_ID}`);
    expect(options.method).toBe("PUT");
    expect(options.body).toEqual({
      zones: [
        {
          stall_id: STALL_ID,
          polygon: polygon.map(([x, y]) => [x, y]),
          source_width: 480,
          source_height: 270,
        },
      ],
    });
  });

  test("⛔ `id` va `version` tanaga TUSHMAYDI — versiya serverda hisoblanadi", async () => {
    seedSession(MARKET_ID);
    apiClientMock.apiFetch.mockResolvedValue({
      items: [],
      frame_width: 480,
      frame_height: 270,
    });

    const { result } = renderHook(() => useReplaceCameraZones(CAMERA_ID), {
      wrapper,
    });
    await result.current.mutateAsync([
      {
        stallId: STALL_ID,
        polygon: [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
        sourceWidth: 480,
        sourceHeight: 270,
      },
    ]);

    const body = apiClientMock.apiFetch.mock.calls[0][1].body as {
      zones: Record<string, unknown>[];
    };
    expect(Object.keys(body.zones[0]).sort()).toEqual([
      "polygon",
      "source_height",
      "source_width",
      "stall_id",
    ]);
  });

  test("javob keshga TO'G'RIDAN-TO'G'RI yoziladi — ikkinchi `GET` yo'q", async () => {
    seedSession(MARKET_ID);
    const response = {
      items: [],
      frame_width: 480,
      frame_height: 270,
    };
    apiClientMock.apiFetch.mockResolvedValue(response);

    const { result } = renderHook(() => useReplaceCameraZones(CAMERA_ID), {
      wrapper,
    });
    await result.current.mutateAsync([]);

    expect(
      client.getQueryData(cameraZonesKey(MARKET_ID, CAMERA_ID)),
    ).toEqual(response);
    // Faqat `PUT` — qayta o'qish so'rovi yuborilmadi.
    expect(apiClientMock.apiFetch).toHaveBeenCalledTimes(1);
  });
});
