"use client";

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, apiRequest } from "@/lib/api-client";
import {
  cameraZoneListSchema,
  captureDaySchema,
  zoneCoverageSchema,
} from "@/lib/api-types";
import type { CaptureRun } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * ZONA MUHARRIRINING SERVER HOLATI (05-06 kontrakti, UI-SPEC §5.4).
 *
 * `snapshot-queries.ts` TO'LIQ SHABLON. To'rtinchi modul o'sha sababdan
 * ochildi: har domenning invalidatsiya to'plami O'ZINIKI va ularni bitta
 * faylga yig'ish «zonani saqlash kun jurnalini ham bekor qiladimi?»
 * savolini har tahrirda qaytarardi.
 *
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa
 *   yaratilmaydi. GLOBAL (marketsiz) KALIT KONSTANTASI BU MODULDA
 *   UMUMAN YO'Q: har fabrikaning BIRINCHI argumenti `marketId`.
 *
 * ⚠ TIP TIZIMI YOLG'IZ YETARLI EMAS va bu 04-02 da O'LCHANGAN: kalitdan
 *   `marketId` ni tushirib qoldirish typecheck'ni qizartiradi, lekin
 *   birinchi argument o'rniga DOMEN NOMINI berish TIP JIHATIDAN
 *   YAROQLI — kalit hamma bozor uchun bir xil bo'lib qolardi va faqat
 *   A bozorining zonalari B bozorining sessiyasida ko'rinardi (CR-01).
 *   Shuning uchun kalit SHAKLI `camera-zone-queries.test.tsx` da qiymat
 *   bo'yicha ham qulflanadi.
 *
 * ⛔ POLL YO'Q — VA BU BUTUN Y-1 YUZASI UCHUN (§8.5, birinchi qator).
 *   Zonalar FAQAT foydalanuvchining o'z tahriridan o'zgaradi: birorta
 *   fon jarayoni poligon chizmaydi. `refetchOnWindowFocus` (global
 *   standart) yetarli — ikkinchi tabda saqlangan o'zgarish admin
 *   qaytganda o'zi keladi. Poll qo'yish esa AYNAN CHIZIQ SUDRAYOTGAN
 *   paytda javob kelib, tugallanmagan poligonni bosib ketish yo'lini
 *   ochardi.
 *
 * ⚠ `query-provider.tsx` O'ZGARTIRILMAYDI — sessiya identifikatori
 *   o'zgarganda `client.clear()` butun keshni bo'shatadi.
 * =============================================================================
 */

/* --- Yo'l konstantalari --------------------------------------------------- */

export const CAMERA_ZONES_PATH = "/camera-zones";

/**
 * Kadr manbai — 4-fazaning kun jurnali.
 *
 * ⚠ NEGA MAHZ SHU YO'L: `GET /camera-zones` javobi kadr NISBATINI beradi,
 *   lekin kadrning IDENTIFIKATORINI bermaydi (05-06 kontrakti), ya'ni
 *   rasm baytlarini so'raydigan yo'l boshqa joydan kelishi kerak. Buning
 *   uchun mavjud YAGONA manba — `capture_runs` qatorlaridagi
 *   `snapshot_id`. Cheklovi va sababi `latestOkFrame()` da yozilgan.
 */
export const CAPTURE_RUNS_PATH = "/capture-runs";

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

export const cameraZonesKey = (marketId: string, cameraId: string) =>
  domainKey(marketId, "camera-zones", cameraId);

export const zoneCoverageKey = (marketId: string) =>
  domainKey(marketId, "zone-coverage");

/**
 * Kadr izlash so'rovi — `cameraZonesKey` ning BOLASI, mustaqil fabrika EMAS.
 *
 * `snapshot-dialog.tsx::snapshotImageKey` da o'rnatilgan naqsh: bola
 * kalit doiralashni MEROS oladi va ota kalitning bekor qilinishi uni ham
 * qamraydi (TanStack prefiks bo'yicha solishtiradi). Yangi global
 * fabrika bu yerda ikkinchi doiralash yuzasini ochardi.
 */
