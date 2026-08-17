/**
 * ⛔⛔ G-motion-1(c) + G-motion-2(c,d,e) (09-UI-SPEC §16.4) — 4-QADAM FLIP
 * KLONINING DARVOZASI.
 *
 * =============================================================================
 * ⛔ 1. NEGA HAR TASDIQ INLINE USLUB USTIDA (09-RESEARCH Tuzoq 1).
 *
 *   jsdom Tailwind CSS'ni YUKLAMAYDI: `className="pointer-events-none"`
 *   berilgan elementda `getComputedStyle(...).pointerEvents === "auto"`
 *   [O'LCHANDI: vitest 4.1.10 + jsdom 30.0.1]. Inline uslub esa to'g'ri
 *   qaytadi — ya'ni «bosishni yutmaslik» (T-09-05 mitigatsiyasi) FAQAT
 *   `clone.style.pointerEvents` ustida o'lchanadi. Sinf nomi tasdig'i bu
 *   yerda YOLG'ON YASHIL berardi.
 *
 * ⛔ 2. `matchMedia` STUBI HAR TESTDA ALOHIDA, `vitest.setup.ts` DA EMAS.
 *
 *   Global stub «reduced-motion o'chirilgan» holatni HAMMA testga yoyib,
 *   teskari shox (`reduce: true`) HECH QACHON o'lchanmasdi — G-motion-1(c)
 *   ning butun maqsadi aynan o'sha shox (klon UMUMAN yaratilmaydi).
 *
 * ⛔ 3. G-motion-2(d) — AST, `grep` EMAS.
 *
 *   Matn skani `setTimeout` so'zi uchragan satr izohiga ham qoqilardi; AST
 *   esa FAQAT chaqiruv ifodalarini ko'radi. Detektorning o'zi sun'iy-ijobiy
 *   nazorat bilan tekshiriladi — bo'sh detektor abadiy yashil bo'lardi
 *   (`collect-surface.test.mjs` dagi «detektor ushlaydi» madaniyati).
 *
 * ⛔ 4. G-motion-2(e) — ISTISNO MODELI.
 *
 *   `flyAmountToList` istisno otishi MUMKIN (masalan `cloneNode` yiqilsa)
 *   va u istisnoni O'ZI YUTMAYDI — `try/catch` javobgarligi CHAQIRUVCHIDA
 *   (`collect-session.tsx::onWritten`). Chaqiruvchi tomoni
 *   `collect-session.test.tsx` da o'lchanadi (09-04 Task 3).
 * =============================================================================
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import ts from "typescript";
import { afterEach, describe, expect, test, vi } from "vitest";

import { flyAmountToList } from "@/components/collect/success-choreography";
import { prefersReducedMotion } from "@/lib/motion";

/* -------------------------------------------------------------------------- */
/* YORDAMCHILAR                                                               */
/* -------------------------------------------------------------------------- */

/**
 * `matchMedia` stubi — 09-RESEARCH «Kod namunalari 4» dan [O'LCHANDI: ishladi].
 *
 * ⛔ `vi.stubGlobal` HAR TESTDA chaqiriladi va `afterEach` da bekor qilinadi —
 *    ikkala shox (`reduce: true` / `false`) ham alohida o'lchanadi.
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

/** FLIP uchlari — haqiqiy DOM elementlari (`document.body` ichida). */
function makeEndpoints(): { from: HTMLElement; to: HTMLElement } {
  const from = document.createElement("p");
  from.textContent = "15 000";
  const to = document.createElement("section");
  document.body.append(from, to);
  return { from, to };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  /* Bu fayl React render qilmaydi — body'ni tozalash xavfsiz. */
  document.body.innerHTML = "";
});

/* -------------------------------------------------------------------------- */
/* `lib/motion.ts` — GUARD                                                    */
/* -------------------------------------------------------------------------- */

