/**
 * DL-2 — QATOR BO'YICHA BO'LISH: NOMUVOFIQLIKDA HECH NIMA QO'SHILMAYDI.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (4-fazadagi «qisman to'ldirish yo'q» qoidasi):
 *
 *   RASTALAR SONI POLIGONLAR SONIGA TENG BO'LMASA — NOL POLIGON
 *   QO'SHILADI, YARIMTA EMAS.
 *
 *   Qisman natija «qaysilari qo'shildi?» savolini tug'dirardi va uni
 *   faqat kadrni sanab tekshirish bilan hal qilib bo'lardi — ya'ni
 *   yordamchi tejagan vaqtni tekshirish qaytarib olardi.
 *
 * ⚠ IKKI RAD ETISH SABABI ALOHIDA O'LCHANADI. `vertex-mismatch`
 *   TEPALARNI tenglashtirishni talab qiladi, `count-mismatch` esa
 *   butunlay boshqa tekshiruvni. Ikkalasi bir xil xabar bersa, admin
 *   nima qilishni bilmasdi.
 *
 * ⛔ Bu yordamchi SOF GEOMETRIYA: u kadrga umuman qaramaydi. «Detektor
 *    topgan qutilarni zona qilish» ATAYIN qurilmagan — u aylanma mantiq
 *    bo'lardi (§6.7, §16.2).
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  planRowSplit,
  RowAssistDialog,
  rowTargets,
} from "@/components/camera-zones/row-assist-dialog";
import type { RowTarget } from "@/components/camera-zones/row-assist-dialog";
import { ZoneDetailDialog } from "@/components/camera-zones/zone-detail-dialog";
import { ZoneToolbar } from "@/components/camera-zones/zone-toolbar";
import type { MapZone } from "@/lib/api-types";
import { MAX_ZONES_PER_CAMERA } from "@/lib/zone-geometry";
import type { Poly } from "@/lib/zone-geometry";

const SQUARE: Poly = [
  [0.1, 0.4],
  [0.2, 0.4],
  [0.2, 0.6],
  [0.1, 0.6],
];

const FAR_SQUARE: Poly = [
  [0.8, 0.4],
  [0.9, 0.4],
  [0.9, 0.6],
  [0.8, 0.6],
];

/** Uch tepali — tepa soni AYNAN teng bo'lishi sharti uchun. */
const TRIANGLE: Poly = [
  [0.8, 0.4],
  [0.9, 0.4],
  [0.85, 0.6],
];

const STALL_IDS = [
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222",
  "33333333-3333-4333-8333-333333333333",
  "44444444-4444-4444-8444-444444444444",
  "55555555-5555-4555-8555-555555555555",
];

/** `GET /stalls/map` — kataklar `code_sort` tartibida (2-fazadan). */
const MAP: readonly MapZone[] = [
  {
    id: "99999999-9999-4999-8999-999999999999",
    name: "Sabzavot qatori",
    cells: STALL_IDS.map((id, index) => ({
      code: `14-${String.fromCharCode(65 + index)}`,
      has_vendor: false,
      id,
      status: "active" as const,
    })),
  },
];

function targetsOf(codes: readonly string[]): readonly RowTarget[] {
  return codes.map((code) => ({
    code,
    id: MAP[0].cells.find((cell) => cell.code === code)?.id ?? code,
  }));
}

/* ---------------------------------------------------------------------------
 * ORADAGI RASTALAR — TARTIB MANBAI `code_sort`
 * ------------------------------------------------------------------------ */

