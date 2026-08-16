/**
 * ⛔⛔ G-23(a) — SXEMA QATTIQLIGI VA §9.4 NING 2-QATLAMI.
 *
 * =============================================================================
 * ⛔ 1. IKKI QATLAM, IKKI XIL SAVOL.
 *
 *   `scripts/collect-surface.test.mjs` (G-22) — STATIK: «kodda taqiqlangan
 *   nom YOZILGANMI?». Bu fayl — DINAMIK: «kod nima QILADI?».
 *
 *   Faqat statik bo'lsa `data["char" + "ge_id"]` uni chetlab o'tardi.
 *   Faqat dinamik bo'lsa u faqat TESTDA YOZILGAN payloadni tekshirardi.
 *   Ikkalasi birga — statik chegara + xulq chegarasi.
 *
 * ⛔ 2. JUFTLANGAN INVARIANT IKKI YO'NALISHDA O'LCHANADI.
 *
 *   «Sababsiz yo'q summa» va «summasi bor sabab» — BOSHQA-BOSHQA server
 *   nosozliklari. Bitta yo'nalishni o'lchash ikkinchisini ochiq
 *   qoldirardi va o'sha teshikdan ekranga «yopiq kun, lekin to'la» degan
 *   holat chiqardi.
 *
 * ⛔ 3. MOSLIK SHARTI — XULQ BILAN, KOD-KO'RIK BILAN EMAS.
 *
 *   §9.4 ning 2-qatlami: server javobidagi kod kiritilgan koddan farq
 *   qilsa summa CHIZILMAYDI. Bu shart kesh siyosatidan MUSTAQIL, ya'ni
 *   uni `gcTime` testi bilan almashtirib bo'lmaydi — o'lchov aynan
 *   RENDER natijasida bo'lishi kerak.
 *
 * ⛔ 4. YO'L BERMAGAN AFFORDANS CHIZILMAYDI (05-14 darsi).
 *
 *   `onRequestOverride` berilmaganda tugma DOM'da BO'LMASLIGI kerak —
 *   `disabled` bo'lib turishi EMAS. O'chirilgan tugma «bor, lekin
 *   ishlamayapti» deb yolg'on gapiradi.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { PendingCard } from "@/components/collect/pending-card";
import { pendingStallSchema } from "@/lib/billing-pending-queries";
import type { PendingStall } from "@/lib/billing-pending-queries";

/**
 * Display elementining `sr-only` yorlig'i — summa CHIZILGANINING o'lchovi.
 *
 * ⚠ `{ exact: false }` bilan `collect.todayAmount` ni izlash NOTO'G'RI
 *   bo'lardi: `collect.marketClosed` matni ham «bugungi patta» so'zini
 *   o'z ichiga oladi va registrga sezgir bo'lmagan qism-satr moslashuvi
 *   uni USHLARDI — ya'ni «summa chizilmadi» da'vosi jimgina YOLG'ON
 *   yashil (mos kelmagan holatda esa yolg'on qizil) berardi.
 */
const AMOUNT_LABEL = `${messages.collect.todayAmount}:`;

/**
 * ⛔ TOZA payload — §9.2 ning AYNAN to'qqiz kaliti, ortiqchasi yo'q.
 *
 * ⚠ `stall_status: "active"` + `vendor_assigned: true` MA'NOLI standart:
 *   bu faylning qolgan hamma da'vosi «normal rasta» holatini o'lchaydi va
 *   ogohlantirish bloklari o'sha holatda CHIZILMASLIGI kerak. Boshqa
 *   standart tanlansa har test jimgina ikkinchi da'vo tashib yurardi.
 */
const CLEAN: PendingStall = {
  stall_code: "14-C",
  service_date: "2026-09-14",
  market_open: true,
  amount_soum: 15_000,
  amount_unavailable_reason: null,
  outstanding_soum: 0,
  total_due_soum: 15_000,
  stall_status: "active",
  vendor_assigned: true,
};

/**
 * `collect.stallStatusNotice` ning ICU argumenti TO'LDIRILGAN shakli.
 *
 * ⛔ Kutilgan matn KATALOGDAN hosila qilinadi, testda QAYTA YOZILMAYDI:
 *    qo'lda yozilgan nusxa copy tahrirlanganda jimgina eskirardi va
 *    da'vo «bu matn ekranda» dan «bu matn TESTDA» ga aylanardi.
 */
const statusNotice = (status: string) =>
  messages.collect.stallStatusNotice.replace("{status}", status);

/** Sotuvchisiz rastaning sabab+yechim matni — 409 bilan AYNI reyestrdan. */
const NOT_ASSIGNED_CAUSE = messages.collect.errorCause.stall_not_assigned;
const NOT_ASSIGNED_FIX = messages.collect.errorFix.stall_not_assigned;

