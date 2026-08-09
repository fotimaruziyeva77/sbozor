/**
 * ZONALAR RO'YXATI — OCHIQLIKNING ASOSIY YUZASI (§13.4).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   POLIGONNI KLAVIATURA BILAN TAHRIRLASH MUMKIN — VA U MUQOBIL EMAS.
 *
 *   Kadr ustiga bosish klaviatura bilan BAJARILMAYDI. Chizish faqat
 *   sichqoncha bilan bo'lsa, klaviatura foydalanuvchisi bu ekrandan
 *   BUTUNLAY chiqarib tashlanadi — WCAG 2.1.1 ning to'g'ridan-to'g'ri
 *   buzilishi. Shuning uchun ochiqlik daraxti ro'yxatda, SVG esa uning
 *   ko'zgusi.
 *
 *   ⛔ IKKINCHI DA'VO — BITTA TAB TO'XTASHI (WCAG 2.1.2, T-05-41):
 *      60 zona × 12 tepa = 780 gacha fokuslanadigan element. Har biri
 *      alohida to'xtash bo'lsa, ro'yxat KLAVIATURA TUZOG'IGA aylanardi.
 *
 *   ⛔ UCHINCHI DA'VO — 44 px. SVG'dagi nishon 22 px va u WCAG 2.5.8 ning
 *      minimumiga yetmaydi (ongli chegirma). Kompensatsiya MAJBURIY va u
 *      aynan shu yerda; o'lcham muzokara qilinmaydi.
 *
 * ⚠ NUDGE QADAMI RENDER PIKSELIDA o'lchanadi va test uni AYNAN
 *   tekshiradi: 720 px balandlikdagi yuzada `ArrowUp` normalangan
 *   koordinatani AYNAN `1/720` ga o'zgartiradi. Doimiy normalangan qadam
 *   keng kadrda katta, tor kadrda kichik siljish berardi va «bir bosish =
 *   bir piksel» va'dasi yolg'on bo'lardi.
 * =============================================================================
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test, vi } from "vitest";
import type { Mock } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  invalidZoneIds,
  nudgedPoint,
  ZoneList,
} from "@/components/camera-zones/zone-list";
import type { ListZone } from "@/components/camera-zones/zone-list";
import { MAX_ZONES_PER_CAMERA } from "@/lib/zone-geometry";
import type { Poly, Pt } from "@/lib/zone-geometry";

/** Kadr yuzasining EKRANDAGI o'lchami — nudge qadamining maxraji. */
const RENDER_WIDTH = 1280;
const RENDER_HEIGHT = 720;

const SQUARE: Poly = [
  [0.4, 0.4],
  [0.6, 0.4],
  [0.6, 0.6],
  [0.4, 0.6],
];

const TRIANGLE: Poly = [
  [0.4, 0.4],
  [0.6, 0.4],
  [0.5, 0.6],
];

/** ⛔ «Qum soati» — o'zi bilan kesishgan to'rtburchak (05-03 fixture'i). */
const BOWTIE: Poly = [
  [0.2, 0.2],
  [0.8, 0.8],
  [0.8, 0.2],
  [0.2, 0.8],
];

function makeZone(overrides: Partial<ListZone> = {}): ListZone {
  return {
    id: "zone-a",
    needsReview: false,
    polygon: SQUARE,
    stallCode: "14-A",
    ...overrides,
  };
}

/**
 * ⚠ IMZOLAR OCHIQ YOZILADI, `ReturnType<typeof vi.fn>` EMAS.
 *
 * Bo'sh `vi.fn()` har qanday argumentni qabul qiladigan tip beradi, ya'ni
 * `onMoveVertex` ning IKKINCHI argumenti (tepa koordinatasi) tip
 * tekshiruvidan butunlay chiqib ketardi — aynan shu argument bu faylning
 * markaziy o'lchovi (`camera-row.test.tsx:59-65` naqshi).
 */
type Handlers = {
  onAnnounce: Mock<(message: string) => void>;
  onCreateZone: Mock<() => void>;
  onDeleteVertex: Mock<(index: number) => void>;
  onFocusVertex: Mock<(index: number | null) => void>;
  onInsertVertex: Mock<(index: number) => void>;
  onMoveVertex: Mock<(index: number, point: Pt) => void>;
  onSelectZone: Mock<(zoneId: string | null) => void>;
};

