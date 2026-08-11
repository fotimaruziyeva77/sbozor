"use client";

import { useQuery } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import { soumSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * ⛔⛔ KUTILAYOTGAN PATTA PROYEKSIYASI — ALOHIDA MODUL (W0-F3).
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA U `billing-charge-queries.ts` GA QO'SHILMAYDI [QAROR — §5.3]
 * -----------------------------------------------------------------------
 * Qo'shish TEXNIK JIHATDAN to'g'ri bo'lardi: bir domen, bir backend,
 * o'xshash shakl, ~50 qator kamroq kod. RAD ETILADI — uch sabab bilan,
 * va uchalasi ham MEXANIK.
 *
 * 1. ⛔ G-22 (06-UI-SPEC) SHUNDAN KEYIN YOZILISHI MUMKIN BO'LADI.
 *    `scripts/collect-surface.test.mjs` taqiqlangan nomlarni BUTUN
 *    FAYLDA izlaydi — to'liq va mexanik shart. Aralash modulda o'sha
 *    nomlar QONUNIY bo'lardi (yozilgan hisob ularsiz ifodalanmaydi) va
 *    darvoza «taqiqlangan nom faqat proyeksiya funksiyalarida
 *    uchramaydi» degan KONTEKSTGA BOG'LIQ shartga aylanardi — ya'ni
 *    matn skani bilan tekshirib bo'lmaydigan, kod-ko'rikka qaytadigan
 *    shartga. Kod ko'rigi esa aynan shu sinfdagi xatoni 2 va 3-fazada
 *    15+ marta o'tkazib yuborgan.
 *
 * 2. ⛔ KESH GRAFI AJRALADI. Proyeksiya `gcTime: 0` bilan yashaydi
 *    (§9.4), yozilgan hisob esa 60 s `staleTime` bilan — u O'ZGARMAS
 *    (D-07), ya'ni keshlash xavfsiz. Bitta modulda ikki siyosat bir
 *    opsiyalar to'plamiga siqilib ketardi va ehtiyotkorroq siyosat
 *    yo'qolardi.
 *
 * 3. ⛔ TIP TIZIMI ISH QILADI. `PendingStall` da hisob identifikatori
 *    UMUMAN YO'Q, ya'ni unga murojaat KOMPILYATSIYA XATOSI. Aralash
 *    modulda tip birlashmasi (`union`) paydo bo'lardi va o'sha maydon
 *    `undefined` bo'lib JIMGINA o'tardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ PROYEKSIYA — HISOB EMAS (D-17, §9.1)
 * -----------------------------------------------------------------------
 * Bugungi kun uchun `stall_slot_occupancy` BO'SH (u D+1 03:40 da
 * to'ladi). Ya'ni «bugun band» belgisi ham, slot sanog'i ham, «bu rasta
 * pattaga tushadi» da'vosi ham SOXTA KO'RSATKICH bo'lardi. Proyeksiya =
 * TARIF + QOLDIQ, bandlik shartisiz.
 *
 * Shuning uchun hisob identifikatori bu payloadda YASHIRILMAGAN —
 * u MAVJUD EMAS. Yashirish kod-ko'rik da'vosi bo'lardi; yo'qlik esa
 * `z.strictObject` bilan o'lchanadigan xossa.
 *
 * -----------------------------------------------------------------------
 * ⛔ D-20 NING KUCHLI SHAKLI: KLIENTDA PUL ARIFMETIKASI IMKONSIZ
 * -----------------------------------------------------------------------
 * Tarifning kirish ma'lumoti (identifikatori, toifasi, amal qilish
 * boshlanishi) bu javobda YO'Q. Ya'ni summani klientda hisoblash
 * *taqiqlanmaydi* — u IMKONSIZ. Yig'indi ham serverdan keladi
 * (`total_due_soum`, §9.6): aks holda `[Qarzni ham olish]` tugmasi
 * D-20 ni BITTA QO'SHISH AMALI bilan buzardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ KESH FAQAT `removeQueries` BILAN TOZALANADI [§5.4, G-23(e)]
 * -----------------------------------------------------------------------
 * TanStack'ning `invalidate*` oilasi yozuvni keshda QOLDIRIB uni
 * «eskirgan» deb belgilaydi. `removeQueries` esa uni GRAFDAN CHIQARADI.
 * ⛔ Shu sababdan `invalidate*` chaqiruvi bu faylda UMUMAN yo'q va
 *    yo'qligi statik darvoza bilan o'lchanadi.
 *
 * ⚠⚠ 05-13 O'LCHADI: kafolat JUFTLIKDAN chiqadi. `gcTime: 0` oynani
 *    yopadi, `removeQueries` esa darhol tozalaydi — va `gcTime` bir kun
 *    oshirilsa, yolg'iz o'zi ham kafolat beradi. Shuning uchun IKKALASI
 *    ham alohida qo'riqlanadi: `removeQueries` — statik darvoza (G-23e),
 *    `gcTime`/`staleTime` — komponent testi.
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const BILLING_PENDING_PATH = "/billing/pending";

