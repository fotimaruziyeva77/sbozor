"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { ApiError, apiFetch } from "@/lib/api-client";
import type { HeadlineMetric, HeadlineUnit } from "@/lib/api-types";
import { HEADLINE_UNIT } from "@/lib/api-types";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * ⛔⛔ BOSH EKRAN KO'RSATKICHI — BITTA SON, BITTA YORLIQ (W0-F5).
 *
 * -----------------------------------------------------------------------
 * ⛔ SHARTNOMA: `{metric, value}` — VA UCHINCHI MAYDON IMKONSIZ
 * -----------------------------------------------------------------------
 * `headlineResponseSchema` — `z.strictObject`. Server bir kun
 * `secondary_value` yoki `label` qo'shsa, klient PARSE PAYTIDA yiqiladi
 * va bu ATAYIN: D-29 ning butun ma'nosi «foydalanuvchi BITTA raqamni
 * ko'radi» degan da'voda, ikkinchi son esa «qaysi biri asosiy?» degan
 * savolni tug'dirardi — va o'sha savolning javobi ROLGA bog'liq bo'lardi
 * (§10.2). Ya'ni yuzaning jimgina kengayishi klientni ROL O'QISHGA
 * qaytaradigan yagona yo'l.
 *
 * ⛔ IKKI QATLAM: server tomonda `extra="forbid"`
 * (`schemas.py::HeadlineResponse`), klient tomonda `strictObject`. Ular
 * BIR-BIRINI ALMASHTIRMAYDI: server pinini olib tashlash klientni
 * ochmaydi va aksincha (05-13 darsi — kafolat JUFTLIKDAN chiqadi).
 *
 * -----------------------------------------------------------------------
 * ⛔ SERVER MATN EMAS, KALIT QAYTARADI
 * -----------------------------------------------------------------------
 * `metric` — i18n KALITI (`headline.revenue_today` | `.review_queue` |
 * `.receipts_written`), matn EMAS (`alerting.py:1003-1008` naqshi).
 * Server matn qaytarsa u uchala locale'ni (`uz-Latn`, `uz-Cyrl`, `ru`)
 * bilishi kerak bo'lardi va i18n IKKI joyda yashardi.
 *
 * ⛔ KALITLAR TO'PLAMI SXEMADA QULFLANMAYDI (yopiq ro'yxat validatori
 *    ATAYIN ishlatilmagan) va bu 04-10 ning darsi: yopiq to'plam
 *    backendga qo'shilgan BITTA yangi metrikani butun ekranni yiqitadigan
 *    xatoga aylantirardi. Noma'lum kalit `headline.unknown` zaxira
 *    yorlig'i bilan KO'RSATILADI — jimgina yashirilmaydi.
 *
 * ⚠ Taqiqlangan validator NOMI bu faylda LITERAL yozilmaydi: qabul
 *   mezoni uni `grep` bilan SANAYDI, ya'ni izohning o'zi darvozani
 *   qizartirardi (`collect-surface.test.mjs` da o'lchangan sinf).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ `403` — NORMAL HOLAT, XATO EMAS, VA AYNIQSA NOL EMAS (T-05-04)
 * -----------------------------------------------------------------------
 * Server huquq mos kelmasa `403 headline_unavailable` qaytaradi
 * (`me.py`) — masalan `platform_admin` da uchala huquqning birortasi
 * ham yo'q (07-03 da O'LCHANGAN fakt). Bu holatda hook `available:
 * false` beradi va `value` ⛔ `undefined` bo'lib qoladi.
 *
 * ⛔ `value: 0` QAYTARILMAYDI. Nol — O'LCHANGAN QIYMAT: «bugun hech
 *    narsa yig'ilmadi» degan ma'noni berardi va u YOLG'ON bo'lardi
 *    («o'lchanmagan sonning o'rniga NOL yozilmaydi» — 05-14 darsi).
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const HEADLINE_PATH = "/me/headline";

/* --- Birlik reyestri ------------------------------------------------------- */