describe("rowTargets", () => {
  test("oradagi rastalar qaytadi — uchlari O'ZI KIRMAYDI", () => {
    const { skipped, targets } = rowTargets({
      firstStallId: STALL_IDS[0],
      lastStallId: STALL_IDS[4],
      occupiedStallIds: [],
      zones: MAP,
    });

    expect(targets.map((target) => target.code)).toEqual([
      "14-B",
      "14-C",
      "14-D",
    ]);
    expect(skipped).toBe(0);
  });

  test("tanlov tartibi teskari bo'lsa ham natija BIR XIL", () => {
    const forward = rowTargets({
      firstStallId: STALL_IDS[0],
      lastStallId: STALL_IDS[4],
      occupiedStallIds: [],
      zones: MAP,
    });
    const backward = rowTargets({
      firstStallId: STALL_IDS[4],
      lastStallId: STALL_IDS[0],
      occupiedStallIds: [],
      zones: MAP,
    });

    expect(backward.targets).toEqual(forward.targets);
  });

  test("⛔ ALLAQACHON zonasi bor rasta CHIQARILADI va SANALADI", () => {
    /*
     * Jimgina ustiga yozish avvalgi tahrirlarni yo'q qilardi va admin
     * buni faqat keyingi hisobotda sezardi.
     */
    const { skipped, targets } = rowTargets({
      firstStallId: STALL_IDS[0],
      lastStallId: STALL_IDS[4],
      occupiedStallIds: [STALL_IDS[2]],
      zones: MAP,
    });

    expect(targets.map((target) => target.code)).toEqual(["14-B", "14-D"]);
    expect(skipped).toBe(1);
  });

  test("yonma-yon rastalarda oraliq BO'SH (nazorat)", () => {
    const { targets } = rowTargets({
      firstStallId: STALL_IDS[0],
      lastStallId: STALL_IDS[1],
      occupiedStallIds: [],
      zones: MAP,
    });
    expect(targets).toEqual([]);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ YOKI HAMMASI, YOKI HECH NIMA
 * ------------------------------------------------------------------------ */

describe("planRowSplit", () => {
  test("teng tepali ikki poligon oraliqni to'liq to'ldiradi", () => {
    const plan = planRowSplit({
      firstPolygon: SQUARE,
      lastPolygon: FAR_SQUARE,
      targets: targetsOf(["14-B", "14-C", "14-D"]),
    });

    expect(plan.ok).toBe(true);
    if (!plan.ok) return;
    expect(plan.polygons).toHaveLength(3);
    // Har oraliq poligon AYNAN o'z rastasiga bog'lanadi.
    expect(plan.stallIds).toHaveLength(3);
    // Tepa soni saqlanadi — interpolyatsiya tepama-tepa.
    for (const polygon of plan.polygons) {
      expect(polygon).toHaveLength(SQUARE.length);
    }
  });

  test("⛔ TEPA SONI TENG BO'LMASA — hech nima qo'shilmaydi", () => {
    const plan = planRowSplit({
      firstPolygon: SQUARE,
      lastPolygon: TRIANGLE,
      targets: targetsOf(["14-B", "14-C", "14-D"]),
    });

    expect(plan).toEqual({ ok: false, reason: "vertex-mismatch" });
  });

  test("oraliq bo'sh bo'lsa AYRIM sabab qaytadi", () => {
    /*
     * «Oraliq yo'q» — XATO EMAS, u qatorning uchlari yonma-yon degani.
     * Uni `vertex-mismatch` bilan bir xil ko'rsatish adminni tepalarni
     * sanashga majburlardi.
     */
    expect(
      planRowSplit({
        firstPolygon: SQUARE,
        lastPolygon: FAR_SQUARE,
        targets: [],
      }),
    ).toEqual({ ok: false, reason: "no-targets" });
  });
});

/* ---------------------------------------------------------------------------
 * DIALOG — SONLAR, XATO VA «BO'LISH»
 * ------------------------------------------------------------------------ */

function renderDialog(
  overrides: Partial<Parameters<typeof RowAssistDialog>[0]> = {},
) {
  const onApply = vi.fn();
  const onPreview = vi.fn();

  render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <RowAssistDialog
        firstLabel="14-A"
        firstPolygon={SQUARE}
        firstStallId={STALL_IDS[0]}
        lastLabel="14-E"
        lastPolygon={FAR_SQUARE}
        lastStallId={STALL_IDS[4]}
        occupiedStallIds={[]}
        onApply={onApply}
        onOpenChange={() => {}}
        onPreview={onPreview}
        open
        zones={MAP}
        {...overrides}
      />
    </NextIntlClientProvider>,
  );

  return { onApply, onPreview };
}

describe("dialog", () => {
  test("oradagi rastalar soni va hosil bo'ladigan zona soni TENG ko'rinadi", () => {
    renderDialog();

    expect(screen.getByText(messages.cameraZones.rowBetween)).toBeInTheDocument();
    expect(screen.getByText(messages.cameraZones.rowPreview)).toBeInTheDocument();
    // Uchta rasta -> uchta zona: ikkala son ham «3».
    expect(screen.getAllByText("3")).toHaveLength(2);
  });

  test("⛔ tepa soni teng bo'lmaganda XATO chiqadi va `[Bo'lish]` ishlamaydi", () => {
    const { onApply } = renderDialog({ lastPolygon: TRIANGLE });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(messages.cameraZones.rowVertexMismatch);

    const apply = screen.getByRole("button", {
      name: messages.cameraZones.rowApply,
    });
    expect(apply).toHaveAttribute("aria-disabled", "true");

    fireEvent.click(apply);
    // ⛔ HECH NIMA QO'SHILMADI.
    expect(onApply).not.toHaveBeenCalled();
  });

  test("to'g'ri holatda `[Bo'lish]` natijani MUHARRIRGA beradi", () => {
    const { onApply } = renderDialog();

    fireEvent.click(
      screen.getByRole("button", { name: messages.cameraZones.rowApply }),
    );

    expect(onApply).toHaveBeenCalledTimes(1);
    const result = onApply.mock.calls[0][0] as {
      polygons: readonly Poly[];
      stallIds: readonly string[];
    };
    expect(result.polygons).toHaveLength(3);
    expect(result.stallIds).toEqual([STALL_IDS[1], STALL_IDS[2], STALL_IDS[3]]);
  });

  test("o'tkazib yuborilgan rastalar SANALADI", () => {
    renderDialog({ occupiedStallIds: [STALL_IDS[2]] });

    expect(
      screen.getByText(
        messages.cameraZones.rowSkipped.replace("{count}", "1"),
      ),
    ).toBeInTheDocument();
  });

  test("oldindan ko'rish poligonlari kadrga UZATILADI", () => {
    const { onPreview } = renderDialog();

    expect(onPreview).toHaveBeenCalled();
    const last = onPreview.mock.calls[onPreview.mock.calls.length - 1][0] as
      readonly Poly[];
    expect(last).toHaveLength(3);
  });

  test("dialog yopiq bo'lsa oldindan ko'rish BO'SH (kadr toza qoladi)", () => {
    const { onPreview } = renderDialog({ open: false });

    const last = onPreview.mock.calls[onPreview.mock.calls.length - 1][0] as
      readonly Poly[];
    expect(last).toEqual([]);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ QURILMAGAN IMKONIYATLAR — ULARNING YO'QLIGI HAM O'LCHANADI
 *
 * ⚠ NEGA SHU FAYLDA: 3-vazifaning yagona komponent test fayli shu. DL-1
 *   va asboblar qatori uchun alohida fayl ochish rejaning fayl
 *   to'plamidan chiqib ketardi, ularning YO'Q xususiyatlarini esa
 *   umuman o'lchamaslik «darvoza bor» degan yolg'on da'vo bo'lardi.
 * ------------------------------------------------------------------------ */

describe("⛔ «Tiklash» yo'li MAVJUD EMAS (§6.6, §16.2)", () => {
  test("matn katalogida `cameraZones.restore*` kaliti YO'Q", () => {
    /*
     * Eski versiyani tiklash YANGI versiya yaratardi va tarixda
     * «3-versiya aslida 1-versiyaning nusxasi» degan ikki ma'noli qator
     * paydo bo'lardi — «bu rasta qaysi kontur bo'yicha o'lchangan?»
     * savoli javobsiz qolardi.
     *
     * ⚠ MATNDAN BOSHLANADI, KODDAN EMAS: so'z copy'ga kirsa, keyingi
     *   ijrochi uni AMALGA OSHIRISHGA urinardi (G-18 ning aynan
     *   mantiqi).
     */
    const keys = Object.keys(messages.cameraZones);
    expect(keys.filter((key) => key.startsWith("restore"))).toEqual([]);
  });

  test("render qilingan DL-1 da qaytarish tugmasi TOPILMAYDI", () => {
    render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneDetailDialog
          onAssignStall={() => {}}
          onDelete={() => {}}
          onOpenChange={() => {}}
          open
          stallCode="14-A"
          stallId={STALL_IDS[0]}
          version={3}
          zones={MAP}
        />
      </NextIntlClientProvider>,
    );

    // Versiya raqami KO'RINADI — u kontekst, tugma esa yo'q.
    expect(
      screen.getByText(messages.cameraZones.version.replace("{version}", "3")),
    ).toBeInTheDocument();

    for (const label of Object.values(messages.cameraZones)) {
      if (typeof label !== "string") continue;
      if (!/tikla/iu.test(label)) continue;
      expect(screen.queryByRole("button", { name: label })).toBeNull();
    }
  });

  test("saqlanmagan zonada versiya badge'i UMUMAN chizilmaydi", () => {
    render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneDetailDialog
          onAssignStall={() => {}}
          onDelete={() => {}}
          onOpenChange={() => {}}
          open
          stallCode={null}
          stallId={null}
          version={null}
          zones={MAP}
        />
      </NextIntlClientProvider>,
    );

    // «Versiya 0» degan son YO'Q narsani BOR deb ko'rsatardi.
    expect(screen.queryByText(/^Versiya/u)).toBeNull();
  });
});

describe("⛔ AKSENT BUDJETI — asboblarda aksent fonli tugma YO'Q (§10.3)", () => {
  test("beshala asbob ham `secondary`", () => {
    const { container } = render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneToolbar
          canCopy
          canRedo
          canRowSplit
          canUndo
          onAnnounce={() => {}}
          onCopyZone={() => {}}
          onCreateZone={() => {}}
          onOpenRowSplit={() => {}}
          onRedo={() => {}}
          onUndo={() => {}}
          zoneCount={4}
        />
      </NextIntlClientProvider>,
    );

    expect(screen.getAllByRole("button")).toHaveLength(5);
    /*
     * ⚠ SINF NOMI BILAN o'lchanadi: sahifadagi YAGONA aksent fonli tugma
     *   `[Zonalarni saqlash]` va u muharrirda. Asboblardan birortasi
     *   aksent bo'lsa, ko'z saqlashdan chalg'irdi.
     */
    expect(container.querySelectorAll(".bg-accent")).toHaveLength(0);
  });

  test("chegaraga yetganda `[Yangi zona]` `aria-disabled` va SABAB e'lon qilinadi", () => {
    const onAnnounce = vi.fn();
    const onCreateZone = vi.fn();

    render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneToolbar
          canCopy={false}
          canRedo={false}
          canRowSplit={false}
          canUndo={false}
          onAnnounce={onAnnounce}
          onCopyZone={() => {}}
          onCreateZone={onCreateZone}
          onOpenRowSplit={() => {}}
          onRedo={() => {}}
          onUndo={() => {}}
          zoneCount={MAX_ZONES_PER_CAMERA}
        />
      </NextIntlClientProvider>,
    );

    const create = screen.getByRole("button", {
      name: messages.cameraZones.newZone,
    });
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create).not.toBeDisabled();

    fireEvent.click(create);
    expect(onCreateZone).not.toHaveBeenCalled();
    expect(onAnnounce).toHaveBeenCalledWith(
      messages.cameraZones.maxZones.replace(
        "{max}",
        String(MAX_ZONES_PER_CAMERA),
      ),
    );
  });

  test("ikki zona tanlanmaganda `[Qator bo'yicha bo'lish]` sabab AYTADI", () => {
    const onAnnounce = vi.fn();
    const onOpenRowSplit = vi.fn();

    render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        timeZone="Asia/Tashkent"
      >
        <ZoneToolbar
          canCopy={false}
          canRedo={false}
          canRowSplit={false}
          canUndo={false}
          onAnnounce={onAnnounce}
          onCopyZone={() => {}}
          onCreateZone={() => {}}
          onOpenRowSplit={onOpenRowSplit}
          onRedo={() => {}}
          onUndo={() => {}}
          zoneCount={2}
        />
      </NextIntlClientProvider>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: messages.cameraZones.rowSplit }),
    );

    expect(onOpenRowSplit).not.toHaveBeenCalled();
    expect(onAnnounce).toHaveBeenCalledWith(messages.cameraZones.rowNeedsTwo);
  });
});
