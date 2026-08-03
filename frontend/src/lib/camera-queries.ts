"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import {
  cameraListResponseSchema,
  cameraSchema,
  discoveryRunSchema,
  discoveryStartResponseSchema,
  emptyResponseSchema,
  isTerminalRunStatus,
  liveTokenSchema,
  nvrDeviceListResponseSchema,
  nvrDeviceSchema,
  nvrTestConnectionResponseSchema,
} from "@/lib/api-types";
import type {
  CameraStatusValue,
  DiscoveryRunStatusValue,
} from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * 3-faza domenining SERVER HOLATI (03-06 / 03-07 kontrakti).
 *
 * `market-queries.ts:100-250` TO'LIQ SHABLON. Ikkinchi modul aynan o'sha
 * sababdan ochildi: `market-queries.ts` 2-faza domenining ~30 hooki bilan
 * to'lgan va unga kamera yuzasini qo'shish ikkala domenning
 * invalidatsiya to'plamini bir-biriga aralashtirardi.
 *
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§S-10). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa
 *   yaratilmaydi (`market-queries.ts:104-108` dagi ogohlantirish aynan
 *   shu sinfdagi xato haqida). Global (marketsiz) kalit konstantasi bu
 *   modulda UMUMAN YO'Q: har fabrikaning BIRINCHI argumenti `marketId`,
 *   ya'ni doiralashni chetlab o'tish TypeScript xatosisiz mumkin emas.
 *   Bu — CR-01 ning strukturaviy davosi, kod-ko'rikdagi eslatma emas.
 *
 * ⚠ `query-provider.tsx` O'ZGARTIRILMAYDI — sessiya identifikatori
 *   o'zgarganda `client.clear()` butun keshni bo'shatadi va u yangi
 *   kalitlarni AVTOMATIK qamraydi (ikkinchi qatlam, `:54-73`).
 * =============================================================================
 */

/* --- Yo'l konstantalari --------------------------------------------------- */

export const NVR_DEVICES_PATH = "/nvr-devices";
export const CAMERAS_PATH = "/cameras";

/* --- Poll va jonli sessiya konstantalari ---------------------------------- */

/**
 * Kashfiyot poll'ining oralig'i (UI-SPEC §5.3).
 *
 * Byudjet 17–60 s (29 ISAPI so'rovi × 2 borish) -> 9–30 ta poll. 1000 ms
 * ikki barobar yuk berardi va sezilarli foyda bermasdi; 5000 ms esa
 * 17 soniyalik jobni javobsiz ko'rsatardi.
 */
export const DISCOVERY_POLL_INTERVAL_MS = 2000;

/**
 * Poll BUTUNLAY to'xtaydigan chegara — 3 daqiqa (UI-SPEC §5.3).
 *
 * Byudjetning eng yomon holatining (60 s+) uch barobari. Undan keyin
 * panel S5 («Kashfiyot javob bermayapti») ga o'tadi va bu XATO EMAS —
 * job fonda davom etayotgan bo'lishi mumkin.
 *
 * ⚠ CHEKSIZ POLL HECH QACHON. Terminal holat kelmasa ham poll o'ladi:
 *   ochiq qolgan tab aks holda serverni kunlab so'rab turardi.
 */
export const DISCOVERY_POLL_TIMEOUT_MS = 180_000;

/**
 * Bitta jonli ko'rish sessiyasining chegarasi — 5 daqiqa (UI-SPEC §8.3).
 *
 * ⚠ TOKENNING `exp` I EMAS. Token 60 soniya yashaydi (D-08), lekin u
 *   ULANISH CHIPTASI: WebRTC'da signalling bir marta bo'ladi va media
 *   UDP orqali nginx'dan TASHQARIDA oqadi, ya'ni sessiya tokendan
 *   uzoqroq yashaydi; HLS'da esa har segment `auth_request` dan o'tadi
 *   va oqim 60 soniyada uzilardi. Bir xil UI, ikki xil xulq — shuning
 *   uchun chegarani UI O'ZI qo'yadi va ikkala transport bir xil ishlaydi.
 */
export const LIVE_SESSION_MAX_MS = 300_000;

/** Sessiya tugashidan qancha oldin ogohlantiriladi (L4 holati). */
export const LIVE_EXPIRY_WARNING_MS = 30_000;

/** Ulanish o'rnatilmasa L6 (xato) ga o'tish chegarasi. */
export const LIVE_CONNECT_TIMEOUT_MS = 15_000;

