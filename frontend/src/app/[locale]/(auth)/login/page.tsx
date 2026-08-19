import { KeyRound } from "lucide-react";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { LoginForm } from "@/components/auth/login-form";
import { routing } from "@/i18n/routing";

/*
 * Kirish sahifasi — «Sbozor Login» dizayni: chapda rol va'dasi, o'ngda
 * 440px shishasimon karta. Chap ustun <900px da yashiriladi (dizayn media
 * shoxi) — telefonda faqat forma qoladi, chalg'ituvchi matn emas.
 *
 * ⛔ Fon, parda va sahna harakati QOBIQDA (`(auth)/layout.tsx`) — barcha
 * auth sahifalari bitta sahnani baham ko'radi va u bir marta chiziladi.
 */

/** Rol nuqtalari — dizayndagi uch rang: kassir, nazoratchi, direktor. */
const ROLE_BULLETS = [
  { key: "cashier", dot: "bg-success" },
  { key: "inspector", dot: "bg-warning" },
  { key: "director", dot: "bg-accent" },
] as const;

export default async function LoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  // Statik renderni yoqadi — busiz sahifa dinamik bo'lib qoladi.
  setRequestLocale(locale);

  const t = await getTranslations("auth");

  return (
    <div className="grid w-full items-center gap-16 min-[901px]:grid-cols-[1fr_27.5rem]">
      <div className="max-[900px]:hidden">
        <p className="landing-kicker">{t("login.kicker")}</p>
        <h1 className="login-title mt-4 text-balance">{t("login.title")}</h1>
        <p className="login-lead mt-4.5 max-w-[44ch] text-text-muted">
          {t("login.sub")}
        </p>
        <ul className="mt-8 flex max-w-[38ch] flex-col gap-3.5">
          {ROLE_BULLETS.map(({ key, dot }) => (
            <li className="flex items-start gap-3" key={key}>
              <span
                aria-hidden="true"
                className={`mt-1.5 size-[0.4375rem] shrink-0 rounded-full ${dot}`}
              />
              <span className="text-sm leading-relaxed text-text-muted">
                {t(`login.role.${key}`)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="login-card px-8 py-9">
        <h2 className="text-2xl font-semibold">{t("login.cardTitle")}</h2>
        <p className="login-sub mt-1.5 text-text-muted">{t("login.cardSub")}</p>
        <div className="mt-6.5">
          <LoginForm />
        </div>
        {/*
          ⛔⛔ PAROL TIKLASHNING YAGONA JAVOBI — 260819 da KUCHAYTIRILDI.

          Avval bu yerda 12px xira izoh turardi va uning ustida
          «Parolni unutdingizmi?» havolasi bor edi. Havola aynan SHU
          paragrafga (`#tiklash`) olib borardi — ya'ni allaqachon
          ko'rinib turgan joyga: bosilganda ekranda hech nima
          o'zgarmasdi. Havola olib tashlandi, izoh esa endi yagona
          javob bo'lgani uchun KO'RINADIGAN blokka aylandi.

          ⛔ Bu yerda «tiklash tugmasi» YO'Q va bo'lmaydi ham: parolni
            o'zi tiklash oqimi mahsulotda umuman yo'q
            (`users.py::reset_password` — «SMS/email/bot-kod oqimi
            YO'Q»). Administrator vaqtinchalik parol beradi, tizim
            `must_change_password` qo'yadi va barcha eski sessiyalarni
            bekor qiladi. Bu yerga soxta forma qo'yish foydalanuvchini
            mavjud bo'lmagan oqimni kutishga majburlardi.
        */}
        <div className="mt-6.5 flex gap-3 rounded-xl border border-border bg-surface-muted px-4 py-3.5">
          <KeyRound
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0 text-text-muted"
            strokeWidth={1.75}
          />
          <div>
            <p className="text-sm font-semibold text-text">
              {t("login.helpTitle")}
            </p>
            <p className="mt-1 text-sm leading-relaxed text-text-muted">
              {t("login.helpNote")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
