"use client";

import { BellRing, Receipt, RotateCcw, Sunrise, Sunset } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { DeliveryBadge } from "@/components/reconciliation/delivery-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { DELIVERY_STATES, NOTIFICATION_KINDS } from "@/lib/api-types";
import type { DeliveryStateValue, NotificationKindValue } from "@/lib/api-types";
import { deliveryErrorCode } from "@/lib/reconciliation-errors";
import type {
  DeliveryList as DeliveryListResponse,
  DeliveryRow,
} from "@/lib/reconciliation-queries";
import { formatBusinessDay } from "@/lib/format-day";
import {
  isNotificationKind,
  useDeliveries,
  useReconciliationMarketId,
} from "@/lib/reconciliation-queries";
import { useVendorLabels } from "@/lib/vendor-labels";

/*
 * =============================================================================
 * F BLOKI — XABAR YETKAZILISHI (BOT-04, §11.3).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. XABARNING TANASI JADVALDA ⛔ YO'Q — VA U «SIG'MAY QOLGANI» EMAS
 * -----------------------------------------------------------------------
 * Kvitansiya matnida ⛔ SUMMA va RASTA KODI bor. Ularni bu jadvalda
 * takrorlash ⛔ IKKINCHI PUL YUZASI bo'lardi: direktor undan yig'indi
 * chiqarardi va o'sha son hisobot blokidagi son bilan ⛔ AJRALIB
 * KETARDI — ya'ni ekranda «ikki xil haqiqat».
 *
 * ⛔ Va bu shunchaki qoida emas, ⛔ MEXANIKA: matn qatorda ⛔ UMUMAN
 *    SAQLANMAYDI (u `kind` + `payload` dan JO'NATISH paytida quriladi),
 *    ya'ni marshrut uni bera olmaydi ham.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. TAFSILOT DIALOGI ⛔ QURILMAYDI — JADVALNING O'ZI TO'LIQ
 * -----------------------------------------------------------------------
 * Qatorda ko'rsatilishi mumkin bo'lgan HAMMA narsa allaqachon ustunda:
 * vaqt, tur, sotuvchi, holat, urinishlar va xato TURI. Dialog ochilsa,
 * u ⛔ BO'SH bo'lardi yoki uni «to'ldirish» uchun xabar matni kerak
 * bo'lardi — ya'ni 1-band buzilardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. `[Qayta yuborish]` VA `[Bloklashni yechish]` ⛔ QURILMAYDI
 * -----------------------------------------------------------------------
 * Uchta mustaqil sabab:
 *   (a) navbat ⛔ O'ZI qayta uradi (backoff) — qo'lda urinish
 *       mexanizmning IKKINCHI nusxasi bo'lardi;
 *   (b) qo'lda yuborish idempotentlik kalitiga TO'QNASHARDI yoki uni
 *       aylanib o'tib sotuvchiga ⛔ IKKINCHI KVITANSIYA yuborardi;
 *   (c) aloqa uzilganda qayta urinish ⛔ TA'RIFAN foydasiz.
 *
 * ⛔ Serverda ham bu yo'l ⛔ UMUMAN OCHILMAGAN: yetkazilganlik
 *    marshrutida faqat o'qish metodi bor va u OpenAPI ustidan
 *    o'lchanadi. Ya'ni tugma yozilsa, u ⛔ MURojaat qiladigan marshrut
 *    topolmasdi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. BESHALA HISOBLAGICH NOL BO'LGANDA HAM CHIZILADI
 * -----------------------------------------------------------------------
 * Sikl ⛔ REYESTR ustidan yuradi (D-32), ya'ni «nolmaslarini ko'rsatish»
 * sharti umuman yo'q: yo'qolgan sanoq «bugun aloqa uzilmagan» bilan
 * «hisoblagich ishlamayapti» ni mexanik ravishda BIR XIL ko'rsatardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 5. `blocked` — MA'LUMOT, XATO EMAS (D-22)
 * -----------------------------------------------------------------------
 * Yolg'iz nishon «texnik nosozlik» deb o'qilardi, shuning uchun blok
 * bo'lgan kunda ⛔ TO'LIQ JUMLA va ⛔ KEYINGI QADAM matn sifatida
 * ko'rsatiladi. ⛔ Bu ⛔ TAKLIF, tugma EMAS: ilova ichida qiladigan ish
 * YO'Q va tugma mavjud bo'lmagan imkoniyatni va'da qilardi.
 * ⛔ `role="alert"` ham YO'Q — bu shoshilinch xato emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ 6. AVTOMATIK YANGILANISH YO'Q, `[Yangilash]` BOR
 * -----------------------------------------------------------------------
 * Taymer bilan JIMGINA o'zgaradigan raqam «men boshqa raqam ko'rgandim»
 * nizosini tug'dirardi. Yangilash — foydalanuvchining ⛔ OCHIQ NIYATI,
 * va u ⛔ `aria-live="polite"` O'RAMI bilan e'lon qilinadi (skrinrider
 * foydalanuvchisi o'zgarishni ESHITADI).
 *
 * ⛔ E'LON `<dl>` NING O'ZIGA QO'YILMAYDI: `role="status"` uning implicit
 *    rolini ALMASHTIRIB, `<dt>`/`<dd>` bog'lanishini yo'q qilardi (WR-08).
 *    O'ram esa ikkalasini ham saqlaydi. ⛔ Va bu yuzadagi ⛔ YAGONA doimiy
 *    jonli hudud: qo'shni uch blokda foydalanuvchi boshlaydigan yangilash
 *    YO'Q, ya'ni ular e'lonni hech kim kutmagan paytda berardi.
 *
 * ⚠ `[Yangilash]` FAQAT BUGUN chiziladi: o'tgan kunning yetkazilganligi
 *   ⛔ O'ZGARMAS va tugma hech nima qilmasdi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 7. RO'YXAT 50 QATORDA ⛔ QIRQILMAYDI (B-6)
 * -----------------------------------------------------------------------
 * Marshrut `next_cursor` qaytaradi va u bir muddat ⛔ HECH KIM TOMONIDAN
 * o'qilmasdi. Kvitansiya soni kunlik to'lov soniga TENG — Karmana
 * konvertida 50 dan oshishi ODATIY hol, ya'ni jadval kunning bir qismini
 * ko'rsatib, sanoq esa BUTUNINI aytib turardi.
 *
 * ⛔ `[Yana yuklash]` — `[Yangilash]` DAN ALOHIDA: biri ekrandagini QAYTA
 *    so'raydi, ikkinchisi KEYINGISINI qo'shadi.
 * =============================================================================
 */