function renderCard(node: ReactNode) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      {node}
    </NextIntlClientProvider>,
  );
}

/* -------------------------------------------------------------------------- */
/* G-23(a) — SXEMA                                                            */
/* -------------------------------------------------------------------------- */

describe("G-23(a) (06-UI-SPEC): proyeksiya sxemasi", () => {
  test("⛔ toza payload PARSE bo'ladi (nazorat)", () => {
    /*
     * Usiz quyidagi hamma «throw» da'vosi BUZUQ SXEMA ustida ham rost
     * bo'lardi: har narsani rad etadigan sxema abadiy yashil qolardi.
     */
    expect(() => pendingStallSchema.parse({ ...CLEAN })).not.toThrow();
  });

  test("⛔ hisob identifikatori qo'shilsa PARSE YIQILADI (D-17)", () => {
    /*
     * ⛔ Server bir kun bu maydonni qo'shsa, klient DARHOL qizaradi va
     *    maydon jimgina ekranga oqib o'tmaydi. Brauzerga yetgan maydon
     *    O'QILADI (DevTools, `JSON.stringify`) — CSS bilan yashirish
     *    yoki shartli render YETARLI EMAS.
     */
    expect(() =>
      pendingStallSchema.parse({ ...CLEAN, charge_id: "x" }),
    ).toThrow();
  });

  test("⛔ `z.strictObject`: ortiqcha kalit PARSE ni yiqitadi", () => {
    expect(() =>
      pendingStallSchema.parse({ ...CLEAN, tariff_id: "x" }),
    ).toThrow();
    expect(() =>
      pendingStallSchema.parse({ ...CLEAN, vendor_name: "Anvar" }),
    ).toThrow();
  });

  test("⛔ JUFTLANGAN INVARIANT — 1-yo'nalish: SABABSIZ YO'Q SUMMA", () => {
    expect(() =>
      pendingStallSchema.parse({
        ...CLEAN,
        amount_soum: null,
        amount_unavailable_reason: null,
      }),
    ).toThrow();
  });

  test("⛔ JUFTLANGAN INVARIANT — 2-yo'nalish: SUMMASI BOR SABAB", () => {
    /*
     * ⛔ IKKINCHI YO'NALISH ALOHIDA TEST: birinchisi bilan birga
     *    yozilsa, bittasi yiqilib ikkinchisi umuman o'lchanmay qolardi.
     */
    expect(() =>
      pendingStallSchema.parse({
        ...CLEAN,
        amount_soum: 1_000,
        amount_unavailable_reason: "tariff_missing",
      }),
    ).toThrow();
  });

  test("nomlangan sabab bilan yo'q summa PARSE bo'ladi", () => {
    expect(() =>
      pendingStallSchema.parse({
        ...CLEAN,
        amount_soum: null,
        amount_unavailable_reason: "market_closed",
      }),
    ).not.toThrow();
  });

  /* --- F7: yangi maydonlar MAJBURIY, qattiqlik esa SAQLANADI ------------ */

  test("⛔ ESKI YETTI KALITLI payload RAD ETILADI (yangi maydonlar majburiy)", () => {
    /*
     * ⛔ Da'vo «yangi maydon ixtiyoriy emas» degani. `.optional()` bilan
     *    e'lon qilingan maydon eski serverda `undefined` bo'lib kelardi
     *    va karta ogohlantirishni JIMGINA chizmasdi — ya'ni topilma
     *    qaytib kelardi, hech qaysi darvoza qizarmasdan.
     */
    const { stall_status, vendor_assigned, ...seven } = CLEAN;
    void stall_status;
    void vendor_assigned;

    expect(Object.keys(seven)).toHaveLength(7);
    expect(() => pendingStallSchema.parse(seven)).toThrow();
  });

  test("⛔ O'NINCHI KALIT ham PARSE ni yiqitadi — qattiqlik saqlandi", () => {
    /*
     * To'plam YETTIDAN TO'QQIZGA o'sdi, lekin `z.strictObject` ning
     * o'zi bo'shashmadi: darvoza kengaydi, OCHILMADI.
     */
    expect(() =>
      pendingStallSchema.parse({ ...CLEAN, occupied_slots: 2 }),
    ).toThrow();
  });

  test("⛔ `stall_status` YOPIQ to'plam — erkin matn RAD ETILADI", () => {
    expect(() =>
      pendingStallSchema.parse({ ...CLEAN, stall_status: "ta'mirda" }),
    ).toThrow();
  });
});

/* -------------------------------------------------------------------------- */
/* §9.4 — MOSLIK SHARTI (2-QATLAM)                                            */
/* -------------------------------------------------------------------------- */

