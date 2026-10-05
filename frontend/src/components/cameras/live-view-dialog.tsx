"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Video } from "lucide-react";
import { useTranslations } from "next-intl";

import { LivePlayer } from "@/components/cameras/live-player";
import { LiveZoneOverlay } from "@/components/cameras/live-zone-overlay";
import { useFrameImage } from "@/lib/camera-zone-queries";
import { NvrErrorBlock } from "@/components/cameras/nvr-error-block";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import type { Camera } from "@/lib/api-types";
import {
  LIVE_CONNECT_TIMEOUT_MS,
  LIVE_EXPIRY_WARNING_MS,
  LIVE_SESSION_MAX_MS,
  useLiveToken,
} from "@/lib/camera-queries";
import { channelLabel } from "@/components/cameras/camera-row";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * JONLI KO'RISH — DIALOG, MARSHRUT EMAS (CAM-03, SC#6, UI-SPEC §8).
 *
 * Marshrutda «oqim qachon to'xtaydi?» savoli NOANIQ qolardi (orqaga
 * bosish? tab yopish?). Dialogda javob bitta va ko'rinadigan:
 * DIALOG YOPILISHI = OQIM TO'XTASHI.
 *
 * ⚠ L0 MAJBURIY — DIALOG OCHILISHI BILAN OQIM BOSHLANMAYDI VA TOKEN
 *   SO'RALMAYDI. go2rtc oqimni FAQAT birinchi tomoshabin ulanganda
 *   ochadi va har ochilgan oqim NVR ning BITREYT BYUDJETIDAN yeydi.
 *   Dialogni tasodifan ochish NVR sessiyasini ochmasligi kerak. Bitta
 *   qo'shimcha bosish — bu narxning to'liq to'lovi.
 *
 * ⚠ TOKEN — ULANISH CHIPTASI, SESSIYA MUDDATI EMAS (D-08, §8.3).
 *   Bu farq aniqlanmasa dala xatosiga aylanadi:
 *
 *     nginx `auth_request` tokenni ULANISH PAYTIDA tekshiradi.
 *     WebRTC'da signalling BIR MARTA bo'ladi va media UDP orqali
 *     nginx'dan TASHQARIDA oqadi — ya'ni ulanish o'rnatilgach sessiya
 *     tokendan UZOQROQ yashaydi. HLS'da esa HAR SEGMENT nginx'dan
 *     o'tadi — ya'ni oqim 60 soniyada uziladi.
 *
 *   Bir xil UI, ikki xil xulq. Shuning uchun sessiya chegarasini UI
 *   O'ZI belgilaydi va u ikkala transportda ham bir xil ishlaydi.
 *
 *   To'rtta mustaqil sabab:
 *     1. NVR BYUDJETI — nazoratsiz sessiya RTSP oqimini CHEKSIZ ushlab
 *        turardi; avtorizatsiyadan QAT'I NAZAR qattiq chegara kerak.
 *     2. TRANSPORTLAR BIR XIL ISHLAYDI — dala nosozligi transportga
 *        bog'liq bo'lmaydi.
 *     3. AVTORIZATSIYA QAYTA TEKSHIRILADI — har yangilashda server
 *        huquqni va kameraning mavjudligini qaytadan tekshiradi hamda
 *        yangi o'qish izini yozadi; rol o'zgargan sessiya eski ruxsat
 *        ustida ishlab turmaydi.
 *     4. BO'SH BRAUZER TUNAB QOLMAYDI — «Davom ettirish» odamning
 *        aniq harakati.
 *
 * ⚠ YANGILASHDA PLEYER QAYTA MOUNT QILINADI va uning narxi (WebRTC'da
 *   ~0.5 s qora kadr) QABUL QILINADI: u 5 daqiqada bir marta bo'ladi va
 *   foydalanuvchi 30 soniya oldin ogohlantirilgan. «Uzilmasdan
 *   yangilash» ATAYIN RAD ETILDI — eski media sessiyasini saqlab, faqat
 *   serverda huquqni tekshirish «yangilandi» degan YOLG'ON his berardi:
 *   media yo'li aslida ESKI ruxsat ustida ishlab turardi.
 *
 * ⚠ SUBTITR / AUDIO TAVSIF TALAB QILINMAYDI VA BERILMAYDI, va bu
 *   QAROR shu yerda hujjatlashtiriladi (aks holda tekshirgich uni
 *   buzilish deb belgilardi): oqim OVOZSIZ va JONLI video-only.
 *   WCAG 1.2.1/1.2.3/1.2.5 OLDINDAN YOZILGAN mediaga tegishli, 1.2.4
 *   esa jonli AUDIO subtitriga — bu yerda audio umuman so'ralmaydi
 *   (`live-player.tsx::applyPlayerPolicy`). Matn ekvivalenti video
 *   YONIDA: dialog sarlavhasida kamera nomi va kanal raqami turadi.
 *
 * ⚠ NIMA HECH QACHON OCHILMAYDI (§8.7): oqim identifikatori UI'da
 *   ko'rsatilmaydi va nusxa olinmaydi — shuning uchun uning maydon nomi
 *   bu izohda ham yozilmaydi (u qabul mezonining grep naqshi); RTSP
 *   manzili hech qachon ko'rsatilmaydi; jonli ko'rish havolasi URL'ga
 *   chiqarilmaydi va ulashish tugmasi YO'Q. Dialog holati URL'da EMAS:
 *   ulashiladigan havola avtorizatsiya ortidagi oqimga ishora qilardi.
 * =============================================================================
 */

