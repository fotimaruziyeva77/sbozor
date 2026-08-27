"use client";

import { useCallback, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { localeHref } from "@/lib/locale-href";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ShiftCloseForm } from "@/components/collect/shift-close-form";
import { ShiftOpenCard } from "@/components/collect/shift-open-card";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";
import { useOpenShift } from "@/lib/shift-queries";

/*
 * =============================================================================
 * Y-3 — SMENA VA KO'R NAQD DEKLARATSIYASI (UI-SPEC §4.1, §4.2, §10).
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA MARSHRUT `/collect` OSTIDA, MUSTAQIL `/shifts` EMAS (§4.2)
 * -----------------------------------------------------------------------
 * 1. Smena — kassir oqimining SHARTI, alohida ish emas: `/collect` ochiq
 *    smenasiz ishlamaydi va u yerdan bitta havola bilan shu sahifaga
 *    o'tiladi. URL ierarxiyasi shu bog'liqlikni TAKRORLAYDI.
 * 2. Navigatsiya byudjeti: mustaqil element kassirning mobil panelida
 *    kuniga 2 marta bosiladigan narsani kuniga 500 marta bosiladigan
 *    narsa bilan TENG OG'IRLIKDA qo'yardi.
 * 3. Direktorga bu marshrut kerak emas — u farqni Y-4 da, kun kesimida
 *    ko'radi (§11.5), ya'ni ikkinchi marshrut ikkinchi iste'molchi
 *    topmasdi.
 *
 * ⛔ SHUNING UCHUN BU SAHIFA `NAV_ITEMS` GA QO'SHILMAYDI (§4.6) — u
 *    `/collect` sarlavhasidagi havola bo'lib yashaydi, `/cameras/[id]/zones`
 *    bilan AYNAN bir xil naqsh: bola marshrut nav elementi emas.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ URL HOLATI TAQIQLANADI (§4.5)
 * -----------------------------------------------------------------------
 * Deklaratsiya bir marta yoziladi va O'ZGARMAS (D-25). Har qanday
 * so'rov parametri uni OLDINDAN TO'LDIRILGAN qilib qo'yardi, ya'ni
 * kassir naqdni SANAB emas, ekrandagi tayyor raqamni TASDIQLAB
 * yuborardi — ko'r deklaratsiya o'z maqsadini yo'qotardi.
 *
 * ⚠ Shu sababdan bu faylda so'rov parametrini o'qiydigan hech qanday
 *   ilgak yo'q va `Suspense` chegarasi ham KERAK EMAS (`occupancy` va
 *   `snapshots` sahifalarida u AYNAN o'sha ilgak tufayli majburiy edi).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KOMPOZITSIYA — SAHIFA BOLALARINI O'ZI ALMASHTIRADI
 * -----------------------------------------------------------------------
 * Naqsh `occupancy/page.tsx:149-328` dan: sahifa bolalarini O'ZI import
 * qilib, holatga qarab ALMASHTIRADI. Yopish yuzasi kartaga ko'tarilmaydi
 * (`shift-open-card.tsx` ning §10.1 shartnomasi — IKKI holat, uchinchisi
 * yo'q).
 *
 * ⛔ ALMASHTIRISH, QO'SHISH EMAS: yopish oqimida karta DOM'dan CHIQADI —
 *    CSS bilan ko'zdan yashirilgan holda QOLMAYDI. Aks holda yopilgandan
 *    keyin ekranda §10.3 ning AYNAN UCHTA narsasi o'rniga BESHTA bo'lardi
 *    va ko'rlikning ekran qatlami buzilardi.
 *
 * ⚠ Ushbu izohda yashirish utilitalarining nomi LITERAL sifatida
 *   yozilmaydi: taqiqni o'lchaydigan darvoza xom matn skani va izohning
 *   O'ZI uni qizartirardi (kodbaza konvensiyasi, `badge.tsx` da ham
 *   xuddi shu sabab).
 *
 * ⚠ HUQUQ KO'ZGUSI — HAQIQIY NAZORAT SERVERDA. `shift_manage` yo'q
 *   sessiyada sahifa umuman chizilmaydi (naqsh `collect/page.tsx:76-85`
 *   dan). Yuk ko'taruvchi qatlam — `require_permission(SHIFT_MANAGE)`
 *   (06-10).
 * =============================================================================
 */