/* --- Summaning yo'qlik sabablari (YOPIQ enum, serverdan) ------------------ */

/**
 * `amount_soum === null` bo'lganda uning NOMLANGAN sababi (§9.4).
 *
 * ⛔ Ro'yxat YOPIQ va u serverning yagona so'zi: klient «taxminiy summa»
 *    ham, «oxirgi ma'lum summa» ni ham KO'RSATMAYDI. Yo'q summa — yo'q
 *    summa (D-20).
 */
export const AMOUNT_UNAVAILABLE_REASONS = [
  "market_closed",
  "tariff_missing",
] as const;

export type AmountUnavailableReason =
  (typeof AMOUNT_UNAVAILABLE_REASONS)[number];

/* --- Sxemalar -------------------------------------------------------------- */

/**
 * `GET /billing/pending?stall_code=…` — BITTA rastaning proyeksiyasi.
 *
 * =========================================================================
 * ⛔ KALITLAR TO'PLAMI AYNAN YETTITA (§9.2) va `z.strictObject` buni
 *    DINAMIK ravishda qo'riqlaydi: server bir kun ortiqcha maydon
 *    qo'shsa, klient PARSE PAYTIDA yiqiladi va ekran xato blokini
 *    ko'rsatadi.
 *
 *    Bu «buzilgan ekran» emas — bu PUL YIG'ISHNI HIMOYA QILISH:
 *    brauzerga yetgan maydon O'QILADI (DevTools, React DevTools,
 *    `JSON.stringify`), ya'ni CSS bilan yashirish yoki shartli render
 *    YETARLI EMAS (Pitfall 6).
 *
 * ⛔ IKKI QATLAM: statik darvoza (`collect-surface.test.mjs`) KOD nima
 *    yozilganini o'qiydi, bu sxema esa KOD NIMA QILISHINI o'lchaydi.
 *    Faqat statik bo'lsa `data["char" + "ge_id"]` uni chetlab o'tardi;
 *    faqat dinamik bo'lsa u faqat testda yozilgan payloadni tekshirardi.
 * =========================================================================
 */
export const pendingStallSchema = z.strictObject({
  /** ⛔ Kassir yuzasidagi YAGONA identifikator (§5.5). */
  stall_code: z.string(),
  /** «Qaysi kun uchun» — C-4 ning javobi (ISO sana). */
  service_date: z.string(),
  market_open: z.boolean(),
  /** Bugungi patta. `null` — FAQAT nomlangan sabab bilan. */
  amount_soum: soumSchema.nullable(),
  amount_unavailable_reason: z.enum(AMOUNT_UNAVAILABLE_REASONS).nullable(),
  /** Eski qarz — HISOBLANADIGAN qoldiq (BILL-03), saqlangan ustun emas. */
  outstanding_soum: soumSchema,
  /** ⛔ SERVERDA hisoblangan yig'indi (§9.6). */
  total_due_soum: soumSchema,
})
  /*
   * ⛔ JUFTLANGAN INVARIANT — naqsh `NO_COVERAGE_IS_PAIRED_CHECK` dan
   *   (`sbozor_core/models/occupancy.py`). Ikki yo'nalish IKKI ALOHIDA
   *   tekshiruvda, chunki xato xabari ikki holatni AJRATIB aytishi
   *   kerak: «sababsiz yo'q summa» va «summasi bor sabab» — ular
   *   boshqa-boshqa server nosozliklari.
   */
  .refine(
    (value) =>
      !(value.amount_soum === null && value.amount_unavailable_reason === null),
    {
      message:
        "SABABSIZ YO'Q SUMMA: `amount_soum` null, lekin sabab berilmagan. " +
        "Ekran «summa yo'q» deb ko'rsatardi va kassir NIMA UCHUN yo'qligini " +
        "bilmasdi — D-20 aynan buni taqiqlaydi (§9.4).",
    },
  )
  .refine(
    (value) =>
      !(value.amount_soum !== null && value.amount_unavailable_reason !== null),
    {
      message:
        "SUMMASI BOR SABAB: `amount_soum` bor, lekin yo'qlik sababi ham " +
        "kelgan. Ikkalasi bir vaqtda rost bo'la olmaydi va bu holat " +
        "ekranda «yopiq kun, lekin to'la» bo'lib chizilardi.",
    },
  );

