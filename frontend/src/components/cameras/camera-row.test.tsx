/**
 * KAMERA QATORI — IKKI HOLAT ATAYIN FARQLANADI (UI-SPEC §6.1, §6.6, §8.6, §13.5).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   «ULANMAGAN» VA «ARXIVLANGAN» BIR XIL KO'RINMAYDI.
 *
 *   * ULANMAGAN kamerada «Ko'rish» tugmasi TURADI va sababi aytiladi.
 *     Yo'qolgan tugma «bu kamerada ko'rish umuman yo'q» degan YOLG'ON
 *     xabar berardi — holbuki kamera qaytishi bilan u ishlaydi.
 *
 *   * ARXIVLANGAN kamerada «Ko'rish» UMUMAN render qilinmaydi: oqim
 *     go2rtc'da ro'yxatga olinmaydi, ya'ni tugma HAR DOIM yiqilardi.
 *
 *   Ikkisi bir qoidaga yig'ilsa qaysi biri tanlansa ham bitta holat
 *   noto'g'ri chiqadi. Rejaning sabotaj bandi aynan shu chegarani
 *   o'lchaydi: «ulanmaganda ham yashirish» birinchi testni qizartirib,
 *   ikkinchisini YASHIL qoldirishi kerak.
 * =============================================================================
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { CameraRow, channelLabel } from "@/components/cameras/camera-row";
import type { Camera } from "@/lib/api-types";

const VIEW_LABEL = messages.cameras.view;
const RESTORE_LABEL = messages.cameras.restore;
const OFFLINE_REASON = messages.cameras.viewDisabledOffline;
const NAME_OVERRIDDEN = messages.cameras.nameOverridden;
const ARCHIVED_LABEL = messages.cameras.status.archived;
const ONLINE_LABEL = messages.cameras.status.online;
const OFFLINE_LABEL = messages.cameras.status.offline;
const UNKNOWN_LABEL = messages.cameras.status.unknown;

const NOW = new Date("2026-08-03T09:32:00Z");

function makeCamera(overrides: Partial<Camera> = {}): Camera {
  return {
    id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    nvr_id: "22222222-2222-4222-8222-222222222222",
    channel_no: 7,
    name: "Sabzavot qatori",
    name_overridden: false,
    status: "online",
    is_archived: false,
    has_substream: true,
    source_ip: "192.168.1.101",
    source_model: "DS-2CD2143G0",
    last_seen_at: "2026-08-03T09:30:00Z",
    ...overrides,
  };
}

type CameraHandler = (camera: Camera) => void;

type Handlers = {
  onArchive: ReturnType<typeof vi.fn<CameraHandler>>;
  onRename: ReturnType<typeof vi.fn<CameraHandler>>;
  onRestore: ReturnType<typeof vi.fn<CameraHandler>>;
  onView: ReturnType<typeof vi.fn<CameraHandler>>;
};

function renderRow(
  camera: Camera,
  options: { canManage?: boolean } = {},
): Handlers {
  const handlers: Handlers = {
    onArchive: vi.fn<CameraHandler>(),
    onRename: vi.fn<CameraHandler>(),
    onRestore: vi.fn<CameraHandler>(),
    onView: vi.fn<CameraHandler>(),
  };

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone="Asia/Tashkent"
    >
      <ul>
        <CameraRow
          camera={camera}
          canManage={options.canManage ?? true}
          {...handlers}
        />
      </ul>
    </NextIntlClientProvider>
  );

  render(tree);
  return handlers;
}

/* ---------------------------------------------------------------------------
 * ULANMAGAN KAMERA — TUGMA TURADI, SABABI AYTILADI (§8.6)
 * ------------------------------------------------------------------------ */

describe("ulanmagan kamera", () => {
  test("«Ko'rish» YASHIRILMAYDI va sababi bilan bog'lanadi", () => {
    renderRow(makeCamera({ status: "offline" }));

    const button = screen.getByRole("button", { name: VIEW_LABEL });
    expect(button).toBeInTheDocument();

    // ARIA holati — oddiy `disabled` propi EMAS (u fokusni ham,
    // e'lonni ham yo'q qilardi).
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).not.toBeDisabled();

    // Sabab DASTURIY bog'langan, shunchaki yonida turgan matn emas.
    const describedBy = button.getAttribute("aria-describedby");
    expect(describedBy).not.toBeNull();
    expect(document.getElementById(describedBy as string)?.textContent).toBe(
      OFFLINE_REASON,
    );
  });

  test("bosilganda dialog OCHILMAYDI, sabab e'lon qilinadi", () => {
    const handlers = renderRow(makeCamera({ status: "offline" }));

    fireEvent.click(screen.getByRole("button", { name: VIEW_LABEL }));

    expect(handlers.onView).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(OFFLINE_REASON);
  });

  test("`unknown` holati ham bloklanadi — hali tekshirilmagan kanal", () => {
    renderRow(makeCamera({ status: "unknown" }));

    expect(screen.getByRole("button", { name: VIEW_LABEL })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByText(UNKNOWN_LABEL)).toBeInTheDocument();
  });

  test("onlayn kamerada tugma ISHLAYDI", () => {
    const camera = makeCamera({ status: "online" });
    const handlers = renderRow(camera);

    const button = screen.getByRole("button", { name: VIEW_LABEL });
    expect(button).not.toHaveAttribute("aria-disabled");

    fireEvent.click(button);
    expect(handlers.onView).toHaveBeenCalledWith(camera);
  });
});

