"use client";

import { useEffect } from "react";
import { ChevronLeft, ChevronRight, ImageOff, TriangleAlert } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";

import { channelLabel } from "@/components/cameras/camera-row";
import { captureCellState } from "@/components/snapshots/capture-cell";
import { formatSlotTime } from "@/components/snapshots/schedule-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { apiRequest } from "@/lib/api-client";
import type { CaptureRun, SnapshotDetail } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { captureErrorView } from "@/lib/capture-errors";
import { cn } from "@/lib/cn";
import { SNAPSHOTS_PATH, snapshotKey, useSnapshotDetail } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * DL-3 — KADR DETALI (§6.6, D-12, D-16, D-18).
 *
 * ⛔⛔ SIFAT HUKMI VA YORUG'LIK REJIMI BITTA JUMLAGA BIRLASHADI.
 *
 *     Ikki alohida belgi (`[Qorong'i]` `[Tungi rejim]`) RAD ETILDI va
 *     sabab D-12 ning butun mazmuni: ular IKKI FAKT beradi, lekin
 *     XULOSA bermaydi. Adminning savoli bitta — «kamera buzuqmi?» — va
 *     unga javob faqat JUFTLIKNING TALQINIDAN chiqadi:
 *
 *       qorong'i + tungi rejim  -> NORMAL, hech nima qilinmaydi;
 *       qorong'i + kunduzgi rejim -> NOSOZLIK, linza va yoritish tekshiriladi.
 *
 *     Ikki belgi bu talqinni foydalanuvchining zimmasiga yuklardi — va u
 *     buni kuniga 175 marta takrorlashi kerak bo'lardi. Shuning uchun
 *     sakkiz juftlik — sakkiz jumla.
 *
 * ⛔⛔ RASM FAQAT `core-api` PROXYSIDAN KELADI (§14.3).
 *
 *     Oldindan imzolangan havola SO'RALMAYDI va ombor kaliti EKRANGA
 *     CHIQMAYDI. Sabab to'rtta va ularning hech biri qulaylik haqida
 *     emas: (1) bunday havola muddati tugagunicha O'QISH IZISIZ ishlaydi
 *     va kadr shaxsiy ma'lumot; (2) u sessiyadan mustaqil bo'lib qoladi,
 *     ya'ni rol o'zgarsa yoki bozor almashsa ham tirik; (3) u ombor
 *     manzilini brauzer tarixiga va nusxalangan havolaga chiqaradi;
 *     (4) manzil tashqariga chiqmasa, O'zbekiston hostingiga ko'chish
 *     sozlama o'zgarishi bo'lib qoladi — refaktor emas.
 *
 *     ⚠ Baytlar `apiRequest` orqali olinadi (sessiya tokeni bilan) va
 *       brauzer ichida vaqtinchalik havolaga aylantiriladi. Ya'ni HAR
 *       ochilish serverda `audit_read` yozadi — «kim ko'rdi» dalili
 *       nizoda aynan shu yerdan chiqadi.
 *
 * ⚠ RASM YUKLANMAGANDA QORA TO'RTBURCHAK CHIZILMAYDI (§9.5): u
 *   «buzilgan» degan YOLG'ON signal berardi. Yuklanish paytida och fon +
 *   skelet, xato bo'lganda esa ikonka va aniq jumla — dialog YIQILMAYDI.
 *
 * ⚠ C5…C9 HUJAYRALARIDA RASM UMUMAN YO'Q — o'rniga SABAB + NIMA QILISH
 *   KERAK + KIM TUZATADI bloki (§10.5). Uchinchi qator (`actor`) 4-fazada
 *   yangi: xatolarning bir qismi bozor adminining ishi EMAS va usiz u
 *   soatlab NVR sozlamalarini titkilardi.
 *
 * ⚠ NOMA'LUM XATO KODIDA XOM TAFSILOT KO'RSATILMAYDI (T-02-99): u ichki
 *   tuzilma va yo'llarni oshkor qilishi mumkin. Foydalanuvchi umumiy
 *   xabarni ko'radi.
 * =============================================================================
 */

type VerdictKey =
  | "snapshots.verdict.okDay"
  | "snapshots.verdict.okLowLight"
  | "snapshots.verdict.okIrNight"
  | "snapshots.verdict.darkIrNight"
  | "snapshots.verdict.darkLowLight"
  | "snapshots.verdict.darkDay"
  | "snapshots.verdict.blank"
  | "snapshots.verdict.corrupt";

