/**
 * ⛔⛔ G-land-2(a…e) (10-UI-SPEC §16.4) — 12s SIKL VA REDUCED-MOTION STATIK
 * KADRINING DARVOZASI. ROADMAP SC#2 ning yagona halol o'lchovi.
 *
 * =============================================================================
 * ⛔ 1. jsdom CHEKLOVLARI (MEROS, o'lchangan: jsdom 30.0.1 + vitest 4.1.10):
 *
 *   - `window.matchMedia` YO'Q → har testda ALOHIDA `vi.stubGlobal`
 *     (⛔ `vitest.setup.ts` ga QO'YILMAYDI: teskari shox — reduced-motion
 *     YOQILGAN holat — hech qachon o'lchanmasdi). Naqsh:
 *     `collect/success-choreography.test.tsx`.
 *   - `IntersectionObserver` YO'Q → qo'lda mock: `observe`/`disconnect`
 *     chaqiruvlarini SANAYDI va callback QO'LDA ateshlanadi (jsdom real
 *     kesishuv hisoblamaydi).
 *   - Tailwind sinfidan `getComputedStyle` `"auto"` → barcha «final-kadr»
 *     tasdiqlari DOM MATNI va ATRIBUTLARI ustida (`2 306 000`,
 *     `data-state="unpaid"`), sinf/uslub ustida EMAS.
 *
 * ⛔ 2. SIKL DAVRI — 13 500 ms, «12s» faqat nom (§5.5: besh faza yig'indisi
 *   2600+2700+3000+1700+3500). Server kadri 5-faza — mount'dan keyin sikl
 *   PHASE5 oynasi (3500 ms) o'tib 1-fazaga kiradi, so'ng har 13 500 ms da
 *   AYNAN shu reset nuqtasiga qaytadi. (b) shu ikkala nuqtani o'lchaydi.
 *
 * ⛔ 3. SABOTAJ ISBOTI (§16.3): (a) — komponentdagi reduced-motion erta
 *   return olib tashlansa qizaradi (IO trigger + advance shuning uchun (a)
 *   ichida ham bor: trigger'siz taymer baribir 0 bo'lib sabotaj o'tardi);
 *   (d) — effekt tozalash funksiyasi olib tashlansa qizaradi. O'lchov
 *   natijalari 10-05-SUMMARY'da.
 * =============================================================================
 */
import { act, cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { HeroScene } from "./hero-scene";

/* -------------------------------------------------------------------------- */
/* KONTRAKT KONSTANTALARI                                                     */
/* -------------------------------------------------------------------------- */

/** §5.5 timing kontrakti — sikl davri va faza oynalari (ms). */
const CYCLE_MS = 13_500;
const PHASE_WINDOWS_MS = [2600, 2700, 3000, 1700, 3500] as const;
const PHASE5_HOLD_MS = 3500;
const STALL_COUNT = 30;
const FINAL_REVENUE_TEXT = "2 306 000";

/**
 * ⛔ Yorliqlar reyestri — MATN KATALOGIDAN HOSILA (G-land-2(c)): testda
 * literal qayta yozilsa u ikkinchi manba bo'lardi va copy o'zgarganda
 * jimgina eskirardi.
 */
const PHASE_NUMBERS = [1, 2, 3, 4, 5] as const;
const PHASE_LABELS = PHASE_NUMBERS.map(
  (n) =>
    messages.landing.scene[`phase${n}` as keyof typeof messages.landing.scene],
);

/* -------------------------------------------------------------------------- */
/* YORDAMCHILAR                                                               */
/* -------------------------------------------------------------------------- */

/**
 * `matchMedia` stubi — har testda alohida, ikkala shox ham o'lchanadi
 * (09-RESEARCH «Kod namunalari 4», `success-choreography.test.tsx` naqshi).
 */
function stubMatchMedia(reduce: boolean): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    addEventListener() {},
    addListener() {},
    dispatchEvent: () => false,
    matches: reduce && query.includes("reduce"),
    media: query,
    onchange: null,
    removeEventListener() {},
    removeListener() {},
  }));
}

/**
 * IntersectionObserver mock'i — jsdom'da YO'Q. `observe`/`disconnect`
 * SANALADI, callback `trigger()` bilan QO'LDA ateshlanadi.
 */
class MockIntersectionObserver {
  static instances: MockIntersectionObserver[] = [];

  readonly callback: IntersectionObserverCallback;
  observeCalls = 0;
  disconnectCalls = 0;

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
    MockIntersectionObserver.instances.push(this);
  }

  observe(): void {
    this.observeCalls += 1;
  }

  unobserve(): void {}

  disconnect(): void {
    this.disconnectCalls += 1;
  }

  trigger(isIntersecting: boolean): void {
    this.callback(
      [{ isIntersecting } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    );
  }
}