/**
 * Ketma-ket necha marta yiqilgan poll'dan keyin so'rov TO'XTAYDI
 * (UI-SPEC §5.3 — «3 ta ketma-ket tarmoq xatosi -> S5»).
 *
 * ⚠ BU IKKINCHI, MUSTAQIL CHEGARA. `DISCOVERY_POLL_TIMEOUT_MS`
 *   yugurishning `started_at` iga tayanadi, ya'ni u BIRINCHI muvaffaqiyatli
 *   javobdan keyingina ishlay boshlaydi. Server umuman javob bermasa
 *   (tarmoq uzildi, 500) `started_at` hech qachon kelmaydi va birinchi
 *   chegara MANGU ochiq qolardi — poll esa cheksiz davom etardi.
 */
export const DISCOVERY_POLL_MAX_FAILURES = 3;

/**
 * `GET /cameras` da so'raladigan hajm.
 *
 * Backend chegarasi 200 (`CAMERA_PAGE_SIZE_MAX`); bitta NVR eng ko'pi 32
 * kanal beradi (UI-SPEC §6.1), ya'ni bitta sahifa BUTUN ro'yxatni
 * qamraydi. `useInfiniteQuery` ATAYIN ishlatilmaydi: `next_cursor` bugun
 * har doim `null` (03-07 ziddiyat C) va "Ko'proq yuklash" tugmasi
 * hech qachon ko'rinmaydigan affordans bo'lardi.
 */
export const CAMERA_PAGE_SIZE = 100;

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan) ------------------------ */

export const nvrDevicesKey = (marketId: string) =>
  domainKey(marketId, "nvr-devices");

export const camerasKey = (marketId: string, filters: CameraFilters) =>
  domainKey(marketId, "cameras", "list", filters);

export const discoveryRunKey = (
  marketId: string,
  nvrId: string,
  runId: string,
) => domainKey(marketId, "discovery-run", nvrId, runId);

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `market-queries.ts:140-150` dagi bilan AYNI sabab: `useAuthStore()` ni
 * har hookda takrorlash "bittasi tushib qoladi" xatosini kafolatlardi.
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
 * Kamera reestriga tegadigan har amalning yon ta'siri.
 *
 * Ro'yxat qo'lda emas, shu yerda quriladi (`market-queries.ts` dagi
 * `stallSideEffects` bilan aynan bir xil sabab): kashfiyot NVR
 * pasportini ham yangilaydi (`last_discovery_at`, `model`, `rtsp_port`),
 * ya'ni faqat ro'yxatni bekor qilish kartani eskirgan holda qoldirardi.
 */
const cameraSideEffects = (marketId: string) =>
  [domainKey(marketId, "cameras"), nvrDevicesKey(marketId)] as const;

/* --- NVR qurilmalari ------------------------------------------------------ */

/**
 * ⚠ `enabled` shartidagi `marketId !== null` QULAYLIK EMAS, KONTRAKT
 * (`market-queries.ts:186-192`).
 *
 * Bozorsiz sessiyada domen so'rovi serverda `409 market_not_selected`
 * oladi va o'sha xato kesh grafida yashab qolardi. Shu sababli
 * `marketId` `null` bo'lganda kalitdagi bo'sh satr ham xavfsiz: o'sha
 * kalit ostida hech qachon ma'lumot yozilmaydi.
 */
export function useNvrDevicesQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: nvrDevicesKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(NVR_DEVICES_PATH, { schema: nvrDeviceListResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

export type NvrCredentialsInput = {
  address: string;
  username: string;
  password: string;
};

/*
 * ⚠ PAROL YUBORADIGAN UCHALA CHAQIRUV HAM `useMutation` (`useQuery`
 *   EMAS) — `temp-password-dialog.tsx:23` dagi bilan AYNAN bir xil
 *   sabab: `useQuery` argumentlari `queryKey` ga tushadi va parol
 *   sessiya oxirigacha kesh grafida yashab qolardi. `useMutation` da
 *   argument keshga umuman kirmaydi.
 *
 *   Ikkinchi qatlam ham bor (`query-provider.tsx` sessiya o'zgarganda
 *   `clear()` qiladi), lekin u BIRINCHISINING o'rnini bosmaydi: bir
 *   sessiya ichida ochilgan devtools yoki xotira dumpi keshni baribir
 *   ko'rardi.
 */

/**
 * `POST /nvr-devices` — qurilmani ro'yxatga oladi (D-01: uchta maydon).
 *
 * ⚠ `address` XOM SATR bo'lib yuboriladi (`192.168.1.64:8080`,
 *   `https://nvr.local`). Uni `host`/`port`/`use_tls` ga ajratish
 *   SERVERDA (`app/services/nvr_host.py::split_address`) — klientdagi
 *   ajratish QULAYLIK, serverdagisi esa KONTRAKT. Klient tomonda
 *   ajratib yuborish ikkinchi, ajralib ketadigan grammatika tug'dirardi.
 */
export function useCreateNvr() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: NvrCredentialsInput) =>
      apiFetch(NVR_DEVICES_PATH, {
        method: "POST",
        body: input,
        schema: nvrDeviceSchema,
      }),
    onSuccess: () => invalidate(client, cameraSideEffects(marketId)),
  });
}

