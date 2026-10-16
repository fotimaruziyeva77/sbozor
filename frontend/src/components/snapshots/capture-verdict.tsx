"use client";

import { CameraOff, CheckCircle2, Clock, TriangleAlert } from "lucide-react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";

import { captureCellState } from "@/components/snapshots/capture-cell";
import { cameraNameCounts } from "@/components/snapshots/capture-grid";
import type { CaptureCameraMeta } from "@/components/snapshots/capture-grid";
import { formatSlotTime } from "@/components/snapshots/schedule-card";
import { Button } from "@/components/ui/button";
import type { CaptureRun } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { formatInstant } from "@/lib/format-day";
import { useRelativePast } from "@/lib/format-relative";

/*
 * =============================================================================
 * KADR OLISH HOLATI — sahifaning BIRINCHI javobi (261016).
 *
 * Buyurtmachi: «Kadr olish tushunarsiz». Oltita hisoblagich va matritsa
 * aniq, lekin «kameralar ishlayaptimi?» degan savolga hech biri bitta
 * jumlada javob bermasdi. Banner shu jumla: qizil — bitta ham kadr yo'q,
 * sariq — ba'zi kameralarda muammo (nomi bilan), yashil — hammasi joyida,
 * neytral — bugungi birinchi vaqt hali kelmagan.
 *
 * ⛔ HISOB QATORLARDAN (`rows`) va matritsa bilan AYNI holat funksiyasidan
 *    (`captureCellState`): banner aytgan muammoli kamera jadvalda ham
 *    muammoli ko'rinadi. Kunlik xulosaning oltita hisoblagichi o'z
 *    joyida qoladi — banner ularni almashtirmaydi, faqat so'z bilan aytadi.
 *
 * ⛔ «Oxirgi kadr» FAQAT BUGUN uchun: `newest_capture_at` — HOZIRGI
 *    holat. O'tgan kun ko'rilayotganda u boshqa kunning javobi bo'lardi.
 * =============================================================================
 */

/** Bitta kameraning kunlik hisobi — matritsa qatori bilan bir xil. */
export type CameraHealth = {
  cameraId: string;
  name: string;
  ok: number;
  /** Olindi, lekin sifatsiz: qorong'i, bo'sh, buzuq. */
  poor: number;
  /** Umuman kelmadi: xato yoki olinmadi. */
  lost: number;
  /** Navbatda yoki hozir olinmoqda. */
  pending: number;
};

export function cameraHealth(rows: readonly CaptureRun[]): CameraHealth[] {
  const byCamera = new Map<string, CameraHealth>();
  for (const row of rows) {
    let entry = byCamera.get(row.camera_id);
    if (entry === undefined) {
      entry = {
        cameraId: row.camera_id,
        name: row.camera_name,
        ok: 0,
        poor: 0,
        lost: 0,
        pending: 0,
      };
      byCamera.set(row.camera_id, entry);
    }
    switch (captureCellState(row)) {
      case "ok":
        entry.ok += 1;
        break;
      case "dark":
      case "blank":
      case "corrupt":
        entry.poor += 1;
        break;
      case "failed":
      case "missed":
        entry.lost += 1;
        break;
      case "pending":
      case "running":
        entry.pending += 1;
        break;
      case "skipped":
        /* Rejaga kirmagan vaqt — hisobga ham kirmaydi. */
        break;
    }
  }
  return [...byCamera.values()];
}

export type CaptureVerdict =
  | { kind: "down"; lost: number }
  | { kind: "issues"; cameras: number; problems: CameraHealth[] }
  | { kind: "ok"; cameras: number; next: string | null; ok: number }
  | { kind: "waiting"; cameras: number; next: string | null };

/**
 * Kun holati — `null` bo'lsa banner chizilmaydi (rejada kamera yo'q;
 * buni kunlik xulosaning «rejalashtirilmagan» holati aytadi).
 */
export function captureVerdict(rows: readonly CaptureRun[]): CaptureVerdict | null {
  const health = cameraHealth(rows);
  if (health.length === 0) return null;

  const sum = (pick: (camera: CameraHealth) => number) =>
    health.reduce((total, camera) => total + pick(camera), 0);
  const ok = sum((camera) => camera.ok);
  const poor = sum((camera) => camera.poor);
  const lost = sum((camera) => camera.lost);

  const waitingTimes = rows
    .filter((row) => {
      const state = captureCellState(row);
      return state === "pending" || state === "running";
    })
    .map((row) => row.slot_time)
    .sort();
  const next = waitingTimes[0] === undefined ? null : formatSlotTime(waitingTimes[0]);

  if (ok + poor === 0 && lost > 0) return { kind: "down", lost };

  if (lost > 0 || poor > 0) {
    const problems = health
      .filter((camera) => camera.lost > 0 || camera.poor > 0)
      .sort((left, right) => right.lost - left.lost || right.poor - left.poor);
    return { kind: "issues", cameras: health.length, problems };
  }

  if (ok > 0) return { kind: "ok", cameras: health.length, next, ok };

  return { kind: "waiting", cameras: health.length, next };
}

