"use client";

import { useState } from "react";
/*
 * ⛔⛔ `next/link` EMAS, i18n `Link` (2026-08-25 audit, «bo'limlarni
 *     bossak boshqa joyga o'tyapti»).
 *
 *   Xom `next/link` locale prefiksini QO'YMAYDI: /ru dagi direktor
 *   katakni bosganda proxy uni STANDART locale'ga (/uz) qaytarardi —
 *   ya'ni bosish tilni almashtirib, «boshqa joyga» olib borardi.
 */
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";

import type { Period } from "@/components/director/period";
import { includesToday, periodRange } from "@/components/director/period";
import { PeriodPicker } from "@/components/director/period-picker";
import { AuditSheet } from "@/components/director/audit-sheet";
import { RevenueTrend } from "@/components/director/revenue-trend";
import { DebtorsReport } from "@/components/reports/debtors-report";
import { RevenueReport } from "@/components/reports/revenue-report";
import { SixTiles } from "@/components/director/six-tiles";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { formatBusinessDay } from "@/lib/format-day";

/*
 * =============================================================================
 * DIREKTOR PANELI — `Sbozor Direktor.dc.html` ning sarlavhasi va tablari.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-18).
 *
 * ⛔⛔ 260819: PANEL KECHAGI KUNGA QOTIRILGAN EDI — ENDI DAVR TANLANADI.
 *
 *     Dizayn sarlavhasi «kechagi kun bo'yicha yopilgan raqamlar» deb
 *     yozardi va bu rost edi: butun panel `today - 1` ni ko'rsatardi.
 *     Foydalanuvchi buni nuqson deb baholadi — direktor ekranga «hozir
 *     qanday ketyapti» degan savol bilan qaraydi.
 *
 *     Tekshirildi: bugungi tushumni ko'rsatish MUMKIN — tushum so'rovi
 *     to'lovlarni `payments.business_date` bo'yicha o'qiydi va «kun
 *     yopilgan bo'lsin» degan shart u yerda yo'q (`period.ts` izohi).
 *
 *     Endi sarlavha TANLANGAN davrni aytadi va davr bugunni o'z ichiga
 *     olsa «kun tugamagan» ogohlantirishi qo'shiladi — raqam kun
 *     davomida o'sib boradi va buni aytmaslik yolg'on bo'lardi.
 *
 * ⛔ TO'RTALA TAB HAM MAVJUD MARSHRUTGA BORADI (260819):
 *    Bugun -> /dashboard · Hisobot -> /reports ·
 *    Sotuvchi -> /reports/vendor · Tekshiruv uchun -> /reports/audit.
 *
 * ⛔ «Yangi ma'lumot bor — yangilash» yorlig'i BU FAZADA QURILMADI:
 *    u serverdan «yangi ma'lumot bor» signalini talab qiladi, bizda esa
 *    bunday kanal yo'q. Soxta yorliq chizish — o'lchanmagan da'vo.
 *    Buning o'rniga panel sarlavhasida bitta «yangilandi HH:MM»
 *    turadi (260819: u har katakda takrorlanardi va oltala katakda
 *    AYNAN bir xil raqam edi).
 * =============================================================================
 */

/*
 * ⛔⛔ BULAR TAB EMAS, TEZKOR O'TISH HAVOLALARI (2026-08-25 audit,
 *     «bo'limlarni bossak boshqa joyga o'tyapti»).
 *
 *   Avval ular TAB ko'rinishida chizilardi va foydalanuvchi «shu yerda
 *   almashadi» deb kutardi — bosganda esa BOSHQA SAHIFA ochilardi.
 *   Ustiga `next/link` locale prefiksini yo'qotib, ruscha sessiyani
 *   o'zbekchaga qaytarardi (tuzatildi — i18n `Link`).
 *
 *   Endi ular OCHIQ havola-chip: har birida o'q belgisi bor, ya'ni
 *   «bu boshqa sahifaga olib boradi» degani ekranning o'zida aytiladi.
 *   Yorliqlar i18n dan (avval qattiq kodlangan o'zbekcha edi).
 */
/*
 * 2026-08-25 (buyurtmachi №2/№3): tablar endi HAVOLA EMAS — mazmun SHU
 * sahifada ochiladi («Hisobotlarni bossam boshqa sahifaga o'tyapti —
 * unaqa emas, shu yerda ko'rinsin»). Har tab MAVJUD komponentni ichki
 * chizadi: Hisobotlar -> RevenueReport, Sotuvchi kesimi -> DebtorsReport,
 * Tekshiruv -> AuditSheet. To'liq sahifalar joyida qoladi (nav orqali).
 */
