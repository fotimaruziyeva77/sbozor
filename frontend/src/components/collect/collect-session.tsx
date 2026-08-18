"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { DoorOpen } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { toast } from "sonner";

import { PaymentBar } from "@/components/collect/payment-bar";
import { PaymentRow } from "@/components/collect/payment-row";
import { VendorReceiptDialog } from "@/components/collect/vendor-receipt-dialog";
import { PendingCard } from "@/components/collect/pending-card";
import { ReasonDialog } from "@/components/collect/reason-dialog";
import { StallLookup } from "@/components/collect/stall-lookup";
import { flyAmountToList } from "@/components/collect/success-choreography";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ApiError } from "@/lib/api-client";
import type { AdjustmentReasonValue, PaymentMethodValue } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import {
  dropPendingAfterPayment,
  usePendingStall,
} from "@/lib/billing-pending-queries";
import type { PendingStall } from "@/lib/billing-pending-queries";
import { useRecentPayments, useReversePayment } from "@/lib/payment-queries";
import type { PaymentRecord } from "@/lib/payment-queries";
import { useOpenShift } from "@/lib/shift-queries";

/*
 * =============================================================================
 * Y-1 NING QADAM MASHINASI — ≤3 O'ZARO TA'SIR (UI-SPEC §8.1–§8.7).
 *
 * ⛔⛔ KASSIRNING KUNI — BITTA 3-QADAMLI OQIM EMAS, UNING 300–1000 MARTA
 *     TAKRORI. Shuning uchun bu fayldagi eng qimmat qism oxirgi bandda:
 *     muvaffaqiyatli yozuvdan keyin fokus qidiruv maydoniga AVTOMATIK
 *     qaytadi. Qaytmasa, har takrorga bitta bosish qo'shilib real sanoq
 *     4 ga chiqardi — D-18 rasmiy ravishda bajarilib, amalda BUZILGAN
 *     bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ INVARIANT: DOM'DA HAR LAHZADA AYNAN BITTA `[data-collect-step]`
 * -----------------------------------------------------------------------
 * Qadam identifikatorining EGASI shu komponentda hal qilinadi:
 *
 *   rasta yechilmagan  -> `stall-lookup` (input yoki ro'yxat konteyneri)
 *   rasta yechilgan    -> `payment-bar` (to'lov turi yoki tasdiq)
 *
 * Bu shunchaki uslub emas — u SANOQNI HOSILA qiladi. «Uchta tugma bor»
 * degan strukturaviy tekshiruv to'rtinchi qadam qo'shilganda YASHIL
 * qolardi; DOM'dan sanaladigan sikl esa 4 ni qaytaradi va HECH KIM
 * ro'yxatni yangilamasdan test qizaradi.
 *
 * ⛔ §9.4 ning 3-QATLAMI ham shu: to'lov turi bloki rasta yechilmaguncha
 *    DOM'da UMUMAN yo'q, ya'ni 2-qadamni «eski summa ustida» bosishning
 *    fizik imkoni qolmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ IDEMPOTENTLIK KALITINING HAYOT DAVRI (§8.7, yettala hodisa)
 * -----------------------------------------------------------------------
 * Kalit SAHIFA HOLATIDA yashaydi — mutatsiya ichida EMAS. Mutatsiya
 * ichida tug'ilsa, har qayta urinish YANGI kalit olib, server uchun
 * YANGI TO'LOV bo'lib ko'rinardi va dublikat to'sig'ining server yarmi
 * umuman ishlamasdi.
 *
 * Kalit `urug'` (rasta + summa + to'lov turi) o'zgarganda QAYTA
 * TUG'ILADI va boshqa hech qachon o'zgarmaydi:
 *
 *   rasta yechildi         -> tug'iladi
 *   summa o'zgartirildi    -> YANGI kalit (aks holda server 409 berardi)
 *   to'lov turi o'zgardi   -> YANGI kalit (u ham imzoning qismi)
 *   tarmoq xatosi / 5xx    -> ⛔ SAQLANADI (qayta yuborish AYNI kalit bilan)
 *   `[Qayta yuborish]`     -> ⛔ SAQLANADI, qulf esa ochilgan
 *   2xx javob              -> iste'foga chiqadi (urug' `null` bo'ladi)
 *   rasta kodi o'zgardi    -> iste'foga chiqadi
 *
 * ⛔ Kalit ekranda HECH QACHON ko'rsatilmaydi (§7.2) va URL'da yashamaydi
 *    (§4.5). U ichki mexanizm — foydalanuvchi uchun ma'nosi yo'q.
 *
 * ⚠ Kalit RENDER FAZASIDA sinxronlanadi (naqsh `blind-session.tsx:97-101`
 *   dan): `useEffect` bilan qilinsa, birinchi renderda kalit `null`
 *   bo'lib, kassir shu lahzada tasdiqni bosса «summa yo'q» xabari
 *   chiqardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ §8.1 NING TO'QQIZ HOLATIDAN IKKITASI `payment-bar.tsx` DA
 * -----------------------------------------------------------------------
 * `submitting` va `error` — mutatsiya EGASINING holatlari, ya'ni ular
 * tugma bilan bir joyda yashaydi. Ularni bu yerga ko'tarish `useRef`
 * qulfini ota-komponent orqali render aylanishiga bog'lardi — 05-13
 * o'lchagan nuqsonning aynan o'zi. Qolgan yettitasi `collectState()` da.
 *
 * ⛔ OPTIMISTIK YANGILASH YO'Q (§16.3): pul raqamida optimizm
 *    taqiqlanadi. «Yozildi» faqat 2xx dan KEYIN aytiladi.
 * =============================================================================
 */