export const cameraFrameKey = (
  marketId: string,
  cameraId: string,
  day: string,
) => [...cameraZonesKey(marketId, cameraId), "frame", day] as const;

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `snapshot-queries.ts:111-114` bilan AYNI sabab: `useAuthStore()` ni har
 * hookda takrorlash «bittasi tushib qoladi» xatosini kafolatlardi.
 * Funksiya EKSPORT QILINMAYDI — u modulning ichki kontrakti.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Zonalar ro'yxati ------------------------------------------------------ */

/**
 * `GET /camera-zones?camera_id=…` — kameraning FAOL zonalari (§6.3 zona B).
 *
 * ⚠ `enabled` shartidagi `marketId !== null` QULAYLIK EMAS, KONTRAKT
 *   (`market-queries.ts:186-192`). Bozorsiz sessiyada domen so'rovi
 *   serverda `409 market_not_selected` oladi va o'sha XATO kesh grafida
 *   yashab qolardi. Shu sababli `marketId` `null` bo'lganda kalitdagi
 *   bo'sh satr ham xavfsiz: u kalit ostida hech qachon ma'lumot
 *   yozilmaydi.
 */
export function useCameraZones(
  cameraId: string | null,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: cameraZonesKey(marketId ?? "", cameraId ?? ""),
    queryFn: () =>
      apiFetch(
        `${CAMERA_ZONES_PATH}?camera_id=${encodeURIComponent(cameraId ?? "")}`,
        { schema: cameraZoneListSchema },
      ),
    enabled:
      marketId !== null && cameraId !== null && (options?.enabled ?? true),
  });
}

/* --- Qamrov kartasi (D-22) ------------------------------------------------- */

/**
 * `GET /camera-zones/coverage` — uchlik, HAR DOIM uchalasi (§6.9).
 *
 * ⚠ POLL YO'Q, bu yerda ham: qamrov zonalarni saqlashdan VA rasta
 *   yaratishdan o'zgaradi — ikkalasi ham foydalanuvchining amali.
 */
