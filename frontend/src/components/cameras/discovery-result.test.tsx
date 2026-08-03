/**
 * NATIJA PANELI — SC#2 NING UI ISBOTI (UI-SPEC §6.3, §13.5).
 *
 * =============================================================================
 * BU FAYL BITTA DA'VONI O'LCHAYDI:
 *
 *   «Hech narsa o'zgarmagan skan buzuq skandan FARQLANADI.»
 *
 * Farqlanish IKKI mustaqil belgidan iborat va ikkalasi ham shu yerda
 * alohida qulflanadi:
 *
 *   (a) UCHALA HISOBLAGICH HAM KO'RINADI — noli bilan birga. Nol qatorni
 *       yashirish «bu skan hech narsa qilmadi» degan yolg'on signal
 *       berardi. Reja bu bandni SABOTAJ bilan tekshirishni talab qiladi:
 *       `{count > 0 && …}` sharti AYNAN shu testni qizartirishi kerak.
 *
 *   (b) ANTI-«BUZUQ KO'RINADI» JUMLASI — u faqat O'ZGARISH BO'LMAGAN
 *       holatda chiqadi va boshqa hech qachon.
 *
 * ⚠ REJADAGI ZIDDIYAT VA UNING O'LCHOVI (SUMMARY'ga yozildi):
 *   rejaning `<action>` bandi jumlani «uchala nol» ga bog'laydi,
 *   `<behavior>` bandi va UI-SPEC §6.3 ESKIZI esa `0 / 0 / 6` holatida
 *   talab qiladi. Quyida IKKALA holat ham alohida test bilan qulflangan
 *   — shart `added === 0 && offline === 0` ikkalasini ham qamraydi.
 *   Harfma-harf «uchala nol» esa jumlani faqat kanalsiz NVR'da
 *   chiqarardi, ya'ni SC#2 ning aynan teskarisi bo'lardi.
 * =============================================================================
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  DiscoveryResult,
  discoveryCounts,
  runNoChanges,
} from "@/components/cameras/discovery-result";
import type { DiscoveryRun } from "@/lib/api-types";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const DONE_LABEL = messages.cameras.runDone;
const ADDED_LABEL = messages.cameras.runAdded;
const OFFLINE_LABEL = messages.cameras.runOffline;
const UNCHANGED_LABEL = messages.cameras.runUnchanged;
const NO_CHANGES = messages.cameras.runNoChanges;
const CLOSE_LABEL = messages.cameras.runClose;

function makeRun(overrides: Partial<DiscoveryRun> = {}): DiscoveryRun {
  return {
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    nvr_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    status: "succeeded",
    started_at: "2026-08-03T09:30:00Z",
    finished_at: "2026-08-03T09:30:41Z",
    channels_found: 6,
    channels_added: 0,
    channels_marked_offline: 0,
    error_code: null,
    error_detail: null,
    ...overrides,
  };
}

function renderResult(element: ReactElement): ReturnType<typeof render> {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      {element}
    </NextIntlClientProvider>,
  );
}

/** Yorliq -> unga bog'langan `<dd>` ning matni (dasturiy bog'lanish orqali). */
function counterValue(label: string): string {
  const term = screen.getByText(label);
  expect(term.tagName).toBe("DT");
  const row = term.parentElement;
  expect(row).not.toBeNull();
  const value = row?.querySelector("dd");
  expect(value).not.toBeNull();
  return (value?.textContent ?? "").trim();
}

/* ---------------------------------------------------------------------------
 * (a) UCHALA HISOBLAGICH — NOL BO'LGANDA HAM
 * ------------------------------------------------------------------------ */

