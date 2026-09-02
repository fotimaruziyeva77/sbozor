"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Maximize2, WifiOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { channelLabel } from "@/components/cameras/camera-row";
import { LivePlayer } from "@/components/cameras/live-player";
import { LiveViewDialog } from "@/components/cameras/live-view-dialog";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { Camera } from "@/lib/api-types";
import {
  EMPTY_CAMERA_FILTERS,
  useCamerasQuery,
  useLiveToken,
} from "@/lib/camera-queries";
import { useFrameImageHref } from "@/lib/camera-zone-queries";

/*
 * =============================================================================
 * KAMERALAR DEVORI (mozaika) — «Hik-Connect kabi hammasini bitta ekranda».
 *
 * NEGA ALOHIDA REJIM, RO'YXAT O'RNINI BOSMAYDI (opt-in, `page.tsx` dagi
 * toggle): devor har onlayn kamera uchun JONLI oqim ochadi. Jonli oqim
 * NVR ning bitreyt byudjetidan yeydi (`live-view-dialog.tsx` L0 izohi) —
 * ya'ni ro'yxatdagi «bitta-bitta ochish» ATAYIN edi. Devor esa bir
 * vaqtda N oqim degani: LAN'da (yakka kameralar) bemalol, tor uplink'li
 * bozorda esa qimmat. Shuning uchun u alohida, ongli tanlov ostida
 * turadi va ro'yxat standart bo'lib qoladi.
 *
 * ⚠ QURILMA BO'YICHA AJRATILMAYDI. Ro'yxat bitta NVR/qurilmaga
 *   doiralangan (`nvr_id` filtri), devor esa BUTUN bozorning barcha
 *   onlayn kameralarini ko'rsatadi — aynan shu «bittalab tanlash»
 *   muammosini yo'q qiladi.
 *
 * ⚠ KATAK 10 SONIYA JONLI, KEYIN OXIRGI KADR (260829). Chipta
 *   YANGILANMAYDI va bu ataylab: uzluksiz 16 oqim bozorning butun
 *   uplink'ini (o'lchangan 10.7 Mbit/s) shu sahifaga bog'lab qo'yardi
 *   va sahifa ochiq qolgan har daqiqa NVR bitreyt byudjetidan yerdi.
 *   O'n soniya harakatni ko'rsatishga yetadi, undan keyin kadr
 *   ma'lumotning o'zini beradi.
 *
 * ⚠ CHEGARA IKKI QATLAMDA: brauzer pleyerni unmount qiladi, server esa
 *   oqimga QISQA muddat beradi (`PREVIEW_DURATION_S`) va agent uni o'zi
 *   o'chiradi. Tab yopilsa yoki JS to'xtasa ham oqim yashab qolmaydi.
 * =============================================================================
 */

/** Katak start'lari orasidagi siljish — NVR'larга bir vaqtda yopirilmasin. */
const TILE_STAGGER_MS = 300;

/**
 * Katakcha shuncha vaqt JONLI turadi, keyin oxirgi kadrga qaytadi.
 *
 * ⛔ Uzunroq qilish uplink narxini oshiradi (sabab `LiveTile` ichidagi
 *   izohda), qisqaroq qilish esa harakatni ko'rsatishga ulgurmaydi:
 *   WebRTC ulanishining o'zi ~1-2 soniya oladi.
 */
const LIVE_PREVIEW_MS = 10_000;

/**
 * Ulanish shuncha kutiladi, keyin katakcha oxirgi kadrga o'tadi.
 *
 * Oyna 16 katakchaning eng sekiniga mo'ljallangan: siljish (300 ms ×
 * 16 ≈ 5 s) + agentda ffmpeg ko'tarilishi (~3 s) + WebRTC qo'l
 * berishi. Qisqaroq qilish sekin obyektda jonli tasvirni umuman
 * ko'rsatmasdi.
 */
const CONNECT_TIMEOUT_MS = 25_000;

