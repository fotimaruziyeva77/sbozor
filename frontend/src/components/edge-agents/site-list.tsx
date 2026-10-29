"use client";

import { useNow, useTranslations } from "next-intl";

import { AgentStatusBadge } from "@/components/edge-agents/agent-status-badge";
import { agentState } from "@/components/edge-agents/edge-labels";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import type { EdgeDeviceStatus, EdgeSite } from "@/lib/api-types";
import { useEdgeSitesQuery } from "@/lib/edge-site-queries";
import { useRelativePast } from "@/lib/format-relative";

/** Obyektlar jadvali — `/agents`. */
export function SiteList() {
  const t = useTranslations();
  const sites = useEdgeSitesQuery();

  if (sites.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
    );
  }

  if (sites.isError) {
    return (
      <div
        className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
        role="alert"
      >
        <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
        <p className="text-sm">{t("errors.loadFailedBody")}</p>
        <Button onClick={() => void sites.refetch()} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  const items = sites.data.items;

  if (items.length === 0) {
    return (
      <EmptyState
        description={t("edgeAgents.emptyHint")}
        title={t("edgeAgents.emptyTitle")}
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{t("edgeAgents.title")}</caption>
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-muted">
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colName")}</th>
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colKind")}</th>
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colStatus")}</th>
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colVersion")}</th>
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colHost")}</th>
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colLastSeen")}</th>
            <th className="p-3 font-normal" scope="col">{t("edgeAgents.colDevices")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((site) => (
            <SiteRow key={site.id} site={site} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SiteRow({ site }: { site: EdgeSite }) {
  const t = useTranslations("edgeAgents");
  const now = useNow({ updateInterval: 30_000 });
  const relative = useRelativePast();
  const agent = site.agent;
  const lastSeen =
    agent?.last_seen_at != null ? new Date(agent.last_seen_at) : null;

  return (
    <tr className="border-b border-border align-top">
      <td className="p-3">
        <Link
          className="font-semibold text-accent-text underline-offset-2 hover:underline"
          href={`/agents/${encodeURIComponent(site.id)}`}
        >
          {site.name}
        </Link>
      </td>
      <td className="p-3">{t(`kind.${site.kind}`)}</td>
      <td className="p-3">
        <AgentStatusBadge state={agentState(site)} />
      </td>
      <td className="p-3 font-mono tabular-nums">{agent?.version || "—"}</td>
      <td className="p-3">{agent?.hostname || "—"}</td>
      <td className="p-3 whitespace-nowrap">
        {lastSeen !== null && !Number.isNaN(lastSeen.getTime())
          ? relative(lastSeen, now)
          : "—"}
      </td>
      <td className="p-3">
        <DevicesSummary devices={agent?.heartbeat?.devices ?? null} />
      </td>
    </tr>
  );
}

/**
 * «3/4 onlayn» + ishlamayotganlar ro'yxati. Ro'yxat `<details>` ichida —
 * klaviatura va skrinriderda ham ochiladi (sichqoncha `title` i yetmaydi).
 */
export function DevicesSummary({
  devices,
}: {
  devices: readonly EdgeDeviceStatus[] | null;
}) {
  const t = useTranslations("edgeAgents");

  if (devices === null || devices.length === 0) {
    return <span className="text-text-muted">{t("devicesNone")}</span>;
  }

  const online = devices.filter((device) => device.status === "online").length;
  const problems = devices.filter((device) => device.status !== "online");
  const summary = t("devicesSummary", { online, total: devices.length });

  if (problems.length === 0) {
    return <span className="whitespace-nowrap">{summary}</span>;
  }

  return (
    <details>
      <summary className="cursor-pointer whitespace-nowrap text-danger-text">
        {summary}
      </summary>
      <ul className="mt-2 flex flex-col gap-1 text-xs">
        {problems.map((device) => (
          <li key={device.id}>
            <span className="font-mono">{device.id}</span>
            {" — "}
            {device.status === "offline" || device.status === "degraded"
              ? t(`deviceStatus.${device.status}`)
              : device.status}
            {device.reason ? (
              <span className="text-text-muted">{` (${device.reason})`}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </details>
  );
}
