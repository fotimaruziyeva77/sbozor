/**
 * KADR YUZASI — SVG, VA U OCHIQLIK DARAXTIDA YO'Q.
 *
 * =============================================================================
 * BU FAYLNING UCHTA DA'VOSI:
 *
 *   1. ⛔ HAR ZONA UCHUN AYNAN BITTA `<polygon>`. Bu «bir zona jimgina
 *      chizilmay qoldi» sinfini ushlaydigan eng arzon invariant: sanoq
 *      farq qilsa, kadrda ko'rinmaydigan zona bor demakdir va admin uni
 *      YO'Q deb o'ylab, qaytadan chizardi.
 *
 *   2. ⛔ KONTEYNER `aria-hidden="true"` — butun ochiqlik ro'yxatda
 *      (§13.4). Ikkalasi ham ochiq bo'lsa skrinrider har poligonni IKKI
 *      MARTA e'lon qilardi.
 *
 *   3. ⛔⛔ `frame_width`/`frame_height` PIKSEL O'LCHAMI SIFATIDA
 *      ISHLATILMAYDI. Bu 05-06 SUMMARY ning to'g'ridan-to'g'ri
 *      ogohlantirishi: o'sha ustunlar `draft()` ning KICHRAYTIRILGAN
 *      dekodi (1280×720 uchun taxminan 320×180) va ularni koordinataga
 *      ko'paytirish HAR KOORDINATADA to'rt barobar xato berardi.
 *      Test buni LITERAL o'lchaydi: 480×270 kadrda x=0,5 tepasi 500 da
 *      chiziladi, 240 da EMAS.
 *
 * ⚠ SUDRASH MATEMATIKASI SOF FUNKSIYADA (`clientToNormalized`) va u shu
 *   yerda alohida o'lchanadi: jsdom `getBoundingClientRect()` ni har doim
 *   nol qaytaradi, ya'ni komponent ichida qolgan matematika UMUMAN
 *   o'lchanmasdi — «bo'sh to'plam ustida yashil» sinfining aynan o'zi.
 * =============================================================================
 */
import { fireEvent, render } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import {
  clientToNormalized,
  midpointOf,
  pointsAttr,
  VIEW_WIDTH,
  viewHeight,
  ZoneCanvas,
} from "@/components/camera-zones/zone-canvas";
import type { CanvasZone } from "@/components/camera-zones/zone-canvas";
import { denormalize, MAX_VERTICES_PER_ZONE } from "@/lib/zone-geometry";
import type { Poly } from "@/lib/zone-geometry";

/**
 * ⚠ AYNAN 05-06 NING SEED QIYMATLARI: `DECODED_WIDTH = 480`,
 *   `DECODED_HEIGHT = 270`. Bular HAQIQIY kadr o'lchami EMAS —
 *   `draft()` natijasi sinfida, ishlab chiqarishda ham shunday.
 */
const FRAME_WIDTH = 480;
const FRAME_HEIGHT = 270;

const SQUARE: Poly = [
  [0.4, 0.4],
  [0.6, 0.4],
  [0.6, 0.6],
  [0.4, 0.6],
];

function makeZone(id: string, polygon: Poly = SQUARE): CanvasZone {
  return { id, invalid: false, label: id, polygon };
}

function renderCanvas(
  zones: readonly CanvasZone[],
  overrides: Partial<Parameters<typeof ZoneCanvas>[0]> = {},
) {
  return render(
    <ZoneCanvas
      aspectHeight={FRAME_HEIGHT}
      aspectWidth={FRAME_WIDTH}
      focusedVertex={null}
      frameHref="blob:test-frame"
      onBackgroundPress={() => {}}
      onInsertMidpoint={() => {}}
      onMoveVertex={() => {}}
      onSelectZone={() => {}}
      preview={[]}
      selectedZoneId={null}
      zones={zones}
      {...overrides}
    />,
  );
}

/* ---------------------------------------------------------------------------
 * 1. POLIGON SANOG'I
 * ------------------------------------------------------------------------ */

