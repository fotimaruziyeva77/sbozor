"use client";

import { useEffect } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ApiError, apiFetch, apiRequest } from "@/lib/api-client";
import {
  edgeActivationCodeSchema,
  edgeCommandListSchema,
  edgeCommandSchema,
  edgeConfigInvalidSchema,
  edgeConfigSchema,
  edgeEventPageSchema,
  edgeParkingReportSchema,
  edgeParkingSummarySchema,
  edgeSiteCreatedSchema,
  edgeSiteListSchema,
  edgeSiteSchema,
} from "@/lib/api-types";
import type {
  EdgeCommand,
  EdgeConfigIssue,
  EdgeSiteKind,
} from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey, saveBlob } from "@/lib/market-queries";

/*
 * =============================================================================
 * Universal agentlar (edge sites) — server holati.
 *
 * `camera-queries.ts` naqshi: har kalit `domainKey(marketId, ...)` bilan
 * TUG'ILISHIDANOQ doiralangan va `marketId === null` da so'rov yuborilmaydi
 * (aks holda `409 market_not_selected` kesh grafida yashab qolardi).
 * =============================================================================
 */

export const EDGE_SITES_PATH = "/edge-sites";

/** Hodisalar sahifasi hajmi — backend standarti bilan bir xil. */
export const EDGE_EVENT_PAGE_SIZE = 50;

/** Yetkazilmagan buyruq bor paytdagi poll oralig'i. */
const COMMAND_POLL_MS = 5_000;

/** Agentlar ro'yxati / sahifa holati — onlayn belgisi eskirmasin. */
const SITE_POLL_MS = 30_000;

export const edgeSitesKey = (marketId: string) =>
  domainKey(marketId, "edge-sites");
export const edgeSiteKey = (marketId: string, siteId: string) =>
  domainKey(marketId, "edge-sites", "detail", siteId);
export const edgeConfigKey = (marketId: string, siteId: string) =>
  domainKey(marketId, "edge-sites", "config", siteId);
export const edgeCommandsKey = (marketId: string, siteId: string) =>
  domainKey(marketId, "edge-sites", "commands", siteId);
export const edgeEventsKey = (marketId: string, siteId: string, type: string) =>
  domainKey(marketId, "edge-sites", "events", siteId, type);
export const edgeParkingSummaryKey = (marketId: string, siteId: string) =>
  domainKey(marketId, "edge-sites", "parking-summary", siteId);
export const edgeParkingReportKey = (
  marketId: string,
  siteId: string,
  from: string,
  to: string,
) => domainKey(marketId, "edge-sites", "parking-report", siteId, from, to);
/**
 * Seanslarsiz yig'indi (`sessions=0`) — direktor paneli. ⛔ ALOHIDA kalit:
 * `/parking` sahifasi to'liq javobni (seanslar bilan) shu davr uchun
 * keshdan bo'sh ro'yxat bilan olib qo'ymasin.
 */
export const edgeParkingTotalsKey = (
  marketId: string,
  siteId: string,
  from: string,
  to: string,
) => domainKey(marketId, "edge-sites", "parking-report-totals", siteId, from, to);
export const edgeFileKey = (marketId: string, siteId: string, fileId: string) =>
  domainKey(marketId, "edge-file", siteId, fileId);

function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

function sitePath(siteId: string): string {
  return `${EDGE_SITES_PATH}/${encodeURIComponent(siteId)}`;
}

/* --- Obyektlar ------------------------------------------------------------ */

/**
 * `options.enabled` — huquq tekshiruvi SO'ROVDAN OLDIN (direktor paneli:
 * `camera_view` siz sessiyada ro'yxat so'ralmaydi va 403 yozilmaydi).
 */
export function useEdgeSitesQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: edgeSitesKey(marketId ?? ""),
    queryFn: () => apiFetch(EDGE_SITES_PATH, { schema: edgeSiteListSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    refetchInterval: SITE_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useEdgeSiteQuery(siteId: string) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: edgeSiteKey(marketId ?? "", siteId),
    queryFn: () => apiFetch(sitePath(siteId), { schema: edgeSiteSchema }),
    enabled: marketId !== null && siteId !== "",
    refetchInterval: SITE_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useCreateEdgeSite() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { kind: EdgeSiteKind; name: string }) =>
      apiFetch(EDGE_SITES_PATH, {
        method: "POST",
        body: input,
        schema: edgeSiteCreatedSchema,
      }),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: edgeSitesKey(marketId) }),
  });
}

/**
 * Yangi aktivatsiya kodi. `useMutation` — kod bir martalik va muddatli,
 * keshlangan qiymat eskirgan kodni ko'rsatardi.
 */
export function useCreateActivationCode(siteId: string) {
  return useMutation({
    mutationFn: () =>
      apiFetch(`${sitePath(siteId)}/activation-codes`, {
        method: "POST",
        schema: edgeActivationCodeSchema,
      }),
  });
}

/* --- Konfiguratsiya ------------------------------------------------------- */

