"use client";

import Link from "next/link";
import { useFormatter, useLocale, useNow, useTimeZone } from "next-intl";

import { RevenueTrend } from "@/components/director/revenue-trend";
import { SixTiles } from "@/components/director/six-tiles";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { formatBusinessDay } from "@/lib/format-day";

/*
 * =============================================================================
 * DIREKTOR PANELI — `Sbozor Direktor.dc.html` ning sarlavhasi va tablari.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-18).
 *
 * ⛔⛔ SARLAVHA MATNI DIZAYNDAN AYNAN OLINGAN VA U DA'VO QILADI:
 *     «kechagi kun bo'yicha yopilgan raqamlar». Bu jumla PANELNING
 *     SHARTNOMASI — u kataklardagi hamma son nima uchun kechagi kunga
 *     tegishli ekanini aytadi. Olib tashlanса, direktor raqamlarni
 *     bugungi deb o'qirdi va «tushum kam» degan xulosa chiqarardi.
 *
 * ⛔ TO'RTALA TAB HAM MAVJUD MARSHRUTGA BORADI (260819):
 *    Bugun -> /dashboard · Hisobot -> /reports ·
 *    Sotuvchi -> /reports/vendor · Tekshiruv uchun -> /reports/audit.
 *
 * ⛔ «Yangi ma'lumot bor — yangilash» yorlig'i BU FAZADA QURILMADI:
 *    u serverdan «yangi ma'lumot bor» signalini talab qiladi, bizda esa
 *    bunday kanal yo'q. Soxta yorliq chizish — o'lchanmagan da'vo.
 *    Buning o'rniga har katak o'z yangilanish vaqtini ko'rsatadi.
 * =============================================================================
 */

/** Dizayn tab tartibi — «Sotuvchi» sahifa qurilgach shu yerga qo'shiladi. */
const TABS = [
  { href: "/dashboard", label: "Bugun", active: true },
  { href: "/reports", label: "Hisobot", active: false },
  { href: "/reports/vendor", label: "Sotuvchi", active: false },
  { href: "/reports/audit", label: "Tekshiruv uchun", active: false },
] as const;

export function DirectorPanel({ marketName }: { marketName: string }) {
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="dir-eyebrow">{marketName} · Direktor</div>
          <h1 className="dir-title">Bugun paneli</h1>
          <p className="dir-tile-sub">
            {formatBusinessDay(format, todayIso, locale)}
            {" · Toshkent vaqti · kechagi kun bo'yicha yopilgan raqamlar"}
          </p>
        </div>
      </header>

      <nav className="dir-tabs">
        {TABS.map((tab) =>
          tab.active ? (
            <span className="dir-tab-active" key={tab.href}>
              {tab.label}
            </span>
          ) : (
            <Link className="dir-tab" href={tab.href} key={tab.href}>
              {tab.label}
            </Link>
          ),
        )}
      </nav>

      <SixTiles />

      {/*
       * ⛔ TREND KATAKLARDAN KEYIN — dizayn tartibi. Kataklar «bugun
       *    qanday» savoliga javob beradi, trend esa «qanday ketyapti».
       */}
      <RevenueTrend />

      {/*
       * ⛔ DIZAYNNING YOPILISH MATNI — u panelning MA'NOSINI aytadi va
       *    shuning uchun ko'chirildi: har son dalilga olib boradi.
       */}
      <p className="dir-closing">
        Panelning har bir soni ikki bosishda dalilga olib boradi: katak →
        kun/rasta kesimi → to&apos;lov yozuvi, kamera kadri va audit jurnali.
      </p>
    </div>
  );
}
