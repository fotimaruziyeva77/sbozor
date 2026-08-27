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
  LIVE_SESSION_MAX_MS,
  useCamerasQuery,
  useLiveToken,
} from "@/lib/camera-queries";

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
 * ⚠ HAR KATAK O'Z CHIPTASINI OLADI va O'ZI YANGILAB TURADI: jonli
 *   sessiya 5 daqiqada tugaydi (`LIVE_SESSION_MAX_MS`), shuning uchun
 *   katak tugashdan biroz oldin chiptani QAYTA oladi va pleyerni qayta
 *   mount qiladi — devor o'chib qolmaydi. Katak DOM'dan chiqarilganda
 *   (devordan chiqish, kamera oflayn) `LivePlayer` unmount bo'lib oqimni
 *   yopadi — qo'shimcha tozalash shart emas.
 * =============================================================================
 */

/** Sessiya tugashidan shuncha oldin chipta qayta olinadi. */
const REFRESH_BEFORE_EXPIRY_MS = 10_000;

/** Katak start'lari orasidagi siljish — NVR'larга bir vaqtda yopirilmasin. */
const TILE_STAGGER_MS = 300;

export function CameraWall() {
  const t = useTranslations();

  // Butun bozor, faqat onlayn — devor qurilma bo'yicha ajratmaydi.
  const cameras = useCamerasQuery({ ...EMPTY_CAMERA_FILTERS, status: "online" });
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
  const [status, setStatus] = useState<"connecting" | "playing" | "failed">(
    "connecting",
  );

  // Mutatsiya obyekti har renderda yangi — `mutateAsync` ni ref'da
  // saqlaймiz, aks holda start effekti har renderda qayta ishlardi.
  const fetchToken = useRef(liveToken.mutateAsync);
  useEffect(() => {
    fetchToken.current = liveToken.mutateAsync;
  });

  const start = useCallback(async () => {
    try {
      const ticket = await fetchToken.current(camera.id);
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

  // Muddati tugashidan oldin chiptani yangilaydi.
  useEffect(() => {
    if (url === null) return;
    const timer = setTimeout(
      () => void start(),
      LIVE_SESSION_MAX_MS - REFRESH_BEFORE_EXPIRY_MS,
    );
    return () => clearTimeout(timer);
  }, [url, seq, start]);

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
      {url !== null && status !== "failed" ? (
        <LivePlayer
          className="absolute inset-0 block size-full"
          key={seq}
          onError={handleError}
          onReady={handleReady}
          onTransport={noop}
          url={url}
        />
      ) : null}

      {/* Holat qoplamasi — oqim kelgunча yoki xatoda */}
      {status !== "playing" ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-surface-muted">
          {status === "failed" ? (
            <>
              <WifiOff aria-hidden="true" className="size-6 text-text-muted" />
              <span className="text-xs text-text-muted">
                {t("cameras.wallTileFailed")}
              </span>
            </>
          ) : (
            <span className="text-xs text-text-muted" role="status">
              {t("cameras.wallReconnecting")}
            </span>
          )}
        </div>
      ) : null}

      {/* Nom + kanal — pastki gradient ustida, doim ko'rinadi */}
      <span className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-black/70 to-transparent px-2 py-1.5">
        <span className="truncate text-xs font-medium text-white">
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