function renderList(
  zones: readonly ListZone[],
  options: {
    focusedVertex?: number | null;
    renderHeight?: number;
    renderWidth?: number;
    selectedZoneId?: string | null;
  } = {},
): Handlers {
  const handlers: Handlers = {
    onAnnounce: vi.fn<(message: string) => void>(),
    onCreateZone: vi.fn<() => void>(),
    onDeleteVertex: vi.fn<(index: number) => void>(),
    onFocusVertex: vi.fn<(index: number | null) => void>(),
    onInsertVertex: vi.fn<(index: number) => void>(),
    onMoveVertex: vi.fn<(index: number, point: Pt) => void>(),
    onSelectZone: vi.fn<(zoneId: string | null) => void>(),
  };

  render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <ZoneList
        focusedVertex={options.focusedVertex ?? null}
        maxZones={MAX_ZONES_PER_CAMERA}
        renderHeight={options.renderHeight ?? RENDER_HEIGHT}
        renderWidth={options.renderWidth ?? RENDER_WIDTH}
        selectedZoneId={options.selectedZoneId ?? null}
        zones={zones}
        {...handlers}
      />
    </NextIntlClientProvider>,
  );

  return handlers;
}

/**
 * Tepa tugmasi — NOMI BO'YICHA, indeks bo'yicha emas.
 *
 * ⚠ To'liq ochiqlik nomi `«Tepa 2 · 0,318 · 0,441»` (§13.4): koordinata
 *   UCH XONAGACHA va u nomning bir qismi. Regexp aynan shu shaklni
 *   talab qiladi, ya'ni koordinata nomdan tushib qolsa test QIZARADI —
 *   bu «tepa qayerda?» savoliga javob beradigan yagona kanal.
 */
function vertexButton(index: number): HTMLElement {
  return screen.getByRole("button", {
    name: new RegExp(`^Tepa ${index} · \\d,\\d{3} · \\d,\\d{3}$`, "u"),
  });
}

/* ---------------------------------------------------------------------------
 * SEMANTIKA — `<ul>`/`<li>`, UMUMIY ARIA ROLI YO'Q
 * ------------------------------------------------------------------------ */

