import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

/*
 * Landing footer — Server Component. ⛔ Harakat YO'Q (scroll-reveal ham):
 * footer hikoyaning oxiri, e'tibor talab qilmaydi.
 *
 * Tarkib: maxfiylik siyosati havolasi (`/maxfiylik` — K-8 majburiy sahifa,
 * shu fazaning keyingi rejasida quriladi), aloqa bandi va ©.
 *
 * Aloqa telefoni `.env` dan (O-06: `NEXT_PUBLIC_CONTACT_PHONE`) — build
 * vaqtida qotiriladi, SSG buzilmaydi; berilmagan bo'lsa faqat yorliq
 * ko'rsatilmaydi (yolg'on kanal ochilmaydi).
 *
 * ⛔ `{year}` ICU argumentiga SATR beriladi: raqam berilsa ICU standart
 * raqam formati guruhlash qo'yadi («2 026») — yil sana emas, matn.
 */
export async function Footer() {
  const t = await getTranslations("landing");
  const phone = process.env.NEXT_PUBLIC_CONTACT_PHONE;

  return (
    <footer className="landing-night" data-theme="dark">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-6 py-8 text-sm text-text-muted sm:flex-row sm:items-center sm:justify-between">
        <p>
          {t("footer.copyright", {
            year: String(new Date().getFullYear()),
          })}
        </p>
        <div className="flex items-center gap-6">
          {phone ? (
            <a
              className="inline-flex min-h-11 items-center hover:text-text"
              href={`tel:${phone}`}
            >
              {t("footer.contact")}: {phone}
            </a>
          ) : null}
          <Link
            className="inline-flex min-h-11 items-center hover:text-text"
            href="/maxfiylik"
          >
            {t("footer.privacy")}
          </Link>
        </div>
      </div>
    </footer>
  );
}
