import { Archive, Clock, Wifi, WifiOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import type { CameraStatusValue } from "@/lib/api-types";

/*
 * =============================================================================
 * KAMERA HOLATI — RANG HECH QACHON YAGONA SIGNAL EMAS (UI-SPEC §2.5, WCAG 1.4.1).
 *
 * Har holatda UCHALA kanal ham bor:
 *   1. RANG   — badge tinti;
 *   2. IKONKA — holatga xos shakl (`Wifi` / `WifiOff` / `Clock` / `Archive`);
 *   3. MATN   — to'liq so'z, qisqartmasiz.
 *
 * ⚠ `unknown` `offline` NING SINONIMI EMAS va shuning uchun uchinchi
 *   ikonkani oladi: `offline` — kanal ro'yxatda bor, lekin javob
 *   bermayapti; `unknown` — kanal endigina yozildi va holati HALI
 *   o'lchanmagan. Ikkalasini bitta ko'rinishga yig'ish birinchi skandan
 *   oldin «kamera buzuq» degan YOLG'ON dalilni ekranga chiqarardi.
 *
 * ⚠ BADGE HECH QACHON QISQARTIRILMAYDI (UI-SPEC §11.7 Qoida 4): matn
 *   MA'NO tashiydi va uni uch nuqta bilan kesish uchinchi kanalni
 *   yo'q qiladi. Ru tilida qator uzunroq — konteyner o'sadi, matn
 *   kesilmaydi.
 *
 * ⚠ ARXIV HOLATI STATUSDAN USTUN: arxivlangan kameraning «Onlayn»
 *   ligini ko'rsatish uni ishchi ro'yxatda turgandek ko'rsatardi.
 * =============================================================================
 */

type StatusView = {
  Icon: typeof Wifi;
  labelKey: "online" | "offline" | "unknown" | "archived";
  tone: BadgeTone;
};

const STATUS_VIEW: Record<CameraStatusValue, StatusView> = {
  online: { Icon: Wifi, labelKey: "online", tone: "success" },
  offline: { Icon: WifiOff, labelKey: "offline", tone: "muted" },
  unknown: { Icon: Clock, labelKey: "unknown", tone: "muted" },
};

const ARCHIVED_VIEW: StatusView = {
  Icon: Archive,
  labelKey: "archived",
  tone: "muted",
};

export function CameraStatusBadge({
  isArchived,
  status,
}: {
  isArchived: boolean;
  status: CameraStatusValue;
}) {
  const t = useTranslations("cameras.status");
  const view = isArchived ? ARCHIVED_VIEW : STATUS_VIEW[status];
  const { Icon } = view;

  return (
    <Badge className="gap-1" tone={view.tone}>
      <Icon aria-hidden="true" className="size-3" />
      {t(view.labelKey)}
    </Badge>
  );
}