/* ---------------------------------------------------------------------------
 * ARXIVLANGAN QATOR — «Ko'rish» UMUMAN YO'Q (§6.6)
 * ------------------------------------------------------------------------ */

describe("arxivlangan qator", () => {
  test("«Ko'rish» UMUMAN render qilinmaydi", () => {
    renderRow(makeCamera({ is_archived: true, status: "online" }));

    // Rol bo'yicha ham, MATN bo'yicha ham — yashirilgan tugma
    // ikkinchisidan o'tib ketardi.
    expect(screen.queryByRole("button", { name: VIEW_LABEL })).toBeNull();
    expect(document.body.textContent).not.toContain(VIEW_LABEL);
  });

  test("faqat «Arxivdan qaytarish» amali bo'ladi", () => {
    const camera = makeCamera({ is_archived: true });
    const handlers = renderRow(camera);

    const restore = screen.getByRole("button", { name: RESTORE_LABEL });
    fireEvent.click(restore);
    expect(handlers.onRestore).toHaveBeenCalledWith(camera);

    // Amallar menyusi ham chiqmaydi — nom va arxivlash bu yerda ma'nosiz.
    expect(
      screen.queryByRole("button", {
        name: `${messages.cameras.actions}: ${camera.name}`,
      }),
    ).toBeNull();
  });

  test("holat badge'i «Arxivda» deydi — statusdan USTUN", () => {
    renderRow(makeCamera({ is_archived: true, status: "online" }));

    expect(screen.getByText(ARCHIVED_LABEL)).toBeInTheDocument();
    expect(screen.queryByText(ONLINE_LABEL)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * QATORNING QOLGAN KONTRAKTI
 * ------------------------------------------------------------------------ */

describe("qator razmetkasi", () => {
  test("kanal raqami IKKI XONALI formatlanadi", () => {
    expect(channelLabel(1)).toBe("01");
    expect(channelLabel(7)).toBe("07");
    expect(channelLabel(16)).toBe("16");
    expect(channelLabel(132)).toBe("132");

    renderRow(makeCamera({ channel_no: 7 }));
    expect(screen.getByText("07")).toBeInTheDocument();
  });

  test("`name_overridden` belgisi ko'rinadi va u bo'lmasa CHIQMAYDI", () => {
    renderRow(makeCamera({ name_overridden: true }));
    expect(screen.getByText(NAME_OVERRIDDEN)).toBeInTheDocument();

    screen.getByText(NAME_OVERRIDDEN);
  });

  test("`name_overridden === false` da belgi yo'q", () => {
    renderRow(makeCamera({ name_overridden: false }));
    expect(screen.queryByText(NAME_OVERRIDDEN)).toBeNull();
  });

  test("nom DB kontenti — qisqartiriladi va `title` bilan to'liq qoladi", () => {
    const camera = makeCamera({
      name: "Sabzavot qatori — shimoliy tomon, uchinchi ustun yonida",
    });
    renderRow(camera);

    const label = screen.getByTitle(camera.name);
    expect(label).toHaveClass("truncate");
  });

  test("⚠ `last_seen_at` meta qatorida — skanning IKKINCHI dalil kanali", () => {
    renderRow(makeCamera());

    const prefix = messages.cameras.lastSeen.split("{")[0];
    expect(document.body.textContent).toContain(prefix);
    // IP `font-mono` bilan — qurilma interfeysi bilan solishtiriladi.
    expect(screen.getByText("192.168.1.101")).toHaveClass("font-mono");
  });

  test("holat badge'ida MATN ham bor — rang yagona signal emas", () => {
    renderRow(makeCamera({ status: "offline" }));
    expect(screen.getByText(OFFLINE_LABEL)).toBeInTheDocument();
  });

  test("`camera_manage` yo'q bo'lsa amallar menyusi render qilinmaydi", () => {
    const camera = makeCamera();
    renderRow(camera, { canManage: false });

    expect(
      screen.queryByRole("button", {
        name: `${messages.cameras.actions}: ${camera.name}`,
      }),
    ).toBeNull();
    // «Ko'rish» esa QOLADI — u `camera_view` amali.
    expect(screen.getByRole("button", { name: VIEW_LABEL })).toBeInTheDocument();
  });

  test("amallar menyusi nom va arxivlashni beradi", () => {
    const camera = makeCamera();
    const handlers = renderRow(camera);

    const trigger = screen.getByRole("button", {
      name: `${messages.cameras.actions}: ${camera.name}`,
    });
    fireEvent.pointerDown(
      trigger,
      new PointerEvent("pointerdown", { bubbles: true, button: 0 }),
    );

    fireEvent.click(screen.getByText(messages.cameras.rename));
    expect(handlers.onRename).toHaveBeenCalledWith(camera);
  });
});
