import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
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
 * ⛔ NOMI `PanelTile`, `DirectorTile` EMAS (260819): bu karta Stitch
 *    dizaynining ANATOMIYASI — yorliq, kichik qator, tartib raqami,
 *    qiymat, ajratgich, «yangilandi» va amal havolasi. Uni direktor
 *    paneli ham, bozor admini paneli ham AYNAN bir xil ishlatadi.
 *    `director/` katalogida qolgan bo'lsa, admin paneli «direktor»
 *    komponentini import qilib turgandek ko'rinardi.
 *
 * ⛔ Tartib raqami (1–6) `Badge tone="muted"` da — dizayn shunday
 *    qiladi va u tasodifiy emas: direktor telefonda «uchinchi katakka
 *    qara» deb aytishi mumkin bo'lishi kerak.
 *
 * ⛔⛔ VA AYNAN SHU SABAB RAQAM O'QISH TARTIBIGA BOG'LIQ. Kataklar
 *     qayta tartiblanganda raqamlar eski joyida qolib, ekranda
 *     «1 · 3 · 6 · 2 · 4 · 5» bo'lib o'qildi [O'LCHANDI 260819,
 *     brauzerda]. Raqam o'z va'dasini bajarmasa u shovqin — shuning
 *     uchun `index` endi IXTIYORIY va u BERILMASA belgi umuman
 *     chizilmaydi. Bosh katak («yig'ilish darajasi») raqamsiz: u
 *     ro'yxatning a'zosi emas, u ro'yxat javob beradigan SAVOL.
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
  /**
   * Katakning tartib raqami — dizaynda o'ng yuqoridagi belgi.
   * Berilmasa belgi chizilmaydi (bosh katak shunday).
   */
  index?: number;
  label: string;
  /**
   * Sarlavha ostidagi kichik qator: MANBA yoki kesim.
   *
   * ⛔ IXTIYORIY va u SANANI TAKRORLASH uchun EMAS — davr sarlavhada
   *    bir marta yozilgan. Bu qator faqat katak BOSHQA kesimga
   *    tegishli bo'lganda beriladi («Reestr holati · …»,
   *    «nazoratchi ko'rgan rastalar»).
   */
  sub?: string;
  /** Katakni tanitadigan ingichka chiziqli ikonka (lucide). */
  icon?: LucideIcon;
  href: string;
  /** Pastdagi affordans matni — «→» belgisi bu yerda QO'SHILADI. */
  action: string;
  /** Kirish animatsiyasining kechikish indeksi (0–6). */
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

export function PanelTile({
  className,
  index,
  label,
  sub,
  icon: Icon,
  href,
  action,
  step,
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
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-2.5">
              {Icon === undefined ? null : (
                <Icon
                  aria-hidden="true"
                  className="mt-px size-4 shrink-0 text-text-muted"
                />
              )}
              <div className="min-w-0">
                <p className="dir-tile-label">{label}</p>
                {sub === undefined ? null : (
                  <p className="dir-tile-sub">{sub}</p>
                )}
              </div>
            </div>
            {index === undefined ? null : <Badge tone="muted">{index}</Badge>}
          </div>
        </CardHeader>

        <CardContent className="dir-tile-body">
          <div className="flex flex-col gap-3">
            {children}

            {/*
             * ⛔ AJRATGICH CHIZIQ QOLDI, LEKIN ENDI FAQAT AMAL QATORINI
             *    ajratadi: «Yangilandi» ketgach, chiziq qiymat bilan
             *    «keyingi qadam» ni ajratadigan yagona vazifani oladi.
             *    Usiz «Kunlar kesimi →» ko'rsatkichning bir qismi
             *    bo'lib o'qilardi.
             */}
            <div className="dir-tile-foot">
              <span className="dir-tile-action">{action} →</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
