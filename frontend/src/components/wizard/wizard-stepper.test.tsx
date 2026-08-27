/**
 * Qadam relsining REGRESSIYA darvozasi (UI-SPEC §6.3, §6.7 / D-11, D-16).
 *
 * NEGA AYNAN SHU BESH DA'VO:
 *
 *   1. BLOKLANGAN QADAM SABABINI KO'RSATADI VA HAVOLA EMAS. Sababsiz
 *      bloklangan element foydalanuvchini boshi berk ko'chaga olib boradi;
 *      havola bo'lib qolgan bloklangan qadam esa uni bajarib bo'lmaydigan
 *      ekranga tashlardi. Ikkalasi ham typecheck, lint va build'dan
 *      BEMALOL o'tadi.
 *
 *   2. BAJARILGAN QADAM HAVOLA (nazorat). Usiz 1-test "rels umuman
 *      chizilmadi" holatida ham yashil ko'rinardi.
 *
 *   3. IXTIYORIY QADAM BELGILANADI VA HECH QACHON BLOKLANMAYDI (D-11).
 *      Belgisiz admin o'zini bloklangan deb o'ylab, sotuvchilarsiz davom
 *      eta olmasligiga ishonardi.
 *
 *   4. JORIY QADAMDA `aria-current="step"`. Skrinrider foydalanuvchisi
 *      uchun bu QAYERDALIK haqidagi yagona signal.
 *
 *   5. KAMERA KO'RSATKICHI NEYTRAL (D-16 regressiyasi). "Xavfsizroq
 *      ko'rinsin" niyatidagi keyingi ishlovchi bu yerga ogohlantirish
 *      qo'shishi juda ehtimolli — qaror shuning uchun test bilan
 *      qulflanadi.
 *
 * DIQQAT: bosish `fireEvent` bilan, `@testing-library/user-event` bilan
 * EMAS — u tasdiqlangan paketlar ro'yxatiga kirmaydi (01-12 qarori). Bu
 * fayl bosishni umuman talab qilmaydi: hamma da'vo RENDER natijasida.
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ComponentProps, ReactElement } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { WizardStepper } from "@/components/wizard/wizard-stepper";
import type { SetupStatusResponse } from "@/lib/api-types";

/*
 * `@/i18n/navigation` `next/navigation` ga tayanadi va u vitest ESM
 * yechimida topilmaydi (01-12 dagi `market-picker.test.tsx` bilan AYNI
 * sabab). Mock `Link` ni oddiy `<a>` ga aylantiradi.
 *
 * Bu QAMROVNI TORAYTIRMAYDI: bu faylning da'volari relsning STRUKTURASI
 * haqida (havolami yoki emas, `href` qaysi qadamga ketadi, ARIA nima
 * deydi) — locale prefiksini qo'yish esa `next-intl` ning o'z zimmasida
 * va u shu yerda sinalmaydi.
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

/**
 * To'liq bo'sh qoralama: bozor bor, ichida hech nima yo'q.
 *
 * `blocking` AYNAN 02-11 o'lchagan shakl — bo'sh qoralamada uchta band
 * (`calendar_configured` `true`, chunki `market_create()` standart
 * haftalik jadvalni O'ZI yozadi).
 */
const EMPTY_DRAFT: SetupStatusResponse = {
  zones: 0,
  categories: 0,
  tariffs_covered: 0,
  categories_total: 0,
  stalls: 0,
  stalls_with_category: 0,
  vendors: 0,
  calendar_configured: true,
  cameras: 0,
  can_activate: false,
  blocking: [
    { step: 2, code: "zones_missing", detail: "0" },
    { step: 3, code: "categories_missing", detail: "0" },
    { step: 5, code: "stalls_missing", detail: "0" },
  ],
};

/** Zona va toifa kiritilgan, tarif hali yo'q — 4-qadam server to'sig'ida. */
const PARTIAL_DRAFT: SetupStatusResponse = {
  ...EMPTY_DRAFT,
  zones: 4,
  categories: 2,
  categories_total: 2,
  tariffs_covered: 0,
  blocking: [
    { step: 4, code: "tariff_missing_for_category", detail: "0/2" },
    { step: 5, code: "stalls_missing", detail: "0" },
  ],
};

function renderStepper(
  status: SetupStatusResponse | null,
  currentStep: number,
): ReturnType<typeof render> {
  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <WizardStepper currentStep={currentStep} status={status} />
    </NextIntlClientProvider>
  );
  return render(tree);
}

/** Qadam nomiga ko'ra rels elementini topadi (havola bo'lsin, bo'lmasin). */
function stepElement(name: string): HTMLElement {
  const item = screen
    .getAllByRole("listitem")
    .find((node) => node.textContent?.includes(name) === true);
  if (item === undefined) throw new Error(`Qadam topilmadi: ${name}`);
  return item;
}