function stubIntersectionObserver(): void {
  MockIntersectionObserver.instances = [];
  vi.stubGlobal(
    "IntersectionObserver",
    MockIntersectionObserver as unknown as typeof IntersectionObserver,
  );
}

function renderScene() {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={{ landing: messages.landing }}
    >
      <HeroScene />
    </NextIntlClientProvider>,
  );
}

/** Sahnani «ko'rinadigan» qilish — IO callback'ini qo'lda ateshlash. */
function triggerIntersection(isIntersecting: boolean): void {
  act(() => {
    for (const instance of MockIntersectionObserver.instances) {
      instance.trigger(isIntersecting);
    }
  });
}

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

/** Final-kadr tasdig'i — DOM matni va atributlari ustida (jsdom qoidasi). */
function expectFinalFrame(): void {
  const map = screen.getByTestId("hero-scene-map");
  expect(map.children).toHaveLength(STALL_COUNT);
  expect(map.querySelectorAll('[data-on="true"]')).toHaveLength(STALL_COUNT);
  expect(map.querySelectorAll('[data-state="unpaid"]')).toHaveLength(1);
  expect(map.querySelectorAll('[data-state="paid"]')).toHaveLength(
    STALL_COUNT - 1,
  );
  expect(screen.getByTestId("hero-scene-report").dataset.visible).toBe("true");
  expect(screen.getByTestId("hero-scene-revenue").textContent).toBe(
    FINAL_REVENUE_TEXT,
  );
}

