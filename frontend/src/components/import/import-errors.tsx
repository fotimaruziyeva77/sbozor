"use client";

import { useCallback, useState } from "react";
import { Download } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { ImportErrorItem } from "@/lib/api-types";
import { downloadErrorReport } from "@/lib/market-queries";

/*
 * =============================================================================
 * Import xatolari — "300 xato muammosi" ning yechimi (UI-SPEC §8.5 C1).
 *
 * Bu fazaning eng nozik ekrani. Yettita qoida va ularning sabablari:
 *
 *  1. "HECH NARSA SAQLANMADI" — BIRINCHI jumla, DOIM (D-14). Busiz admin
 *     qisman yozuvdan qo'rqadi va bazani qo'lda tekshira boshlaydi. Bu
 *     jumla bitta xato bo'lganda ham chiqadi.
 *
 *  2. XATO KODI BO'YICHA GURUHLASH ro'yxatdan YUQORIDA. 300 qator o'qib
 *     bo'lmaydi; uchta jumla o'qiladi va harakatga aylanadi. Bu ekranning
 *     eng qimmatli qismi.
 *
 *  3. Faqat BIRINCHI 50 qator (T-02-122): 300 DOM elementi ham brauzerni,
 *     ham skrinriderni foydasiz yuklaydi.
 *
 *  4. Qolganlari `.xlsx` bo'lib yuklab olinadi — 300 xato brauzerda emas,
 *     Excelda tuzatiladi.
 *
 *  5. Qator formati AYNAN `{row}-qator: {matn}` (CONTEXT `<specifics>`).
 *
 *  6. Shoshilinch e'lon roli — FAQAT sarlavhada. 50 elementga qo'yilsa
 *     skrinrider 50 marta uzilardi.
 *
 *  7. Ro'yxat `<ol>`: tartib MA'NOLI (qator raqami o'sib boradi) va u
 *     SERVERDAN kelgan tartibda qoladi — klientda qayta saralanmaydi.
 *
 * ⚠ MATN QAYERDAN KELADI. Ekrandagi qator matni `code` ning TARJIMASI,
 * serverning `message` maydoni EMAS. Sabab: `message` server tomonda
 * yaratiladi va u FAQAT uz-Latn (`ImportIssue` docstringi buni literal
 * aytadi) — uni ekranga chiqarish rus tilidagi admin uchun tarjimasiz
 * matn berardi va "3 til majburiy" cheklovini buzardi. Aniq qiymat
 * ("qaysi zona topilmadi") YO'QOLMAYDI: u `message` bilan birga xatolar
 * hisobotiga (`.xlsx`) tushadi va aynan shu 4-qoidaning maqsadi.
 * =============================================================================
 */

/** T-02-122: DOM'ga tushadigan qatorlarning qat'iy chegarasi. */
const MAX_VISIBLE_ROWS = 50;

/**
 * `ImportIssue.code` -> tarjima kaliti (LITERAL xarita).
 *
 * `t(\`import.errors.${code}\`)` shaklidagi dinamik kalit tip
 * xavfsizligini buzadi: noto'g'ri nom kompilyatsiyadan o'tib, ekranda xom
 * kalit bo'lib chiqardi. Ro'yxat backend bilan `error-codes.test.mjs`
 * darvozasi orqali 1:1 qulflangan (02-13), ya'ni yangi kod qo'shilsa u
 * test bilan darhol ko'rinadi.
 */
const ERROR_LABEL_KEYS = {
  zone_not_found: "import.errors.zone_not_found",
  category_not_found: "import.errors.category_not_found",
  duplicate_code_in_file: "import.errors.duplicate_code_in_file",
  invalid_status: "import.errors.invalid_status",
  empty_code: "import.errors.empty_code",
  invalid_phone: "import.errors.invalid_phone",
  duplicate_phone_in_file: "import.errors.duplicate_phone_in_file",
  stall_not_found: "import.errors.stall_not_found",
  invalid_date: "import.errors.invalid_date",
  row_too_short: "import.errors.row_too_short",
  // --- xodimlar rosteri (02-24) ---
  //
  // ⚠ `invalid_role` va `role_not_allowed` ATAYIN alohida: birinchisi
  // imlo xatosi (`kassr`), ikkinchisi esa to'g'ri yozilgan, lekin
  // adminning darajasidan yuqori rol (`market_admin`). Adminning
  // harakati ikkalasida BUTUNLAY boshqa — faylni tuzatish yoki
  // platforma adminiga murojaat qilish — va bitta matn ikkalasini ham
  // noto'g'ri yo'naltirardi.
  invalid_role: "import.errors.invalid_role",
  role_not_allowed: "import.errors.role_not_allowed",
  phone_taken: "import.errors.phone_taken",
} as const;