/**
 * ⛔ Reyestr `api-types.ts` DA yashaydi va bu yerda QAYTA EKSPORT qilinadi.
 *
 * Sabab: `api-types.ts` — server reyestrlarining klientdagi ikkinchi
 * nusxasi uchun ajratilgan joy (o'sha fayl, `06-02` bloki), bu modul esa
 * bosh ko'rsatkichning YAGONA yuzasi (UI-SPEC §10.3 uni shu yerda
 * ko'rsatadi). Ikkinchi TA'RIF yozilmaydi — u ikki haqiqat manbai
 * bo'lardi va biri ikkinchisidan jimgina ajralib ketardi.
 */
export { HEADLINE_UNIT };
export type { HeadlineMetric, HeadlineUnit };

/**
 * Noma'lum metrika uchun ZAXIRA yorliq kaliti.
 *
 * ⛔ Jimgina YASHIRISH emas, KO'RSATISH: backend yangi ko'rsatkich
 *    qo'shganda foydalanuvchi «raqam bor, nomi hali tarjima qilinmagan»
 *    holatini ko'radi. Bo'sh ekran esa nosozlikni YASHIRARDI va uni
 *    hech kim xabar qilmasdi.
 */
export const HEADLINE_UNKNOWN_LABEL_KEY = "headline.unknown" as const;

/** `metric` reyestrda bormi — tip darajasida ham toraytiradi. */
export function isHeadlineMetric(metric: string): metric is HeadlineMetric {
  return Object.hasOwn(HEADLINE_UNIT, metric);
}

/**
 * Metrikaning birligi; noma'lum kalitda ⛔ `"count"`.
 *
 * ⛔ Zaxira AYNAN `"count"`, chunki u ENG KAM DA'VO QILADIGAN standart:
 *    `"soum"` bo'lganda ekran noma'lum songa «so'm» yozib qo'yardi va
 *    sanoqni PULGA aylantirardi — bu Pitfall 1 ning aynan o'zi, faqat
 *    orqa eshikdan.
 */
export function headlineUnitOf(metric: string): HeadlineUnit {
  return isHeadlineMetric(metric) ? HEADLINE_UNIT[metric] : "count";
}

/** Metrikaning yorliq kaliti; noma'lum kalitda zaxira yorliq. */
export function headlineLabelKey(
  metric: string,
): HeadlineMetric | typeof HEADLINE_UNKNOWN_LABEL_KEY {
  return isHeadlineMetric(metric) ? metric : HEADLINE_UNKNOWN_LABEL_KEY;
}

/* --- Sxema ----------------------------------------------------------------- */

/**
 * `GET /me/headline` javobi — ⛔ AYNAN IKKI MAYDON.
 *
 * ⛔ `strictObject` MAJBURIY: `parse({metric, value, secondary_value})`
 *    THROW qilishi kerak. `z.object` bo'lsa ortiqcha maydon JIMGINA
 *    olib tashlanardi va yuzaning kengayishi hech qayerda ko'rinmasdi.
 *
 * ⛔ `_soum` bilan tugaydigan maydon YO'Q va bu alohida o'lchanadi
 *    (G-33(e)): pul birligi javobda emas, `HEADLINE_UNIT` da.
 *
 * ⚠ `value: z.number().int()` — birlikdan QAT'I NAZAR butun son. So'm ham
 *   butun (`money.py`: `BIGINT`), sanoq ham. Klientda pul arifmetikasi
 *   YO'Q: son serverdan kelgan holicha formatlanadi.
 */
export const headlineResponseSchema = z.strictObject({
  /** i18n KALITI — matn emas. */
  metric: z.string().min(1),
  /** ⛔ Yagona son. Kassir uchun bu SANOQ (Pitfall 1). */
  value: z.number().int(),
});

export type HeadlineResponse = z.infer<typeof headlineResponseSchema>;

/* --- Query kaliti (TUG'ILISHIDANOQ doiralangan, §5.4) --------------------- */

