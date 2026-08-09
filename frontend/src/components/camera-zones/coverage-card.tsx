"use client";

import { TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { useZoneCoverage } from "@/lib/camera-zone-queries";

/*
 * =============================================================================
 * ZONA QAMROVI — D-22 BU YERDA KO'ZGA KO'RINADI (UI-SPEC §6.9).
 *
 * ⛔ UCHALA SON HAM DOIM KO'RSATILADI, NOL BO'LGANDA HAM.
 *
 *   Bu 3 va 4-fazadan meros «nol — natija» qoidasi, lekin bu yerda uning
 *   narxi boshqacha. `coverage-warning.tsx` nol bo'lganda UMUMAN
 *   chizilmaydi va bu to'g'ri edi: u OGOHLANTIRISH, ya'ni nol holatda
 *   aytadigan gapi yo'q. Bu esa HISOBOT — «qamrovsiz rasta: 0» degan
 *   qator adminning savoliga («hammasini belgilab bo'ldimmi?») aynan
 *   JAVOB beradi. Kartani yashirish o'sha savolni javobsiz qoldirardi va
 *   admin uni har safar zonalarni sanab tekshirardi.
 *
 * ⛔ «QAMROVSIZ RASTA» MATNIDA «BO'SH» SO'ZI ISHLATILMAYDI (D-22).
 *
 *   Qamrovsiz rasta bo'sh EMAS — u haqida MA'LUMOT YO'Q. Farq DB'da bor,
 *   lekin matn darajasida yo'qolsa hisobot jimgina noto'g'ri o'qilardi va
 *   buni hech qanday sxema ushlamasdi. Mexanik darvoza — G-15
 *   (`scripts/zone-copy.test.mjs`), ya'ni bu qoida ko'rikka emas, testga
 *   bog'langan.
 *
 * ⚠ `role="status"`, `role="alert"` EMAS (§13.6). Bu sahifa
 *   yuklanganda MAVJUD BO'LGAN holat, yangi hodisa emas; `alert` uni har
 *   yuklanishda qayta o'qitib, admin uni eshitmay qo'yardi.
 *
 * ⚠ SARIQ MATN EMAS (§10.2): `bg-warning/20 text-text` — o'lchangan
 *   15,64:1. Ogohlantirish rangi MATN uchun hech qachon ishlatilmaydi.
 *
 * ⚠ «Ro'yxatni ko'rish» TUGMASI QO'YILMADI. §6.9 ning eskizida u bor,
 *   lekin u olib boradigan ro'yxat — `/cameras` sahifasining O'ZI, ya'ni
 *   karta o'sha sahifada turganda tugma foydalanuvchini turgan joyiga
 *   yuborardi. Navigatsiya byudjeti (§4.2) qat'iy: bu fazada kameralar
 *   sahifasiga BITTA amal qo'shiladi va u qatorda yashaydi.
 * =============================================================================
 */

export function CoverageCard({ className }: { className?: string }) {
  const t = useTranslations();
  const coverage = useZoneCoverage();

  if (coverage.isPending) {
    return (
      <Card aria-busy="true" className={className} role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <CardContent className="pt-5">
          <Skeleton className="h-24" />
        </CardContent>
      </Card>
    );
  }

  if (coverage.isError) {
    /*
     * ⚠ XATO BLOKI EMAS, JIM QATOR. Qamrov — sahifaning IKKINCHI darajali
     *   ma'lumoti; uning yuklanmagani `role="alert"` ga arzimaydi va
     *   kameralar ro'yxatining ustida qizil blok chiqarish adminni
     *   mavjud bo'lmagan nosozlikni qidirishga yuborardi. Mavjud kalit
     *   ishlatiladi — bu holat uchun yangi matn o'ylab topilmaydi.
     */
    return (
      <Card className={className}>
        <CardContent className="pt-5">
          <p className="text-sm text-text-muted" role="status">
            {t("errors.loadFailedBody")}
          </p>
        </CardContent>
      </Card>
    );
  }

  const { covered, uncovered, cameras_without_zones: withoutZones } =
    coverage.data;

  return (
    <Card className={className} role="status">
      <CardHeader>
        <h2 className="text-sm font-semibold">{t("cameraZones.coverageTitle")}</h2>
      </CardHeader>

      <CardContent>
        {/*
         * `<dl>` — yorliq va son DASTURIY juftlik (`coverage-warning.tsx`
         * naqshi). Skrinrider «Qamrovdagi rasta: 258» deb o'qiydi; ikki
         * mustaqil `<p>` da bu bog'lanish yo'qolardi.
         */}
        <dl className="flex flex-col gap-2">
          <CoverageRow label={t("cameraZones.covered")} value={covered} />

          {/*
           * ⚠ SABAB QATORI HAR DOIM EMAS, FAQAT NOL BO'LMAGANDA: nol
           *   qamrovsiz rastada «ular haqida ma'lumot yig'ilmaydi»
           *   jumlasi hech kimga tegishli bo'lmasdi. SON esa baribir
           *   ko'rsatiladi — bu ikki xil narsa.
           */}
          <CoverageRow
            hint={uncovered > 0 ? t("cameraZones.uncoveredWhy") : null}
            label={t("cameraZones.uncovered")}
            tone={uncovered > 0 ? "warning" : "plain"}
            value={uncovered}
          />

          <CoverageRow
            label={t("cameraZones.camerasWithoutZones")}
            value={withoutZones}
          />
        </dl>

        {/*
         * ⚠ IJOBIY XULOSA QO'SHIMCHA, ALMASHTIRUVCHI EMAS: uchala son
         *   yuqorida turadi va bu jumla ularni faqat SO'Z bilan
         *   takrorlaydi. Uni sonlar O'RNIGA ko'rsatish «nol — natija»
         *   qoidasini buzardi.
         */}
        {uncovered === 0 ? (
          <p className="mt-3 text-sm text-text-muted">
            {t("cameraZones.allCovered")}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

/**
 * Bitta `<dt>`/`<dd>` juftligi.
 *
 * ⚠ RANG YAGONA SIGNAL EMAS (WCAG 1.4.1, §10.4): sariq tint bilan BIRGA
 *   `TriangleAlert` ikonkasi VA sabab jumlasi keladi — uchta kanal.
 */
function CoverageRow({
  hint,
  label,
  tone = "plain",
  value,
}: {
  hint?: string | null;
  label: string;
  tone?: "plain" | "warning";
  value: number;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1 rounded-sm",
        tone === "warning" ? "bg-warning/20 px-3 py-2 text-text" : null,
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <dt className="flex items-center gap-2 text-sm">
          {tone === "warning" ? (
            <TriangleAlert aria-hidden="true" className="size-4 shrink-0" />
          ) : null}
          {label}
        </dt>
        {/* `font-mono` — HUJJATLASHTIRILGAN ISTISNO (§9.4): ustunlashgan sonlar. */}
        <dd className="font-mono text-sm font-semibold tabular-nums">{value}</dd>
      </div>
      {hint === null || hint === undefined ? null : (
        <dd className="text-xs leading-normal">{hint}</dd>
      )}
    </div>
  );
}
