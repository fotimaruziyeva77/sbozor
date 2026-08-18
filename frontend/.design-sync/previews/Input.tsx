import { Input } from "sbozor-frontend";

export const Basic = () => (
  <div className="flex w-80 flex-col gap-3">
    <Input placeholder="+998 90 123 45 67" />
    <Input defaultValue="A-01" />
  </div>
);

export const Numeric = () => (
  <div className="w-80">
    <Input className="min-h-14 font-mono text-lg tabular-nums" defaultValue="8000" inputMode="numeric" />
  </div>
);

export const States = () => (
  <div className="flex w-80 flex-col gap-3">
    <Input aria-invalid defaultValue="8 000!" />
    <Input disabled defaultValue="O'zgartirib bo'lmaydi" />
  </div>
);