describe("lib/motion: prefersReducedMotion() guard (09-RESEARCH Tuzoq 1)", () => {
  test("`window` yo'q (SSR) — `false`: mavjud bo'lmagan API cheklov emas", () => {
    vi.stubGlobal("window", undefined);
    expect(prefersReducedMotion()).toBe(false);
  });

  test("`matchMedia` funksiya emas (jsdom standarti) — `false`", () => {
    /* jsdom 30.0.1 `window.matchMedia` ni UMUMAN bermaydi [O'LCHANDI]. */
    expect(typeof window.matchMedia).not.toBe("function");
    expect(prefersReducedMotion()).toBe(false);
  });

  test("`reduce` mos kelsa — `true`", () => {
    stubMatchMedia(true);
    expect(prefersReducedMotion()).toBe(true);
  });

  test("`reduce` mos kelmasa — `false`", () => {
    stubMatchMedia(false);
    expect(prefersReducedMotion()).toBe(false);
  });
});

/* -------------------------------------------------------------------------- */
/* G-motion-1(c) — REDUCED-MOTION SHOXI                                       */
/* -------------------------------------------------------------------------- */

describe("G-motion-1(c): reduced-motion shoxi", () => {
  test("⛔ `reduce: true` — klon UMUMAN yaratilmaydi (body bolalar soni O'ZGARMAYDI)", () => {
    stubMatchMedia(true);
    const { from, to } = makeEndpoints();
    const before = document.body.children.length;

    flyAmountToList({ from, to });

    expect(document.body.children.length).toBe(before);
  });

  test("`reduce: false` — klon YARATILADI va 450ms tozalashda O'ZI yo'qoladi", () => {
    vi.useFakeTimers();
    stubMatchMedia(false);
    const { from, to } = makeEndpoints();
    const before = document.body.children.length;

    flyAmountToList({ from, to });

    expect(document.body.children.length).toBe(before + 1);

    /* Tozalash — `setTimeout` FAQAT `remove()` uchun (G-motion-2(d)). */
    vi.advanceTimersByTime(450);
    expect(document.body.children.length).toBe(before);
  });
});

/* -------------------------------------------------------------------------- */
/* G-motion-2(c) — KLON XOSSALARI INLINE USLUBDAN                             */
/* -------------------------------------------------------------------------- */

describe("G-motion-2(c): klon xossalari — INLINE uslubdan o'qiladi", () => {
  test("⛔ pointerEvents=none · aria-hidden=true · position=fixed", () => {
    vi.useFakeTimers();
    stubMatchMedia(false);
    const { from, to } = makeEndpoints();
    const before = Array.from(document.body.children);

    flyAmountToList({ from, to });

    const clone = Array.from(document.body.children).find(
      (el) => !before.includes(el),
    ) as HTMLElement;
    expect(clone).toBeDefined();

    /* ⛔ INLINE uslub — jsdom'da yagona ishonchli o'qish yo'li. */
    expect(clone.style.pointerEvents).toBe("none");
    expect(clone.getAttribute("aria-hidden")).toBe("true");
    expect(clone.style.position).toBe("fixed");
    /* Inline uslubdan `getComputedStyle` ham to'g'ri qaytaradi [O'LCHANDI]. */
    expect(getComputedStyle(clone).pointerEvents).toBe("none");

    vi.advanceTimersByTime(450);
  });

  test("`from === null` — jim qaytadi (istisno YO'Q, klon YO'Q)", () => {
    stubMatchMedia(false);
    const { to } = makeEndpoints();
    const before = document.body.children.length;

    expect(() => flyAmountToList({ from: null, to })).not.toThrow();
    expect(document.body.children.length).toBe(before);
  });

  test("`to === null` — jim qaytadi", () => {
    stubMatchMedia(false);
    const { from } = makeEndpoints();
    const before = document.body.children.length;

    expect(() => flyAmountToList({ from, to: null })).not.toThrow();
    expect(document.body.children.length).toBe(before);
  });
});

/* -------------------------------------------------------------------------- */
/* G-motion-2(d) — AST: `setTimeout` ICHIDA HOLAT O'ZGARTIRISH YO'Q           */
/* -------------------------------------------------------------------------- */

