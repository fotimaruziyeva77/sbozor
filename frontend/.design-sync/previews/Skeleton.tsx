import { Skeleton } from "sbozor-frontend";

export const AmountPlaceholder = () => (
  <div className="flex w-80 flex-col gap-3">
    <Skeleton className="h-11 w-40" />
    <Skeleton className="h-4 w-24" />
  </div>
);

export const CardPlaceholder = () => (
  <div className="w-80">
    <Skeleton className="h-24 w-full" />
  </div>
);