describe("§9.4 (2-qatlam): eski summa yangi rasta ostida ko'rinmaydi", () => {
  test("kod MOS kelganda summa chiziladi", () => {
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={CLEAN}
      />,
    );

    expect(
      screen.getByText(AMOUNT_LABEL),
    ).toBeInTheDocument();
  });

  test("⛔ kod MOS KELMAGANDA summa CHIZILMAYDI — `Skeleton` ko'rinadi", () => {
    /*
     * Kassir `15-A` ni terdi, keshdagi javob esa hamon `14-C` niki.
     * §9.4 ning 2-qatlami aynan shu lahzani to'sadi.
     */
    const { container } = renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="15-A"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={CLEAN}
      />,
    );

    expect(
      screen.queryByText(AMOUNT_LABEL),
    ).toBeNull();
    expect(container.querySelectorAll('[aria-busy="true"]')).toHaveLength(1);
  });
});

/* -------------------------------------------------------------------------- */
/* 05-14 DARSI — YO'L BERMAGAN AFFORDANS CHIZILMAYDI                          */
/* -------------------------------------------------------------------------- */

describe("`onRequestOverride` ixtiyoriy propi", () => {
  test("⛔ prop BERILMAGANDA tugma DOM'da 0 va `disabled` tugma ham YO'Q", () => {
    const { container } = renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={CLEAN}
      />,
    );

    expect(
      screen.queryByRole("button", { name: messages.collect.override }),
    ).toBeNull();
    /* ⛔ «o'chirilgan tugma» yo'li ham yopiq — u yolg'on affordans. */
    expect(container.querySelectorAll("button[disabled]")).toHaveLength(0);
  });

  test("prop BERILGANDA tugma ko'rinadi va bosiladi", () => {
    const onRequestOverride = vi.fn();
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRequestOverride={onRequestOverride}
        onRetry={vi.fn()}
        pending={CLEAN}
      />,
    );

    expect(
      screen.getByRole("button", { name: messages.collect.override }),
    ).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* §9.3 / §9.4 — KANALLAR VA NOMLANGAN SABAB                                  */
/* -------------------------------------------------------------------------- */

describe("§9.3 kanallari va §9.4 nomlangan sabablari", () => {
  test("⛔ 4-kanal: TO'LIQ JUMLA chiziladi, qisqartma emas", () => {
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={CLEAN}
      />,
    );

    expect(screen.getByText(messages.collect.pendingNotice)).toBeInTheDocument();
    expect(screen.getByText(messages.collect.pendingTitle)).toBeInTheDocument();
  });

  test("⛔ `market_closed`: nomlangan sabab, «taxminiy summa» YO'Q", () => {
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={{
          ...CLEAN,
          amount_soum: null,
          amount_unavailable_reason: "market_closed",
          outstanding_soum: 20_000,
          total_due_soum: 20_000,
        }}
      />,
    );

    expect(screen.getByText(messages.collect.marketClosed)).toBeInTheDocument();
    expect(
      screen.queryByText(AMOUNT_LABEL),
    ).toBeNull();
  });

  test("⛔ so'rov xatosida summa UMUMAN chizilmaydi", () => {
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={CLEAN}
      />,
    );

    expect(
      screen.queryByText(AMOUNT_LABEL),
    ).toBeNull();
    expect(
      screen.getByRole("button", { name: messages.common.retry }),
    ).toBeInTheDocument();
  });

  test("⛔ ortiqcha to'langan rasta AVANS bo'lib ko'rinadi (A4)", () => {
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={vi.fn()}
        onRetry={vi.fn()}
        pending={{ ...CLEAN, outstanding_soum: -5_000, total_due_soum: 10_000 }}
      />,
    );

    expect(screen.getByText(messages.collect.advance)).toBeInTheDocument();
  });

  test("`[Qarzni ham olish]` SERVER bergan yig'indi bilan chaqiriladi", () => {
    const onCollectDebt = vi.fn();
    renderCard(
      <PendingCard
        chosenAmount={null}
        enteredCode="14-C"
        isError={false}
        isLoading={false}
        onCollectDebt={onCollectDebt}
        onRetry={vi.fn()}
        pending={{ ...CLEAN, outstanding_soum: 45_000, total_due_soum: 60_000 }}
      />,
    );

    screen
      .getByRole("button", { name: new RegExp(messages.collect.withDebt) })
      .click();

    /* ⛔ Klient `15000 + 45000` ni HISOBLAMAYDI — qiymat payloaddan. */
    expect(onCollectDebt).toHaveBeenCalledWith(60_000);
  });
});

/* -------------------------------------------------------------------------- */
/* TOPILMA №L — RASTA KONTEKSTI SUBMIT'DAN OLDIN KO'RINADI                    */
/* -------------------------------------------------------------------------- */