/**
 * ⛔ SAKKIZ JUFTLIK -> SAKKIZ JUMLA (§6.6 jadvali) — SOF FUNKSIYA.
 *
 * `null` — hukm noma'lum. Sakkiztadan birortasini «taxminan» tanlash
 * ekranga tekshirilmagan da'vo chiqarardi, holbuki bu jumla aynan
 * DA'VONING o'zi.
 *
 * ⚠ NOMA'LUM YORUG'LIK REJIMI `darkDay` GA HECH QACHON TUSHMAYDI.
 *   `darkDay` — sakkiztadan YAGONA nosozlik e'lon qiladigan jumla
 *   («linzani tekshiring»). O'lchov yo'qligidan yolg'on nosozlik
 *   chiqarish jimgina o'tkazib yuborishdan yomonroq: admin mavjud
 *   bo'lmagan muammoni qidirib, haqiqiylariga ishonchini yo'qotardi.
 *   Shuning uchun `dark` + noma'lum rejim `darkLowLight` ga tushadi.
 */
export function verdictKey(
  verdict: string,
  lightMode: string,
): VerdictKey | null {
  switch (verdict) {
    case "ok":
      if (lightMode === "ir_night") return "snapshots.verdict.okIrNight";
      if (lightMode === "low_light") return "snapshots.verdict.okLowLight";
      return "snapshots.verdict.okDay";
    case "dark":
      if (lightMode === "ir_night") return "snapshots.verdict.darkIrNight";
      if (lightMode === "day") return "snapshots.verdict.darkDay";
      return "snapshots.verdict.darkLowLight";
    case "blank":
      return "snapshots.verdict.blank";
    case "corrupt":
      return "snapshots.verdict.corrupt";
    default:
      return null;
  }
}

const LIGHT_MODE_KEYS = {
  day: "snapshots.lightMode.day",
  low_light: "snapshots.lightMode.lowLight",
  ir_night: "snapshots.lightMode.irNight",
  unknown: "snapshots.lightMode.unknown",
} as const;

type MethodKey =
  | "snapshots.method.stream"
  | "snapshots.method.device"
  | "snapshots.method.fallback";

/**
 * Xom usul tokeni -> inson tili (§10.7).
 *
 * ⚠ XOM TOKENNING O'ZI XABAR KATALOGIGA KIRMAYDI [O'LCHANDI: M-3]: u
 *   raqam aralashgan lotin token va transliteratorda buziladi, override
 *   esa uni TUZATA OLMAYDI. Shuning uchun yuzada inson tili turadi,
 *   token esa API javobidan to'g'ridan-to'g'ri, faqat yig'iladigan
 *   blok ichida chiziladi — dala diagnostikasida «qaysi yo'l bilan
 *   olingan?» birinchi savol va texnik yordam aynan tokenni tushunadi.
 *
 * ⚠ BU XARITA OBYEKT LITERALI EMAS, SOLISHTIRUV — va bu ATAYIN.
 *   3-fazaning go2rtc darvozasi (`nvr-copy.test.mjs` G-6) o'sha
 *   xizmatning MANBA SXEMALARINI taqiqlaydi, chunki ular RCE yuzasi
 *   bo'lgan oqim boshqaruv API'siga uzatiladi. Obyekt kaliti sifatida
 *   yozilgan zaxira usul nomi o'sha sxemaning aynan matniga aylanardi
 *   va darvoza — TO'G'RI ravishda — qizarardi. Darvoza
 *   KUCHSIZLANTIRILMADI; o'zgargan narsa — shu yerdagi kodning SHAKLI.
 */
function methodKeyOf(method: string): MethodKey | null {
  if (method === "go2rtc") return "snapshots.method.stream";
  if (method === "isapi") return "snapshots.method.device";
  if (method === "ffmpeg") return "snapshots.method.fallback";
  return null;
}

const TIER_KEYS = {
  full: "snapshots.tierFull",
  compressed: "snapshots.tierCompressed",
  purged: "snapshots.tierPurged",
} as const;

const TIER_WHY_KEYS = {
  compressed: "snapshots.tierCompressedWhy",
  purged: "snapshots.tierPurgedWhy",
} as const;

