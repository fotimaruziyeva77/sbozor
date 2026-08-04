/**
 * DL-3 — D-12 NING UI TARJIMASI: IKKI FAKT EMAS, BITTA XULOSA.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   `dark` + `ir_night` va `dark` + `day` TURLI JUMLA BERADI.
 *
 *   Ikkalasida ham sifat hukmi BIR XIL (`dark`) va ikkala kadr ham
 *   hisobga kirmaydi. Lekin adminning savoli sifat haqida emas —
 *   «kamera buzuqmi?» — va javob faqat JUFTLIKNING TALQINIDAN chiqadi:
 *
 *     qorong'i + tungi rejim   -> NORMAL, hech nima qilinmaydi;
 *     qorong'i + kunduzgi rejim -> NOSOZLIK, linza va yoritish tekshiriladi.
 *
 *   Ikki alohida belgi (`[Qorong'i]` `[Tungi rejim]`) bu talqinni
 *   foydalanuvchining zimmasiga yuklardi — kuniga 175 marta. Shuning
 *   uchun sakkiz juftlik — sakkiz jumla, va bu test ikkala uchning ham
 *   BOSHQA matn berishini talab qiladi.
 * =============================================================================
 *
 * Qolgan da'volar (§6.6, §10.5, §14.3, T-02-99):
 *   * noma'lum xato kodida umumiy xabar chiqadi va XOM TAFSILOT
 *     ko'rsatilmaydi;
 *   * `purged` holati HALOL ko'rsatiladi — rasm o'rniga sabab bloki;
 *   * `is_billable === false` belgisi ombor qatlamidan OLDIN turadi;
 *   * texnik o'lchovlar FAQAT mavjud bo'lganda chiziladi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  SnapshotDialog,
  snapshotImageKey,
  verdictKey,
} from "@/components/snapshots/snapshot-dialog";
import type { CaptureRun, SnapshotDetail } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { snapshotKey } from "@/lib/snapshot-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SNAPSHOT_ID = "88888888-8888-4888-8888-888888888888";
const CAMERA = "Kiyim qatori";

function makeRun(overrides: Partial<CaptureRun> = {}): CaptureRun {
  return {
    run_id: "66666666-6666-4666-8666-666666666666",
    camera_id: "77777777-7777-4777-8777-777777777777",
    channel_no: 3,
    camera_name: CAMERA,
    slot_time: "06:30:00",
    scheduled_at: "2026-09-01T01:30:00Z",
    status: "succeeded",
    attempts: 1,
    error_code: null,
    quality_verdict: "ok",
    snapshot_id: SNAPSHOT_ID,
    ...overrides,
  };
}

function makeDetail(overrides: Partial<SnapshotDetail> = {}): SnapshotDetail {
  return {
    id: SNAPSHOT_ID,
    camera_id: "77777777-7777-4777-8777-777777777777",
    business_date: "2026-09-01",
    slot_time: "06:30:00",
    scheduled_at: "2026-09-01T01:30:00Z",
    captured_at: "2026-09-01T01:30:04Z",
    size_bytes: 63_488,
    width: 1280,
    height: 720,
    quality_verdict: "ok",
    light_mode: "day",
    capture_method: "go2rtc",
    storage_tier: "full",
    is_billable: true,
    quality_mean: 118.5,
    quality_stddev: 41.25,
    quality_saturation: 0.32,
    quality_thresholds_version: 1,
    ...overrides,
  };
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

function renderDialog(options: {
  detail?: SnapshotDetail | null;
  run?: CaptureRun;
}): ReturnType<typeof render> {
  const run = options.run ?? makeRun();
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });

  if (options.detail != null) {
    client.setQueryData(snapshotKey(MARKET_ID, SNAPSHOT_ID), options.detail);
    /*
     * Rasm baytlari ham keshga EKILADI — aks holda test HTTP qatlamiga
     * chiqib ketardi. Kalitning O'ZI shu modulning eksporti, ya'ni
     * doiralash (birinchi argument `marketId`) test yo'lida ham
     * o'lchanadi.
     */
    client.setQueryData(snapshotImageKey(MARKET_ID, SNAPSHOT_ID), "blob:test");
  }

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <SnapshotDialog
            cameraName={CAMERA}
            canNext
            canPrev
            channelNo={3}
            onNavigate={() => {}}
            onOpenChange={() => {}}
            open
            run={run}
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
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
 * ⛔ D-12 — SAKKIZ JUFTLIK, SAKKIZ JUMLA
 * ------------------------------------------------------------------------ */

