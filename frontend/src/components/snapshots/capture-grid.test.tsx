/**
 * IJRO JURNALI MATRITSASI — 175 HUJAYRA KLAVIATURA TUZOG'I EMAS.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (T-04-88, WCAG 2.1.2):
 *
 *   MATRITSADA BITTA TAB TO'XTASHI BOR — 175 EMAS.
 *
 *   25 kamera × 7 vaqt = 175 bosiladigan hujayra. Ularning har biri
 *   alohida tab to'xtashi bo'lsa, klaviatura foydalanuvchisi jurnaldan
 *   CHIQIB KETA OLMAYDI: keyingi boshqaruv elementiga yetish uchun 175
 *   marta `Tab` bosish kerak bo'lardi. Bu — ta'rif bo'yicha klaviatura
 *   tuzog'i.
 *
 *   Yechim — ARIA APG ning roving tabindex naqshi (§12.4): faol hujayra
 *   `tabIndex={0}`, qolgan 174 tasi `tabIndex={-1}`; ular orasida o'q
 *   tugmalari ko'chiradi.
 *
 *   ⛔ SEMANTIKA NATIVE `<table>` — matritsa roli QO'YILMAYDI (§12.4).
 *      Native `<th scope>` skrinriderda KUCHLIROQ: qator va ustun
 *      sarlavhasi avtomatik e'lon qilinadi. O'sha rol bu semantikani
 *      almashtirardi va indeks atributlarini QO'LDA yuritishni talab
 *      qilardi — 175 hujayrada bu ikkinchi haqiqat manbai bo'lardi.
 *      Roving tabindex o'sha rolsiz ham ishlaydi.
 * =============================================================================
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { CaptureGrid, buildMatrix } from "@/components/snapshots/capture-grid";
import type { CaptureRun } from "@/lib/api-types";

const CAMERA_A = "11111111-aaaa-4aaa-8aaa-111111111111";
const CAMERA_B = "22222222-bbbb-4bbb-8bbb-222222222222";
const TIMES = ["06:00:00", "06:30:00", "07:00:00"];

function makeRun(
  cameraId: string,
  channelNo: number,
  name: string,
  slot: string,
  overrides: Partial<CaptureRun> = {},
): CaptureRun {
  return {
    run_id: `${cameraId}-${slot}`,
    camera_id: cameraId,
    channel_no: channelNo,
    camera_name: name,
    slot_time: slot,
    scheduled_at: `2026-09-01T${slot.slice(0, 5)}:00Z`,
    status: "succeeded",
    attempts: 1,
    error_code: null,
    quality_verdict: "ok",
    snapshot_id: "88888888-8888-4888-8888-888888888888",
    ...overrides,
  };
}

/** Ikki kamera × uch vaqt = olti hujayra. Kanal tartibi ATAYIN teskari. */
function makeRows(): CaptureRun[] {
  const rows: CaptureRun[] = [];
  for (const slot of TIMES) {
    rows.push(makeRun(CAMERA_B, 7, "Kiyim qatori", slot));
    rows.push(makeRun(CAMERA_A, 2, "Sabzavot qatori", slot));
  }
  return rows;
}

function renderGrid(
  rows: readonly CaptureRun[],
  onOpen: (run: CaptureRun) => void = () => {},
): ReturnType<typeof render> {
  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <CaptureGrid onOpen={onOpen} rows={rows} />
    </NextIntlClientProvider>
  );
  return render(tree);
}

function cells(): HTMLElement[] {
  return screen.getAllByRole("button");
}

/* ---------------------------------------------------------------------------
 * ⛔ BITTA TAB TO'XTASHI (T-04-88)
 * ------------------------------------------------------------------------ */