/**
 * Rasm so'rovining kesh kaliti — MAVJUD kalit fabrikasining BOLASI.
 *
 * ⚠ Yangi global fabrika QURILMAYDI: `snapshotKey` ning birinchi
 *   argumenti allaqachon `marketId` va bola kalit o'sha doiralashni
 *   MEROS oladi. Qo'shimcha foyda: detalning bekor qilinishi rasmni ham
 *   bekor qiladi (TanStack prefiks bo'yicha solishtiradi).
 */
export function snapshotImageKey(
  marketId: string,
  snapshotId: string,
): readonly unknown[] {
  return [...snapshotKey(marketId, snapshotId), "image"];
}

export function SnapshotDialog({
  cameraName,
  canNext,
  canPrev,
  channelNo,
  onNavigate,
  onOpenChange,
  open,
  run,
}: {
  cameraName: string;
  canNext: boolean;
  canPrev: boolean;
  channelNo: number;
  /** ⚠ O'SHA QATORDAGI oldingi/keyingi VAQT — kamera bo'ylab emas (§6.6). */
  onNavigate: (direction: -1 | 1) => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  run: CaptureRun | null;
}) {
  const t = useTranslations();

  const title =
    run === null
      ? t("snapshots.logTitle")
      : t("snapshots.detailTitle", {
          camera: cameraName,
          channel: channelLabel(channelNo),
          time: formatSlotTime(run.slot_time),
        });

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Content
        description={t("snapshots.detailDescription")}
        sheetOnMobile
        size="lg"
        srOnlyDescription
        title={title}
      >
        {run === null ? null : <DetailBody run={run} />}

        {/*
         * ⚠ NAVIGATSIYA O'SHA QATOR ICHIDA: admin bitta kameraning kunini
         *   ketma-ket ko'radi. Kamera bo'ylab ko'chish «bu qaysi
         *   kamera edi?» savolini har bosishda qaytarardi.
         */}
        <Dialog.Footer className="justify-between sm:flex-row">
          <Button
            aria-disabled={!canPrev}
            onClick={() => {
              if (canPrev) onNavigate(-1);
            }}
            size="sm"
            variant="secondary"
          >
            <ChevronLeft aria-hidden="true" />
            {t("snapshots.prevSlot")}
          </Button>
          <Button
            aria-disabled={!canNext}
            onClick={() => {
              if (canNext) onNavigate(1);
            }}
            size="sm"
            variant="secondary"
          >
            {t("snapshots.nextSlot")}
            <ChevronRight aria-hidden="true" />
          </Button>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}

function DetailBody({ run }: { run: CaptureRun }) {
  /*
   * ⛔ KADR YO'Q BO'LSA RASM HAM YO'Q (C5…C9). O'rniga SABAB + NIMA
   *    QILISH KERAK + KIM TUZATADI bloki — «nega?» savoli javobsiz
   *    qolmaydi.
   */
  if (run.snapshot_id === null) {
    return <CaptureFailureBlock run={run} />;
  }
  return <SnapshotBody run={run} snapshotId={run.snapshot_id} />;
}

function SnapshotBody({
  run,
  snapshotId,
}: {
  run: CaptureRun;
  snapshotId: string;
}) {
  const t = useTranslations();
  const detail = useSnapshotDetail(snapshotId);

  if (detail.isPending) {
    return (
      <div aria-busy="true" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="aspect-video w-full" />
      </div>
    );
  }

  if (detail.isError) {
    return <CaptureFailureBlock run={run} />;
  }

  return <SnapshotDetailView detail={detail.data} />;
}

