/*
 * =============================================================================
 * O'ZBEKISTON BAYROG'I — INLINE SVG, EMOJI EMAS (260819).
 *
 * ⛔⛔ NEGA EMOJI ISHLAMAYDI. Avval bu yerda `🇺🇿` turgan edi. Windows'da
 *     u BAYROQ BO'LIB CHIZILMAYDI: Segoe UI Emoji da mintaqaviy
 *     indikator juftliklari uchun glif YO'Q va brauzer ikkita harfni —
 *     «UZ» ni — quticha ichida ko'rsatadi. Xromdagi tekshiruvda aynan
 *     shu ko'rindi: bayroq o'rnida kichkina «uz» yozuvi.
 *
 *     Bu «kelajakda tuzaladigan» nuqson emas — Microsoft mintaqaviy
 *     bayroqlarni ATAYIN chizmaydi. Demak yagona ishonchli yo'l — o'z
 *     SVG'imiz. U hamma OS'da BIR XIL chiqadi va rasm so'rovi ham
 *     tug'dirmaydi (inline, CSP toza).
 *
 * ⛔ QATLAMLAR TARTIBI MUHIM: har rect o'zidan oldingisining ustki
 *    qismini yopadi va ochiq qolgan tasma qizil chiziqni beradi. Shu
 *    sababli ular kattadan kichikka yozilgan (12 → 8.1 → 7.9 → 3.9 →
 *    3.8) va joyini almashtirsa bayroq buziladi.
 *
 * ⛔ Yarim oy — ikki doira: oq doira va uning ustidagi ko'k doira.
 *    12 ta yulduz ATAYIN yo'q: 16px kenglikda ular yarim pikseldan
 *    kichik bo'lib, faqat loyqalik qo'shardi.
 *
 * ⚠ `aria-hidden` — chaqiruvchi joyda (`role="group"` ning `aria-label`
 *   ida) nom allaqachon bor; bayroq skrinriderga hech nima qo'shmaydi.
 * =============================================================================
 */
export function UzFlag({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      focusable="false"
      viewBox="0 0 24 12"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect fill="#1EB53A" height="12" width="24" />
      <rect fill="#CE1126" height="8.1" width="24" />
      <rect fill="#FFFFFF" height="7.9" width="24" />
      <rect fill="#CE1126" height="3.9" width="24" />
      <rect fill="#0099B5" height="3.8" width="24" />
      <circle cx="4.1" cy="1.9" fill="#FFFFFF" r="1.25" />
      <circle cx="4.85" cy="1.9" fill="#0099B5" r="1.25" />
    </svg>
  );
}
