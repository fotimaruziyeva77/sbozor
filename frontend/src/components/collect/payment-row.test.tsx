/**
 * ⛔⛔ BEKOR HODISASI ↔ BEKOR QILINGAN ASL QATOR — EKRANDA AJRALADI.
 *
 * =============================================================================
 * TOPILMA №M (TEST-REPORT 2026-08-15): bekordan keyin ro'yxatda IKKITA
 * BIR XIL KO'RINISHLI qator turardi va qaysi biri nima ekani hech qayerda
 * aytilmasdi.
 *
 * Sabab bitta qatorda edi:
 *
 *     const undone = record.reversed || record.kind === "reversal";
 *
 * Bu `||` IKKI BOSHQA HODISANI bitta bool'ga siqadi va aynan o'sha
 * lahzada MA'LUMOT YO'QOLADI:
 *
 *   * `kind === "reversal"`  — bu BEKOR QILISH HODISASI (yangi qator,
 *                              manfiy kredit, o'z vaqti bilan);
 *   * `reversed === true`    — bu BEKOR QILINGAN ASL TO'LOV (eski qator,
 *                              o'zgarmagan, faqat endi kuchsiz).
 *
 * =============================================================================
 * ⛔ BELGI KO'RINISHDA TUG'ILADI, USTUNDA EMAS (C-5).
 *
 * `payments.amount_soum` da `CHECK (> 0)` bor va storno manfiy summa
 * bilan EMAS, `kind = 'reversal'` bilan yoziladi. Manfiy belgi
 * `billing_repo._SIGNED_PAYMENT_EXPR` da SERVER yarmida, bu yerda esa
 * UI yarmida tug'iladi. Ya'ni M3 yangi qaror emas — MAVJUD qarorning
 * ikkinchi yarmini qulflaydi.
 *
 * ⚠ M3 DA'VOSI `Intl.NumberFormat` NATIJASIGA bog'lanadi, qo'lda yozilgan
 *   `"-8,000"` satrga EMAS: uz locale ajratgichi boshqa va qotirilgan
 *   satr locale o'zgargan kuni YOLG'ON QIZIL berardi.
 *
 * ⛔ SABAB-KOD QATORDA KO'RSATILMAYDI va bu unutilgan emas, O'LCHANGAN:
 *    `paymentResponseSchema` sakkiz kalitli va unda `reason_code` YO'Q.
 *    Uni chizish uchun avval `/payments` javob SHAKLI o'zgarishi kerak —
 *    bu vazifaning chegarasidan tashqarida.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { PaymentRow, rowKind } from "@/components/collect/payment-row";
import type { PaymentRecord } from "@/lib/payment-queries";

const LOCALE = "uz-Latn";

const REVERSED_LABEL = messages.collect.reversed;
const REVERSAL_ENTRY_LABEL = messages.collect.reversalEntry;
const WRITTEN_LABEL = messages.collect.written;
const REVERSE_BUTTON = messages.collect.reverse;

/**
 * ⛔ Kutilgan summa matni — `Intl` dan, qo'lda yozilgan satrdan EMAS.
 *
 * ⚠ `.replace(/\s+/gu, " ")` — testing-library ning STANDART
 *   normalizatori bilan AYNI amal. `Intl` guruh ajratgichi sifatida
 *   TOR UZILMAS BO'SHLIQ ishlatadi, DOM matni esa normalizatordan
 *   o'tadi; ikkalasini bir shaklga keltirmasa da'vo mahsulot to'g'ri
 *   bo'lganda ham qizarardi (yolg'on qizil).
 */
/*
 * ⛔⛔ MANBA `Intl` DAN O'ZGARDI (260819): o'zbek lotin pul soni endi
 *     `formatAmount` qoidasidan o'tadi — brauzer `Intl` i bu yozuvda
 *     VERGUL beradi va u pul uchun xato (vergul ba'zi konvensiyalarda
 *     KASR belgisi). Yangi qoida dizayndan: uch xonalab uzilmas
 *     bo'shliq + manfiyda `U+2212` MINUS belgisi.
 *
 * ⚠ Kutilma `formatAmount` dan MUSTAQIL quriladi — bog'lansa ikkalasi
 *   birga siljib, test jimgina yashil qolardi.
 */
const group = (value: number): string => {
  const digits = Math.round(Math.abs(value)).toString();
  let out = "";
  for (let i = 0; i < digits.length; i += 1) {
    if (i > 0 && (digits.length - i) % 3 === 0) out += " ";
    out += digits[i];
  }
  return value < 0 ? `−${out}` : out;
};

const money = (value: number) =>
  `${group(value)} ${messages.collect.amountUnit}`.replace(/\s+/gu, " ");

const PAYMENT: PaymentRecord = {
  payment_id: "33333333-3333-4333-8333-333333333333",
  stall_code: "14-C",
  service_date: "2026-09-14",
  amount_soum: 8_000,
  kind: "payment",
  method: "cash",
  created_at: "2026-09-14T06:00:00Z",
  reversed: false,
};

