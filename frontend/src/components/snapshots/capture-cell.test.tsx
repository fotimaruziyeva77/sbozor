/**
 * ⛔ G-7 — YO'Q KADR BO'SH KATAK EMAS, HODISA.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI — SC#2 NING MEXANIK SHAKLI:
 *
 *   «O'tkazib yuborilgan slot jurnalda OCHIQ KO'RINADI» (ROADMAP Phase 4
 *   SC#2). «Jurnalga yozilgan» va «jurnalda ochiq ko'rinadi» — BOSHQA
 *   talab: birinchisini backend bajardi (`04-07` ning yo'qlik yozuvi),
 *   ikkinchisi esa AYNAN shu hujayrada yashaydi.
 *
 *   Uni buzishning aniq bir usuli bor va u kod-ko'rikda begunoh
 *   ko'rinadi: BO'SH KATAK. Bo'shliq «bu yerda ko'radigan narsa yo'q»
 *   deydi — ya'ni yo'qlikni ko'rsatish o'rniga uni YASHIRADI.
 *
 *   Shuning uchun `missed` hujayra UCHTA MUSTAQIL KANALDA o'lchanadi
 *   (§9.4) va ular alohida-alohida tekshiriladi:
 *
 *     1. IKONKA (shakl)   — hujayra bo'sh emas;
 *     2. SO'Z (`aria-label`) — skrinriderda ikonka yo'q, matn YAGONA kanal;
 *     3. PUNKTIR CHEGARA  — rangsiz, ikonkasiz uchinchi kanal: «bu yerda
 *        nimadir bo'lishi kerak edi».
 *
 *   Va to'rtinchi da'vo — 44×44 nishon: `missed` hujayra `succeeded`
 *   hujayra bilan AYNI JOYNI egallaydi. Kichraytirilgan yoki siqilgan
 *   yo'qlik ham «muhim emas» degan xabar berardi (va WCAG 2.5.8 ni
 *   buzardi).
 * =============================================================================
 *
 * Beshinchi va oltinchi da'vo — IKONKALARNING AJRALISHI:
 *   * `succeeded+dark` `succeeded+ok` dan ikonkasi bilan farq qiladi
 *     (ikkalasi ham «olindi», lekin biri hisobga kirmaydi);
 *   * ⛔ `missed` va `failed` TURLI ikonka: «bizning tizimimiz ishlamadi»
 *     va «NVR javob bermadi» operatsion jihatdan butunlay boshqa va bir
 *     xil ko'rinishi dala diagnostikasini o'ldirardi.
 *
 * Yettinchi — HUJAYRADA MATN YO'Q [O'LCHANDI: M-4]: `Buzuq` -> `Повреждён`
 * nisbati 1,80× va u 44px hujayraga SIG'MAYDI. So'z legendada va
 * `aria-label` da yashaydi.
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { CaptureCell, captureCellState } from "@/components/snapshots/capture-cell";
import type { CaptureRun } from "@/lib/api-types";

const CAMERA = "Kiyim qatori";
const SLOT = "06:30:00";

function makeRun(overrides: Partial<CaptureRun> = {}): CaptureRun {
  return {
    run_id: "66666666-6666-4666-8666-666666666666",
    camera_id: "77777777-7777-4777-8777-777777777777",
    channel_no: 3,
    camera_name: CAMERA,
    slot_time: SLOT,
    scheduled_at: "2026-09-01T01:30:00Z",
    status: "succeeded",
    attempts: 1,
    error_code: null,
    quality_verdict: "ok",
    snapshot_id: "88888888-8888-4888-8888-888888888888",
    ...overrides,
  };
}

function renderCell(run: CaptureRun | null): ReturnType<typeof render> {
  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <CaptureCell
        cameraName={CAMERA}
        onOpen={() => {}}
        run={run}
        slotTime={SLOT}
      />
    </NextIntlClientProvider>
  );
  return render(tree);
}

/** Ikonkaning O'ZI — sinf nomiga emas, chizmaga tayanadi. */
function iconShape(container: HTMLElement): string {
  const svg = container.querySelector("svg");
  expect(svg).not.toBeNull();
  return svg?.innerHTML ?? "";
}

/* ---------------------------------------------------------------------------
 * ⛔ G-7 — `missed` HUJAYRA BO'SH EMAS (to'rt da'vo)
 * ------------------------------------------------------------------------ */

