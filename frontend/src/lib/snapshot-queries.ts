"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import {
  alertListResponseSchema,
  captureDaySchema,
  emptyResponseSchema,
  snapshotDetailSchema,
  snapshotScheduleListResponseSchema,
  snapshotScheduleSchema,
  snapshotScheduleTodaySchema,
} from "@/lib/api-types";
import type { CaptureRun } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * 4-faza domenining SERVER HOLATI (04-09 kontrakti).
 *
 * `camera-queries.ts` TO'LIQ SHABLON, u esa o'z navbatida
 * `market-queries.ts:100-250` dan qurilgan. Uchinchi modul aynan o'sha
 * sababdan ochildi: har domenning invalidatsiya to'plami O'ZINIKI va
 * ularni bitta faylga yig'ish «kamerani qayta nomlash kun jurnalini ham
 * bekor qiladimi?» degan savolni har tahrirda qaytarardi.
 *
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa
 *   yaratilmaydi. GLOBAL (marketsiz) KALIT KONSTANTASI BU MODULDA
 *   UMUMAN YO'Q: har fabrikaning BIRINCHI argumenti `marketId`, ya'ni
 *   doiralashni chetlab o'tish TypeScript xatosisiz mumkin emas.
 *   Bu — CR-01 ning strukturaviy davosi, kod-ko'rikdagi eslatma emas.
 *
 * ⚠ TIP TIZIMI YOLG'IZ YETARLI EMAS va bu o'lchangan (04-02): kalitdan
 *   `marketId` ni TUSHIRIB QOLDIRISH typecheck'ni qizartiradi, lekin
 *   `domainKey("snapshots", ...)` yozish — ya'ni birinchi argument
 *   o'rniga domen nomini berish — TIP JIHATIDAN YAROQLI. Shuning uchun
 *   kalit SHAKLI birlik testi bilan ham qulflanadi
 *   (`snapshot-queries.test.tsx`).
 *
 * ⚠ `query-provider.tsx` O'ZGARTIRILMAYDI — sessiya identifikatori
 *   o'zgarganda `client.clear()` butun keshni bo'shatadi va u yangi
 *   kalitlarni AVTOMATIK qamraydi (ikkinchi qatlam).
 * =============================================================================
 */

/* --- Yo'l konstantalari --------------------------------------------------- */

export const SNAPSHOT_SCHEDULES_PATH = "/snapshot-schedules";
export const CAPTURE_RUNS_PATH = "/capture-runs";
export const SNAPSHOTS_PATH = "/snapshots";
export const ALERTS_PATH = "/alerts";

/* --- Poll konstantalari (§6.8) -------------------------------------------- */

/**
 * Kun jurnali va ogohlantirish zonasining poll oralig'i — 30 SONIYA.
 *
 * Slotlar orasidagi eng kichik oraliq 15 daqiqa (§4.6 dagi `Qadam`
 * tanlagichi). 30 s yangilanish «hozir olinyapti» ni ko'rsatish uchun
 * yetarlidan ko'p.
 *
 * ⚠ 3-FAZADAGI 2000 ms BU YERGA KO'CHIRILMAYDI. U kashfiyot uchun edi —
 *   17–60 soniyalik job, ya'ni 9–30 ta poll. Bu yerdagi oyna 15 DAQIQA,
 *   ya'ni o'sha qiymat serverni 900 barobar ortiqcha yuklardi va hech
 *   qanday yangi ma'lumot bermasdi.
 */
export const CAPTURE_POLL_INTERVAL_MS = 30_000;

/**
 * Poll DAVOM ETADIGAN holatlar — `pending` va `running`.
 *
 * Ro'yxat sifatida ATAYIN: «terminal emas» degan inkor shakli
 * `skipped` ni ham faol deb hisoblardi, holbuki u boshidanoq yakuniy
 * (bozor kun o'rtasida ulangan — o'sha slot hech qachon bajarilmaydi).
 */
const ACTIVE_RUN_STATUSES = ["pending", "running"] as const;

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

