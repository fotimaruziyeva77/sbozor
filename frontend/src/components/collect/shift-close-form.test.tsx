/**
 * ⛔⛔ G-7 NING FRONTEND YARMI (d) VA G-23 NING (b)/(c) BANDLARI.
 *
 * =============================================================================
 * ⛔ 1. IKKI QATLAM, IKKI XIL SAVOL.
 *
 *   `scripts/collect-surface.test.mjs` — STATIK: «kodda taqiqlangan nom
 *   YOZILGANMI?». Bu fayl — DINAMIK: «kod nima QILADI va ekranda nima
 *   KO'RINADI?». Faqat statik bo'lsa `data["system" + "_soum"]` uni
 *   chetlab o'tardi; faqat dinamik bo'lsa u faqat testda YOZILGAN
 *   payloadni tekshirardi.
 *
 * ⛔ 2. TO'PLAM TENGLIGI, INKOR TASDIQ EMAS (D-31).
 *
 *   05-14 ning S7 sabotaji: «bu nom yo'q» shaklidagi tasdiq FAQAT
 *   aynan o'sha nomni ushlaydi va maydon qayta nomlansa JIMGINA o'tib
 *   ketardi. Shuning uchun bu fayldagi hech bir da'vo taqiqlangan
 *   NOMNI aytmaydi — ular ekrandagi SONLAR to'plamini va natija bloki
 *   BOLALARINING to'plamini o'lchaydi.
 *
 *   ⚠ Inkor matcher'ning nomi bu faylda LITERAL sifatida yozilmaydi:
 *     taqiqni o'lchaydigan mezon xom matn skani va izohning O'ZI uni
 *     qizartirardi (kodbaza konvensiyasi — `badge.tsx` da ham xuddi
 *     shu sabab).
 *
 * ⛔ 3. 3-DA'VO NOM BILAN BOG'LANMAGAN — VA BU UNING BUTUN QIYMATI.
 *
 *   U DOM matnidan har qanday raqamli qiymatni ajratib oladi va
 *   ularning to'plami AYNAN BITTA (kiritilgan naqd) bo'lishini talab
 *   qiladi. Ya'ni ikkinchi son qanday nom bilan, qanday uslub bilan va
 *   qaysi elementda paydo bo'lishidan QAT'I NAZAR test qizaradi.
 *
 * ⛔ 4. 4-DA'VO NOMLANMAGAN TO'RTINCHI ELEMENTNI HAM USHLAYDI.
 *
 *   `data-shift-result` to'plami tengligi nomlangan qo'shimchani
 *   ushlaydi; bolalar SANOG'I esa nomlanmaganini. Ikkalasi birga —
 *   05-15 ning S-D darsi: sabotaj sistemaga yetib borsa ham, test
 *   tanlagan YUZA ikkala shoxda bir xil javob berishi mumkin edi.
 *
 * ⚠ TAQIQLANGAN NOMLAR BU FAYLDA ATAYIN YOZILGAN (1-da'vo) va bu
 *   ziddiyat EMAS: `collect-surface.test.mjs` mahsulot fayllarini
 *   skanerlaydi, `*.test.tsx` esa `TEST_FILE` regeksi bilan qamrovdan
 *   CHIQARILADI. Sxema qattiqligini o'lchash uchun aynan o'sha nomlar
 *   bilan urinib ko'rish SHART.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiRequest: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: apiClientMock.apiFetch,
    apiRequest: apiClientMock.apiRequest,
  };
});

import messages from "../../../messages/uz-Latn.json";
import { ShiftCloseForm } from "@/components/collect/shift-close-form";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { shiftCloseResponseSchema } from "@/lib/shift-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SHIFT_ID = "22222222-2222-4222-8222-222222222222";

/**
 * Kiritiladigan naqd.
 *
 * ⚠ ATAYIN «yumaloq bo'lmagan» qiymat: sabotaj sinovida qo'shiladigan
 *   ikkinchi son (masalan 1 200 000) undan FARQ qilishi kerak, aks holda
 *   sonlar TO'PLAMI o'smasdi va 3-da'vo yolg'on-yashil qolardi.
 */
const DECLARED = 980_000;

