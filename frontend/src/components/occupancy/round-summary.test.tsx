/**
 * NAMUNA HOLATI — O'LCHANMAGAN QATOR TUG'ILA OLMAYDI.
 *
 * =============================================================================
 * ⛔⛔ 1. QATORLAR TO'PLAMI LITERAL QULFLANADI — «SO'Z YO'Q» EMAS.
 *
 *   D-16 (nazoratchining ichki mosligi) bu blokning ENG TABIIY qatori
 *   edi: UI-SPEC §11.6 uni aynan shu yerga chizadi. U bugungi sxemada
 *   IFODALAB BO'LMAYDI (05-11) va serverdan MAYDON sifatida ham
 *   kelmaydi (05-12).
 *
 *   ⚠ «Ichki moslik so'zi topilmadi» degan assert YOZILMAYDI: u
 *     komponentda hech qachon bo'lmagan narsa uchun HAR DOIM yashil
 *     bo'lardi va sabotaj uni qizartira olmasdi (05-13 ning S2 darsi:
 *     da'vo o'lchanadigan FARQDAN chiqishi kerak).
 *
 *   O'rniga qatorlar TO'PLAMI aynan sanab chiqiladi — beshinchi qator
 *   qo'shilsa test QIZARADI, qanday nomlangan bo'lishidan qat'i nazar.
 *
 * ⛔ 2. `null` -> QATOR YO'Q; `0` -> QATOR BOR.
 *
 *   Ikkalasi ham sof funksiya darajasida VA DOM darajasida o'lchanadi.
 *   `?? 0` yozish eng tabiiy qisqartma va u o'lchanmagan miqdorni NOL
 *   deb e'lon qilardi — aynan D-16 uchun rad etilgan yo'l.
 *
 * ⛔ 3. «TORTILMAGAN» va «HAMMASI BAJARILDI» — IKKI XIL EKRAN.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  RoundSummary,
  roundCounters,
} from "@/components/occupancy/round-summary";
import type { AuditRound } from "@/lib/api-types";

const DAY = "2026-09-14";

function drawnRound(overrides: Partial<AuditRound> = {}): AuditRound {
  return {
    day: DAY,
    drawn: true,
    round_no: 3,
    drawn_at: "2026-09-14T01:10:00Z",
    frame_size: 420,
    sample_size: 30,
    answered: 26,
    unanswered: 4,
    dont_know: 2,
    fast_decisions: 1,
    ...overrides,
  };
}

const NOT_DRAWN: AuditRound = {
  day: DAY,
  drawn: false,
  round_no: null,
  drawn_at: null,
  frame_size: null,
  sample_size: null,
  answered: null,
  unanswered: null,
  dont_know: null,
  fast_decisions: null,
};

function renderRound(round: AuditRound) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <RoundSummary round={round} />
    </NextIntlClientProvider>,
  );
}

/* -------------------------------------------------------------------------- */
/* 1. SOF FUNKSIYA                                                            */
/* -------------------------------------------------------------------------- */

describe("roundCounters — o'lchanmagan qator TUG'ILMAYDI", () => {
  test("to'rtta o'lchangan son to'rtta qator beradi, TARTIB qat'iy", () => {
    expect(roundCounters(drawnRound())).toEqual([
      { labelKey: "occupancy.answered", value: 26 },
      { labelKey: "occupancy.unanswered", value: 4 },
      { labelKey: "occupancy.unclearCount", value: 2 },
      { labelKey: "occupancy.fastDecisions", value: 1 },
    ]);
  });

  test("⛔ `0` QATOR BERADI — u NATIJA", () => {
    const rows = roundCounters(drawnRound({ unanswered: 0, fast_decisions: 0 }));
    expect(rows).toContainEqual({ labelKey: "occupancy.unanswered", value: 0 });
    expect(rows).toContainEqual({
      labelKey: "occupancy.fastDecisions",
      value: 0,
    });
  });

  test("⛔ `null` QATOR BERMAYDI — u o'lchovning YO'QLIGI", () => {
    const rows = roundCounters(drawnRound({ dont_know: null }));
    expect(rows.map((row) => row.labelKey)).toEqual([
      "occupancy.answered",
      "occupancy.unanswered",
      "occupancy.fastDecisions",
    ]);
  });

  test("tortilmagan turda birorta qator yo'q", () => {
    expect(roundCounters(NOT_DRAWN)).toEqual([]);
  });
});

