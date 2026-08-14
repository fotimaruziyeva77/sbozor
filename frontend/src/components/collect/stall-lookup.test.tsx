/**
 * ⛔⛔ TEST-REPORT TOPILMA №8 — «RASTA QIDIRUVIDA `Enter` ISHLAMADI».
 *
 * =============================================================================
 * (a) KUZATUV (brauzer sessiyasi, `/uz/collect`)
 * -----------------------------------------------------------------------
 * Rasta kodi terilgandan keyin HAQIQIY klaviatura `Enter` i qidiruvni
 * ishga TUSHIRMADI; o'sha lahzada JS orqali dispatch qilingan `keydown`
 * esa ISHLADI. Kuzatuv IKKI xil o'qiladi va farq narxli:
 *
 *   (1) MAHSULOT NUQSONI — ishlovchi noto'g'ri hodisani tinglaydi,
 *       noto'g'ri maydonni tekshiradi, yoki fokus maydonda emas;
 *   (2) AVTOMATLASH ARTEFAKTI — brauzer boshqaruv qatlami kalit
 *       hodisasini maydonga umuman yetkazmagan.
 *
 * Noto'g'ri o'qish IKKALA tomonga ham zarar qiladi: yo'q nuqsonni
 * «tuzatish» ishlab turgan kodni buzadi, bor nuqsonni «artefakt» deb
 * yopish esa uni Karmanaga JONLI olib chiqadi. Shuning uchun bu fayl
 * avval TASHXIS quroli, keyin regressiya darvozasi.
 *
 * ⛔ Narxi D-18 da: qidiruv — kassir oqimining BIRINCHI qadami va u
 *    kuniga 300–1000 marta takrorlanadi. `Enter` o'rniga sichqoncha
 *    kerak bo'lsa, «≤3 o'zaro ta'sir» byudjeti har takrorda buziladi.
 *
 * -----------------------------------------------------------------------
 * (b) ⛔⛔ NEGA HODISA `document.activeElement` GA YUBORILADI
 * -----------------------------------------------------------------------
 * `collect-session.test.tsx:194-198` (`actOn`) allaqachon
 * `fireEvent.keyDown(el, { key: "Enter" })` qiladi va u YASHIL. Bu —
 * brauzerda ISHLAGAN «JS dispatch» yo'lining aynan o'zi. Ya'ni
 * elementga QARATIB yuborilgan yana bir `keyDown` TAVTOLOGIYA bo'lardi:
 * allaqachon yashil bo'lgan da'voning uchinchi nusxasi, kuzatuvni esa
 * QAYTA HOSIL QILMAYDI.
 *
 * Haqiqiy klaviatura hodisasi elementga NOM bilan emas, FOKUS bilan
 * yetadi. jsdom da bu marshrutning yagona farqlovchi proksisi —
 * hodisani `document.activeElement` ga yuborish. Shunda test IKKI
 * narsani birga o'lchaydi: ishlovchi ishlaydimi VA maydon fokusdami.
 * Ikkinchisi bu to'plamda BIRINCHI marta o'lchanmoqda:
 * `collect-session.test.tsx:337-351` fokusni faqat TO'LOVDAN KEYIN
 * (§8.5 qaytish kontrakti) tekshiradi, BIRINCHI `Enter` lahzasida emas.
 *
 * -----------------------------------------------------------------------
 * (c) ⚠⚠ jsdom NING CHEKLOVI — OCHIQ YOZILADI, YASHIRILMAYDI
 * -----------------------------------------------------------------------
 * Bu yerda ham hodisa TRUSTED emas (`isTrusted === false`). Demak:
 *
 *   ⛔ Chromium ning kalit-hodisa sintezi O'LCHANMAYDI;
 *   ⛔ CDP `Input.dispatchKeyEvent` ning parametrlari
 *      (`windowsVirtualKeyCode`, `nativeVirtualKeyCode`, `text`)
 *      O'LCHANMAYDI;
 *   ⛔ IME/kompozitsiya va OS klaviatura tartibi O'LCHANMAYDI.
 *
 * Ya'ni bu darvoza ISHLOVCHI + FOKUS marshrutini qoplaydi, brauzerning
 * KIRISH QATLAMINI emas. Artefakt gipotezasini faqat brauzerda hal
 * qilish mumkin va uning retsepti SUMMARY da yozilgan.
 * =============================================================================
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useRef, useState } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { StallLookup } from "@/components/collect/stall-lookup";

const FIELD_ID = "stall-lookup-under-test";
const CODE = "A-01";

/**
 * ⛔ HARNESS — `StallLookup` boshqariladigan komponent: `value` va
 *    `inputRef` EGASI sessiya. Egasini soxtalashtirmasdan o'lchash uchun
 *    shu yerda eng kichik haqiqiy ega quriladi (`useState` + `useRef`),
 *    ya'ni `onValueChange -> value` halqasi HAQIQATAN yopiladi.
 *
 * ⚠ `useTranslations` ishlatiladi -> `NextIntlClientProvider` MAJBURIY.
 *   Mock qilinmaydi: yorliq matni `getByLabelText` ning langari va uni
 *   soxtalashtirish yorliq bog'lanishini o'lchovdan chiqarardi.
 */
function Harness({ onSubmit }: { onSubmit: (code: string) => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [value, setValue] = useState("");

  return (
    <StallLookup
      fieldId={FIELD_ID}
      inputRef={inputRef}
      matches={[]}
      notFound={false}
      onSelectMatch={() => {}}
      onSubmit={onSubmit}
      onValueChange={setValue}
      ownsStep
      value={value}
    />
  );
}

function renderHarness(onSubmit: (code: string) => void) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <Harness onSubmit={onSubmit} />
    </NextIntlClientProvider>,
  );
}

