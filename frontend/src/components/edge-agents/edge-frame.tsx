"use client";

import { useEffect, useRef, useState } from "react";
import { ImageOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useEdgeFileHref } from "@/lib/edge-site-queries";

/**
 * Element ko'rinish maydoniga kirdimi. `IntersectionObserver` yo'q muhitda
 * (eski brauzer, jsdom) darhol `true` — kadr ko'rinmay qolgandan ko'ra
 * erta yuklangani yaxshi.
 *
 * Bir marta `true` bo'lgach qaytmaydi: kadr qayta-qayta so'ralmasin
 * (har ochilish serverda auditga yoziladi).
 */
function useSeenOnce<T extends Element>(): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null);
  const [seen, setSeen] = useState(
    () => typeof IntersectionObserver === "undefined",
  );

  useEffect(() => {
    if (seen) return;
    const node = ref.current;
    if (node === null) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [seen]);

  return [ref, seen];
}

/**
 * Hodisa kadrining kichik ko'rinishi — ko'rinishga kirganda yuklanadi,
 * bosilganda kattalashadi. Katta ko'rinish AYNI obyekt havolasini
 * ishlatadi: ikkinchi so'rov (va ikkinchi audit yozuvi) bo'lmaydi.
 */
export function EdgeFrameThumb({
  siteId,
  fileId,
}: {
  siteId: string;
  fileId: string;
}) {
  const t = useTranslations("edgeAgents.frame");
  const [ref, seen] = useSeenOnce<HTMLSpanElement>();
  const image = useEdgeFileHref(siteId, fileId, seen);
  const [open, setOpen] = useState(false);

  return (
    <span className="inline-flex h-12 w-16 shrink-0" ref={ref}>
      {image.href !== null ? (
        <>
          <button
            aria-label={t("open")}
            className="h-12 w-16 overflow-hidden rounded-sm border border-border"
            onClick={() => setOpen(true)}
            type="button"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              alt={t("alt")}
              className="h-full w-full object-cover"
              src={image.href}
            />
          </button>
          <Dialog.Root onOpenChange={setOpen} open={open}>
            <Dialog.Content
              description={t("description")}
              size="xl"
              title={t("title")}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                alt={t("alt")}
                className="max-h-[75vh] w-full rounded-md object-contain"
                src={image.href}
              />
            </Dialog.Content>
          </Dialog.Root>
        </>
      ) : image.isError ? (
        <span
          className="flex h-12 w-16 items-center justify-center rounded-sm bg-surface-muted text-text-muted"
          title={t("unavailable")}
        >
          <ImageOff aria-hidden="true" className="size-4" />
          <span className="sr-only">{t("unavailable")}</span>
        </span>
      ) : (
        <Skeleton className="h-12 w-16" />
      )}
    </span>
  );
}
