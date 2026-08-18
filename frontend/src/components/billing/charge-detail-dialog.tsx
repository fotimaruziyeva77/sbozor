"use client";

import { useFormatter, useLocale, useTimeZone, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  ChargeAdjustment,
  ChargeEvidence,
  ChargeRow,
} from "@/lib/billing-charge-queries";
import { useChargeDetail } from "@/lib/billing-charge-queries";
import { formatBusinessDay, formatInstant } from "@/lib/format-day";
import { useUsersQuery } from "@/lib/queries";
import { useEvidenceImageHref } from "@/lib/review-queries";

/*
 * =============================================================================
 * DL-3 — YOZILGAN HISOB TAFSILOTI VA DALIL KADRI (§11.3, BILL-02, D-02).
 *
 * ⛔ ANALOGI YO'Q (§3.3) — soxta analog berilmadi. Eng yaqin qarindosh
 *    `occupancy/stall-detail-dialog.tsx` bo'lardi, lekin u AYNAN teskari
 *    holatni hujjatlashtiradi: u yerda dalil kadri OCHILMAYDI, chunki
 *    marshrut `snapshot_id` bermaydi. Bu yerda beradi — ya'ni 05-14 ning
 *    darsi bu safar «ko'rsat» tomonga ishlaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ G-28 — YANGI MARSHRUT HAM, YANGI HUQUQ HAM YO'Q [O'LCHANDI: M-8]
 * -----------------------------------------------------------------------
 * Kadr baytlari MAVJUD YAGONA marshrutdan: `GET /snapshots/{id}/image`.
 * U 05-15 da `CAMERA_VIEW` **yoki** `OCCUPANCY_REVIEW` ostiga o'tgan va
 * `director` ham, `market_admin` ham `camera_view` ga EGA
 * [KOD: `rbac.ts:92,101,120`]. Ya'ni `require_any_permission()` ning
 * ⛔ YOPIQ TO'PLAMI TEGILMAYDI va `SNAPSHOT_EVIDENCE_FRAME_ROUTES` aynan
 * bitta marshrutda qoladi (C-9). Bu fazaning eng arzon xavfsizlik
 * yutug'i bitta KO'LAM qarori bilan qo'lga kiritiladi: dalil kadri
 * ⛔ FAQAT direktor yuzasida, kassirda YO'Q.
 *
 * ⛔ BAYTLAR `<img src>` BILAN TO'G'RIDAN-TO'G'RI OLINMAYDI VA BU
 *    TANLOV EMAS, MEXANIKA: marshrut sessiya tokenini talab qiladi,
 *    `<img>` esa sarlavha qo'sha olmaydi. Shuning uchun
 *    `useEvidenceImageHref` (05-13/05-15 ning mavjud hooki) baytlarni
 *    `apiRequest` bilan oladi va brauzer ichidagi VAQTINCHALIK havolaga
 *    aylantiradi — u sahifadan tashqariga chiqmaydi va komponent
 *    yopilganda bekor qilinadi.
 *    ⚠ Shu sababdan marshrut da'vosi DOM'dagi `src` MATNIDAN emas,
 *      ⛔ `apiRequest` GA BERILGAN YO'LDAN o'lchanadi
 *      (`review-session.test.tsx:339-350` ning aynan naqshi). DOM'dagi
 *      `src` — brauzer havolasi; tarmoq yuzasi esa o'sha yo'l.
 *
 * ⛔ `snapshot_id` YO'Q QATORDA `img` UMUMAN CHIZILMAYDI — na
 *    platsholder, na «yuklanmadi» (05-14 darsi: marshrut bermagan qator
 *    CHIZILMAYDI, stub ham, bo'sh jadval ham rad etilgan).
 *
 * ⛔ Oldindan avtorizatsiyalangan havola, yuklab olish, ulashish va
 *    kanvas orqali nusxa olish — ⛔ BIRORTASI HAM YO'Q (§14.2).
 *    ⚠ Taqiqlangan tokenlar bu izohda LITERAL yozilmaydi: qabul mezoni
 *      ularni xom manbada `grep` bilan sanaydi va izohdagi nusxa
 *      darvozani o'ziga qarshi qo'yardi (kodbaza konvensiyasi,
 *      `badge.tsx:24-26`).
 *
 * -----------------------------------------------------------------------
 * ⛔ D-07 — YOZUV YUZASI YO'Q
 * -----------------------------------------------------------------------
 * Hisobni tahrirlaydigan yoki o'chiradigan marshrut SERVERDA umuman
 * yozilmagan (shartsiz `BEFORE UPDATE OR DELETE` trigger), shuning uchun
 * bu dialogda ham unga sim yo'q. ⛔ O'zgarmaslik jumlasi esa
 * ⛔ HAR DOIM ko'rinadi — tuzatish bo'lmasa ham: u kunning natijasiga
 * emas, YOZUVNING TABIATIGA tegishli va shartga bog'lansa, aynan
 * tuzatishsiz hisobda (ya'ni ko'pchilikda) yo'qolardi.
 *
 * ⛔ TARIF IDENTIFIKATORI KO'RSATILMAYDI (§11.3, 2-bo'lim): u direktorga
 *    ham ma'nosiz identifikator. Ko'rinadigan YAGONA identifikator —
 *    hisobning qisqa shakli, chunki D-02 ning butun sababi «nizo paytida
 *    qaysi yozuv dalil?» degan savolga javob berish.
 * =============================================================================
 */

