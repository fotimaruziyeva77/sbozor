import type { LucideIcon } from "lucide-react";
import { Banknote, Camera, FileSpreadsheet } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/*
 * Rol-kartalar — 3 ta (10-UI-SPEC §9.1 blok 5, §9.3). Server Component.
 *
 * ⛔⛔ SKRINSHOT QO'YILMAYDI (§9.3, brief §2.5 dan ONGLI chekinish; T-10-10):
 *    (1) app ekranlarida sotuvchi F.I.Sh. va telefoni bor — ommaviy sahifaga
 *        qo'yish K-8 bilan bir sinfdagi huquqiy xavf, tozalash ro'yxati esa
 *        hali yozilmagan;
 *    (2) skrinshotdagi matn rasmga qotgan — 3 rol × 3 til = 9 rasm va ular
 *        app har o'zgarganda eskiradi;
 *    (3) 9 ekran rasmi Lighthouse ≥95 / LCP <1,5s byudjetiga o'lchanadigan yuk.
 *    ⛔ Soxta mockup ham QO'YILMAYDI (brief §3 taqig'i) — vizual isbot yukini
 *    hero sahnasi ko'taradi. Har karta o'rniga BITTA aniq, tekshiriladigan
 *    da'vo beradi (`text-xs text-accent-text`).
 *
 * ⛔ Hover mini-animatsiyasi QO'SHILMAYDI (§17.2) — `Card` ning meros hover
 *    ko'tarilishi dizayn tizimining o'z xulqi, yangi mexanizm emas.
 *
 * Ikonkalar — `lucide-react` MEROS (yangi paket YO'Q): `Banknote` va
 * `Camera` app'ning kassir/wizard oqimlarida allaqachon ishlatiladi —
 * «reklamadagi bilan bir xil» oilaviy ko'rinish. Ikonka YOLG'IZ signal emas
 * (§15.12): har biri sarlavha matni bilan juft, o'zi `aria-hidden`.
 *
 * ⛔ Sarlavha ierarxiyasi: blok o'z `<h2>` sini chizadi (10-07 `<Section>`
 *    ni `title` prop'siz o'raydi); rol sarlavhalari — `<h3>`.
 */
const ROLE_CARDS: ReadonlyArray<{
  key: "director" | "cashier" | "inspector";
  Icon: LucideIcon;
}> = [
  { key: "director", Icon: FileSpreadsheet },
  { key: "cashier", Icon: Banknote },
  { key: "inspector", Icon: Camera },
];

export async function RoleCards() {
  const t = await getTranslations("landing");

  return (
    <div className="flex flex-col gap-6">
      <Reveal>
        <h2 className="text-2xl font-semibold tracking-tight">
          {t("roles.title")}
        </h2>
      </Reveal>
      <div className="grid gap-4 md:grid-cols-3">
        {ROLE_CARDS.map(({ key, Icon }, index) => (
          <Reveal className="h-full" delayIndex={index} key={key}>
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Icon aria-hidden="true" className="size-5 text-text-muted" />
                  <h3 className="text-lg font-semibold">
                    {t(`roles.${key}.title`)}
                  </h3>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <p className="max-w-[66ch] text-sm leading-relaxed text-text-muted">
                  {t(`roles.${key}.body`)}
                </p>
                {/* Bitta aniq, tekshiriladigan da'vo (§9.3) — skrinshot o'rni. */}
                <p className="text-xs font-semibold text-accent-text">
                  {t(`roles.${key}.claim`)}
                </p>
              </CardContent>
            </Card>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
