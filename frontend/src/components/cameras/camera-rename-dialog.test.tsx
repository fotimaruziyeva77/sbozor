/**
 * KAMERA NOMI DIALOGI — ⛔ BOSILADIGAN, LEKIN JIM TUGMA (F-4).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI VA UNING MEXANIKASI:
 *
 *   Bo'sh nom bilan «Saqlash» bosilganda SABAB ko'rinadi. Ilgari:
 *     * tugma `aria-disabled` bilan «yopilgan» edi, lekin `Button` ning
 *       CSS'i FAQAT native `disabled` ni biladi
 *       (`disabled:pointer-events-none`) — ya'ni tugma haqiqatda
 *       BOSILARDI va ko'rinishi ham o'zgarmasdi;
 *     * bosilganda `save()` `if (invalid) return` bilan JIMGINA chiqib
 *       ketardi: so'rov yo'q, xato yo'q, dialog ochiq.
 *   Ikkinchi yolg'on birinchisidan ham yomonroq: `aria-disabled` skrinriderga
 *   «yopiq» deydi, sichqonchaga esa «ochiq». Bu ikki foydalanuvchiga IKKI
 *   XIL ilova ko'rsatish demakdir.
 *
 *   Etalon — `create-user-dialog.tsx`: `useForm` + `zodResolver`, xabar
 *   `${id}-error` bilan ko'rinadi, tugma `disabled={<yuborilyapti>}`.
 * =============================================================================
 *
 * ⚠ T3 — MEXANIKANING O'ZI o'lchanadi, natijasi emas: tugma HAQIQIY submit
 *   tugmasi bo'lishi va bo'sh nomda `aria-disabled` bilan YOPILMASLIGI
 *   kerak. Usiz tuzatish «xabar chiqaraman, lekin tugmani baribir
 *   aria-disabled qilaman» shaklida qaytib kelardi.
 *
 * ⚠ T5 — CHEGARA: «NVR qurilmasidagi nomga qaytarish» ghost tugmasi formani
 *   YUBORMAYDI (`Button` ning standarti `type="button"`) va o'z yo'lini
 *   saqlaydi.
 *
 * DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import messages from "../../../messages/uz-Latn.json";
import { CameraRenameDialog } from "@/components/cameras/camera-rename-dialog";
import type { Camera } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const CAMERA_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const CAMERA_PATH = `/cameras/${CAMERA_ID}`;

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const SAVE = messages.common.save;
const REQUIRED = messages.errors.required;
const NAME_LABEL = messages.cameras.nameLabel;
const RESET_LABEL = messages.cameras.resetName;

const CAMERA: Camera = {
  id: CAMERA_ID,
  nvr_id: "22222222-2222-4222-8222-222222222222",
  channel_no: 7,
  name: "Sabzavot qatori",
  name_overridden: true,
  status: "online",
  is_archived: false,
  has_substream: true,
  source_ip: "192.168.1.101",
  source_model: "DS-2CD2143G0",
  last_seen_at: "2026-08-16T05:00:00Z",
};

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "55555555-5555-4555-8555-555555555555",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderDialog(): { onSaved: ReturnType<typeof vi.fn> } {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const onSaved = vi.fn();

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <CameraRenameDialog
            camera={CAMERA}
            onOpenChange={vi.fn()}
            onSaved={onSaved}
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
  return { onSaved };
}

function nameInput(): HTMLElement {
  return screen.getByLabelText(NAME_LABEL);
}

function saveButton(): HTMLElement {
  return screen.getByRole("button", { name: SAVE });
}

/**
 * Xato blokining idsi — maydonning O'Z idsidan hosila.
 *
 * `useId()` ATAYIN qayta hisoblanmaydi: forma `key={camera.id}` bilan
 * montaj qilinadi va React bergan id test uchun oldindan noma'lum. Shuning
 * uchun id DOM'dan o'qiladi — `Field` ning `${id}-error` konvensiyasi
 * (`ui/field.tsx`) shu bilan o'lchanadi.
 */
function nameErrorElement(): HTMLElement | null {
  const id = nameInput().getAttribute("id");
  return id === null ? null : document.getElementById(`${id}-error`);
}

function clearName(): void {
  fireEvent.change(nameInput(), { target: { value: "" } });
}

function renameCalls(): unknown[][] {
  return apiFetch.mock.calls.filter((args: unknown[]) => args[0] === CAMERA_PATH);
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
});