export type PendingStall = z.infer<typeof pendingStallSchema>;

/**
 * `GET /billing/pending?stall_code=…` ning KO'P MOSLIK javobi (§8.3).
 *
 * =========================================================================
 * ⛔⛔ SERVER IKKI SHAKLDAN AYNAN BITTASINI QAYTARADI (06-08 kontrakti).
 *
 *   Kassir kodni PREFIKS sifatida teradi. `"1"` bozorda yo'q, lekin `"10"`
 *   va `"100"` bor bo'lsa summa UMUMAN hisoblanmaydi — taxminiy summa
 *   ko'rsatish §9.4 ning aynan taqiqlagan xatosi. O'shanda javob faqat
 *   KODLAR ro'yxati bo'ladi (`code_sort` tartibi SERVERDA, klientda emas).
 *
 * ⛔ 06-03 bu shaklni umuman bilmasdi: `usePendingStall` faqat TEKIS
 *    javobni parse qilardi, ya'ni ko'p moslikda ekran «xato» blokini
 *    ko'rsatardi va kassir uchun rasta YO'Q bo'lib ko'rinardi.
 *
 * ⛔ JUFTLANGAN INVARIANT — serverning `_exactly_one_shape` validatorining
 *    AYNAN takrori: `stall` va `matches` bir vaqtda to'lgan bo'la olmaydi.
 *    Ikkalasi ham to'lgan javobda kassir ro'yxatdan BOSHQA rastani tanlab,
 *    ekranda TURGAN summani to'lardi — §9.4 ning «eski summa yangi rasta
 *    ostida» xatosi, faqat bitta so'rov ichida.
 * =========================================================================
 */
export const pendingLookupSchema = z
  .strictObject({
    matches: z.array(z.string()),
    stall: pendingStallSchema.nullable(),
  })
  .refine((value) => !(value.stall !== null && value.matches.length > 0), {
    message:
      "IKKI SHAKL BIR VAQTDA: `stall` to'lgan va `matches` ham bo'sh emas. " +
      "Aynan bitta moslikda ro'yxat BO'SH bo'ladi, ko'p moslikda esa summa " +
      "UMUMAN hisoblanmaydi (§8.3, §9.4).",
  });

/**
 * Marshrutning IKKALA shakli — birlashma.
 *
 * ⚠ Ikki shakl DISJUNKT: tekis javobda `matches` kaliti yo'q, ro'yxat
 *   javobida esa `service_date` yo'q, va ikkala sxema ham `strictObject`.
 *   Ya'ni birlashma qaysi shox ekanini TAXMIN QILMAYDI — ortiqcha kalitli
 *   javob ikkala shoxda ham yiqiladi.
 */
export const pendingLookupResponseSchema = z.union([
  pendingStallSchema,
  pendingLookupSchema,
]);

/**
 * Qidiruv natijasining YAGONA klient shakli.
 *
 * =============================================================================
 * ⛔⛔ BU YERDA `matchesRequestedCode` MAYDONI BOR EDI — U OLIB TASHLANDI
 *     (WR-05), VA SABAB DOKUMENTATSIYA TOZALASH EMAS.
 *
 * Maydon «§9.4 ning IKKINCHI qatlami» deb e'lon qilingan, hisoblangan,
 * eksport qilingan va HECH KIM O'QIMAGAN edi. Uni «shunchaki ulash»
 * esa ⛔ MAHSULOTNI BUZARDI: server kodni ⛔ PREFIKS sifatida qidiradi
 * va AYNAN BITTA moslik topilganda o'sha rastaning TO'LIQ kodini
 * qaytaradi (`billing_repo.pending_projection()`: `elif len(codes) == 1:
 * exact = codes[0]`).
 *
 *     kassir «14-» teradi -> yagona moslik «14-C» -> javob «14-C»
 *
 * Ya'ni `javob === tergan kod` sharti bu QONUNIY oqimda `false` bo'lardi
 * va to'lov yuzasi UMUMAN chizilmasdi. Da'vo maydonning nomida ham
 * yashiringan edi: u «kod BIR XILmi?» degan savolga javob beradi,
 * himoya kerak bo'lgan savol esa «summa BOSHQA rastanikimi?».
 *
 * ⛔ HAQIQIY HIMOYA QAYERDA (§9.4):
 *
 *   1. so'rov KALITI `stallCode` ni o'z ichiga oladi — boshqa kod ostida
 *      yozilgan javob bu kalit ostida UMUMAN yashamaydi;
 *   2. `staleTime: 0` + `gcTime: 0` — eski javob keshda QOLMAYDI;
 *   3. `PendingCard` javobning kodini kiritilgan kod bilan O'ZI
 *      solishtiradi (`pending-card.tsx`) va mos kelmasa SUMMA o'rniga
 *      skeleton chizadi.
 *
 * ⚠ To'lov tanasiga ketadigan kod SERVERNIKI (`stall.stall_code`,
 *   `collect-session.tsx`), kassir tergan matn EMAS — ya'ni prefiks
 *   oqimida ham `POST /payments` kanonik kodni yuboradi.
 * =============================================================================
 */
