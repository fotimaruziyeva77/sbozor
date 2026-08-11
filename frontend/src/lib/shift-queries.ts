"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import { soumSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * SMENA VA ⛔⛔ KO'R NAQD DEKLARATSIYASI (CASH-04, D-25, D-26).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ D-25 — YO'QLIK, YASHIRISH EMAS
 * -----------------------------------------------------------------------
 * Kassir smenani yopganda naqdni SANAB kiritadi va tizim unga o'z
 * summasini KO'RSATMAYDI. Bu mexanizm CSS bilan ham, shartli render
 * bilan ham qurilmaydi: brauzerga yetgan maydon O'QILADI — DevTools,
 * tarmoq paneli, React DevTools, `JSON.stringify`. «Ko'rsatmayapmiz» —
 * kod-ko'rik da'vosi, O'LCHOV EMAS (Pitfall 6).
 *
 * ⛔ `null` qilib yuborish ham YARAMAYDI: `null` maydonning BORLIGINI
 *    tasdiqlaydi va keyingi ijrochi uni to'ldirardi. Shuning uchun
 *    yopish javobining sxemasida tizim summasi va farq maydonlari
 *    UMUMAN E'LON QILINMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ FARQ (variance) KASSIRGA KO'RSATILMAYDI, DIREKTORGA KO'RSATILADI
 * -----------------------------------------------------------------------
 * Uch sabab (§10.4):
 *
 * 1. Farq TIZIM SUMMASINI OSHKOR QILADI — `tizim = deklaratsiya − farq`,
 *    bitta ayirish. Ya'ni farqni qaytarish D-25 ni HISOB-KITOB BILAN
 *    buzardi.
 * 2. KEYINGI SMENANING KO'RLIGINI buzadi: har kun farqni ko'rgan kassir
 *    bir haftada «tizim odatda shuncha deydi» degan LANGAR hosil qiladi
 *    va sanashdan oldin TAXMIN qiladi.
 * 3. Bu smenada TUZATISH YO'LI YO'Q: deklaratsiya o'zgarmas (D-25) va
 *    farq avtomatik to'g'rilanmaydi (D-26). Ya'ni kassirga farqni
 *    ko'rsatish hech qanday harakatni ochmaydi — u faqat ma'lumot oqadi.
 *
 * ⚠ MEZON O'LCHANISHI SAQLANADI. 06-RESEARCH SC#5(d) «farq serverda
 *   hisoblangan va `declared > system` holatida ham qaytariladi» deydi —
 *   bu talab `GET /shifts?day=` MARSHRUTIDA bajariladi (§10.4) va faza
 *   darvozasi mezon testini AYNAN shu marshrutga qaratishi shart. Yopish
 *   javobida yo'q maydonni izlagan test yolg'on-qizil bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ IKKI YUZA — BITTA FAYL, VA BU QONUNIY
 * -----------------------------------------------------------------------
 * Direktor sxemasi tizim summasi va farqni O'Z ICHIGA OLADI. U shu
 * faylda yashaydi, chunki `collect-surface.test.mjs` FAQAT
 * `components/collect/**` va proyeksiya modulini skanerlaydi — ya'ni
 * darvozaning qamrovi kassir YUZASI, «smena» DOMENI emas (§15.3, G-7).
 *
 * ⛔ Kassir komponentlari bu fayldan FAQAT ochish/yopish sxemalarini
 *    import qiladi; hisobot sxemasi direktor sahifasiga tegishli.
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const SHIFTS_PATH = "/shifts";

/* --- Reyestr --------------------------------------------------------------- */

/**
 * Smena holati — ikki qiymat, uchinchisi yo'q (§10.1).
 *
 * Bir vaqtda BITTA ochiq smena strukturaviy kafolat: qisman `UNIQUE`
 * indeks (`uq_cashier_shifts_market_id_cashier_open`) `status = 'open'`
 * predikati bilan. UI ikkinchi «ochish» tugmasini ko'rsatmaydi.
 */
export const SHIFT_STATUSES = ["open", "closed"] as const;

export type ShiftStatus = (typeof SHIFT_STATUSES)[number];

/* --- Yopish javobi — ⛔⛔ AYNAN TO'RT KALIT ------------------------------- */

/**
 * `POST /shifts/{id}/close` javobi (§10.3).
 *
 * =========================================================================
 * ⛔⛔ KALITLAR TO'PLAMI AYNAN TO'RTTA. Quyidagilar E'LON QILINMAYDI va
 *    `null` qilib ham YOZILMAYDI:
 *
 *      tizim summasi · kutilgan summa · farq (ikkala nomda ham) ·
 *      to'lovlar soni · naqd sanog'i · terminal summasi
 *
 *    Ular «yig'indiga olib boradigan» kirish ma'lumoti va ularning har
 *    biri D-25 ni bir amalda buzardi.
 *
 * ⛔ `z.strictObject` — DINAMIK yarim: server bir kun maydon qo'shsa,
 *    klient PARSE PAYTIDA yiqiladi va maydon ekranga JIMGINA oqib
 *    o'tmaydi. Statik yarim `collect-surface.test.mjs` da.
 *
 * **Kassir yopgandan keyin ko'radigan narsa AYNAN UCHTA:** «Deklaratsiya
 * yozildi» belgisi · kiritilgan summa · [Yangi smena ochish].
 * =========================================================================
 */
