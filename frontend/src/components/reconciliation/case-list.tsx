"use client";

import { useState } from "react";
import { useFormatter, useLocale, useTimeZone, useTranslations } from "next-intl";

import { CaseDetailDialog } from "@/components/reconciliation/case-detail-dialog";
import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { CASE_STATUSES } from "@/lib/api-types";
import type { CaseStatusValue } from "@/lib/api-types";
import { formatBusinessDay, formatInstantDay } from "@/lib/format-day";
import type {
  CaseList as CaseListResponse,
  CaseRow,
} from "@/lib/reconciliation-queries";
import {
  useReconciliationCases,
  useReconciliationMarketId,
} from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * D BLOKI — NOMUVOFIQLIK NAVBATI (RECON-02, §9.2).
 *
 * -----------------------------------------------------------------------
 * ⛔ 1. «NOMUVOFIQLIK OCHISH» TUGMASI ⛔ QURILMAYDI
 * -----------------------------------------------------------------------
 * Navbat `recon.open` cron'ida ⛔ AVTOMATIK va sinf A uchun kechikish
 * chegarasi bilan tug'iladi. Qo'lda ochish:
 *   (1) ⛔ CHEGARANI AYLANIB O'TARDI — direktor bugungi hisobga navbat
 *       ochib, ertaga to'lov kelganda uni YOPISHGA majbur bo'lardi
 *       (aynan o'sha shovqin uchun chegara qo'yilgan);
 *   (2) ⛔ IDEMPOTENTLIKNI BUZARDI — qisman UNIQUE indeks qo'lda va cron
 *       urinishlari orasida POYGA yaratardi;
 *   (3) direktorning haqiqiy ehtiyoji «buni tezroq ko'ring», ya'ni
 *       MAS'UL biriktirish — yangi qator emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ 2. HOLAT O'ZGARTIRISH BOSHQARUVI BU YERDA YO'Q
 * -----------------------------------------------------------------------
 * Hukm — tafsilot dialogining ishi va u ALOHIDA huquq ostida. Bu blok
 * ⛔ SOF O'QISH: yozuv yuzasi AYNAN NOL.
 *
 * ⛔ `[Ko'rib chiqish]` — `ghost`, ⛔ AKSENT EMAS: u HAR QATORDA
 *    takrorlanadi va aksent fonli bo'lsa sahifada 10-50 ta urg'uli
 *    tugma paydo bo'lardi — 10% chegarasi BUZILARDI. Fazadagi yagona
 *    aksent fonli tugma — tafsilot dialogidagi YAKUNIY amal.
 *
 * ⛔ DIALOG HOLATI URL'DA EMAS: dialogda erkin matnli yechim maydoni
 *    bor va URL'ga chiqarilgan holat YARIM YOZILGAN matn ulashiladigan
 *    havola yaratardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. OMMAVIY AMAL ⛔ QURILMAYDI
 * -----------------------------------------------------------------------
 * Ko'p tanlovli ro'yxat direktorga ⛔ BIR BOSISHDA 50 NOMUVOFIQLIKNI
 * yopish imkonini berardi — bu «hammasini tasdiqlash» dan QIMMATROQ
 * xato, chunki natijasi HUKM va u aniqlik ulushini BUZADI. Hech qanday
 * yechim matni ham qolmasdi.
 *
 * ⚠ Bu katalog o'sha taqiqning mexanik skanidan o'tadi va qamrov
 *   dizayn kontraktining E'LONIDAN hosila qilinadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. TO'RT SANOQ NOL BO'LGANDA HAM KO'RINADI
 * -----------------------------------------------------------------------
 * Sikl ⛔ REYESTR ustidan yuradi (D-32), ya'ni «nolmaslarini ko'rsatish»
 * sharti umuman yo'q: yo'qolgan sanoq «bugun hech nima yopilmadi» bilan
 * «hisoblagich ishlamayapti» ni mexanik ravishda bir xil ko'rsatardi.
 *
 * ⛔ AYNAN SHU TO'RT SANOQDAN aniqlik ulushi ham chiqadi — ⛔ IKKINCHI
 *    SO'ROVSIZ. Ikki so'rov ikki lahzani ko'rsatib, ekranda «ikki xil
 *    raqam» tug'dirardi.
 *
 * ⛔ SANOQ ⛔ BIRINCHI SAHIFADAN o'qiladi va sahifalar bo'ylab
 *    ⛔ YIG'ILMAYDI: server kontrakti bo'yicha u filtrdan ham, sahifadan
 *    ham MUSTAQIL va HAR javobda BUTUN kunning soni bo'lib keladi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 4b. RO'YXAT 50 QATORDA ⛔ QIRQILMAYDI (B-6)
 * -----------------------------------------------------------------------
 * Sanoq kun bo'yicha to'liq, jadval esa bir sahifada 50 qator edi —
 * ya'ni direktor «Yangi 120» yozuvini 50 qatorli jadval ustida ko'rardi
 * va qolgan 70 tasiga ⛔ HECH QANDAY YO'L YO'Q edi. Bu shu faylning O'Z
 * printsipiga («yo'qolgan sanoq — jim xato») ⛔ TO'G'RIDAN-TO'G'RI zid.
 *
 * ⛔ YECHIM — KEYSET KURSOR va `[Yana yuklash]`, ⛔ AVTOMATIK YUKLASH
 *    EMAS: skroll bilan o'zi yuklanadigan ro'yxat direktor «oxiriga
 *    yetdim» deb o'ylagan paytda ham o'sib turardi va u nechta qator
 *    ko'rganini BILMASDI. Yuklash — foydalanuvchining OCHIQ NIYATI.
 *
 * -----------------------------------------------------------------------
 * ⚠⚠ 5. SOTUVCHI USTUNI ⛔ YO'Q — DIZAYN KONTRAKTIDAN ASOSLI CHETLANISH
 * -----------------------------------------------------------------------
 * Kontrakt bu jadvalga «Sotuvchi (klientda join)» ustunini yozgan, lekin
 * 07-10 ning SHIPLANGAN `CaseRowResponse` ida sotuvchi identifikatori
 * ⛔ UMUMAN YO'Q — qator faqat case, nishon (anomaliya YOKI hisob), sana,
 * holat, mas'ul va ochilish vaqti bilan keladi. Server docstringi buni
 * ochiq aytadi: rasta kodi, sotuvchi va summa navbat qatorida EMAS,
 * chunki ularni ko'chirish navbatni ⛔ IKKINCHI HAQIQAT MANBAIGA
 * aylantirardi.
 *
 * ⛔ SHUNING UCHUN USTUN QO'SHILMAYDI, «—» BILAN HAM: to'qilgan yoki
 *    doim bo'sh ustun 4-fazadagi «bo'sh katak» sinfidagi jim xato
 *    bo'lardi (05-14 darsi). Sotuvchi hisobot bloklarida KO'RINADI va
 *    o'sha yerda u HAQIQIY ma'lumot bilan keladi.
 * =============================================================================
 */

/** Holat -> envelope'dagi ALOHIDA sanoq. ⛔ Yig'indi maydoni YO'Q. */
const STATUS_COUNT: Record<
  CaseStatusValue,
  (data: CaseListResponse) => number
> = {
  new: (data) => data.new_count,
  in_review: (data) => data.in_review_count,
  justified: (data) => data.justified_count,
  unjustified: (data) => data.unjustified_count,
};

export function CaseList({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const marketId = useReconciliationMarketId();
  const hasMarket = marketId !== null;
  const cases = useReconciliationCases(day, { enabled: hasMarket });

  /* ⛔ Dialog holati SHU YERDA, URL'da EMAS (modul izohining 2-bandi). */
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);

  /* ⛔ Qatorlar BARCHA sahifalardan; sanoqlar esa BIRINCHISIDAN (4-band). */
  const rows = cases.rows;
  const counts = cases.counts;

  return (
    /* ⛔ Atribut ENG TASHQI elementda va HAR holatda — yuklanishda ham. */
    <div className="flex flex-col gap-3" data-recon-content="cases">
      <h2 className="text-lg font-semibold">{t("recon.casesTitle")}</h2>

      {/* ⛔ BOZORSIZ SESSIYA — NOMLANGAN HOLAT (IN-08, `unpaid-list.tsx` naqshi). */}
      {hasMarket ? null : (
        <div className="flex flex-col gap-1">
          <p className="text-sm">{t("recon.marketMissing")}</p>
          <p className="text-xs text-text-muted">
            {t("recon.marketMissingHint")}
          </p>
        </div>
      )}

      {hasMarket && cases.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {/*
       * ⛔ BLOK DARAJASIDAGI XATO — KEYINGI SAHIFANIKIDAN AJRATILGAN.
       *   Sahifa yuklanmagani «butun blok yiqildi» degani EMAS: qatorlar
       *   ham, sanoq ham ekranda TURADI. Ikkalasini bir matn bilan
       *   ko'rsatish direktorga ro'yxat BUTUNLAY yo'q deb aytardi.
       */}
      {cases.isError && !cases.isFetchNextPageError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {/*
       * ⛔ `role` YO'Q (WR-08): `role="status"` `<dl>` ning implicit rolini
       *   ALMASHTIRADI va «Yangi 120 Ko'rilmoqda 7» skrinriderda
       *   atama–qiymat bog'lanishini yo'qotib, oddiy matn oqimiga
       *   aylanardi.
       *
       * ⛔ JONLI HUDUD HAM YO'Q: bu blokda foydalanuvchi BOSHLAYDIGAN
       *   yangilash yo'q, ya'ni e'lon faqat sahifa yuklanganda — hech kim
       *   kutmagan paytda — sodir bo'lardi. Jonli hudud AYNAN BITTA
       *   joyda: `[Yangilash]` tugmasi bor yetkazilganlik blokida.
       */}
      {counts !== undefined ? (
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {CASE_STATUSES.map((status) => (
            <div className="flex items-center gap-2" key={status}>
              <dt className="order-2 text-xs text-text-muted">
                {t(`recon.caseStatus.${status}`)}
              </dt>
              {/*
               * ⛔ `as` ASSERTSIYASI YO'Q (IN-02): `counts` yuqoridagi
               *   `!== undefined` shoxi bilan ALLAQACHON toraytirilgan va
               *   assertsiya `strict` rejimda kelajakdagi HAQIQIY tur
               *   xatosini ⛔ YASHIRARDI.
               */}
              <dd className="order-1 m-0 font-mono tabular-nums">
                {STATUS_COUNT[status](counts)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {counts !== undefined && rows.length === 0 ? (
        <EmptyState
          description={t("recon.emptyCasesHint", {
            date: formatBusinessDay(format, day, locale),
          })}
          title={t("recon.emptyCases")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{t("recon.casesTitle")}</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-3 font-normal">{t("recon.subjectColumn")}</th>
                <th className="p-3 font-normal">{t("recon.statusColumn")}</th>
                <th className="p-3 font-normal">
                  {t("recon.assigneeColumn")}
                </th>
                <th className="p-3 font-normal">{t("recon.openedColumn")}</th>
                <th className="p-3 font-normal">
                  <span className="sr-only">{t("recon.caseReview")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <CaseRowView
                  key={row.case_id}
                  onReview={() => setOpenCaseId(row.case_id)}
                  row={row}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/*
       * ⛔ KEYINGI SAHIFA YIQILGANDA — NOMLANGAN MATN, JIM BO'SH SAHIFA
       *   EMAS. 07-20 o'lchagan: buzilgan kursor bazada `200` + BO'SH
       *   `rows` qaytarardi (ya'ni ekran JIMGINA yolg'on gapirardi); endi
       *   u `422`. Klient uni KO'RSATADI va allaqachon kelgan qatorlar
       *   ⛔ JOYIDA QOLADI.
       */}
      {cases.isFetchNextPageError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("recon.loadMoreFailed")}
        </p>
      ) : null}

      {/*
       * ⛔ TUGMA `next_cursor === null` DA UMUMAN CHIZILMAYDI (o'chirilgan
       *   emas): mavjud lekin ishlamaydigan boshqaruv MAVJUD BO'LMAGAN
       *   imkoniyatni e'lon qilardi.
       *
       * ⛔ `secondary`, `default` EMAS: fazadagi yagona aksent fonli tugma
       *   — DL-5 dagi yakuniy amal (§13.3).
       */}
      {cases.hasNextPage ? (
        <div>
          <Button
            aria-disabled={cases.isFetchingNextPage}
            onClick={() => {
              /*
               * ⛔ ERTA `return` — `aria-disabled` bosishni TO'XTATMAYDI
               *   (u faqat E'LON QILADI). `disabled` esa fokusni
               *   YO'QOTARDI va klaviatura foydalanuvchisi yuklanish
               *   tugagan lahzada sahifa boshiga otilib ketardi.
               */
              if (cases.isFetchingNextPage) return;
              void cases.fetchNextPage();
            }}
            size="sm"
            variant="secondary"
          >
            {t("recon.loadMore")}
          </Button>
        </div>
      ) : null}

      <CaseDetailDialog
        caseId={openCaseId}
        onOpenChange={(open) => {
          if (!open) setOpenCaseId(null);
        }}
      />
    </div>
  );
}

function CaseRowView({
  onReview,
  row,
}: {
  onReview: () => void;
  row: CaseRow;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const timeZone = useTimeZone();
  const locale = useLocale();

  return (
    /*
     * §10.5 [L-5] — CASE QATORI CHETDAN SIRG'ALIB KIRADI: `starting:`
     * (`@starting-style`) + `transition-transform` + `--motion-slow`
     * (400ms) — `ui/dialog.tsx` ning O'LCHANGAN presedenti (09-02 T1:
     * Tailwind 4.3.3 `starting:` ni `@starting-style` ga kompilyatsiya
     * qiladi). `@keyframes` reyestri YOPIQ (8 nom, `globals.css` 09-01
     * egaligida) — yangi keyframe ochilmaydi, kirish TRANZITSIYA bilan
     * (09-05 sparkline qarori bilan ayni sinf).
     *
     * ⛔ Tranzitsiya transform OILASI bilan chegaralangan
     *    (`transition-transform`) — hover fon rangi bu 400ms ga TUSHMAYDI:
     *    hover `group-hover` orqali kataklarda o'z `transition-colors`
     *    (150ms standart token) bilan yashaydi. Qator darajasida
     *    `hover:bg-*` yozilsa fon ham 400ms sirg'alardi — ikki savolga
     *    bitta davomiylik bo'lardi.
     *
     * ⚠ Reduced-motion: global blok (09-01) tranzitsiyani 0.01ms ga
     *   tushiradi — qator darhol joyida, natija ayni.
     * ⛔ FLIP / saralash animatsiyasi YO'Q (§12.8): sahifalash va tartib
     *   serverniki, qatorlar qayta terilganda ular sirg'alib O'YNAMAYDI —
     *   `@starting-style` faqat elementning BIRINCHI renderida ishlaydi.
     */
    <tr className="group border-b border-border transition-transform duration-(--motion-slow) last:border-b-0 starting:-translate-x-2">
      <td className="relative p-3 transition-colors group-hover:bg-surface-muted">
        {/*
          * §10.5 — AMBER DIQQAT-HALQA, BIR MARTA: faqat `new` (amber)
          * holatdagi case. `.motion-attention` (09-01 reyestri):
          * box-shadow 0 -> 10px shaffof, `--motion-slow`,
          * `animation-iteration-count: 1` — ⛔ qayta pulsatsiya YO'Q.
          * ⛔ Halqa `aria-hidden` BEZAK: holatni `CaseStatusBadge` MATN
          *   bilan aytadi — rang yolg'iz signal emas (WCAG 1.4.1).
          * ⚠ `<tr>` ustida emas, katak ICHIDAGI absolut span ustida:
          *   `border-collapse` jadvalda qator box-shadow'i brauzerlarda
          *   ishonchsiz chiziladi; katak esa `relative` bo'la oladi.
          */}
        {row.status === "new" ? (
          <span
            aria-hidden="true"
            className="motion-attention pointer-events-none absolute inset-1 rounded-sm"
          />
        ) : null}
        {row.subject_kind === "occupied_unpaid"
          ? t("recon.unpaidTitle")
          : t("recon.unregisteredTitle")}
      </td>
      <td className="p-3 transition-colors group-hover:bg-surface-muted">
        <CaseStatusBadge status={row.status} />
      </td>
      <td className="p-3 transition-colors group-hover:bg-surface-muted">
        {/*
         * ⛔ MAS'UL — IDENTIFIKATOR, ISM EMAS. Ismni qo'shish uchun
         *   foydalanuvchilar reestrini ham tortish kerak bo'lardi; u
         *   tafsilot dialogi bilan birga keladi (07-16). Bugun `null`
         *   HOLAT sifatida NOMLANADI — bo'sh katak jim xato bo'lardi.
         */}
        {row.assignee_user_id === null ? (
          <span className="text-text-muted">{t("recon.assigneeNone")}</span>
        ) : (
          <span className="font-mono text-xs">
            {row.assignee_user_id.slice(0, 8)}
          </span>
        )}
      </td>
      <td className="p-3 transition-colors group-hover:bg-surface-muted">
        {formatInstantDay(format, new Date(row.created_at), locale, timeZone)}
      </td>
      <td className="p-3 transition-colors group-hover:bg-surface-muted">
        {/* ⛔ `ghost` — har qatorda takrorlanadigan amal AKSENT olmaydi. */}
        <Button onClick={onReview} size="sm" variant="ghost">
          {t("recon.caseReview")}
        </Button>
      </td>
    </tr>
  );
}