/** Bannerda nomi bilan ko'rsatiladigan muammoli kameralar — qolgani «yana N». */
const VISIBLE_PROBLEMS = 4;

const TONES = {
  down: { Icon: CameraOff, banner: "verdict-danger", icon: "stat-tone-danger" },
  issues: { Icon: TriangleAlert, banner: "verdict-warning", icon: "stat-tone-warning" },
  ok: { Icon: CheckCircle2, banner: "verdict-success", icon: "stat-tone-success" },
  waiting: { Icon: Clock, banner: "verdict-neutral", icon: "stat-tone-accent" },
} as const;

export function CaptureVerdictBanner({
  cameraMeta,
  isToday,
  newestCaptureAt,
  onShowIssues,
  rows,
}: {
  /** `/cameras` dan IP — bir xil nomli kameralarni ajratish uchun. */
  cameraMeta: CaptureCameraMeta;
  isToday: boolean;
  /** `/cameras` javobidagi eng yangi kadr lahzasi (server hisoblaydi). */
  newestCaptureAt: string | null;
  /** Matritsada faqat muammoli qatorlarni qoldiradi (`?issues=1`). */
  onShowIssues: () => void;
  rows: readonly CaptureRun[];
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone();
  const now = useNow();
  const relativePast = useRelativePast();

  const verdict = captureVerdict(rows);
  if (verdict === null) return null;

  const tone = TONES[verdict.kind];
  const names = cameraNameCounts(rows);
  const labelOf = (camera: CameraHealth) => {
    const ip = cameraMeta.get(camera.cameraId)?.ip ?? null;
    return (names.get(camera.name) ?? 0) > 1 && ip !== null
      ? `${camera.name} · ${ip}`
      : camera.name;
  };

  let title: string;
  const lines: string[] = [];
  if (verdict.kind === "down") {
    title = isToday ? t("snapshots.verdictDownToday") : t("snapshots.verdictDownDay");
    lines.push(t("snapshots.verdictDownBody", { count: verdict.lost }));
    if (isToday && newestCaptureAt !== null) {
      const last = new Date(newestCaptureAt);
      lines.push(
        t("snapshots.verdictLastFrame", {
          ago: relativePast(last, now),
          time: formatInstant(format, last, locale, timeZone),
        }),
      );
    }
    lines.push(t("snapshots.verdictDownHint"));
  } else if (verdict.kind === "issues") {
    title = t("snapshots.verdictIssuesTitle", {
      count: verdict.problems.length,
      total: verdict.cameras,
    });
  } else if (verdict.kind === "ok") {
    title = isToday ? t("snapshots.verdictOkToday") : t("snapshots.verdictOkDay");
    lines.push(t("snapshots.verdictOkBody", { cameras: verdict.cameras, count: verdict.ok }));
    if (isToday && verdict.next !== null) {
      lines.push(t("snapshots.verdictNext", { time: verdict.next }));
    }
  } else {
    title =
      verdict.next === null
        ? t("snapshots.verdictWaitingNoTime")
        : t("snapshots.verdictWaiting", { time: verdict.next });
    lines.push(t("snapshots.verdictWaitingBody", { cameras: verdict.cameras }));
  }

  const shown = verdict.kind === "issues" ? verdict.problems.slice(0, VISIBLE_PROBLEMS) : [];
  const hidden = verdict.kind === "issues" ? verdict.problems.length - shown.length : 0;

  return (
    <section aria-label={t("snapshots.verdictLabel")} className={cn("verdict-banner", tone.banner)}>
      <span aria-hidden="true" className={cn("verdict-icon", tone.icon)}>
        <tone.Icon className="size-6" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <h2 className="verdict-title">{title}</h2>
        {lines.length > 0 ? (
          <div className="flex flex-col gap-1 text-sm">
            {lines.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        ) : null}
        {shown.length > 0 ? (
          <ul className="flex flex-wrap gap-2">
            {shown.map((camera) => (
              <li className="verdict-chip" key={camera.cameraId}>
                <span className="font-semibold">{labelOf(camera)}</span>
                {camera.lost > 0 ? (
                  <span className="text-danger-text">
                    {t("snapshots.verdictCameraLost", { count: camera.lost })}
                  </span>
                ) : null}
                {camera.poor > 0 ? (
                  <span className="text-text-muted">
                    {t("snapshots.verdictCameraPoor", { count: camera.poor })}
                  </span>
                ) : null}
              </li>
            ))}
            {hidden > 0 ? (
              <li className="verdict-chip text-text-muted">
                {t("snapshots.verdictMore", { count: hidden })}
              </li>
            ) : null}
          </ul>
        ) : null}
        {verdict.kind === "issues" ? (
          <div>
            <Button onClick={onShowIssues} size="sm" variant="secondary">
              {t("snapshots.verdictShowIssues")}
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