type DirectorTab = "today" | "reports" | "vendor" | "audit";

const TABS = [
  { key: "today", labelKey: "director.tabToday" },
  { key: "reports", labelKey: "director.tabReports" },
  { key: "vendor", labelKey: "director.tabVendor" },
  { key: "audit", labelKey: "director.tabAudit" },
] as const;

export function DirectorPanel({
  marketName,
  roleLabel,
}: {
  marketName: string;
  /*
   * ⛔⛔ ROL YORLIG'I TASHQARIDAN — VA U «Direktor» DEB QOTIRILMAYDI
   *     (260819, jonli o'lchandi).
   *
   *     Panel `report_view` bilan darvozalangan, u esa direktorda HAM,
   *     BOZOR ADMINIDA HAM bor. Ya'ni bozor admini kirganda sarlavha
   *     unga «… · Direktor» deb turardi — ekran uni BOSHQA ODAM deb
   *     atagan bo'lardi. Hokimga ko'rsatiladigan panelda kim qarab
   *     turgani noto'g'ri yozilishi — eng arzon, lekin eng uyatli xato.
   */
  roleLabel: string;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  /*
   * ⛔ Boshlang'ich davr — BUGUN. Foydalanuvchi talabi va u mantiqan
   *    ham to'g'ri: panel ochilganda birinchi javob berishi kerak
   *    bo'lgan savol «hozir qanday ketyapti».
   *
   * ⛔ URL ga yozilmaydi (`nuqs` ISHLATILMAYDI): bu bosh ekran va u
   *    HAR DOIM bugundan boshlanishi kerak. URL da qolib ketgan eski
   *    oraliq ertasiga direktorni eski raqam bilan kutib olardi.
   */
  const [activeTab, setActiveTab] = useState<DirectorTab>("today");
  const [period, setPeriod] = useState<Period>(() =>
    periodRange("today", todayIso),
  );
  const partial = includesToday(period, todayIso);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="dir-eyebrow">
            {marketName} · {roleLabel}
          </div>
          <h1 className="dir-title">{t("director.title")}</h1>
          {/*
           * ⛔⛔ «YANGILANDI» SHU YERDA, BIR MARTA (260819).
           *
           *     Avval u HAR KATAKNING pastida turardi — oltala katakda
           *     AYNAN bir xil raqam bilan, chunki u ma'lumot yoshi
           *     emas, shunchaki soat edi. Olti marta yozilgan bir xil
           *     fakt ekranni ham to'ldirardi, ham hech narsa aytmasdi.
           */}
          <p className="dir-tile-sub">
            {formatBusinessDay(format, todayIso, locale)}
            {" · "}
            {t("director.updatedLine", {
              time: format.dateTime(now, { timeStyle: "short" }),
            })}
            {" · "}
            {partial
              ? t("director.dayOpenNote")
              : t("director.periodClosedNote")}
          </p>
        </div>

        {/* ⛔ Filtr sarlavha bilan BIR QATORDA: u panelning boshqaruvi,
            kataklarning ustidagi qo'shimcha emas. */}
        <PeriodPicker
          onChange={setPeriod}
          period={period}
          todayIso={todayIso}
        />
      </header>

      <nav aria-label={t("director.tabsLabel")} className="dir-tabs">
        {TABS.map((tab) => (
          <button
            aria-pressed={activeTab === tab.key}
            className={activeTab === tab.key ? "dir-tab-active" : "dir-tab"}
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            type="button"
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </nav>

      {activeTab === "today" ? (
        <>
          <SixTiles period={period} />

          {/*
           * ⛔ TREND KATAKLARDAN KEYIN — dizayn tartibi. Kataklar «bugun
           *    qanday» savoliga javob beradi, trend esa «qanday ketyapti».
           */}
          <RevenueTrend />
        </>
      ) : activeTab === "reports" ? (
        <RevenueReport />
      ) : activeTab === "vendor" ? (
        <DebtorsReport />
      ) : (
        <AuditSheet />
      )}

      {/*
       * ⛔ DIZAYNNING YOPILISH MATNI — u panelning MA'NOSINI aytadi va
       *    shuning uchun ko'chirildi: har son dalilga olib boradi.
       */}
      <p className="dir-closing">{t("director.closing")}</p>
    </div>
  );
}
