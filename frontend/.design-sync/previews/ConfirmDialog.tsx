import { ConfirmDialog } from "sbozor-frontend";

const noop = () => {};

export const Open = () => (
  <ConfirmDialog
    cancelLabel="Yopish"
    confirmLabel="Bekor qilish"
    description="Ro'yxatdan sabab tanlang. Bekor qilingan yozuv ro'yxatda qoladi."
    onConfirm={noop}
    onOpenChange={noop}
    open
    title="To'lovni bekor qilish"
  />
);