describe("G-7: `missed` hujayra hech qachon bo'sh emas", () => {
  test("⛔ 1-kanal — IKONKA render bo'ladi", () => {
    const { container } = renderCell(makeRun({ status: "missed", quality_verdict: null, snapshot_id: null }));

    expect(container.querySelectorAll("svg")).toHaveLength(1);
  });

  test("⛔ 2-kanal — `aria-label` `cell.missed` SO'ZINI o'z ichiga oladi", () => {
    renderCell(makeRun({ status: "missed", quality_verdict: null, snapshot_id: null }));

    const cell = screen.getByRole("button");
    const label = cell.getAttribute("aria-label") ?? "";

    expect(label).toContain(messages.snapshots.cell.missed);
    // To'liq jumla: vaqt · kamera · holat (§6.4). Ikkovisiz «Olinmadi»
    // yolg'iz eshitilardi va 175 hujayrada u ma'nosiz bo'lardi.
    expect(label).toContain("06:30");
    expect(label).toContain(CAMERA);
    // Sichqoncha foydalanuvchisi uchun AYNI matn.
    expect(cell).toHaveAttribute("title", label);
  });

  test("⛔ 3-kanal — PUNKTIR chegara (rangsiz, ikonkasiz kanal)", () => {
    renderCell(makeRun({ status: "missed", quality_verdict: null, snapshot_id: null }));

    expect(screen.getByRole("button").className).toContain("border-dashed");
  });

  test("⛔ 4-da'vo — 44×44 nishon: yo'qlik BAJARILGAN kadr bilan bir xil joy egallaydi", () => {
    renderCell(makeRun({ status: "missed", quality_verdict: null, snapshot_id: null }));

    const className = screen.getByRole("button").className;
    expect(className).toContain("min-h-11");
    expect(className).toContain("min-w-11");
  });
});

/* ---------------------------------------------------------------------------
 * IKONKALARNING AJRALISHI (§6.4, §9.4)
 * ------------------------------------------------------------------------ */

describe("ikonkalar bir-biridan ajraladi", () => {
  test("`succeeded+dark` `succeeded+ok` dan IKONKASI bilan farq qiladi", () => {
    const ok = render(
      <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
        <CaptureCell cameraName={CAMERA} onOpen={() => {}} run={makeRun()} slotTime={SLOT} />
      </NextIntlClientProvider>,
    );
    const okShape = iconShape(ok.container);
    ok.unmount();

    const dark = renderCell(makeRun({ quality_verdict: "dark" }));
    expect(iconShape(dark.container)).not.toBe(okShape);
  });

  test("⛔ `missed` va `failed` TURLI ikonka — «biz» va «NVR» bir xil ko'rinmaydi", () => {
    const failed = renderCell(
      makeRun({ status: "failed", quality_verdict: null, snapshot_id: null, error_code: "capture_timeout" }),
    );
    const failedShape = iconShape(failed.container);
    failed.unmount();

    const missed = renderCell(
      makeRun({ status: "missed", quality_verdict: null, snapshot_id: null, error_code: "capture_slot_missed" }),
    );
    expect(iconShape(missed.container)).not.toBe(failedShape);
  });
});

/* ---------------------------------------------------------------------------
 * HUJAYRADA MATN YO'Q [O'LCHANDI: M-4]
 * ------------------------------------------------------------------------ */

describe("hujayrada matn yo'q", () => {
  test("⛔ hujayraning matn mazmuni BO'SH — so'z legendada va `aria-label` da", () => {
    renderCell(makeRun({ status: "succeeded", quality_verdict: "corrupt" }));

    const cell = screen.getByRole("button");
    expect(cell.textContent).toBe("");
    // Lekin so'z YO'QOLMAYDI — u yordamchi texnologiya uchun bor.
    expect(cell.getAttribute("aria-label")).toContain(messages.snapshots.cell.corrupt);
  });
});

/* ---------------------------------------------------------------------------
 * HOLAT XARITASI — SOF FUNKSIYA
 * ------------------------------------------------------------------------ */

describe("captureCellState", () => {
  test("to'qqizala holat `status` + `quality_verdict` juftligidan chiziladi", () => {
    expect(captureCellState({ status: "succeeded", quality_verdict: "ok" })).toBe("ok");
    expect(captureCellState({ status: "succeeded", quality_verdict: "dark" })).toBe("dark");
    expect(captureCellState({ status: "succeeded", quality_verdict: "blank" })).toBe("blank");
    expect(captureCellState({ status: "succeeded", quality_verdict: "corrupt" })).toBe("corrupt");
    expect(captureCellState({ status: "failed", quality_verdict: null })).toBe("failed");
    expect(captureCellState({ status: "missed", quality_verdict: null })).toBe("missed");
    expect(captureCellState({ status: "pending", quality_verdict: null })).toBe("pending");
    expect(captureCellState({ status: "running", quality_verdict: null })).toBe("running");
    expect(captureCellState({ status: "skipped", quality_verdict: null })).toBe("skipped");
  });

  test("noma'lum qiymat BITTA hujayrani egallaydi, kunni yiqitmaydi", () => {
    // 04-10 qarori: enum sxemada `z.string()`. Backend o'n ikkinchi
    // holatni qo'shsa, u YO'QLIK deb ko'rsatilmasligi kerak — yolg'on
    // ogohlantirish jimgina o'tkazib yuborishdan yomonroq.
    expect(captureCellState({ status: "deferred", quality_verdict: null })).toBe("pending");
    expect(captureCellState({ status: "succeeded", quality_verdict: "hazy" })).toBe("ok");
  });

  test("qator umuman yo'q bo'lsa hujayra REJAGA KIRMAGAN bo'ladi (bo'sh emas)", () => {
    renderCell(null);

    const cell = screen.getByRole("button");
    expect(cell.getAttribute("aria-label")).toContain(messages.snapshots.cell.skipped);
    expect(cell.className).toContain("border-dashed");
  });
});
