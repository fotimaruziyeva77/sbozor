import { Button } from "sbozor-frontend";

export const Variants = () => (
  <div className="flex flex-wrap items-center gap-3">
    <Button>To'lovni tasdiqlash</Button>
    <Button variant="secondary">Qarzni ham olish</Button>
    <Button variant="ghost">Summani o'zgartirish</Button>
    <Button variant="destructive">Bekor qilish</Button>
  </div>
);

export const Sizes = () => (
  <div className="flex flex-wrap items-center gap-3">
    <Button size="sm">Qayta yuborish</Button>
    <Button size="md">Saqlash</Button>
    <Button size="lg">Smenani yopish</Button>
    <Button size="hero">Demo so'rang</Button>
  </div>
);

export const Disabled = () => (
  <div className="flex flex-wrap items-center gap-3">
    <Button disabled>To'lovni tasdiqlash</Button>
    <Button variant="secondary" disabled>Qarzni ham olish</Button>
  </div>
);

/* Mobil oqimdagi asosiy naqsh: to'liq kenglikdagi tasdiqlash tugmasi. */
export const FullWidth = () => (
  <div className="w-80">
    <Button className="w-full" size="lg">To'lovni tasdiqlash</Button>
  </div>
);