describe("roving tabindex", () => {
  test("⛔ butun matritsada AYNAN BITTA tab to'xtashi bor", () => {
    renderGrid(makeRows());

    const all = cells();
    expect(all).toHaveLength(6);

    const stops = all.filter((node) => node.tabIndex === 0);
    expect(stops).toHaveLength(1);
    // Boshlang'ich faol hujayra — birinchi qatorning birinchisi (§12.4).
    expect(stops[0]).toBe(all[0]);
  });

  test("`ArrowRight` qator ichida ko'chiradi va qator OXIRIDA to'xtaydi", () => {
    renderGrid(makeRows());
    const all = cells();

    all[0].focus();
    fireEvent.keyDown(all[0], { key: "ArrowRight" });
    expect(document.activeElement).toBe(all[1]);

    fireEvent.keyDown(all[1], { key: "ArrowRight" });
    expect(document.activeElement).toBe(all[2]);

    // ⛔ Qator oxirida TO'XTAYDI — keyingi qatorga o'tmaydi.
    fireEvent.keyDown(all[2], { key: "ArrowRight" });
    expect(document.activeElement).toBe(all[2]);
  });

  test("`ArrowDown`/`ArrowUp` ustun ichida ko'chiradi va chetda to'xtaydi", () => {
    renderGrid(makeRows());
    const all = cells();

    all[0].focus();
    fireEvent.keyDown(all[0], { key: "ArrowDown" });
    // Ikkinchi qatorning birinchi hujayrasi (uch ustunli matritsa).
    expect(document.activeElement).toBe(all[3]);

    fireEvent.keyDown(all[3], { key: "ArrowDown" });
    expect(document.activeElement).toBe(all[3]);

    fireEvent.keyDown(all[3], { key: "ArrowUp" });
    expect(document.activeElement).toBe(all[0]);
  });

  test("`Home`/`End` qatorning chetiga, `Ctrl` bilan matritsaning chetiga", () => {
    renderGrid(makeRows());
    const all = cells();

    all[3].focus();
    fireEvent.keyDown(all[3], { key: "End" });
    expect(document.activeElement).toBe(all[5]);

    fireEvent.keyDown(all[5], { key: "Home" });
    expect(document.activeElement).toBe(all[3]);

    fireEvent.keyDown(all[3], { key: "Home", ctrlKey: true });
    expect(document.activeElement).toBe(all[0]);

    fireEvent.keyDown(all[0], { key: "End", ctrlKey: true });
    expect(document.activeElement).toBe(all[5]);
  });

  test("fokus ko'chganda tab to'xtashi HAM ko'chadi (bitta qoladi)", () => {
    renderGrid(makeRows());
    const all = cells();

    all[0].focus();
    fireEvent.keyDown(all[0], { key: "ArrowRight" });

    expect(cells().filter((node) => node.tabIndex === 0)).toHaveLength(1);
    expect(cells()[1].tabIndex).toBe(0);
    expect(cells()[0].tabIndex).toBe(-1);
  });
});

/* ---------------------------------------------------------------------------
 * DL-3 NI OCHISH (§12.4)
 * ------------------------------------------------------------------------ */

describe("hujayrani ochish", () => {
  test("`Enter` va `Space` kadr detalini ochadi", () => {
    const onOpen = vi.fn();
    renderGrid(makeRows(), onOpen);
    const all = cells();

    fireEvent.keyDown(all[1], { key: "Enter" });
    expect(onOpen).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(all[1], { key: " " });
    expect(onOpen).toHaveBeenCalledTimes(2);
  });

  test("sichqoncha bosishi ham o'sha yo'lni ochadi", () => {
    const onOpen = vi.fn();
    renderGrid(makeRows(), onOpen);

    fireEvent.click(cells()[4]);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ SEMANTIKA — NATIVE JADVAL (§12.4, §12.5)
 * ------------------------------------------------------------------------ */

describe("jadval semantikasi", () => {
  test("⛔ matritsa roli QO'YILMAGAN — native jadval semantikasi", () => {
    const { container } = renderGrid(makeRows());

    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelector("[role='grid']")).toBeNull();
    expect(container.querySelector("[role='gridcell']")).toBeNull();
    expect(container.querySelector("[role='row']")).toBeNull();
  });

  test("`<caption>` va ikkala yo'nalishdagi `<th scope>` mavjud", () => {
    const { container } = renderGrid(makeRows());

    const caption = container.querySelector("caption");
    expect(caption?.textContent).toBe(messages.snapshots.gridCaption);
    expect(caption?.className).toContain("sr-only");

    expect(container.querySelectorAll("th[scope='col']").length).toBeGreaterThanOrEqual(3);
    expect(container.querySelectorAll("th[scope='row']")).toHaveLength(2);
  });

  test("aylantiriladigan hudud landmark VA klaviatura bilan aylantiriladi", () => {
    renderGrid(makeRows());

    const region = screen.getByRole("region", { name: messages.snapshots.gridRegion });
    expect(region.className).toContain("overflow-x-auto");
    expect(region.tabIndex).toBe(0);
  });
});

/* ---------------------------------------------------------------------------
 * MATRITSANING QURILISHI — SOF FUNKSIYA
 * ------------------------------------------------------------------------ */

describe("buildMatrix", () => {
  test("qatorlar `channel_no` bo'yicha, ustunlar vaqt bo'yicha O'SISH tartibida", () => {
    const matrix = buildMatrix(makeRows());

    expect(matrix.columns).toEqual(TIMES);
    expect(matrix.cameras.map((camera) => camera.channelNo)).toEqual([2, 7]);
  });

  test("⛔ yetishmagan juftlik BO'SH qolmaydi — u REJAGA KIRMAGAN hujayra bo'ladi", () => {
    // Ikkinchi kameraning o'rta vaqti umuman kelmagan (kamera kun
    // o'rtasida qo'shilgan): katak `null` bo'ladi va hujayra baribir
    // CHIZILADI — bu G-7 ning matritsa darajasidagi aksi.
    const rows = makeRows().filter(
      (row) => !(row.camera_id === CAMERA_B && row.slot_time === "06:30:00"),
    );
    const matrix = buildMatrix(rows);

    const camera = matrix.cameras.find((item) => item.cameraId === CAMERA_B);
    expect(camera?.cells).toHaveLength(3);
    expect(camera?.cells[1]).toBeNull();

    renderGrid(rows);
    expect(cells()).toHaveLength(6);
  });
});