export default function CollectShiftPage() {
  const t = useTranslations();
  const locale = useLocale();
  const { principal } = useAuthStore();

  const canManage = hasPermission(principal?.roles ?? [], "shift_manage");

  /*
   * ⛔ Ochiq smenaning identifikatori SAHIFADA yechiladi — yopish oqimi
   *    shu qiymatga tayanadi. Karta ham shu ilgakni chaqiradi, LEKIN bu
   *    ikkinchi so'rov EMAS: react-query kalit bo'yicha dedupe qiladi
   *    (`occupancy/page.tsx` da ham xuddi shu naqsh).
   */
  const { data } = useOpenShift({ enabled: canManage });
  const openShift = data ?? null;

  /*
   * =========================================================================
   * ⛔⛔ CR-05: YOPISH OQIMI SO'ROV NATIJASIGA EMAS, O'ZI USHLAGAN
   *     IDENTIFIKATORGA TAYANADI.
   *
   * Ilgari holat `closing: boolean` edi va shart
   * `closing && openShift !== null` bo'lgan. `useCloseShift()` ning
   * `onSuccess` i esa `removeQueries({ queryKey: shiftPrefix(marketId) })`
   * chaqiradi va `shiftPrefix` — `openShiftKey` ning PREFIKSI, ya'ni
   * ochiq smena yozuvi keshdan CHIQADI.
   *
   * ⛔ MEXANIZM O'LCHANDI (`page.test.tsx`), TAXMIN QILINMADI — va u
   *    «darhol unmount» EMAS: react-query v5 da `removeQueries()` mount
   *    holatidagi kuzatuvchiga XABAR BERMAYDI va qayta so'rov ham
   *    yubormaydi. Shuning uchun yopilgan zahoti natija ekrani
   *    KO'RINADI. Nuqson KEYINGI QAYTA CHIZISHDA otiladi:
   *
   *   1. sahifa har qanday sababdan qayta chiziladi;
   *   2. `useQuery` o'chirilgan yozuvga qayta obuna bo'ladi ->
   *      `data === undefined` -> `openShift` `null`;
   *   3. eski shart `false` -> `ShiftCloseForm` UNMOUNT bo'ladi va uning
   *      LOKAL `result` holati YO'Q QILINADI;
   *   4. qayta so'rov javobi baribir `null` (smena YOPILGAN), ya'ni
   *      forma QAYTIB KELMAYDI.
   *
   * ⛔ AYNAN SHU UNI XAVFLI QILADI: §10.3 natija ekranining yashashi
   *    «sahifa qayta chizilmaydi» degan KAFOLATLANMAGAN shartga
   *    tayanardi. Sabablar ro'yxati yopiq emas — `AuthProvider`,
   *    locale/tema konteksti, brauzer fokusi, React ning dev rejimidagi
   *    ikki marta chizishi, kelajakda bu sahifaga qo'shiladigan HAR
   *    QANDAY holat. Ya'ni kassir moliyaviy deklaratsiya yozib, natija
   *    ekranini ko'rmasligi — vaqti aniq bo'lmagan, LEKIN kutiladigan
   *    oqibat; yagona dalil esa toast bo'lib qolardi.
   *
   * ⛔ IDENTIFIKATOR BIR MARTA OLINADI: forma butun oqim davomida
   *    MOUNT holatda qoladi, ya'ni `result` yashaydi. `openShift` endi
   *    faqat [Smenani yopish] BOSILGAN LAHZADA o'qiladi.
   *
   * ⚠ `shift-close-form.test.tsx` bu nuqsonni ko'ra olmasdi: u
   *   `ShiftCloseForm` ni TO'G'RIDAN-TO'G'RI chizadi, ya'ni ota-onaning
   *   unmount qarori umuman ishtirok etmaydi (WR-09).
   * =========================================================================
   */
  const [closingShiftId, setClosingShiftId] = useState<string | null>(null);
  const requestClose = useCallback(
    () => setClosingShiftId(openShift?.id ?? null),
    [openShift],
  );
  const reopen = useCallback(() => setClosingShiftId(null), []);

  if (!canManage) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("collect.shiftTitle")}
        </h1>

        <a
          className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-semibold text-text hover:bg-surface-muted"
          href={localeHref(locale, "/collect")}
        >
          <ArrowLeft aria-hidden="true" className="size-4" />
          {t("collect.title")}
        </a>
      </div>

      {/*
       * ⛔⛔ SHARTNING IKKALA TARMOG'I HAM KOMPONENT CHIZADI.
       *
       *   Bo'sh o'ram, `null` yoki `data-*` o'rami EMAS: yopish formasi
       *   qurilib, uni HECH KIM chizmasa uchala task ham yashil
       *   qaytardi va CASH-04 ekranda KUZATILMAS bo'lib qolardi —
       *   kassir [Smenani yopish] ni bosgach hech nima ochilmasdi.
       *
       *   ⚠ QO'RIQCHI `requestClose()` GA KO'CHDI (CR-05): `useOpenShift()`
       *     yuklanayotganda `openShift?.id` `undefined` bo'ladi va
       *     `closingShiftId` `null` bo'lib qoladi — ya'ni [Smenani
       *     yopish] hech nima ochmaydi va kassir BO'SH ekran ko'rmaydi.
       *     Farq shundaki, endi qo'riqcha BIR MARTA, bosish lahzasida
       *     baholanadi; ilgari u HAR RENDERDA baholanardi va yopilgandan
       *     keyin formani UNMOUNT qilardi.
       *
       *   ⛔ ALMASHTIRISH: yopish oqimida karta DOM'dan CHIQADI. Aks
       *      holda ekranda §10.3 ning AYNAN UCHTA narsasi o'rniga
       *      BESHTA bo'lardi (karta + tugma qo'shilardi).
       */}
      {closingShiftId !== null ? (
        <ShiftCloseForm onReopen={reopen} shiftId={closingShiftId} />
      ) : (
        <ShiftOpenCard onRequestClose={requestClose} />
      )}
    </div>
  );
}
