"use client";

import { useState } from "react";
import { DoorOpen, Download, RefreshCw } from "lucide-react";
import { useFormatter, useLocale, useTimeZone, useTranslations } from "next-intl";
import { toast } from "sonner";

import {
  COMMAND_TYPES,
  commandState,
  commandTypeLabel,
  gateLanes,
} from "@/components/edge-agents/edge-labels";
import type { CommandStateLabel } from "@/components/edge-agents/edge-labels";
import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { EdgeCommand, EdgeLane, EdgeSite } from "@/lib/api-types";
import { ApiError, errorMessageKey } from "@/lib/api-client";
import { formatInstant } from "@/lib/format-day";
import {
  useEdgeCommandsQuery,
  useSendEdgeCommand,
} from "@/lib/edge-site-queries";

const STATE_TONE: Record<CommandStateLabel, BadgeTone> = {
  pending: "muted",
  delivered: "accent",
  done: "success",
  rejected: "danger",
  failed: "danger",
  expired: "warning",
};

type Pending =
  | { kind: "gate"; lane: EdgeLane; label: string }
  | { kind: "update" }
  | null;

/** Buyruq tugmalari (faqat `camera_manage`) + so'nggi buyruqlar jadvali. */
export function CommandPanel({
  site,
  canManage,
}: {
  site: EdgeSite;
  canManage: boolean;
}) {
  const t = useTranslations();
  const send = useSendEdgeCommand(site.id);
  const [confirm, setConfirm] = useState<Pending>(null);

  async function issue(type: string, data: Record<string, unknown>) {
    try {
      await send.mutateAsync({ type, data });
      toast.success(t("edgeAgents.commands.sent"));
    } catch (cause) {
      if (cause instanceof ApiError && cause.detail === "command_type_invalid") {
        toast.error(t("edgeAgents.commands.invalidType"));
      } else {
        toast.error(t(errorMessageKey(cause)));
      }
    } finally {
      setConfirm(null);
    }
  }

  function laneLabel(lane: EdgeLane): string {
    const name = lane.name || lane.id;
    return lane.direction === "in" || lane.direction === "out"
      ? `${name} (${t(`edgeAgents.commands.direction.${lane.direction}`)})`
      : name;
  }

  const lanes = gateLanes(site);

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">{t("edgeAgents.commands.title")}</h2>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {canManage ? (
          <div className="flex flex-col gap-3">
            {site.kind === "parking" || lanes.length > 0 ? (
              lanes.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {lanes.map((lane) => (
                    <Button
                      disabled={send.isPending}
                      key={lane.id}
                      onClick={() =>
                        setConfirm({ kind: "gate", lane, label: laneLabel(lane) })
                      }
                    >
                      <DoorOpen aria-hidden="true" />
                      {t("edgeAgents.commands.openGate", { lane: laneLabel(lane) })}
                    </Button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-muted">
                  {t("edgeAgents.commands.noLanes")}
                </p>
              )
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={send.isPending}
                onClick={() => void issue(COMMAND_TYPES.configRefresh, {})}
                variant="secondary"
              >
                <RefreshCw aria-hidden="true" />
                {t("edgeAgents.commands.refreshConfig")}
              </Button>
              <Button
                disabled={send.isPending}
                onClick={() => setConfirm({ kind: "update" })}
                variant="secondary"
              >
                <Download aria-hidden="true" />
                {t("edgeAgents.commands.updateAgent")}
              </Button>
            </div>
          </div>
        ) : null}

        <RecentCommands siteId={site.id} />
      </CardContent>

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          confirm?.kind === "update"
            ? t("edgeAgents.commands.confirmUpdate")
            : t("edgeAgents.commands.confirmGate")
        }
        confirmVariant="default"
        description={
          confirm?.kind === "gate"
            ? t("edgeAgents.commands.confirmGateBody", { lane: confirm.label })
            : t("edgeAgents.commands.confirmUpdateBody")
        }
        isBusy={send.isPending}
        onConfirm={() => {
          if (confirm?.kind === "gate") {
            void issue(COMMAND_TYPES.gateOpen, { lane_id: confirm.lane.id });
          } else if (confirm?.kind === "update") {
            void issue(COMMAND_TYPES.agentUpdate, {});
          }
        }}
        onOpenChange={(open) => {
          if (!open) setConfirm(null);
        }}
        open={confirm !== null}
        title={
          confirm?.kind === "update"
            ? t("edgeAgents.commands.confirmUpdateTitle")
            : t("edgeAgents.commands.confirmGateTitle")
        }
      />
    </Card>
  );
}

function RecentCommands({ siteId }: { siteId: string }) {
  const t = useTranslations();
  const commands = useEdgeCommandsQuery(siteId);

  return (
    <section aria-labelledby="edge-commands-recent" className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold" id="edge-commands-recent">
        {t("edgeAgents.commands.recentTitle")}
      </h3>
      {commands.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : commands.isError ? (
        <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
          {t("errors.loadFailedBody")}
        </p>
      ) : commands.data.items.length === 0 ? (
        <p className="text-sm text-text-muted">{t("edgeAgents.commands.empty")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{t("edgeAgents.commands.recentTitle")}</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-2 font-normal" scope="col">{t("edgeAgents.commands.colType")}</th>
                <th className="p-2 font-normal" scope="col">{t("edgeAgents.commands.colIssued")}</th>
                <th className="p-2 font-normal" scope="col">{t("edgeAgents.commands.colResult")}</th>
              </tr>
            </thead>
            <tbody>
              {commands.data.items.map((command) => (
                <CommandRow command={command} key={command.id} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function CommandRow({ command }: { command: EdgeCommand }) {
  const t = useTranslations("edgeAgents.commands");
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone();
  const label = commandTypeLabel(command.type);
  const state = commandState(command);
  const issued = new Date(command.issued_at);
  const laneId = command.data.lane_id;

  return (
    <tr className="border-b border-border align-top">
      <td className="p-2">
        {label === null ? <span className="font-mono">{command.type}</span> : t(label)}
        {typeof laneId === "string" ? (
          <span className="text-text-muted">{` · ${laneId}`}</span>
        ) : null}
      </td>
      <td className="p-2 whitespace-nowrap">
        {Number.isNaN(issued.getTime())
          ? command.issued_at
          : formatInstant(format, issued, locale, timeZone, "short", "medium")}
      </td>
      <td className="p-2">
        <Badge tone={STATE_TONE[state]}>{t(`result.${state}`)}</Badge>
        {command.result_reason ? (
          <span className="ml-2 text-xs text-text-muted">{command.result_reason}</span>
        ) : null}
      </td>
    </tr>
  );
}