export const shiftCloseResponseSchema = z.strictObject({
  id: z.uuid(),
  status: z.enum(SHIFT_STATUSES),
  declared_soum: soumSchema,
  closed_at: z.string(),
});

export type ShiftCloseResult = z.infer<typeof shiftCloseResponseSchema>;

/* --- Ochiq smena ----------------------------------------------------------- */

/**
 * `GET /shifts/open` javobi — ochiq smena yo'q bo'lsa `null`.
 *
 * ⛔ Kartada to'lovlar soni, yig'ilgan summa, o'rtacha yoki «bugungi
 *    natija» YO'Q — hech qanday shaklda (§10.1). Ular ham yig'indiga
 *    olib boradi.
 */
export const shiftOpenSchema = z.strictObject({
  id: z.uuid(),
  status: z.enum(SHIFT_STATUSES),
  opened_at: z.string(),
});

export type OpenShift = z.infer<typeof shiftOpenSchema>;

/* --- Direktor yuzasi (§11.5) ---------------------------------------------- */

/**
 * `GET /shifts?day=` jadvalining bitta qatori.
 *
 * ⛔ Kassir ISMI bu javobda YO'Q — faqat `cashier_id`. Ism klientda,
 *    mavjud va audit qilingan `GET /users` marshrutidan joinlanadi
 *    (§5.5): moliyaviy marshrutga shaxsiy-ma'lumot qo'riqchisini
 *    o'rnatish keyingi ijrochi ko'chiradigan naqsh bo'lardi.
 *
 * ⛔ `abs(variance_soum)` YO'Q va bo'lmaydi ham: ishora MA'NO TASHIYDI.
 *    `< 0` — kamomad, `> 0` — ortiqcha, `= 0` — mos keldi; uchalasi ham
 *    uch kanalda (rang + ikonka + MATN) ko'rsatiladi.
 *
 * ⛔ `declared > system` (ortiqcha) TENG OG'IRLIKDA ko'rsatiladi va JIM
 *    YUTILMAYDI (D-26): «ortiqcha naqd ham signal — uni jimgina yutish
 *    kamomadni yashirish bilan bir xil xato».
 */
export const shiftReportRowSchema = z.strictObject({
  id: z.uuid(),
  cashier_id: z.uuid(),
  opened_at: z.string(),
  /** Hali yopilmagan smena hisobot kunida ochiq bo'lishi mumkin. */
  closed_at: z.string().nullable(),
  declared_soum: soumSchema.nullable(),
  system_soum: soumSchema,
  /**
   * ⛔ SERVERDA hisoblangan farq — klientda AYIRISH qilinmaydi.
   *
   * 05-14 ning darsi: klientdagi qayta hisob xato bo'lib emas, IKKINCHI
   * JAVOB bo'lib chiqadi. Manfiy qiymat ham keladi, ya'ni `soumSchema`
   * emas, oddiy butun son.
   */
  variance_soum: z.number().int(),
});

export type ShiftReportRow = z.infer<typeof shiftReportRowSchema>;

/**
 * `GET /shifts?day=` javobi.
 *
 * =========================================================================
 * ⛔ «SMENASIZ TO'LOVLAR» — NOMLANGAN MAYDON, JIM YO'QOLISH EMAS.
 *
 *    `shift_id IS NULL` bo'lgan to'lovlar birorta kassir qutisiga
 *    tushmagan, ya'ni ular farq hisobiga KIRMAYDI. Ammo ular PUL va
 *    ularni jadvaldan tushirib qoldirish «o'lchanmagan miqdorni nol deb
 *    yozish» bo'lardi (D-14 ruhi).
 *
 *    Shuning uchun ularga NOM berildi — sanog'i ham, summasi ham — va
 *    ular jadval ostida alohida qator bo'lib ko'rinadi. Bu 06-UI-SPEC
 *    §11.5 dagi FLAG'ni yopadi.
 * =========================================================================
 */
export const shiftReportSchema = z.strictObject({
  /**
   * ⛔ SERVER QAYTARGAN KUN — klient so'ragan kun EMAS.
   *
   *    `ChargeListResponse` / `AnomalyListResponse` bilan bitta naqsh:
   *    envelope o'zi qaysi kunni javob berayotganini AYTADI. Usiz ekran
   *    so'rov parametridan taxmin qilardi va Toshkent yarim tunida
   *    sarlavha boshqa kunni ko'rsatardi.
   *
   *    ⚠ `z.strictObject` ostida bu maydonning YO'QLIGI parse paytida
   *    THROW berardi (server uni `ShiftReportResponse.day: date` deb
   *    e'lon qiladi) — 06-13 ning farq bloki birinchi yuklashdayoq
   *    yiqilardi.
   */
  day: z.string(),
  rows: z.array(shiftReportRowSchema),
  shiftless_payment_count: z.number().int(),
  shiftless_payment_soum: soumSchema,
});

