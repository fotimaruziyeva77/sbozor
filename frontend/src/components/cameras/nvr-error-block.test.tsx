/**
 * XATO BLOKI — D-02 NING RENDER DALILI (UI-SPEC §13.5).
 *
 * =============================================================================
 * NEGA BU TEST G-1 DAN KEYIN HAM KERAK:
 *
 *   `scripts/error-codes.test.mjs` (G-1) har kod uchun `errorCause.*` VA
 *   `errorFix.*` kalitlarining uchala tilda MAVJUDLIGINI o'lchaydi. U
 *   kalitlar RO'YXATINI ko'radi, ekranni EMAS: `fixKey` ni render
 *   qatoridan olib tashlash G-1 ni YASHIL qoldiradi va D-02 jimgina
 *   yo'qoladi.
 *
 *   Bu fayl esa aynan RENDER BO'LISHINI o'lchaydi. Ikkovi bir-birining
 *   o'rnini bosmaydi va bu reja tomonidan SABOTAJ bilan tekshirilgan.
 *
 * ⚠ ICU PLATSHOLDERI BO'LGAN MATNLAR bilan solishtirish uchun kalitning
 *   BIRINCHI `{` gacha bo'lgan qismi olinadi. Butun satrni solishtirish
 *   `{minutes}` / `{time}` / `{model}` / `{channel}` bo'lgan to'rtta
 *   kodda ishlamasdi, prefiks esa ularning HAMMASIDA ishlaydi va
 *   matnning aynan shu kalitdan kelganini isbotlaydi.
 * =============================================================================
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { NvrErrorBlock, formatMmSs } from "@/components/cameras/nvr-error-block";
import type { NvrErrorCode } from "@/lib/nvr-errors";
import {
  AUTH_LOCKING_CODES,
  MAX_RAW_DETAIL_CHARS,
  NVR_ERROR_CODES,
  nvrErrorView,
} from "@/lib/nvr-errors";

/** uz-Latn kataloglaridagi AYNAN qiymatlar — test shu faylni yuklaydi. */
const CAUSE_LABEL = messages.cameras.errorCauseLabel;
const FIX_LABEL = messages.cameras.errorFixLabel;
const DETAILS_LABEL = messages.cameras.errorDetails;
const RETRY_LABEL = messages.cameras.retryCheck;
const GENERIC_ERROR = messages.errors.generic;

/** Xom javob namunasi — go2rtc yuzasining izlarini O'Z ICHIGA OLMAYDI (G-6). */
const RAW_SAMPLE =
  '<?xml version="1.0"?><ResponseStatus><statusCode>4</statusCode></ResponseStatus>';

function renderBlock(element: ReactElement): ReturnType<typeof render> {
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      {element}
    </NextIntlClientProvider>,
  );
}

/** Kalit matnining BIRINCHI platsholdergacha bo'lgan qismi. */
function staticPrefix(message: string): string {
  const at = message.indexOf("{");
  return (at === -1 ? message : message.slice(0, at)).trim();
}

function causeText(code: NvrErrorCode): string {
  return messages.cameras.errorCause[code];
}

function fixText(code: NvrErrorCode): string {
  return messages.cameras.errorFix[code];
}

/** Blok — `role="alert"` bilan topiladi (§7.6). */
function block(): HTMLElement {
  return screen.getByRole("alert");
}

/* ---------------------------------------------------------------------------
 * (a) HAR KOD UCHUN SABAB VA TUZATISH — ikkalasi ham render bo'ladi
 * ------------------------------------------------------------------------ */

describe("NvrErrorBlock — sabab VA tuzatish (D-02)", () => {
  test.each(NVR_ERROR_CODES)(
    "%s: ikkala yorliq va ikkala matn ham render bo'ladi",
    (code) => {
      renderBlock(<NvrErrorBlock code={code} detail={null} />);

      const container = block();

      // Yorliqlar — ikkalasi ham bor va bir xil tipografik sinfda.
      const terms = within(container).getAllByRole("term");
      expect(terms.map((node) => node.textContent)).toEqual([
        CAUSE_LABEL,
        FIX_LABEL,
      ]);
      expect(terms[0]?.className).toBe(terms[1]?.className);

      // Matnlar — ikkalasi ham AYNAN shu kalitdan keladi.
      const values = within(container).getAllByRole("definition");
      expect(values).toHaveLength(2);
      expect(values[0]?.textContent).toContain(staticPrefix(causeText(code)));
      expect(values[1]?.textContent).toContain(staticPrefix(fixText(code)));

      // Teng og'irlik razmetkada ham ko'rinadi.
      expect(values[0]?.className).toBe(values[1]?.className);
    },
  );

  test("tuzatish matni sabab jumlasining DUMIGA ulanmagan", () => {
    /*
     * D-02 ning aynan taqiqlagan shakli: «… — NTP xizmatini yoqing».
     * Agar tuzatish sabab `<dd>` ining ichida bo'lsa, u ikkinchi
     * darajali bo'lib qolardi. Ikkita ALOHIDA `<dd>` — o'lchanadigan
     * farq.
     */
    renderBlock(<NvrErrorBlock code="nvr_clock_drift" detail={null} />);

    const values = within(block()).getAllByRole("definition");
    expect(values[0]?.textContent).not.toContain(
      staticPrefix(fixText("nvr_clock_drift")),
    );
  });
});

