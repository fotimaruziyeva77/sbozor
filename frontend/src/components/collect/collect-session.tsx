"use client";

import { useCallback, useId, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { DoorOpen } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { toast } from "sonner";

import { PaymentBar } from "@/components/collect/payment-bar";
import { PendingCard } from "@/components/collect/pending-card";
import { StallLookup } from "@/components/collect/stall-lookup";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ApiError } from "@/lib/api-client";
import type { PaymentMethodValue } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import {
  dropPendingAfterPayment,
  usePendingStall,
} from "@/lib/billing-pending-queries";
import type { PendingStall } from "@/lib/billing-pending-queries";
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

  /* ⛔ Rasta kodi SAHIFA HOLATIDA — URL'da EMAS (§4.5). */
  const [draft, setDraft] = useState("");
  const [submittedCode, setSubmittedCode] = useState("");
  const [method, setMethod] = useState<PaymentMethodValue | null>(null);
  const [extraAmount, setExtraAmount] = useState<number | null>(null);
  const [wrote, setWrote] = useState<PaymentRecord | null>(null);

  const shift = useOpenShift();
  const hasOpenShift =
    shift.data === undefined ? null : shift.data !== null;

  const pending = usePendingStall(submittedCode, {
    enabled: hasOpenShift === true,
  });

  const lookup = pending.data;
  const matches = lookup?.matches ?? [];
  const stall = lookup === undefined ? null : lookup.stall;
  const notFound = lookupErrorCodeOf(pending.error) === "stall_not_found";

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
  const chosenAmount = extraAmount ?? baseAmount;

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

  /** Yangi rasta — varaqning HAMMASI noldan boshlanadi. */
  const startLookup = useCallback((code: string) => {
    setSubmittedCode(code);
    setMethod(null);
    setExtraAmount(null);
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

      /* ⛔ Fokus qidiruv maydoniga QAYTADI — kassir hech nima bosmaydi. */
      inputRef.current?.focus();

      toast.success(
        `${t("collect.written")} · ${record.stall_code} · ${money(record.amount_soum)}`,
      );
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
          chosenAmount={chosenAmount}
          enteredCode={submittedCode}
          isError={pending.isError && !notFound}
          isLoading={pending.isFetching}
          onCollectDebt={setExtraAmount}
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
          stallCode={stall.stall_code}
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
    </div>
  );
}