/*
 * =============================================================================
 * ⛔⛔ VAQT FORMATI — AYNIQ RAQAMLI MAYDONLARDAN, `dateStyle` DAN EMAS.
 *
 * `dateStyle: "short"` CLDR SKELETINI tanlaydi va locale yechilmaganda
 * ILDIZ (root) namunasiga tushadi — o'shanda oy `M08` shaklidagi NOM bo'lib
 * chiqadi va ekranda «2026 M08 15» paydo bo'ladi (Kamchilik №1 ning aynan
 * mexanikasi).
 *
 * ⛔ Ayniq raqamli maydonlar bilan oy NOMI STRUKTURAVIY IMKONSIZ: chiqishda
 *    faqat raqam va ajratgich bo'lishi mumkin; ajratgich va tartib esa
 *    locale ixtiyorida QOLADI (ular tarjima qilinadigan qaror).
 *
 * ⛔ `hour12: false` MAJBURIY: usiz zaxira locale `AM`/`PM` HARFLARINI
 *    qo'shib, harfsizlik darvozasini (`delivery-list.test.tsx`) buzardi.
 *
 * ⚠ BU VAQTINCHALIK YECHIM EMAS, TO'G'RI YECHIM: 8-fazaning umumiy sana
 *   utili kelganda bu ikki obyekt o'sha utilga almashadi va DARVOZA
 *   O'ZGARMAYDI — u formatning SHAKLINI emas, CHIQISHINI o'lchaydi.
 * =============================================================================
 */

/** Bugungi sahifa: faqat soat:daqiqa. */
const TIME_ONLY = {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
} as const;

/** O'tgan kun sahifasi: kun.oy + soat:daqiqa. */
const DATE_TIME = {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
} as const;

/**
 * Sabab qatori chiziladigan YOPIQ to'plam.
 *
 * ⛔ `delivered` CHIQARILGAN: yetib borgan xabarning oldingi urinishdagi
 *    xatosini ko'rsatish muvaffaqiyatni NOSOZLIKKA aylantirardi.
 * ⛔ `blocked` CHIQARILGAN: sababi ALLAQACHON to'liq jumla bilan aytilgan
 *    (yuqoridagi 5-band) va ikkinchi sabab uni texnik nosozlik kabi
 *    ko'rsatardi.
 */