/*
 * ⚠ `import.meta.url` vitest transformida `file:` sxemasida EMAS —
 *   manba yo'li ish katalogidan quriladi (vitest har doim `frontend/`
 *   ildizidan yuguradi: `vitest.config.ts` shu yerda).
 */
const CHOREOGRAPHY_SOURCE = readFileSync(
  path.join(
    process.cwd(),
    "src",
    "components",
    "collect",
    "success-choreography.tsx",
  ),
  "utf8",
);

/**
 * Har `setTimeout(...)` chaqiruvi argumentlari ichidagi `set[A-Z]…`
 * identifikator-chaqiruvlarini yig'adi.
 *
 * ⚠ `setTimeout`/`setInterval` NING O'ZI `/^set[A-Z]/` ga tushadi — ular
 *   holat-setterlari emas, shuning uchun aniq chiqarib tashlanadi (aks
 *   holda ichma-ich `setTimeout` sun'iy-ijobiy berardi).
 */
function setterCallsInsideSetTimeout(source: string): string[] {
  const sourceFile = ts.createSourceFile(
    "success-choreography.tsx",
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const offenders: string[] = [];

  const collectSetterCalls = (node: ts.Node): void => {
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      /^set[A-Z]/u.test(node.expression.text) &&
      node.expression.text !== "setTimeout" &&
      node.expression.text !== "setInterval"
    ) {
      offenders.push(node.expression.text);
    }
    ts.forEachChild(node, collectSetterCalls);
  };

  const visit = (node: ts.Node): void => {
    if (ts.isCallExpression(node)) {
      const callee = node.expression;
      const isSetTimeout =
        (ts.isIdentifier(callee) && callee.text === "setTimeout") ||
        (ts.isPropertyAccessExpression(callee) &&
          callee.name.text === "setTimeout");
      if (isSetTimeout) {
        for (const arg of node.arguments) collectSetterCalls(arg);
      }
    }
    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
  return offenders;
}

describe("G-motion-2(d): AST — `setTimeout` faqat tozalash", () => {
  test("⛔ manbada `setTimeout` callback'ida `set[A-Z]…` chaqiruvi 0 marta", () => {
    /* Manbada kamida bitta `setTimeout` BOR (tozalash) — parser jonli. */
    expect(CHOREOGRAPHY_SOURCE).toContain("setTimeout");
    expect(setterCallsInsideSetTimeout(CHOREOGRAPHY_SOURCE)).toEqual([]);
  });

  test("sun'iy-ijobiy nazorat: namuna satrni detektor USHLAYDI", () => {
    expect(
      setterCallsInsideSetTimeout("setTimeout(() => setBusy(false), 10);"),
    ).toEqual(["setBusy"]);
    /* `window.setTimeout` shakli ham qamrovda. */
    expect(
      setterCallsInsideSetTimeout(
        "window.setTimeout(() => { setDone(true); }, 450);",
      ),
    ).toEqual(["setDone"]);
    /* Toza tozalash chaqiruvi esa ushlanmaydi. */
    expect(
      setterCallsInsideSetTimeout(
        "window.setTimeout(() => clone.remove(), 450);",
      ),
    ).toEqual([]);
  });
});

/* -------------------------------------------------------------------------- */
/* G-motion-2(e) — ISTISNO MODELI                                             */
/* -------------------------------------------------------------------------- */

describe("G-motion-2(e): istisno modeli — funksiya istisnoni YUTMAYDI", () => {
  test("`cloneNode` buzilganda istisno OTILADI — `try/catch` chaqiruvchida", () => {
    stubMatchMedia(false);
    const { from, to } = makeEndpoints();
    from.cloneNode = () => {
      throw new Error("sinov: cloneNode buzildi");
    };

    /*
     * ⛔ Funksiya istisnoni yutsa, bu tasdiq qizarardi — va u ATAYIN
     *    shunday: himoya qatlami BITTA joyda (`onWritten` dagi try/catch)
     *    yashaydi, ikki joyda yashasa biri jimgina o'lik bo'lardi.
     */
    expect(() => flyAmountToList({ from, to })).toThrow();
  });
});
