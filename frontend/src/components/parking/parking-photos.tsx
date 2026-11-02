"use client";

import { useState } from "react";
import { ImageOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { useSeenOnce } from "@/components/edge-agents/edge-frame";
import {
  isPaymentMethod,
  recentWithPhotos,
  sessionStatus,
} from "@/components/parking/parking-data";
import type { SessionStatus } from "@/components/parking/parking-data";
import { PlateBadge } from "@/components/parking/plate-badge";
import { useParkingFormat } from "@/components/parking/use-parking-format";
import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { EdgeParkingReport, EdgeParkingReportSession } from "@/lib/api-types";
import { useEdgeFileHref } from "@/lib/edge-site-queries";

/*
 * =============================================================================
 * MASHINA SURATLARI — kirish kamerasining kadrlari (261102).
 *
 * ⛔ HAR KADR OCHILISHI SERVERDA AUDITGA YOZILADI (`edge_frame_view`):
 *    galereya kadrni faqat karta KO'RINISHGA KIRGANDA so'raydi
 *    (`useSeenOnce`) va katta ko'rinish AYNI obyekt havolasini ishlatadi —
 *    ikkinchi so'rov ham, ikkinchi audit yozuvi ham yo'q.
 *
 * ⛔ Galereya kichik (8 ta): telefon internetida har kadr ~100–400 KB.
 *    To'liq ro'yxat — jurnalda, u yerda kadr faqat BOSILGANDA ochiladi.
 * =============================================================================
 */

const GALLERY_SIZE = 8;

const STATUS_TONE: Record<SessionStatus, BadgeTone> = {
  open: "accent",
  paid: "success",
  online: "success",
  free: "neutral",
  exempt: "neutral",
  manual: "warning",
  other: "muted",
};

/** Holat yorlig'i — rang ikkinchi kanal, matn har doim bor. */
export function StatusBadge({ session }: { session: EdgeParkingReportSession }) {
  const t = useTranslations("parkingReport");
  const status = sessionStatus(session);
  const method =
    (status === "paid" || status === "manual") && isPaymentMethod(session.method)
      ? ` · ${t(`method.${session.method}`)}`
      : "";
  return (
    <Badge tone={STATUS_TONE[status]}>
      {t(`status.${status}`)}
      {method}
    </Badge>
  );
}

export function GalleryCard({
  data,
  siteId,
}: {
  data: EdgeParkingReport;
  siteId: string;
}) {
  const t = useTranslations("parkingReport");
  const shots = recentWithPhotos(data.sessions, GALLERY_SIZE);

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("gallery.title")}</h2>
        <p className="dir-tile-sub">{t("gallery.sub")}</p>
      </CardHeader>
      <CardContent>
        {shots.length === 0 ? (
          <EmptyState description={t("gallery.emptyHint")} title={t("gallery.empty")} />
        ) : (
          <ul className="park-gallery">
            {shots.map((session) => (
              <ShotCard key={session.session_id} session={session} siteId={siteId} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function ShotCard({
  siteId,
  session,
}: {
  siteId: string;
  session: EdgeParkingReportSession;
}) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const [ref, seen] = useSeenOnce<HTMLDivElement>();
  const image = useEdgeFileHref(siteId, session.entry_file_id, seen);
  const [open, setOpen] = useState(false);
  const plate = session.plate ?? t("noPlate");

  return (
    <li className="park-shot">
      <div className="park-shot-frame" ref={ref}>
        {image.href !== null ? (
          <button
            aria-label={t("gallery.open", { plate })}
            className="park-shot-open"
            onClick={() => setOpen(true)}
            type="button"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt={t("gallery.alt", { plate })} src={image.href} />
          </button>
        ) : image.isError ? (
          <span className="park-shot-missing">
            <ImageOff aria-hidden="true" className="size-5" />
            <span className="text-xs">{t("gallery.unavailable")}</span>
          </span>
        ) : (
          <Skeleton className="park-shot-skeleton" />
        )}
        <PlateBadge className="park-shot-plate" plate={session.plate} size="sm" />
        {session.entered_at === null ? null : (
          <span className="park-shot-time">{fmt.time(session.entered_at)}</span>
        )}
      </div>

      <div className="park-shot-body">
        <StatusBadge session={session} />
        <SessionTimes session={session} />
      </div>

      {image.href === null ? null : (
        <SessionDialog href={image.href} onOpenChange={setOpen} open={open} session={session} />
      )}
    </li>
  );
}

/** «08:14 → 09:02 · 48 daq · 4 000 so'm» — ma'lum bo'lmagan qism yozilmaydi. */
function SessionTimes({ session }: { session: EdgeParkingReportSession }) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const facts = [
    session.duration_minutes === null ? null : fmt.duration(session.duration_minutes),
    session.amount_soum > 0 ? fmt.soum(session.amount_soum) : null,
  ].filter((fact): fact is string => fact !== null);

  return (
    <>
      <p className="park-shot-line">
        {session.entered_at === null ? t("unknown") : fmt.time(session.entered_at)}
        {" → "}
        {session.exited_at === null ? t("status.open") : fmt.time(session.exited_at)}
      </p>
      {facts.length === 0 ? null : <p className="park-shot-line">{facts.join(" · ")}</p>}
    </>
  );
}

/**
 * Seans oynasi: katta kadr + tafsilotlar. `href` — chaqiruvchi allaqachon
 * olgan obyekt havolasi (`null` — hali yuklanmoqda), `failed` — kadr ochilmadi.
 */
export function SessionDialog({
  session,
  href,
  failed = false,
  open,
  onOpenChange,
}: {
  session: EdgeParkingReportSession;
  href: string | null;
  failed?: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("parkingReport");
  const tf = useTranslations("edgeAgents.frame");
  const fmt = useParkingFormat();
  const plate = session.plate ?? t("noPlate");
  /* Chiqishda ro'yxatga olingan seansning kadri — chiqish kamerasidan. */
  const title = t(session.opened_at_exit ? "dialog.titleExit" : "dialog.title", { plate });

  const stamp = (iso: string | null): string =>
    iso === null ? t("unknown") : `${fmt.day(iso)} · ${fmt.time(iso)}`;

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Content description={tf("description")} size="xl" title={title}>
        <div className="park-dialog">
          <div className="park-dialog-frame">
            {href !== null ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img alt={title} src={href} />
            ) : failed ? (
              <span className="park-shot-missing">
                <ImageOff aria-hidden="true" className="size-5" />
                <span className="text-sm">{t("gallery.unavailable")}</span>
              </span>
            ) : (
              <Skeleton className="park-shot-skeleton" />
            )}
          </div>
          <dl className="park-dialog-facts">
            <div>
              <dt>{t("journal.colPlate")}</dt>
              <dd>
                <PlateBadge plate={session.plate} size="lg" />
              </dd>
            </div>
            <div>
              <dt>{t("journal.colStatus")}</dt>
              <dd>
                <StatusBadge session={session} />
              </dd>
            </div>
            <div>
              <dt>{t("journal.colEntered")}</dt>
              <dd>{session.opened_at_exit ? t("journal.atExit") : stamp(session.entered_at)}</dd>
            </div>
            <div>
              <dt>{t("journal.colExited")}</dt>
              <dd>{session.exited_at === null ? t("status.open") : stamp(session.exited_at)}</dd>
            </div>
            <div>
              <dt>{t("journal.colDuration")}</dt>
              <dd>
                {session.duration_minutes === null || session.opened_at_exit
                  ? t("unknown")
                  : fmt.duration(session.duration_minutes)}
              </dd>
            </div>
            <div>
              <dt>{t("journal.colAmount")}</dt>
              <dd>{fmt.soum(session.amount_soum)}</dd>
            </div>
          </dl>
        </div>
      </Dialog.Content>
    </Dialog.Root>
  );
}

/**
 * Jurnaldan ochilgan kadr — FAQAT bosilganda so'raladi. Kesh doirasi
 * alohida (`journal`): galereya kartasi ochiq turgan AYNI kadrning
 * havolasini oyna yopilganda bekor qilib qo'ymasin.
 */
export function JournalPhotoDialog({
  siteId,
  session,
  onClose,
}: {
  siteId: string;
  session: EdgeParkingReportSession;
  onClose: () => void;
}) {
  const image = useEdgeFileHref(siteId, session.entry_file_id, true, "journal");
  return (
    <SessionDialog
      failed={image.isError}
      href={image.href}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      open
      session={session}
    />
  );
}