describe("Usta relsi — to'rt holat, uch kanal (§6.3)", () => {
  test("bloklangan qadam SABABINI ko'rsatadi va havola EMAS", () => {
    // 2-qadam (zona) bajarilmagan -> 5-qadam (rasta) bloklangan.
    renderStepper(EMPTY_DRAFT, 2);

    const blocked = stepElement(messages.wizard.step["5"]);
    const control = blocked.querySelector("[aria-disabled='true']");

    expect(control).not.toBeNull();
    /*
     * `aria-describedby` MAVJUD va u HAQIQIY elementga ishora qiladi —
     * bo'sh havolali `describedby` skrinriderga hech nima aytmaydi.
     */
    const describedBy = control?.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(blocked.querySelector(`#${describedBy ?? ""}`)).not.toBeNull();

    // Sabab BLOKLOVCHI qadamni nomma-nom aytadi ("Avval «Zonalar» ...").
    expect(blocked).toHaveTextContent(messages.wizard.step["2"]);

    // Bloklangan qadam bosiladigan havola BO'LMASLIGI shart.
    expect(within(blocked).queryByRole("link")).toBeNull();
    expect(blocked.querySelector("a")).toBeNull();
  });

  test("NAZORAT: bajarilgan qadam havola bo'lib qoladi", () => {
    // Zona va toifa kiritilgan; joriy qadam 4 -> 2-qadam "bajarilgan".
    renderStepper(PARTIAL_DRAFT, 4);

    const done = stepElement(messages.wizard.step["2"]);
    const link = within(done).getByRole("link");

    expect(link).not.toHaveAttribute("aria-disabled");
    expect(link.getAttribute("href")).toContain("step=2");
    // Holat ARIA'da SO'Z bilan ham beriladi, faqat ikonka bilan emas.
    expect(link.getAttribute("aria-label")).toContain("bajarilgan");
  });

  test("ixtiyoriy qadam belgilanadi va HECH QACHON bloklanmaydi", () => {
    /*
     * 5-qadam (rasta) bajarilmagan, ya'ni `blockedBy` bo'yicha 6-qadam
     * bloklanadi — LEKIN u ixtiyoriy va `blocking[]` ga hech qachon
     * tushmaydi (D-11). Bu test ikkinchi yarmini qulflaydi: yorliq
     * KO'RINADI.
     */
    renderStepper(PARTIAL_DRAFT, 4);

    const optional = stepElement(messages.wizard.step["6"]);
    expect(optional).toHaveTextContent(messages.wizard.optional);

    // Server ro'yxatida 6-qadam YO'Q — bu da'vo fixture'ning o'zida.
    expect(PARTIAL_DRAFT.blocking.some((item) => item.step === 6)).toBe(false);
  });

  test("joriy qadamda aria-current=\"step\" bo'ladi va u havola emas", () => {
    renderStepper(PARTIAL_DRAFT, 4);

    const current = stepElement(messages.wizard.step["4"]);
    const marked = current.querySelector("[aria-current='step']");

    expect(marked).not.toBeNull();
    expect(within(current).queryByRole("link")).toBeNull();

    // Rels bo'ylab joriy qadam AYNAN bitta.
    expect(document.querySelectorAll("[aria-current='step']")).toHaveLength(1);
  });

  test("kamera ko'rsatkichi NEYTRAL — nosozlik sifatida ko'rinmaydi", () => {
    renderStepper(EMPTY_DRAFT, 2);

    const camera = stepElement(messages.wizard.step.cameras);
    const text = camera.textContent ?? "";

    /*
     * D-16: kamera hali ulanmagani REJALASHTIRILGAN holat, nosozlik emas.
     * Uchta mustaqil kanal tekshiriladi — matn, rol va fon sinfi — chunki
     * regressiya ularning HAR BIRIDA alohida kelishi mumkin.
     */
    expect(text).not.toMatch(/chala|tugallanmagan|e'tibor bering/iu);
    expect(camera.querySelector("[role='alert']")).toBeNull();
    expect(camera.innerHTML).not.toMatch(/bg-(warning|danger)/iu);

    /*
     * 3-FAZA DELTASI (UI-SPEC §3.4, U-2): ko'rsatkich endi HAQIQIY
     * HAVOLA va `aria-disabled` YO'Q.
     *
     * Da'vo TESKARISIGA o'zgardi va bu ataylab: 2-fazada bo'lim MAVJUD
     * EMAS edi, ya'ni bloklangan ko'rinish ROST edi. 3-fazadan keyin
     * `/cameras` bor — bosilmaydigan ko'rsatkich adminni kameralarni
     * izlab yurishga majburlardi.
     *
     * ⚠ QADAM MAQOMI BERILMAGANI HAMON QULFLANGAN (pastdagi ikki
     *   assert): havola qadam raqamini ham, `Check`/`Lock` belgisini
     *   ham OLMAYDI — D-16 shu ikkisi orqali buzilardi.
     */
    const link = within(camera).getByRole("link");
    expect(link).toHaveAttribute("href", "/cameras");
    expect(link).not.toHaveAttribute("aria-disabled");
    expect(camera.querySelector("[aria-disabled='true']")).toBeNull();

    // Qadam maqomi berilmagan: sanoq doirasi ham, holat belgisi ham yo'q.
    expect(text).not.toMatch(/\d/u);
    expect(camera.querySelector("[aria-current]")).toBeNull();

    // Butun relsda ham shoshilinch e'lon yo'q.
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
