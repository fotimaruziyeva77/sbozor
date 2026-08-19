import type { ReactNode } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * DIREKTOR KATAGI — dizaynning olti katagi uchun YAGONA qobiq.
 *
 * Manba: `Sbozor Direktor.dc.html` (MCP orqali o'qildi 2026-08-18).
 * O'lchamlar dizayndan AYNAN olingan va ular `globals.css` dagi
 * `.dir-*` sinflarida yashaydi — bu yerda arbitrar qiymat YO'Q
 * (G-land-5(d)/G-motion-7(d,e) darvozalari arbitrar Tailwind
 * o'lchamlarini rad etadi).
 *
 * ⛔⛔ KATAK BUTUNLAY BOSILADIGAN — VA BU DIZAYNNING QARORI.
 *
 * Dizaynda har katak `<a>` ichida. Sabab uning yopilish matnida
 * yozilgan: «Panelning har bir soni IKKI BOSISHDA dalilga olib
 * boradi». Ya'ni katak — ko'rsatkich emas, YO'LNING boshi.
 *
 * ⚠ Shuning uchun katak ichida IKKINCHI havola BO'LMAYDI: ichma-ich
 *   havola HTML'da yaroqsiz va skrinriderda ikki nishon bo'lib
 *   o'qilardi. Pastdagi «… →» matni havola EMAS, u tashqi havolaning
 *   affordansi.
 *
 * ⛔ Tartib raqami (1–6) `Badge tone="muted"` da — dizayn shunday
 *    qiladi va u tasodifiy emas: direktor telefonda «uchinchi katakka
 *    qara» deb aytishi mumkin bo'lishi kerak.
 * =============================================================================
 */

export type DirectorTileProps = {
  /** Katakning tartib raqami — dizaynda o'ng yuqoridagi belgi. */
  index: number;
  label: string;
  /** Sarlavha ostidagi kichik qator: sana yoki manba. */
  sub: string;
  href: string;
  /** Pastdagi affordans matni — «→» belgisi bu yerda QO'SHILADI. */
  action: string;
  /** Yangilanish vaqti. `stale` bo'lsa ogohlantirish rangida. */
  updatedAt: string;
  stale?: boolean;
  /** Kirish animatsiyasining kechikish indeksi (0–5). */
  step: number;
  /*
   * ⛔ Qo'shimcha sinf — FAQAT setkadagi joyni o'zgartirish uchun
   *    (`dir-tile-hero` butun qatorni egallaydi). Kartaning ICHKI
   *    ko'rinishi bu prop bilan o'zgartirilmaydi: aks holda har
   *    chaqiruvchi o'z katagini «biroz boshqacha» qilib, dizayn
   *    birligi yo'qolardi.
   */
  className?: string;
  children: ReactNode;
};

export function DirectorTile({
  className,
  index,
  label,
  sub,
  href,
  action,
  updatedAt,
  stale = false,
  step,
  children,
}: DirectorTileProps) {
  return (
    <Link
      className={cn("dir-tile-link", className)}
      href={href}
      style={{ "--i": step } as never}
    >
      <Card className="dir-tile">
        <CardHeader className="dir-tile-head">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="dir-tile-label">{label}</p>
              <p className="dir-tile-sub">{sub}</p>
            </div>
            <Badge tone="muted">{index}</Badge>
          </div>
        </CardHeader>

        <CardContent className="dir-tile-body">
          <div className="flex flex-col gap-3">
            {children}

            {/*
             * ⛔ AJRATGICH CHIZIQ MAJBURIY: usiz «Yangilandi» qatori
             *    ko'rsatkichning bir qismi bo'lib ko'rinardi, holbuki u
             *    MA'LUMOTNING YOSHI — boshqa turdagi fakt.
             */}
            <div className="dir-tile-foot">
              <span className={stale ? "dir-tile-stale" : "dir-tile-updated"}>
                {updatedAt}
              </span>
              <span className="dir-tile-action">{action} →</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
