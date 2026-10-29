import type { EdgeCommand, EdgeLane, EdgeSite } from "@/lib/api-types";

/*
 * Agentlar sahifasining sof yordamchilari — tarjima KALITLARI qaytaradi,
 * matn emas. Tarjima chaqiruvchida (`useTranslations("edgeAgents")`).
 */

/** Hodisa turi -> `edgeAgents.events.type.*` kaliti. */
export const EVENT_TYPE_LABELS = {
  "parking.plate.read": "plateRead",
  "parking.session.opened": "sessionOpened",
  "parking.session.closed": "sessionClosed",
  "parking.gate.opened": "gateOpened",
  "parking.anomaly.detected": "anomaly",
  "core.payment.cash": "paymentCash",
  "core.agent.started": "agentStarted",
  "core.device.status": "deviceStatus",
  "core.config.applied": "configApplied",
  "core.update.status": "updateStatus",
  "core.alert.raised": "alertRaised",
  "livestock.vehicle.entered": "vehicleEntered",
  "livestock.fee.collected": "feeCollected",
  "market.occupancy.observed": "occupancyObserved",
} as const;

export type EventTypeLabel =
  (typeof EVENT_TYPE_LABELS)[keyof typeof EVENT_TYPE_LABELS];

export const KNOWN_EVENT_TYPES = Object.keys(
  EVENT_TYPE_LABELS,
) as (keyof typeof EVENT_TYPE_LABELS)[];

/** Noma'lum tur `null` — chaqiruvchi xom turni ko'rsatadi. */
export function eventTypeLabel(type: string): EventTypeLabel | null {
  return Object.hasOwn(EVENT_TYPE_LABELS, type)
    ? EVENT_TYPE_LABELS[type as keyof typeof EVENT_TYPE_LABELS]
    : null;
}

/** Ruxsat etilgan buyruqlar (server ham tekshiradi — 422 `command_type_invalid`). */
export const COMMAND_TYPES = {
  gateOpen: "parking.gate.open",
  configRefresh: "core.config.refresh",
  agentUpdate: "core.agent.update",
} as const;

export type CommandTypeLabel = "gateOpenType" | "refreshConfig" | "updateAgent";

export function commandTypeLabel(type: string): CommandTypeLabel | null {
  switch (type) {
    case COMMAND_TYPES.gateOpen:
      return "gateOpenType";
    case COMMAND_TYPES.configRefresh:
      return "refreshConfig";
    case COMMAND_TYPES.agentUpdate:
      return "updateAgent";
    default:
      return null;
  }
}

export type CommandStateLabel =
  | "pending"
  | "delivered"
  | "done"
  | "rejected"
  | "failed"
  | "expired";

export function commandState(command: EdgeCommand): CommandStateLabel {
  if (command.result_status !== null) return command.result_status;
  return command.delivered_at === null ? "pending" : "delivered";
}

export type AgentState = "online" | "offline" | "never";

export function agentState(site: EdgeSite): AgentState {
  const agent = site.agent;
  if (agent === null || agent.last_seen_at === null) return "never";
  return agent.online ? "online" : "offline";
}

/** Shlagbaum ochiladigan yo'laklar: `kind` yo'q yoki `parking`. */
export function gateLanes(site: EdgeSite): EdgeLane[] {
  return site.setup.lanes.filter(
    (lane) => lane.kind === undefined || lane.kind === null || lane.kind === "parking",
  );
}

/** Avtoturargoh xulosasi qaysi obyektlarda chiziladi. */
export function hasParkingSummary(site: EdgeSite): boolean {
  return site.kind === "parking" || site.kind === "livestock";
}

/**
 * Hodisa `data` sining qisqa ko'rinishi: faqat oddiy (satr/son/mantiqiy)
 * qiymatlar, `kalit: qiymat` juftlari `·` bilan, uzunligi cheklangan.
 * Pul maydonlari (`*_soum`) chaqiruvchining `formatMoney` i bilan.
 */
export function summarizeEventData(
  data: Record<string, unknown>,
  formatMoney: (value: number) => string,
  maxLength = 160,
): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === "number" && key.endsWith("_soum")) {
      parts.push(`${key}: ${formatMoney(value)}`);
    } else if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    ) {
      parts.push(`${key}: ${String(value)}`);
    }
  }
  const text = parts.join(" · ");
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

/** `JSON.parse` natijasi obyekt (massiv yoki `null` EMAS)mi. */
export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
