/**
 * `Reveal` — scroll-reveal primitivining xulq kontrakti (10-06 Task 1, TDD RED).
 *
 * ⛔ jsdom 30.0.1 da `IntersectionObserver` UMUMAN YO'Q [O'LCHANDI: 10-06
 * reja banди; `stall-map` presedenti bilan bir sinf] — shuning uchun mock
 * QO'LDA quriladi: konstruktorga berilgan callback saqlanadi,
 * `observe`/`disconnect` chaqiruvlari sanaladi va callback QO'LDA otiladi.
 *
 * ⛔ `matchMedia` stubi HAR TESTDA ALOHIDA, `vitest.setup.ts` da EMAS
 * (`success-choreography.test.tsx` dagi 2-band darsi): global stub
 * reduced-motion'ning ikkala shoxini bir holatga yopishtirib qo'yardi.
 *
 * O'lchanadigan beshala xulq (reja <behavior> bandlari):
 *   1. Ko'rinmagan holatda `.motion-enter` QO'YILMAYDI — kontent esa
 *      DOM'da KO'RINADI (JS kelmasa yo'qolib qolmaslik sharti).
 *   2. `isIntersecting: true` callback'ida `.motion-enter` qo'shiladi.
 *   3. Ochilgandan keyin `disconnect()` chaqiriladi (bir martalik guard).
 *   4. `unmount()` da `disconnect()` chaqiriladi (ochilmagan holatda ham).
 *   5. Reduced-motion TRUE bo'lsa observer UMUMAN qurilmaydi va kontent
 *      darhol ko'rinadi.
 *   + `onReveal` kontrakt: ochilishda BIR marta (step-line iste'moli uchun).
 */
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { Reveal } from "./reveal";

type ObserverEntry = { isIntersecting: boolean };
type ObserverCallback = (entries: ObserverEntry[]) => void;

const ioState: {
  callbacks: ObserverCallback[];
  observeCalls: number;
  disconnectCalls: number;
  constructed: number;
} = {
  callbacks: [],
  observeCalls: 0,
  disconnectCalls: 0,
  constructed: 0,
};

class MockIntersectionObserver {
  constructor(callback: ObserverCallback) {
    ioState.constructed += 1;
    ioState.callbacks.push(callback);
  }
  observe(): void {
    ioState.observeCalls += 1;
  }
  disconnect(): void {
    ioState.disconnectCalls += 1;
  }
  unobserve(): void {}
  takeRecords(): ObserverEntry[] {
    return [];
  }
}

/** `success-choreography.test.tsx:55` naqshi — har testda alohida stub. */
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

/** Saqlangan callback'ni QO'LDA otish — React holati `act` ichida yangilanadi. */
function fireIntersect(isIntersecting: boolean, index = 0): void {
  act(() => {
    ioState.callbacks[index]?.([{ isIntersecting }]);
  });
}

beforeEach(() => {
  ioState.callbacks = [];
  ioState.observeCalls = 0;
  ioState.disconnectCalls = 0;
  ioState.constructed = 0;
  vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Reveal — scroll-reveal primitivi (10-06)", () => {
  test("1: ko'rinmagan holatda `.motion-enter` YO'Q, kontent esa DOM'da ko'rinadi", () => {
    const { container } = render(
      <Reveal delayIndex={2}>
        <p>Salom dunyo</p>
      </Reveal>,
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.classList.contains("motion-enter")).toBe(false);
    // Boshlang'ich holat KO'RINADIGAN: `opacity: 0` sinfidagi yashirish yo'q —
    // JS/observer ishlamasa ham kontent yo'qolmaydi.
    expect(screen.getByText("Salom dunyo")).toBeInTheDocument();
    // Stagger indeksi `--i` sifatida uzatiladi (revenue-card naqshi).
    expect(wrapper.style.getPropertyValue("--i")).toBe("2");
    // Observer qurilgan va kuzatuv boshlangan (2-xulqning zamini).
    expect(ioState.constructed).toBe(1);
    expect(ioState.observeCalls).toBe(1);
  });

  test("2: `isIntersecting: true` callback'i `.motion-enter` qo'shadi (false — qo'shmaydi)", () => {
    const { container } = render(
      <Reveal>
        <p>Kontent</p>
      </Reveal>,
    );
    const wrapper = container.firstElementChild as HTMLElement;

    fireIntersect(false);
    expect(wrapper.classList.contains("motion-enter")).toBe(false);

    fireIntersect(true);
    expect(wrapper.classList.contains("motion-enter")).toBe(true);
  });

  test("3: ochilgandan keyin `disconnect()` chaqiriladi — takroriy kuzatuv yo'q", () => {
    render(
      <Reveal>
        <p>Kontent</p>
      </Reveal>,
    );

    expect(ioState.disconnectCalls).toBe(0);
    fireIntersect(true);
    expect(ioState.disconnectCalls).toBe(1);
  });

  test("4: `unmount()` da `disconnect()` chaqiriladi (ochilmagan holatda ham)", () => {
    const { unmount } = render(
      <Reveal>
        <p>Kontent</p>
      </Reveal>,
    );

    expect(ioState.disconnectCalls).toBe(0);
    unmount();
    expect(ioState.disconnectCalls).toBe(1);
  });

  test("5: reduced-motion TRUE — observer UMUMAN qurilmaydi, kontent darhol ko'rinadi", () => {
    stubMatchMedia(true);

    const { container } = render(
      <Reveal>
        <p>{"Darhol ko'rinadigan kontent"}</p>
      </Reveal>,
    );

    expect(ioState.constructed).toBe(0);
    expect(ioState.observeCalls).toBe(0);
    expect(screen.getByText("Darhol ko'rinadigan kontent")).toBeInTheDocument();
    // Sinfsiz ham ko'rinadi — `.motion-enter` faqat KIRISH animatsiyasini
    // qo'shadi, ko'rinishni boshqarmaydi.
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.classList.contains("motion-enter")).toBe(false);
  });

  test("onReveal kontrakti: ochilish paytida BIR marta chaqiriladi (step-line iste'moli)", () => {
    const onReveal = vi.fn();
    render(
      <Reveal onReveal={onReveal}>
        <p>Kontent</p>
      </Reveal>,
    );

    fireIntersect(true);
    // Mock'da `disconnect` haqiqiy oqimni to'xtatmaydi — bir martalik guard
    // callback'ning O'ZIDA bo'lishi shart (takroriy otish sinovi).
    fireIntersect(true);

    expect(onReveal).toHaveBeenCalledTimes(1);
  });
});