type KnownErrorCode = keyof typeof ERROR_LABEL_KEYS;

function isKnownCode(code: string): code is KnownErrorCode {
  return Object.hasOwn(ERROR_LABEL_KEYS, code);
}

export function ImportErrors({
  errorCounts,
  errors,
}: {
  /** `{kod: soni}` — TO'LIQ sanoq (`errors` esa cheklangan namuna). */
  errorCounts: Readonly<Record<string, number>>;
  errors: readonly ImportErrorItem[];
}) {
  const t = useTranslations();
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  /*
   * Javob kelganda fokus sarlavhaga ko'chadi (§8.5): aks holda klaviatura
   * foydalanuvchisi 50 qatorli ro'yxatning boshini topa olmaydi. Callback
   * ref — element montaj bo'lgan lahzada chaqiriladi, ya'ni effekt ichida
   * `setState` ham, kechikish ham kerak emas.
   */
  const focusOnMount = useCallback((node: HTMLHeadingElement | null) => {
    node?.focus();
  }, []);

  /*
   * UMUMIY sanoq `error_counts` dan olinadi, `errors.length` dan EMAS:
   * ikkinchisi serverda cheklangan NAMUNA va u "300 ta xato" o'rniga
   * "50 ta xato" deb yolg'on gapirardi.
   */
  const total = Object.values(errorCounts).reduce((sum, n) => sum + n, 0);

  const visible = errors.slice(0, MAX_VISIBLE_ROWS);
  const remaining = total - visible.length;

  /** Guruhlar kamayish tartibida: eng ko'p uchragan sabab birinchi. */
  const groups = Object.entries(errorCounts).sort(
    (left, right) => right[1] - left[1],
  );

  function labelOf(item: ImportErrorItem): string {
    /*
     * Notanish kod — zaxira yo'l: serverning O'Z matni ko'rsatiladi. U
     * uz-Latn, lekin tarjimasiz TEXNIK kod ko'rsatishdan yaxshiroq. Bu
     * holat `error-codes.test.mjs` darvozasi tufayli amalda kelmasligi
     * kerak; u faqat "jimgina bo'sh qator" ehtimolini yopadi.
     */
    return isKnownCode(item.code) ? t(ERROR_LABEL_KEYS[item.code]) : item.message;
  }

  async function onDownload(): Promise<void> {
    setDownloadError(null);
    setDownloading(true);
    try {
      await downloadErrorReport(errors);
    } catch {
      setDownloadError(t("errors.generic"));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/*
       * 6-qoida: shoshilinch e'lon roli AYNAN shu bitta elementda.
       * Ro'yxat qatorlarida u TAKRORLANMAYDI.
       */}
      <h3
        className="text-base font-semibold text-danger-text"
        ref={focusOnMount}
        role="alert"
        tabIndex={-1}
      >
        {t("import.errorTitle", { count: total })}
      </h3>

      {/* 1-qoida: birinchi jumla, DOIM — bitta xato bo'lganda ham. */}
      <p className="text-sm">{t("import.nothingSaved")}</p>

      {/* 2-qoida: guruhlash ro'yxatdan YUQORIDA. */}
      <ul className="flex flex-col gap-1">
        {groups.map(([code, count]) => (
          <li className="flex justify-between gap-4 text-sm" key={code}>
            <span>
              {isKnownCode(code) ? t(ERROR_LABEL_KEYS[code]) : code}
            </span>
            <span className="text-text-muted">
              {t("wizard.countUnit", { count })}
            </span>
          </li>
        ))}
      </ul>

      {visible.length > 0 ? (
        <>
          <p className="text-xs text-text-muted">
            {t("import.showingFirst", { count: visible.length })}
          </p>

          {/* 7-qoida: `<ol>` — tartib ma'noli, serverdan kelgan holida. */}
          <ol className="flex flex-col gap-1">
            {visible.map((item) => (
              <li className="text-sm" key={`${item.row}-${item.code}`}>
                {/* 5-qoida: format AYNAN `{row}-qator: {matn}`. */}
                {t("import.rowError", {
                  message: labelOf(item),
                  row: item.row,
                })}
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {remaining > 0 ? (
        <p className="text-sm text-text-muted">
          {t("import.remaining", { count: remaining })}
        </p>
      ) : null}

      <div className="flex flex-col gap-2">
        {/* 4-qoida: qolganlari Excelda tuzatiladi. */}
        <Button
          className="self-start"
          disabled={downloading}
          onClick={() => void onDownload()}
          variant="ghost"
        >
          <Download aria-hidden="true" />
          {t("import.downloadErrors")}
        </Button>

        {downloadError !== null ? (
          <p className="text-sm text-text-muted" role="status">
            {downloadError}
          </p>
        ) : null}
      </div>
    </div>
  );
}
