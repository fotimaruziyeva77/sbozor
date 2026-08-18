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
const ROLE_CARDS: ReadonlyArray<{
  key: "director" | "cashier" | "inspector";
  letter: string;
}> = [
  { key: "director", letter: "D" },
  { key: "cashier", letter: "K" },
  { key: "inspector", letter: "N" },
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
        {ROLE_CARDS.map(({ key, letter }, index) => (
          <Reveal className="h-full" delayIndex={index} key={key}>
            <Card className="landing-card h-full">
              <CardHeader>
                <span
                  aria-hidden="true"
                  className="flex size-10 items-center justify-center rounded-md bg-accent/10 text-sm font-bold text-accent-text"
                >
                  {letter}
                </span>
                <h3 className="mt-3 landing-h3">
                  {t(`roles.${key}.title`)}
                </h3>
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
