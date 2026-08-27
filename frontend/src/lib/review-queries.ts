"use client";

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, apiRequest } from "@/lib/api-client";
import {
  answerRequestBody,
  answerResponseSchema,
  reviewBudgetResponseSchema,
  reviewItemSchema,
} from "@/lib/api-types";
import type { HumanAnswer } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * NOANIQ NAVBATNING SERVER HOLATI (05-10 kontrakti, UI-SPEC §5.4, §8.5).
 *
 * `camera-zone-queries.ts` TO'LIQ SHABLON. Beshinchi modul o'sha sababdan
 * ochildi: har domenning bekor qilish to'plami O'ZINIKI.
 *
 * ⛔⛔ KO'R AUDIT BU YERDA YASHAMAYDI — U ALOHIDA MODUL
 *     (`lib/blind-audit-queries.ts`, UI-SPEC §5.3).
 *
 *     Uni shu faylga qo'shish TEXNIK JIHATDAN to'g'ri bo'lardi: bir
 *     domen, bir backend, o'xshash shakl. Rad etiladi, chunki G-12
 *     darvozasi FAYL TO'PLAMINI skanerlaydi, satrni emas. Aralash
 *     modulda shart «taqiqlangan nom faqat `uncertain` funksiyalarida
 *     uchramaydi» degan KONTEKSTGA BOG'LIQ holga aylanardi — ya'ni
 *     mexanik tekshirib bo'lmaydigan, kod-ko'rikka qaytadigan shartga.
 *     Takrorlanishning narxi ~40 qator; xolislik kafolatining narxi
 *     undan ANCHA yuqori.
 *
 * ⛔ POLL YO'Q (§8.5, ikkinchi qator). Navbat SO'ROV BO'YICHA yuriydi:
 *    javob -> `mutate` -> bekor qilish -> keyingi band. Poll «men javob
 *    berayotganimda band o'zgardi» holatini tug'dirardi — nazoratchi
 *    ko'rgan rasmga javob berardi-yu, javob BOSHQA bandga yozilardi.
 *
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4): `domainKey`
 *   `market-queries.ts` DAN import qilinadi, ikkinchi nusxa
 *   YARATILMAYDI, va marketsiz kalit konstantasi bu modulda UMUMAN
 *   YO'Q.
 * =============================================================================
 */

/* --- Yo'l konstantalari --------------------------------------------------- */

export const REVIEW_PATH = "/review";
export const SNAPSHOTS_PATH = "/snapshots";

/* --- Query kalitlari ------------------------------------------------------- */

export const uncertainNextKey = (marketId: string) =>
  domainKey(marketId, "review-uncertain", "next");

export const reviewBudgetKey = (marketId: string, day: string) =>
  domainKey(marketId, "review-budget", day);

/**
 * ⛔ NOANIQ NAVBATNING BEKOR QILISH PREFIKSI — `review-budget` NI
 *    QAMRAMAYDI va bu ataylab: byudjet IKKALA navbatning sonini olib
 *    yuradi, ya'ni uni `review-uncertain` prefiksiga qo'yish ko'r
 *    auditning hisoblagichini noaniq navbatning holatiga bog'lardi.
 */
const uncertainPrefix = (marketId: string) =>
  domainKey(marketId, "review-uncertain");

/**
 * Dalil kadrining kesh kaliti — IKKALA navbat uchun UMUMIY.
 *
 * =========================================================================
 * ⚠ NEGA U `review-uncertain` YOKI `blind-audit` PREFIKSIDA EMAS.
 *
 *   Kadr — nazoratchi ikkala navbatda ham ko'radigan BIR XIL bayt, va
 *   unda tizimning javobi YO'Q: u shunchaki rasm. Uni ikkala prefiksga
 *   ko'chirish bir xil baytni ikki marta so'rashga majburlardi.
 *
 *   Ko'r auditning kesh kafolati (§14.3, 4-qatlam) BUZILMAYDI, chunki u
 *   PAYLOAD haqida — «tizim javobi kesh grafida qolmasin». Kadr esa
 *   `gcTime: 0` bilan yuritiladi, ya'ni komponent yopilishi bilan
 *   grafdan chiqadi. Sabab: kadr TASHRIFCHINING shaxsiy ma'lumoti
 *   (§14.2) va uni xotirada ushlab turish uchun hech qanday sabab yo'q.
 * =========================================================================
 */
