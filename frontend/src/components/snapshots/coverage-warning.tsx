"use client";

import { TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * QOPLANMAGAN KUN — BO'SHLIQ XATO EMAS, LEKIN JIM HAM EMAS (§10.5).
 *
 * Ikki jadval profili orasidagi bo'shliq NOSOZLIK EMAS: mavsumiy
 * yopiladigan bozorda u butunlay qonuniy holat. Lekin u KO'RINMASA,
 * natija jim MA'LUMOT YO'QOTISH bo'ladi — o'sha kunlarda kadr umuman
 * olinmaydi va buni hech kim bilmaydi. Kunlar o'tib ketgach, «o'sha
 * hafta nega bo'sh?» savoliga javob beradigan hech narsa qolmaydi.
 *
 * Shuning uchun blok `nvr-error-block.tsx` ning shaklini oladi —
 * SABAB + NIMA QILISH KERAK — lekin `role="alert"` OLMAYDI: bu yangi
 * hodisa emas, sahifa yuklanganda mavjud bo'lgan HOLAT. `role="alert"`
 * uni har sahifa yuklanishida qayta o'qitardi (§12.6 dagi zona B
 * qoidasining aynan o'zi).
 *
 * ⚠ SARIQ MATN EMAS (§9.2): `bg-warning/20 text-text` — o'lchangan
 *   15,64:1. `--color-warning` oq fonda 2,03:1 beradi va u MATN rangi
 *   sifatida hech qachon ishlatilmaydi. Shu sababdan taqiqlangan
 *   utilita nomi bu izohda ham literal yozilmaydi (kodbaza
 *   konvensiyasi: darvoza o'z hujjati ustida qizarmasin).
 *
 * ⚠ TUZATISH YO'LI IKKI MUQOBILNI BERADI (`coverageFix`): mavsumiy
 *   jadval qo'shish YOKI amaldagi jadvalning tugash sanasini olib
 *   tashlash. Bittasini ko'rsatish adminni noto'g'ri yo'lga majburlardi
 *   — bo'shliq ikkala sababdan ham paydo bo'ladi.
 * =============================================================================
 */

export function CoverageWarning({
  className,
  count,
  horizonDays,
}: {
  className?: string;
  /** `uncovered_days` — `GET /snapshot-schedules/today` javobidan. */
  count: number;
  /** `uncovered_horizon_days` — sanoq QAYSI oyna ustida aytilgani. */
  horizonDays: number;
}) {
  const t = useTranslations();

  /*
   * ⛔ NOL — KOMPONENT UMUMAN CHIZILMAYDI. «Hammasi qoplangan» degan
   *    yashil panel shovqin bo'lardi: u har kuni ekranda turib, admin
   *    uni o'qishni to'xtatardi va bo'shliq paydo bo'lgan kuni ham
   *    e'tibor bermasdi (zona B ning Z-3 qoidasi bilan bir xil mantiq).
   */
  if (count <= 0) return null;

  return (
    <div
      className={cn(
        "flex gap-3 rounded-md bg-warning/20 p-4 text-text",
        className,
      )}
      role="status"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />

      {/*
       * `<dl>` — yorliq va mazmun AYNAN juftlik (`nvr-error-block.tsx`
       * naqshi). Ikkala `<dt>` bir xil sinfda, ikkala `<dd>` ham: teng
       * og'irlik razmetkadan ham ko'rinadi va tuzatish yo'li sababning
       * «izohi» bo'lib qolmaydi (D-02).
       */}
      <dl className="flex min-w-0 flex-1 flex-col gap-3">
        <div>
          <dt className="text-sm font-semibold">{t("snapshots.coverageTitle")}</dt>
          <dd className="text-sm leading-normal">
            {t("snapshots.coverageBody", { count, horizon: horizonDays })}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold tracking-wide">
            {t("snapshots.errorFixLabel")}
          </dt>
          <dd className="text-sm leading-normal">
            {t("snapshots.coverageFix")}
          </dd>
        </div>
      </dl>
    </div>
  );
}
