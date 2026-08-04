/**
 * VAQTLAR MUHARRIRI — CHEGARA, DUBLIKAT VA ORALIQ (§4.6, §12.3).
 *
 * =============================================================================
 * BU FAYLNING UCH MARKAZIY DA'VOSI VA ULAR MUSTAQIL:
 *
 *   1. CHEGARADA `aria-disabled`, `disabled` EMAS. `disabled` tugma fokus
 *      OLMAYDI va skrinrider uni umuman O'QIMAYDI — ya'ni «nega
 *      bosilmayapti?» savoliga javob beradigan joy qolmaydi. Chegara
 *      ko'rsatkichi (`7 / 12`) esa foydalanuvchi unga YETGUNICHA
 *      ko'rinadi.
 *
 *   2. DUBLIKAT RAD ETILADI VA AYTILADI. Jimgina yutish «qo'shdim,
 *      ko'rinmadi» tuyg'usini berardi va admin uni yana bir marta
 *      kiritib ko'rardi.
 *
 *   3. ⛔ ORALIQ CHEGARADAN OSHSA HECH NIMA QO'SHILMAYDI. Qisman
 *      to'ldirish «qaysilari qo'shildi?» savolini tug'dirardi va admin
 *      ro'yxatni qo'lda solishtirishga majbur bo'lardi. Bu da'vo
 *      DUBLIKAT da'vosidan MUSTAQIL: birini buzish ikkinchisini
 *      qizartirmaydi — rejaning sabotaj bandi aynan shu chegarani
 *      o'lchaydi.
 * =============================================================================
 *
 * ⚠ KLIENTDAGI CHEGARA — QULAYLIK, XAVFSIZLIK CHEGARASI EMAS
 *   (§4.6 [TALAB]). Haqiqiy shift serverda
 *   (`Settings.snapshot_max_times_per_day`, 04-05/04-09) va u DevTools
 *   bilan chetlab o'tilmaydi. Bu yerdagi testlar UI KUTILMASINI
 *   o'lchaydi, tenant xavfsizligini emas.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import type { ReactElement } from "react";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  expandRange,
  MAX_TIMES_PER_DAY,
  mergeTimes,
  SlotEditor,
} from "@/components/snapshots/slot-editor";

const ADD_LABEL = messages.snapshots.addTime;
const TIME_LABEL = messages.snapshots.time;
const RANGE_APPLY = messages.snapshots.rangeApply;
const RANGE_FROM = messages.snapshots.rangeFrom;
const RANGE_TO = messages.snapshots.rangeTo;
const RANGE_STEP = messages.snapshots.rangeStep;
const RANGE_FILL = messages.snapshots.rangeFill;
const LIMIT_REACHED = messages.snapshots.slotLimitReached.replace(
  "{max}",
  String(MAX_TIMES_PER_DAY),
);
const DUPLICATE = messages.snapshots.slotDuplicate;
const RANGE_TOO_MANY = messages.snapshots.rangeTooMany;
const RANGE_INVALID = messages.snapshots.rangeInvalid;
const TIMES_LEGEND = messages.snapshots.times;

/** Boshqariladigan komponent — holat sinov qobig'ida yashaydi. */
function Harness({ initial }: { initial: readonly string[] }) {
  const [times, setTimes] = useState<readonly string[]>(initial);
  return <SlotEditor onChange={setTimes} value={times} />;
}

function renderEditor(initial: readonly string[]): ReturnType<typeof render> {
  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <Harness initial={initial} />
    </NextIntlClientProvider>
  );
  return render(tree);
}

