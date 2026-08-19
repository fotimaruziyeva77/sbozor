import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

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
 * ⛔ NOMI `PanelTile`, `DirectorTile` EMAS (260819): bu karta Stitch
 *    dizaynining ANATOMIYASI — yorliq, kichik qator, tartib raqami,
 *    qiymat, ajratgich, «yangilandi» va amal havolasi. Uni direktor
 *    paneli ham, bozor admini paneli ham AYNAN bir xil ishlatadi.
 *    `director/` katalogida qolgan bo'lsa, admin paneli «direktor»
 *    komponentini import qilib turgandek ko'rinardi.
 *
 * ⛔⛔ TARTIB RAQAMI (1–6) OLIB TASHLANDI (260819).
 *
 *     Karta burchagida `Badge` ichida raqam turardi. Stitch maketida
 *     u YO'Q — va Stitch haq: raqam hech qanday savolga javob
 *     bermaydi, u faqat «uchinchi katakka qara» deyish uchun edi.
 *     Bir marta u allaqachon shovqinga aylangan ham edi (kataklar
 *     qayta tartiblanganda ekranda «1 · 3 · 6 · 2 · 4 · 5» bo'lib
 *     o'qildi). Kartani kim nomlaydi — YORLIQ va IKONKA.
 *
 *     Kirish animatsiyasining navbati (`step`) esa QOLADI va u hamon
 *     o'qish tartibida bo'lishi kerak — buni `director-order`
 *     darvozasi tekshiradi.
 * =============================================================================
 */

/*
 * ⛔⛔ «YANGILANDI» QATORI OLIB TASHLANDI (260819, ekranga qarab).
 *
 *     Har katakning pastida `Yangilandi: 20:57` turardi va u
 *     MA'LUMOTNING YOSHI deb tanishtirilgan edi. Aslida u shunchaki
 *     SOAT: qiymat bir marta `now` dan hisoblanib, oltala katakka
 *     BIR XIL uzatilardi. Ekranda bir xil raqam OLTI MARTA yozilib,
 *     har katakka ajratgich chiziq + qator qo'shardi (~40px × 6) —
 *     va aynan shu kartalarni baland va bo'sh qilgan.
 *
 *     Endi u panel SARLAVHASIDA, bir marta. Ma'lumot yo'qolmadi,
 *     TAKROR yo'qoldi.
 *
 * ⛔⛔ IKONKA QO'SHILDI — VA U BEZAK EMAS. Stitch maketida har kartada
 *     bitta ingichka chiziqli ikonka bor. U ikki ish qiladi:
 *     (a) katakni bir qarashda tanitadi (pul · qarz · odam · kamera),
 *     (b) kartaning bo'sh chap-yuqori burchagini kompozitsiyaga
 *         kiritadi. Bizda u YO'Q edi va keng kartalar shuning uchun
 *         bo'm-bo'sh ko'rinardi.
 *
 *     Rang BERILMAYDI (`text-text-muted`): ikonka holat emas, NOM.
 *     Rangli ikonka «bu yerda muammo bor» deb yolg'on signal berardi.
 */
export type PanelTileProps = {
  label: string;
  /**
   * Sarlavha ostidagi kichik qator — FAQAT katak boshqa kesimga
   * tegishli bo'lganda («Reestr holati · …»). Davr sarlavhada bir
   * marta yozilgan va bu yerda TAKRORLANMAYDI.
   */
  sub?: string;
  /** O'ng yuqoridagi ingichka chiziqli ikonka (lucide). */
  icon?: LucideIcon;
  /** Yorliq oldidagi holat nuqtasi — Stitch «Band, lekin to'lovsiz» kartasi. */
  dot?: "success" | "warning" | "danger";
  href: string;
  /** Kirish animatsiyasining kechikish indeksi (0–6). */
  step: number;
  /**
   * Kartaning PASTKI qatori — izoh, yorliq yoki chap/o'ng juftlik.
   * `margin-top: auto` bilan pastga yopishadi.
   */
  note?: ReactNode;
  /**
   * Ajratgich + amal havolasi.
   *
   * ⛔ FAQAT BOSH KATAKDA. Stitch maketida kichik kartalarda amal
   *    qatori YO'Q — karta butunlay bosiladigan va ortiqcha qator
   *    olti marta takrorlanib, har kartaga ~40px qo'shardi.
   */
  action?: string;
  /*
   * ⛔ Qo'shimcha sinf — FAQAT setkadagi joyni o'zgartirish uchun
   *    (`dir-tile-hero` butun qatorni egallaydi). Kartaning ICHKI
   *    ko'rinishi bu prop bilan o'zgartirilmaydi.
   */
  className?: string;
  children: ReactNode;
};

const DOT_CLASS = {
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
} as const;

export function PanelTile({
  className,
  label,
  sub,
  icon: Icon,
  dot,
  href,
  step,
  note,
  action,
  children,
}: PanelTileProps) {
  return (
    <Link
      className={cn("dir-tile-link", className)}
      href={href}
      style={{ "--i": step } as never}
    >
      <Card className="dir-tile">
        <CardHeader className="dir-tile-head">
          <div className="flex flex-row items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              {dot === undefined ? null : (
                <span
                  aria-hidden="true"
                  className={cn("dir-tile-dot", DOT_CLASS[dot])}
                />
              )}
              <p className="dir-tile-label">{label}</p>
            </div>
            {Icon === undefined ? null : (
              <Icon aria-hidden="true" className="dir-tile-icon" />
            )}
          </div>
          {sub === undefined ? null : <p className="dir-tile-sub">{sub}</p>}
        </CardHeader>

        <CardContent className="dir-tile-body">
          <div className="flex flex-col gap-2">
            {children}

            {note === undefined ? null : (
              <div className="dir-tile-note">{note}</div>
            )}

            {action === undefined ? null : (
              <div className="dir-tile-foot">
                <span className="dir-tile-action">{action} →</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