/** ⛔ TOZA javob — §10.3 ning AYNAN to'rt kaliti, ortiqchasi yo'q. */
const CLEAN = {
  id: SHIFT_ID,
  status: "closed",
  declared_soum: DECLARED,
  closed_at: "2026-09-14T13:00:00Z",
};

let client: QueryClient;

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000000",
      fullName: "Test Cashier",
      roles: ["cashier"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderTree(node: ReactNode) {
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <NextIntlClientProvider
          locale="uz-Latn"
          messages={messages}
          timeZone="Asia/Tashkent"
        >
          {node}
        </NextIntlClientProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

function amountInput(): HTMLElement {
  return screen.getByLabelText(messages.collect.declaredLabel);
}

/** Formadagi yuborish tugmasi — dialogdagi tasdiqdan BOSHQA yorliq. */
function submitButton(): HTMLElement {
  return screen.getByRole("button", { name: messages.common.close });
}

function closeCalls(): { declared_soum: number }[] {
  return (
    apiClientMock.apiFetch.mock.calls as [
      string,
      { method?: string; body?: { declared_soum: number } },
    ][]
  )
    .filter(([path, options]) => path.endsWith("/close") && options.method === "POST")
    .map(([, options]) => options.body as { declared_soum: number });
}

/**
 * DOM MATNIDAGI HAR QANDAY RAQAMLI QIYMAT — nom bilan BOG'LANMAGAN skan.
 *
 * Ajratmalar (probel, uzilmas probel, nuqta, vergul) olib tashlanadi:
 * da'vo FORMATLASH haqida emas, EKRANDA NECHTA HAR XIL SON borligi
 * haqida. Shuning uchun natija — raqamlar satrlarining TO'PLAMI.
 */
function distinctNumbers(root: HTMLElement): Set<string> {
  const runs = (root.textContent ?? "").match(/\d[\d\s  .,]*\d|\d/g);
  return new Set((runs ?? []).map((run) => run.replace(/\D/g, "")));
}

/** Yopilgan holatga olib boradigan to'liq yo'l — forma -> DL-4 -> javob. */
async function driveToClosed(): Promise<void> {
  apiClientMock.apiFetch.mockResolvedValue({ ...CLEAN });

  renderTree(<ShiftCloseForm onReopen={vi.fn()} shiftId={SHIFT_ID} />);

  fireEvent.change(amountInput(), { target: { value: String(DECLARED) } });
  fireEvent.click(submitButton());

  const confirm = await screen.findByRole("button", {
    name: messages.collect.shiftClose,
  });
  fireEvent.click(confirm);

  await waitFor(() => {
    expect(
      document.body.querySelector("[data-shift-result-region]"),
    ).not.toBeNull();
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* 1 — G-23(b): SXEMA QATTIQLIGI                                              */
/* -------------------------------------------------------------------------- */

describe("G-23(b) (06-UI-SPEC §10.3): yopish javobining sxemasi", () => {
  test("⛔ toza javob PARSE bo'ladi (nazorat)", () => {
    /*
     * Usiz quyidagi uchala «throw» da'vosi HAR NARSANI rad etadigan
     * buzuq sxema ustida ham rost bo'lardi — darvoza abadiy yashil.
     */
    expect(() => shiftCloseResponseSchema.parse({ ...CLEAN })).not.toThrow();
  });

  test("⛔ tizim yig'indisi qo'shilsa PARSE YIQILADI — 1-nom", () => {
    expect(() =>
      shiftCloseResponseSchema.parse({ ...CLEAN, system_total_soum: 1 }),
    ).toThrow();
  });

  test("⛔ farq maydoni qo'shilsa PARSE YIQILADI — 2-nom", () => {
    /*
     * ⛔ ALOHIDA TEST, birinchisi bilan birga EMAS: server uchala nomni
     *    ham qo'shishi mumkin va bittasi yiqilsa qolgani UMUMAN
     *    o'lchanmay qolardi.
     */
    expect(() =>
      shiftCloseResponseSchema.parse({ ...CLEAN, variance_soum: 1 }),
    ).toThrow();
  });

  test("⛔ tizim summasi qo'shilsa PARSE YIQILADI — 3-nom", () => {
    expect(() =>
      shiftCloseResponseSchema.parse({ ...CLEAN, system_soum: 1 }),
    ).toThrow();
  });
});

/* -------------------------------------------------------------------------- */
/* 2 — G-23(c): KALITLAR TO'PLAMI AYNAN TO'RTTA                               */
/* -------------------------------------------------------------------------- */

describe("G-23(c): sxema maydonlari to'plami", () => {
  test("⛔ AYNAN `{id, status, declared_soum, closed_at}` — to'plam TENGLIGI", () => {
    /*
     * ⛔ `toEqual` bilan TO'PLAM tengligi (D-31): maydon QO'SHILSA ham,
     *    TUSHIB QOLSA ham darvoza qizaradi. Inkor tasdiq esa faqat o'zi
     *    bilgan nomni ushlardi.
     */
    expect(new Set(Object.keys(shiftCloseResponseSchema.shape))).toEqual(
      new Set(["id", "status", "declared_soum", "closed_at"]),
    );
  });

  test("⛔ sxema QAT'IY: nomi ahamiyatsiz, ortiqcha kalitning O'ZI yiqitadi", () => {
    /*
     * ⛔ NOM BILAN BOG'LANMAGAN QAT'IYLIK DA'VOSI, va u yuqoridagi
     *    to'plam tengligidan MUSTAQIL narsani o'lchaydi.
     *
     *    To'plam tengligi «beshinchi maydon E'LON QILINGANMI?» degan
     *    savolga javob beradi; qat'iylik esa «e'lon qilinmagan maydon
     *    JIMGINA o'tib ketadimi?» degan savolga. `z.strictObject` ->
     *    `z.object` almashuvi birinchisini UMUMAN o'zgartirmaydi (shakl
     *    bir xil qoladi), ikkinchisini esa darhol buzadi — shuning
     *    uchun ikkala da'vo ham kerak.
     *
     * ⚠ Kalit nomi ISHLASH PAYTIDA quriladi: qotirilgan nom bo'lsa
     *   da'vo yana «aynan o'sha nom» sinfiga qaytardi (D-31).
     */
    const unexpectedKey = `unexpected_${Date.now().toString(36)}`;

    expect(() =>
      shiftCloseResponseSchema.parse({ ...CLEAN, [unexpectedKey]: 1 }),
    ).toThrow();
  });
});

/* -------------------------------------------------------------------------- */
/* 3 — G-7(d): EKRANDA IKKINCHI SON YO'Q                                      */
/* -------------------------------------------------------------------------- */

describe("G-7(d) (06-RESEARCH; §10.3, §10.4): yopilgandan keyingi ekran", () => {
  test("⛔ ko'rinadigan SONLAR to'plami AYNAN BITTA — kiritilgan naqd", async () => {
    await driveToClosed();

    /*
     * ⛔ Da'vo NOM BILAN BOG'LANMAGAN: ikkinchi son qanday nom, uslub
     *    yoki elementda paydo bo'lishidan qat'i nazar to'plam O'SADI va
     *    test qizaradi. `tizim = deklaratsiya − farq` — bitta ayirish,
     *    ya'ni IKKINCHI SONNING O'ZI ko'rlikni buzadi.
     */
    expect(distinctNumbers(document.body)).toEqual(
      new Set([String(DECLARED)]),
    );
  });

  test("⛔ e'lon hududi kiritilgan naqdni aytadi (§14.5, 5-hudud)", async () => {
    await driveToClosed();

    const status = screen.getByRole("status");
    expect(status.textContent).toContain(messages.collect.declarationWritten);
    expect(distinctNumbers(status)).toEqual(new Set([String(DECLARED)]));
  });
});

/* -------------------------------------------------------------------------- */
/* 4 — §10.3: YOPILGANDAN KEYIN AYNAN UCHTA ELEMENT                           */
/* -------------------------------------------------------------------------- */

describe("§10.3: natija bloki", () => {
  test("⛔ AYNAN UCHTA element — to'plam TENGLIGI va bolalar SANOG'I", async () => {
    await driveToClosed();

    const region = document.body.querySelector("[data-shift-result-region]");
    expect(region).not.toBeNull();

    const marked = Array.from(
      region!.querySelectorAll("[data-shift-result]"),
    ).map((el) => el.getAttribute("data-shift-result"));

    /* Nomlangan to'rtinchi element qo'shilsa — to'plam o'zgaradi. */
    expect(new Set(marked)).toEqual(new Set(["badge", "figure", "action"]));

    /*
     * ⛔ Nomlanmagan to'rtinchi element esa SANOQ bilan ushlanadi: aks
     *    holda «yig'indi» qatorini atributsiz qo'shib, darvozani chetlab
     *    o'tsa bo'lardi.
     */
    expect(region!.children.length).toBe(marked.length);
  });

  test("uchala elementning MAZMUNI ham o'lchanadi", async () => {
    await driveToClosed();

    expect(
      screen.getAllByText(messages.collect.declarationWritten).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", { name: messages.collect.shiftNew }),
    ).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 5 — XULQ: NOL RUXSAT, MANFIY RAD, BO'SH BLOKLANGAN                         */
/* -------------------------------------------------------------------------- */

describe("§10.2: deklaratsiya qiymatining chegaralari", () => {
  test("⛔ NOL deklaratsiya RUXSAT — DL-4 ochiladi va so'rov ketadi", async () => {
    /*
     * ⛔ Butun smenasi terminal bo'lgan kun REAL holat. Nolni rad etish
     *    kassirni YOLG'ON son kiritishga majburlardi.
     */
    apiClientMock.apiFetch.mockResolvedValue({ ...CLEAN, declared_soum: 0 });

    renderTree(<ShiftCloseForm onReopen={vi.fn()} shiftId={SHIFT_ID} />);

    fireEvent.change(amountInput(), { target: { value: "0" } });
    fireEvent.click(submitButton());

    const confirm = await screen.findByRole("button", {
      name: messages.collect.shiftClose,
    });
    fireEvent.click(confirm);

    await waitFor(() => {
      expect(closeCalls()).toHaveLength(1);
    });
    expect(closeCalls()[0]?.declared_soum).toBe(0);
  });

  test("⛔ MANFIY qiymat RAD ETILADI — `aria-invalid`, so'rov YO'Q", () => {
    renderTree(<ShiftCloseForm onReopen={vi.fn()} shiftId={SHIFT_ID} />);

    fireEvent.change(amountInput(), { target: { value: "-5000" } });

    expect(amountInput()).toHaveAttribute("aria-invalid", "true");

    fireEvent.click(submitButton());

    /* DL-4 ham ochilmaydi — tasdiq tugmasi umuman tug'ilmaydi. */
    expect(
      screen.queryByRole("button", { name: messages.collect.shiftClose }),
    ).toBeNull();
    expect(closeCalls()).toHaveLength(0);
  });

  test("⛔ MANFIY qiymat JIMGINA MUSBATGA aylanmaydi", () => {
    /*
     * ⛔ Filtrlab tashlash (`replace`) `-5000` ni `5000` ga aylantirib,
     *    kassir YOZMAGAN raqamni yozib qo'yardi — bu rad etishdan
     *    KO'RA yomonroq nuqson va u jimgina o'tib ketardi.
     */
    renderTree(<ShiftCloseForm onReopen={vi.fn()} shiftId={SHIFT_ID} />);

    fireEvent.change(amountInput(), { target: { value: "-5000" } });

    expect(amountInput()).toHaveValue("-5000");
  });

  test("⛔ summa kiritilmasa tasdiq `aria-disabled` va so'rov YUBORILMAYDI", () => {
    renderTree(<ShiftCloseForm onReopen={vi.fn()} shiftId={SHIFT_ID} />);

    const submit = submitButton();
    expect(submit).toHaveAttribute("aria-disabled", "true");

    fireEvent.click(submit);

    /*
     * §14.3: bosish RAD ETILMAYDI — u SABABNI e'lon qiladi.
     *
     * ⛔ E'LON MAYDON NOMINI EMAS, SABABNI aytadi (06-14). Ilgari bu
     *    yerda `collect.declaredLabel` («Yig'ilgan naqd») turardi va u
     *    VAQTINCHA yechim edi: `collect.*` da to'g'ri kalit YO'Q edi
     *    (`deferred-items.md` 8-band). Maydon nomini qaytarish
     *    foydalanuvchiga «nima qilay?» degan savolga javob bermasdi.
     */
    expect(screen.getByRole("status").textContent).toBe(
      messages.collect.declaredInvalid,
    );
    expect(closeCalls()).toHaveLength(0);
  });
});