/* ---------------------------------------------------------------------------
 * (b) AUTH QULFI — retry affordansi RENDER QILINMAYDI (D-03, T-03-63)
 * ------------------------------------------------------------------------ */

describe("NvrErrorBlock — qulflovchi kodlarda qayta urinish YO'Q", () => {
  test.each(AUTH_LOCKING_CODES)(
    "%s: tugma DOM'da umuman yo'q (yashirilgan emas)",
    (code) => {
      const onRetry = vi.fn();
      renderBlock(
        <NvrErrorBlock code={code} detail={{ raw: RAW_SAMPLE }} onRetry={onRetry} />,
      );

      const container = block();

      // Roli bo'yicha ham, matni bo'yicha ham yo'q: `hidden` qilingan
      // tugma birinchi tekshiruvdan o'tib ketardi, ikkinchisidan yo'q.
      expect(
        within(container).queryByRole("button", { name: RETRY_LABEL }),
      ).toBeNull();
      expect(container.textContent).not.toContain(RETRY_LABEL);
      expect(onRetry).not.toHaveBeenCalled();
    },
  );

  test("`device_not_supported` — qulflovchi emas, lekin retry baribir yo'q", () => {
    /*
     * Sabab BOSHQA: qayta urinish hech narsani o'zgartirmaydi, ya'ni
     * tugma FOYDASIZ va u adminni «yana bosib ko'ray» sikliga tashlardi.
     */
    expect(nvrErrorView("device_not_supported")?.retrySafe).toBe(false);

    renderBlock(
      <NvrErrorBlock code="device_not_supported" detail={null} onRetry={vi.fn()} />,
    );

    expect(block().textContent).not.toContain(RETRY_LABEL);
  });

  test("`retrySafe` kodlarda tugma BOR va bosilganda ishlaydi", () => {
    const onRetry = vi.fn();
    renderBlock(
      <NvrErrorBlock code="nvr_clock_drift" detail={null} onRetry={onRetry} />,
    );

    const button = within(block()).getByRole("button", { name: RETRY_LABEL });
    button.click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  test("`onRetry` berilmaganda tugma render qilinmaydi", () => {
    renderBlock(<NvrErrorBlock code="nvr_unreachable" detail={null} />);
    expect(block().textContent).not.toContain(RETRY_LABEL);
  });
});

/* ---------------------------------------------------------------------------
 * (c) NOMA'LUM KOD — `error_detail` KO'RSATILMAYDI (T-03-66)
 * ------------------------------------------------------------------------ */

describe("NvrErrorBlock — noma'lum kod", () => {
  test("`errors.generic` chiqadi va `error_detail` UMUMAN ko'rsatilmaydi", () => {
    renderBlock(
      <NvrErrorBlock
        code="nvr_brand_new_code"
        detail={{ drift_seconds: 4242, raw: RAW_SAMPLE }}
        onRetry={vi.fn()}
      />,
    );

    const container = block();
    expect(container.textContent).toContain(GENERIC_ERROR);
    expect(container.textContent).not.toContain("4242");
    expect(container.textContent).not.toContain("statusCode");
    expect(container.querySelector("details")).toBeNull();
    expect(container.textContent).not.toContain(DETAILS_LABEL);
  });

  test("`code === null` ham noma'lum kod bilan bir xil yo'ldan boradi", () => {
    renderBlock(<NvrErrorBlock code={null} detail={{ raw: RAW_SAMPLE }} />);

    expect(block().textContent).toContain(GENERIC_ERROR);
    expect(block().querySelector("details")).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * (d) `<details>` — FAQAT `raw` bo'lganda (UI-SPEC §7.4)
 * ------------------------------------------------------------------------ */

describe("NvrErrorBlock — texnik tafsilot", () => {
  test("`raw` YO'Q bo'lsa `<details>` render qilinmaydi", () => {
    renderBlock(
      <NvrErrorBlock
        code="nvr_clock_drift"
        detail={{ drift_seconds: 420, server_time: "2026-08-03T10:00:00Z" }}
      />,
    );

    expect(block().querySelector("details")).toBeNull();
  });

  test("`raw` BOR bo'lsa `<details>` yopiq holda render bo'ladi", () => {
    renderBlock(
      <NvrErrorBlock code="nvr_stream_limit" detail={{ raw: RAW_SAMPLE }} />,
    );

    const details = block().querySelector("details");
    expect(details).not.toBeNull();
    expect(details?.open).toBe(false);
    expect(details?.textContent).toContain(DETAILS_LABEL);
    expect(details?.textContent).toContain("statusCode");
  });

  test("xom matn MATN sifatida chiqadi — razmetka sifatida emas", () => {
    renderBlock(
      <NvrErrorBlock
        code="nvr_stream_limit"
        detail={{ raw: "<img src=x onerror=alert(1)>" }}
      />,
    );

    const details = block().querySelector("details");
    expect(details?.querySelector("img")).toBeNull();
    expect(details?.textContent).toContain("<img src=x onerror=alert(1)>");
  });

  test("xom matn 2000 belgidan KESILADI", () => {
    const long = "A".repeat(MAX_RAW_DETAIL_CHARS + 500);
    renderBlock(<NvrErrorBlock code="nvr_stream_limit" detail={{ raw: long }} />);

    const shown = block().querySelector("details p")?.textContent ?? "";
    expect(shown.length).toBe(MAX_RAW_DETAIL_CHARS + 1); // + kesish belgisi
    expect(shown.endsWith("…")).toBe(true);
  });

  test("noma'lum kalit render qilinmaydi", () => {
    renderBlock(
      <NvrErrorBlock
        code="nvr_unreachable"
        detail={{ internal_stack: "app/services/isapi/client.py:214" }}
      />,
    );

    expect(block().textContent).not.toContain("client.py");
  });
});

/* ---------------------------------------------------------------------------
 * Tone, fokus va ICU qiymatlari
 * ------------------------------------------------------------------------ */

describe("NvrErrorBlock — ko'rinish va fokus", () => {
  test("`danger` va `warning` bir-biridan farq qiladi, sariq MATN rangi emas", () => {
    const { unmount } = renderBlock(
      <NvrErrorBlock code="nvr_bad_credentials" detail={null} />,
    );
    expect(block().className).toContain("bg-danger/10");
    unmount();

    renderBlock(<NvrErrorBlock code="nvr_clock_drift" detail={null} />);
    expect(block().className).toContain("bg-warning/20");
    expect(block().className).toContain("text-text");
  });

  test("blok fokuslanadi va `autoFocus` bilan fokusni O'ZIGA oladi", () => {
    renderBlock(<NvrErrorBlock autoFocus code="nvr_unreachable" detail={null} />);

    expect(block().getAttribute("tabindex")).toBe("-1");
    expect(document.activeElement).toBe(block());
  });

  test("`autoFocus` berilmasa fokus KO'CHMAYDI (kashfiyot natijasi yo'li)", () => {
    renderBlock(<NvrErrorBlock code="nvr_unreachable" detail={null} />);
    expect(document.activeElement).toBe(document.body);
  });

  test("`drift_seconds` daqiqaga aylanadi va matnga tushadi", () => {
    renderBlock(
      <NvrErrorBlock code="nvr_clock_drift" detail={{ drift_seconds: 420 }} />,
    );

    const values = within(block()).getAllByRole("definition");
    expect(values[0]?.textContent).toContain("7");
  });

  test("`model` yetishmasa matn buzilmaydi", () => {
    renderBlock(<NvrErrorBlock code="device_not_supported" detail={{}} />);

    const values = within(block()).getAllByRole("definition");
    expect(values[0]?.textContent).toContain("—");
  });
});

describe("formatMmSs", () => {
  test.each([
    [0, "00:00"],
    [1000, "00:01"],
    [61_000, "01:01"],
    [1_800_000, "30:00"],
    [-5000, "00:00"],
  ])("%i ms -> %s", (input, expected) => {
    expect(formatMmSs(input)).toBe(expected);
  });
});
