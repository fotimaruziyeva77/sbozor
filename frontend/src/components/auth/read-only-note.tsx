import { Eye } from "lucide-react";
import { useTranslations } from "next-intl";

/*
 * =============================================================================
 * «FAQAT KO'RISH» QATORI — HUQUQNING YO'QLIGINI JIMLIKDAN CHIQARADI.
 *
 * ⛔⛔ NEGA BU KERAK BO'LDI (260819, jonli o'lchandi).
 *
 *   Direktor `/vendors`, `/tariffs`, `/calendar`, `/users` ekranlarini
 *   OCHA OLADI (`*_view` huquqlari bor), lekin `*_manage` YO'Q — ya'ni
 *   «Qo'shish» tugmasi shunchaki CHIZILMAYDI. Ekranda esa bu HECH
 *   NARSA bilan izohlanmasdi: direktor ro'yxatga qarab turib, tugma
 *   qani deb o'ylardi. Foydalanuvchining aynan shikoyati shu edi —
 *   «UI qismida tushunmovchiliklar mavjud».
 *
 *   Yo'q tugma — bu xabar EMAS. Yo'qlikni odam ikki xil o'qiydi:
 *   «menga ruxsat yo'q» yoki «tizim buzuq». Ikkinchisi bizga qimmatga
 *   tushadi: direktor buni nuqson deb aytadi va u tekshirishga ketadi.
 *
 * ⛔ NEGA TUGMA «O'CHIRILGAN» (`disabled`) HOLDA CHIZILMAYDI: bosilmaydigan
 *    tugma — taklif qilib, keyin tortib olish. U kursorni tortadi, 403
 *    va'da qiladi va skrinriderda ham «tugma» bo'lib qolaveradi. Bir
 *    qator matn esa savolga TO'G'RIDAN javob beradi va joy egallamaydi.
 *
 * ⛔ KIM QILISHINI AYTADI, «ruxsat yo'q» DEMAYDI. Foydalanuvchining
 *    savoli «kim qo'shadi?» edi va javob shu qatorda turishi kerak:
 *    bozor admini. Aks holda odam javobni qidirib qo'ng'iroq qiladi.
 *
 * ⚠ Bu XAVFSIZLIK chegarasi EMAS (`lib/rbac.ts` boshidagi bandga
 *   qarang) — haqiqiy darvoza serverda. Bu qator faqat ekrandagi
 *   jimlikni tushuntiradi.
 * =============================================================================
 */
export function ReadOnlyNote() {
  const t = useTranslations("common");

  return (
    <p className="flex items-center gap-2 text-xs text-text-muted">
      <Eye aria-hidden="true" className="size-3.5 shrink-0" />
      {t("readOnlyNote")}
    </p>
  );
}