/**
 * `POST /nvr-devices/test-connection` — YOZUV YARATMAYDI (§4.3).
 *
 * ⚠ HAR DOIM 200 QAYTADI, xato holatida ham: javobning `ok: false` va
 *   `error_code` maydonlari xato blokini boshqaradi. Shuning uchun bu
 *   yerda `retry` sozlamasi ham kerak emas — TanStack 200 ni qayta
 *   urinishga arziydigan xato deb hisoblamaydi va D-03 buzilmaydi.
 *
 * Invalidatsiya YO'Q: chaqiruv hech narsani o'zgartirmaydi.
 */
export function useTestConnection() {
  return useMutation({
    mutationFn: (input: NvrCredentialsInput) =>
      apiFetch(`${NVR_DEVICES_PATH}/test-connection`, {
        method: "POST",
        body: input,
        schema: nvrTestConnectionResponseSchema,
      }),
  });
}

/**
 * `POST /nvr-devices/{id}/password` — 204, tanasiz (§4.6).
 *
 * ESKI PAROL SO'RALMAYDI: u bizda ochiq matnda yo'q. Darvoza boshqa
 * joyda — `CAMERA_MANAGE` huquqi.
 */
export function useUpdateNvrPassword() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { nvrId: string; password: string }) =>
      apiFetch(`${NVR_DEVICES_PATH}/${input.nvrId}/password`, {
        method: "POST",
        body: { password: input.password },
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, [nvrDevicesKey(marketId)]),
  });
}

/**
 * `POST /nvr-devices/{id}/discover` — 202, `run_id` bilan.
 *
 * 409 (`discovery_already_running`) XATO EMAS (UI-SPEC §5.6): javob
 * tanasida MAVJUD yugurishning `run_id` i keladi va chaqiruvchi o'sha
 * yugurishni poll qila boshlaydi. Shakl ajratish `camera-errors`
 * darajasida emas, chaqiruvchida (`discoveryRunIdOf`) — `ApiError.body`
 * ni bu yerda "yumshoq muvaffaqiyat" ga aylantirish mutatsiyaning
 * `onError` shartnomasini yashirardi.
 */
export function useStartDiscovery() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (nvrId: string) =>
      apiFetch(`${NVR_DEVICES_PATH}/${nvrId}/discover`, {
        method: "POST",
        schema: discoveryStartResponseSchema,
      }),
    onSuccess: () => invalidate(client, [nvrDevicesKey(marketId)]),
  });
}

/* --- Kashfiyot yugurishi: kodbazadagi BIRINCHI poll ----------------------- */

/**
 * Kashfiyot yugurishini kuzatadi (UI-SPEC §5.3).
 *
 * ⚠ POLL — BU KODBAZADAGI BIRINCHI NAQSH [O'LCHANDI: `grep -rn
 *   "refetchInterval" frontend/src` -> 0 hodisa]. Shuning uchun kontrakt
 *   shu yerda, bitta joyda o'rnatiladi va uch cheklovning HAMMASI
 *   majburiy:
 *
 *   1. TERMINAL HOLATDA POLL TO'XTAYDI (`succeeded`/`failed` -> `false`).
 *   2. YASHIRIN TABDA POLL YO'Q (`refetchIntervalInBackground: false`) —
 *      admin boshqa tabga o'tsa server bekorga yuklanmaydi; qaytganda
 *      `refetchOnWindowFocus` darhol yangilaydi.
 *   3. IKKI MUSTAQIL CHEGARA. **Cheksiz poll HECH QACHON:**
 *        (a) yugurishning `started_at` idan `DISCOVERY_POLL_TIMEOUT_MS`
 *            o'tsa — worker qotib qolgan holat;
 *        (b) ketma-ket `DISCOVERY_POLL_MAX_FAILURES` ta yiqilgan so'rov —
 *            server umuman javob bermayotgan holat, unda (a) ning
 *            hisoblagichi hech qachon boshlanmasdi.
 *
 * ⚠ CHEGARA SERVERNING `started_at` IGA TAYANADI, klientdagi taymerga
 *   EMAS. Sabab UI-SPEC §5.4 da: `?run=` bilan sahifa yangilanganda yoki
 *   yugurish BOSHQA QURILMADAN ochilganda klient taymeri noldan
 *   boshlanardi va qotib qolgan yugurish har yangilashda yana uch daqiqa
 *   poll qilinardi. Server vaqti esa bitta va u sahifa yangilanishidan
 *   omon o'tadi.
 */
