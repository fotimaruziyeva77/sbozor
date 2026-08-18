import { Badge } from "sbozor-frontend";

export const Tones = () => (
  <div className="flex flex-wrap items-center gap-2">
    <Badge tone="neutral">Faol</Badge>
    <Badge tone="muted">Ta'mirda</Badge>
    <Badge tone="accent">Namunaviy</Badge>
    <Badge tone="success">To'lov yozildi</Badge>
    <Badge tone="warning">Band, lekin to'lovsiz</Badge>
    <Badge tone="danger">Qarzdor</Badge>
  </div>
);

export const InRow = () => (
  <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-surface px-4 py-3">
    <span className="text-sm font-semibold">A-01</span>
    <span className="font-mono text-sm tabular-nums">8 000 so'm</span>
    <Badge tone="success">To'lov yozildi</Badge>
  </div>
);