/** Yettita holat (UI-SPEC §8.2 — L0…L6). */
export type LiveStage =
  | "idle" // L0
  | "authorizing" // L1
  | "connecting" // L2
  | "playing" // L3
  | "expiring" // L4
  | "expired" // L5
  | "error"; // L6

/** Sessiya tugashiga qancha qolganda ogohlantiriladi. */
const WARN_AT_MS = LIVE_SESSION_MAX_MS - LIVE_EXPIRY_WARNING_MS;

/**
 * Ichki bosqich — SESSIYA VAQTIDAN mustaqil qism.
 *
 * `expiring` va `expired` bu yerda YO'Q: ular vaqtdan HOSIL bo'ladi va
 * ularni holatga yozish ikkinchi haqiqat manbaini tug'dirardi.
 */
export type LivePhase = "idle" | "authorizing" | "connecting" | "playing" | "error";

/**
 * Ko'rinadigan bosqich — SOF FUNKSIYA (`discoveryStageOf` bilan bir xil
 * sabab: vaqtga bog'langan qarorni testda soatni ushlab turmasdan
 * o'lchash mumkin bo'lishi kerak).
 *
 * ⚠ TARTIB QARORNING O'ZI:
 *   1. `idle` / `authorizing` / `error` — vaqtdan mustaqil.
 *   2. SESSIYA CHEGARASI — avtorizatsiyadan QAT'I NAZAR (T-03-69).
 *   3. Ulanish chegarasi FAQAT `connecting` da: ulanmagan oqim 15
 *      soniyadan keyin xato, lekin ULANGAN oqim uchun bu chegara
 *      qo'llanmaydi.
 *   4. Ogohlantirish — `playing` ning oxirgi 30 soniyasi.
 */
export function liveStageOf(input: {
  phase: LivePhase;
  elapsedMs: number;
}): LiveStage {
  if (input.phase === "idle") return "idle";
  if (input.phase === "authorizing") return "authorizing";
  if (input.phase === "error") return "error";

  if (input.elapsedMs >= LIVE_SESSION_MAX_MS) return "expired";

  if (input.phase === "connecting") {
    return input.elapsedMs >= LIVE_CONNECT_TIMEOUT_MS ? "error" : "connecting";
  }

  return input.elapsedMs >= WARN_AT_MS ? "expiring" : "playing";
}

