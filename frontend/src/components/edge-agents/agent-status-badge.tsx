"use client";

import { useTranslations } from "next-intl";

import type { AgentState } from "@/components/edge-agents/edge-labels";
import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";

const TONE: Record<AgentState, BadgeTone> = {
  online: "success",
  offline: "danger",
  never: "muted",
};

export function AgentStatusBadge({ state }: { state: AgentState }) {
  const t = useTranslations("edgeAgents.status");
  return <Badge tone={TONE[state]}>{t(state)}</Badge>;
}
