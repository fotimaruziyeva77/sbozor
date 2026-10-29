"use client";

import { useState } from "react";
import { ArrowLeft, KeyRound } from "lucide-react";
import { useNow, useTranslations } from "next-intl";
import { toast } from "sonner";

import { ActivationCodeDialog } from "@/components/edge-agents/activation-code-dialog";
import { AgentStatusBadge } from "@/components/edge-agents/agent-status-badge";
import { CommandPanel } from "@/components/edge-agents/command-panel";
import { ConfigEditor } from "@/components/edge-agents/config-editor";
import {
  agentState,
  hasParkingSummary,
} from "@/components/edge-agents/edge-labels";
import { EventList } from "@/components/edge-agents/event-list";
import { ParkingSummary } from "@/components/edge-agents/parking-summary";
import { DevicesSummary } from "@/components/edge-agents/site-list";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import type { EdgeActivationCode, EdgeSite } from "@/lib/api-types";
import { ApiError, errorMessageKey } from "@/lib/api-client";
import {
  useCreateActivationCode,
  useEdgeSiteQuery,
} from "@/lib/edge-site-queries";
import { useRelativePast } from "@/lib/format-relative";

/** `/agents/[siteId]` ning butun ish maydoni. */
export function SiteDetail({
  siteId,
  canManage,
}: {
  siteId: string;
  canManage: boolean;
}) {
  const t = useTranslations();
  const site = useEdgeSiteQuery(siteId);

  if (site.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (site.isError) {
    if (site.error instanceof ApiError && site.error.status === 404) {
      return (
        <EmptyState
          action={<BackLink />}
          description={t("errors.notFound")}
          title={t("errors.loadFailedTitle")}
        />
      );
    }
    return (
      <div
        className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
        role="alert"
      >
        <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
        <p className="text-sm">{t("errors.loadFailedBody")}</p>
        <Button onClick={() => void site.refetch()} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <SiteHeader canManage={canManage} site={site.data} />
      {hasParkingSummary(site.data) ? <ParkingSummary siteId={siteId} /> : null}
      <CommandPanel canManage={canManage} site={site.data} />
      <EventList siteId={siteId} />
      <ConfigEditor canManage={canManage} siteId={siteId} />
    </div>
  );
}

function BackLink() {
  const t = useTranslations("edgeAgents");
  return (
    <Link
      className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-accent-text underline-offset-2 hover:underline"
      href="/agents"
    >
      <ArrowLeft aria-hidden="true" className="size-4" />
      {t("backToList")}
    </Link>
  );
}

function SiteHeader({ site, canManage }: { site: EdgeSite; canManage: boolean }) {
  const t = useTranslations();
  const now = useNow({ updateInterval: 30_000 });
  const relative = useRelativePast();
  const createCode = useCreateActivationCode(site.id);
  const [code, setCode] = useState<EdgeActivationCode | null>(null);

  const agent = site.agent;
  const lastSeen =
    agent?.last_seen_at != null ? new Date(agent.last_seen_at) : null;

  async function requestCode() {
    try {
      setCode(await createCode.mutateAsync());
    } catch (cause) {
      toast.error(t(errorMessageKey(cause)));
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <BackLink />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-2">
          {/* D-16: obyekt nomi DB kontenti — tarjima qilinmaydi. */}
          <h1 className="text-2xl font-semibold tracking-tight break-words">
            {site.name}
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge tone="neutral">{t(`edgeAgents.kind.${site.kind}`)}</Badge>
            <AgentStatusBadge state={agentState(site)} />
            {agent?.version ? (
              <span className="text-text-muted">
                {t("edgeAgents.agentVersion", { version: agent.version })}
              </span>
            ) : null}
            {agent?.hostname ? (
              <span className="text-text-muted">
                {t("edgeAgents.agentHost", { host: agent.hostname })}
              </span>
            ) : null}
            {lastSeen !== null && !Number.isNaN(lastSeen.getTime()) ? (
              <span className="text-text-muted">{relative(lastSeen, now)}</span>
            ) : null}
          </div>
          {agent !== null ? (
            <div className="text-sm">
              <DevicesSummary devices={agent.heartbeat?.devices ?? null} />
            </div>
          ) : null}
        </div>
        {canManage ? (
          <Button
            disabled={createCode.isPending}
            onClick={() => void requestCode()}
            variant="secondary"
          >
            <KeyRound aria-hidden="true" />
            {t("edgeAgents.codeButton")}
          </Button>
        ) : null}
      </div>
      <ActivationCodeDialog code={code} onClose={() => setCode(null)} />
    </div>
  );
}
