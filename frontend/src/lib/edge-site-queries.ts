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
import { domainKey } from "@/lib/market-queries";

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

export function useEdgeSitesQuery() {
  const marketId = useMarketId();
  return useQuery({
    queryKey: edgeSitesKey(marketId ?? ""),
    queryFn: () => apiFetch(EDGE_SITES_PATH, { schema: edgeSiteListSchema }),
    enabled: marketId !== null,
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
 */
export function useEdgeFileHref(
  siteId: string,
  fileId: string | null,
  enabled: boolean,
): { href: string | null; isPending: boolean; isError: boolean } {
  const marketId = useMarketId();

  const image = useQuery({
    queryKey: edgeFileKey(marketId ?? "", siteId, fileId ?? ""),
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
