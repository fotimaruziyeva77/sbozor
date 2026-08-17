"use client";

import { useCallback, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Banknote, CreditCard, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { PAYMENT_METHODS } from "@/lib/api-types";
import type { AdjustmentReasonValue, PaymentMethodValue } from "@/lib/api-types";
import { billingErrorView } from "@/lib/billing-errors";
import { usePayment } from "@/lib/payment-queries";
import type { PaymentRecord } from "@/lib/payment-queries";

/*
 * =============================================================================
 * 2 va 3-QADAM — TO'LOV TURI VA TASDIQ (UI-SPEC §8.4, §8.7, §12.3, §14.3).
 *
 * ⛔⛔ BU FAYL FAZANING ENG QIMMAT UI QISMI: bu yerdagi nuqson PUL
 *     YOZUVIGA aylanadi va u KECHIKKAN yolg'on aytadi — kassir 80 ta
 *     to'lov yozadi, uchtasi ikki marta ketadi va kechqurun sotuvchi
 *     «men to'lagandim» deydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ DUBLIKAT TO'SIQNING MIJOZ YARMI — `useRef` QULFI (D-22, §8.7)
 * -----------------------------------------------------------------------
 * 05-13 O'LCHADI: uch tez bosish UCHTA so'rov yubordi. Sabab — so'rov
 * holatining bayrog'i FAQAT KEYINGI RENDERDA o'zgaradi, ya'ni bir hodisa
 * oqimidagi uch bosish uchalasi ham ESKI qiymatni ko'radi. Server
 * kafolati (`UNIQUE (market_id, idempotency_key)`) ma'lumotni himoya
 * qildi, LEKIN UI ni to'xtatmadi.
 *
 * ⛔ Shuning uchun qulf `useRef` da va u RENDERNI KUTMAYDI. Naqsh
 *    `blind-audit/blind-session.tsx:85-137` dan; yagona farq — qulf band
 *    identifikatorini emas, IDEMPOTENTLIK KALITINI saqlaydi.
 *
 * ⛔ Qulf FAQAT XATODA ochiladi (`onError`). Muvaffaqiyatdan keyin u
 *    yopiq qoladi: kalit `collect-session.tsx` da iste'foga chiqadi va
 *    keyingi to'lov YANGI kalit bilan keladi, ya'ni qulfni ochish
 *    kerak emas.
 *
 * ⛔ SO'ROV HOLATINING BAYROG'I BU FAYLDA UMUMAN O'QILMAYDI — spinner
 *    ALOHIDA, aniq holatdan chiziladi. Bu ataylab: bayroqni o'qish
 *    keyingi ijrochida «demak qulf ham shundan bo'ladi» degan tabiiy
 *    xulosa tug'dirardi va 05-13 ning nuqsoni qaytib kelardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ `event.repeat` E'TIBORSIZ QOLDIRILADI (`decision-bar.tsx:101` qoidasi)
 * -----------------------------------------------------------------------
 * Tasdiq tugmasida `Enter` ni BOSIB TURISH brauzerda `keydown` ni
 * sekundiga o'nlab marta qo'zg'atadi. Bu ommaviy tasdiqlashning
 * KLAVIATURA SHAKLI va bu yerda uning oqibati — o'nlab PUL YOZUVI.
 *
 * ⚠ Ishlovchi `preventDefault()` chaqiradi va yuborishni O'ZI bajaradi:
 *   aks holda brauzer sintez qilgan `click` ikkinchi yo'l bo'lib qolardi
 *   va `repeat` filtri uni umuman ko'rmasdi.
 *
 * ⛔ GLOBAL BIR-TUGMALI YORLIQLAR (`1`/`2`/`3`) YO'Q (§14.4) — 5-fazadagi
 *    `decision-bar` dan ATAYIN farqli: (1) qidiruv maydoni §8.5 fokus
 *    qaytishi tufayli KO'P VAQT fokusda va `1` ham raqam belgisi, ham
 *    buyruq bo'lardi; (2) adashgan bosish bu yerda PUL YOZARDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ STANDART TANLOV YO'Q (§8.4) · AKSENT FAQAT TASDIQDA (§12.3)
 * -----------------------------------------------------------------------
 * Naqd oldindan tanlansa, kassir terminal to'lovini NAQD deb yozib
 * yuborardi va bank solishtiruvi jimgina buzilardi.
 *
 * To'lov turi tugmalari aksent OLMAYDI: ular TANLOV va 05-UI-SPEC ning
 * ankorlash mulohazasi kuchda. Tasdiq esa TANLOV EMAS, OQIBAT —
 * raqobatchisi yo'q, ya'ni urg'u hech narsani buzmaydi.
 *
 * ⛔ OMMAVIY AMAL YUZASI NOL: bitta tanlov semantikasi (radio), massiv
 *    tanali mutatsiya yo'q, «tanlanganlarni to'lash» yo'q (§15.4).
 * =============================================================================
 */

/**
 * ⛔ TARMOQ UZILISHINING KODI — `billing-errors.ts` jadvalidagi a'zo.
 *
 * Satr literali IKKINCHI MARTA yozilmaydi: uni pastdagi
 * `billingErrorCodeOf()` ham, `failureView` ning zaxira shoxi ham
 * ishlatadi va ikki nusxa bir kun ajralib ketardi.
 */
const NETWORK_UNREACHABLE = "network_unreachable";

/**
 * Xato -> KOD. ⛔ HAR DOIM kod qaytaradi, `null` HECH QACHON emas.
 *
 * =============================================================================
 * ⛔⛔ CR-03: BU YERDA `null` QAYTARISH TO'LOVNI JIMGINA YO'QOTARDI.
 *
 * `api-client.ts` transport nosozligida `NetworkError` otadi va u ⛔ `ApiError`
 * NING AVLODI EMAS (`class NetworkError extends Error`). Eski shakl
 * (`error instanceof ApiError ? error.detail : null`) o'shanda `null`
 * qaytarardi, `failureCode` `null` bo'lib qolardi va xato bloki UMUMAN
 * chizilmasdi:
 *
 *     kassir [Tasdiqlash] ni bosadi -> spinner to'xtaydi -> BOSHQA HECH NIMA
 *
 * Ya'ni `[Qayta yuborish]` tugmasi ham, sabab matni ham yo'q. To'lov
 * YOZILGAN bo'lishi ham mumkin edi — va bu AYNAN idempotentlik
 * mexanizmi (§8.7, D-21) mavjud bo'lgan YAGONA stsenariy. Ko'rmagan
 * kassir naqdni QAYTA oladi.
 *
 * ⛔ `collect.errorCause.network_unreachable` va `collect.retrySafe`
 *    uchala locale'da ALLAQACHON bor edi — ular bu yo'lda O'LIK matn edi.
 *
 * ⚠ `ApiError` ning tanilmagan `detail` i (masalan 500 `internal_error`)
 *   bu yerdan O'ZI qaytadi va chaqiruvchidagi `??` uni
 *   `network_unreachable` ga tushiradi — o'sha xulq O'ZGARMADI
 *   (`payment-bar.test.tsx` ning (c)/(d) kanallari uni qulflaydi).
 * =============================================================================
 *
 * ⚠ `review-session.tsx:115` dan import QILINMADI (u Y-2 sessiyasining
 *   moduli va butun nazoratchi ekranini kassir to'plamiga tortib kelardi)
 *   — lekin bu funksiya endi uning NUSXASI ham emas: u yerdagi `null`
 *   ma'noli, bu yerda esa YO'QOTISH edi.
 */
function billingErrorCodeOf(error: unknown): string {
  return error instanceof ApiError ? error.detail : NETWORK_UNREACHABLE;
}

const METHOD_LABEL: Record<
  PaymentMethodValue,
  "collect.methodCash" | "collect.methodTerminal"
> = {
  cash: "collect.methodCash",
  terminal: "collect.methodTerminal",
};

export type PaymentBarProps = {
  stallCode: string;
  /** Yuboriladigan summa — SERVERDAN kelgan qiymat (D-20). `null` — yo'q. */
  amountSoum: number | null;
  /** DL-1 da tanlangan sabab; summa server taklifiga teng bo'lsa YO'Q. */
  reasonCode?: AdjustmentReasonValue;
  /** ⛔ Kalit SAHIFA HOLATIDA tug'iladi (§8.7) — bu yerda EMAS. */
  idempotencyKey: string | null;
  method: PaymentMethodValue | null;
  onMethodChange: (method: PaymentMethodValue) => void;
  onWritten: (record: PaymentRecord) => void;
};

export function PaymentBar({
  stallCode,
  amountSoum,
  reasonCode,
  idempotencyKey,
  method,
  onMethodChange,
  onWritten,
}: PaymentBarProps) {
  const t = useTranslations();
  const pay = usePayment();

  /* ⛔ QULF — band qilingan kalitni saqlaydi, renderni KUTMAYDI. */
  const submittedRef = useRef<string | null>(null);

  const [busy, setBusy] = useState(false);
  const [failureCode, setFailureCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<"method" | "amount" | null>(null);

  const blocked = method === null || amountSoum === null || idempotencyKey === null;

  const submit = useCallback(() => {
    if (amountSoum === null || idempotencyKey === null) {
      setNotice("amount");
      return;
    }
    if (method === null) {
      setNotice("method");
      return;
    }
    /* ⛔ QULF: o'sha kalit ikkinchi marta yuborilmaydi. */
    if (submittedRef.current === idempotencyKey) return;
    submittedRef.current = idempotencyKey;

    setNotice(null);
    setFailureCode(null);
    setBusy(true);

    pay.mutate(
      {
        idempotency_key: idempotencyKey,
        stall_code: stallCode,
        method,
        amount_soum: amountSoum,
        ...(reasonCode === undefined ? {} : { reason_code: reasonCode }),
      },
      {
        onError: (error) => {
          /* ⛔ FAQAT XATODA ochiladi — kalit esa SAQLANADI (§8.7). */
          submittedRef.current = null;
          setBusy(false);
          setFailureCode(billingErrorCodeOf(error));
        },
        onSuccess: (record) => {
          setBusy(false);
          onWritten(record);
        },
      },
    );
  }, [
    amountSoum,
    idempotencyKey,
    method,
    onWritten,
    pay,
    reasonCode,
    stallCode,
  ]);

  const onConfirmKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      /* Yagona yo'l shu ishlovchi — brauzer sintez qiladigan `click` yopiladi. */
      event.preventDefault();
      if (event.repeat) return;
      submit();
    },
    [submit],
  );

  /*
   * ⛔ `failureCode === null` — «hali xato bo'lmagan», «xato kodsiz» EMAS.
   *   `billingErrorCodeOf()` HAR DOIM satr qaytaradi (CR-03), ya'ni
   *   `onError` dan keyin bu qiymat hech qachon `null` bo'lmaydi va
   *   blok CHIZILADI. Zaxira shox esa faqat TANILMAGAN `ApiError.detail`
   *   uchun qoladi.
   */
  const failureView =
    failureCode === null
      ? null
      : (billingErrorView(failureCode) ??
        billingErrorView(NETWORK_UNREACHABLE));

  return (
    <div className="flex flex-col gap-4">
      {/* --- 2-QADAM: RADIOGROUP, ikki tugma emas (§8.4) ---------------- */}
      <fieldset
        className="flex flex-col gap-2"
        data-collect-step={method === null ? "method" : undefined}
      >
        <legend className="pb-2 text-lg leading-snug font-semibold">
          {t("collect.methodLegend")}
        </legend>

        <div className="flex gap-2">
          {PAYMENT_METHODS.map((value) => (
            <label
              className="flex min-h-12 flex-1 cursor-pointer items-center justify-center gap-2 rounded-md border border-border-ui bg-surface px-4 text-sm font-semibold text-text has-[:checked]:border-text has-[:checked]:bg-surface-muted has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent/25"
              key={value}
            >
              <input
                checked={method === value}
                className="sr-only"
                data-collect-option="method"
                name="method"
                onChange={() => {
                  setNotice(null);
                  onMethodChange(value);
                }}
                type="radio"
                value={value}
              />
              {value === "cash" ? (
                <Banknote aria-hidden="true" className="size-4" />
              ) : (
                <CreditCard aria-hidden="true" className="size-4" />
              )}
              {t(METHOD_LABEL[value])}
            </label>
          ))}
        </div>
      </fieldset>

      {/* --- 3-QADAM: TASDIQ — fazadagi YAGONA aksent fonli tugma ------- */}
      <Button
        /*
         * ⛔ `aria-disabled`, `disabled` EMAS (§14.3): o'chirilgan tugma
         *    fokus olmaydi va skrinrider uni umuman o'qimaydi, ya'ni
         *    «nega bosilmayapti?» savoliga javob beradigan joy qolmaydi.
         *    Bozor sharoitida bu OQIM TO'XTASHI demak.
         */
        aria-disabled={blocked ? true : undefined}
        className="min-h-14 w-full text-sm"
        data-collect-step={method === null ? undefined : "confirm"}
        onClick={submit}
        onKeyDown={onConfirmKeyDown}
      >
        {busy ? (
          <Loader2
            aria-hidden="true"
            className="animate-spin motion-reduce:animate-none"
          />
        ) : pay.isSuccess ? (
          /*
           * --- 2-QADAM (09-UI-SPEC §8.1): CHECK-MARK CHIZILADI — 250ms ----
           *
           * ⛔ `Loader2` O'RNIDA, lekin `busy` shoxi O'CHIRILMAGAN: `busy` —
           *    bosilgandan javobgacha, check esa javobdan KEYIN. Ikki BOSHQA
           *    holat; manba — `busy` ni hosil qiluvchi mutatsiya obyektining
           *    MAVJUD muvaffaqiyat bayrog'i (`pay.isSuccess`), yangi prop
           *    ham, yangi holat ham YO'Q.
           *
           * ⛔ `aria-hidden="true"` — bu BEZAK; faktni mavjud
           *    `collect.written` toasti va sr-only status aytadi.
           *
           * ⚠ HALOLLIK IZOHI: jonli oqimda 6-qadam (M-9) javob kelgan
           *   flush'da `stall` ni nolga tushiradi va bu tugma o'sha zahoti
           *   unmount bo'ladi — check to'liq 250ms ni faqat tugma mounted
           *   qolgan holatlarda o'ynaydi. Ulanish nuqtasi shartnoma
           *   bo'yicha shu yerda (§8.1 jadvali) va 6-qadam TEGILMAYDI.
           *
           * Chizish mexanikasi `globals.css::.motion-check-draw` da
           * (stroke-dasharray 30, offset 30→0, var(--motion-base)) —
           * davomiylik komponentda TAKRORLANMAYDI (G-motion-3(b,c)).
           * Reduced-motion'da global blok chizishni 0.01ms ga tushiradi —
           * check DARHOL to'liq ko'rinadi (§8.4).
           */
          <svg
            aria-hidden="true"
            className="size-4"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              className="motion-check-draw"
              d="M4.5 12.5 9.5 17.5 19.5 6.5"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.5"
            />
          </svg>
        ) : null}
        {t("collect.confirm")}
      </Button>

      {/*
       * §14.5, 1 va 3-hudud. `status` — to'lov turi tanlanmagan (oddiy
       * yo'riqnoma); `alert` — summa yo'q (ish davom etmaydi).
       */}
      {notice === "method" ? (
        <p className="text-sm text-text-muted" role="status">
          {t("collect.methodLegend")}
        </p>
      ) : null}

      {notice === "amount" ? (
        <p className="text-sm text-danger-text" role="alert">
          {t("collect.errorCause.amount_unavailable")}
        </p>
      ) : null}

      {/*
       * ⛔ §14.5, 4-hudud + §13.8 toast 6 ning matni: KAFOLAT aytiladi,
       *    mexanizm nomi emas («idempotent» so'zi ekranga chiqmaydi).
       *
       * ⛔ Kalit SAQLANADI: `[Qayta yuborish]` AYNI kalit bilan ketadi va
       *    server o'sha to'lovni 200 bilan qaytaradi. Yangi kalit
       *    olinsa — ikkinchi to'lov yozilardi.
       */}
      {failureView !== null ? (
        <div
          className="flex flex-col items-start gap-2 rounded-sm bg-danger/10 px-3 py-2"
          role="alert"
        >
          <p className="text-sm font-semibold text-danger-text">
            {t(failureView.causeKey)}
          </p>
          <p className="text-sm text-text">{t("collect.retrySafe")}</p>
          <Button onClick={submit} size="sm" variant="secondary">
            {t("collect.retry")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