export type PendingLookupResult = {
  /** Aynan bitta moslik topilgan bo'lsa — proyeksiya; aks holda `null`. */
  stall: PendingStall | null;
  /** Ko'p moslikda kodlar ro'yxati (server tartibida), aks holda bo'sh. */
  matches: readonly string[];
};

/**
 * Server javobini yagona shaklga keltiradi — ikki shox, bitta natija.
 *
 * ⚠ Eksport qilinadi, chunki komponent testi uni SO'ROVSIZ o'lchay oladi.
 */
export function normalizePendingLookup(
  data: z.infer<typeof pendingLookupResponseSchema>,
): PendingLookupResult {
  if ("matches" in data) {
    return { stall: data.stall, matches: data.matches };
  }
  return { stall: data, matches: [] };
}

/**
 * `GET /billing/pending` (rasta parametrisiz) — BOZOR kesimi (§9.5).
 *
 * ⛔ Bu ham `strictObject` va unda ham hisob identifikatori YO'Q: bozor
 *    kesimi proyeksiyaning YIG'INDISI, hisoblar ro'yxati EMAS.
 *
 * `fetched_at` — «oxirgi olingan vaqt». U ATAYIN payloadda: §9.5 avtomatik
 * taymerni rad etadi va uning o'rniga [Yangilash] tugmasi + vaqt tamg'asi
 * qo'yadi — «men boshqa raqam ko'rgandim» nizosining manbai jimgina
 * o'zgaradigan raqam edi.
 */
export const pendingMarketSummarySchema = z.strictObject({
  service_date: z.string(),
  market_open: z.boolean(),
  pending_amount_soum: soumSchema,
  outstanding_soum: soumSchema,
  pending_stall_count: z.number().int(),
  fetched_at: z.string(),
});

export type PendingMarketSummary = z.infer<typeof pendingMarketSummarySchema>;

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

/**
 * ⛔ PREFIKS — `removeQueries` ning YAGONA nishoni.
 *
 * `domainKey` `market-queries.ts` DAN import qilinadi, ikkinchi nusxa
 * yaratilmaydi. Har fabrikaning BIRINCHI argumenti `marketId`: kalit
 * tug'ilishidanoq tenant chegarasi ichida.
 */
export const pendingPrefix = (marketId: string) =>
  domainKey(marketId, "billing-pending");

export const pendingStallKey = (marketId: string, stallCode: string) =>
  domainKey(marketId, "billing-pending", stallCode);

export const pendingMarketKey = (marketId: string) =>
  domainKey(marketId, "billing-pending", "market");

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Rasta proyeksiyasi ---------------------------------------------------- */