describe("SVG yuzasi", () => {
  test("⛔ `<polygon>` soni ro'yxatdagi zonalar soniga TENG", () => {
    const { container } = renderCanvas([
      makeZone("a"),
      makeZone("b"),
      makeZone("c"),
    ]);

    expect(container.querySelectorAll("polygon")).toHaveLength(3);
  });

  test("nol zonada `<polygon>` ham yo'q (nazorat)", () => {
    const { container } = renderCanvas([]);
    expect(container.querySelectorAll("polygon")).toHaveLength(0);
    // Kadr esa BOR — zonasiz kamera bo'sh ekran EMAS (Z-3).
    expect(container.querySelector("image")).not.toBeNull();
  });

  test("⛔ konteyner `aria-hidden='true'` — ochiqlik daraxtida YO'Q", () => {
    const { container } = renderCanvas([makeZone("a")]);
    const wrapper = container.querySelector("[aria-hidden='true']");

    expect(wrapper).not.toBeNull();
    expect(wrapper?.querySelector("svg")).not.toBeNull();
  });

  test("kadr `<image href>` bilan qo'yiladi va `crossOrigin` YO'Q (§14.2)", () => {
    const { container } = renderCanvas([]);
    const image = container.querySelector("image");

    expect(image?.getAttribute("href")).toBe("blob:test-frame");
    // Boshqa manba yo'q — atribut uning borligini anglatardi.
    expect(image?.hasAttribute("crossorigin")).toBe(false);
  });

  test("kadr hali kelmagan bo'lsa `<image>` UMUMAN chizilmaydi", () => {
    const { container } = renderCanvas([makeZone("a")], { frameHref: null });
    expect(container.querySelector("image")).toBeNull();
    // Poligonlar esa joyida — «zonalar hech qachon almashmaydi» (§6.3).
    expect(container.querySelectorAll("polygon")).toHaveLength(1);
  });
});

/* ---------------------------------------------------------------------------
 * 2. ⛔⛔ `frame_width` PIKSEL O'LCHAMI EMAS — LITERAL O'LCHOV
 * ------------------------------------------------------------------------ */

describe("⛔ kadr o'lchami NISBAT sifatida ishlatiladi, piksel sifatida EMAS", () => {
  test("`viewBox` kengligi DOIMIY, balandligi faqat nisbatdan", () => {
    expect(VIEW_WIDTH).toBe(1000);
    // 480×270 = 16:9 -> 1000 × 562,5. YAXLITLANMAYDI.
    expect(viewHeight(FRAME_WIDTH, FRAME_HEIGHT)).toBe(562.5);
  });

  test("⛔ x=0,5 tepasi 500 da chiziladi — 240 da EMAS", () => {
    /*
     * 240 — aynan `0.5 * frame_width` va u NOTO'G'RI javob.
     * `frame_width` `draft()` ning kichraytirilgan dekodi, ya'ni undan
     * piksel geometriyasi qurish har koordinatada TO'RT BAROBAR xato
     * berardi (05-06 SUMMARY, «Keyingi rejalar uchun ochiq bandlar»).
     */
    const attr = pointsAttr([[0.5, 0.5]], viewHeight(FRAME_WIDTH, FRAME_HEIGHT));

    expect(attr).toBe("500,281.25");
    expect(attr).not.toContain("240");
    expect(attr).not.toContain("135");
  });

  test("⛔ `denormalize()` bu yerda ISHLATILMAYDI — va farqi o'lchanadi", () => {
    /*
     * `denormalize` KADR PIKSELLARI uchun: u butun songa yaxlitlaydi va
     * uning yaxlitlash sharti serverning `_round_half_up()` i bilan
     * juftlashtirilgan. Render birliklari BOSHQA masshtabda, ya'ni
     * uni bu yerda chaqirish ikki xatoni bir vaqtda kiritardi:
     * noto'g'ri masshtab VA keraksiz aniqlik yo'qotishi.
     */
    expect(denormalize([0.5, 0.5], FRAME_WIDTH, FRAME_HEIGHT)).toEqual([
      240, 135,
    ]);
    expect(pointsAttr([[0.5, 0.5]], viewHeight(FRAME_WIDTH, FRAME_HEIGHT))).toBe(
      "500,281.25",
    );
  });

  test("⚠ 4:3 kadr ham AYNAN o'z nisbatini oladi (nazorat)", () => {
    // 640×480 -> 1000 × 750. Konteynerning `aspect-ratio` si ham shu.
    expect(viewHeight(640, 480)).toBe(750);
  });

  test("konteynerning nisbati kadrnikiga TENG — letterbox tuzatishi kerak emas", () => {
    const { container } = renderCanvas([]);
    const wrapper = container.querySelector<HTMLElement>(
      "[aria-hidden='true']",
    );
    expect(wrapper?.style.aspectRatio).toBe(`${FRAME_WIDTH} / ${FRAME_HEIGHT}`);
  });
});

/* ---------------------------------------------------------------------------
 * 3. SUDRASH — `setPointerCapture`
 * ------------------------------------------------------------------------ */

