"use client";

import { useTranslations } from "next-intl";

import { EmptyState } from "@/components/ui/empty-state";

/*
 * =============================================================================
 * F BLOKI — XABAR YETKAZILISHI. ⛔ BU REJADA UNING O'RNI VA BO'SH HOLATI.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA BLOK BUGUN HAM MAVJUD, TO'LDIRILMAGAN BO'LSA HAM
 * -----------------------------------------------------------------------
 * Blok to'plami kunga qarab qulflangan va u ⛔ TO'PLAM TENGLIGI bilan
 * o'lchanadi: `bugun` -> {kun tanlagichi, yetkazilganlik};
 * `kecha` -> oltala blok. Ya'ni yetkazilganlik ⛔ KESISHMANING a'zosi va
 * u ⛔ BUGUN HAM chiziladi — kvitansiya HOZIR ketadi va «xabar kelmadi»
 * nizosi O'SHA KUNI chiqadi. Blok kechaga qulflansa, BOT-04 ning amaliy
 * qiymati NOLGA tushardi.
 *
 * ⛔ VA MAZMUN JUFTLIGI DARVOZASI SHU YERGA QARAYDI: blok atributi bor,
 *    lekin ro'yxat komponenti mazmun atributini CHIQARMASA, darvoza
 *    ⛔ BO'SH O'RAMNI o'tkazardi. Shuning uchun o'rin BO'SH `<div>` emas,
 *    ⛔ NOMLANGAN BO'SH HOLAT bilan keladi.
 *
 * -----------------------------------------------------------------------
 * ⚠ NEGA `delivery-list.tsx` EMAS — NOM ATAYIN BOSHQA
 * -----------------------------------------------------------------------
 * Haqiqiy jadval (besh holat, urinishlar, xato TURI) keyingi rejaning
 * ishi va u `delivery-list.tsx` bo'lib keladi. Bu fayl o'sha nomni
 * BAND QILMAYDI: aks holda keyingi ijrochi to'ldirilmagan o'ramni
 * «allaqachon bor» deb o'qib, mazmun juftligi darvozasi esa
 * ⛔ YASHIL qolardi.
 *
 * ⛔ BU YERDA HOLAT NISHONI YO'Q va bu ATAYIN: besh holatning matni
 *    ⛔ ISBOTLANGANDAN ORTIQ DA'VO QILMASLIGI kerak (Bot API
 *    yetkazilganlik kvitansiyasini UMUMAN bermaydi). Yarim yozilgan
 *    yorliq «yetkazildi» degan isbotlanmagan gapni ekranga olib
 *    chiqarardi — shuning uchun bu yerda ⛔ BIRORTA holat matni yo'q.
 *
 * ⛔ `[Qayta yuborish]` ham QURILMAYDI: navbat o'zi qayta uradi va
 *    qo'lda yuborish IKKINCHI kvitansiya yuborardi.
 * =============================================================================
 */

export function DeliveryPlaceholder({ day }: { day: string }) {
  const t = useTranslations();

  return (
    /* ⛔ Atribut ENG TASHQI elementda — mazmun juftligi shundan o'qiladi. */
    <div className="flex flex-col gap-3" data-recon-content="delivery">
      <h2 className="text-lg font-semibold">{t("recon.deliveryTitle")}</h2>

      {/* ⛔ Bo'sh holatda AMAL yo'q — foydalanuvchi qiladigan ish yo'q. */}
      <EmptyState
        description={t("recon.emptyDeliveryHint", { date: day })}
        title={t("recon.emptyDelivery")}
      />
    </div>
  );
}