/** §8.1 ning to'qqiz holati — nomi bilan, «yuklanmoqda» degan umumiy yo'q. */
export type CollectState =
  | "no-shift"
  | "idle"
  | "looking-up"
  | "not-found"
  | "ready"
  | "amount-unavailable"
  | "submitting"
  | "written"
  | "error";

/**
 * Sessiya darajasidagi holat — SOF funksiya (naqsh `sessionState` dan).
 *
 * ⚠ `submitting` va `error` bu yerdan CHIQMAYDI: yuqoridagi blokka
 *   qarang. Ular `payment-bar.tsx` ning lokal holatlari.
 */
export function collectState(input: {
  /** `null` — ochiq smena holati hali bilinmaydi. */
  hasOpenShift: boolean | null;
  submittedCode: string;
  isFetching: boolean;
  notFound: boolean;
  hasMatches: boolean;
  stall: PendingStall | null;
  wrote: boolean;
}): CollectState {
  if (input.hasOpenShift === false) return "no-shift";
  if (input.submittedCode === "") return input.wrote ? "written" : "idle";
  if (input.notFound) return "not-found";
  if (input.hasMatches) return "idle";
  if (input.stall === null || input.isFetching) return "looking-up";
  return input.stall.amount_soum === null ? "amount-unavailable" : "ready";
}

/** Xato kodi — `payment-bar.tsx` dagi bilan bir xil sabab (lokal nusxa). */
function lookupErrorCodeOf(error: unknown): string | null {
  return error instanceof ApiError ? error.detail : null;
}

export type CollectSessionProps = {
  /** `/collect/shift` — til prefiksi bilan; egasi sahifa komponenti. */
  shiftHref: string;
};

