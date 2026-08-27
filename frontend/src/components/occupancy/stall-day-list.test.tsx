/**
 * RASTALAR RO'YXATI VA DL-5.
 *
 * =============================================================================
 * ⛔ 1. TARTIB SERVERDAN — KLIENT UNI QAYTA HISOBLAMAYDI.
 *
 *   Fixture ATAYIN alifbo bo'yicha TESKARI: agar komponent `sort()`
 *   qilsa, DOM tartibi kirish tartibidan farq qiladi va test qizaradi.
 *   Bu ikkinchi tartib qoidasining tug'ilishini to'sadi (`/stalls` bilan
 *   ajralib ketish).
 *
 * ⛔ 2. FILTR RO'YXATNI KESADI, XULOSANI EMAS.
 *
 *   `?nocov=1` ostida ro'yxatda faqat qamrovsizlar qoladi; hisoblagichlar
 *   esa boshqa komponentda va ular to'liq kunni ko'rsatishda davom etadi.
 *
 * ⛔ 3. BADGE MATNI QISQARTIRILMAYDI (§10.4).
 *
 *   «Ko'rilmagani uchun bo'sh» va «Qamrov yo'q» — to'liq matn. Ularni
 *   qisqartirish D-19/D-22 ni MATN darajasida yo'q qilardi.
 *
 * ⛔ 4. DL-5 DA PATTA/SUMMA YO'Q va MANBA HUKM BO'LGANDA ko'rinadi.
 *
 *   ⚠ DA'VONING CHEGARASI OCHIQ: DL-5 SLOT QATORLARINI ko'rsatmaydi,
 *     chunki ularni beradigan marshrut YO'Q (`stall-detail-dialog.tsx`
 *     docstringi). Bu test o'sha yo'qlikni «xususiyat» deb tasdiqlamaydi
 *     — u faqat CHIZILGAN narsaning halolligini o'lchaydi.
 * =============================================================================
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  StallDayList,
  visibleStalls,
} from "@/components/occupancy/stall-day-list";
import {
  StallDetailDialog,
  stallSource,
} from "@/components/occupancy/stall-detail-dialog";
import type { OccupancyStallItem } from "@/lib/api-types";

function stall(
  overrides: Partial<OccupancyStallItem> & { stall_id: string },
): OccupancyStallItem {
  return {
    stall_code: "01-A",
    zone_name: "Sabzavot qatori",
    status: "occupied",
    slots: 7,
    occupied_slots: 3,
    human_confirmed: false,
    ...overrides,
  };
}

/** ⚠ ALIFBO BO'YICHA TESKARI — klient saralasa tartib buziladi. */
const ITEMS: readonly OccupancyStallItem[] = [
  stall({ stall_id: "s1", stall_code: "14-C", zone_name: "Zira qatori" }),
  stall({
    stall_id: "s2",
    stall_code: "02-B",
    zone_name: "Meva qatori",
    status: "default_empty",
    occupied_slots: 0,
  }),
  stall({
    stall_id: "s3",
    stall_code: "07-A",
    zone_name: "Go'sht qatori",
    status: "no_coverage",
    occupied_slots: 0,
  }),
];

function renderList(
  options: {
    items?: readonly OccupancyStallItem[];
    noCoverageOnly?: boolean;
    onChange?: (next: boolean) => void;
    onOpen?: (item: OccupancyStallItem) => void;
  } = {},
) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <StallDayList
        items={options.items ?? ITEMS}
        noCoverageOnly={options.noCoverageOnly ?? false}
        onNoCoverageOnlyChange={options.onChange ?? (() => {})}
        onOpen={options.onOpen ?? (() => {})}
      />
    </NextIntlClientProvider>,
  );
}

function renderDialog(item: OccupancyStallItem | null) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <StallDetailDialog item={item} onOpenChange={() => {}} />
    </NextIntlClientProvider>,
  );
}

/* -------------------------------------------------------------------------- */
/* 1. RO'YXAT                                                                 */
/* -------------------------------------------------------------------------- */

describe("rastalar ro'yxati", () => {
  test("⛔ tartib SERVERDAN — klient saralamaydi", () => {
    const { container } = renderList();

    const codes = [...container.querySelectorAll("li")].map(
      (node) => node.querySelector("span")?.textContent,
    );
    expect(codes).toEqual(["14-C", "02-B", "07-A"]);
  });

  test("⛔ badge matnlari TO'LIQ — qisqartirilmagan", () => {
    renderList();

    expect(screen.getByText("Ko'rilmagani uchun bo'sh")).toBeTruthy();
    expect(screen.getByText("Qamrov yo'q")).toBeTruthy();
  });

  test("slot soni NISBAT bo'lib chiziladi va foiz belgisi yo'q", () => {
    const { container } = renderList();

    expect(screen.getByText("7 vaqtdan 3 tasida band")).toBeTruthy();
    expect(container.textContent ?? "").not.toContain("%");
  });

  test("qator ochilganda tanlangan BAND uzatiladi", () => {
    const onOpen = vi.fn();
    const { container } = renderList({ onOpen });

    const first = container.querySelector("li button");
    fireEvent.click(first as HTMLElement);

    expect(onOpen).toHaveBeenCalledWith(
      expect.objectContaining({ stall_id: "s1" }),
    );
  });

  test("⛔ virtualizatsiya kutubxonasi emas, `content-visibility` naqshi", () => {
    /*
     * [O'LCHANDI: M-12] 1000 `<li>` DOM uchun arzon. Bu assert
     * qatorlarning HAMMASI DOM'da ekanini ham tasdiqlaydi — ya'ni
     * klaviatura va brauzer qidiruvi ishlashda davom etadi.
     */
    const { container } = renderList();
    expect(container.querySelectorAll("li").length).toBe(3);
    expect(
      container.querySelector("li")?.className.includes("content-visibility"),
    ).toBe(true);
  });
});

