import { useTranslations } from "next-intl";

import { looksLikePlate, splitUzPlate } from "@/components/parking/parking-data";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * DAVLAT RAQAMI — haqiqiy O'zbekiston raqami ko'rinishida (261102).
 *
 * Oq plastina, qora hoshiya, chapda hudud katagi, o'ngda bayroq va «UZ».
 * Kassir va direktor raqamni ko'chada qanday ko'rsa, ekranda ham shunday
 * ko'radi — «01A123BC» satridan ko'ra tezroq tanib olinadi.
 *
 * ⛔ Plastina HAR TEMADA OQ: bu jismoniy buyum rangi, interfeys tokeni
 *    emas (`globals.css` → `.park-plate`).
 *
 * ⛔ Skrinrider XOM raqamni o'qiydi (`sr-only`), bo'lingan katakchalar
 *    `aria-hidden` — aks holda «01, A 123 BC, UZ» deb o'qilardi.
 * =============================================================================
 */
export function PlateBadge({
  plate,
  size = "md",
  className,
}: {
  plate: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const t = useTranslations("parkingReport");
  const sizeClass = size === "md" ? null : `park-plate-${size}`;

  if (plate === null) {
    return (
      <span className={cn("park-plate park-plate-none", sizeClass, className)}>
        {t("noPlate")}
      </span>
    );
  }

  /* Kamera raqam o'rniga matn bergan (`UNKNOWN`) — plastina emas, xom matn. */
  if (!looksLikePlate(plate)) {
    return (
      <span className={cn("park-plate park-plate-none", sizeClass, className)}>{plate}</span>
    );
  }

  const parts = splitUzPlate(plate);
  return (
    <span className={cn("park-plate", sizeClass, className)}>
      <span className="sr-only">{plate}</span>
      {parts === null ? (
        <span aria-hidden="true" className="park-plate-body">
          {plate}
        </span>
      ) : (
        <>
          <span aria-hidden="true" className="park-plate-region">
            {parts.region}
          </span>
          <span aria-hidden="true" className="park-plate-body">
            {parts.body}
          </span>
          <span aria-hidden="true" className="park-plate-country">
            <span className="park-plate-flag" />
            UZ
          </span>
        </>
      )}
    </span>
  );
}