export function useZoneCoverage(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: zoneCoverageKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(`${CAMERA_ZONES_PATH}/coverage`, { schema: zoneCoverageSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/* --- Kadr manbai ----------------------------------------------------------- */

/**
 * Kun jurnalidagi qatorlardan BITTA kameraning eng so'nggi YAROQLI kadri.
 *
 * SOF FUNKSIYA — so'rov qatlamidan mustaqil, ya'ni tanlov qoidasi test
 * bilan yolg'iz o'lchanadi (`camera-page-state.ts` da o'rnatilgan naqsh).
 *
 * ⚠ SHART SERVERNIKI BILAN AYNAN BIR XIL BO'LISHI KERAK: 05-06 ning
 *   `latest_frame_size()` i FAQAT `quality_verdict = 'ok'` kadrni oladi
 *   va eng so'nggisini `captured_at` bo'yicha tanlaydi. Bu yerda
 *   `captured_at` yo'q (jurnal qatori uni bermaydi), shuning uchun BIR
 *   KUN ICHIDA `slot_time` bo'yicha eng kechi olinadi — u shu kun uchun
 *   `captured_at` tartibi bilan bir xil natija beradi (slotlar kun
 *   davomida o'sish tartibida bajariladi).
 *
 * ⚠ `snapshot_id === null` QATOR TASHLAB YUBORILADI: sifat hukmi `ok`
 *   bo'lsa ham kadr arxivdan chiqarilgan bo'lishi mumkin va u holda
 *   rasm marshruti hech qachon bayt bermasdi.
 */
export function latestOkFrame(
  rows: readonly CaptureRun[] | undefined,
  cameraId: string,
): CaptureRun | null {
  if (rows === undefined) return null;

  let best: CaptureRun | null = null;
  for (const row of rows) {
    if (row.camera_id !== cameraId) continue;
    if (row.quality_verdict !== "ok") continue;
    if (row.snapshot_id === null) continue;
    if (best === null || row.slot_time > best.slot_time) best = row;
  }
  return best;
}

/**
 * Kameraning chiziladigan kadri — bugun, topilmasa kecha.
 *
 * =========================================================================
 * ⚠ BU IKKI SO'ROVLI QIDIRUV — 05-06 KONTRAKTIDAGI BO'SHLIQNING O'RNI.
 *
 *   `GET /camera-zones` javobida `frame_width`/`frame_height` bor, lekin
 *   o'sha kadrning IDENTIFIKATORI YO'Q. Ya'ni server «nisbat mana bu
 *   kadrdan olindi» deydi, lekin qaysi kadr ekanini aytmaydi. Rasm esa
 *   `GET /snapshots/{id}/image` dan keladi, ya'ni identifikator SHART.
 *
 *   To'g'ri yechim — javobga `frame_snapshot_id` qo'shish (bir maydon):
 *   shunda nisbat ham, ko'rsatilayotgan rasm ham AYNAN BIR kadrdan
 *   bo'lardi. Bu reja backend fayllariga tegmaydi, shuning uchun bu yerda
 *   klient tomondan izlanadi va farq EKRANDA KO'RINADI: `cameraZones.frameAt`
 *   topilgan kadrning vaqtini yozadi, ya'ni admin qaysi kadr ustida
 *   chizayotganini ko'radi. Qoldiq xavf — nisbat lentasi (§6.8) server
 *   ko'rgan kadrga tegishli bo'lib, ekranda boshqa kadr turishi; u
 *   OGOHLANTIRISH, hisob emas.
 *
 * ⚠ IKKI KUN — CHEGARA, TAXMIN EMAS. Jadval kuniga 7 slot bajaradi
 *   (4-faza), ya'ni 48 soat ichida birorta yaroqli kadr bermagan kamera
 *   — kadr olish bo'limida hal qilinadigan nosozlik. E-1 ning amali
 *   (`[Kadr olishga o'tish]`) aynan o'sha bo'limga olib boradi. Uzunroq
 *   oyna har ochilishda ko'proq so'rov qilib, o'sha xulosani sekinroq
 *   berardi.
 * =========================================================================
 */
export function useCameraFrame(
  cameraId: string | null,
  todayIso: string,
  yesterdayIso: string,
) {
  const marketId = useMarketId();

  const today = useQuery({
    queryKey: cameraFrameKey(marketId ?? "", cameraId ?? "", todayIso),
    queryFn: () =>
      apiFetch(`${CAPTURE_RUNS_PATH}?day=${encodeURIComponent(todayIso)}`, {
        schema: captureDaySchema,
      }),
    enabled: marketId !== null && cameraId !== null,
  });

  const todayFrame = latestOkFrame(today.data?.rows, cameraId ?? "");

  /*
   * ⚠ IKKINCHI SO'ROV FAQAT BIRINCHISI TUGAGACH VA BO'SH CHIQQACH
   *   yuboriladi. `today.isSuccess` sharti majburiy: `todayFrame === null`
   *   yuklanish paytida ham to'g'ri bo'ladi va usiz ikkala so'rov
   *   BIR VAQTDA ketardi — ya'ni har ochilishda ikki barobar yuk.
   */
  const yesterday = useQuery({
    queryKey: cameraFrameKey(marketId ?? "", cameraId ?? "", yesterdayIso),
    queryFn: () =>
      apiFetch(`${CAPTURE_RUNS_PATH}?day=${encodeURIComponent(yesterdayIso)}`, {
        schema: captureDaySchema,
      }),
    enabled:
      marketId !== null &&
      cameraId !== null &&
      today.isSuccess &&
      todayFrame === null,
  });

  const frame =
    todayFrame ?? latestOkFrame(yesterday.data?.rows, cameraId ?? "");

  return {
    frame,
    isPending: today.isPending || (yesterday.fetchStatus !== "idle" && yesterday.isPending),
    isError: today.isError || yesterday.isError,
  };
}

/* --- Kadr baytlari ---------------------------------------------------------- */

export const SNAPSHOTS_PATH = "/snapshots";

/**
 * Kadr rasmining kesh kaliti — `camera-zones` domenining bolasi.
 *
 * ⚠ `snapshot-dialog.tsx::snapshotImageKey` QAYTA ISHLATILMADI va bu
 *   ongli tanlov: uni import qilish MA'LUMOT QATLAMINI KOMPONENTGA
 *   bog'lardi (`lib/` -> `components/`), ya'ni bog'liqlik yo'nalishi
 *   teskari bo'lardi. Narxi — bir xil baytlarni ikkala yuza ham ochiq
 *   bo'lgan holatda ikki marta so'rash; u nazariy (dialog kadr olish
 *   sahifasida, muharrir esa boshqa marshrutda) va `gcTime: 0` bilan
 *   baribir keshda qolmaydi.
 */
export const frameImageKey = (marketId: string, snapshotId: string) =>
  domainKey(marketId, "camera-zones", "frame-image", snapshotId);

/**
 * `GET /api/v1/snapshots/{id}/image` — SESSIYA TOKENI bilan, proxy orqali.
 *
 * ⚠ BRAUZERNING O'ZI SO'ROV YUBORA OLMAYDI: marshrut sessiya tokenini
 *   talab qiladi va `<image>` elementi sarlavha qo'sha olmaydi. Shuning
 *   uchun baytlar `apiRequest` bilan olinadi va brauzer ichidagi
 *   vaqtinchalik havolaga aylantiriladi — u sahifadan tashqariga
 *   chiqmaydi, ulashilmaydi va komponent yopilganda BEKOR QILINADI
 *   (`snapshot-dialog.tsx:441-470` naqshi).
 *
 * ⚠ `gcTime: 0` — kadr TASHRIFCHILARNING shaxsiy ma'lumoti; uni keshda
 *   ushlab turish uchun hech qanday sabab yo'q va uni ushlab turish
 *   sessiya almashganda ham xotirada qoldirardi.
 */
export function useFrameImageHref(snapshotId: string | null): string | null {
  const marketId = useMarketId();

  const image = useQuery({
    queryKey: frameImageKey(marketId ?? "", snapshotId ?? ""),
    queryFn: async () => {
      const response = await apiRequest(
        `${SNAPSHOTS_PATH}/${snapshotId ?? ""}/image`,
      );
      return URL.createObjectURL(await response.blob());
    },
    enabled: marketId !== null && snapshotId !== null,
    gcTime: 0,
    retry: false,
    staleTime: Infinity,
  });

  const href = image.data ?? null;

  useEffect(() => {
    if (href === null) return;
    return () => URL.revokeObjectURL(href);
  }, [href]);

  return href;
}

/* --- Muharrir darvozasi (Z-1…Z-8) ------------------------------------------ */

/**
 * Sahifaning to'rt tarmog'i — `Z-3`…`Z-7` «ready» ning ICHIDA yashaydi.
 *
 * `Z-3` (kadr bor, zona yo'q) muharrirni OCHADI va bo'sh holatni zonalar
 * ro'yxati ichida ko'rsatadi — kadr yuzasi bo'sh emas, u kadrni
 * ko'rsatadi. `Z-5` (nisbat farqi) va `Z-6`/`Z-7` (saqlash) esa
 * muharrirning ICHKI holatlari, ya'ni ular bu qarordan keyin keladi.
 */
export type ZoneEditorState = "loading" | "load-failed" | "no-frame" | "ready";

/**
 * Muharrir ochiladimi — SOF FUNKSIYA (§8.2, Z-1…Z-8).
 *
 * ⛔ Z-2 QAT'IY: kamerada yaroqli kadr bo'lmasa muharrir UMUMAN
 *    OCHILMAYDI. Fonsiz chizish ma'nosiz — admin bo'sh to'rtburchakka
 *    poligonlar qo'yib, ular kadrda qayerga tushishini KO'RMASDI va
 *    natijani faqat birinchi bandlik hisobotida sezardi.
 *
 * ⚠ TARTIB AHAMIYATLI VA U SHU YERDA QULFLANADI:
 *
 *     xato -> yuklanmoqda -> kadr yo'q -> tayyor
 *
 *   Xato pastga tushsa, so'rov yiqilgan holat «kadr yo'q» bo'lib
 *   ko'rinardi va admin nosozlikni kadr olish bo'limidan qidirardi —
 *   holbuki muammo tarmoqda yoki serverda. Bu ikki holatning KEYINGI
 *   QADAMI butunlay boshqa: birinchisida «Qayta urinish», ikkinchisida
 *   «Kadr olishga o'tish».
 *
 * ⚠ IKKI SHART VA BILAN EMAS, YOKI BILAN: serverning `frame_width` i
 *   `null` bo'lishi «bu kamera hech qachon yaroqli kadr bermagan»
 *   demakdir; klient kadr topa olmasligi esa «oxirgi 48 soatda yaroqli
 *   kadr yo'q» demakdir. Ikkalasining ham OQIBATI bir xil — hozir chizib
 *   bo'lmaydi — va ikkalasining ham keyingi qadami bitta: kadr olish
 *   bo'limi. Ularni ikki xil ekranga ajratish adminga farqi bo'lmagan
 *   tanlov taklif qilardi.
 */
export function zoneEditorState(input: {
  isError: boolean;
  isPending: boolean;
  /** `GET /camera-zones` javobidagi `frame_width` (nisbat langari). */
  frameWidth: number | null | undefined;
  /** Klient topgan kadr qatori — rasm baytlarining manbai. */
  frameSnapshotId: string | null;
}): ZoneEditorState {
  if (input.isError) return "load-failed";
  if (input.isPending) return "loading";
  if (
    input.frameWidth === null ||
    input.frameWidth === undefined ||
    input.frameSnapshotId === null
  ) {
    return "no-frame";
  }
  return "ready";
}

/* --- Saqlash --------------------------------------------------------------- */

/**
 * `PUT /camera-zones?camera_id=…` tanasidagi BITTA zona.
 *
 * ⛔ `id` va `version` YUBORILMAYDI va ular sxemada ham YO'Q: versiya
 *    SERVERDA `MAX(version)` dan hisoblanadi (05-06). Klient versiya
 *    yuborsa, ikki tabda ochilgan muharrir bir xil raqamni qayta
 *    ishlatib, sababsiz 409 berardi.
 */
export type CameraZoneWriteInput = {
  stallId: string;
  /** Normalangan (0..1) tepalar — piksel EMAS. */
  polygon: readonly (readonly [number, number])[];
  sourceWidth: number;
  sourceHeight: number;
};

/**
 * `PUT /camera-zones?camera_id=…` — kameraning TO'LIQ holati (§6.6).
 *
 * ⛔ QISMAN SAQLASH YO'Q: ro'yxatda bo'lmagan faol zona SERVERDA
 *    eskirtiriladi. Ya'ni tana har doim muharrirdagi BARCHA zonalarni
 *    olib yuradi — «faqat o'zgarganini yuborish» optimizatsiyasi
 *    o'chirishni ifodalay olmasdi.
 *
 * ⚠ KOORDINATA QAYTA YAXLITLANMAYDI. Server 0..1 sonlarni qanday kelsa
 *   shunday saqlaydi va piksellarga o'tkazish FAQAT aniqlash paytida,
 *   serverning `denormalize()` i bilan bo'ladi. Klientda yaxlitlash
 *   ikkinchi (va boshqacha) yaxlitlash nuqtasini ochardi — 05-06 ning S6
 *   sabotaji aynan shu sinfning narxini o'lchagan.
 *
 * ⚠ JAVOB `GET` BILAN BIR XIL SHAKLDA keladi, shuning uchun u keshga
 *   TO'G'RIDAN-TO'G'RI yoziladi (`setQueryData`) va qayta so'rov
 *   YUBORILMAYDI. Qamrov esa bekor qilinadi: yangi zona `covered`/
 *   `uncovered` sonlarini o'zgartiradi.
 */
export function useReplaceCameraZones(cameraId: string) {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (zones: readonly CameraZoneWriteInput[]) =>
      apiFetch(
        `${CAMERA_ZONES_PATH}?camera_id=${encodeURIComponent(cameraId)}`,
        {
          method: "PUT",
          body: {
            zones: zones.map((zone) => ({
              stall_id: zone.stallId,
              polygon: zone.polygon.map((point) => [point[0], point[1]]),
              source_width: zone.sourceWidth,
              source_height: zone.sourceHeight,
            })),
          },
          schema: cameraZoneListSchema,
        },
      ),
    onSuccess: (data) => {
      client.setQueryData(cameraZonesKey(marketId, cameraId), data);
      void client.invalidateQueries({ queryKey: zoneCoverageKey(marketId) });
    },
  });
}