/** Reset (1-faza boshi) tasdig'i — birorta katak yoniq EMAS. */
function expectResetFrame(): void {
  const map = screen.getByTestId("hero-scene-map");
  expect(map.querySelectorAll('[data-on="true"]')).toHaveLength(0);
  expect(screen.getByTestId("hero-scene-report").dataset.visible).toBe("false");
  expect(screen.getByTestId("hero-scene-phase").textContent).toBe(
    PHASE_LABELS[0],
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

/* -------------------------------------------------------------------------- */
/* G-land-2(a) — REDUCED-MOTION: 0 TAYMER + TO'LIQ FINAL-KADR                 */
/* -------------------------------------------------------------------------- */

describe("G-land-2(a): reduced-motion — sikl UMUMAN boshlanmaydi", () => {
  test("(a) reduce=true: birorta taymer yaratilmaydi VA DOM to'liq yakuniy kadr", async () => {
    vi.useFakeTimers();
    stubMatchMedia(true);
    stubIntersectionObserver();
    const timerSpy = vi.spyOn(globalThis, "setTimeout");

    renderScene();
    /*
     * ⛔ Trigger + advance ATAYIN bor: erta return olib tashlansa (sabotaj)
     * sikl aynan shu yo'ldan boshlanib josus > 0 bo'ladi. Trigger'siz
     * taymer baribir 0 bo'lib sabotaj jimgina o'tardi.
     */
    triggerIntersection(true);
    await advance(PHASE5_HOLD_MS + 1000);

    expect(timerSpy).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
    /* Reduced'da IntersectionObserver ham YARATILMAYDI (batareya). */
    expect(MockIntersectionObserver.instances).toHaveLength(0);
    expectFinalFrame();
  });
});

/* -------------------------------------------------------------------------- */
/* G-land-2(b) — REWIND YO'Q + SIKL DAVRI 13 500 ms                           */
/* -------------------------------------------------------------------------- */

describe("G-land-2(b): server kadridan davom — rewind yo'q, davr 13 500 ms", () => {
  test("(b) 0 ms da DOM hamon yakuniy kadr; 13 500 ms to'liq davrdan keyin sikl 1-fazaga qaytgan (kataklar on emas)", async () => {
    vi.useFakeTimers();
    stubMatchMedia(false);
    stubIntersectionObserver();

    renderScene();
    /* 0 ms — hidratatsiyadan keyin ham server kadri turibdi (rewind yo'q). */
    expectFinalFrame();

    /* Ko'rinish boshlandi — kadr BARIBIR o'zgarmaydi (5-fazadan davom). */
    triggerIntersection(true);
    expectFinalFrame();
    expect(screen.getByTestId("hero-scene-phase").textContent).toBe(
      PHASE_LABELS[4],
    );

    /* PHASE5 oynasi o'tdi — sikl 1-fazaga kirdi (reset). */
    await advance(PHASE5_HOLD_MS);
    expectResetFrame();

    /* ⛔ 13 500 ms — TO'LIQ davr: sikl AYNAN shu reset nuqtasiga qaytadi. */
    await advance(CYCLE_MS);
    expectResetFrame();
  });
});

/* -------------------------------------------------------------------------- */
/* G-land-2(c) — BESHALA FAZA YORLIG'I KETMA-KET, REYESTR KATALOGDAN          */
/* -------------------------------------------------------------------------- */

describe("G-land-2(c): faza yorliqlari — matn katalogidan hosila reyestr", () => {
  test("(c) beshala yorliq sikl davomida ketma-ket ko'rinadi", async () => {
    vi.useFakeTimers();
    stubMatchMedia(false);
    stubIntersectionObserver();

    /* Reyestr katalogdan kelganining o'zi ham o'lchanadi (bo'sh emas). */
    expect(PHASE_LABELS).toHaveLength(5);
    for (const label of PHASE_LABELS) {
      expect(label).toBeTruthy();
    }

    renderScene();
    triggerIntersection(true);

    const phaseNode = screen.getByTestId("hero-scene-phase");
    /* Server kadri — 5-faza yorlig'i. */
    expect(phaseNode.textContent).toBe(PHASE_LABELS[4]);

    /* 5 → 1: hold oynasi. */
    await advance(PHASE5_HOLD_MS);
    expect(phaseNode.textContent).toBe(PHASE_LABELS[0]);

    /* 1 → 2 → 3 → 4 → 5: har faza o'z oynasi bilan (§5.5). */
    await advance(PHASE_WINDOWS_MS[0]);
    expect(phaseNode.textContent).toBe(PHASE_LABELS[1]);
    await advance(PHASE_WINDOWS_MS[1]);
    expect(phaseNode.textContent).toBe(PHASE_LABELS[2]);
    await advance(PHASE_WINDOWS_MS[2]);
    expect(phaseNode.textContent).toBe(PHASE_LABELS[3]);
    await advance(PHASE_WINDOWS_MS[3]);
    expect(phaseNode.textContent).toBe(PHASE_LABELS[4]);
  });
});

/* -------------------------------------------------------------------------- */
/* G-land-2(d) — TAYMER SIZIB QOLMAYDI                                        */
/* -------------------------------------------------------------------------- */

describe("G-land-2(d): unmount'da taymerlar to'liq tozalanadi", () => {
  test("(d) unmount'dan keyin clearTimeout soni yaratilgan taymerlar soniga TENG", async () => {
    vi.useFakeTimers();
    stubMatchMedia(false);
    stubIntersectionObserver();
    const createSpy = vi.spyOn(globalThis, "setTimeout");
    const clearSpy = vi.spyOn(globalThis, "clearTimeout");

    const { unmount } = renderScene();
    triggerIntersection(true);
    /* Bir necha faza o'tsin — reyestrda ishlagan VA kutayotgan id'lar bor. */
    await advance(PHASE5_HOLD_MS + PHASE_WINDOWS_MS[0] + PHASE_WINDOWS_MS[1]);

    const createdCount = createSpy.mock.calls.length;
    expect(createdCount).toBeGreaterThan(0);

    unmount();

    /* ⛔ Har yaratilgan id AYNAN bir marta tozalanadi — sizish YO'Q. */
    expect(clearSpy.mock.calls.length).toBe(createdCount);
    expect(vi.getTimerCount()).toBe(0);
    /* IO ham uziladi — `disconnect` tozalash funksiyasida MAJBURIY. */
    expect(MockIntersectionObserver.instances[0]?.disconnectCalls).toBe(1);
  });
});

/* -------------------------------------------------------------------------- */
/* G-land-2(e) — KO'RINMAGANDA TAYMER YARATILMAYDI                            */
/* -------------------------------------------------------------------------- */

describe("G-land-2(e): isIntersecting=false — sikl boshlanmaydi", () => {
  test("(e) ko'rinmas sahnada yangi taymer YARATILMAYDI", async () => {
    vi.useFakeTimers();
    stubMatchMedia(false);
    stubIntersectionObserver();
    const timerSpy = vi.spyOn(globalThis, "setTimeout");

    renderScene();
    /* Kuzatuv o'rnatilgan (observe chaqirilgan) — mexanizm jonli. */
    expect(MockIntersectionObserver.instances).toHaveLength(1);
    expect(MockIntersectionObserver.instances[0]?.observeCalls).toBe(1);

    triggerIntersection(false);
    await advance(CYCLE_MS + PHASE5_HOLD_MS);

    expect(timerSpy).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
    /* DOM server kadrida qoladi — hech nima «o'ynab qo'ymaydi». */
    expectFinalFrame();
  });
});