describe("semantika", () => {
  test("⛔ har poligon `<li>` sifatida mavjud", () => {
    const { container } = render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneList
          focusedVertex={null}
          maxZones={MAX_ZONES_PER_CAMERA}
          onAnnounce={() => {}}
          onCreateZone={() => {}}
          onDeleteVertex={() => {}}
          onFocusVertex={() => {}}
          onInsertVertex={() => {}}
          onMoveVertex={() => {}}
          onSelectZone={() => {}}
          renderHeight={RENDER_HEIGHT}
          renderWidth={RENDER_WIDTH}
          selectedZoneId={null}
          zones={[
            makeZone({ id: "a", stallCode: "14-A" }),
            makeZone({ id: "b", stallCode: "14-B" }),
            makeZone({ id: "c", stallCode: "14-C" }),
          ]}
        />
      </NextIntlClientProvider>,
    );

    expect(container.querySelectorAll("li")).toHaveLength(3);
  });

  test("⛔ MATRITSA/DARAXT ROLI QO'YILMAGAN — native semantika yetadi", () => {
    /*
     * `capture-grid.tsx:16-32` ning AYNAN o'sha qarori: native
     * `<ul>`/`<li>` skrinriderda kuchliroq va u indeks atributlarini
     * qo'lda yuritishni talab qilmaydi — 780 elementda bu ikkinchi
     * haqiqat manbai bo'lardi.
     */
    const { container } = render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneList
          focusedVertex={0}
          maxZones={MAX_ZONES_PER_CAMERA}
          onAnnounce={() => {}}
          onCreateZone={() => {}}
          onDeleteVertex={() => {}}
          onFocusVertex={() => {}}
          onInsertVertex={() => {}}
          onMoveVertex={() => {}}
          onSelectZone={() => {}}
          renderHeight={RENDER_HEIGHT}
          renderWidth={RENDER_WIDTH}
          selectedZoneId="zone-a"
          zones={[makeZone()]}
        />
      </NextIntlClientProvider>,
    );

    expect(
      container.querySelectorAll(
        "[role='grid'], [role='tree'], [role='gridcell'], [role='treeitem'], [role='row']",
      ),
    ).toHaveLength(0);
  });

  test("tanlanganda tepalar RO'YXAT bo'lib ochiladi", () => {
    renderList([makeZone()], { selectedZoneId: "zone-a" });

    // To'rt tepa -> to'rtta «Tepa N» tugmasi.
    for (const index of [1, 2, 3, 4]) {
      expect(
        vertexButton(index),
      ).toBeInTheDocument();
    }
  });

  test("tanlanmagan zonaning tepalari OCHILMAYDI (nazorat)", () => {
    renderList([makeZone()]);
    expect(screen.queryByRole("button", { name: /^Tepa 1 ·/u })).toBeNull();
  });

  test("⛔ har tepa tugmasi TO'LIQ 44 px (22 px SVG nishonining kompensatsiyasi)", () => {
    renderList([makeZone()], { selectedZoneId: "zone-a" });

    /*
     * ⚠ `getBoundingClientRect()` ISHLATILMAYDI: jsdom layout
     *   hisoblamaydi va u har doim 0 qaytaradi — bunday assert BO'SH
     *   TO'PLAM ustida yashil bo'lardi (`capture-grid.test.tsx:326-333`
     *   da o'lchangan sinf). O'rniga sinf tokenlari sanaladi.
     */
    const vertex = vertexButton(1);
    for (const token of ["min-h-11", "min-w-11"]) {
      expect(vertex.className.split(/\s+/)).toContain(token);
    }
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ ROVING TABINDEX — BITTA TAB TO'XTASHI
 * ------------------------------------------------------------------------ */

describe("roving tabindex (WCAG 2.1.2)", () => {
  test("⛔ butun ro'yxatda AYNAN BITTA `tabIndex={0}` element bor", () => {
    renderList(
      [
        makeZone({ id: "a", stallCode: "14-A" }),
        makeZone({ id: "b", stallCode: "14-B" }),
        makeZone({ id: "c", stallCode: "14-C" }),
      ],
      { focusedVertex: 2, selectedZoneId: "b" },
    );

    const stops = screen
      .getAllByRole("button")
      .filter((node) => node.tabIndex === 0);

    expect(stops).toHaveLength(1);
    // Fokusdagi tepa to'xtashni oladi — ro'yxat va kadr BIR XIL indeksda.
    expect(stops[0]).toBe(vertexButton(3));
  });

  test("hech nima tanlanmaganda BIRINCHI zona to'xtashni oladi", () => {
    renderList([
      makeZone({ id: "a", stallCode: "14-A" }),
      makeZone({ id: "b", stallCode: "14-B" }),
    ]);

    const stops = screen
      .getAllByRole("button")
      .filter((node) => node.tabIndex === 0);
    expect(stops).toHaveLength(1);
  });

  test("⚠ «o'chirish» tugmasi tab to'xtashi EMAS — u sichqoncha yo'li", () => {
    /*
     * Klaviatura yo'li — fokusdagi tepada `Delete`. Ikkalasi ham
     * mavjud, ya'ni WCAG 2.1.1 bajariladi, lekin to'xtash bittaligicha
     * qoladi (2.1.2).
     */
    renderList([makeZone()], { focusedVertex: 0, selectedZoneId: "zone-a" });

    const remove = screen.getByRole("button", {
      name: `${messages.cameraZones.removeVertex}: Tepa 1`,
    });
    expect(remove.tabIndex).toBe(-1);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ O'Q TUGMALARI SILJITADI — 1 PIKSEL, `Shift` BILAN 10
 * ------------------------------------------------------------------------ */

describe("klaviatura bilan siljitish", () => {
  test("⛔ `ArrowUp` AYNAN 1 render pikselga siljitadi", () => {
    const handlers = renderList([makeZone()], {
      focusedVertex: 0,
      selectedZoneId: "zone-a",
    });

    fireEvent.keyDown(vertexButton(1), {
      key: "ArrowUp",
    });

    expect(handlers.onMoveVertex).toHaveBeenCalledWith(0, [
      0.4,
      0.4 - 1 / RENDER_HEIGHT,
    ]);
  });

  test("⛔ `Shift+ArrowUp` AYNAN 10 render pikselga siljitadi", () => {
    const handlers = renderList([makeZone()], {
      focusedVertex: 0,
      selectedZoneId: "zone-a",
    });

    fireEvent.keyDown(vertexButton(1), {
      key: "ArrowUp",
      shiftKey: true,
    });

    expect(handlers.onMoveVertex).toHaveBeenCalledWith(0, [
      0.4,
      0.4 - 10 / RENDER_HEIGHT,
    ]);
  });

  test("gorizontal qadam KENGLIKDAN olinadi — balandlikdan emas", () => {
    /*
     * ⚠ FIXTURE ASOSLI: `RENDER_WIDTH !== RENDER_HEIGHT`, aks holda test
     *   ikkala maxrajni ham qanoatlantirib, jimgina yashil qolardi.
     */
    expect(RENDER_WIDTH).not.toBe(RENDER_HEIGHT);

    const handlers = renderList([makeZone()], {
      focusedVertex: 0,
      selectedZoneId: "zone-a",
    });

    fireEvent.keyDown(vertexButton(1), {
      key: "ArrowRight",
    });

    expect(handlers.onMoveVertex).toHaveBeenCalledWith(0, [
      0.4 + 1 / RENDER_WIDTH,
      0.4,
    ]);
  });

  test("⛔ o'lchanmagan yuzada tepa BURCHAKKA SAKRAMAYDI", () => {
    /*
     * `1/0` = `Infinity`; `clamp01` uni 0 yoki 1 ga aylantirib, tepani
     * burchakka tashlardi — ya'ni bitta tugma bosish poligonni buzardi.
     */
    expect(nudgedPoint([0.4, 0.4], "ArrowUp", false, 0, 0)).toBeNull();

    const handlers = renderList([makeZone()], {
      focusedVertex: 0,
      renderHeight: 0,
      renderWidth: 0,
      selectedZoneId: "zone-a",
    });
    fireEvent.keyDown(vertexButton(1), {
      key: "ArrowUp",
    });

    expect(handlers.onMoveVertex).not.toHaveBeenCalled();
  });

  test("`PageUp`/`PageDown` FOKUSNI ko'chiradi (o'qlar siljitishga band)", () => {
    const handlers = renderList([makeZone()], {
      focusedVertex: 1,
      selectedZoneId: "zone-a",
    });

    const vertex = vertexButton(2);
    fireEvent.keyDown(vertex, { key: "PageDown" });
    expect(handlers.onFocusVertex).toHaveBeenCalledWith(2);

    fireEvent.keyDown(vertex, { key: "PageUp" });
    expect(handlers.onFocusVertex).toHaveBeenCalledWith(0);

    fireEvent.keyDown(vertex, { key: "Home" });
    expect(handlers.onFocusVertex).toHaveBeenCalledWith(0);

    fireEvent.keyDown(vertex, { key: "End" });
    expect(handlers.onFocusVertex).toHaveBeenCalledWith(3);
  });

  test("`Enter` qirra o'rtasiga tepa qo'shadi", () => {
    const handlers = renderList([makeZone()], {
      focusedVertex: 1,
      selectedZoneId: "zone-a",
    });

    fireEvent.keyDown(vertexButton(2), {
      key: "Enter",
    });
    expect(handlers.onInsertVertex).toHaveBeenCalledWith(1);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ 3 TEPADA O'CHIRISH `aria-disabled`
 * ------------------------------------------------------------------------ */

describe("uchinchi tepa — quyi chegara", () => {
  test("⛔ 3 tepada «o'chirish» `aria-disabled` bo'ladi", () => {
    renderList([makeZone({ polygon: TRIANGLE })], {
      focusedVertex: 0,
      selectedZoneId: "zone-a",
    });

    const remove = screen.getByRole("button", {
      name: `${messages.cameraZones.removeVertex}: Tepa 1`,
    });
    expect(remove).toHaveAttribute("aria-disabled", "true");
    /*
     * ⚠ `disabled` ATRIBUTI QO'YILMAYDI (§13.3): u fokus olmaydi va
     *   skrinrider uni o'qimaydi — «nega bosilmayapti?» javobsiz
     *   qolardi.
     */
    expect(remove).not.toBeDisabled();
  });

  test("4 tepada o'chirish ISHLAYDI (nazorat)", () => {
    const handlers = renderList([makeZone({ polygon: SQUARE })], {
      focusedVertex: 0,
      selectedZoneId: "zone-a",
    });

    const remove = screen.getByRole("button", {
      name: `${messages.cameraZones.removeVertex}: Tepa 1`,
    });
    expect(remove).not.toHaveAttribute("aria-disabled");

    fireEvent.click(remove);
    expect(handlers.onDeleteVertex).toHaveBeenCalledWith(0);
  });

  test("3 tepada `Delete` HECH NIMA qilmaydi va SABAB e'lon qilinadi", () => {
    const handlers = renderList([makeZone({ polygon: TRIANGLE })], {
      focusedVertex: 0,
      selectedZoneId: "zone-a",
    });

    fireEvent.keyDown(vertexButton(1), {
      key: "Delete",
    });

    expect(handlers.onDeleteVertex).not.toHaveBeenCalled();
    expect(handlers.onAnnounce).toHaveBeenCalledWith(
      messages.cameraZones.minVertices,
    );
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ SAQLASHNI TO'SUVCHI POLIGON
 * ------------------------------------------------------------------------ */

describe("kesishgan poligon saqlashni to'sadi", () => {
  test("`invalidZoneIds` aynan kesishganini qaytaradi", () => {
    expect(
      invalidZoneIds([
        makeZone({ id: "ok", polygon: SQUARE }),
        makeZone({ id: "bowtie", polygon: BOWTIE }),
      ]),
    ).toEqual(["bowtie"]);
  });

  test("⛔ SABAB `role='alert'` da va u AYBLANUVCHIGA bog'lanadi", () => {
    renderList([makeZone({ id: "bowtie", polygon: BOWTIE })]);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(
      messages.cameraZones.errorCause.zone_polygon_self_intersecting,
    );
    // D-02: sabab YOLG'IZ kelmaydi — nima qilish kerak ham bor.
    expect(alert).toHaveTextContent(
      messages.cameraZones.errorFix.zone_polygon_self_intersecting,
    );

    /*
     * ⚠ `aria-invalid` ISHLATILMAYDI — u `button` rolida
     *   QO'LLAB-QUVVATLANMAYDI (`jsx-a11y/role-supports-aria-props`
     *   bilan o'lchandi). To'g'ri shakl — `aria-describedby`: fokus
     *   ayblanuvchi zonaga tushganda sabab O'QILADI.
     */
    const zoneButton = screen.getByRole("button", { name: /14-A/u });
    expect(zoneButton.getAttribute("aria-describedby")).toBe(alert.id);
  });

  test("kesishmagan poligonda ogohlantirish YO'Q (nazorat)", () => {
    renderList([makeZone({ polygon: SQUARE })]);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(invalidZoneIds([makeZone({ polygon: SQUARE })])).toEqual([]);
  });
});

/* ---------------------------------------------------------------------------
 * Z-3 — BO'SH HOLAT RO'YXAT ICHIDA
 * ------------------------------------------------------------------------ */

describe("bo'sh holat (Z-3)", () => {
  test("zona yo'q bo'lsa RO'YXAT ICHIDA bo'sh holat va yaratish yo'li chiqadi", () => {
    const handlers = renderList([]);

    expect(
      screen.getByText(messages.cameraZones.emptyNoZones),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: messages.cameraZones.newZone }),
    );
    expect(handlers.onCreateZone).toHaveBeenCalledTimes(1);
  });

  test("hisoblagich `18 / 60` naqshida ko'rinadi", () => {
    renderList([makeZone({ id: "a" }), makeZone({ id: "b" })]);
    expect(screen.getByText(`2 / ${MAX_ZONES_PER_CAMERA}`)).toBeInTheDocument();
  });

  test("ko'rinadigan ko'rsatma DOIM turadi (§13.4)", () => {
    renderList([makeZone()]);
    expect(screen.getByText(messages.cameraZones.moveHint)).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * RASTASIZ VA «TEKSHIRISH KERAK» YORLIQLARI
 * ------------------------------------------------------------------------ */

describe("zona yorliqlari", () => {
  test("rastasiz zona yorliq oladi va SAQLANADIGAN ro'yxatda qoladi", () => {
    renderList([makeZone({ stallCode: null })]);
    expect(
      screen.getAllByText(messages.cameraZones.noStall).length,
    ).toBeGreaterThan(0);
  });

  test("nisbat farqi FAKT sifatida ko'rsatiladi (§6.8)", () => {
    renderList([makeZone({ needsReview: true })]);
    expect(
      screen.getByText(messages.cameraZones.needsReview),
    ).toBeInTheDocument();
  });
});
