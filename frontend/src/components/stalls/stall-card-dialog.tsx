"use client";

import type { ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { formatSoum } from "@/lib/format-number";

import { EvidenceLink } from "@/components/reconciliation/evidence-link";
import { StallStatusBadge } from "@/components/stalls/stall-list";
import { DAY_STATE_KEYS } from "@/components/stalls/stall-tone";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { StallDetail } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import type { MapDayRow } from "@/lib/map-day-queries";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useStallQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";
import { useCaseDetail } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * Rasta kartasi — BITTA modal `<Dialog>`, tanlangan ID sahifa holatida
 * (UI-SPEC §7.6).
 *
 * RAD ETILGAN MUQOBILLAR:
 *   har katakka o'z suzuvchi     -> 1000 ta Radix portali; zich gridda
 *   oynachasi                       pozitsiyalash ekran chekkasiga urilardi.
 *                                   (Radix'ning o'sha primitivi NOMI bu
 *                                   yerda literal yozilmaydi — taqiq
 *                                   mexanik grep darvozasi bilan
 *                                   qulflangan, kodbaza konvensiyasi.)
 *   yon panel (drawer)           -> yangi layout primitivi; <=768px da
 *                                   gridni siqib qo'yardi;
 *   qator ichida kengayish       -> `auto-fill` tartibini yorib yuborardi;
 *   alohida marshrut `/stalls/id`-> xaritadagi skroll pozitsiyasi yo'qolardi.
 *
 * ⚠ TANLANGAN ID KATAKNING PROPIGA TUSHMAYDI (Pitfall 8). U sahifa
 * holatida yashaydi va faqat SHU dialog uni o'qiydi — aks holda har
 * bosishda 1000 katak qayta render bo'lardi. Qo'shimcha foyda: katak qayta
 * render bo'lmagani uchun dialog yopilganda fokus AYNAN bosilgan katakka
 * qaytadi (trigger DOM'da qolgan).
 * =============================================================================
 */

export type StallCardProps = {
  stallId: string | null;
  onClose: () => void;
  /**
   * 6–7 fazalar: dalil-rasm galereyasi shu yerga tushadi. 2-fazada
   * `undefined` — galereya, lightbox va rasm yuklash bu fazada
   * QURILMAYDI (Scope Fence). Bitta prop, nol infratuzilma.
   */
  children?: ReactNode;
  /**
   * `stall_manage` huquqi. Amal tugmalari faqat shu bilan render qilinadi
   * — bu UI KO'ZGUSI, xavfsizlik chegarasi EMAS (T-02-109).
   */
  canManage?: boolean;
  /** Berilmasa "Tahrirlash" tugmasi render qilinmaydi. */
  onEdit?: (stallId: string) => void;
};

export function StallCardDialog({
  canManage = false,
  children,
  onClose,
  onEdit,
  stallId,
}: StallCardProps) {
  const t = useTranslations();
  const stallQuery = useStallQuery(stallId);
  const stall = stallQuery.data;

  return (
    <Dialog.Root
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      open={stallId !== null}
    >
      {/*
       * `sheetOnMobile` — `<640px` da pastki varaq (§7.6). Faqat CSS:
       * ikkinchi komponent ham, ikkinchi bog'liqlik ham qo'shilmaydi.
       */}
      <Dialog.Content
        description={t("stalls.cardHint")}
        sheetOnMobile
        size="lg"
        srOnlyDescription
        title={
          <span className="flex flex-wrap items-center gap-3">
            {/* D-16: rasta raqami DB kontenti — tarjima qilinmaydi. */}
            <span className="font-mono text-xl tabular-nums">
              {stall?.code ?? ""}
            </span>
            {stall ? <StallStatusBadge status={stall.status} /> : null}
          </span>
        }
      >
        {stallQuery.isPending ? (
          <div aria-busy="true" className="flex flex-col gap-2" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-24 rounded-lg" />
          </div>
        ) : null}

        {stallQuery.isError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {t(marketErrorMessageKey(stallQuery.error))}
          </p>
        ) : null}

        {stall ? (
          <StallCardBody canManage={canManage} onEdit={onEdit} stall={stall} />
        ) : null}

        {/*
         * BUGUNGI HOLAT — ⛔ RASTA MA'LUMOTI KELGANDAN KEYIN.
         *
         * `stallId !== null` sharti hookni SHARTLI qilmaydi: bo'lim
         * ALOHIDA komponent va u umuman mount BO'LMAGANDA hook ham
         * chaqirilmaydi. Ichkarida esa hamma hook SHARTSIZ ishlaydi.
         */}
        {stall ? <StallDayStatus stallId={stall.id} /> : null}

        {children}
      </Dialog.Content>
    </Dialog.Root>
  );
}

/**
 * Yo'q summaning NOMLANGAN sababi -> tarjima kaliti.
 *
 * ⛔ TO'LIQ `Record`, `switch` + `default` EMAS: serverga uchinchi sabab
 *    qo'shilsa kod KOMPILYATSIYA BO'LMAYDI. `default` bo'lganda yangi
 *    sabab jimgina «sababsiz» bo'lib chizilardi — D-20 aynan buni
 *    taqiqlaydi.
 */
const DAY_REASON_KEYS: Record<
  NonNullable<MapDayRow["unavailable_reason"]>,
  | "map.dayReasonMarketClosed"
  | "map.dayReasonTariffMissing"
  | "map.dayReasonFairStall"
  | "map.dayReasonStallClosed"
  | "map.dayReasonStallMaintenance"
> = {
  market_closed: "map.dayReasonMarketClosed",
  tariff_missing: "map.dayReasonTariffMissing",
  // 0028 — to'liq Record o'z ishini qildi: yangi sabab kompilyatsiyada ushlandi.
  fair_stall: "map.dayReasonFairStall",
  // 2026-08-25: yopiq/ta'mirda ham «olinmaydi» sinfida.
  stall_closed: "map.dayReasonStallClosed",
  stall_maintenance: "map.dayReasonStallMaintenance",
};

/**
 * ⛔⛔ «BUGUNGI HOLAT» — MA'LUMOT YO'Q BO'LSA BO'LIM **UMUMAN CHIZILMAYDI**.
 *
 * =============================================================================
 * Uch holatda bo'lim `null` qaytaradi va ⛔ NA PLATSHOLDER, NA TIRE, NA NOL
 * qoldiradi (05-14 darsi):
 *
 *   1. ko'ruvchida `billing_collect_view` YO'Q — so'rov ham ketmaydi (D-C4);
 *   2. bozor QORALAMA — server `rows: []` beradi va indeks bo'sh qoladi;
 *   3. bu rastaning qatori umuman kelmadi.
 *
 * «Ma'lumot yo'q» ni nol bilan ko'rsatish «bugun hech kim to'lamadi» degan
 * YOLG'ON da'vo bo'lardi — mahsulot aynan shu sinfdagi yolg'onni fosh
 * qilish uchun mavjud.
 *
 * =============================================================================
 * ⛔ IKKINCHI SO'ROV KETMAYDI: xaritadan ochilganda `useMapDayStatusQuery()`
 *    AYNI kesh yozuvini o'qiydi (kalit `domainKey(marketId, "map-day")`),
 *    ya'ni karta o'z nusxasini tortmaydi. Kartani boshqa yuzadan ochish
 *    esa bitta so'rov qiladi va bu to'g'ri.
 *
 * ⛔ PUL ARIFMETIKASI YO'Q: uchala son ham SERVERDAN (`amount_soum`,
 *    `paid_soum`, `remaining_soum`). Qoldiqni bu yerda ayirish katakning
 *    rangi bilan kartadagi sonni IKKI BOSHQA hisobdan chiqarardi.
 * =============================================================================
 */
function StallDayStatus({ stallId }: { stallId: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const { principal } = useAuthStore();
  const dayLayer = useMapDayStatusQuery();

  const row = dayLayer.byStallId.get(stallId) ?? null;

  /*
   * ⚠ HOOK SHARTSIZ CHAQIRILADI, `enabled` bilan boshqariladi: `report_view`
   *   `GET /reconciliation/cases/{id}` ning KO'ZGUSI. Huquqsiz rolda
   *   so'rov ketmaydi va dalil bo'limi ham chizilmaydi.
   */
  const roles = principal?.roles ?? [];
  const caseQuery = useCaseDetail(row?.open_case_id ?? null, {
    enabled: hasPermission(roles, "report_view"),
  });

  if (row === null) return null;

  /*
   * ⛔⛔ `Intl` VALYUTA USLUBI EMAS — `formatSoum` (260820, ekranda ko'rildi).
   *
   *     `style: "currency"` ekranda «UZS 10,000» beradi: ISO kodi va
   *     VERGUL bilan guruhlash. Mahsulotning qolgan hamma joyida esa
   *     «10 000 so'm» — ingichka bo'sh joy va o'zbekcha so'z. Bitta
   *     ekranda ikki xil pul formati — ma'muriyat uchun ikki xil tizim
   *     taassuroti.
   */
  const money = (value: number) => formatSoum(format, value, locale);

  const evidenceIds = caseQuery.data?.evidence_snapshot_ids ?? [];

  return (
    <section className="flex flex-col gap-2 border-t border-border pt-4">
      <h3 className="text-sm font-semibold">{t("map.dayStatusTitle")}</h3>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <dt className="text-text-muted">{t("map.dayStatusState")}</dt>
        {/*
         * ⛔ YORLIQ XARITA KATAGI BILAN AYNI KALITDAN (`DAY_STATE_KEYS`):
         *   ikkinchi lug'at yozilsa katakda bir so'z, kartada boshqasi
         *   ko'rinardi va foydalanuvchi ularni ikki xil holat deb
         *   o'qirdi (G-24 ning aynan sinfi).
         */}
        <dd className="font-semibold">{t(DAY_STATE_KEYS[row.state])}</dd>

        <dt className="text-text-muted">{t("map.dayStatusAmount")}</dt>
        <dd className="font-semibold tabular-nums">
          {row.amount_soum === null ? (
            /*
             * ⛔ SABAB SO'Z BILAN, TIRE BILAN EMAS: «summa yo'q» bilan
             *   «nega yo'q» ni ajratmaydigan belgi kassirni ham, adminni
             *   ham tuzatib bo'lmaydigan holatga tashlardi (§9.4).
             */
            <span className="font-normal text-text-muted">
              {row.unavailable_reason === null
                ? null
                : t(DAY_REASON_KEYS[row.unavailable_reason])}
            </span>
          ) : (
            money(row.amount_soum)
          )}
        </dd>

        <dt className="text-text-muted">{t("map.dayStatusPaid")}</dt>
        {/* ⚠ NOL ham NATIJA: «bugun hali to'lanmadi» — ma'lumot yo'qligi emas. */}
        <dd className="font-semibold tabular-nums">{money(row.paid_soum)}</dd>

        {/*
         * ⛔ QOLDIQ QATORI FAQAT HISOB BOR KUNDA: hisob yo'q kunda
         *   «qolgan qarz» MA'NOSIZ va nol uni «to'liq to'langan» bilan
         *   bir xil ko'rsatardi. Server buni `null` bilan aytadi.
         */}
        {row.remaining_soum === null ? null : (
          <>
            <dt className="text-text-muted">{t("map.dayStatusRemaining")}</dt>
            <dd className="font-semibold tabular-nums">
              {money(row.remaining_soum)}
            </dd>
          </>
        )}

        {/*
         * ⛔ CASE SANASI — «BUGUN» DEB TAXMIN QILINMAYDI: ochiq
         *   nomuvofiqlik kechagi kunniki bo'lishi mumkin (server uni kun
         *   bo'yicha filtrlamaydi) va uni bugungi deb ko'rsatish YOLG'ON
         *   bo'lardi. Xom ISO sana — `case-detail-dialog.tsx:257` dagi
         *   naqshning aynan o'zi.
         */}
        {row.open_case_service_date === null ? null : (
          <>
            <dt className="text-text-muted">{t("map.dayStatusCaseDate")}</dt>
            <dd className="font-semibold tabular-nums">
              {row.open_case_service_date}
            </dd>
          </>
        )}
      </dl>

      {/*
       * ⛔ DALIL — HAVOLA, KADR EMAS (D-C7). MAVJUD `EvidenceLink`
       *   O'ZGARTIRILMASDAN qayta ishlatiladi: u huquqni ham, bo'sh
       *   identifikator ro'yxatini ham O'ZI hal qiladi va ikkala shoxda
       *   ham `null` qaytaradi. Bu yuzada rasm baytlarini chizishning
       *   BIRORTA usuli yozilmaydi.
       */}
      {caseQuery.data === undefined ? null : (
        <EvidenceLink
          serviceDate={caseQuery.data.service_date}
          snapshotIds={evidenceIds}
        />
      )}
    </section>
  );
}

function StallCardBody({
  canManage,
  onEdit,
  stall,
}: {
  canManage: boolean;
  onEdit?: (stallId: string) => void;
  stall: StallDetail;
}) {
  const t = useTranslations();
  const tStatus = useTranslations("stalls.status");
  const format = useFormatter();
  const locale = useLocale();

  const categoryLabel = stall.category_name ?? t("stalls.categoryUnset");

  return (
    <div className="flex flex-col gap-4">
      {/* D-16: toifa va zona nomi DB kontenti — tarjima qilinmaydi. */}
      <p className="text-sm text-text-muted">
        {categoryLabel} · {stall.zone_name}
      </p>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <dt className="text-text-muted">{t("stalls.categoryLabel")}</dt>
        <dd className="font-semibold">{categoryLabel}</dd>

        <dt className="text-text-muted">{t("stalls.tariffLabel")}</dt>
        <dd className="font-semibold tabular-nums">
          {stall.tariff_soum === null ? (
            /*
             * ⚠ "Tarif belgilanmagan" MAJBURIY va OGOHLANTIRISH uslubida
             * ko'rinadi (D-08 fail-closed): tarifsiz rasta kunlik patta
             * hisobiga umuman tushmaydi va 6-fazada anomaliyaga aylanadi,
             * ya'ni bu HAQIQIY NOSOZLIK. Kamera bo'limidan farqli o'laroq
             * bu yerda qizil uslub TO'G'RI.
             *
             * Rang yagona signal emas: yonida ikonka va matn turadi
             * (WCAG 1.4.1).
             */
            <span className="flex items-center gap-2 text-danger-text">
              <AlertCircle aria-hidden="true" className="size-4 shrink-0" />
              {t("stalls.noTariff")}
            </span>
          ) : (
            formatSoum(format, stall.tariff_soum, locale)
          )}
        </dd>

        <dt className="text-text-muted">{t("stalls.vendorLabel")}</dt>
        {/*
         * Sotuvchisiz rasta — ANOMALIYA, lekin NOSOZLIK EMAS (D-11): bozor
         * bo'sh rasta bilan ham normal ishlaydi. Shuning uchun uslub
         * neytral, ogohlantirish emas.
         *
         * D-16: sotuvchi ismi DB kontenti — tarjima qilinmaydi.
         */}
        <dd className={stall.vendor_name === null ? "text-text-muted" : "font-semibold"}>
          {stall.vendor_name ?? t("stalls.noVendor")}
        </dd>

        {stall.phone === null ? null : (
          <>
            <dt className="text-text-muted">{t("stalls.phoneLabel")}</dt>
            {/*
             * Telefon MASKALANMAYDI (§8.6): server raqamni allaqachon
             * yuborgan va uni klientda yulduzcha bilan yopish xavfsizlik
             * teatri bo'lardi. `GET /vendors` audit bildirishi bu yerda
             * TAKRORLANMAYDI — karta bitta rasta konteksti.
             */}
            <dd className="font-semibold tabular-nums">
              <a className="underline underline-offset-2" href={`tel:${stall.phone}`}>
                {stall.phone}
              </a>
            </dd>
          </>
        )}

        <dt className="text-text-muted">{t("stalls.statusLabel")}</dt>
        <dd className="font-semibold">{tStatus(stall.status)}</dd>
      </dl>

      {canManage && onEdit ? (
        <Dialog.Footer>
          <Button
            className="sm:flex-1"
            onClick={() => onEdit(stall.id)}
            size="lg"
          >
            {t("stalls.edit")}
          </Button>
        </Dialog.Footer>
      ) : null}
    </div>
  );
}