describe("uch hisoblagich DOIM ko'rinadi", () => {
  test("uchala nol holatida uchala hisoblagich ham render bo'ladi", () => {
    renderResult(
      <DiscoveryResult
        onClose={vi.fn()}
        run={makeRun({
          channels_added: 0,
          channels_found: 0,
          channels_marked_offline: 0,
        })}
      />,
    );

    // Yorliqlar — uchalasi ham DOM'da.
    expect(screen.getByText(ADDED_LABEL)).toBeInTheDocument();
    expect(screen.getByText(OFFLINE_LABEL)).toBeInTheDocument();
    expect(screen.getByText(UNCHANGED_LABEL)).toBeInTheDocument();

    // Va ularning HAR BIRIDA nol raqami turadi — «yo'q» emas.
    expect(counterValue(ADDED_LABEL)).toBe("0");
    expect(counterValue(OFFLINE_LABEL)).toBe("0");
    expect(counterValue(UNCHANGED_LABEL)).toBe("0");
  });

  test("idempotent qayta skan (0 / 0 / 6) da ham uchalasi turadi", () => {
    renderResult(
      <DiscoveryResult
        onClose={vi.fn()}
        run={makeRun({
          channels_added: 0,
          channels_found: 6,
          channels_marked_offline: 0,
        })}
      />,
    );

    expect(counterValue(ADDED_LABEL)).toBe("0");
    expect(counterValue(OFFLINE_LABEL)).toBe("0");
    expect(counterValue(UNCHANGED_LABEL)).toBe("6");
  });

  test("raqam va yorliq `<dl>` bilan DASTURIY bog'langan", () => {
    const { container } = renderResult(
      <DiscoveryResult onClose={vi.fn()} run={makeRun()} />,
    );

    const lists = container.querySelectorAll("dl");
    expect(lists).toHaveLength(1);

    const list = lists[0];
    // Uchta juftlik — skrinriderda «Yangi qo'shildi: 0» bo'lib eshitiladi.
    expect(list.querySelectorAll("dt")).toHaveLength(3);
    expect(list.querySelectorAll("dd")).toHaveLength(3);

    // Har `<dt>` va `<dd>` BIR XIL o'ramda — bog'lanish razmetkadan
    // ko'rinadi, tartibga tayanmaydi.
    for (const term of list.querySelectorAll("dt")) {
      expect(within(term.parentElement as HTMLElement).getByText(/^\d+$/u))
        .toBeInTheDocument();
    }
  });
});

/* ---------------------------------------------------------------------------
 * (b) ANTI-«BUZUQ KO'RINADI» JUMLASI
 * ------------------------------------------------------------------------ */