const REASON_STATES: ReadonlySet<string> = new Set(["pending", "sent", "failed"]);

/** Xabar turi -> ikonka. ⛔ `Record<…>` — yangi a'zo `tsc` da qizaradi. */
const KIND_ICON: Record<NotificationKindValue, LucideIcon> = {
  payment_receipt: Receipt,
  overdue_reminder: BellRing,
  digest_morning: Sunrise,
  digest_evening: Sunset,
};

/** Holat -> envelope'dagi ALOHIDA sanoq. ⛔ Yig'indi maydoni YO'Q. */
const STATE_COUNT: Record<
  DeliveryStateValue,
  (data: DeliveryListResponse) => number
> = {
  pending: (data) => data.pending_count,
  sent: (data) => data.sent_count,
  delivered: (data) => data.delivered_count,
  /*
   * ⛔ `failed` va `blocked` — IKKI ALOHIDA sanoq va ular
   *   QO'SHILMAYDI (D-22): blok sotuvchining HUQUQI, nosozlik emas.
   */
  failed: (data) => data.failed_count,
  blocked: (data) => data.blocked_count,
};

export function DeliveryList({
  day,
  isToday,
}: {
  day: string;
  isToday: boolean;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const marketId = useReconciliationMarketId();
  const hasMarket = marketId !== null;
  const deliveries = useDeliveries(day, isToday, { enabled: hasMarket });
  const vendors = useVendorLabels({ enabled: hasMarket });

  /* ⛔ Qatorlar BARCHA sahifalardan; sanoqlar esa BIRINCHISIDAN (4-band). */
  const rows = deliveries.rows;
  const counts = deliveries.counts;
  const hasBlocked = (counts?.blocked_count ?? 0) > 0;

  return (
    /* ⛔ Atribut ENG TASHQI elementda va HAR holatda — yuklanishda ham. */
    <div className="flex flex-col gap-3" data-recon-content="delivery">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{t("recon.deliveryTitle")}</h2>

        {/*
         * ⛔ FAQAT BUGUN: o'tgan kunning yetkazilganligi O'ZGARMAS.
         * ⛔ `secondary` — aksent EMAS (§13.3: aksent fonli tugma
         *   fazada AYNAN BITTA va u DL-5 dagi yakuniy amal).
         */}
        {isToday ? (
          <Button
            /*
             * ⛔⛔ `aria-disabled`, ⛔ `disabled` EMAS (IN-04).
             *
             * `disabled` element FOKUSNI YO'QOTADI: yangilanish
             * boshlanishi bilan brauzer fokusni `<body>` ga qaytaradi
             * va klaviatura foydalanuvchisi so'rov tugagan lahzada
             * sahifa BOSHIGA otilib ketardi. `case-detail-dialog.tsx`
             * bu qoidani ALLAQACHON o'rnatgan — bu blok esa unga zid
             * javob berardi, ya'ni bir fazada bir savolga IKKI javob.
             *
             * ⛔ `aria-disabled` bosishni TO'XTATMAYDI (u faqat E'LON
             *    qiladi), shuning uchun to'siq `onClick` ichida ERTA
             *    `return` bilan qo'yiladi (`case-list.tsx` naqshi).
             */
            aria-disabled={deliveries.isFetching}
            className="gap-2"
            onClick={() => {
              if (deliveries.isFetching) return;
              void deliveries.refetch();
            }}
            size="sm"
            variant="secondary"
          >
            <RotateCcw aria-hidden="true" className="size-4" />
            {t("recon.deliveryRefresh")}
          </Button>
        ) : null}
      </div>

      {/* ⛔ BOZORSIZ SESSIYA — NOMLANGAN HOLAT (IN-08, `unpaid-list.tsx` naqshi). */}
      {hasMarket ? null : (
        <div className="flex flex-col gap-1">
          <p className="text-sm">{t("recon.marketMissing")}</p>
          <p className="text-xs text-text-muted">
            {t("recon.marketMissingHint")}
          </p>
        </div>
      )}

      {hasMarket && deliveries.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {/* ⛔ Blok darajasidagi xato — KEYINGI SAHIFANIKIDAN ajratilgan. */}
      {deliveries.isError && !deliveries.isFetchNextPageError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {/*
       * ⛔ BESHALA SANOQ — REYESTRDAN, «nolmaslari» EMAS (4-band).
       *
       * ⛔⛔ JONLI HUDUD ⛔ O'RAMDA, `<dl>` NING O'ZIDA EMAS (WR-08).
       *   `role="status"` `<dl>` ning implicit rolini ALMASHTIRARDI va
       *   `<dt>`/`<dd>` juftligi skrinriderda atama–qiymat bog'lanishini
       *   yo'qotib, oddiy matn oqimiga aylanardi. O'ram esa e'lonni
       *   SAQLAYDI va semantikaga TEGMAYDI.
       *
       * ⛔ VA E'LON FAQAT SHU BLOKDA ASOSLI: `[Yangilash]` —
       *   foydalanuvchining OCHIQ NIYATI, ya'ni u natijani KUTADI.
       *   Qo'shni uch blokda bunday amal YO'Q va o'sha yerda jonli hudud
       *   hech kim kutmagan paytda e'lon qilardi.
       */}
      {counts !== undefined ? (
        <div aria-live="polite">
          <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            {DELIVERY_STATES.map((state) => (
              <div className="flex items-center gap-2" key={state}>
                <dt className="order-2 text-xs text-text-muted">
                  {t(`recon.deliveryState.${state}`)}
                </dt>
                {/* ⛔ `as` assertsiyasi YO'Q (IN-02) — `counts` allaqachon toraytirilgan. */}
                <dd className="order-1 m-0 font-mono tabular-nums">
                  {STATE_COUNT[state](counts)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      {counts !== undefined && rows.length === 0 ? (
        <EmptyState
          /*
           * ⛔ KUN BITTA YORDAMCHI ORQALI (WR-07): qo'shni uch blok ham
           *   AYNI shakldan o'qiydi, ya'ni bir fazada bir maydonning
           *   ikki xil ko'rinishi TUG'ILMAYDI.
           */
          description={t("recon.emptyDeliveryHint", {
            date: formatBusinessDay(format, day, locale),
          })}
          title={t("recon.emptyDelivery")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{t("recon.deliveryTitle")}</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-3 font-normal">{t("recon.timeColumn")}</th>
                <th className="p-3 font-normal">{t("recon.kindColumn")}</th>
                <th className="p-3 font-normal">{t("recon.vendorColumn")}</th>
                <th className="p-3 font-normal">{t("recon.statusColumn")}</th>
                <th className="p-3 font-normal">
                  {t("recon.deliveryAttempts")}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <DeliveryRowView
                  isToday={isToday}
                  key={row.outbox_id}
                  row={row}
                  vendorLabel={vendors.labelOf(row.vendor_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* ⛔ Keyingi sahifa yiqilganda — NOMLANGAN matn (`case-list.tsx` naqshi). */}
      {deliveries.isFetchNextPageError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("recon.loadMoreFailed")}
        </p>
      ) : null}

      {/*
       * ⛔ `[Yana yuklash]` — `[Yangilash]` DAN ALOHIDA JOYDA (jadvaldan
       *   keyin) va ALOHIDA ma'noda: biri ekrandagini QAYTA so'raydi,
       *   ikkinchisi KEYINGISINI qo'shadi. Ularni yonma-yon qo'yish ikki
       *   xil amalni bir xil ko'rsatardi.
       */}
      {deliveries.hasNextPage ? (
        <div>
          <Button
            aria-disabled={deliveries.isFetchingNextPage}
            onClick={() => {
              if (deliveries.isFetchingNextPage) return;
              void deliveries.fetchNextPage();
            }}
            size="sm"
            variant="secondary"
          >
            {t("recon.loadMore")}
          </Button>
        </div>
      ) : null}

      {/*
       * ⛔ `blocked` NING TO'LIQ JUMLASI VA KEYINGI QADAMI (5-band).
       * ⛔ `role="alert"` YO'Q va ⛔ `tone="danger"` fon YO'Q: bu
       *   MA'LUMOT, xato emas. ⛔ TUGMA ham yo'q — ilova ichida
       *   qiladigan ish yo'q.
       */}
      {hasBlocked ? (
        <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm text-text">
          {t("recon.blockedBody")} {t("recon.blockedFix")}
        </p>
      ) : null}
    </div>
  );
}

function DeliveryRowView({
  isToday,
  row,
  vendorLabel,
}: {
  isToday: boolean;
  row: DeliveryRow;
  vendorLabel: string | null;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  /*
   * ⛔ XOM ISTISNO SINFI EKRANGA CHIQMAYDI — u yopiq to'plamga
   *   xaritalanadi (§14.9). `RemoteProtocolError` direktorga hech nima
   *   aytmaydi; «Telegram javob bermadi» esa aytadi.
   *
   * ⛔⛔ SHART YOPIQ TO'PLAM BILAN — VA «`pending` DA XATO HALI YO'Q»
   *     DEGAN ESKI FARAZ O'LCHOV BILAN RAD ETILDI (Topilma №I).
   *     Manzilsiz shox (`outbox_repo.defer_unresolved()`) `last_error_type`
   *     ni YOZADI va holatni `pending` da QOLDIRADI (urinishlar sonini
   *     ham oshirmaydi). Ya'ni eski `status === "failed"` sharti AYNAN
   *     eng uzoq qotib qoladigan sababni ekrandan to'sardi: kvitansiya
   *     18 soat «Navbatda · Urinishlar: 0» bo'lib turardi va nima uchun
   *     turgani hech qayerda ko'rinmasdi.
   */
  const errorCode = REASON_STATES.has(row.status)
    ? deliveryErrorCode(row.error_type, row.error_status_code)
    : null;

  const KindIcon = isNotificationKind(row.kind) ? KIND_ICON[row.kind] : null;

  return (
    /* Qator hover foni (§12.8) — davomiylik `--default-transition-*` dan. */
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3">
        {/*
         * ⛔ NISBIY VAQT YO'Q (§3.5): «5 daqiqa oldin» taymersiz eskiradi.
         *
         * ⛔ SANA FAQAT O'TGAN KUNDA. Jadval `created_at` bo'yicha KUN
         *   FILTRIDA (`outbox_repo._DELIVERY_ROWS`), ya'ni bugungi
         *   sahifada har qator bugungi va sana ORTIQCHA SHOVQIN bo'lardi;
         *   o'tgan kun sahifasida esa u YAGONA aniqlovchi — usiz qator
         *   «12:36» deb turib, qaysi kun ekanini AYTMASDI.
         */}
        {format.dateTime(
          new Date(row.created_at),
          isToday ? TIME_ONLY : DATE_TIME,
        )}
      </td>
      <td className="p-3">
        <span className="inline-flex items-center gap-1">
          {KindIcon === null ? null : (
            <KindIcon aria-hidden="true" className="size-4 text-text-muted" />
          )}
          {isNotificationKind(row.kind)
            ? t(`recon.notificationKind.${row.kind}`)
            : t("recon.notificationKind.unknown")}
        </span>
      </td>
      <td className="p-3">
        {/*
         * ⛔ SOTUVCHI — KLIENTDA joinlangan YORLIQ. Marshrut ism
         *   QAYTARMAYDI va qator uni `vendor_id` bilan aytadi.
         * ⛔ Direktorning xabarida sotuvchi UMUMAN yo'q — bo'sh katak
         *   emas, NOMLANGAN holat.
         */}
        {row.vendor_id === null ? (
          <span className="text-text-muted">{t("recon.recipientDirector")}</span>
        ) : (
          (vendorLabel ?? (
            <span className="text-text-muted">{t("recon.vendorUnknown")}</span>
          ))
        )}
      </td>
      <td className="p-3">
        <div className="flex flex-col gap-1">
          <DeliveryBadge status={row.status} />
          {errorCode === null ? null : (
            <span className="text-xs text-text-muted">
              {t(`recon.deliveryError.${errorCode}`)}
            </span>
          )}
        </div>
      </td>
      <td className="p-3 text-xs text-text-muted">
        {/*
         * ⛔ `font-mono` EMAS (§7.3): urinishlar soni ICHKI MEXANIZM
         *   o'lchovi va u nizoda o'qib aytilmaydi.
         *
         * ⛔ MAXRAJ («2/5») YOZILMAYDI: chegara SERVER konstantasi va u
         *   javobda YO'Q. Uni klientda literal bilan to'qish serverdagi
         *   qiymat o'zgargan kuni JIMGINA yolg'on gapirardi — 05-14 ning
         *   «to'qilgan qiymat» darsi.
         */}
        {row.attempt_count}
      </td>
    </tr>
  );
}