export function CameraWall() {
  const t = useTranslations();

  /*
   * ⛔ HOLAT BO'YICHA FILTRLANMAYDI (260829, panelda o'lchandi).
   *
   *   Ilgari devor faqat `status: "online"` kameralarni so'rardi.
   *   Agent to'xtagan zahoti hamma kamera «ulanmagan» bo'ladi va
   *   devor BUTUNLAY BO'SH qolardi — «Onlayn kamera yo'q». Holbuki
   *   aynan o'sha daqiqada operator uchun eng qimmatli narsa
   *   OXIRGI KADR: rastada mol bormi, sotuvchi turibdimi.
   *
   *   Endi hamma kamera chiziladi. Jonli oqim ochilmasa katakcha
   *   oxirgi kadrni va «jonli emas» belgisini ko'rsatadi.
   */
  const cameras = useCamerasQuery(EMPTY_CAMERA_FILTERS);
  const [expanded, setExpanded] = useState<Camera | null>(null);

  const items = cameras.data?.items ?? [];

  if (cameras.isPending) {
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton className="aspect-video" key={index} />
        ))}
      </div>
    );
  }

  if (cameras.isError) {
    return (
      <div
        className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
        role="alert"
      >
        <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
        <p className="text-sm">{t("errors.loadFailedBody")}</p>
        <Button onClick={() => void cameras.refetch()} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        description={t("cameras.wallEmptyHint")}
        title={t("cameras.wallEmpty")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-text-muted">
        {t("cameras.wallHint", { count: items.length })}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {items.map((camera, index) => (
          <LiveTile
            camera={camera}
            key={camera.id}
            onExpand={() => setExpanded(camera)}
            startDelayMs={index * TILE_STAGGER_MS}
          />
        ))}
      </div>

      {/*
       * Kattalashtirish — MAVJUD dialogni qayta ishlatadi: to'liq jonli
       * sessiya (ijara, transport belgisi, «Davom ettirish»). Dialog
       * yopilganda devor katagi joyida jonli qolaveradi.
       */}
      {expanded !== null ? (
        <LiveViewDialog
          camera={expanded}
          onOpenChange={(next) => {
            if (!next) setExpanded(null);
          }}
          open
        />
      ) : null}
    </div>
  );
}

function LiveTile({
  camera,
  onExpand,
  startDelayMs,
}: {
  camera: Camera;
  onExpand: () => void;
  startDelayMs: number;
}) {
  const t = useTranslations();
  const liveToken = useLiveToken();

  const [url, setUrl] = useState<string | null>(null);
  const [seq, setSeq] = useState(0);
  const [status, setStatus] = useState<
    "connecting" | "playing" | "failed" | "frame"
  >("connecting");

  // Mutatsiya obyekti har renderda yangi — `mutateAsync` ni ref'da
  // saqlaймiz, aks holda start effekti har renderda qayta ishlardi.
  const fetchToken = useRef(liveToken.mutateAsync);
  useEffect(() => {
    fetchToken.current = liveToken.mutateAsync;
  });

  const start = useCallback(async () => {
    try {
      // `preview: true` — server oqimga QISQA muddat beradi
      // (`PREVIEW_DURATION_S`): katakcha 10 soniyadan keyin oxirgi
      // kadrga qaytadi va 16 ta oqim uplink'da turib qolmaydi.
      const ticket = await fetchToken.current({
        cameraId: camera.id,
        preview: true,
      });
      setUrl(ticket.url);
      setSeq((value) => value + 1);
      setStatus("connecting");
    } catch {
      setStatus("failed");
    }
  }, [camera.id]);

  // Boshlanishi — siljish bilan (thundering herd bo'lmasin).
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      if (!cancelled) void start();
    }, startDelayMs);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [start, startDelayMs]);

  /*
   * ⛔⛔ O'N SONIYADAN KEYIN OQIM TO'XTAYDI (260829, operator so'rovi).
   *
   *     Devor 16 katakchani BIR VAQTDA ochadi. Ular uzluksiz oqsa,
   *     bozorning butun uplink'i (o'lchangan 10.7 Mbit/s) shu devorga
   *     ketardi va sahifa ochiq qolgan har daqiqa NVR bitreyt
   *     byudjetidan yerdi — ya'ni «hammasini bir ekranda» qulayligi
   *     jadval slotining narxiga tushardi (4-prinsip).
   *
   *     Endi katakcha 10 soniya JONLI ko'rsatadi — harakat, odam,
   *     mashina ko'rinadi — keyin OXIRGI KADRga qaytadi. Kadr esa
   *     baribir yangilanib turadi (jadval bo'yicha soatiga bir marta).
   *
   * ⚠ SERVER TOMONI HAM QISQA: oqim `PREVIEW_DURATION_S` bilan
   *   ochiladi va agent uni O'ZI o'chiradi. Brauzerga ishonilmaydi —
   *   tab yopilsa yoki JS to'xtasa ham oqim yashab qolmaydi.
   */
  useEffect(() => {
    if (url === null || status !== "playing") return;
    const timer = setTimeout(() => setStatus("frame"), LIVE_PREVIEW_MS);
    return () => clearTimeout(timer);
  }, [url, seq, status]);

  /*
   * ⛔ ULANISH CHEKSIZ KUTILMAYDI (260829, devorda o'lchandi).
   *
   *   16 katakcha bir vaqtda ochilganda ba'zilariga oqim yetib
   *   kelmaydi: agentda ffmpeg navbati, uplink cho'qqisi, MediaMTX
   *   yo'lining kechikishi. `LivePlayer` bunday holatda `onError` ham,
   *   `onReady` ham chaqirmasligi mumkin — katakcha «Qayta
   *   ulanmoqda…» yozuvi bilan ABADIY kulrang qolardi.
   *
   *   Kutish tugagach katakcha OXIRGI KADRga o'tadi: operator
   *   ma'lumotsiz qolmaydi va «jonli emas» belgisi sababni aytadi.
   */
  useEffect(() => {
    if (status !== "connecting") return;
    const timer = setTimeout(() => setStatus("failed"), CONNECT_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [status, seq]);

  const handleReady = useCallback(() => setStatus("playing"), []);
  const handleError = useCallback(() => setStatus("failed"), []);
  const noop = useCallback(() => {}, []);

  const label = t("cameras.liveLabel", {
    channel: channelLabel(camera.channel_no),
    name: camera.name,
  });

  return (
    <button
      aria-label={label}
      className="group relative aspect-video overflow-hidden rounded-md bg-text text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      onClick={onExpand}
      type="button"
    >
      {/*
        * ⚠ `frame` HOLATIDA PLEYER DOM'DAN CHIQADI, yashirilmaydi:
        *   yashirilgan `<video>` oqimni O'QIYVERADI va butun tejash
        *   ma'nosiz bo'lardi. Unmount esa WebRTC ulanishini yopadi.
        */}
      {url !== null && (status === "connecting" || status === "playing") ? (
        <LivePlayer
          className="absolute inset-0 block size-full"
          key={seq}
          onError={handleError}
          onReady={handleReady}
          onTransport={noop}
          url={url}
        />
      ) : null}

      {/*
        * Jonli oyna tugagach — oxirgi kadr.
        *
        * ⛔ XATODA HAM KADR CHIZILADI (260829). Ilgari oqim ochilmasa
        *   katakcha «ulanmadi» degan bo'sh kulrang maydon bo'lardi —
        *   holbuki oxirgi kadr QO'LDA turadi va u operatorga jonli
        *   videodan ko'ra ko'proq narsa aytadi (rastada mol bormi,
        *   sotuvchi turibdimi). Agent oflayn bo'lgan obyektda butun
        *   devor bo'sh ko'rinardi.
        *
        * ⚠ XATO YASHIRILMAYDI: kadr ustida `WifiOff` belgisi qoladi,
        *   ya'ni «bu jonli emas» degani ko'rinib turadi.
        */}
      {status === "frame" || status === "failed" ? (
        <FrameImage snapshotId={camera.last_snapshot_id} />
      ) : null}

      {status === "failed" ? (
        <span
          className="absolute right-1.5 top-1.5 rounded bg-black/60 p-1"
          title={t("cameras.wallTileFailed")}
        >
          <WifiOff aria-hidden="true" className="size-3.5 text-white" />
          <span className="sr-only">{t("cameras.wallTileFailed")}</span>
        </span>
      ) : null}

      {/* Holat qoplamasi — faqat oqim kelguncha */}
      {status === "connecting" ? (
        <div className="absolute inset-0 flex items-center justify-center bg-surface-muted">
          <span className="text-xs text-text-muted" role="status">
            {t("cameras.wallReconnecting")}
          </span>
        </div>
      ) : null}

      {/* Nom + kanal — pastki gradient ustida, doim ko'rinadi */}
      <span className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-black/70 to-transparent px-2 py-1.5">
        {/*
          * ⚠ `font-medium` EMAS (G-motion-7(e) darvozasi): qora
          *   gradient ustidagi oq matn baribir yetarli kontrastda va
          *   qalinlik byudjeti bu yerda ma'no bermaydi.
          */}
        <span className="truncate text-xs text-white">
          {camera.name}
        </span>
        <Maximize2
          aria-hidden="true"
          className="size-3.5 shrink-0 text-white/70 opacity-0 transition-opacity group-hover:opacity-100"
        />
      </span>
    </button>
  );
}

function FrameImage({ snapshotId }: { snapshotId: string | null }) {
  /*
   * OXIRGI KADR — jonli oyna tugagach katakchada shu qoladi.
   *
   * ⚠ RASM SESSIYA TOKENI BILAN OLINADI va brauzer ichidagi
   *   vaqtinchalik havolaga aylanadi (`useFrameImageHref`): `<img src>`
   *   sarlavha qo'sha olmaydi, ya'ni to'g'ridan-to'g'ri URL ishlamasdi
   *   va kadr avtorizatsiyasiz ochilardi.
   *
   * ⚠ AVTOMATIK YANGILANMAYDI: kadr jadval bo'yicha soatiga bir marta
   *   keladi, ya'ni tez-tez so'rash faqat trafik sarflardi.
   */
  const t = useTranslations();
  const href = useFrameImageHref(snapshotId);

  if (href === null) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-surface-muted">
        <span className="text-xs text-text-muted" role="status">
          {snapshotId === null
            ? t("cameras.wallNoFrame")
            : t("cameras.wallReconnecting")}
        </span>
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      alt=""
      className="absolute inset-0 block size-full object-cover"
      src={href}
    />
  );
}