export function useEdgeConfigQuery(siteId: string) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: edgeConfigKey(marketId ?? "", siteId),
    queryFn: () =>
      apiFetch(`${sitePath(siteId)}/config`, { schema: edgeConfigSchema }),
    enabled: marketId !== null && siteId !== "",
    // Tahrirlanayotgan matn ostidan hujjat almashib qolmasin.
    refetchOnWindowFocus: false,
  });
}

export function useSaveEdgeConfig(siteId: string) {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (doc: Record<string, unknown>) =>
      apiFetch(`${sitePath(siteId)}/config`, {
        method: "PUT",
        body: { doc },
        schema: edgeConfigSchema,
      }),
    onSuccess: (saved) => {
      client.setQueryData(edgeConfigKey(marketId, siteId), saved);
      void client.invalidateQueries({ queryKey: edgeSitesKey(marketId) });
    },
  });
}

/**
 * 422 `config_invalid` -> server aytgan xatolar ro'yxati.
 * `null` — bu boshqa xato (chaqiruvchi umumiy xabarni ko'rsatadi).
 */
export function edgeConfigIssuesOf(error: unknown): EdgeConfigIssue[] | null {
  if (!(error instanceof ApiError) || error.status !== 422) return null;
  const parsed = edgeConfigInvalidSchema.safeParse(error.body);
  return parsed.success ? parsed.data.detail.errors : null;
}

/* --- Buyruqlar ------------------------------------------------------------ */

export function isCommandPending(command: EdgeCommand): boolean {
  return command.result_status === null;
}

export function useEdgeCommandsQuery(siteId: string) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: edgeCommandsKey(marketId ?? "", siteId),
    queryFn: () =>
      apiFetch(`${sitePath(siteId)}/commands`, {
        schema: edgeCommandListSchema,
      }),
    enabled: marketId !== null && siteId !== "",
    refetchInterval: (query) =>
      (query.state.data?.items ?? []).some(isCommandPending) &&
      query.state.fetchFailureCount < 3
        ? COMMAND_POLL_MS
        : false,
    refetchIntervalInBackground: false,
  });
}

export function useSendEdgeCommand(siteId: string) {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { type: string; data: Record<string, unknown> }) =>
      apiFetch(`${sitePath(siteId)}/commands`, {
        method: "POST",
        body: input,
        schema: edgeCommandSchema,
      }),
    onSuccess: () =>
      void client.invalidateQueries({
        queryKey: edgeCommandsKey(marketId, siteId),
      }),
  });
}

/* --- Hodisalar va avtoturargoh xulosasi ----------------------------------- */

export function useEdgeEventsQuery(siteId: string, type: string) {
  const marketId = useMarketId();
  return useInfiniteQuery({
    queryKey: edgeEventsKey(marketId ?? "", siteId, type),
    queryFn: ({ pageParam, signal }) => {
      const params = new URLSearchParams();
      if (type) params.set("type", type);
      params.set("limit", String(EDGE_EVENT_PAGE_SIZE));
      params.set("offset", String(pageParam));
      return apiFetch(`${sitePath(siteId)}/events?${params.toString()}`, {
        schema: edgeEventPageSchema,
        signal,
      });
    },
    initialPageParam: 0,
    getNextPageParam: (last, pages) =>
      last.has_more
        ? pages.reduce((sum, page) => sum + page.items.length, 0)
        : undefined,
    enabled: marketId !== null && siteId !== "",
    refetchOnWindowFocus: false,
  });
}

export function useEdgeParkingSummaryQuery(
  siteId: string,
  options: { enabled: boolean },
) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: edgeParkingSummaryKey(marketId ?? "", siteId),
    queryFn: () =>
      apiFetch(`${sitePath(siteId)}/parking-summary`, {
        schema: edgeParkingSummarySchema,
      }),
    enabled: marketId !== null && siteId !== "" && options.enabled,
    refetchInterval: SITE_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

/* --- Avtoturargoh davr hisoboti -------------------------------------------- */

/** Hisobot davri — ⛔ IKKALA chegara ham MAJBURIY (fayl davrsiz tarqalmasin). */
export type ParkingReportPeriod = {
  readonly from: string;
  readonly to: string;
};

/**
 * ⛔ IKKI YO'L, IKKI FUNKSIYA (`report-queries.ts::buildReportDataPath` /
 *    `buildReportPath` bilan AYNI mulohaza): bitta funksiyaga format
 *    argumenti qo'shilsa uni unutish mumkin bo'lardi va `saveBlob` diskka
 *    `.xlsx` nomi bilan JSON yozardi.
 */
function buildParkingReportDataPath(
  siteId: string,
  period: ParkingReportPeriod,
  sessions: boolean,
): string {
  const query = new URLSearchParams({ from: period.from, to: period.to });
  /* `sessions=0`: javob AYNI, faqat `sessions: []` va davr 366 kungacha. */
  if (!sessions) query.set("sessions", "0");
  return `${sitePath(siteId)}/parking-report?${query.toString()}`;
}

