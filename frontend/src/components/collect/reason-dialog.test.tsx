/**
 * ⛔⛔ G-24 NING DOM YARMI (06-UI-SPEC §8.6, §13.5, §15.3).
 *
 * =============================================================================
 * ⛔ 1. ERKIN MATN MAYDONI DOM DARAJASIDA YO'Q (D-19).
 *
 *   «Erkin matn yozmaymiz» — KOD-KO'RIK DA'VOSI. Bu yerda esa u
 *   O'LCHANADI: dialogda `<textarea>` ham, matn turidagi maydon ham
 *   bo'lmasligi kerak. Sabab mahsulotda: erkin matn hisobotda
 *   GURUHLANMAYDI va amalda «boshqa» eng katta guruh bo'lib qolardi —
 *   ya'ni sabab tahlili ma'nosiz bo'lardi.
 *
 * ⛔ 2. TO'PLAM TENGLIGI, `not.toContain` EMAS (D-31).
 *
 *   05-14 ning S7 sabotaji: inkor tasdiq FAQAT aynan o'sha nomni
 *   ushlaydi. `<option>` lar to'plami REYESTRGA TENG bo'lishi kerak —
 *   shundagina reyestrga yangi a'zo qo'shilsa yoki bittasi tushib
 *   qolsa, darvoza O'ZI qizaradi.
 *
 * ⛔ 3. `other` / `custom` YO'Q.
 *
 *   U erkin matnni ORQA ESHIKDAN qaytarib keltirardi. To'plam tengligi
 *   buni allaqachon qamraydi; takror ATAYIN, chunki bu aynan
 *   06-RESEARCH OQ-3 da nomma-nom rad etilgan variant.
 *
 * ⛔ 4. NARX — ANTI-AFFORDANS.
 *
 *   Sabab tanlanmaguncha tasdiq `aria-disabled` va bosish HECH NIMA
 *   yubormaydi. Override ISTISNO bo'lib qolishi kerak: arzon bo'lsa,
 *   kassir uni har rastada bosib tarifni effektiv bekor qilardi.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { ReasonDialog } from "@/components/collect/reason-dialog";
import { ADJUSTMENT_REASONS, REVERSAL_REASONS } from "@/lib/api-types";

function renderDialog(node: ReactNode) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      {node}
    </NextIntlClientProvider>,
  );
}

/** ⛔ Radix PORTALGA chizadi — skan `document.body` dan boshlanadi. */
function optionValues(root: HTMLElement): Set<string> {
  return new Set(
    Array.from(root.querySelectorAll("option"))
      .map((el) => el.value)
      /* `placeholder` ning bo'sh qiymati TANLOV emas — u chiqariladi. */
      .filter((value) => value !== ""),
  );
}

describe("G-24 (06-UI-SPEC): DL-1 — summani o'zgartirish", () => {
  test("⛔ `<option>` qiymatlari REYESTRGA AYNAN TENG (D-32 + D-31)", () => {
    const { baseElement } = renderDialog(
      <ReasonDialog
        mode="override"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open
      />,
    );

    expect(optionValues(baseElement)).toEqual(new Set(ADJUSTMENT_REASONS));
  });

  test("⛔ `other` / `custom` sabab-kodi YO'Q (OQ-3)", () => {
    const { baseElement } = renderDialog(
      <ReasonDialog
        mode="override"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open
      />,
    );

    const values = optionValues(baseElement);
    expect(values.has("other")).toBe(false);
    expect(values.has("custom")).toBe(false);
  });

  test("⛔ ERKIN MATN YUZASI — BO'SH TO'PLAM", () => {
    const { baseElement } = renderDialog(
      <ReasonDialog
        mode="override"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open
      />,
    );

    expect(baseElement.querySelectorAll("textarea")).toHaveLength(0);
    expect(baseElement.querySelectorAll('input[type="text"]')).toHaveLength(0);

    /*
     * ⛔ TO'PLAM TENGLIGI: «erkin matn kiritish yuzasi» — `textarea`,
     *   matn turi VA raqamli klaviatura e'lon qilmagan har qanday
     *   maydon. Uchalasining birlashmasi BO'SH bo'lishi kerak; inkor
     *   tasdiq esa maydon qayta nomlanганда o'tib ketardi.
     */
    const freeText = Array.from(
      baseElement.querySelectorAll(
        'textarea, input[type="text"], input:not([inputmode])',
      ),
    ).map((el) => el.tagName.toLowerCase());

    expect(new Set(freeText)).toEqual(new Set());
  });

  test("⛔ sabab tanlanmasa tasdiq `aria-disabled` va HECH NIMA yubormaydi", () => {
    const onConfirm = vi.fn();
    renderDialog(
      <ReasonDialog
        mode="override"
        onConfirm={onConfirm}
        onOpenChange={vi.fn()}
        open
      />,
    );

    const confirm = screen.getByRole("button", { name: messages.common.save });
    expect(confirm).toHaveAttribute("aria-disabled", "true");

    confirm.click();
    expect(onConfirm).not.toHaveBeenCalled();

    /*
     * §14.3: `aria-disabled` JIM turmaydi — sabab JONLI HUDUDDA aytiladi.
     *
     * ⚠ Matn bo'yicha izlash noto'g'ri bo'lardi: ayni satr dialogning
     *   `aria-describedby` tavsifida ham turibdi. Da'vo KANAL haqida
     *   («`role="status"` bilan e'lon qilinadi»), shuning uchun element
     *   ham ROL bo'yicha topiladi.
     */
    expect(screen.getByRole("status")).toHaveTextContent(
      messages.collect.errorFix.reason_required,
    );
  });

  test("⛔ `data-collect-step` YO'Q — override baxtli yo'lning qadami emas", () => {
    const { baseElement } = renderDialog(
      <ReasonDialog
        mode="override"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open
      />,
    );

    expect(baseElement.querySelectorAll("[data-collect-step]")).toHaveLength(0);
  });
});

describe("G-24 (06-UI-SPEC): DL-2 — to'lovni bekor qilish", () => {
  test("⛔ `<option>` qiymatlari storno REYESTRIGA AYNAN TENG", () => {
    const { baseElement } = renderDialog(
      <ReasonDialog
        mode="reversal"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open
      />,
    );

    expect(optionValues(baseElement)).toEqual(new Set(REVERSAL_REASONS));
  });

  test("⛔ erkin matn yuzasi bu yerda ham BO'SH", () => {
    const { baseElement } = renderDialog(
      <ReasonDialog
        mode="reversal"
        onConfirm={vi.fn()}
        onOpenChange={vi.fn()}
        open
      />,
    );

    expect(baseElement.querySelectorAll("textarea")).toHaveLength(0);
    expect(baseElement.querySelectorAll('input[type="text"]')).toHaveLength(0);
  });

  test("⛔ sabab tanlanmasa tasdiq `aria-disabled`", () => {
    const onConfirm = vi.fn();
    renderDialog(
      <ReasonDialog
        mode="reversal"
        onConfirm={onConfirm}
        onOpenChange={vi.fn()}
        open
      />,
    );

    const confirm = screen.getByRole("button", {
      name: messages.collect.reverse,
    });
    expect(confirm).toHaveAttribute("aria-disabled", "true");

    confirm.click();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