/** Sessiya tugashiga qolgan soniya (L4 qatori uchun). */
export function secondsLeft(elapsedMs: number): number {
  return Math.max(0, Math.ceil((LIVE_SESSION_MAX_MS - elapsedMs) / 1000));
}

/** Pleyer DOM'da bo'ladigan bosqichlar. */
function playerVisible(stage: LiveStage): boolean {
  return stage === "connecting" || stage === "playing" || stage === "expiring";
}

export function LiveViewDialog({
  camera,
  onOpenChange,
  onRefreshList,
  open,
}: {
  camera: Camera;
  onOpenChange: (open: boolean) => void;
  /** 404 holatida ro'yxatni yangilash (§8.5). */
  onRefreshList?: () => void;
  open: boolean;
}) {
  const t = useTranslations();

  const title = t("cameras.liveTitle", {
    channel: channelLabel(camera.channel_no),
    // D-16: nom DB kontenti — tarjima qilinmaydi.
    name: camera.name,
  });

  /*
   * MATN EKVIVALENTI VIDEO YONIDA (§12.4): kamera nomi va kanal raqami
   * dialogning tavsifida turadi va u `aria-describedby` ga bog'lanadi.
   */
  const label = t("cameras.liveLabel", {
    channel: channelLabel(camera.channel_no),
    name: camera.name,
  });

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Content description={label} sheetOnMobile size="xl" title={title}>
        {/*
         * ⚠ SESSIYA HOLATI SHU BOLADA YASHAYDI VA U DIALOG BILAN BIRGA
         *   O'LADI. `Dialog.Content` yopilganda portaldan chiqariladi,
         *   ya'ni pleyer DARHOL unmount bo'ladi, taymer tozalanadi va
         *   qayta ochilganda holat yana L0 dan boshlanadi.
         *
         *   Muqobil variant — `open` o'zgarganda effektda holatni
         *   tozalash — React Compiler qoidasiga urilardi
         *   (`react-hooks/set-state-in-effect`) va undan muhimi: u
         *   «yopildi, lekin oqim hali tirik» oynasini ochiq
         *   qoldirardi. Montaj chegarasi bu kafolatni STRUKTURAVIY
         *   qiladi.
         */}
        <LiveSession camera={camera} onRefreshList={onRefreshList} />
      </Dialog.Content>
    </Dialog.Root>
  );
}