/* -------------------------------------------------------------------------- */
/* 2. QATORLAR TO'PLAMI — D-16 NING STRUKTURAVIY YO'QLIGI                     */
/* -------------------------------------------------------------------------- */

describe("blokda AYNAN to'rtta hisoblagich bor", () => {
  test("⛔⛔ `<dt>` yorliqlari TO'PLAMI literal — beshinchisi test qizartiradi", () => {
    const { container } = renderRound(drawnRound());

    const labels = [...container.querySelectorAll("dt")].map(
      (node) => node.textContent,
    );

    /*
     * ⛔ BESHINCHI QATOR — «Nazoratchining ichki mosligi» — SHU YERDA
     *    QIZARADI. U o'lchanmagan miqdor va uning har qanday shakli
     *    (son, `0`, «—», o'chirilgan qator) ko'rilgan zahoti o'lchangan
     *    deb o'qilardi (T-05-04).
     */
    expect(labels).toEqual([
      "Javob berildi",
      "Javobsiz",
      "Aniq ayta olmadi",
      "Tez qaror",
    ]);
  });

  test("javobsiz NOL bo'lganda ham qator chiziladi", () => {
    const { container } = renderRound(drawnRound({ unanswered: 0 }));

    const labels = [...container.querySelectorAll("dt")].map(
      (node) => node.textContent,
    );
    expect(labels).toContain("Javobsiz");
    expect([...container.querySelectorAll("dd")].map((n) => n.textContent)).toContain(
      "0",
    );
  });

  test("tur satri raqam, vaqt va hajmni beradi", () => {
    renderRound(drawnRound());
    expect(screen.getByText(/3-tur/u)).toBeTruthy();
    expect(screen.getByText(/30 band/u)).toBeTruthy();
  });
});

/* -------------------------------------------------------------------------- */
/* 3. TORTILMAGAN TUR                                                         */
/* -------------------------------------------------------------------------- */

describe("«tortilmagan» va «bajarildi» — IKKI XIL holat", () => {
  test("tortilmagan turda hisoblagich UMUMAN chizilmaydi", () => {
    const { container } = renderRound(NOT_DRAWN);

    expect(screen.getByText("Bugungi namuna hali tortilmagan")).toBeTruthy();
    expect(container.querySelectorAll("dt").length).toBe(0);
  });

  test("hammasiga javob berilgan tur — hisoblagichlar BOR va nol emas", () => {
    const { container } = renderRound(
      drawnRound({ answered: 30, unanswered: 0 }),
    );

    expect(screen.queryByText("Bugungi namuna hali tortilmagan")).toBeNull();
    expect(container.querySelectorAll("dt").length).toBe(4);
  });
});

/* -------------------------------------------------------------------------- */
/* 4. QURILMAGAN BOSHQARUV                                                    */
/* -------------------------------------------------------------------------- */

describe("namunani qayta tortadigan yo'l YO'Q (D-17.1)", () => {
  test("⛔ blokda birorta tugma yoki forma boshqaruvi yo'q", () => {
    for (const round of [drawnRound(), NOT_DRAWN]) {
      const { container, unmount } = renderRound(round);
      expect(container.querySelector("button")).toBeNull();
      expect(container.querySelector("input")).toBeNull();
      expect(container.querySelector("form")).toBeNull();
      unmount();
    }
  });

  test("⛔ urug'ning O'ZI ko'rsatilmaydi — javobda ham, ekranda ham", () => {
    /*
     * Urug' `audit_rounds` da USTUN sifatida ham yo'q (05-11), ya'ni
     * bu yerdagi o'lchov ikkinchi qatlam: hosila iz (tur, vaqt, hajm)
     * ko'rinadi, urug'ning o'zi esa hech qayerdan kelmaydi.
     */
    const { container } = renderRound(drawnRound());
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("urug");
    expect(text).not.toContain("seed");
  });
});