export function useDiscoveryRunQuery(
  nvrId: string | null,
  runId: string | null,
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: discoveryRunKey(marketId ?? "", nvrId ?? "", runId ?? ""),
    queryFn: () =>
      apiFetch(
        `${NVR_DEVICES_PATH}/${nvrId}/discovery-runs/${runId}`,
        { schema: discoveryRunSchema },
      ),
    enabled: marketId !== null && nvrId !== null && runId !== null,
    refetchInterval: (query) =>
      discoveryPollInterval({
        status: query.state.data?.status,
        startedAt: query.state.data?.started_at ?? null,
        failureCount: query.state.fetchFailureCount,
        now: Date.now(),
      }),
    refetchIntervalInBackground: false,
    gcTime: 5 * 60_000,
  });
}

/**
 * Poll qarori — SOF FUNKSIYA (`refetchInterval` uni faqat chaqiradi).
 *
 * ⚠ NEGA HOOKDAN AJRATILGAN: qaror uchta chegarani birlashtiradi va
 *   ularning ikkitasini (uch daqiqa, uch yiqilish) haqiqiy poll bilan
 *   o'lchash testni real vaqtga bog'lab qo'yardi. Sof funksiya
 *   `now` ni ARGUMENT sifatida oladi, ya'ni chegarani soatni ushlab
 *   turmasdan tekshirish mumkin. Ikkinchi foyda: qaror TanStack
 *   ning ichki `query` shakliga bog'liq emas.
 */
export function discoveryPollInterval(input: {
  status: DiscoveryRunStatusValue | undefined;
  startedAt: string | null;
  failureCount: number;
  now: number;
}): number | false {
  // 1. Terminal holat — poll BUTUNLAY to'xtaydi.
  if (isTerminalRunStatus(input.status)) return false;

  // 2. Server javob bermayapti — `started_at` hech qachon kelmasligi
  //    mumkin, ya'ni 3-chegara yolg'iz yetarli emas.
  if (input.failureCount >= DISCOVERY_POLL_MAX_FAILURES) return false;

  // 3. Yugurish qotib qolgan (worker yiqilgan yoki javob yo'qolgan).
  if (
    input.startedAt !== null &&
    isDiscoveryTimedOut(input.startedAt, input.now)
  ) {
    return false;
  }

  return DISCOVERY_POLL_INTERVAL_MS;
}

/**
 * S5 (timeout) holatiga o'tildimi — panel shu bo'yicha chiziladi.
 *
 * Sof funksiya va hookdan AJRATILGAN: uni komponent test qila oladi va
 * u `Date.now()` ni chaqirmaydi (argument sifatida oladi), ya'ni test
 * soatni ushlab turishi shart emas.
 */
export function isDiscoveryTimedOut(
  startedAtIso: string,
  now: number,
): boolean {
  const started = Date.parse(startedAtIso);
  if (!Number.isFinite(started)) return false;
  return now - started >= DISCOVERY_POLL_TIMEOUT_MS;
}

/* --- Kameralar reestri ---------------------------------------------------- */

/**
 * `/cameras` filtrlari (UI-SPEC §6.1).
 *
 * Tiplar `string`, `UUID`/`boolean` EMAS: qiymatlar `nuqs` orqali
 * URL'dan keladi va URL har doim satr beradi (`StallFilters` bilan
 * aynan bir xil sabab).
 *
 * `archived` UCH HOLATLI va bu backend kontraktining ko'zgusi: `""` —
 * standart (arxivlanganlar yashirin), `"true"` — checkbox yoqilgan.
 * Farq `audit_log.new_value.filters` da ko'rinadi: «admin checkbox'ni
 * ataylab o'chirdi» va «umuman tegmadi» ikki xil hodisa.
 */
export type CameraFilters = {
  nvrId: string;
  status: string;
  archived: string;
};

export const EMPTY_CAMERA_FILTERS: CameraFilters = {
  nvrId: "",
  status: "",
  archived: "",
};