describe("«o'zgarish topilmadi» jumlasi", () => {
  test("uchala nol bo'lganda chiqadi", () => {
    renderResult(
      <DiscoveryResult
        onClose={vi.fn()}
        run={makeRun({
          channels_added: 0,
          channels_found: 0,
          channels_marked_offline: 0,
        })}
      />,
    );

    expect(screen.getByText(NO_CHANGES)).toBeInTheDocument();
  });

  test("0 / 0 / 6 — hech narsa o'zgarmagan skanda ham chiqadi", () => {
    renderResult(
      <DiscoveryResult
        onClose={vi.fn()}
        run={makeRun({
          channels_added: 0,
          channels_found: 6,
          channels_marked_offline: 0,
        })}
      />,
    );

    expect(screen.getByText(NO_CHANGES)).toBeInTheDocument();
  });

  test("`added > 0` bo'lganda CHIQMAYDI", () => {
    renderResult(
      <DiscoveryResult
        onClose={vi.fn()}
        run={makeRun({
          channels_added: 6,
          channels_found: 6,
          channels_marked_offline: 0,
        })}
      />,
    );

    expect(screen.queryByText(NO_CHANGES)).toBeNull();
    expect(counterValue(ADDED_LABEL)).toBe("6");
    expect(counterValue(UNCHANGED_LABEL)).toBe("0");
  });

  test("`offline > 0` bo'lganda CHIQMAYDI, o'rniga qisman muvaffaqiyat qatori keladi", () => {
    renderResult(
      <DiscoveryResult
        onClose={vi.fn()}
        run={makeRun({
          channels_added: 0,
          channels_found: 6,
          channels_marked_offline: 2,
        })}
      />,
    );

    expect(screen.queryByText(NO_CHANGES)).toBeNull();
    // Ulanmagan kanal — XATO EMAS (UI-SPEC §6.4), shuning uchun matn
    // tushuntiruvchi qator bo'lib chiqadi.
    expect(
      screen.getByText(
        messages.cameras.runSomeOffline.replace("{count}", "2"),
      ),
    ).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * SARLAVHA, VAQT BELGISI VA ROL
 * ------------------------------------------------------------------------ */

describe("sarlavha va e'lon", () => {
  test("sarlavha AMALNI aytadi va birinchi hisoblagichni takrorlamaydi", () => {
    renderResult(<DiscoveryResult onClose={vi.fn()} run={makeRun()} />);

    expect(screen.getByText(DONE_LABEL)).toBeInTheDocument();
    // «0 ta kamera qo'shildi» shaklidagi sarlavha TAQIQLANGAN (§6.3).
    expect(screen.queryByText(new RegExp(`^0 .*${ADDED_LABEL}`, "iu"))).toBeNull();
  });

  test("vaqt belgisi ko'rinadi — skan HOZIR bo'lganining ikkinchi dalili", () => {
    const { container } = renderResult(
      <DiscoveryResult onClose={vi.fn()} run={makeRun()} />,
    );

    // Vaqt qismi (`09:30` -> Toshkent vaqtida `14:30`) — raqamli belgi.
    expect(container.textContent).toMatch(/\d{1,2}:\d{2}/u);
  });

  test("`role=\"status\"`, `alert` EMAS — muvaffaqiyat ogohlantirish emas", () => {
    const { container } = renderResult(
      <DiscoveryResult onClose={vi.fn()} run={makeRun()} />,
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  test("yopish tugmasi chaqiruvchini xabardor qiladi", () => {
    const onClose = vi.fn();
    renderResult(<DiscoveryResult onClose={onClose} run={makeRun()} />);

    screen.getByRole("button", { name: CLOSE_LABEL }).click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

/* ---------------------------------------------------------------------------
 * FORMULA — SOF FUNKSIYA
 * ------------------------------------------------------------------------ */

describe("discoveryCounts / runNoChanges", () => {
  test("`unchanged = channels_found − channels_added`", () => {
    expect(
      discoveryCounts(
        makeRun({ channels_added: 2, channels_found: 6, channels_marked_offline: 1 }),
      ),
    ).toEqual({ added: 2, offline: 1, unchanged: 4 });
  });

  test("`channels_found` OFLAYN kanalni ham sanaydi (UI-SPEC §6.3 [TALAB])", () => {
    // 6 kanal sanaldi, 2 tasi oflayn deb belgilandi, yangi qo'shilgani yo'q
    // -> o'zgarishsiz 6 (oflayn kanal ham ro'yxatda BOR).
    expect(
      discoveryCounts(
        makeRun({ channels_added: 0, channels_found: 6, channels_marked_offline: 2 }),
      ),
    ).toEqual({ added: 0, offline: 2, unchanged: 6 });
  });

  test("`null` maydonlar nolga tushadi va formula manfiy chiqmaydi", () => {
    expect(
      discoveryCounts(
        makeRun({
          channels_added: 3,
          channels_found: null,
          channels_marked_offline: null,
        }),
      ),
    ).toEqual({ added: 3, offline: 0, unchanged: 0 });
  });

  test("jumla sharti — o'zgarish bo'lmaganda va FAQAT o'shanda", () => {
    expect(runNoChanges({ added: 0, offline: 0 })).toBe(true);
    expect(runNoChanges({ added: 1, offline: 0 })).toBe(false);
    expect(runNoChanges({ added: 0, offline: 1 })).toBe(false);
  });
});