/**
 * `GET /billing/pending?stall_code=…` — kassir yuzasining YAGONA summa manbai.
 *
 * =========================================================================
 * ⛔ `staleTime: 0` VA `gcTime: 0` — BU FAZANING ENG JIM XATO SINFIGA
 *    QARSHI (§9.4).
 *
 *    Kassir `14-C` ni terdi (15 000), keyin `15-A` ni terdi va BIR ZUMGA
 *    `15-A` kodi ostida 15 000 ko'rindi — u shu paytda [Naqd] va
 *    [Tasdiqlash] ni bosdi. Eski rastaning summasi yangi rasta kodi
 *    ostida ko'rinishi TO'G'RIDAN-TO'G'RI noto'g'ri pul yig'ish.
 *
 * ⛔ IKKINCHI QATLAM SHU MODULDA EMAS, `PendingCard` DA (WR-05).
 *    Ilgari bu docstring `select` HOSIL QILADIGAN `matchesRequestedCode`
 *    maydonini «2-qatlam» deb e'lon qilardi — maydonni esa HECH KIM
 *    o'qimasdi va uni ulash mahsulotni BUZARDI (prefiks qidiruvi, sabab
 *    `PendingLookupResult` docstringida). Amaldagi qatlamlar:
 *
 *      1. so'rov KALITI `stallCode` ni o'z ichiga oladi;
 *      2. `staleTime: 0` + `gcTime: 0` — eski javob keshda QOLMAYDI;
 *      3. `PendingCard` javobning kodini O'ZI solishtiradi va mos
 *         kelmasa summa o'rniga skeleton chizadi.
 *
 * ⛔ IZOH ENDI KODNI TA'RIFLAYDI, DA'VO QILMAYDI: yolg'on izoh
 *    yo'qligidan YOMONROQ — keyingi o'quvchi mavjud bo'lmagan himoyaga
 *    ishonib, haqiqiysini olib tashlashi mumkin edi.
 *
 * ⚠ `retry: false`: `market_closed` va `tariff_missing` NORMAL holatlar va
 *   ular javob tanasida keladi; tarmoq xatosida esa avtomatik takror
 *   urinish kassirni «summa hozir chiqadi» deb kutishga majburlardi —
 *   §9.4 bo'yicha bu holatda summa UMUMAN chizilmaydi va [Qayta urinish]
 *   FOYDALANUVCHI qarori bo'lib qoladi.
 * =========================================================================
 */
export function usePendingStall(
  stallCode: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: pendingStallKey(marketId ?? "", stallCode),
    queryFn: () =>
      apiFetch(
        `${BILLING_PENDING_PATH}?stall_code=${encodeURIComponent(stallCode)}`,
        { schema: pendingLookupResponseSchema },
      ),
    select: (data: z.infer<typeof pendingLookupResponseSchema>) =>
      normalizePendingLookup(data),
    enabled:
      marketId !== null && stallCode !== "" && (options?.enabled ?? true),
    retry: false,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });
}

/* --- Bozor kesimi (direktor) ---------------------------------------------- */

/**
 * `GET /billing/pending` — bozor kesimidagi proyeksiya (§9.5).
 *
 * ⛔ `staleTime: 0` va `gcTime: 0` shu yerda ham: raqam KUN ICHIDA
 *    o'zgaradi va eski yig'indi direktor ekranida «bugungi holat» bo'lib
 *    ko'rinardi.
 *
 * ⚠ `refetchOnWindowFocus` ATAYIN QO'YILMAYDI va standart holida qoladi —
 *   §9.5 ning so'zma-so'z qarori. Kassir yuzasidan farqi ochiq: u yerda
 *   fokus qaytishi so'rov TUG'DIRMASLIGI kerak (kassir bir rastada
 *   turadi), bu yerda esa direktor sahifaga qaytganda eng yangi raqamni
 *   ko'rgani ma'qul. AVTOMATIK TAYMER esa ikkala yuzada ham YO'Q:
 *   raqamni o'qib turgan paytda uni jimgina o'zgartirib qo'yish
 *   «men boshqa raqam ko'rgandim» nizosining manbai.
 */
export function useMarketPending(options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: pendingMarketKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(BILLING_PENDING_PATH, { schema: pendingMarketSummarySchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
}

/* --- Muvaffaqiyatli to'lovdan keyingi tozalash ----------------------------- */

/**
 * ⛔ To'lov yozilgach proyeksiya keshdan CHIQARILADI — «eskirgan» deb
 *    belgilanmaydi.
 *
 * =========================================================================
 * ⚠ NOMIDA `invalidate` SO'ZI YO'Q VA BU ATAYIN.
 *
 *   `invalidatePendingAfterPayment` nomi TEXNIK JIHATDAN to'g'ri bo'lardi
 *   (u kesh yozuvini «endi ishonchsiz» deb belgilaydi), lekin u keyingi
 *   o'quvchiga AMALNI NOTO'G'RI aytardi: TanStack'da `invalidate` yozuvni
 *   grafda QOLDIRADI va faqat qayta so'raladigan qilib belgilaydi. To'lov
 *   yozilgandan keyin esa eski proyeksiya BRAUZER XOTIRASIDA turishi ham
 *   kerak emas — u endi YOLG'ON summa.
 *
 *   05-13 ning darsi: kafolat JUFTLIKDAN chiqadi (`gcTime: 0` +
 *   `removeQueries`) va ikkala yarim ALOHIDA qo'riqlanadi. Nom shu
 *   juftlikning ikkinchi yarmini aytadi, birinchisini emas.
 * =========================================================================
 */
export function dropPendingAfterPayment(
  client: QueryClient,
  marketId: string,
): void {
  client.removeQueries({ queryKey: pendingPrefix(marketId) });
}