export function isCameraStatus(value: string): value is CameraStatusValue {
  return value === "online" || value === "offline" || value === "unknown";
}

function buildCamerasPath(filters: CameraFilters): string {
  const params = new URLSearchParams();
  // Nomlar backend'dagi `CameraQuery` dan.
  if (filters.nvrId) params.set("nvr_id", filters.nvrId);
  if (filters.status) params.set("status", filters.status);
  if (filters.archived) params.set("archived", filters.archived);
  params.set("limit", String(CAMERA_PAGE_SIZE));
  return `${CAMERAS_PATH}?${params.toString()}`;
}

/**
 * Kameralar reestri.
 *
 * ⚠ QAYTA SARALANMAYDI: tartib SERVERDA `channel_no` bo'yicha o'sish
 *   tartibida hal qilinadi va u NVR dagi jismoniy uyaga mos keladi
 *   (UI-SPEC §6.1 — «Saralash boshqaruvi YO'Q»). Klient tomonda
 *   saralash uchala tilda boshqa natija berardi.
 */
export function useCamerasQuery(
  filters: CameraFilters,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: camerasKey(marketId ?? "", filters),
    queryFn: () =>
      apiFetch(buildCamerasPath(filters), { schema: cameraListResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/**
 * Kamera nomini o'zgartiradi yoki NVR dagi nomga QAYTARADI (§6.5).
 *
 * ⚠ `name` va `name_overridden` BIRGA yuboriladi va bu backendning
 *   talabi: bayroq nomning HOSILASI — ularni ajratish oradagi skanning
 *   nomni bosib ketishiga yo'l ochardi (`nvr_repo.rename_camera`).
 *   Qaytarish esa `{name_overridden: false}` — nomsiz.
 */
export function useRenameCamera() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { cameraId: string; name: string } | { cameraId: string; resetToDeviceName: true }) =>
      apiFetch(`${CAMERAS_PATH}/${input.cameraId}`, {
        method: "PATCH",
        body:
          "resetToDeviceName" in input
            ? { name_overridden: false }
            : { name: input.name },
        schema: cameraSchema,
      }),
    onSuccess: () => invalidate(client, [domainKey(marketId, "cameras")]),
  });
}

/**
 * Kamerani ARXIVLAYDI (D-10).
 *
 * ⚠ `DELETE` marshruti backendда UMUMAN YO'Q va bu KELISHUV EMAS,
 *   STRUKTURA: snapshot (4-faza) va zona bog'lanishlari (5-faza)
 *   `cameras.id` ga qadaladi. Fe'lning o'zi ham darvoza ostida —
 *   `scripts/nvr-copy.test.mjs` (G-4).
 */
export function useArchiveCamera() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (cameraId: string) =>
      apiFetch(`${CAMERAS_PATH}/${cameraId}/archive`, {
        method: "POST",
        schema: cameraSchema,
      }),
    onSuccess: () => invalidate(client, [domainKey(marketId, "cameras")]),
  });
}

/**
 * Arxivdan qaytaradi — tasdiqsiz (§9.3).
 *
 * MAJBURIY JUFT: usiz arxivlash amalda qaytarib bo'lmaydigan bo'lardi
 * va u holda §9.2 bo'yicha 2-darajali tasdiq talab qilinardi.
 */
export function useRestoreCamera() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (cameraId: string) =>
      apiFetch(`${CAMERAS_PATH}/${cameraId}/restore`, {
        method: "POST",
        schema: cameraSchema,
      }),
    onSuccess: () => invalidate(client, [domainKey(marketId, "cameras")]),
  });
}

/**
 * Jonli ko'rish CHIPTASI (§8.3).
 *
 * ⚠ `useMutation`, `useQuery` EMAS — va bu yerda sabab paroldan BOSHQA:
 *   chipta 60 soniya yashaydi, ya'ni keshlangan qiymat deyarli har doim
 *   MUDDATI O'TGAN bo'lardi va "qayta ishlatilgan chipta" ni tuzatib
 *   bo'lmas nosozlikka aylantirardi. Bundan tashqari har chaqiruv
 *   serverda avtorizatsiyani QAYTA tekshiradi va `audit_log` ga
 *   `reason='live_view'` yozadi — keshlangan javob o'sha izni
 *   yo'qotardi (D-08).
 */
export function useLiveToken() {
  return useMutation({
    mutationFn: (cameraId: string) =>
      apiFetch(`${CAMERAS_PATH}/${cameraId}/live-token`, {
        method: "POST",
        schema: liveTokenSchema,
      }),
  });
}