/** `<input type="time">` jsdom'da `getByLabelText` orqali topiladi. */
function typeTime(label: string, value: string): void {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

/** `06:00`, `06:30`, … — chegarani to'ldiradigan ro'yxat. */
function times(count: number): string[] {
  return Array.from({ length: count }, (_, index) => {
    const total = 6 * 60 + index * 30;
    const hh = String(Math.floor(total / 60)).padStart(2, "0");
    const mm = String(total % 60).padStart(2, "0");
    return `${hh}:${mm}`;
  });
}

/* ---------------------------------------------------------------------------
 * SOF FUNKSIYALAR — oraliq va birlashtirish
 * ------------------------------------------------------------------------ */

describe("oraliq generatorining sof funksiyalari", () => {
  test("`expandRange` ikkala chetni ham QO'SHADI", () => {
    expect(expandRange("06:00", "07:00", 30)).toEqual([
      "06:00",
      "06:30",
      "07:00",
    ]);
    expect(expandRange("06:00", "06:00", 30)).toEqual(["06:00"]);
  });

  test("`mergeTimes` BIRLASHTIRADI, almashtirmaydi va dublikatni tashlaydi", () => {
    // Qo'lda kiritilgan 16:00 ni jimgina yo'qotish — §4.6 ning aniq taqig'i.
    expect(mergeTimes(["16:00", "06:00"], ["06:00", "06:30"])).toEqual([
      "06:00",
      "06:30",
      "16:00",
    ]);
  });
});

/* ---------------------------------------------------------------------------
 * 1-DA'VO — CHEGARA
 * ------------------------------------------------------------------------ */

describe("12 lik chegara (§4.6)", () => {
  test("ko'rsatkich chegaraga YETGUNICHA ko'rinadi", () => {
    renderEditor(times(3));

    const usage = messages.snapshots.timesUsage
      .replace("{used}", "3")
      .replace("{max}", String(MAX_TIMES_PER_DAY));
    expect(screen.getByText(usage)).toBeInTheDocument();
  });

  test("⛔ chegarada `aria-disabled` — `disabled` EMAS", () => {
    renderEditor(times(MAX_TIMES_PER_DAY));

    const add = screen.getByRole("button", { name: ADD_LABEL });
    expect(add).toHaveAttribute("aria-disabled", "true");
    // `disabled` fokus olmaydi va e'lon qilinmaydi (§12.3).
    expect(add).not.toBeDisabled();
  });

  test("chegarada bosish HECH NIMA qo'shmaydi va SABABNI e'lon qiladi", () => {
    renderEditor(times(MAX_TIMES_PER_DAY));

    typeTime(TIME_LABEL, "22:00");
    fireEvent.click(screen.getByRole("button", { name: ADD_LABEL }));

    expect(screen.queryByText("22:00")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent(LIMIT_REACHED);
  });
});

/* ---------------------------------------------------------------------------
 * 2-DA'VO — DUBLIKAT
 * ------------------------------------------------------------------------ */

describe("dublikat va tartib", () => {
  test("dublikat RAD ETILADI va sababi aytiladi", () => {
    renderEditor(["06:00", "07:00"]);

    typeTime(TIME_LABEL, "07:00");
    fireEvent.click(screen.getByRole("button", { name: ADD_LABEL }));

    expect(screen.getByRole("status")).toHaveTextContent(DUPLICATE);
    // Jimgina yutish «qo'shdim, ko'rinmadi» tuyg'usini berardi.
    expect(screen.getAllByText("07:00")).toHaveLength(1);
  });

  test("yangi vaqt O'SISH tartibiga QO'YILADI, oxiriga emas", () => {
    renderEditor(["07:00", "08:00"]);

    typeTime(TIME_LABEL, "06:30");
    fireEvent.click(screen.getByRole("button", { name: ADD_LABEL }));

    const chips = screen
      .getAllByRole("listitem")
      .map((item) => item.textContent?.slice(0, 5));
    expect(chips).toEqual(["06:30", "07:00", "08:00"]);
  });

  test("vaqtni olib tashlash mumkin", () => {
    renderEditor(["06:00", "07:00"]);

    fireEvent.click(
      screen.getByRole("button", {
        name: `${messages.snapshots.removeTime} 07:00`,
      }),
    );

    expect(screen.queryByText("07:00")).toBeNull();
    expect(screen.getByText("06:00")).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * 3-DA'VO — ORALIQ TO'LDIRISH
 * ------------------------------------------------------------------------ */

describe("oraliq bo'yicha to'ldirish", () => {
  function fill(from: string, to: string, step: string): void {
    typeTime(RANGE_FROM, from);
    typeTime(RANGE_TO, to);
    fireEvent.change(screen.getByLabelText(RANGE_STEP), {
      target: { value: step },
    });
    fireEvent.click(screen.getByRole("button", { name: RANGE_APPLY }));
  }

  test("natija mavjud vaqtlar bilan BIRLASHTIRILADI", () => {
    renderEditor(["16:00"]);

    fill("06:00", "07:00", "30");

    const chips = screen
      .getAllByRole("listitem")
      .map((item) => item.textContent?.slice(0, 5));
    // Qo'lda kiritilgan 16:00 JOYIDA qoladi — almashtirish uni jimgina
    // yo'qotardi.
    expect(chips).toEqual(["06:00", "06:30", "07:00", "16:00"]);
  });

  test("⛔ chegaradan oshsa HECH NIMA qo'shilmaydi — qisman to'ldirish YO'Q", () => {
    renderEditor(["06:00"]);

    // 06:00–18:00 / 15 daqiqa = 49 vaqt, chegara esa 12.
    fill("06:00", "18:00", "15");

    expect(screen.getByRole("status")).toHaveTextContent(RANGE_TOO_MANY);
    // Ro'yxat AYNAN o'zgarmagan: bitta chip.
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("06:00")).toBeInTheDocument();
  });

  test("tugash boshlanishdan oldin bo'lsa sabab aytiladi", () => {
    renderEditor(["06:00"]);

    fill("08:00", "07:00", "30");

    expect(screen.getByRole("status")).toHaveTextContent(RANGE_INVALID);
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });
});

/* ---------------------------------------------------------------------------
 * SEMANTIKA (§12.2)
 * ------------------------------------------------------------------------ */

describe("guruhlash semantikasi", () => {
  test("«Vaqtlar» `fieldset`/`legend`, oraliq generatori esa `role='group'`", () => {
    const { container } = renderEditor(["06:00"]);

    const legend = screen.getByText(TIMES_LEGEND);
    expect(legend.tagName).toBe("LEGEND");
    expect(legend.closest("fieldset")).not.toBeNull();

    const group = screen.getByRole("group", { name: RANGE_FILL });
    expect(group).toBeInTheDocument();
    /*
     * ⛔ ICHMA-ICH `fieldset` EMAS (§12.2): uch boshqaruv + tugma bitta
     *    amalni tashkil qiladi va ular allaqachon «Vaqtlar» guruhi
     *    ichida. Ikki daraja skrinriderda ikki marta e'lon qilinardi va
     *    hech qanday foyda bermasdi.
     */
    expect(group.tagName).not.toBe("FIELDSET");
    expect(container.querySelectorAll("fieldset")).toHaveLength(1);
  });
});