/**
 * ⛔⛔ IKKI MUSTAQIL BLOK, IKKI BOSHQA SAVOL.
 *
 *   `stall_status !== "active"`  -> «reyestrda nima deb belgilangan?»
 *   `vendor_assigned === false`  -> «to'lov KIMGA yoziladi?»
 *
 * Ular bir-biridan hosila EMAS: ta'mirdagi rastada sotuvchi bo'lishi ham,
 * faol rastada sotuvchi bo'lmasligi ham mumkin. Shuning uchun F5 ikkalasi
 * BIR VAQTDA chizilishini talab qiladi.
 *
 * ⛔⛔ ULARNING BIRORTASI TO'LOVNI BLOKLAMAYDI. Bu yerdagi da'volar
 *     faqat MATN borligini o'lchaydi; «tugma o'chdimi?» savolining javobi
 *     `pending-card.tsx` ning izohida va `payment-bar` oqimida — u
 *     TEGILMAYDI.
 */
function renderPending(pending: PendingStall) {
  return renderCard(
    <PendingCard
      chosenAmount={null}
      enteredCode={pending.stall_code}
      isError={false}
      isLoading={false}
      onCollectDebt={vi.fn()}
      onRetry={vi.fn()}
      pending={pending}
    />,
  );
}

describe("Topilma №L: rasta holati va sotuvchi konteksti", () => {
  test("F1: `maintenance` rastada holat ogohlantirishi «Ta'mirda» bilan chiziladi", () => {
    renderPending({ ...CLEAN, stall_status: "maintenance" });

    expect(
      screen.getByText(statusNotice(messages.stalls.status.maintenance)),
    ).toBeInTheDocument();
  });

  test("F2: `closed` rastada o'sha blok «Yopiq» yorlig'i bilan chiziladi", () => {
    /*
     * ⛔ IKKINCHI HOLAT ALOHIDA O'LCHANADI: yorliq DINAMIK kalit bilan
     *    emas, reyestr konstantasi bilan tanlanadi va bitta holatni
     *    o'lchash o'sha reyestrning qolgan qatorini sinamasdi.
     */
    renderPending({ ...CLEAN, stall_status: "closed" });

    expect(
      screen.getByText(statusNotice(messages.stalls.status.closed)),
    ).toBeInTheDocument();
  });

  test("F3: `vendor_assigned: false` da sabab+yechim submit'dan OLDIN ko'rinadi", () => {
    /*
     * ⛔ MATN 409 BILAN AYNAN BIR XIL: manba `billingErrorView(
     *    "stall_not_assigned")`, ya'ni yangi copy kaliti YOZILMAGAN.
     *    Ikki xil so'z kassirga ikki xil nosozlik bo'lib ko'rinardi.
     */
    renderPending({ ...CLEAN, vendor_assigned: false });

    expect(screen.getByText(NOT_ASSIGNED_CAUSE)).toBeInTheDocument();
    expect(screen.getByText(NOT_ASSIGNED_FIX)).toBeInTheDocument();
  });

  test("F4 (SALBIY NAZORAT): normal rastada IKKALA blok ham YO'Q", () => {
    /*
     * ⛔ ENG MUHIM DA'VO. Usiz «har doim chizadigan» blok ham F1–F3 ni
     *    yashil qilardi va ogohlantirish SHOVQINGA aylanardi — kassir
     *    kuniga 300–1000 marta ko'rgan ogohlantirishni o'qimay qo'yadi.
     */
    renderPending(CLEAN);

    expect(
      screen.queryByText(statusNotice(messages.stalls.status.maintenance)),
    ).toBeNull();
    expect(
      screen.queryByText(statusNotice(messages.stalls.status.closed)),
    ).toBeNull();
    expect(
      screen.queryByText(statusNotice(messages.stalls.status.active)),
    ).toBeNull();
    expect(screen.queryByText(NOT_ASSIGNED_CAUSE)).toBeNull();
    expect(screen.queryByText(NOT_ASSIGNED_FIX)).toBeNull();
  });

  test("F5: ikkala holat birga kelganda IKKALA blok ham chiziladi", () => {
    renderPending({
      ...CLEAN,
      stall_status: "maintenance",
      vendor_assigned: false,
    });

    expect(
      screen.getByText(statusNotice(messages.stalls.status.maintenance)),
    ).toBeInTheDocument();
    expect(screen.getByText(NOT_ASSIGNED_CAUSE)).toBeInTheDocument();
  });

  test("F6: ⛔ ogohlantirish SUMMANI O'CHIRMAYDI", () => {
    /*
     * ⛔ Reyestr holati hisob qoidasiga KIRMAYDI: ta'mirdagi rasta savdo
     *    qilsa patta to'laydi (`_market_projection()` qarori). Summani
     *    o'chirish `is_billable` ni ORQA ESHIKDAN qaytarib keltirardi.
     */
    renderPending({ ...CLEAN, stall_status: "maintenance" });

    expect(screen.getByText(AMOUNT_LABEL)).toBeInTheDocument();
  });
});
