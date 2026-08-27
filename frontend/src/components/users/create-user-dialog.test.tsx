/**
 * YANGI FOYDALANUVCHI — ⛔ JIMGINA NO-OP HECH QACHON.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (TEST-REPORT 2026-08-14, Topilma №4):
 *
 *   RAD ETILGAN AMAL ALWAYS KO'RINADI. Rol tanlanmagan holda «Saqlash»
 *   bosilganda: so'rov ketmasdi, xato chiqmasdi, dialog ochiq qolardi.
 *   Uch «hech nima» birga — foydalanuvchi uchun ular «saqlandi, dialog
 *   yopilmadi» dan farqlanmaydi.
 *
 *   Ildiz sabab O'CHIRILGAN TUGMA edi (`disabled={selectedRoles.length
 *   === 0 || …}`). U «himoya» ko'rinishida edi, aslida esa zodning
 *   `users.rolesRequired` xabarini EKRANGA CHIQARISHNING YAGONA yo'lini
 *   yopib turardi: `handleSubmit` umuman chaqirilmasdi.
 *
 *   ⚠ O'CHIRILGAN TUGMA VALIDATSIYANING O'RNINI BOSA OLMAYDI va bu
 *     kodbaza qoidasi: u NIMA YETISHMAYOTGANINI aytmaydi. Yo'q tugma
 *     (RBAC ko'zgusi) qoidani o'zi aytadi — u umuman boshqa holat va
 *     boshqa sabab.
 * =============================================================================
 *
 * ⛔ T2 — IKKINCHI QATLAM, VA U FAQAT BIRINCHI TUZATISHDAN KEYIN
 *    KO'RINADI. `toggleRole` qayta validatsiyani `selectedRoles.length >
 *    0` shartiga bog'lagan edi, ya'ni 0->1 o'tishida validatsiya
 *    ISHLAMASDI. Tugmani ochib qo'yib, buni tuzatmaslik BIRINCHI
 *    tuzatishning ustiga IKKINCHI yolg'onni qo'yardi: foydalanuvchi
 *    rolni belgilaydi, xato xabari esa ekranda QOLADI va u yana «nimani
 *    noto'g'ri qildim?» deb o'ylardi.
 *
 * ⚠ T3/T4 — QULF HADDAN TASHQARI QATTIQ BO'LIB QOLMAGANIGA nazorat.
 *   Validatsiyani ko'rinadigan qilish oson yo'li — hamma narsani
 *   bloklash; T3 POST yo'li tirikligini, T4 esa telefon qulfi
 *   buzilmaganini o'lchaydi.
 *
 * ⚠ ROL YORLIQLARI `messages.roles.*` DAN olinadi (`roleLabelKey()`
 *   ko'zgusi), literal yozilmaydi. Va rol checkboxlarining MAVJUDLIGI
 *   testning O'ZIDA tekshiriladi: bo'sh `assignableRoles()` to'plamida
 *   T1 yolg'on-yashil bo'lardi (rol tanlash imkoni yo'q -> tabiiyki
 *   tanlanmagan).
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

import messages from "../../../messages/uz-Latn.json";
import { CreateUserDialog } from "@/components/users/create-user-dialog";
import { MARKET_ADMIN_ASSIGNABLE_ROLES } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { roleLabelKey } from "@/lib/rbac";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

/** uz-Latn kataloglaridagi AYNAN qiymatlar. */
const SAVE = messages.common.save;
const PHONE_LABEL = messages.users.phoneLabel;
const ROLES_REQUIRED = messages.users.rolesRequired;
const REQUIRED = messages.errors.required;
const INVALID_PHONE = messages.auth.invalidPhone;

/**
 * `assignableRoles(false)` ning yorliqlari — REYESTRDAN hosila.
 *
 * ⚠ Literal ro'yxat yozilmaydi: D-04 darajasi o'zgarsa (masalan bozor
 *   admini uchinchi rolni bera oladigan bo'lsa) test JIMGINA eskirardi.
 */
const ROLE_LABELS = MARKET_ADMIN_ASSIGNABLE_ROLES.map((role) => {
  const key = roleLabelKey(role);
  if (key === null) throw new Error(`roleLabelKey topa olmadi: ${role}`);
  return messages.roles[key];
});

const CREATED = {
  id: "44444444-4444-4444-8444-444444444444",
  phone: "+998901234567",
  temporary_password: "Xr7-tmp-9021",
};

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
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

function renderDialog(): { onCreated: ReturnType<typeof vi.fn> } {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const onCreated = vi.fn();

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <CreateUserDialog
            onCreated={onCreated}
            onOpenChange={vi.fn()}
            open
          />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
  return { onCreated };
}

function typePhone(value: string): void {
  fireEvent.change(screen.getByLabelText(PHONE_LABEL), {
    target: { value },
  });
}

