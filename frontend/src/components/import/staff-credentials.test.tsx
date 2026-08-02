/**
 * Vaqtinchalik parollar ro'yxatining REGRESSIYA darvozasi (D-02, MARKET-07).
 *
 * NEGA AYNAN SHU OLTI DA'VO — har biri BOSHQA nosozlik sinfini yopadi va
 * hech biri typecheck, lint yoki build bilan ushlanmaydi:
 *
 *   1. PAROL EKRANDA KO'RINADI. Eng asosiy da'vo va u eng oson buziladi:
 *      qiymatni `•••` bilan maskalash yoki "xavfsizlik uchun" yashirish
 *      butun oqimni ma'nosiz qilardi — parol BOSHQA HECH QAYERDA yo'q.
 *
 *   2. NUSXA TUGMASI AYNAN PAROLNI YOZADI. "Tugma bor" degan da'vo
 *      yetarli emas: u telefonni yoki butun qatorni nusxalayotgan
 *      holatda ham yashil bo'lardi.
 *
 *   3. «HAMMASINI NUSXALASH» BARCHA QATORNI QAMRAYDI. Usiz 30 kishilik
 *      roster uchun admin 30 marta bosardi va aynan shu ish oqimi
 *      qo'lda kiritishdan farq qilmasdi.
 *
 *   4. OGOHLANTIRISH E'LON QILINADI (`role="alert"`). Skrinrider
 *      foydalanuvchisi "bu boshqa ko'rsatilmaydi" faktini ro'yxatga
 *      yetib borgunicha bilishi shart.
 *
 *   5. BO'SH RO'YXAT UMUMAN CHIZILMAYDI. D-15 qayta importi aynan shu
 *      holatni beradi; bo'sh ro'yxatli sarlavha adminni "parol
 *      berilmadimi?" deb o'ylantirardi.
 *
 *   6. CSV AJRATGICHI `;` VA BOM BOR. Ikkalasi ham CIS lokalidagi Excel
 *      uchun MAJBURIY va ikkalasi ham DOM'ga aloqasiz — shuning uchun
 *      sof funksiya (`buildCredentialsCsv`) ustida o'lchanadi.
 *
 * DIQQAT: `fireEvent` ishlatiladi, `@testing-library/user-event` EMAS
 * (01-12 qarori).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  buildCredentialsCsv,
  StaffCredentials,
} from "@/components/import/staff-credentials";
import type { StaffCredential } from "@/lib/api-types";

const CREDENTIALS: readonly StaffCredential[] = [
  {
    row: 2,
    phone: "+998901110001",
    full_name: "Aliyev Vali",
    roles: ["cashier"],
    temporary_password: "aBc123XyZ456",
  },
  {
    row: 3,
    phone: "+998901110002",
    full_name: null,
    roles: ["cashier", "inspector"],
    temporary_password: "qWe789RtY012",
  },
];

const writeText = vi.fn<(text: string) => Promise<void>>();

beforeEach(() => {
  writeText.mockReset();
  writeText.mockResolvedValue(undefined);
  // jsdom'da `navigator.clipboard` yo'q — u shu yerda o'rnatiladi.
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
});

function renderCredentials(
  credentials: readonly StaffCredential[],
): ReturnType<typeof render> {
  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <StaffCredentials credentials={credentials} />
    </NextIntlClientProvider>
  );
  return render(tree);
}

describe("Vaqtinchalik parollar ro'yxati (D-02, MARKET-07)", () => {
  test("har bir parol ekranda OCHIQ ko'rinadi", () => {
    renderCredentials(CREDENTIALS);

    for (const item of CREDENTIALS) {
      expect(screen.getByText(item.temporary_password)).toBeInTheDocument();
    }
  });

  test("qator tugmasi buferga AYNAN parolni yozadi", async () => {
    renderCredentials(CREDENTIALS);

    const button = screen.getByLabelText(
      `${messages.staffCredentials.copy} — ${CREDENTIALS[0].phone}`,
    );
    fireEvent.click(button);
    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });

    // Telefon yoki butun qator emas — AYNAN parol.
    expect(writeText).toHaveBeenCalledWith(CREDENTIALS[0].temporary_password);
  });

  test("«hammasini nusxalash» BARCHA qatorni qamraydi", async () => {
    renderCredentials(CREDENTIALS);

    fireEvent.click(screen.getByText(messages.staffCredentials.copyAll));
    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });

    const written = writeText.mock.calls[0][0];
    for (const item of CREDENTIALS) {
      expect(written).toContain(item.temporary_password);
      expect(written).toContain(item.phone);
    }
  });

  test("ogohlantirish shoshilinch e'lon sifatida beriladi", () => {
    renderCredentials(CREDENTIALS);

    const alerts = document.querySelectorAll("[role='alert']");
    expect(alerts).toHaveLength(1);
    expect(alerts[0].textContent).toBe(messages.staffCredentials.warning);
  });

  test("bo'sh ro'yxatda komponent UMUMAN chizilmaydi (D-15 qayta importi)", () => {
    const { container } = renderCredentials([]);

    expect(container).toBeEmptyDOMElement();
    expect(
      screen.queryByText(messages.staffCredentials.title),
    ).not.toBeInTheDocument();
  });

  test("csv fayli `;` ajratgich va UTF-8 BOM bilan quriladi", () => {
    const csv = buildCredentialsCsv(CREDENTIALS);

    // BOM — Excel cp1251 deb o'qib kirillni buzmasligi uchun.
    expect(csv.startsWith("﻿")).toBe(true);

    const [header, first] = csv.slice(1).split("\r\n");
    expect(header).toBe("F.I.Sh.;telefon;rol;parol");
    expect(first).toBe(
      `Aliyev Vali;${CREDENTIALS[0].phone};cashier;${CREDENTIALS[0].temporary_password}`,
    );
    // Vergul ajratgich sifatida ISHLATILMAYDI (CIS lokalidagi Excel uni
    // ustun chegarasi deb o'qimaydi va butun qator bitta katakka tushardi).
    expect(header).not.toContain(",");
  });
});