describe("D-12: sifat va yorug'lik rejimi bitta jumlada", () => {
  test("⛔ `dark` + `ir_night` va `dark` + `day` TURLI matn beradi", () => {
    renderDialog({
      detail: makeDetail({ quality_verdict: "dark", light_mode: "ir_night" }),
    });
    expect(
      screen.getByText(messages.snapshots.verdict.darkIrNight),
    ).toBeInTheDocument();
    expect(screen.queryByText(messages.snapshots.verdict.darkDay)).toBeNull();
  });

  test("⛔ `dark` + `day` NOSOZLIK deb aytiladi — «bu kutilmagan holat»", () => {
    renderDialog({
      detail: makeDetail({ quality_verdict: "dark", light_mode: "day" }),
    });

    const sentence = screen.getByText(messages.snapshots.verdict.darkDay);
    expect(sentence).toBeInTheDocument();
    expect(sentence.textContent).toContain("kutilmagan");
    expect(
      screen.queryByText(messages.snapshots.verdict.darkIrNight),
    ).toBeNull();
  });

  test("`verdictKey` sakkizala juftlikni qamraydi va noma'lumda `null` beradi", () => {
    expect(verdictKey("ok", "day")).toBe("snapshots.verdict.okDay");
    expect(verdictKey("ok", "low_light")).toBe("snapshots.verdict.okLowLight");
    expect(verdictKey("ok", "ir_night")).toBe("snapshots.verdict.okIrNight");
    expect(verdictKey("dark", "ir_night")).toBe("snapshots.verdict.darkIrNight");
    expect(verdictKey("dark", "low_light")).toBe("snapshots.verdict.darkLowLight");
    expect(verdictKey("dark", "day")).toBe("snapshots.verdict.darkDay");
    expect(verdictKey("blank", "unknown")).toBe("snapshots.verdict.blank");
    expect(verdictKey("corrupt", "unknown")).toBe("snapshots.verdict.corrupt");

    // ⛔ Noma'lum yorug'lik rejimi YAGONA nosozlik jumlasiga tushmaydi.
    expect(verdictKey("dark", "unknown")).toBe("snapshots.verdict.darkLowLight");
    expect(verdictKey("hazy", "day")).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * XOM TAFSILOT KO'RSATILMAYDI (T-02-99)
 * ------------------------------------------------------------------------ */

describe("noma'lum xato kodi", () => {
  test("⛔ umumiy xabar chiqadi va XOM kod ekranga chiqmaydi", () => {
    renderDialog({
      run: makeRun({
        status: "failed",
        quality_verdict: null,
        snapshot_id: null,
        error_code: "capture_unicorn_exploded",
      }),
    });

    expect(screen.getByText(messages.errors.generic)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("capture_unicorn_exploded");
  });

  test("tanilgan kodda SABAB, TUZATISH va KIM TUZATADI — uchalasi ham", () => {
    renderDialog({
      run: makeRun({
        status: "missed",
        quality_verdict: null,
        snapshot_id: null,
        error_code: "capture_slot_missed",
      }),
    });

    expect(
      screen.getByText(messages.snapshots.errorCause.capture_slot_missed),
    ).toBeInTheDocument();
    expect(
      screen.getByText(messages.snapshots.errorFix.capture_slot_missed),
    ).toBeInTheDocument();
    // `capture_slot_missed` -> `platform` (backend reyestri bilan mos).
    expect(screen.getByText(messages.snapshots.actor.platform)).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * OMBOR QATLAMI VA HISOB BELGISI (§6.6, D-16, D-18)
 * ------------------------------------------------------------------------ */

describe("belgilar va ombor qatlami", () => {
  test("⛔ `purged` HALOL ko'rsatiladi — rasm o'rniga sabab bloki", () => {
    renderDialog({ detail: makeDetail({ storage_tier: "purged" }) });

    expect(screen.getByText(messages.snapshots.tierPurged)).toBeInTheDocument();
    expect(screen.getByText(messages.snapshots.tierPurgedWhy)).toBeInTheDocument();
    expect(document.querySelectorAll("img")).toHaveLength(0);
  });

  test("`is_billable === false` belgisi ombor qatlamidan OLDIN turadi", () => {
    renderDialog({
      detail: makeDetail({ is_billable: false, storage_tier: "compressed" }),
    });

    const billable = screen.getByText(messages.snapshots.notBillable);
    const tier = screen.getByText(messages.snapshots.tierCompressed);

    expect(
      billable.compareDocumentPosition(tier) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  test("`full` qatlamida sabab izohi qo'yilmaydi (nazorat)", () => {
    renderDialog({ detail: makeDetail({ storage_tier: "full" }) });

    expect(screen.getByText(messages.snapshots.tierFull)).toBeInTheDocument();
    expect(screen.queryByText(messages.snapshots.notBillable)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * TEXNIK TAFSILOT — FAQAT QIYMAT MAVJUD BO'LGANDA (§6.6)
 * ------------------------------------------------------------------------ */

describe("texnik tafsilot", () => {
  test("o'lchovlar mavjud bo'lsa chiziladi", () => {
    renderDialog({ detail: makeDetail() });

    expect(screen.getByText(messages.snapshots.qualityMean)).toBeInTheDocument();
    expect(screen.getByText("118.50")).toBeInTheDocument();
    // Xom token FAQAT shu blok ichida (§10.7) va yuzada inson tili.
    expect(screen.getByText("go2rtc")).toBeInTheDocument();
    expect(screen.getByText(messages.snapshots.method.stream)).toBeInTheDocument();
  });

  test("⛔ `corrupt` kadrda o'lchov YO'Q — nol ko'rsatilmaydi", () => {
    renderDialog({
      detail: makeDetail({
        quality_verdict: "corrupt",
        light_mode: "unknown",
        quality_mean: null,
        quality_stddev: null,
        quality_saturation: null,
      }),
    });

    expect(screen.queryByText(messages.snapshots.qualityMean)).toBeNull();
    expect(screen.queryByText(messages.snapshots.qualityStddev)).toBeNull();
    // Lekin chegaralar to'plami HAMON ko'rinadi — u o'lchov emas, kontekst.
    expect(
      screen.getByText(messages.snapshots.thresholdsVersion),
    ).toBeInTheDocument();
  });
});