function clickSave(): void {
  fireEvent.click(screen.getByRole("button", { name: SAVE }));
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
 * QAMROV CHEGARASI — bo'sh to'plamda T1 yolg'on-yashil bo'lardi
 * ------------------------------------------------------------------------ */

describe("rol tanlash yuzasi", () => {
  test("bozor admini bera oladigan rollar checkbox bo'lib chiziladi", () => {
    renderDialog();

    expect(ROLE_LABELS.length).toBeGreaterThan(0);
    for (const label of ROLE_LABELS) {
      const checkbox = screen.getByLabelText(label);
      expect(checkbox).toBeInTheDocument();
      expect(checkbox).toHaveAttribute("type", "checkbox");
    }
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ T1 — ROLSIZ SAQLASH KO'RINADIGAN XABAR BERADI
 * ------------------------------------------------------------------------ */

describe("rol tanlanmagan holda saqlash", () => {
  test("⛔ ko'rinadigan validatsiya xabari chiqadi", async () => {
    renderDialog();
    typePhone("901234567");
    clickSave();

    expect(await screen.findByText(ROLES_REQUIRED)).toBeInTheDocument();
  });

  test("⛔ POST YUBORILMAYDI — qulf saqlanadi", async () => {
    renderDialog();
    typePhone("901234567");
    clickSave();

    await screen.findByText(ROLES_REQUIRED);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  test("xabar e'lon qilinadi va guruhga dasturiy bog'lanadi", async () => {
    renderDialog();
    typePhone("901234567");
    clickSave();

    const error = await screen.findByText(ROLES_REQUIRED);

    /*
     * `role="alert"` — xabar formaning O'RTASIDA tug'iladi va fokus
     * saqlash tugmasida qoladi; e'lonsiz u skrinriderda umuman
     * eshitilmasdi. `Field` ning `${id}-error` konvensiyasi checkbox
     * guruhida ham saqlanadi (guruh `Field` ga o'ralmaydi — mavjud
     * izohdagi sabab kuchda).
     */
    expect(error.closest("[role='alert']")).not.toBeNull();

    const errorId = error.getAttribute("id") ?? error.closest("[id]")?.id;
    expect(errorId).toBeTruthy();

    const fieldset = error.closest("fieldset");
    expect(fieldset).not.toBeNull();
    expect(fieldset?.getAttribute("aria-describedby")).toBe(errorId);
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ T2 — BIRINCHI ROL BELGILANGACH XABAR YO'QOLADI (0 -> 1 o'tishi)
 * ------------------------------------------------------------------------ */

describe("xabarning yo'qolishi", () => {
  test("⛔ birinchi rol belgilanishi bilan xato EKRANDAN CHIQADI", async () => {
    renderDialog();
    typePhone("901234567");
    clickSave();

    await screen.findByText(ROLES_REQUIRED);

    // AYNAN 0 -> 1 o'tishi: eski `shouldValidate` sharti shu yagona
    // o'tishda qayta validatsiya qilmasdi.
    fireEvent.click(screen.getByLabelText(ROLE_LABELS[0]));

    await waitFor(() => {
      expect(screen.queryByText(ROLES_REQUIRED)).toBeNull();
    });
  });
});

/* ---------------------------------------------------------------------------
 * T3 — NAZORAT: YAROQLI FORMA POST YUBORADI
 * ------------------------------------------------------------------------ */

describe("yaroqli forma (nazorat)", () => {
  test("AYNAN BITTA POST ketadi va tanasida tanlangan rol bor", async () => {
    apiFetch.mockResolvedValue(CREATED);

    renderDialog();
    typePhone("901234567");
    fireEvent.click(screen.getByLabelText(ROLE_LABELS[0]));
    clickSave();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledTimes(1);
    });

    const [, options] = apiFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.body.roles).toEqual([MARKET_ADMIN_ASSIGNABLE_ROLES[0]]);
  });

  test("muvaffaqiyatda vaqtinchalik parol ota-komponentga uzatiladi (D-02)", async () => {
    apiFetch.mockResolvedValue(CREATED);

    const { onCreated } = renderDialog();
    typePhone("901234567");
    fireEvent.click(screen.getByLabelText(ROLE_LABELS[0]));
    clickSave();

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith(CREATED.temporary_password);
    });
  });
});

/* ---------------------------------------------------------------------------
 * T4 — NAZORAT: BOSHQA MAYDONNING QULFI BUZILMAGAN
 * ------------------------------------------------------------------------ */

describe("telefon maydoni (nazorat)", () => {
  test("telefon bo'sh bo'lsa rol tanlangan bo'lsa ham POST ketmaydi", async () => {
    renderDialog();
    fireEvent.click(screen.getByLabelText(ROLE_LABELS[0]));
    clickSave();

    /*
     * Ikkala matn ham QONUNIY: bo'sh maydon `errors.required` beradi,
     * noto'g'ri terilgan raqam esa `auth.invalidPhone`. Test qaysi
     * biri ekanini emas, KO'RINISHINI talab qiladi.
     */
    await waitFor(() => {
      const shown =
        screen.queryByText(REQUIRED) ?? screen.queryByText(INVALID_PHONE);
      expect(shown).not.toBeNull();
    });

    expect(apiFetch).not.toHaveBeenCalled();
  });
});