export const scheduleTodayKey = (marketId: string) =>
  domainKey(marketId, "schedule", "today");

export const schedulesKey = (marketId: string) =>
  domainKey(marketId, "schedules");

export const captureDayKey = (marketId: string, day: string) =>
  domainKey(marketId, "capture-runs", day);

export const snapshotKey = (marketId: string, snapshotId: string) =>
  domainKey(marketId, "snapshots", "detail", snapshotId);

/**
 * ⚠ `closed` KALITNING BIR QISMI, filtr emas: ochiq va yopilgan
 *   ogohlantirishlar IKKI XIL to'plam va ularni bitta kesh yozuvida
 *   ushlash checkbox yoqilganda eski ro'yxatni ko'rsatardi.
 */
export const alertsKey = (marketId: string, closed: boolean) =>
  domainKey(marketId, "alerts", String(closed));

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `camera-queries.ts:140-143` bilan AYNI sabab: `useAuthStore()` ni har
 * hookda takrorlash "bittasi tushib qoladi" xatosini kafolatlardi.
 * Funksiya EKSPORT QILINMAYDI — u modulning ichki kontrakti.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

function invalidate(client: QueryClient, keys: readonly (readonly unknown[])[]) {
  for (const key of keys) {
    void client.invalidateQueries({ queryKey: key });
  }
}

/**
 * Jadvalga tegadigan har amalning yon ta'siri.
 *
 * ⚠ IKKALA PREFIKS HAM KERAK va bu shaklning oqibati: TanStack kalitni
 *   PREFIKS bo'yicha solishtiradi, `["m", id, "schedule"]` esa
 *   `["m", id, "schedules"]` ni QAMRAMAYDI (`schedule` va `schedules` —
 *   turli segmentlar). Faqat bittasini bekor qilish DL-2 dagi ro'yxatni
 *   yoki zona A dagi kartani eskirgan holda qoldirardi.
 */
const scheduleSideEffects = (marketId: string) =>
  [domainKey(marketId, "schedule"), schedulesKey(marketId)] as const;

/* --- Zona A: jadval ------------------------------------------------------- */

/**
 * `GET /snapshot-schedules/today` — «bugun» va «ertaga» BITTA javobda (D-05).
 *
 * ⚠ POLL YO'Q (§6.8 oxirgi qatori): jadval kunda bir marta o'zgaradi va
 *   uni har 30 soniyada so'rash bekor yuk bo'lardi.
 *   `refetchOnWindowFocus` (global standart) yetarli — admin tabga
 *   qaytganda yarim tundan keyingi holat o'zi yangilanadi.
 *
 * ⚠ `enabled` shartidagi `marketId !== null` QULAYLIK EMAS, KONTRAKT
 *   (`market-queries.ts:186-192`). Bozorsiz sessiyada domen so'rovi
 *   serverda `409 market_not_selected` oladi va o'sha xato kesh grafida
 *   YASHAB QOLARDI. Shu sababli `marketId` `null` bo'lganda kalitdagi
 *   bo'sh satr ham xavfsiz: o'sha kalit ostida hech qachon ma'lumot
 *   yozilmaydi.
 */