/** Yorliq orqali — maydonning `<label for>` bog'lanishi ham shu bilan tirik. */
function stallInput(): HTMLElement {
  return screen.getByLabelText(messages.collect.stallLabel);
}

/** Terish — HAQIQIY halqadan o'tadi: `onChange -> onValueChange -> value`. */
function typeCode(code: string): void {
  fireEvent.change(stallInput(), { target: { value: code } });
}

/**
 * ⛔ Fokusdagi element HAQIQATAN qidiruv maydonimi — hodisa yuborishdan
 *    OLDIN. Bu narrowing emas, DA'VO: fokus boshqa joyda bo'lsa test
 *    «hodisa yubordim, hech nima bo'lmadi» deb jimgina yashil qolmasligi
 *    kerak.
 */
function assertFocusedInput(el: Element | null): asserts el is HTMLInputElement {
  expect(el).not.toBeNull();
  expect(el).toBeInstanceOf(HTMLInputElement);
  if (!(el instanceof HTMLInputElement)) {
    throw new Error("⛔ Fokusda <input> yo'q — hodisa yuborilmadi");
  }
  expect(el.id).toBe(FIELD_ID);
}

/* -------------------------------------------------------------------------- */
/* T1–T2 — FOKUS: BU TO'PLAMDA BIRINCHI MARTA, `Enter` DAN OLDINGI LAHZADA    */
/* -------------------------------------------------------------------------- */

describe("Topilma №8: fokus invarianti (`autoFocus`)", () => {
  test("T1 — mount'dan keyin fokus AYNAN qidiruv maydonida", () => {
    renderHarness(vi.fn());

    /* ⛔ `autoFocus` propi bor-yo'qligi emas — FOKUS QO'NGANI o'lchanadi. */
    expect(document.activeElement).toBe(stallInput());
  });

  test("T2 — terishdan keyin ham fokus O'SHA maydonda qoladi", () => {
    renderHarness(vi.fn());

    typeCode(CODE);

    /*
     * ⛔ Alohida da'vo, T1 ning takrori EMAS: qayta render (`value`
     *    propi o'zgaradi) maydonni almashtirib yuborsa yoki biror
     *    element fokusni o'g'irlasa, `Enter` bosilganda hodisa
     *    BOSHQA elementga borardi — kuzatuvning aynan shakli.
     */
    expect(document.activeElement).toBe(stallInput());
  });
});

/* -------------------------------------------------------------------------- */
/* T3–T8 — HODISA FOKUS ORQALI YETADI (element havolasiga QARATIB EMAS)       */
/* -------------------------------------------------------------------------- */

describe("Topilma №8: `Enter` fokuslangan elementga yuborilganda", () => {
  test("⛔ T3 (ASOSIY DA'VO) — `onSubmit` AYNAN 1 marta, AYNAN kod bilan", () => {
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode(CODE);

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, { bubbles: true, key: "Enter" });

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith(CODE);
  });

  test("T4 (NAZORAT) — boshqa tugma `onSubmit` ni CHAQIRMAYDI", () => {
    /*
     * ⛔ Usiz T3 BO'SH bo'lardi: «biror tugma bosilsa yuboriladi» ham
     *    T3 ni yashil qilardi. Farq AYNAN BITTA o'zgaruvchida — kalit.
     */
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode(CODE);

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, { bubbles: true, key: "a" });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("T5 — chetdagi bo'shliqlar KESILADI (`trim`)", () => {
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode(`  ${CODE}  `);

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, { bubbles: true, key: "Enter" });

    expect(onSubmit).toHaveBeenCalledWith(CODE);
  });

  test("T6 — faqat bo'shliqdan iborat kod YUBORILMAYDI", () => {
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode("   ");

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, { bubbles: true, key: "Enter" });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("⛔ T7 — `preventDefault` MOCK'DAN MUSTAQIL dalil", () => {
    /*
     * ⛔ `onSubmit` josusi ishlovchining ICHIDAN chaqiriladi, ya'ni u
     *    «ishlovchi yugurdimi?» degan savolga O'ZI javob bo'lolmaydi:
     *    josus soxtalashtirilsa yoki noto'g'ri ulansa da'vo yopiladi.
     *    `defaultPrevented` esa DOM ning o'z yozuvi — u faqat ishlovchi
     *    haqiqatan yugurgan va `preventDefault()` chaqirgan holatda
     *    `true` bo'ladi.
     *
     * ⚠ `cancelable: true` MAJBURIY: bo'lmasa `preventDefault()` jimgina
     *   e'tiborsiz qoladi va da'vo hech qachon rost bo'lmasdi.
     * ⚠ `fireEvent` ning QAYTARGAN qiymatiga tayanilmaydi — hodisa
     *   obyektining O'ZI o'qiladi.
     */
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode(CODE);

    const active = document.activeElement;
    assertFocusedInput(active);

    const event = new KeyboardEvent("keydown", {
      bubbles: true,
      cancelable: true,
      key: "Enter",
    });
    fireEvent(active, event);

    expect(event.defaultPrevented).toBe(true);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  test("T8 — `code` emas, `key` o'qiladi: `NumpadEnter` ham ishlaydi", () => {
    /*
     * ⛔ Raqamli klaviaturali kassir bloklanmaydi. `event.code` bu holatda
     *    `"NumpadEnter"`, `event.key` esa `"Enter"` — ishlovchi AYNAN
     *    ikkinchisini o'qishi kerak.
     */
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode(CODE);

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, {
      bubbles: true,
      code: "NumpadEnter",
      key: "Enter",
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith(CODE);
  });
});