function LiveSession({
  camera,
  onRefreshList,
}: {
  camera: Camera;
  onRefreshList?: () => void;
}) {
  const t = useTranslations();
  const liveToken = useLiveToken();

  const [phase, setPhase] = useState<LivePhase>("idle");
  const [url, setUrl] = useState<string | null>(null);
  const [transport, setTransport] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<"not-found" | "forbidden" | "network" | "stream">(
    "stream",
  );
  const [startedAt, setStartedAt] = useState<number | null>(null);
  /** Har yangilash pleyerni QAYTA MOUNT qiladi (§8.3). */
  const [sessionSeq, setSessionSeq] = useState(0);

  const [now, setNow] = useState(() => Date.now());
  const frameRef = useRef<HTMLDivElement | null>(null);

  /*
   * Soat — TASHQI TIZIM: holat faqat interval CALLBACK ida yangilanadi
   * (`react-hooks/set-state-in-effect`). Sessiya boshlanmagan bo'lsa
   * taymer umuman ishga tushmaydi.
   */
  useEffect(() => {
    if (startedAt === null) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [startedAt]);

  const elapsedMs = startedAt === null ? 0 : now - startedAt;
  const stage = liveStageOf({ elapsedMs, phase });

  const handlePlayerReady = useCallback(() => setPhase("playing"), []);
  const handlePlayerError = useCallback(() => {
    setErrorKind("stream");
    setPhase("error");
  }, []);

  async function startSession(): Promise<void> {
    setPhase("authorizing");
    setTransport(null);
    try {
      const ticket = await liveToken.mutateAsync({ cameraId: camera.id });
      setUrl(ticket.url);
      setStartedAt(Date.now());
      setNow(Date.now());
      setSessionSeq((value) => value + 1);
      setPhase("connecting");
    } catch (cause) {
      setErrorKind(errorKindOf(cause));
      setPhase("error");
      setStartedAt(null);
    }
  }

  return (
    <>
      {/*
       * ⚠ RAMKA FONI (§2.3): `idle` da och — u yerda oqim YO'Q va
       *   qora to'rtburchak «buzilgan» degan yolg'on signal berardi.
       *   Qolgan holatlarda qora: oq letterbox tasvir chegarasini
       *   yo'qotadi va qorong'i bozor kadrida ko'zni qamashtiradi.
       *
       * ⚠ `tabIndex={-1}` — ramka fokus TARTIBIGA kirmaydi, lekin
       *   DASTURIY fokusni qabul qiladi. Bu kerak: `[Davom ettirish]`
       *   bosilganda o'sha tugma DOM'dan chiqadi va fokus `body` ga
       *   tushib, foydalanuvchi dialogdan «tashqarida» qolardi.
       */}
      <div
        className={cn(
          /*
           * ⚠ `max-h-[70vh]` — oyna kengaygach (261005) 16:9 kadr past
           *   ekranlarda dialogning `max-h-[85vh]` idan oshib ketardi
           *   va sarlavha bilan pastdagi boshqaruvlar qirqilardi.
           *   Chegara urilganda kadr `object-contain` bilan o'z
           *   nisbatini saqlagan holda kichrayadi — cho'zilmaydi.
           */
          "relative flex aspect-video max-h-[70vh] items-center justify-center overflow-hidden rounded-md",
          stage === "idle" ? "bg-surface-muted" : "bg-text",
        )}
        ref={frameRef}
        tabIndex={-1}
      >
        {stage === "idle" ? (
          /*
           * ⚠ PLASHKA — ortda endi KADR turadi (261005). Usiz ikonka va
           *   matn fotosurat ustida o'qilmasdi.
           */
          <div className="relative z-20 flex flex-col items-center gap-3 rounded-lg bg-black/70 px-6 py-5">
            <Video aria-hidden="true" className="size-8 text-text-muted" />
            <p className="text-sm text-text-muted">{t("cameras.liveIdle")}</p>
            <Button onClick={() => void startSession()} size="lg" variant="secondary">
              {t("cameras.view")}
            </Button>
          </div>
        ) : null}

        {stage === "authorizing" ? (
          <div className="flex w-full flex-col gap-2 p-4" role="status">
            <span className="sr-only">{t("cameras.liveAuthorizing")}</span>
            <Skeleton className="h-24" />
          </div>
        ) : null}

        {stage === "connecting" ? (
          <p className="text-sm text-bg" role="status">
            {t("cameras.liveConnecting")}
          </p>
        ) : null}

        {stage === "expired" ? (
          /*
           * ⚠ XATO RANGI ISHLATILMAYDI — bu NORMAL tugash, nosozlik
           *   emas. Qizil ramka adminni mavjud bo'lmagan muammoni
           *   qidirishga yuborardi.
           */
          <div
            className="relative z-20 flex flex-col items-center gap-3 rounded-lg bg-black/70 px-6 py-5"
            role="status"
          >
            <p className="text-sm text-bg">{t("cameras.liveExpired")}</p>
            <Button onClick={() => void startSession()} size="lg" variant="secondary">
              {t("cameras.resume")}
            </Button>
          </div>
        ) : null}

        {/*
         * ⛔ SAQLANGAN KADR — oqim ko'rinmayotgan HAR holatda (261005).
         *    Sabab `FrameBackdrop` docstringida: Karmanada jonli oqim
         *    ulanmaydi va raqamlar faqat shu kadr ustida ko'rinadi.
         */}
        {!playerVisible(stage) && camera.last_snapshot_id !== null ? (
          <FrameBackdrop snapshotId={camera.last_snapshot_id} />
        ) : null}

        {playerVisible(stage) && url !== null ? (
          /*
           * ⚠ `key` — SESSIYA RAQAMI. Yangi chipta olinganda pleyer
           *   QAYTA MOUNT bo'lishi SHART (§8.3): eski media yo'lini
           *   saqlab qolib faqat serverda huquqni tekshirish
           *   «yangilandi» degan YOLG'ON his berardi.
           *
           * ⚠ Callback'lar BARQAROR (`useCallback`): yangi havola har
           *   renderda pleyer ichidagi effektni qayta ishga tushirardi
           *   va WebRTC'da bu har safar YANGI RTSP sessiyasi degani.
           */
          <LivePlayer
            className="absolute inset-0 block size-full"
            key={sessionSeq}
            onError={handlePlayerError}
            onReady={handlePlayerReady}
            onTransport={setTransport}
            url={url}
          />
        ) : null}

        {/*
         * ⛔⛔ RASTA RAQAMLARI KADR USTIDA (261005, foydalanuvchi talabi).
         *
         *     Kadrda o'nlab rasta ko'rinadi va hammasi bir-biriga
         *     o'xshaydi. Nizoda «bu qaysi rasta?» degan savolga kadrning
         *     O'ZIDAN javob berib bo'lmasdi — operator zona muharririni
         *     ochib solishtirishi kerak edi.
         *
         * ⚠ FAQAT OQIM KO'RINAYOTGANDA: qoplama kutish, xato va
         *   muddati o'tgan holatlar ustida chizilsa, u yerda tasvir
         *   YO'Q va raqamlar bo'sh qora ramkada osilib turardi.
         */}
        {/*
         * ⚠ QOPLAMA IKKALA MANBA USTIDA HAM: jonli oqim ustida ham,
         *   saqlangan kadr ustida ham. `connecting` va `authorizing`
         *   CHIQARILGAN — u yerda tasvir hali yo'q va raqamlar bo'sh
         *   ramkada osilib turardi.
         */}
        {stage === "playing" ||
        stage === "expiring" ||
        (!playerVisible(stage) && camera.last_snapshot_id !== null) ? (
          <LiveZoneOverlay cameraId={camera.id} enabled />
        ) : null}

        {stage === "playing" || stage === "expiring" ? (
          /*
           * TRANSPORT BADGE'I — DALA DIAGNOSTIKASI (§8.4). «Tasvir
           * kechikyapti» shikoyati kelganda birinchi savol shu, va
           * uni ekranda ko'rsatish telefon orqali diagnostikani bir
           * bosqichga qisqartiradi. Aksent rangda EMAS: bu holat
           * ko'rsatkichi, harakat emas.
           */
          <Badge
            aria-label={t("cameras.liveTransport", {
              transport: transport ?? "—",
            })}
            className="absolute top-2 right-2 z-10"
            tone="muted"
          >
            {transport ?? "—"}
          </Badge>
        ) : null}
      </div>

      {stage === "expiring" ? (
          /*
           * ⚠ MODAL EMAS VA VIDEONI TO'SMAYDI: video davom etadi,
           *   qator ramka OSTIDA turadi. Ogohlantirishni videoning
           *   ustiga qo'yish foydalanuvchini aynan kerakli lahzada
           *   ko'rishdan mahrum qilardi.
           */
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-surface-muted px-3 py-2">
            <p className="text-sm" role="status">
              {t("cameras.liveExpiring", { seconds: secondsLeft(elapsedMs) })}
            </p>
            <Button
              onClick={() => {
                void startSession();
                frameRef.current?.focus();
              }}
              size="sm"
              variant="secondary"
            >
              {t("cameras.resume")}
            </Button>
          </div>
        ) : null}

      {stage === "error" ? (
        <LiveError
          kind={errorKind}
          onRefreshList={onRefreshList}
          onRetry={() => void startSession()}
        />
      ) : null}
    </>
  );
}

/**
 * Token yo'lidagi nosozlik turlari (§8.5).
 *
 * ⚠ `403` BO'LMASLIGI KERAK — tugma huquq bilan darvozalangan — lekin
 *   ROL O'ZGARGAN sessiyada bo'ladi va shuning uchun alohida shox oladi.
 */
function errorKindOf(cause: unknown): "not-found" | "forbidden" | "network" | "stream" {
  if (cause instanceof ApiError) {
    if (cause.status === 404) return "not-found";
    if (cause.status === 403) return "forbidden";
    return "stream";
  }
  return "network";
}

function LiveError({
  kind,
  onRefreshList,
  onRetry,
}: {
  kind: "not-found" | "forbidden" | "network" | "stream";
  onRefreshList?: () => void;
  onRetry: () => void;
}) {
  const t = useTranslations();

  /*
   * ⚠ `[Qayta urinish]` BU YERDA XAVFSIZ va §4.4 qulfi bu yerga
   *   QO'LLANMAYDI: jonli ko'rish NVR hisobiga autentifikatsiya
   *   urinishini YUBORMAYDI — u go2rtc'ning allaqachon ochiq
   *   sessiyasidan foydalanadi. Qulfni bu yerga ham yoyish adminni
   *   hech qanday xavf yo'q joyda to'xtatib qo'yardi.
   */
  if (kind === "stream") {
    return (
      <NvrErrorBlock
        code="nvr_stream_limit"
        detail={null}
        onRetry={onRetry}
      />
    );
  }

  const message =
    kind === "not-found"
      ? t("cameras.liveNotFound")
      : kind === "forbidden"
        ? t("errors.forbidden")
        : t("errors.network");

  return (
    <div
      className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
      role="alert"
    >
      <p className="text-sm">{message}</p>
      {kind === "not-found" && onRefreshList !== undefined ? (
        <Button onClick={onRefreshList} size="sm" variant="secondary">
          {t("cameras.refreshList")}
        </Button>
      ) : null}
      {kind === "network" ? (
        <Button onClick={onRetry} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      ) : null}
    </div>
  );
}

/**
 * SAQLANGAN KADR — jonli oqim ko'rinmayotganda oynaning foni.
 *
 * =============================================================================
 * ⛔⛔ NEGA QO'SHILDI (261005, jonli serverda o'lchandi): rasta raqamlari
 *     dastlab FAQAT oqim o'ynayotganda chizilardi. Karmanada esa oqim
 *     umuman ulanmaydi — NVR bir vaqtda ochiladigan oqimlar chegarasiga
 *     yetgan va 16 katakning HAMMASI saqlangan kadrga tushadi. Ya'ni
 *     buyurtmachi so'ragan raqamlar amalda HECH QACHON ko'rinmasdi.
 *
 *     Nizoda dalil baribir SAQLANGAN KADR bo'ladi, jonli oqim emas —
 *     raqam aynan dalil ustida turishi kerak.
 *
 * ⚠ KADR QORAYTIRILMAYDI: ustidagi matn o'z plashkasini oladi
 *   (`live-view-dialog` dagi `bg-black/70` konteynerlari). Butun kadrni
 *   50% qoraytirish matnni o'qiladigan qilardi-yu, dalilning O'ZINI
 *   loyqalantirardi — ya'ni muammoni hal qilib, maqsadni yo'qotardi.
 */
function FrameBackdrop({ snapshotId }: { snapshotId: string }) {
  const { href } = useFrameImage(snapshotId);
  if (href === null) return null;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      alt=""
      className="absolute inset-0 size-full object-contain"
      src={href}
    />
  );
}

