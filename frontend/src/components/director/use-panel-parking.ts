"use client";

import { useNow, useTimeZone } from "next-intl";

import { parkingBusinessDay } from "@/components/parking/parking-data";
import type { EdgeParkingReport, EdgeSite } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import {
  useEdgeParkingReportQuery,
  useEdgeSitesQuery,
} from "@/lib/edge-site-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * PANELDAGI AVTOTURARGOH — bitta manba: katak, trend va bo'lim (261103).
 *
 * Buyurtmachi: «boshqaruv panelida faqat rasta pulini emas, avtoturargoh
 * pulini ham qo'sh». Uch joy (Tushum katagi, Tushum dinamikasi, Avtoturargoh
 * bo'limi) shu hookdan o'qiydi — bir davr uchun AYNI kalit, ya'ni ekranda
 * bitta son ikki xil chiqmaydi.
 *
 * ⛔ HUQUQ SO'ROVDAN OLDIN: `camera_view` siz sessiyada (buxgalter) obyektlar
 *    ro'yxati ham, hisobot ham SO'RALMAYDI — panel bugungi holicha qoladi.
 *
 * ⛔ OBYEKT — BIRINCHI avtoturargoh (`/parking` sahifasi bilan AYNI qoida:
 *    ikkinchisi noutbukdagi sinov obyekti).
 *
 * ⛔ SEANSLARSIZ (`sessions=0`): panelga mashinalar ro'yxati kerak emas.
 *
 * ⛔ DAVR ISH KUNIGA QISQARTIRILADI: avtoturargoh kuni 06:00 da boshlanadi
 *    va 00:00–06:00 orasida server kalendar «bugun» ni kelajak deb rad
 *    etadi. Davr butunlay ish kunidan keyin bo'lsa (tunda «Bugun») so'rov
 *    ketmaydi — o'sha kun hali boshlanmagan, tushumi nol.
 * =============================================================================
 */

export type PanelParkingPeriod = { from: string; to: string };

/** Avtoturargoh so'rovining davri; `null` — davr hali boshlanmagan. */
export function parkingRange(
  period: PanelParkingPeriod,
  parkingToday: string,
): PanelParkingPeriod | null {
  const to = period.to > parkingToday ? parkingToday : period.to;
  return period.from > to ? null : { from: period.from, to };
}

export type PanelParkingSite = {
  /** Sessiyada `camera_view` bor. */
  allowed: boolean;
  /** Birinchi avtoturargoh; yo'q, noma'lum yoki huquqsiz — `null`. */
  site: EdgeSite | null;
  /** Obyektlar ro'yxati hali kelmagan. */
  pending: boolean;
};

export function usePanelParkingSite(): PanelParkingSite {
  const principal = useAuthStore().principal;
  const allowed = hasPermission(principal?.roles ?? [], "camera_view");
  const sites = useEdgeSitesQuery({ enabled: allowed });

  if (!allowed) return { allowed, site: null, pending: false };
  const site =
    sites.data?.items.find((item) => item.kind === "parking") ?? null;
  /* `isLoading`, `isPending` emas: tarmoqsiz (pauza) holatda panel abadiy kutmaydi. */
  return { allowed, site, pending: sites.isLoading };
}

export type PanelParkingReport = {
  site: EdgeSite | null;
  /** So'rov yuborilgan davr (ish kuniga qisqartirilgan); `null` — boshlanmagan. */
  range: PanelParkingPeriod | null;
  /** Obyekt yoki hisobot kutilmoqda — son hali ma'lum emas. */
  pending: boolean;
  /** So'rov yiqildi (masalan eski serverda uzun davr — 422). */
  isError: boolean;
  error: unknown;
  data: EdgeParkingReport | null;
  refetch: () => void;
};

export function usePanelParkingReport(
  period: PanelParkingPeriod,
): PanelParkingReport {
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const { site, pending: sitePending } = usePanelParkingSite();
  const range = parkingRange(period, parkingBusinessDay(timeZone, now));
  const enabled = site !== null && range !== null;

  /* Davr boshlanmagan bo'lsa ham kalit barqaror — so'rov baribir ketmaydi. */
  const report = useEdgeParkingReportQuery(site?.id ?? "", range ?? period, {
    enabled,
    sessions: false,
  });

  return {
    site,
    range,
    pending: sitePending || (enabled && report.isLoading),
    isError: enabled && report.isError,
    error: report.error,
    data: enabled ? (report.data ?? null) : null,
    refetch: () => void report.refetch(),
  };
}

/**
 * Davr bo'yicha avtoturargoh tushumi (naqd + terminal), panel uchun.
 *
 *   `null`   — avtoturargoh yo'q / huquq yo'q / so'rov yiqildi: chaqiruvchi
 *              bugungi (faqat rastalar) holiga qaytadi;
 *   `0`      — obyekt bor, davr hali boshlanmagan (tunda «Bugun»);
 *   `number` — serverning `total.total` i.
 *
 * `pending` alohida: son kelguncha katak skeleton ko'rsatadi, rastalar
 * summasini «jami» deb ko'rsatib keyin sakramaydi.
 */
export function parkingTotalOf(report: PanelParkingReport): number | null {
  if (report.site === null || report.isError) return null;
  if (report.range === null) return 0;
  return report.data?.total.total ?? null;
}