describe("qamrovsizlik filtri", () => {
  test("sof funksiya faqat `no_coverage` ni qoldiradi va SARALAMAYDI", () => {
    expect(visibleStalls(ITEMS, true).map((item) => item.stall_id)).toEqual([
      "s3",
    ]);
    expect(visibleStalls(ITEMS, false)).toBe(ITEMS);
  });

  test("filtr yoqilganda ro'yxatda faqat qamrovsizlar qoladi", () => {
    const { container } = renderList({ noCoverageOnly: true });
    expect(container.querySelectorAll("li").length).toBe(1);
    expect(screen.getByText("07-A")).toBeTruthy();
  });

  test("qamrovsiz rasta yo'q bo'lsa — FAKT, tabrik EMAS", () => {
    const onChange = vi.fn();
    renderList({
      items: [ITEMS[0]],
      noCoverageOnly: true,
      onChange,
    });

    expect(screen.getByText("Qamrovsiz rasta yo'q")).toBeTruthy();
    fireEvent.click(screen.getByText("Filtrni tozalash"));
    expect(onChange).toHaveBeenCalledWith(false);
  });
});

/* -------------------------------------------------------------------------- */
/* 2. MANBA — SOF FUNKSIYA                                                    */
/* -------------------------------------------------------------------------- */

describe("stallSource", () => {
  test("nazoratchi tasdig'i bo'lsa — `human`", () => {
    expect(
      stallSource(stall({ stall_id: "x", human_confirmed: true })),
    ).toBe("human");
  });

  test("`default_empty` — `not_reviewed` (D-19)", () => {
    expect(stallSource(stall({ stall_id: "x", status: "default_empty" }))).toBe(
      "not_reviewed",
    );
  });

  test("dalil bor va inson tegmagan — `system`", () => {
    expect(stallSource(stall({ stall_id: "x", status: "occupied" }))).toBe(
      "system",
    );
    expect(stallSource(stall({ stall_id: "x", status: "empty" }))).toBe(
      "system",
    );
  });

  test("⛔ `no_coverage` — MANBA YO'Q, «Tizim» ham «Ko'rilmadi» ham EMAS", () => {
    /*
     * Qamrovsiz rastada HUKM umuman yo'q. «Tizim» bo'lmagan javobni bor
     * qilardi; «Ko'rilmadi» esa D-22 ni D-19 ga aralashtirardi.
     */
    expect(stallSource(stall({ stall_id: "x", status: "no_coverage" }))).toBe(
      null,
    );
    expect(
      stallSource(
        stall({ stall_id: "x", status: "no_coverage", human_confirmed: true }),
      ),
    ).toBe(null);
  });
});

/* -------------------------------------------------------------------------- */
/* 3. DL-5                                                                    */
/* -------------------------------------------------------------------------- */

describe("DL-5 — rasta tafsiloti", () => {
  test("hukm, manba va slot nisbati ko'rinadi", () => {
    renderDialog(stall({ stall_id: "s1", stall_code: "14-C" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Rasta 14-C")).toBeTruthy();
    expect(within(dialog).getByText("Manba")).toBeTruthy();
    expect(within(dialog).getByText("Tizim")).toBeTruthy();
    expect(within(dialog).getByText("7 vaqtdan 3 tasida band")).toBeTruthy();
  });

  test("⛔ patta/summa ma'nosidagi so'z YO'Q", () => {
    renderDialog(stall({ stall_id: "s1" }));
    const text = (screen.getByRole("dialog").textContent ?? "").toLowerCase();

    /*
     * ⚠ «patta» so'zi QONUNIY va u AYNAN BITTA jumlada — «Patta hisobi
     *   alohida qoidaga ko'ra yuritiladi» (T-05-72 ning to'sig'i).
     *   Taqiqlangani — SUMMA va uning hosilalari.
     */
    for (const forbidden of ["so'm", "som", "summa", "tarif", "qarz"]) {
      expect(text).not.toContain(forbidden);
    }
    expect(text).toContain("patta hisobi alohida qoidaga ko'ra yuritiladi");
  });

  test("⛔ dalil kadrini yuklab olish/ulashish yo'li YO'Q", () => {
    renderDialog(stall({ stall_id: "s1" }));
    const dialog = screen.getByRole("dialog");

    expect(dialog.querySelector("img")).toBeNull();
    expect(dialog.querySelector("a[download]")).toBeNull();
    expect(dialog.querySelector("a")).toBeNull();
  });

  test("qamrovsiz rastada MANBA qatori yo'q, sabab jumlasi BOR", () => {
    renderDialog(stall({ stall_id: "s3", status: "no_coverage" }));
    const dialog = screen.getByRole("dialog");

    expect(within(dialog).queryByText("Manba")).toBeNull();
    expect(
      within(dialog).getByText(
        "Bu rastalarni birorta kamera ko'rmaydi. Ular bo'sh emas — ular haqida ma'lumot yo'q.",
      ),
    ).toBeTruthy();
  });

  test("ko'rilmagan rastada manba «Ko'rilmadi» (D-19)", () => {
    renderDialog(stall({ stall_id: "s2", status: "default_empty" }));
    expect(
      within(screen.getByRole("dialog")).getByText("Ko'rilmadi"),
    ).toBeTruthy();
  });

  test("band yo'q bo'lsa dialog UMUMAN chizilmaydi", () => {
    renderDialog(null);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