describe("tepani sudrash", () => {
  test("⛔ tepada `pointerdown` -> `setPointerCapture` CHAQIRILADI", () => {
    const { container } = renderCanvas([makeZone("a")], {
      selectedZoneId: "a",
    });

    const target = container.querySelector<SVGCircleElement>(
      "[data-testid='vertex-target']",
    );
    expect(target).not.toBeNull();

    const capture = vi.fn();
    Object.assign(target as SVGCircleElement, { setPointerCapture: capture });

    fireEvent.pointerDown(target as SVGCircleElement, { pointerId: 7 });

    /*
     * USHLASH MAJBURIY: usiz kursor tez harakatda SVG'dan chiqib
     * ketganda `pointermove` boshqa elementga tushardi va tepa yarim
     * yo'lda «tushib qolardi».
     */
    expect(capture).toHaveBeenCalledWith(7);
  });

  test("ushlagichlar FAQAT tanlangan poligonda chiziladi (§6.4)", () => {
    const { container } = renderCanvas([makeZone("a"), makeZone("b")], {
      selectedZoneId: "a",
    });

    // Bitta poligonning to'rt tepasi — sakkiz emas.
    expect(
      container.querySelectorAll("[data-testid='vertex-target']"),
    ).toHaveLength(4);
  });

  test("hech nima tanlanmaganda ushlagich UMUMAN yo'q (nazorat)", () => {
    const { container } = renderCanvas([makeZone("a")]);
    expect(
      container.querySelectorAll("[data-testid='vertex-target']"),
    ).toHaveLength(0);
  });

  test("`clientToNormalized` — sof va nol o'lchamda `null`", () => {
    const rect = { height: 200, left: 10, top: 20, width: 400 };

    expect(clientToNormalized(rect, 210, 120)).toEqual([0.5, 0.5]);
    expect(clientToNormalized(rect, 10, 20)).toEqual([0, 0]);

    /*
     * ⛔ NOL KENGLIK — `null`, nol emas: `0/0` `NaN` berib, `clamp01` ni
     *    `RangeError` bilan yiqitardi. Bu holat real — element hali
     *    joylashtirilmagan bo'lishi mumkin.
     */
    expect(clientToNormalized({ ...rect, width: 0 }, 10, 20)).toBeNull();
    expect(clientToNormalized({ ...rect, height: 0 }, 10, 20)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * QIRRA O'RTASI — `insertMidpoint` DAN HOSILA
 * ------------------------------------------------------------------------ */

describe("qirra o'rtasidagi ushlagich", () => {
  test("ushlagich AYNAN qo'yiladigan nuqtada turadi", () => {
    // 0,4 va 0,6 orasidagi qirra -> 0,5.
    expect(midpointOf(SQUARE, 0)).toEqual([0.5, 0.4]);
    // Oxirgi qirra YOPILUVCHI: oxirgi tepadan birinchisiga.
    expect(midpointOf(SQUARE, 3)).toEqual([0.4, 0.5]);
  });

  test("⛔ chegara to'lganda ushlagich UMUMAN chizilmaydi", () => {
    /*
     * 05-03 ning havola kontrakti: rad etilgan amal AYNAN o'sha
     * havolani qaytaradi. Ushlagich chizilsa, u BOSIB BO'LMAYDIGAN
     * nishon bo'lardi — yolg'on va'da.
     */
    const full: Poly = Array.from(
      { length: MAX_VERTICES_PER_ZONE },
      (_, index): [number, number] => [0.1 + index * 0.05, 0.5],
    );
    expect(midpointOf(full, 0)).toBeNull();

    const { container } = renderCanvas([makeZone("a", full)], {
      selectedZoneId: "a",
    });
    expect(
      container.querySelectorAll("[data-testid='midpoint-handle']"),
    ).toHaveLength(0);
    // Tepa ushlagichlari esa JOYIDA — chegara faqat QO'SHISHNI to'sadi.
    expect(
      container.querySelectorAll("[data-testid='vertex-target']"),
    ).toHaveLength(MAX_VERTICES_PER_ZONE);
  });
});

/* ---------------------------------------------------------------------------
 * DL-2 OLDINDAN KO'RISH — PUNKTIR, «HALI MAVJUD EMAS»
 * ------------------------------------------------------------------------ */

describe("oldindan ko'rish", () => {
  test("punktir chiziq bilan chiziladi va `<polygon>` SANOG'IGA kirmaydi", () => {
    const { container } = renderCanvas([makeZone("a")], {
      preview: [SQUARE, SQUARE],
    });

    // Sanoq invarianti buzilmaydi: bitta zona -> bitta `<polygon>`.
    expect(container.querySelectorAll("polygon")).toHaveLength(1);
    // Oldindan ko'rish — `polyline`, ya'ni «hali yopilmagan/mavjud emas».
    expect(container.querySelectorAll("polyline")).toHaveLength(2);
    expect(
      container.querySelector("polyline")?.getAttribute("stroke-dasharray"),
    ).toBe("4 4");
  });
});
