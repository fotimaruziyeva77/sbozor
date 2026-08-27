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
 *
 * -----------------------------------------------------------------------
 * (d) ⛔⛔ SABOTAJ JURNALI — DARVOZANING O'ZI O'LCHANGAN (2026-08-14)
 * -----------------------------------------------------------------------
 * Asl holat: 8/8 YASHIL. Ya'ni jsdom da mahsulot kodi SOG'LOM va darvoza
 * yashilligi o'z-o'zidan hech nimani isbotlamaydi — quyidagi uch o'lchov
 * uning NIMANI ushlashini ko'rsatadi.
 *
 *   S-A  `onKeyDown` -> `onKeyUp`  (stall-lookup.tsx:116)
 *        QIZARDI: T3, T5, T7, T8   (4 qizil / 4 yashil)
 *        Ushlaydi: «ishlovchi noto'g'ri hodisani tinglaydi».
 *
 *   S-B  `event.key !== "Enter"` -> `event.code !== "Enter"`  (:117)
 *        QIZARDI: T8               (1 qizil / 7 yashil)
 *        Ushlaydi: «ishlovchi noto'g'ri MAYDONNI o'qiydi» (NumpadEnter).
 *
 *   S-C  `<Input>` dan `autoFocus` OLIB TASHLANDI  (:109)
 *        QIZARDI: T1, T2, T3, T4, T5, T6, T7, T8  (8 qizil / 0 yashil)
 *        Ushlaydi: «fokus maydonda emas» — brauzer kuzatuvining eng
 *        jiddiy mahsulot-tomon gipotezasi.
 *
 * ⛔⛔ S-B BIRINCHI O'LCHOVDA DARVOZANI FOSH QILDI (05-15 ning darsi).
 *   Dastlabki holatda S-B ham AYNAN S-A bilan bir xil to'rtta testni
 *   qizartirdi (T3/T5/T7/T8), ya'ni darvoza ikki BOSHQA nuqsonni
 *   FARQLAY OLMASDI. Sabab da'voda emas, TEST HOLATIDA edi: T3/T5/T7
 *   hodisani `code: ""` bilan yuborardi, HAQIQIY klaviatura esa `Enter`
 *   ni HAR DOIM `key: "Enter"` + `code: "Enter"` juftligi bilan beradi.
 *   Holat haqiqiy klaviaturaga moslangach (`code` har bir holatga
 *   yozildi: `"Enter"`, T4 da `"KeyA"`, T8 da `"NumpadEnter"`) S-B
 *   AYNAN T8 ni qizartirdi va imzolar ajraldi: S-A = 4 qizil,
 *   S-B = 1 qizil. ⚠ Bu tuzatish da'voni kuchsizlantirmadi — S-A
 *   moslashtirilgan holat bilan QAYTA yugurtirildi va o'sha to'rtta
 *   testni qizartirgani tasdiqlandi.
 *
 * ⛔ Har uch sabotajdan keyin fayl ASLIGA qaytarildi va tiklanish
 *   `git diff -- src/components/collect/stall-lookup.tsx` ning BO'SH
 *   bo'lishi + yashil yugurish bilan tasdiqlandi.
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
      /* ⛔ Harflar endi SERVERDAN keladi (`row_prefixes`) — testda ular
         aniq berilishi kerak, aks holda tugmalar chizilmaydi va
         «harf tugmasi» da'volari jimgina ma'nosiz bo'lib qolardi. */
      rowPrefixes={["A", "B"]}
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
    fireEvent.keyDown(active, { bubbles: true, code: "Enter", key: "Enter" });

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
    fireEvent.keyDown(active, { bubbles: true, code: "KeyA", key: "a" });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("T5 — chetdagi bo'shliqlar KESILADI (`trim`)", () => {
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode(`  ${CODE}  `);

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, { bubbles: true, code: "Enter", key: "Enter" });

    expect(onSubmit).toHaveBeenCalledWith(CODE);
  });

  test("T6 — faqat bo'shliqdan iborat kod YUBORILMAYDI", () => {
    const onSubmit = vi.fn();
    renderHarness(onSubmit);

    typeCode("   ");

    const active = document.activeElement;
    assertFocusedInput(active);
    fireEvent.keyDown(active, { bubbles: true, code: "Enter", key: "Enter" });

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
      code: "Enter",
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
