import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * Apple-uslub: jadval emas, karta va toza ro'yxatlar (topshiriq §7).
 * DIQQAT: matn yo'q — barcha mazmun `children` bo'lib keladi.
 */
export type CardProps = ComponentPropsWithRef<"div">;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface shadow-card",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: CardProps) {
  return (
    <div
      className={cn("flex flex-col gap-1 px-5 pt-5 pb-3", className)}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: CardProps) {
  return <div className={cn("px-5 pb-5", className)} {...props} />;
}
