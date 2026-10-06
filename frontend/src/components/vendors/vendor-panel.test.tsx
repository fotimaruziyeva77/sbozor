/**
 * Sotuvchi paneli — tarix huquqi YO'Q bo'lganda (261006).
 *
 * Bugungi matritsada `vendor_view` bor har rolda `vendor_history_view` ham
 * bor, ya'ni bu holatga «Sotuvchilar» sahifasi orqali yetib bo'lmaydi. Lekin
 * panel huquqni prop bo'lib oladi va rol matritsasi o'zgargan kuni u BO'SH
 * joy yoki 403 emas, SABABNI ko'rsatishi kerak — shuning uchun holat panelning
 * o'zida o'lchanadi.
 *
 * ⚠ Tarix komponenti umuman MONTAJ QILINMAYDI — so'rov ham ketmaydi. Test
 *   QueryClient'siz chiziladi: montaj qilinsa `useQuery` provayder topa
 *   olmay yiqilardi, ya'ni «so'rov yo'q» da'vosi mexanik tekshiriladi.
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { VendorPanel } from "@/components/vendors/vendor-panel";

const VENDOR = {
  id: "55555555-5555-4555-8555-555555555555",
  full_name: "Aliyev Vali",
  phone: "+998901234567",
  stall_count: 1,
  stall_codes: ["A-12"],
  created_at: "2026-07-01T05:00:00Z",
};

describe("sotuvchi paneli", () => {
  test("huquqsiz rolda tarix o'rniga SABAB yoziladi, amallar esa yo'q", () => {
    render(
      <NextIntlClientProvider locale="uz-Latn" messages={messages}>
        <VendorPanel
          canManage={false}
          canSeeHistory={false}
          onAssign={() => {}}
          onEdit={() => {}}
          onOpenChange={() => {}}
          vendor={VENDOR}
        />
      </NextIntlClientProvider>,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(messages.vendors.paymentHistoryNoAccess)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: messages.vendors.edit }),
      "boshqaruv huquqisiz rolga amal tugmasi chizilmasligi kerak",
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: VENDOR.phone })).toBeInTheDocument();
  });
});
