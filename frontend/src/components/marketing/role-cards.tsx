import { ClipboardCheck, LayoutDashboard, Smartphone } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/*
 * Rol-kartalar — 3 ta (Landing v2 dizayni, claude.ai/design buyurtmasi).
 * Server Component.
 *
 * ⛔⛔ SKRINSHOT QO'YILMAYDI (§9.3, brief §2.5 dan ONGLI chekinish; T-10-10):
 *    (1) app ekranlarida sotuvchi F.I.Sh. va telefoni bor — ommaviy sahifaga
 *        qo'yish K-8 bilan bir sinfdagi huquqiy xavf;
 *    (2) skrinshotdagi matn rasmga qotgan — 3 rol × 3 til = 9 rasm eskiradi;
 *    (3) rasm yuki Lighthouse/LCP byudjetiga o'lchanadigan zarba.
 *    ⛔ Soxta mockup ham QO'YILMAYDI (brief §3) — vizual isbot yukini hero
 *    sahnasi ko'taradi. Har karta BITTA tekshiriladigan da'vo beradi.
 *
 * v2 qarori: lucide ikonkalar o'rniga HARF-CHIP avatarlar (D/K/N) —
 * dizayn aynan shu; chip `aria-hidden`, ma'no sarlavha matnida (§15.12).
 *
 * ⛔ Sarlavha ierarxiyasi: blok o'z `<h2>` sini chizadi; rollar — `<h3>`.
 */
/*
 * ⛔ 260819: HARF (D/K/N) IKONKAGA ALMASHDI. Harf faqat o'zbekcha
 *    o'qiydigan odamga ishlardi — ruscha sahifada «D» direktorni
 *    bildirmasdi va uch tilda uch xil harf kerak bo'lardi. Ikonka
 *    esa tildan mustaqil: panel · telefon · tekshiruv varaqasi.
 */
const ROLE_CARDS: ReadonlyArray<{
  key: "director" | "cashier" | "inspector";
  Icon: typeof LayoutDashboard;
}> = [
  { key: "director", Icon: LayoutDashboard },
  { key: "cashier", Icon: Smartphone },
  { key: "inspector", Icon: ClipboardCheck },
];

export async function RoleCards() {
  const t = await getTranslations("landing");

  return (
    <div className="flex flex-col gap-6">
      <Reveal>
        <p className="landing-kicker">{t("roles.kicker")}</p>
        <h2 className="mt-3 landing-h2 tracking-tight">
          {t("roles.title")}
        </h2>
      </Reveal>
      <div className="grid gap-5 md:grid-cols-3">
        {ROLE_CARDS.map(({ key, Icon }, index) => (
          <Reveal className="h-full" delayIndex={index} key={key}>
            <Card className="landing-card h-full">
              <CardHeader>
                <span aria-hidden="true" className="landing-icon">
                  <Icon className="size-5" strokeWidth={1.75} />
                </span>
                <h3 className="mt-4 landing-h3">
                  {t(`roles.${key}.title`)}
                </h3>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <p className="max-w-[66ch] landing-body text-text-muted">
                  {t(`roles.${key}.body`)}
                </p>
                {/* Bitta aniq, tekshiriladigan da'vo (§9.3) — skrinshot o'rni. */}
                <p className="landing-note font-semibold text-accent-text">
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