export function useScheduleToday(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: scheduleTodayKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(`${SNAPSHOT_SCHEDULES_PATH}/today`, {
        schema: snapshotScheduleTodaySchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/**
 * `GET /snapshot-schedules` — bozorning BARCHA profillari (DL-2 ro'yxati).
 *
 * Sahifalash YO'Q va u so'ralmaydi ham: mavsumiy profil yiliga bir necha
 * marta qo'shiladi, ya'ni ro'yxat tabiiy ravishda o'nlab qatorda qoladi.
 */
export function useSchedules(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: schedulesKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(SNAPSHOT_SCHEDULES_PATH, {
        schema: snapshotScheduleListResponseSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/**
 * `PATCH /snapshot-schedules/{id}` — FAQAT vaqtlar (§4.5).
 *
 * ⚠ `starts_on`/`ends_on` YUBORILMAYDI va yuborilsa server 422 beradi
 *   (`ScheduleSlotsIn.model_config` dagi `extra="forbid"`). Davrni
 *   siljitish o'tmishdagi kadrlarni tushuntirmay qo'yardi.
 *
 * ⚠ O'ZGARISH ERTADAN KUCHGA KIRADI (D-05) va bu kafolat SERVERDA,
 *   mutatsiyaning xushmuomalaligida emas: bugungi `capture_runs`
 *   qatorlari allaqachon materializatsiya qilingan. UI buni DL-1 dagi
 *   doimiy izoh bilan aytadi.
 */
export function useUpdateScheduleTimes() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { scheduleId: string; times: readonly string[] }) =>
      apiFetch(`${SNAPSHOT_SCHEDULES_PATH}/${input.scheduleId}`, {
        method: "PATCH",
        body: { times: [...input.times] },
        schema: snapshotScheduleSchema,
      }),
    onSuccess: () => invalidate(client, scheduleSideEffects(marketId)),
  });
}

export type SeasonalScheduleInput = {
  name: string;
  startsOn: string;
  /** `null` — ochiq oxirli profil (§4.7). */
  endsOn: string | null;
  times: readonly string[];
};

/**
 * `POST /snapshot-schedules` — mavsumiy profil (201).
 *
 * ⚠ DAVRNI BO'LISH (split) SEMANTIKASI SERVERDA. Repozitoriy uch qadamni
 *   bitta tranzaksiyada bajaradi: qoplaydigan profilni qisqartiradi,
 *   `ends_on` dan keyin uni NUSXA sifatida tiklaydi va yangisini yozadi.
 *   ⛔ UI BU MANTIQNI TAKRORLAMAYDI — takrorlansa ikki haqiqat manbai
 *   paydo bo'lardi va DL-2 dagi jonli natija qatori server bilan
 *   ajralib ketardi.
 */
export function useCreateSeasonalSchedule() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: SeasonalScheduleInput) =>
      apiFetch(SNAPSHOT_SCHEDULES_PATH, {
        method: "POST",
        body: {
          name: input.name,
          starts_on: input.startsOn,
          ends_on: input.endsOn,
          times: [...input.times],
        },
        schema: snapshotScheduleSchema,
      }),
    onSuccess: () => invalidate(client, scheduleSideEffects(marketId)),
  });
}

/**
 * `DELETE /snapshot-schedules/{id}` — 204, tanasiz (DL-4).
 *
 * ⛔ FAQAT `starts_on > bugun`. Boshlangan profilni o'chirish o'tmishdagi
 *    kadrlarning yagona izohini yo'q qilardi; server uni `403
 *    schedule_not_editable` bilan rad etadi. UI esa tugmani BOSHIDAN
 *    render qilmaydi (§10.8) — ya'ni bu yo'l normal oqimda umuman
 *    ochilmaydi va mutatsiya faqat ikkinchi qatlam bo'lib qoladi.
 */
export function useDeleteSchedule() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (scheduleId: string) =>
      apiFetch(`${SNAPSHOT_SCHEDULES_PATH}/${scheduleId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, scheduleSideEffects(marketId)),
  });
}

/* --- Zona C+D: kun jurnali ------------------------------------------------ */

/**
 * `GET /capture-runs?day=` — kun xulosasi va matritsa qatorlari.
 *
 * Poll kontrakti §6.8 da; qaror `capturePollInterval` sof funksiyasida.
 */
export function useCaptureDay(
  day: string,
  todayIso: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: captureDayKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${CAPTURE_RUNS_PATH}?day=${encodeURIComponent(day)}`, {
        schema: captureDaySchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    refetchInterval: (query) =>
      capturePollInterval({ day, todayIso, rows: query.state.data?.rows }),
    refetchIntervalInBackground: false,
  });
}