function SnapshotDetailView({ detail }: { detail: SnapshotDetail }) {
  const t = useTranslations();
  const format = useFormatter();

  const tierKey = TIER_KEYS[detail.storage_tier as keyof typeof TIER_KEYS];
  const tierWhyKey =
    TIER_WHY_KEYS[detail.storage_tier as keyof typeof TIER_WHY_KEYS];
  const isPurged = detail.storage_tier === "purged";
  const verdict = verdictKey(detail.quality_verdict, detail.light_mode);
  const lightKey =
    LIGHT_MODE_KEYS[detail.light_mode as keyof typeof LIGHT_MODE_KEYS];
  const methodKey = methodKeyOf(detail.capture_method);

  return (
    <div className="flex flex-col gap-4">
      {isPurged ? (
        /*
         * ⛔ 455 kundan keyin obyekt o'chiriladi, QATOR esa QOLADI
         *    (04-RESEARCH §D.10). Bu holat EKRANDA halol ko'rsatiladi:
         *    aks holda rasm ochilmaganda foydalanuvchi buni nosozlik deb
         *    o'ylardi va texnik yordamga murojaat qilardi.
         */
        <div className="flex flex-col items-start gap-2 rounded-md bg-surface-muted p-4">
          <ImageOff aria-hidden="true" className="size-6 text-text-muted" />
          <p className="text-sm">{t("snapshots.tierPurgedWhy")}</p>
        </div>
      ) : (
        <SnapshotImage snapshotId={detail.id} />
      )}

      {/* ⛔ IKKI FAKT EMAS, BITTA XULOSA (D-12) — fayl boshidagi izoh. */}
      {verdict === null ? null : <p className="text-sm">{t(verdict)}</p>}

      <div className="flex flex-wrap items-center gap-2">
        {/*
         * ⚠ «Hisobga kirmaydi» — FAKT, ogohlantirish emas (D-16, §10.3),
         *   va u DOIM ombor qatlamidan OLDIN turadi: pul hisobiga
         *   tegishli javob birinchi o'qiladi.
         */}
        {detail.is_billable ? null : (
          <Badge className="gap-1" title={t("snapshots.notBillableWhy")} tone="warning">
            <TriangleAlert aria-hidden="true" className="size-3" />
            {t("snapshots.notBillable")}
          </Badge>
        )}
        {tierKey === undefined ? null : (
          <Badge
            title={tierWhyKey === undefined ? undefined : t(tierWhyKey)}
            tone="muted"
          >
            {t(tierKey)}
          </Badge>
        )}
      </div>

      <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
        <MetaItem
          label={t("snapshots.capturedAt")}
          value={format.dateTime(new Date(detail.captured_at), {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        />
        {methodKey === null ? null : (
          <MetaItem label={t("snapshots.methodLabel")} value={t(methodKey)} />
        )}
        <MetaItem
          label={t("snapshots.size")}
          value={t("snapshots.sizeKb", {
            value: format.number(Math.max(1, Math.round(detail.size_bytes / 1024))),
          })}
        />
        {detail.width === null || detail.height === null ? null : (
          <MetaItem
            label={t("snapshots.dimensions")}
            value={`${detail.width}×${detail.height}`}
          />
        )}
      </dl>

      {/*
       * ⚠ FAQAT QIYMAT MAVJUD BO'LGANDA (§6.6): uchala o'lchov ham
       *   `null` bo'lishi mumkin va u AYNAN BITTA holatni anglatadi —
       *   buzuq JPEG dekodlanmaydi, ya'ni o'lchovni OLIB BO'LMAYDI.
       *   Nol ko'rsatish «o'lchandi va nol chiqdi» degan yolg'on
       *   bo'lardi.
       */}
      <details className="text-xs">
        <summary className="cursor-pointer text-text-muted">
          {t("snapshots.technicalDetails")}
        </summary>
        <dl className="mt-2 flex flex-col gap-1">
          {lightKey === undefined ? null : (
            <MetaItem label={t("snapshots.lightModeLabel")} value={t(lightKey)} />
          )}
          {detail.quality_mean === null ? null : (
            <MetaItem
              label={t("snapshots.qualityMean")}
              mono
              value={detail.quality_mean.toFixed(2)}
            />
          )}
          {detail.quality_stddev === null ? null : (
            <MetaItem
              label={t("snapshots.qualityStddev")}
              mono
              value={detail.quality_stddev.toFixed(2)}
            />
          )}
          {detail.quality_saturation === null ? null : (
            <MetaItem
              label={t("snapshots.qualitySaturation")}
              mono
              value={detail.quality_saturation.toFixed(2)}
            />
          )}
          <MetaItem
            label={t("snapshots.thresholdsVersion")}
            mono
            value={String(detail.quality_thresholds_version)}
          />
          {/* Xom token — FAQAT shu blok ichida, `font-mono` (§10.7). */}
          <MetaItem label={t("snapshots.methodLabel")} mono value={detail.capture_method} />
        </dl>
      </details>
    </div>
  );
}

function MetaItem({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div className="flex items-center gap-1">
      <dt>{label}</dt>
      <dd className={cn("m-0", mono ? "font-mono" : null)}>{value}</dd>
    </div>
  );
}

/**
 * Dalil-kadrning baytlari — SESSIYA TOKENI bilan, proxy orqali.
 *
 * ⚠ Brauzerning O'ZI so'rov yubora olmaydi: marshrut sessiya tokenini
 *   talab qiladi va tasvir elementi sarlavha qo'sha olmaydi. Shuning
 *   uchun baytlar `apiRequest` bilan olinadi va brauzer ichidagi
 *   vaqtinchalik havolaga aylantiriladi — u sahifadan tashqariga
 *   chiqmaydi, ulashilmaydi va dialog yopilganda bekor qilinadi.
 */
function SnapshotImage({ snapshotId }: { snapshotId: string }) {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const marketId = principal?.marketId ?? null;

  const image = useQuery({
    queryKey: snapshotImageKey(marketId ?? "", snapshotId),
    queryFn: async () => {
      const response = await apiRequest(`${SNAPSHOTS_PATH}/${snapshotId}/image`);
      return URL.createObjectURL(await response.blob());
    },
    enabled: marketId !== null,
    gcTime: 0,
    retry: false,
    staleTime: Infinity,
  });

  const source = image.data ?? null;

  /* Vaqtinchalik havola dialog bilan birga o'ladi — u sizib qolmaydi. */
  useEffect(() => {
    if (source === null) return;
    return () => URL.revokeObjectURL(source);
  }, [source]);

  return (
    <div
      className={cn(
        "flex aspect-video items-center justify-center overflow-hidden rounded-md",
        source === null ? "bg-surface-muted" : "bg-text",
      )}
    >
      {image.isPending ? (
        <div aria-busy="true" className="w-full" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="aspect-video w-full" />
        </div>
      ) : null}

      {/*
       * ⛔ DIALOG YIQILMAYDI: rasm ochilmasa ham sifat hukmi, belgilar va
       *    o'lchovlar joyida qoladi — ular ko'pincha adminning haqiqiy
       *    savoliga javob beradi.
       */}
      {image.isError ? (
        <div className="flex flex-col items-center gap-2 p-4">
          <ImageOff aria-hidden="true" className="size-6 text-text-muted" />
          <p className="text-sm text-text-muted">{t("snapshots.imageUnavailable")}</p>
        </div>
      ) : null}

      {source === null ? null : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={t("snapshots.detailDescription")}
          className="size-full object-contain"
          src={source}
        />
      )}
    </div>
  );
}

/** C5…C9 — SABAB + NIMA QILISH KERAK + KIM TUZATADI (§10.5). */
function CaptureFailureBlock({ run }: { run: CaptureRun }) {
  const t = useTranslations();
  const view = captureErrorView(run.error_code);
  const state = captureCellState(run);

  if (view === null) {
    /*
     * ⛔ NOMA'LUM KOD -> UMUMIY XABAR va XOM TAFSILOT KO'RSATILMAYDI
     *    (T-02-99): u ichki tuzilma, yo'l yoki so'rov matnini oshkor
     *    qilishi mumkin.
     */
    return (
      <div className="flex flex-col gap-2 rounded-md bg-surface-muted p-4">
        <p className="text-sm font-semibold">{t(`snapshots.cell.${state}` as "snapshots.cell.ok")}</p>
        <p className="text-sm">{t("errors.generic")}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-md p-4",
        view.tone === "danger"
          ? "bg-danger/10 text-danger-text"
          : "bg-warning/20 text-text",
      )}
    >
      <div>
        <p className="text-xs font-semibold">{t("snapshots.errorCauseLabel")}</p>
        <p className="text-sm">{t(view.causeKey)}</p>
      </div>
      <div>
        <p className="text-xs font-semibold">{t("snapshots.errorFixLabel")}</p>
        <p className="text-sm">{t(view.fixKey)}</p>
      </div>
      {/*
       * ⚠ `actor` — BADGE EMAS, `text-xs text-text-muted` (§10.5): u
       *   sabab va tuzatish bilan bir darajaga chiqmasligi kerak, lekin
       *   yo'qolmasligi ham kerak — «bu meni ishimmi?» savoliga javob.
       */}
      <p className="text-xs text-text-muted">{t(view.actorKey)}</p>
    </div>
  );
}