/** Ko'rinadigan identifikatorning qisqa shakli — D-02 uchun yetarli. */
const SHORT_ID_LENGTH = 8;

export function shortChargeId(chargeId: string): string {
  return chargeId.slice(0, SHORT_ID_LENGTH);
}

export function ChargeDetailDialog({
  charge,
  onOpenChange,
}: {
  /** `null` — dialog yopiq; ro'yxat holatni O'ZI ushlaydi (DL-3). */
  charge: ChargeRow | null;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations();

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={charge !== null}>
      {/*
       * ⛔ `description` GA `billing.immutableNotice` BERILMAYDI — VA BU
       *    O'LCHANGAN QAROR, uslub emas. Radix tavsifni `sr-only` `<p>`
       *    bo'lib DOM'GA CHIQARADI va u dialog TANASI hali yuklanayotgan
       *    paytda ham mavjud bo'ladi. O'shanda D-07 ning «jumla har doim
       *    ko'rinadi» darvozasi 3-BO'LIMNI umuman ko'rmasdan yashil
       *    qaytardi: bo'lim o'chirilgan holatda ham `sr-only` nusxasi
       *    da'voni qondirardi (05-15 ning S-D sinfi). Jumla endi AYNAN
       *    BITTA joyda — 3-bo'limda.
       */}
      <Dialog.Content
        description={t("billing.detail")}
        size="lg"
        sheetOnMobile
        srOnlyDescription
        title={t("billing.chargeWritten")}
      >
        {charge === null ? null : <ChargeDetailBody charge={charge} />}

        <Dialog.Footer>
          <Dialog.Close asChild>
            <Button variant="secondary">{t("common.close")}</Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}

/**
 * Dialog TANASI — so'rov FAQAT ochilganda ketadi.
 *
 * ⚠ Ajratilgan komponent: `charge === null` bo'lganda u umuman montaj
 *   qilinmaydi, ya'ni `useChargeDetail` ham chaqirilmaydi. 300–1000
 *   rastali bozorda har qator uchun tafsilot tortish sahifani
 *   og'irlashtirardi va foydasi nol edi.
 */
function ChargeDetailBody({ charge }: { charge: ChargeRow }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const detail = useChargeDetail(charge.charge_id);

  if (detail.isPending) {
    return (
      <div aria-busy="true" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (detail.isError || detail.data === undefined) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.loadFailedBody")}
      </p>
    );
  }

  const data = detail.data;
  /* D-09: farq TUZATISH bo'lganini aytadi va u 4-bo'limda ochiladi. */
  const adjusted = data.tariff_amount_soum !== data.amount_soum;

  return (
    <div className="flex flex-col gap-5">
      {/* --- 1. SARLAVHA ------------------------------------------------ */}
      <section className="flex flex-col gap-1">
        <p className="text-base font-semibold">
          {charge.stall_code} ·{" "}
          {formatBusinessDay(format, data.service_date, locale)}
        </p>
        {/*
         * ⛔ KO'RINADIGAN YAGONA IDENTIFIKATOR (D-02). Tarif
         *    identifikatori bu yerda ham, boshqa joyda ham YO'Q.
         */}
        <p className="font-mono text-xs text-text-muted">
          {shortChargeId(data.charge_id)}
        </p>
      </section>

      {/* --- 2. SUMMA --------------------------------------------------- */}
      <section className="flex flex-wrap gap-x-8 gap-y-2">
        {/*
         * ⛔ D-09: tarif summasi va hisob summasi TENG bo'lsa ikkinchisi
         *    KO'RSATILMAYDI. Doim ikki bir xil raqam ko'rsatish direktorni
         *    «nima farqi?» deb o'ylashga majburlardi.
         */}
        {adjusted ? (
          <Amount
            label={t("billing.tariffAmount")}
            unit={t("billing.amountUnit")}
            value={format.number(data.tariff_amount_soum)}
          />
        ) : null}
        <Amount
          label={adjusted ? t("billing.chargeAmount") : t("billing.amount")}
          unit={t("billing.amountUnit")}
          value={format.number(data.amount_soum)}
        />
        <Amount
          label={t("billing.outstanding")}
          unit={t("billing.amountUnit")}
          value={format.number(charge.outstanding_soum)}
        />
      </section>

      {/* --- 3. O'ZGARMASLIK JUMLASI — ⛔ SHARTSIZ (D-07) ---------------- */}
      <p className="rounded-md bg-surface-muted px-3 py-2 text-sm">
        {t("billing.immutableNotice")}
      </p>

      {/* --- 4. TUZATISHLAR --------------------------------------------- */}
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">{t("billing.adjustmentsTitle")}</h3>
        {data.adjustments.length === 0 ? (
          /* ⛔ NOL — NATIJA: jumla YASHIRILMAYDI (§11.3, 4-bo'lim). */
          <p className="text-sm text-text-muted">{t("billing.noAdjustments")}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.adjustments.map((adjustment) => (
              <AdjustmentRow adjustment={adjustment} key={adjustment.adjustment_id} />
            ))}
          </ul>
        )}
      </section>

      {/* --- 5. DALIL KADRLARI ------------------------------------------ */}
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">{t("billing.evidenceTitle")}</h3>
        <ul className="flex flex-col gap-3">
          {data.evidence.map((item, index) => (
            <EvidenceRow
              item={item}
              key={`${item.slot_time}-${item.snapshot_id ?? index}`}
            />
          ))}
        </ul>
      </section>
    </div>
  );
}