export const evidenceImageKey = (marketId: string, snapshotId: string) =>
  domainKey(marketId, "review-evidence", snapshotId);

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `camera-zone-queries.ts:95-98` bilan AYNI sabab va AYNI shakl:
 * `useAuthStore()` ni har hookda takrorlash «bittasi tushib qoladi»
 * xatosini kafolatlardi. Funksiya EKSPORT QILINMAYDI.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Navbatdagi band ------------------------------------------------------- */

/**
 * `GET /review/uncertain/next` — navbatdagi BITTA band.
 *
 * ⛔ RO'YXAT MARSHRUTI YO'Q va bo'lmaydi (D-18). Server bitta band
 *    qaytaradi, klient esa bitta bandni ko'rsatadi — «har qatorda ikki
 *    tugmali ro'yxat» yo'li shu bilan yopiladi (UI-SPEC §7.3).
 *
 * ⚠ `retry: false` MAJBURIY: bo'sh navbat va tugagan byudjet ikkalasi
 *   ham 409 bilan keladi, ya'ni ular NORMAL holatlar. Qayta urinish
 *   ularni «xato» ga aylantirib, ekranni uch marta qayta yuklardi.
 *
 * ⚠ `enabled: marketId !== null` — KONTRAKT (`market-queries.ts:186-192`),
 *   qulaylik emas: bozorsiz sessiyada javob `409 market_not_selected`
 *   bo'lardi va u kesh grafida yashab qolardi.
 */
