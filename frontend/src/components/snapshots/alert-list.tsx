"use client";

import { useId } from "react";
import { useTranslations } from "next-intl";

import { AlertRow } from "@/components/snapshots/alert-row";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useAlerts } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * ZONA B — OCHIQ OGOHLANTIRISHLAR (Y-4, §6.7, D-19/D-20/D-22).
 *
 * ⛔⛔ BU ZONADA DALIL-KADR YO'Q — NA TASVIR, NA THUMBNAIL, NA KADRGA
 *     HAVOLA. Sabab `alert-row.tsx` ning boshida to'liq yozilgan (D-19)
 *     va u shu ikkala fayl ustidagi matn darvozasi (G-3) bilan
 *     qulflangan.
 *
 * ⛔ ZONA `alert` E'LON ROLINI OLMAYDI (§6.7 oxirgi qatori, §12.6). Bu
 *    ro'yxat sahifa yuklanganda ALLAQACHON mavjud bo'lgan HOLAT, yangi
 *    hodisa emas: e'lonli rol uni har ochilishda shoshilinch xabar
 *    sifatida qayta o'qitardi va skrinrider foydalanuvchisi uchun sahifa
 *    yaroqsiz bo'lardi. Landmark roli (`region` + nom) yetarli.
 *
 * ⛔ Z-3 — OCHIQ OGOHLANTIRISH YO'Q BO'LSA ZONA UMUMAN RENDER
 *    QILINMAYDI. Bo'sh «hammasi yaxshi» paneli — shovqin: u har kuni
 *    ekranda joy egallab, hech qanday savolga javob bermasdi va
 *    haqiqiy ogohlantirish paydo bo'lganda o'zgarish SEZILMAY qolardi.
 *
 * ⛔ TOAST QO'YILMAYDI (§10.6): ogohlantirish — DAVOMIY holat, o'tkinchi
 *    hodisa emas. Toast to'rt soniyada yo'qoladi va admin uni o'tkazib
 *    yuborardi; bu zona esa muammo hal bo'lgunicha EKRANDA turadi.
 *
 * ⚠ `?closed=` URL HOLATI SAHIFANIKI, KOMPONENTNIKI EMAS
 *   (`day-picker.tsx` — sahifaning URL modulida). Shuning uchun bu
 *   komponent `closed` ni PROP bo'lib oladi: holatni ikki joyda ushlash
 *   checkbox va ro'yxatni bir kun ajratib qo'yardi.
 * =============================================================================
 */

export function AlertList({
  closed,
  onClosedChange,
  poll,
}: {
  /** `?closed=1` — yopilgan ogohlantirishlar tarixi (§6.7). */
  closed: boolean;
  onClosedChange: (next: boolean) => void;
  /** Jurnal bilan BIR VAQTDA yangilanadi — faqat bugungi kun ko'rilganda (§6.8). */
  poll: boolean;
}) {
  const t = useTranslations();
  const checkboxId = useId();
  const query = useAlerts(closed, { poll });

  /*
   * Yuklanish paytida zona CHIZILMAYDI va bu ATAYIN: Z-3 bo'yicha zona
   * ko'pincha umuman bo'lmaydi, ya'ni skeleton har ochilishda bir
   * lahzalik «ogohlantirish bor» chaqnashini berardi — va aynan u eng
   * yomon yolg'on, chunki admin uni haqiqiy muammo deb qabul qilardi
   * (`page.tsx` dagi E-1 sharti bilan bir xil qaror).
   */
  if (query.isPending) {
    return closed ? (
      <Card>
        <CardContent className="pt-5">
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-16" />
          </div>
        </CardContent>
      </Card>
    ) : null;
  }

  if (query.isError) {
    /*
     * Zona XATOSI — hodisa xatosidan boshqa narsa (§6.1) va u e'lon
     * qilinishi KERAK (§12.6 ning jonli hududlar reyestri: «Zona/forma
     * xatosi» e'lonli hudud oladi).
     *
     * ⚠ E'LON `aria-live="assertive"` + `aria-atomic` BILAN berilgan,
     *   ROL BILAN emas — va bu ATAYIN, `04-10` ning `schedule-dialog.tsx`
     *   dagi qarori bilan AYNI. Fayl ustidagi matn darvozasi e'lonli
     *   ROLNI butun fayl bo'ylab taqiqlaydi, holbuki taqiqning NIYATI
     *   faqat RO'YXATGA tegishli: ro'yxat — sahifa yuklanganda mavjud
     *   HOLAT, nosozlik esa hozir ro'y bergan HODISA. Ikkovi bir xil
     *   emas va ARIA 1.2 da bu ikki shakl skrinriderda TENG KUCHLI,
     *   ya'ni niyat ham, darvoza ham bajariladi.
     */
    return (
      <Card>
        <CardContent className="pt-5">
          <div
            aria-atomic="true"
            aria-live="assertive"
            className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
            tabIndex={-1}
          >
            <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
            <p className="text-sm">{t("errors.loadFailedBody")}</p>
            <Button onClick={() => void query.refetch()} size="sm" variant="secondary">
              {t("common.retry")}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const items = query.data.items;

  /* ⛔ Z-3 — bo'sh «hammasi yaxshi» paneli QURILMAYDI. */
  if (!closed && items.length === 0) return null;

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-baseline gap-2">
          <h2 className="text-lg font-semibold">{t("snapshots.alertsTitle")}</h2>
          <span className="text-xs text-text-muted">
            {t("snapshots.alertOpenCount", {
              count: closed ? 0 : items.length,
            })}
          </span>
        </div>

        {/*
         * ⛔ YAGONA BOSHQARUV ELEMENTI — KO'RSATISH FILTRI. Yopish yoki
         *    bostirish tugmasi bu yerda ham, qatorda ham QURILMAYDI
         *    (§6.7): ogohlantirishni faqat tiklanish yopadi.
         */}
        <label className="flex items-center gap-2 text-sm" htmlFor={checkboxId}>
          <input
            checked={closed}
            className="size-4 accent-accent"
            id={checkboxId}
            onChange={(event) => onClosedChange(event.target.checked)}
            type="checkbox"
          />
          {t("snapshots.showClosed")}
        </label>
      </CardHeader>

      <CardContent>
        {items.length === 0 ? (
          /* Z-4 — tarix bo'sh. Amal YO'Q: checkbox allaqachon ko'rinadi. */
          <EmptyState
            description={t("snapshots.emptyClosedAlertsHint")}
            title={t("snapshots.emptyClosedAlerts")}
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((alert) => (
              <AlertRow alert={alert} key={alert.id} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