export type ShiftReport = z.infer<typeof shiftReportSchema>;

/* --- Query kalitlari ------------------------------------------------------- */

export const shiftPrefix = (marketId: string) => domainKey(marketId, "shift");

export const openShiftKey = (marketId: string) =>
  domainKey(marketId, "shift", "open");

export const shiftReportKey = (marketId: string, day: string) =>
  domainKey(marketId, "shifts", day);

/**
 * Direktor hisobotining `staleTime` i — 30 SONIYA (§5.4).
 *
 * ⚠ Kassir yuzasining NOLI bu yerga ko'chirilmaydi: hisobot O'QISH
 *   yuzasi va undagi eskilik hech kimni noto'g'ri pul yig'ishga
 *   majburlamaydi. Kun yopilgandan keyin qatorlar umuman o'zgarmaydi.
 */
export const SHIFT_REPORT_STALE_TIME_MS = 30_000;

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Ochiq smena holati ---------------------------------------------------- */

/**
 * `GET /shifts/open` — ochiq smena bormi.
 *
 * ⛔ `staleTime: 0` + `gcTime: 0`: eski javob «smena ochiq» deb YOLG'ON
 *    gapirardi va kassir yopilgan smenaga to'lov yozardi (server uni
 *    rad etardi, lekin xato KASSIR ISHINING O'RTASIDA chiqardi).
 *
 * ⚠ `retry: false`: «ochiq smena yo'q» NORMAL holat va u `null` bo'lib
 *   keladi, xato bo'lib emas.
 */
export function useOpenShift(options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: openShiftKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(`${SHIFTS_PATH}/open`, {
        schema: shiftOpenSchema.nullable(),
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    retry: false,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });
}

/* --- Smena ochish ---------------------------------------------------------- */

/**
 * `POST /shifts` — smenani ochish.
 *
 * ⚠ Server `shift_already_open` qaytarsa, u sabab + nima qilish kerak
 *   juftligi bilan chiziladi (§13.7); UI ikkinchi «ochish» tugmasini
 *   ko'rsatmaydi (§10.1).
 */
export function useOpenShiftMutation() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: () =>
      apiFetch(SHIFTS_PATH, {
        method: "POST",
        schema: shiftOpenSchema,
      }),
    retry: false,
    onSuccess: () => {
      client.removeQueries({ queryKey: shiftPrefix(marketId) });
    },
  });
}

/* --- Smenani yopish -------------------------------------------------------- */

/**
 * `POST /shifts/{id}/close` — KO'R deklaratsiya.
 *
 * ⛔ Tana AYNAN bitta maydon: sanab kiritilgan naqd. Manfiy qiymat
 *    rad etiladi, NOL esa RUXSAT — butun smenasi terminal bo'lgan kun
 *    real holat va uni rad etish kassirni YOLG'ON son kiritishga
 *    majburlardi (§10.2).
 *
 * ⛔ Deklaratsiya O'ZGARMAS: tahrirlash marshruti yo'q, shuning uchun bu
 *    modulda ham unga sim yo'q.
 */
export function useCloseShift() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: { shift_id: string; declared_soum: number }) =>
      apiFetch(
        `${SHIFTS_PATH}/${encodeURIComponent(input.shift_id)}/close`,
        {
          method: "POST",
          body: { declared_soum: input.declared_soum },
          schema: shiftCloseResponseSchema,
        },
      ),
    retry: false,
    onSuccess: () => {
      client.removeQueries({ queryKey: shiftPrefix(marketId) });
    },
  });
}

/* --- Direktor hisoboti ----------------------------------------------------- */

/**
 * `GET /shifts?day=` — kun kesimidagi smenalar va farqlar (§11.5).
 *
 * ⛔ Bu blokda YOZUV YUZASI AYNAN NOL: [To'g'rilash], [Tasdiqlash],
 *    [Izoh qo'shish], [Kechirish] — birortasi ham yo'q, chunki farq
 *    HECH QACHON avtomatik to'g'rilanmaydi (D-26) va qo'lda to'g'rilash
 *    marshruti 6-fazada ochilmaydi. Shuning uchun bu modulda hisobotga
 *    yozadigan MUTATSIYA ham yo'q.
 *
 * ⚠ Blok `day = bugun` da ham, `day < bugun` da ham chiziladi (§11.2,
 *   E qatori) — smena kun ichida yopiladi.
 */
export function useShiftReport(day: string, options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: shiftReportKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${SHIFTS_PATH}?day=${encodeURIComponent(day)}`, {
        schema: shiftReportSchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: SHIFT_REPORT_STALE_TIME_MS,
  });
}