export function useUncertainNext(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: uncertainNextKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(`${REVIEW_PATH}/uncertain/next`, { schema: reviewItemSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    retry: false,
    gcTime: 0,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}

/* --- Kunlik byudjet -------------------------------------------------------- */

/**
 * `GET /review/budget?day=…` — IKKALA hisoblagich (UI-SPEC §7.2).
 *
 * ⛔ POLL YO'Q (§8.5): hisoblagich faqat nazoratchining O'Z javobidan
 *    o'zgaradi, ya'ni uni fonda so'rash mavjud bo'lmagan hodisani kutish
 *    bo'lardi.
 */
export function useReviewBudget(day: string, options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: reviewBudgetKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${REVIEW_PATH}/budget?day=${encodeURIComponent(day)}`, {
        schema: reviewBudgetResponseSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    refetchOnWindowFocus: false,
  });
}

/* --- Javob ----------------------------------------------------------------- */

/**
 * `POST /review/{id}/answer` — BITTA topshiriqqa BITTA javob (D-18).
 *
 * =========================================================================
 * ⛔ TANA MASSIV EMAS VA HECH QACHON MASSIV BO'LMAYDI.
 *
 *    `answerRequestBody()` AYNAN BITTA obyekt qaytaradi va uning tipi
 *    ham shunday. «Tanlanganlarni tasdiqlash» yo'li klientda ham
 *    yozilmaydi: server tomonda uning yo'qligi OpenAPI skani bilan
 *    o'lchangan (05-10 `test_no_bulk_approve_endpoint`), bu yerda esa
 *    `review-session.test.tsx` DOM'da checkbox yo'qligini va mutatsiya
 *    tanasi massiv emasligini o'lchaydi (G-18b).
 * =========================================================================
 *
 * ⚠ `shown_ai_verdict` KLIENTDAN YUBORILMAYDI va uning yo'li ham yo'q:
 *   `answerRequestBody()` faqat bitta maydon quradi. Qiymat SERVERDA
 *   hisoblanadi (D-17, 3-himoya) — klient yuborsa u YOLG'ON gapira
 *   olardi.
 *
 * ⚠ BEKOR QILISH `invalidate` BILAN VA BU YERDA U TO'G'RI: noaniq
 *   navbatda ko'rilgan bandni keshda qoldirish xolislikka ta'sir
 *   qilmaydi (tizim javobi payloadda umuman yo'q). Ko'r auditda esa
 *   `remove` MAJBURIY va sabab boshqa — `blind-audit-queries.ts` ga
 *   qarang.
 */
export function useAnswerUncertainItem(day: string) {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: { assignmentId: string; answer: HumanAnswer }) =>
      apiFetch(
        `${REVIEW_PATH}/${encodeURIComponent(input.assignmentId)}/answer`,
        {
          method: "POST",
          body: answerRequestBody(input.answer),
          schema: answerResponseSchema,
        },
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: uncertainPrefix(marketId) });
      void client.invalidateQueries({
        queryKey: reviewBudgetKey(marketId, day),
      });
    },
  });
}

/* --- Dalil kadri ----------------------------------------------------------- */

/**
 * `GET /api/v1/snapshots/{id}/image` — SESSIYA TOKENI bilan, proxy orqali.
 *
 * ⚠ BRAUZERNING O'ZI SO'ROV YUBORA OLMAYDI: marshrut sessiya tokenini
 *   talab qiladi va `<img>` elementi sarlavha qo'sha olmaydi. Shuning
 *   uchun baytlar `apiRequest` bilan olinadi va brauzer ichidagi
 *   VAQTINCHALIK havolaga aylantiriladi — u sahifadan tashqariga
 *   chiqmaydi, ulashilmaydi va komponent yopilganda BEKOR QILINADI
 *   (`camera-zone-queries.ts:290-315` naqshi).
 *
 * ⛔ IMZOLANGAN (oldindan avtorizatsiyalangan) HAVOLA SO'RALMAYDI va
 *    berilmaydi ham (§14.2): kadr tashrifchilarning shaxsiy ma'lumoti va
 *    uning yagona yuzasi — `core-api` proxysi, u esa `audit_read` yozadi.
 *    ⚠ Taqiqlangan token bu izohda ATAYIN yozilmagan: `snapshot-copy.
 *      test.mjs` xom manbani skanerlaydi va izohdagi nusxa darvozani
 *      o'zi qizartirardi (03-07 qoidasi).
 *
 * ⚠ 403 HAMON MUMKIN, LEKIN SABABI ENDI BOSHQA — VA BU FARQ MUHIM.
 *    05-13 gacha sof `inspector` roli SHU MARSHRUTDA har doim 403
 *    olardi: uning huquqi `OCCUPANCY_REVIEW`, marshrut esa `CAMERA_VIEW`
 *    talab qilardi. 05-15 buni yopdi — marshrut endi
 *    `EVIDENCE_FRAME_PERMISSIONS` («`CAMERA_VIEW` YOKI
 *    `OCCUPANCY_REVIEW`») ostida (`snapshots.py`), ya'ni nazoratchi
 *    dalil kadrini KO'RADI. Qolgan 403 yo'llari — huquqsiz rol, boshqa
 *    bozorning kadri, bloklangan hisob — va ular xato bo'lib KO'RINISHI
 *    KERAK.
 *
 * ⚠ XULQ O'ZGARMADI va u ATAYIN shunday qoldi: `frameState()` har qanday
 *    nosozlikda «tayyor emas» qaytaradi, uchala javob tugmasi
 *    `aria-disabled` bo'lib qoladi va TAXMINIY javob yozilmaydi. Rasm
 *    kelmagan holatda javob berish — o'lchovga axlat qo'shish.
 */
export function useEvidenceImageHref(snapshotId: string | null): {
  href: string | null;
  isPending: boolean;
  isError: boolean;
  retry: () => void;
} {
  const marketId = useMarketId();

  const image = useQuery({
    queryKey: evidenceImageKey(marketId ?? "", snapshotId ?? ""),
    queryFn: async () => {
      const response = await apiRequest(
        `${SNAPSHOTS_PATH}/${encodeURIComponent(snapshotId ?? "")}/image`,
      );
      return URL.createObjectURL(await response.blob());
    },
    enabled: marketId !== null && snapshotId !== null,
    gcTime: 0,
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  const href = image.data ?? null;

  useEffect(() => {
    if (href === null) return;
    return () => URL.revokeObjectURL(href);
  }, [href]);

  return {
    href,
    isPending: snapshotId !== null && image.isPending,
    isError: image.isError,
    retry: () => void image.refetch(),
  };
}