function renderRow(record: PaymentRecord, onRequestReverse?: () => void) {
  return render(
    <NextIntlClientProvider
      locale={LOCALE}
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <ul>
        <PaymentRow onRequestReverse={onRequestReverse} record={record} />
      </ul>
    </NextIntlClientProvider>,
  );
}

/* -------------------------------------------------------------------------- */
/* SOF QAROR — UCH HOLAT, BITTA BOOL EMAS                                     */
/* -------------------------------------------------------------------------- */

describe("`rowKind()` — uch holat", () => {
  test("bekor HODISASI", () => {
    expect(rowKind({ ...PAYMENT, kind: "reversal" })).toBe("reversal");
  });

  test("bekor qilingan ASL to'lov", () => {
    expect(rowKind({ ...PAYMENT, reversed: true })).toBe("reversed-payment");
  });

  test("oddiy to'lov (NAZORAT)", () => {
    expect(rowKind(PAYMENT)).toBe("payment");
  });
});

/* -------------------------------------------------------------------------- */
/* M1–M6 — RENDER                                                             */
/* -------------------------------------------------------------------------- */

describe("Topilma №M: ikki qator ekranda ajraladi", () => {
  test("M1: bekor qilingan ASL qator — «Bekor qilingan» + chizilgan summa, tugma YO'Q", () => {
    const { container } = renderRow(
      { ...PAYMENT, reversed: true },
      vi.fn(),
    );

    expect(screen.getByText(REVERSED_LABEL)).toBeInTheDocument();
    expect(screen.queryByText(REVERSAL_ENTRY_LABEL)).toBeNull();

    /*
     * ⛔ Chiziq YOLG'IZ signal emas — yorliq matni allaqachon bor
     *    (§12.4). Lekin u BOR bo'lishi kerak: summa endi kuchsiz va
     *    buni qatorga qarab bir zumda ko'rish mumkin bo'lsin.
     */
    const amount = screen.getByText(money(8_000));
    expect(amount.className).toContain("line-through");

    expect(
      screen.queryByRole("button", { name: REVERSE_BUTTON }),
    ).toBeNull();
    /* ⛔ «O'chirilgan tugma» yo'li ham yopiq (05-14 darsi). */
    expect(container.querySelectorAll("button[disabled]")).toHaveLength(0);
  });

  test("M2: bekor HODISASI — «Bekor qilish yozuvi», «Bekor qilingan» EMAS", () => {
    /*
     * ⛔ BU FAYLNING MARKAZIY DA'VOSI. Bugungi kodda ikkala qator ham
     *    «Bekor qilingan» ko'rsatadi — aynan shu test qizaradi.
     */
    renderRow({ ...PAYMENT, kind: "reversal" });

    expect(screen.getByText(REVERSAL_ENTRY_LABEL)).toBeInTheDocument();
    expect(screen.queryByText(REVERSED_LABEL)).toBeNull();
  });

  test("M3: bekor hodisasining summasi MANFIY belgi bilan chiziladi", () => {
    renderRow({ ...PAYMENT, kind: "reversal" });

    expect(screen.getByText(money(-8_000))).toBeInTheDocument();
    /* Nazorat: MUSBAT shakl o'sha qatorda ko'rinmaydi. */
    expect(screen.queryByText(money(8_000))).toBeNull();
  });

  test("M4: bekorni bekor qilib bo'lmaydi — tugma YO'Q", () => {
    renderRow({ ...PAYMENT, kind: "reversal" }, vi.fn());

    expect(
      screen.queryByRole("button", { name: REVERSE_BUTTON }),
    ).toBeNull();
  });

  test("M5 (NAZORAT): oddiy to'lov — «To'lov yozildi», musbat summa, tugma BOR", () => {
    /*
     * ⛔ Usiz M1–M4 «har doim bekor» ko'rsatadigan kod ustida ham yashil
     *    bo'lardi.
     */
    renderRow(PAYMENT, vi.fn());

    expect(screen.getByText(WRITTEN_LABEL)).toBeInTheDocument();
    const amount = screen.getByText(money(8_000));
    expect(amount.className).not.toContain("line-through");
    expect(
      screen.getByRole("button", { name: REVERSE_BUTTON }),
    ).toBeInTheDocument();
  });

  test("M6: har ikkala qator O'Z vaqtini `created_at` dan ko'rsatadi", () => {
    /*
     * «Qaysi biri qachon» — topilmaning ikkinchi yarmi. Ikki qator bir
     * xil ko'ringanda vaqt yagona ajratuvchi edi va u ham o'qilmasdi.
     */
    const original = renderRow({ ...PAYMENT, reversed: true });
    const originalTime = original.container.querySelector("time");
    expect(originalTime?.getAttribute("dateTime")).toBe(PAYMENT.created_at);

    const reversal = renderRow({
      ...PAYMENT,
      kind: "reversal",
      created_at: "2026-09-14T07:30:00Z",
    });
    const reversalTimes = [...reversal.container.querySelectorAll("time")];
    expect(
      reversalTimes.some(
        (node) => node.getAttribute("dateTime") === "2026-09-14T07:30:00Z",
      ),
    ).toBe(true);
  });
});