function buildParkingReportExportPath(
  siteId: string,
  period: ParkingReportPeriod,
): string {
  const query = new URLSearchParams({ from: period.from, to: period.to });
  return `${sitePath(siteId)}/parking-report.xlsx?${query.toString()}`;
}

/**
 * `GET /edge-sites/{id}/parking-report?from=&to=` — kunlar, yig'indi, seanslar.
 *
 * `staleTime` 1 daqiqa: bugungi kun ham davrga kiradi va hodisalar real
 * vaqtda keladi — lekin har fokusda qayta so'rash direktor ekranini
 * sababsiz miltillatardi.
 *
 * `options.sessions === false` — seanslarsiz yig'indi (`sessions=0`,
 * direktor paneli): kunlar, soatlar va yig'indilar AYNI, mashinalar
 * ro'yxati bo'sh, davr 366 kungacha. Standart — to'liq javob (`/parking`
 * sahifasi jurnal va galereya uchun seanslarni talab qiladi).
 */
export function useEdgeParkingReportQuery(
  siteId: string,
  period: ParkingReportPeriod,
  options: { enabled: boolean; sessions?: boolean },
) {
  const marketId = useMarketId();
  const sessions = options.sessions ?? true;
  const keyOf = sessions ? edgeParkingReportKey : edgeParkingTotalsKey;
  return useQuery({
    queryKey: keyOf(marketId ?? "", siteId, period.from, period.to),
    queryFn: ({ signal }) =>
      apiFetch(buildParkingReportDataPath(siteId, period, sessions), {
        schema: edgeParkingReportSchema,
        signal,
      }),
    enabled: marketId !== null && siteId !== "" && options.enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

/**
 * `Content-Disposition` dan fayl nomini O'QIYDI — server quradi (D-06).
 * Sarlavha yo'q/bo'sh/`download` bo'lsa ASCII zaxira shablon.
 */
function parkingReportFilename(
  response: Response,
  siteId: string,
  period: ParkingReportPeriod,
): string {
  const header = response.headers.get("content-disposition") ?? "";
  const quoted = /filename\s*=\s*"([^"]*)"/iu.exec(header);
  const name = (quoted?.[1] ?? "").split(/[/\\]/u).pop()?.trim() ?? "";
  if (name === "" || name === "download") {
    return `avtoturargoh_${siteId}_${period.from}_${period.to}.xlsx`;
  }
  return name;
}

/**
 * `.xlsx` ni diskka tushiradi — `report-queries.ts::downloadReport` naqshi.
 *
 * ⛔ `window.open` / `location.href` / xom anchor YO'Q: access token
 *    XOTIRADA va SARLAVHADA ketadi (`api-client.ts`), brauzer boshlagan
 *    yuklab olish tokensiz 401 olardi va 401 tanasini `.xlsx` nomi bilan
 *    saqlardi. Yagona zanjir: `apiRequest` -> `blob` -> `saveBlob`.
 */
export async function downloadParkingReport(
  siteId: string,
  period: ParkingReportPeriod,
): Promise<void> {
  const response = await apiRequest(buildParkingReportExportPath(siteId, period));
  saveBlob(await response.blob(), parkingReportFilename(response, siteId, period));
}

/* --- Kadr fayllari -------------------------------------------------------- */

/**
 * `GET /edge-sites/{id}/files/{file_id}` — SESSIYA TOKENI bilan.
 *
 * `review-queries.ts::useEvidenceImageHref` naqshi: `<img>` sarlavha
 * qo'sha olmaydi, shuning uchun baytlar `apiRequest` bilan olinadi va
 * vaqtinchalik obyekt havolasiga aylanadi; komponent yopilganda bekor
 * qilinadi. Har ochilish serverda auditga yoziladi — shuning uchun
 * `retry` va fokusda qayta so'rash YO'Q, `enabled` esa faqat qator
 * ko'rinishga kirganda yoqiladi.
 *
 * `scope` — bitta sahifada AYNI kadr ikki mustaqil joyda ochilsa (hisobot
 * galereyasi va jurnal oynasi): umumiy kesh yozuvida birinchisi yopilganda
 * obyekt havolasini bekor qilib, ikkinchisining rasmini buzardi.
 */
export function useEdgeFileHref(
  siteId: string,
  fileId: string | null,
  enabled: boolean,
  scope = "",
): { href: string | null; isPending: boolean; isError: boolean } {
  const marketId = useMarketId();
  const key = edgeFileKey(marketId ?? "", siteId, fileId ?? "");

  const image = useQuery({
    queryKey: scope === "" ? key : [...key, scope],
    queryFn: async () => {
      const response = await apiRequest(
        `${sitePath(siteId)}/files/${encodeURIComponent(fileId ?? "")}`,
      );
      return URL.createObjectURL(await response.blob());
    },
    enabled: marketId !== null && fileId !== null && enabled,
    gcTime: 0,
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  const href = image.data ?? null;

  useEffect(() => {
    if (href === null) return;
    return () => URL.revokeObjectURL(href);
  }, [href]);

  return {
    href,
    isPending: fileId !== null && image.isPending,
    isError: image.isError,
  };
}