export function CollectSession({ shiftHref }: CollectSessionProps) {
  const t = useTranslations();
  const format = useFormatter();
  const client = useQueryClient();
  const { principal } = useAuthStore();
  const marketId = principal?.marketId ?? "";
  const fieldId = useId();

  const inputRef = useRef<HTMLInputElement | null>(null);

  /*
   * 4-QADAM FLIP UCHLARI (09-UI-SPEC §8.1, 09-04) — REF, HOLAT EMAS:
   * `amountRef` «Kutilayotgan patta» summasiga (`PendingCard` ichida),
   * `listRef` to'lovlar ro'yxati seksiyasiga. ⛔ Xoreografiya uchun YANGI
   * `useState` QO'SHILMAYDI — u renderga umuman tegmaydi (G-motion-2(d)).
   */
  const amountRef = useRef<HTMLParagraphElement | null>(null);
  const listRef = useRef<HTMLElement | null>(null);

  /* ⛔ Rasta kodi SAHIFA HOLATIDA — URL'da EMAS (§4.5). */
  const [draft, setDraft] = useState("");
  const [submittedCode, setSubmittedCode] = useState("");
  const [method, setMethod] = useState<PaymentMethodValue | null>(null);
  const [extraAmount, setExtraAmount] = useState<number | null>(null);
  const [wrote, setWrote] = useState<PaymentRecord | null>(null);

  /*
   * ⛔ DL-1 / DL-2 SAHIFA HOLATIDA, URL'da EMAS (§4.4): dialogni
   *    ulashiladigan havolaga aylantirish uni sahifa holatidan marshrutga
   *    ko'chirardi va «orqaga» tugmasi uni qayta ochardi.
   */
  const [dialog, setDialog] = useState<
    { mode: "override" } | { mode: "reversal"; paymentId: string } | null
  >(null);
  const [override, setOverride] = useState<{
    amountSoum: number;
    reasonCode: AdjustmentReasonValue;
  } | null>(null);

  const shift = useOpenShift();
  const recent = useRecentPayments();
  const reverse = useReversePayment();
  /* K-3: sotuvchiga ko'rsatiladigan tasdiq — sof ko'rinish holati. */
  const [vendorRecord, setVendorRecord] = useState<PaymentRecord | null>(null);
  const hasOpenShift =
    shift.data === undefined ? null : shift.data !== null;

  const pending = usePendingStall(submittedCode, {
    enabled: hasOpenShift === true,
  });

  const lookup = pending.data;
  const matches = lookup?.matches ?? [];
  const stall = lookup === undefined ? null : lookup.stall;
  const notFound = lookupErrorCodeOf(pending.error) === "stall_not_found";

  /*
   * =========================================================================
   * ⛔⛔ SERVER YECHGAN KODNI QABUL QILISH (260818, brauzerda o'lchandi).
   * =========================================================================
   * Kassir «B» deb yozsa (yoki qator tugmasini bossa), server uni YECHADI
   * va `stall_code: "B-01"` qaytaradi. `PendingCard` esa javobning kodini
   * KIRITILGAN kod bilan solishtiradi (`matched`) — va u ATAYIN shunday:
   * boshqa rastaning summasini shu rasta kodi ostida chizish PUL
   * XATOSI bo'lardi.
   *
   * Natijada karta MANGU skeletonda qolardi: javob kelgan, summa bor,
   * lekin kod mos emas. Jonli o'lchandi — «B» -> 200 javob -> karta
   * «Yuklanmoqda» da qotdi va kassir nima bo'layotganini bilmasdi.
   *
   * ⛔ HIMOYA ZAIFLASHTIRILMAYDI: `matched` sharti TEGILMAYDI. Buning
   *    o'rniga YUBORILGAN kod serverning javobiga tenglashtiriladi —
   *    ya'ni ekranda ko'rinadigan kod ham, summa ham BIR javobdan.
   *    Eski (boshqa rastaga tegishli) javob baribir mos kelmaydi.
   *
   * ⚠ Sikl YO'Q: tenglashtirilgandan keyin shart yolg'on bo'ladi. Kalit
   *   o'zgargani uchun bitta qo'shimcha so'rov ketadi va bu TO'G'RI —
   *   kesh kaliti endi haqiqiy rasta kodi bo'ladi.
   */
  useEffect(() => {
    if (stall === null) return;
    if (stall.stall_code === submittedCode) return;
    setSubmittedCode(stall.stall_code);
  }, [stall, submittedCode]);

  const state = collectState({
    hasOpenShift,
    submittedCode,
    isFetching: pending.isFetching,
    notFound,
    hasMatches: matches.length > 0,
    stall,
    wrote: wrote !== null,
  });

  /*
   * ⛔ SUMMA SERVERDAN, KLIENTDA ARIFMETIKA YO'Q (D-20).
   *
   *   Standart — BUGUNGI patta. Yopiq kunda yoki tarif belgilanmaganda
   *   yagona qonuniy summa — eski qarz (D-24: yopiq kunda ham qarz
   *   undiriladi). `[Qarzni ham olish]` esa serverdan kelgan tayyor
   *   qiymatni beradi va u `extraAmount` da saqlanadi.
   */
  const baseAmount =
    stall === null
      ? null
      : (stall.amount_soum ??
        (stall.outstanding_soum > 0 ? stall.outstanding_soum : null));
  /*
   * ⛔ DL-1 ning natijasi eng ustuvor: kassir sabab-kod bilan ATAYIN
   *    boshqa qiymat kiritdi va u serverga AYNAN shu qiymat bilan
   *    ketadi. Server esa uni o'z takliflari bilan solishtirib, sabab
   *    haqiqatan kerakmi yoki ortiqchami — o'zi hal qiladi (D-19).
   */
  const chosenAmount = override?.amountSoum ?? extraAmount ?? baseAmount;

  /*
   * ⛔ KALIT URUG'I — §8.7 jadvalining MEXANIK shakli.
   *
   *   Urug'dagi har uchala qism ham serverning `request_fingerprint` iga
   *   kiradi, ya'ni ularning biri o'zgargach ESKI kalitni yuborish
   *   `409 idempotency_key_reused` berardi. Yangi kalit bu holatni
   *   umuman tug'ilmaydigan qiladi (Pitfall 4).
   */
  const keySeed =
    stall === null || chosenAmount === null
      ? null
      : `${submittedCode}|${chosenAmount}|${method ?? ""}`;
  const [seenSeed, setSeenSeed] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);
  if (keySeed !== seenSeed) {
    setSeenSeed(keySeed);
    setIdempotencyKey(keySeed === null ? null : crypto.randomUUID());
  }

  const money = useCallback(
    (value: number) => `${format.number(value)} ${t("collect.amountUnit")}`,
    [format, t],
  );

  /*
   * ⛔ RO'YXAT SERVER BERGANICHA — klientda kesilmaydi ham, uzaytirilmaydi
   *    ham. Oyna marshrutning IMKONIYATIDA (parametri yo'q), ya'ni uni
   *    klientdan kengaytirishning yo'li umuman qolmagan.
   */
  const recentItems = recent.data?.items ?? [];

  /** Yangi rasta — varaqning HAMMASI noldan boshlanadi. */
  const startLookup = useCallback((code: string) => {
    setSubmittedCode(code);
    setMethod(null);
    setExtraAmount(null);
    setOverride(null);
    setWrote(null);
  }, []);

  /*
   * ⛔⛔ §8.5 — FAZANING O'TKAZUVCHANLIK KONTRAKTI.
   *
   *   Muvaffaqiyatli `POST` dan KEYIN, AVTOMATIK va BOSISHSIZ: e'lon,
   *   keshdan chiqarish, maydonni bo'shatish, FOKUSNI QAYTARISH, to'lov
   *   turini nolga qaytarish va kalitning iste'foga chiqishi.
   */
  const onWritten = useCallback(
    (record: PaymentRecord) => {
      setWrote(record);

      /*
       * ⛔ `removeQueries`, `invalidate*` EMAS: to'lovdan keyingi eski
       *    proyeksiya endi YOLG'ON summa va u brauzer xotirasida turishi
       *    ham kerak emas.
       *
       * ⚠ Mutatsiyaning o'z `onSuccess` i ham shu tozalashni bajaradi.
       *   Takror ATAYIN: bu yerdagi chaqiruv §8.5 ning 2-bandini SHU
       *   faylda ko'rinadigan qiladi va so'rov qatlami bir kun qayta
       *   yozilsa, kontrakt jimgina yo'qolmaydi. Amal idempotent.
       */
      dropPendingAfterPayment(client, marketId);

      setSubmittedCode("");
      setDraft("");
      setMethod(null);
      setExtraAmount(null);
      setOverride(null);

      /* ⛔ Fokus qidiruv maydoniga QAYTADI — kassir hech nima bosmaydi. */
      inputRef.current?.focus();

      toast.success(
        `${t("collect.written")} · ${record.stall_code} · ${money(record.amount_soum)}`,
      );

      /*
       * ⛔⛔ 1–5-QADAM XOREOGRAFIYASI — AYNAN SHU YERDA, `focus()` VA
       *     `toast.success` DAN KEYIN (09-UI-SPEC §8.3, 09-04).
       *
       * Sabab MEXANIK, uslub emas: `position: fixed` klon `focus()` dan
       * OLDIN DOM'ga qo'shilsa, brauzer scroll-anchoring hisobini qayta
       * qiladi va telefonda fokuslangan input ekrandan chiqib ketishi
       * mumkin. Tartib — SHARTNOMA.
       *
       * ⛔ `await` YO'Q: bayram oqimni KUTDIRMAYDI (G-motion-2(a,b)).
       * ⛔ `try/catch` MAJBURIY: bayram yiqilsa ham to'lov qatori va fokus
       *    JOYIDA qoladi (G-motion-2(e)) — himoya qatlami FAQAT shu yerda,
       *    funksiyaning o'zi istisnoni yutmaydi.
       * ⛔ Klon React daraxtidan tashqarida — keyingi flush `PendingCard`
       *    ni unmount qilganda ham uchish tugaydi.
       */
      try {
        flyAmountToList({ from: amountRef.current, to: listRef.current });
      } catch {
        /* bayram — bezak; oqimni to'xtatmaydi */
      }
    },
    [client, marketId, money, t],
  );

  if (state === "no-shift") {
    /*
     * ⛔ SMENASIZ TO'LOV YOZILMAYDI va bu «jarayonni to'xtatish» EMAS:
     *    smena ochish BITTA bosish va u shu ekrandan boshlanadi.
     *    Sabab — CASH-04 ning farqi `shift_id` ga tayanadi (D-27), ya'ni
     *    smenasiz yozilgan to'lov hisobotdan JIMGINA tushib qolardi.
     */
    return (
      <Card>
        <CardContent className="pt-5">
          <EmptyState
            action={
              <a
                className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-surface px-6 text-sm font-semibold text-text hover:bg-surface-muted"
                href={shiftHref}
              >
                <DoorOpen aria-hidden="true" className="size-4" />
                {t("collect.shiftOpen")}
              </a>
            }
            description={t("collect.errorFix.no_open_shift")}
            title={t("collect.errorCause.no_open_shift")}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <StallLookup
        fieldId={fieldId}
        inputRef={inputRef}
        matches={matches}
        notFound={notFound}
        onSelectMatch={(code) => {
          setDraft(code);
          startLookup(code);
        }}
        onSubmit={startLookup}
        onValueChange={setDraft}
        ownsStep={stall === null}
        value={draft}
      />

      {submittedCode !== "" && !notFound && matches.length === 0 ? (
        <PendingCard
          amountRef={amountRef}
          chosenAmount={chosenAmount}
          enteredCode={submittedCode}
          isError={pending.isError && !notFound}
          isLoading={pending.isFetching}
          onCollectDebt={setExtraAmount}
          /*
           * ⛔ T1 da IXTIYORIY qoldirilgan prop endi BERILADI — ya'ni
           *    `[Summani o'zgartirish]` shu taskdan boshlab ko'rinadi.
           */
          onRequestOverride={() => setDialog({ mode: "override" })}
          onRetry={() => void pending.refetch()}
          pending={stall}
        />
      ) : null}

      {stall !== null ? (
        <PaymentBar
          amountSoum={chosenAmount}
          idempotencyKey={idempotencyKey}
          method={method}
          onMethodChange={setMethod}
          onWritten={onWritten}
          reasonCode={override?.reasonCode}
          stallCode={stall.stall_code}
          vendorAssigned={stall.vendor_assigned}
        />
      ) : null}

      {/*
       * §14.5, 2-hudud — §8.5 ning 1-bandi. Yozilgan to'lov E'LON
       * QILINADI; ko'rinadigan qatorlar ro'yxati keyingi taskda qo'shiladi
       * va G-20 sanog'i unga TAYANMAYDI (u faqat qadam elementlarini
       * sanaydi).
       */}
      {wrote !== null ? (
        <p className="sr-only" role="status">
          {t("collect.written")} · {wrote.stall_code} ·{" "}
          {money(wrote.amount_soum)}
        </p>
      ) : null}

      {/*
       * ⛔ §8.5 NING 1-BANDI KO'RINADIGAN SHAKLDA — oyna SERVERDA qat'iy
       *    (oxirgi beshta), ya'ni bu ro'yxatdan smenaning jamini
       *    chiqarib olishning yo'li yo'q. ⛔ Bu yerda ham yig'uvchi amal
       *    yozilmaydi (§8.8, G-7 ning frontend yarmi).
       */}
      {/*
       * ⛔ §13.8 NING 3-BO'SH HOLATI: BLOK HAR DOIM CHIZILADI.
       *
       * Ilgari ro'yxat bo'sh bo'lganda butun bo'lim YO'QOLARDI va kassir
       * «yozdimmi yoki yo'qmi?» degan savolga ekrandan javob topa
       * olmasdi — yo'qlik NOSOZLIK bilan bir xil ko'rinardi. Endi
       * yo'qlik NOMLANADI (`collect.recentEmpty`).
       *
       * ⚠ Matn oynaning CHEGARASINI aytmaydi va SANOQ bermaydi: har
       *   qanday «N ta to'lov» shakli §8.8 ning yig'indi taqig'iga
       *   yaqinlashardi (G-7).
       */}
      <section
        aria-label={t("collect.recentTitle")}
        className="flex flex-col gap-2"
        /* 4-qadam NISHONI: klon shu konteyner tomon uchadi (09-04). */
        ref={listRef}
      >
        <h2 className="text-lg leading-snug font-semibold">
          {t("collect.recentTitle")}
        </h2>
        {recentItems.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {recentItems.map((record) => (
              <PaymentRow
                key={record.payment_id}
                onRequestReverse={() =>
                  setDialog({ mode: "reversal", paymentId: record.payment_id })
                }
                onShowVendor={() => {
                  setVendorRecord(record);
                }}
                record={record}
              />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-muted">{t("collect.recentEmpty")}</p>
        )}
      </section>

      {/*
       * ⛔ DL-1 / DL-2 — HAQIQIY render, `null` yoki bo'sh o'ram EMAS.
       *    Ikkisi qurilib hech kim chizmasa, CASH-02 va CASH-03 ekranda
       *    UMUMAN mavjud bo'lmasdi va uchala task ham yashil qaytardi.
       */}
      {vendorRecord !== null ? (
        <VendorReceiptDialog
          onOpenChange={(next) => {
            if (!next) setVendorRecord(null);
          }}
          open
          record={vendorRecord}
        />
      ) : null}

      {dialog !== null ? (
        <ReasonDialog
          mode={dialog.mode}
          onConfirm={(result) => {
            if (result.mode === "override") {
              setOverride({
                amountSoum: result.amountSoum,
                reasonCode: result.reasonCode,
              });
            } else if (dialog.mode === "reversal") {
              /*
               * ⛔ JAVOB MAJBURIY (K-5, 2026-08-18 da o'lchangan nuqson):
               *   ilgari bu chaqiruv `onSuccess`/`onError` SIZ edi va bekor
               *   qilish o'tdimi-yo'qmi ekranda HECH NIMA o'zgarmasdi —
               *   kassir pul masalasida ko'r qolardi.
               */
              reverse.mutate(
                {
                  payment_id: dialog.paymentId,
                  reason_code: result.reasonCode,
                },
                {
                  onError: () => {
                    toast.error(t("collect.reverseFailed"));
                  },
                  onSuccess: (record) => {
                    toast.success(
                      `${t("collect.reversalEntry")} · ${record.stall_code} · ${money(record.amount_soum)}`,
                    );
                  },
                },
              );
            }
            setDialog(null);
          }}
          onOpenChange={(next) => {
            if (!next) setDialog(null);
          }}
          open
        />
      ) : null}
    </div>
  );
}