/**
 * ⛔ BIRINCHI ARGUMENT — `marketId` (04-10 qarori).
 *
 * `domainKey` `market-queries.ts` DAN import qilinadi, ikkinchi nusxa
 * yaratilmaydi: kalit `["m", marketId, "headline"]` bo'ladi va shu bilan
 * `["m", marketId]` prefiksi bo'yicha tozalashga ham TUSHADI. Global
 * kalit konstantalari (`HEADLINE_KEY`) ATAYIN yozilmaydi — ular
 * doiralashni chetlab o'tishning eng qulay yo'li edi (CR-01).
 *
 * ⚠ REJADAN OG'ISH (ochiq qayd): reja qabul mezoni `headlineKey("m1")[0]
 *   === "m1"` deb yozgan, ya'ni `["m1", "headline"]` yalang'och shaklini
 *   nazarda tutgan. Rejaning O'ZI keltirgan manba —
 *   `tenant-cache.test.tsx` ning «doiralash qoidasi» — esa buning
 *   TESKARISINI qulflaydi: `key[0] === "m"`, `key[1] === marketId`
 *   (o'sha fayl, 175-178). Yalang'och shakl `domainKey` prefiksidan
 *   tashqarida qolardi, ya'ni kodbazadagi YAGONA doiralash konvensiyasi
 *   ikkiga bo'linardi. Rejaning ⛔ bilan belgilangan qoidasi — «birinchi
 *   ARGUMENT `marketId`» — bu shaklda to'liq bajariladi.
 */
export const headlineKey = (marketId: string) =>
  domainKey(marketId, "headline");

/* --- Hook ------------------------------------------------------------------ */

/**
 * Bosh ko'rsatkichning klientdagi holati.
 *
 * ⛔ `metric`/`value` UNDEFINED bo'la oladi va `available` ular bilan
 *    BIRGA yuradi: «ko'rsatkich yo'q» holatida komponent kartani UMUMAN
 *    chizmaydi (§10.2), ya'ni nol ham, tire ham, bo'sh qator ham
 *    ko'rinmaydi.
 */
export type HeadlineState = {
  /** `false` — huquq yo'q (`403`) yoki javob kelmadi: karta CHIZILMAYDI. */
  available: boolean;
  /** i18n kaliti (server bergan holicha). */
  metric: string | undefined;
  /** ⛔ `403` da `undefined` — `0` EMAS. */
  value: number | undefined;
  isPending: boolean;
  isError: boolean;
};

/**
 * `GET /me/headline` — huquqqa qarab SERVER tanlagan bitta ko'rsatkich.
 *
 * =========================================================================
 * ⛔⛔ `403` XATO EMAS — U SHU YERDA «KO'RSATKICH YO'Q» HOLATIGA
 *     AYLANTIRILADI.
 *
 *   `queryFn` ichida ushlanishi ATAYIN: agar u `useQuery` ning xato
 *   kanaliga tushsa, TanStack uni «nosozlik» deb belgilardi va
 *   `retry: false` bo'lsa ham React Query DevTools'da qizil holat
 *   qolardi — keyingi ijrochi esa uni TUZATILADIGAN nosozlik deb
 *   o'qirdi. Huquqi yo'q foydalanuvchi uchun `403` — TO'G'RI javob.
 *
 * ⛔ `null` — «ko'rsatkich yo'q» ning YAGONA belgisi. `0` qaytarish
 *    kartani O'LCHANGAN NOL bilan chizardi (T-05-04).
 * =========================================================================
 *
 * ⚠ `retry: false`: `403` allaqachon normal holat, tarmoq xatosida esa
 *   qayta urinish bosh ekranni «raqam hozir chiqadi» kutishiga
 *   majburlardi — §10.2 bo'yicha bu holatda karta UMUMAN chizilmaydi.
 *
 * ⚠ AVTOMATIK YANGILANISH TAYMERI YO'Q (§10.5): o'qib turgan paytda
 *   jimgina o'zgaradigan raqam «men boshqa raqam ko'rgandim» nizosining
 *   manbai. `refetchOnWindowFocus` standart holida qoladi.
 */
export function useHeadline(marketId: string | null): HeadlineState {
  const query = useQuery({
    queryKey: headlineKey(marketId ?? ""),
    queryFn: async (): Promise<HeadlineResponse | null> => {
      try {
        return await apiFetch(HEADLINE_PATH, {
          schema: headlineResponseSchema,
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 403) return null;
        throw error;
      }
    },
    enabled: marketId !== null,
    retry: false,
  });

  const data = query.data ?? null;

  return {
    available: data !== null,
    metric: data?.metric,
    value: data?.value,
    isPending: query.isPending,
    isError: query.isError,
  };
}