function Amount({
  label,
  unit,
  value,
}: {
  label: string;
  unit: string;
  value: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-xs text-text-muted">{label}</p>
      <p className="text-sm font-semibold">
        <span className="font-mono tabular-nums">{value}</span> {unit}
      </p>
    </div>
  );
}

/**
 * Bitta tuzatish yozuvi — sabab TARJIMA QILINGAN, aktor ismi KLIENTDA join.
 *
 * ⛔ Ism moliyaviy marshrutdan SO'RALMAYDI (§5.5, C-10): u mavjud va
 *    AUDIT QILINGAN `GET /users` dan olinadi, ya'ni `PERSONAL_ROUTES`
 *    reyestri o'smaydi.
 */
function AdjustmentRow({ adjustment }: { adjustment: ChargeAdjustment }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone();
  const users = useUsersQuery();

  const actor =
    users.data?.items.find((user) => user.id === adjustment.actor_user_id) ??
    null;

  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-border px-3 py-2">
      <Badge tone={adjustment.direction === "increase" ? "warning" : "neutral"}>
        {adjustment.direction === "increase"
          ? t("billing.increase")
          : t("billing.decrease")}
      </Badge>

      <span className="font-mono text-sm tabular-nums">
        {format.number(adjustment.amount_soum)}
      </span>
      <span className="text-sm">{t("billing.amountUnit")}</span>

      {/* ⛔ Sabab-kod TARJIMA QILINADI — xom identifikator ekranga chiqmaydi. */}
      <span className="text-sm text-text-muted">
        {t(`collect.adjustmentReason.${adjustment.reason_code}`)}
      </span>

      {/*
       * ⚠ Ism topilmasa qator YO'QOLMAYDI — u tuzatishning O'ZI haqidagi
       *   yozuv. Ism o'rniga hech nima ko'rsatilmaydi: to'qilgan «Noma'lum
       *   foydalanuvchi» matni bo'lmagan faktni bor qilardi.
       */}
      {actor?.full_name === undefined || actor.full_name === null ? null : (
        <span className="text-sm">{actor.full_name}</span>
      )}

      <span className="text-xs text-text-muted">
        {formatInstant(
          format,
          new Date(adjustment.created_at),
          locale,
          timeZone,
          "short",
        )}
      </span>
    </li>
  );
}

/**
 * Bitta dalil kadri.
 *
 * ⛔⛔ `snapshot_id === null` -> BU QATOR UMUMAN CHIZILMAYDI. Na
 *     platsholder, na «yuklanmadi», na bo'sh ramka. Marshrut kadr
 *     bermagan bo'lsa, ekran ham hech narsa DA'VO QILMAYDI (05-14).
 */
function EvidenceRow({ item }: { item: ChargeEvidence }) {
  if (item.snapshot_id === null) return null;
  return <EvidenceFrame slotTime={item.slot_time} snapshotId={item.snapshot_id} />;
}

function EvidenceFrame({
  slotTime,
  snapshotId,
}: {
  slotTime: string;
  snapshotId: string;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const image = useEvidenceImageHref(snapshotId);

  return (
    <li className="flex flex-col gap-1">
      <p className="font-mono text-xs tabular-nums text-text-muted">
        {format.dateTime(new Date(slotTime), { timeStyle: "short" })}
      </p>

      {image.href === null ? (
        <div aria-busy={image.isPending} role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-40" />
        </div>
      ) : (
        /*
         * ⛔ RAMKA — `bg-text` letterbox + `text-bg` (15,6:1)
         *    [MEROS: 03-UI-SPEC §2.3]. Kadr nisbati saqlanadi
         *    (`object-contain`), ya'ni dalil cho'zilmaydi.
         */
        <div className="flex justify-center overflow-hidden rounded-md bg-text text-bg">
          {/*
           * ⚠ `next/image` ISHLATILMAYDI (`evidence-frame.tsx:217` naqshi):
           *   manba — brauzer ichidagi vaqtinchalik havola, ya'ni Next
           *   optimizatorining hech qanday foydasi yo'q va u havolani
           *   TASHQI so'rovga aylantirardi.
           */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt={t("billing.evidenceTitle")}
            className="max-h-64 w-auto object-contain"
            src={image.href}
          />
        </div>
      )}
    </li>
  );
}