afterEach(() => {
  clearSession();
});

/* ---------------------------------------------------------------------------
 * ⛔ T1/T2 — BO'SH NOM SABABINI AYTADI VA SO'ROV YUBORMAYDI
 * ------------------------------------------------------------------------ */

describe("bo'sh nom bilan saqlash", () => {
  test("⛔ `errors.required` EKRANDA ko'rinadi", async () => {
    renderDialog();
    clearName();

    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(nameErrorElement()).not.toBeNull();
    });
    expect(nameErrorElement()?.textContent).toBe(REQUIRED);
  });

  test("⛔ `PATCH /cameras/{id}` YUBORILMAYDI", async () => {
    renderDialog();
    clearName();

    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(nameErrorElement()).not.toBeNull();
    });
    expect(renameCalls()).toHaveLength(0);
  });

  test("⛔ xabar maydonga DASTURIY bog'lanadi — izoh bilan BIRGA", async () => {
    renderDialog();
    clearName();

    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(nameErrorElement()).not.toBeNull();
    });

    const input = nameInput();
    const id = input.getAttribute("id");
    expect(input).toHaveAttribute("aria-invalid", "true");

    /*
     * Izoh (`${id}-hint`) YO'QOLMAYDI: u `name_overridden` ning ma'nosini
     * tushuntiradi va usiz admin qayta skanerlashdan qo'rqadi (§6.5).
     * Naqsh `tariff-dialog.tsx` dan — xato va izoh BIRGA e'lon qilinadi.
     */
    const describedBy = input.getAttribute("aria-describedby") ?? "";
    expect(describedBy.split(/\s+/u)).toContain(`${id}-error`);
    expect(describedBy.split(/\s+/u)).toContain(`${id}-hint`);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ T3 — TUGMANING MEXANIKASI: HAQIQIY SUBMIT, YOLG'ON QULF EMAS
 * ------------------------------------------------------------------------ */

describe("saqlash tugmasining mexanikasi", () => {
  test("⛔ `type=\"submit\"` va bo'sh nomda `aria-disabled` bilan YOPILMAYDI", () => {
    renderDialog();
    clearName();

    const button = saveButton();
    expect(button).toHaveAttribute("type", "submit");

    /*
     * ⛔ `aria-disabled` BU YERDA YOLG'ON EDI: `Button` ning CSS'i faqat
     *   native `disabled` ga reaksiya qiladi, ya'ni tugma ko'rinishda ham,
     *   amalda ham ochiq turardi — skrinrider esa «yopiq» deb e'lon
     *   qilardi.
     */
    expect(button).not.toHaveAttribute("aria-disabled");
    expect(button).toBeEnabled();
  });
});

/* ---------------------------------------------------------------------------
 * T4/T5 — NAZORAT: YAROQLI NOM VA QAYTARISH YO'LI BUZILMAGAN
 * ------------------------------------------------------------------------ */

describe("yaroqli nom (nazorat)", () => {
  test("AYNAN BITTA so'rov ketadi va `onSaved` chaqiriladi", async () => {
    apiFetch.mockResolvedValue({ ...CAMERA, name: "Meva qatori" });

    const { onSaved } = renderDialog();
    fireEvent.change(nameInput(), { target: { value: "  Meva qatori  " } });
    fireEvent.click(saveButton());

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalled();
    });

    expect(renameCalls()).toHaveLength(1);
    const options = renameCalls()[0][1] as {
      body: Record<string, unknown>;
      method: string;
    };
    expect(options.method).toBe("PATCH");
    expect(options.body.name).toBe("Meva qatori");
  });
});

describe("NVR nomiga qaytarish (chegara)", () => {
  test("qaytarish tugmasi ishlaydi va formani YUBORMAYDI", async () => {
    apiFetch.mockResolvedValue({ ...CAMERA, name_overridden: false });

    const { onSaved } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: RESET_LABEL }));

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalled();
    });

    /*
     * AYNAN BITTA so'rov: agar bu tugma `type="submit"` bo'lib qolsa,
     * bosish HAM `onClick` yo'lini, HAM forma yuborishni ateshlab ikki
     * so'rov yuborardi.
     */
    expect(renameCalls()).toHaveLength(1);
    const options = renameCalls()[0][1] as { body: Record<string, unknown> };
    expect(options.body).toEqual({ name_overridden: false });
  });
});