/**
 * Poll qarori — SOF FUNKSIYA (`refetchInterval` uni faqat chaqiradi).
 *
 * ⛔ CHEKSIZ POLL HECH QACHON, va bu yerda terminal shart QO'SHIMCHA
 *    TAYMERSIZ ta'minlanadi: u MA'LUMOTNING O'ZIDAN hosil bo'ladi.
 *    Kun tugagach barcha qatorlar terminal holatga o'tadi,
 *    `hasActiveRuns` `false` bo'ladi va poll O'ZI to'xtaydi. 3-fazadagi
 *    kashfiyot pollida ikkita mustaqil taymer kerak edi, chunki u yerda
 *    «qotib qolgan yugurish» holati bor edi; bu yerda esa qotib qolgan
 *    qatorni watchdog `missed` ga o'tkazadi va u ham TERMINAL.
 *
 * Ikki shart VA bilan bog'langan:
 *   1. `day === bugun` — o'tgan kun O'ZGARMAYDI, uni poll qilish bekor
 *      yuk (va kelajakdagi kun umuman tanlanmaydi, §6.3);
 *   2. kunda `pending` yoki `running` qator BOR.
 *
 * ⚠ MA'LUMOT HALI KELMAGANDA (`rows === undefined`) poll YOQILADI.
 *   Birinchi javob kelgunicha «faol qator yo'q» deb hisoblash bugungi
 *   kunni birinchi yuklashda muzlatib qo'yardi.
 */
export function capturePollInterval(input: {
  day: string;
  todayIso: string;
  rows: readonly CaptureRun[] | undefined;
}): number | false {
  if (input.day !== input.todayIso) return false;

  const hasActiveRuns =
    input.rows === undefined ||
    input.rows.some((row) =>
      (ACTIVE_RUN_STATUSES as readonly string[]).includes(row.status),
    );

  return hasActiveRuns ? CAPTURE_POLL_INTERVAL_MS : false;
}

/**
 * `GET /snapshots/{id}` — kadr detali (DL-3).
 *
 * ⚠ `object_key` javobda YO'Q va so'ralmaydi ham (§14.3). Rasm
 *   baytlari alohida marshrutdan (`/snapshots/{id}/image`) `<img>`
 *   manbai sifatida keladi va o'sha marshrut `audit_read` yozadi —
 *   ya'ni rasm TanStack keshiga umuman tushmaydi.
 */
export function useSnapshotDetail(snapshotId: string | null) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: snapshotKey(marketId ?? "", snapshotId ?? ""),
    queryFn: () =>
      apiFetch(`${SNAPSHOTS_PATH}/${snapshotId}`, {
        schema: snapshotDetailSchema,
      }),
    enabled: marketId !== null && snapshotId !== null,
  });
}

/* --- Zona B: ogohlantirishlar --------------------------------------------- */

/**
 * `GET /alerts?closed=0|1` — ochiq yoki yopilgan ogohlantirishlar.
 *
 * ⚠ POLL JURNAL BILAN BIR VAQTDA (§6.8): aks holda ekranda «2 kadr
 *   olinmadi» ko'rinib turib, ogohlantirish paydo bo'lmasdi va admin
 *   ikkisini solishtira olmasdi (D-20 ning butun mazmuni). Shuning
 *   uchun oraliq AYNI konstanta va shart ham AYNI: faqat bugungi kun
 *   ko'rilayotganda.
 *
 * ⚠ YOPISH/BOSTIRISH MUTATSIYASI YO'Q va u qurilmaydi (§6.7):
 *   ogohlantirishni faqat TIKLANISH yopadi. Backendda ham bunday
 *   marshrut umuman mavjud emas.
 */
export function useAlerts(
  closed: boolean,
  options?: { enabled?: boolean; poll?: boolean },
) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: alertsKey(marketId ?? "", closed),
    queryFn: () =>
      apiFetch(`${ALERTS_PATH}?closed=${closed ? "1" : "0"}`, {
        schema: alertListResponseSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    refetchInterval: options?.poll === true ? CAPTURE_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: false,
  });
}
