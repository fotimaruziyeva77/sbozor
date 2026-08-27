"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import {
  ADJUSTMENT_REASONS,
  ANOMALY_KINDS,
  soumSchema,
} from "@/lib/api-types";
import type {
  AdjustmentReasonValue,
  AnomalyKindValue,
} from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * YOZILGAN HISOB, TUZATISH VA ANOMALIYA — DIREKTOR YUZASINING SERVER HOLATI.
 *
 * `occupancy-queries.ts` TO'LIQ SHABLON: `?day=` parametrli hisobot
 * so'rovlari va standart keshlash.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA U `billing-pending-queries.ts` DAN AJRATILGAN (W0-F3, §5.3)
 * -----------------------------------------------------------------------
 * Bu modulda hisob identifikatori QONUNIY va MAJBURIY — usiz DL-3
 * (tafsilot dialogi) ochilmaydi. Aynan shu sababdan u proyeksiya moduli
 * bilan bitta faylda yashamaydi: aralash faylda `collect-surface.test.mjs`
 * ning taqiqlangan nomlar skani KONTEKSTGA BOG'LIQ shartga aylanardi.
 *
 * Ikki modul = ikki kesh siyosati ham. Bu yerdagi javob O'ZGARMAS (D-07:
 * hisob yaratilgach tahrirlanmaydi, tuzatish ALOHIDA yozuv bo'lib
 * qo'shiladi), ya'ni 60 s `staleTime` va standart `gcTime` XAVFSIZ.
 * Proyeksiyada esa ikkalasi ham NOL bo'lishi shart (§9.4).
 *
 * -----------------------------------------------------------------------
 * ⛔ MUTATSIYA BU MODULDA YO'Q VA BO'LMAYDI HAM
 * -----------------------------------------------------------------------
 * Hisobni tahrirlaydigan marshrut serverda umuman yozilmagan (D-07:
 * shartsiz `BEFORE UPDATE OR DELETE` trigger). Tuzatish `charge_adjustments`
 * orqali, sabab-kod bilan keladi va uning YOZUV yuzasi 6-fazada
 * ochilmaydi. Anomaliya ro'yxatida ham case oqimi (holat, mas'ul, qaror,
 * [Ko'rildi]) YO'Q — 7-fazaning egaligi (§11.4).
 * =============================================================================
 */

/* --- Yo'l konstantalari ---------------------------------------------------- */

export const BILLING_CHARGES_PATH = "/billing/charges";
export const BILLING_ANOMALIES_PATH = "/billing/anomalies";

/* --- Reyestrlar (yopiq to'plamlar) ---------------------------------------- */

/*
 * ⛔⛔ REYESTRLAR `api-types.ts` DAN IMPORT QILINADI — NUSXA YO'Q (06-11).
 *
 * 06-03 bu modulda `ANOMALY_KINDS` va `ADJUSTMENT_REASONS` ni VAQTINCHA
 * `as const` literal sifatida saqlagan edi: `api-types.ts` o'sha to'lqinda
 * 06-02 ning egaligida edi va ikki worktree bitta faylni yozsa merge
 * paytida jimgina `Duplicate identifier` chiqardi.
 *
 * ⛔ Endi nusxa OLIB TASHLANDI va sabab MEXANIK: G-24 va G-26 darvozalari
 *    (`scripts/billing-copy.test.mjs`) reyestrni AYNAN `api-types.ts` dan
 *    o'qiydi va uni Python enumlari hamda uchala locale bilan taqqoslaydi.
 *    Ikkinchi nusxa qolganda ikki reyestr AJRALIB KETISHI mumkin edi va
 *    darvoza har safar YASHIL qolardi — u ajralgan nusxani umuman
 *    ko'rmaydi.
 *
 * ⚠ Ko'zgu MANTIG'I o'zgarmaydi: `api-types.ts` ning o'zi Python enumining
 *   ATAYIN yozilgan ikkinchi nusxasi (til chegarasi tufayli kompilyator
 *   ularni solishtira olmaydi). Bu yerdagi import esa UCHINCHI nusxani
 *   yo'q qiladi — u qo'riqlanmagan yagona nusxa edi.
 */

/**
 * Anomaliya turlari (BILL-04, §11.4).
 *
 * ⛔ UCHALASI ALOHIDA SANALADI va bitta «anomaliya» soniga QO'SHILMAYDI
 *    (D-05): «ko'ra olmadik» ≠ «band, lekin biriktirilmagan». Ikkisini
 *    qo'shish ko'r nuqtadan tushum da'vosi to'qish bo'lardi.
 */
export type AnomalyKind = AnomalyKindValue;

/**
 * Tuzatish yo'nalishi — MUSBAT KATTALIK + yo'nalish ustuni (C-5).
 *
 * Manfiy summa yozilmaydi: `CHECK (amount_soum > 0)` har moliyaviy
 * jadvalda majburiy va `assert_safe_soum()` manfiy qiymatni rad etadi.
 * Belgi FAQAT ko'rinishda tug'iladi.
 */
export const ADJUSTMENT_DIRECTIONS = ["increase", "decrease"] as const;

export type AdjustmentDirection = (typeof ADJUSTMENT_DIRECTIONS)[number];

/**
 * Tuzatish sabab-kodlari — YOPIQ ro'yxat (D-19, §13.5).
 *
 * ⛔ `other`/`custom` YO'Q: erkin matn hisobotda ENG KATTA GURUH bo'lib
 *    qolardi va sabab tahlilini ma'nosiz qilardi. To'plamning O'ZI
 *    `api-types.ts` da (yuqoridagi blokka qarang).
 */
export type AdjustmentReason = AdjustmentReasonValue;

/* --- Sxemalar -------------------------------------------------------------- */

/**
 * `GET /billing/charges?day=…` jadvalining bitta qatori (§11.2).
 *
 * ⛔ Sotuvchi NOMI bu javobda YO'Q — faqat `vendor_id`. Ism KLIENTDA,
 *    mavjud va AUDIT QILINGAN `GET /vendors` marshrutidan joinlanadi
 *    (§5.5). Sabab: `PERSONAL_ROUTES` reyestri o'smasin — yangi moliyaviy
 *    marshrutga shaxsiy-ma'lumot qo'riqchisini o'rnatish keyingi
 *    ijrochi ko'chiradigan naqsh bo'lardi.
 *
 * ⛔ `outstanding_soum` — HISOBLANADIGAN qoldiq (BILL-03). Saqlangan
 *    ustun ham, shunday nomli ustun ham yo'q.
 */
export const chargeRowSchema = z.strictObject({
  charge_id: z.uuid(),
  stall_code: z.string(),
  vendor_id: z.uuid(),
  service_date: z.string(),
  /** Tarif summasi (D-09) — tuzatish bo'lsa hisob summasidan farq qiladi. */
  tariff_amount_soum: soumSchema,
  amount_soum: soumSchema,
  outstanding_soum: soumSchema,
});

export type ChargeRow = z.infer<typeof chargeRowSchema>;

/**
 * `GET /billing/charges?day=…` javobining O'RAMI (06-08 kontrakti).
 *
 * =========================================================================
 * ⛔⛔ O'RAM `{items}` EMAS — `{day, rows, charge_count, charged_soum}`.
 *
 *   06-03 bu sxemani `z.strictObject({ items })` deb yozgan edi, 06-08
 *   esa serverni AYNAN yuqoridagi to'rt kalit bilan shipladi va bu
 *   kontrakt `test_billing_api.py` da to'plam TENGLIGI bilan qulflangan.
 *   Ya'ni klientni «serverni `items` ga qaytarish» bilan tuzatib
 *   bo'lmaydi — nol-natija hisoblagichlari D-05 ning talabi.
 *
 * ⛔ `day` ATAYIN javobda: standart kun SERVERDA hisoblanadi (KECHA,
 *    §11.1) va klient qaysi kunni ko'rayotganini javobning O'ZIDAN
 *    biladi. Aks holda «kun tanlanmagan» holatda ekran o'z taxminini
 *    ko'rsatardi va u server bilan bir kun ajralib ketardi.
 *
 * ⛔ IKKALA HISOBLAGICH HAM NOL BO'LGANDA HAM KELADI: «bu kunda hisob
 *    yo'q» (C-3 bo'yicha NORMAL) va «hisoblagich ishlamayapti» bir xil
 *    ko'rinmasligi kerak.
 * =========================================================================
 */
export const chargeListSchema = z.strictObject({
  day: z.string(),
  rows: z.array(chargeRowSchema),
  charge_count: z.number().int(),
  charged_soum: soumSchema,
});

export type ChargeList = z.infer<typeof chargeListSchema>;

/**
 * DL-3 ning 4-bo'limi — tuzatish yozuvi (§11.3).
 *
 * ⛔ Bo'sh massiv YASHIRILMAYDI: dialog «Tuzatish yo'q» jumlasini
 *    ko'rsatadi. Nol — natija, yo'qlik emas.
 */
export const chargeAdjustmentSchema = z.strictObject({
  adjustment_id: z.uuid(),
  direction: z.enum(ADJUSTMENT_DIRECTIONS),
  amount_soum: soumSchema,
  reason_code: z.enum(ADJUSTMENT_REASONS),
  /** Aktor — identifikator; ismi §5.5 bo'yicha alohida marshrutdan. */
  actor_user_id: z.uuid().nullable(),
  created_at: z.string(),
});

export type ChargeAdjustment = z.infer<typeof chargeAdjustmentSchema>;

/**
 * DL-3 ning 5-bo'limi — dalil kadri (§11.3, BILL-02).
 *
 * ⛔ `snapshot_id` NULLABLE va `null` bo'lgan qator uchun kadr bloki
 *    UMUMAN chizilmaydi: na placeholder, na «yuklanmadi». Bu 05-14 ning
 *    darsi — marshrut bermagan qatorni to'qish (stub) ham, bo'sh jadval
 *    ham RAD ETILGAN.
 *
 * ⛔ Tarif identifikatori bu yerda YO'Q va u ATAYIN yo'q: direktorga ham
 *    ma'nosiz identifikator (§11.3, 2-bo'lim).
 */
export const chargeEvidenceSchema = z.strictObject({
  snapshot_id: z.uuid().nullable(),
  slot_time: z.string(),
});

export type ChargeEvidence = z.infer<typeof chargeEvidenceSchema>;

/** `GET /billing/charges/{id}` — DL-3 ning besh bo'limi bitta javobda. */
export const chargeDetailSchema = z.strictObject({
  charge_id: z.uuid(),
  service_date: z.string(),
  stall_code: z.string(),
  tariff_amount_soum: soumSchema,
  amount_soum: soumSchema,
  adjustments: z.array(chargeAdjustmentSchema),
  evidence: z.array(chargeEvidenceSchema),
});

export type ChargeDetail = z.infer<typeof chargeDetailSchema>;

/**
 * `GET /billing/anomalies?day=…` ning bitta qatori (§11.4).
 *
 * =========================================================================
 * ⛔ JUFTLANGAN INVARIANT — C-12 ning `CHECK` ining KLIENT TOMONIDAGI
 *    AYNAN TAKRORI:
 *
 *        (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)
 *
 *    Ya'ni «qamrovsiz rasta» dalilsiz, qolgan ikki tur esa dalil bilan
 *    keladi. Ikkala yo'nalish ham ifodalab bo'lmaydigan qilinadi:
 *    «qamrovsiz, lekin kadri bor» — ko'r nuqtadan dalil da'vosi;
 *    «band, lekin kadrsiz» — hukmning dalilsiz qolishi.
 *
 * ⛔ UI'da bu shart `disabled` tugma bilan EMAS, affordansning UMUMAN
 *    chizilmasligi bilan takrorlanadi: o'chirilgan tugma «kadr bor,
 *    lekin ochilmayapti» deb YOLG'ON gapirardi (§11.4).
 * =========================================================================
 */
export const anomalyRowSchema = z.strictObject({
  anomaly_id: z.uuid(),
  kind: z.enum(ANOMALY_KINDS),
  stall_code: z.string(),
  service_date: z.string(),
  snapshot_id: z.uuid().nullable(),
})
  .refine(
    (value) =>
      (value.kind === "no_coverage_stall") === (value.snapshot_id === null),
    {
      message:
        "C-12 JUFTLIGI BUZILDI: `no_coverage_stall` dalilsiz, qolgan turlar " +
        "esa dalil bilan kelishi SHART. `(kind = 'no_coverage_stall') = " +
        "(snapshot_id IS NULL)` — bu DB CHECK ining aynan takrori (D-05).",
    },
  );

export type AnomalyRow = z.infer<typeof anomalyRowSchema>;

/**
 * `GET /billing/anomalies?day=…` javobining O'RAMI (06-08 kontrakti).
 *
 * =========================================================================
 * ⛔⛔ UCH ALOHIDA SANOQ — VA UMUMIY `anomaly_count` MAYDONI YO'Q (D-05).
 *
 *   «Ko'ra olmadik» (`no_coverage_stall`) ≠ «band, lekin biriktirilmagan»
 *   (`unassigned_occupied`). Ikkisini bitta songa qo'shish KO'R NUQTADAN
 *   TUSHUM DA'VOSI TO'QISH bo'lardi. Yagona son MAVJUD bo'lsa ekran uni
 *   ko'rsatardi va farq matn darajasida yo'qolardi.
 *
 * ⛔ Klient ham ularni QO'SHMAYDI: uchala son serverdan alohida keladi va
 *    `strictObject` ortiqcha (masalan, agregat) maydonni PARSE PAYTIDA
 *    rad etadi.
 *
 * ⛔ UCHALASI HAM NOL BO'LGANDA HAM KELADI — nol NATIJA, yo'qlik emas.
 * =========================================================================
 */
export const anomalyListSchema = z.strictObject({
  day: z.string(),
  rows: z.array(anomalyRowSchema),
  unassigned_count: z.number().int(),
  closed_day_count: z.number().int(),
  no_coverage_count: z.number().int(),
});

export type AnomalyList = z.infer<typeof anomalyListSchema>;

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

export const chargesKey = (marketId: string, day: string) =>
  domainKey(marketId, "billing-charges", day);

export const chargeDetailKey = (marketId: string, chargeId: string) =>
  domainKey(marketId, "billing-charges", "detail", chargeId);

export const anomaliesKey = (marketId: string, day: string) =>
  domainKey(marketId, "billing-anomalies", day);

/**
 * Yozilgan hisobning `staleTime` i — 60 SONIYA.
 *
 * ⚠ Proyeksiyaning NOLI bu yerga KO'CHIRILMAYDI va aksincha ham: qaror
 *   har domenda QAYTA hisoblanadi. Hisob D+1 04:10 da bir marta yoziladi
 *   va undan keyin O'ZGARMAYDI (D-07) — ya'ni 60 s ichida ekranda
 *   noto'g'ri raqam paydo bo'lishining YO'LI yo'q. Qo'shiladigan yagona
 *   narsa — yangi tuzatish yozuvi, u esa kun ichida kamdan-kam bo'ladi.
 */
export const CHARGE_STALE_TIME_MS = 60_000;

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Yozilgan hisoblar ----------------------------------------------------- */

/**
 * `GET /billing/charges?day=…` — kun kesimidagi yozilgan hisoblar (§11.2).
 *
 * ⚠ Bu blok `day = bugun` da UMUMAN chizilmaydi (§9.3, 7-kanal): hisob
 *   D+1 04:10 da tug'iladi, ya'ni bugungi kun uchun u MAVJUD EMAS. Shart
 *   sahifada qo'llanadi; hook esa `enabled` orqali boshqariladi va
 *   o'zi kun haqida qaror qabul qilmaydi.
 */
export function useCharges(day: string, options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: chargesKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${BILLING_CHARGES_PATH}?day=${encodeURIComponent(day)}`, {
        schema: chargeListSchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: CHARGE_STALE_TIME_MS,
  });
}

/**
 * `GET /billing/charges/{id}` — DL-3 tafsiloti.
 *
 * ⚠ Dialog OCHILGANDA so'raladi (`enabled`), oldindan yuklanmaydi: 300–1000
 *   rastali bozorda har qator uchun tafsilot tortish sahifani og'irlashtirardi
 *   va foydasi nol edi (dialog kamdan-kam ochiladi).
 */
export function useChargeDetail(
  chargeId: string | null,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: chargeDetailKey(marketId ?? "", chargeId ?? ""),
    queryFn: () =>
      apiFetch(`${BILLING_CHARGES_PATH}/${encodeURIComponent(chargeId ?? "")}`, {
        schema: chargeDetailSchema,
      }),
    enabled:
      marketId !== null && chargeId !== null && (options?.enabled ?? true),
    staleTime: CHARGE_STALE_TIME_MS,
  });
}

/* --- Anomaliyalar ---------------------------------------------------------- */

/**
 * `GET /billing/anomalies?day=…` — uch tur, uch yorliq (§11.4).
 *
 * ⛔ Klient turlarni QO'SHMAYDI va umumiy «anomaliya soni» chiqarmaydi:
 *    agregatning o'zi D-05 ni buzardi. Har tur o'z yorlig'i, o'z soni va
 *    o'z dalil qoidasi bilan yashaydi.
 */
export function useAnomalies(day: string, options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: anomaliesKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${BILLING_ANOMALIES_PATH}?day=${encodeURIComponent(day)}`, {
        schema: anomalyListSchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: CHARGE_STALE_TIME_MS,
  });
}
