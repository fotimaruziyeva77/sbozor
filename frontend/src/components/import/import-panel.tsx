"use client";

import { useState } from "react";
import { Download, Upload } from "lucide-react";
import { useTranslations } from "next-intl";

import { ImportErrors } from "@/components/import/import-errors";
import { StaffCredentials } from "@/components/import/staff-credentials";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  downloadTemplate,
  type ImportKind,
  importErrorsOf,
  useImportMutation,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Excel import paneli — TO'RT holat (UI-SPEC §8.5, D-13/D-14/D-15).
 *
 * SAHIFA ICHIDAGI PANEL, DIALOG EMAS [QAROR]. Xato ro'yxati uzun bo'lishi
 * mumkin, o'z sarlavha ierarxiyasiga muhtoj va yuklab olish havolasi bilan
 * birga yashaydi. Dialog ichida bularning hammasi ikki qavatli skrollga
 * aylanardi.
 *
 * A — Tanlash: `<label>` + YASHIRIN `<input type="file">`. Drag-drop
 *     YAGONA yo'l EMAS (WCAG 2.1.1): maydon `sr-only` bilan yashiriladi,
 *     `hidden` bilan EMAS — oxirgisi elementni fokus tartibidan butunlay
 *     chiqarib, klaviatura foydalanuvchisiga import yo'lini yopardi.
 *
 * B — Tekshirilmoqda: fayl nomi + skelet. PROGRESS INDIKATORI YO'Q —
 *     1000 qator serverda 9 ms (o'lchangan) + tarmoq vaqti; soxta
 *     ko'rsatkich yolg'on bo'lardi.
 *
 * C1 — Xato (422): `import-errors.tsx`.
 *
 * C2 — Muvaffaqiyat: `skipped > 0` bo'lsa TUSHUNTIRISH MAJBURIY (D-15).
 *     Usiz admin "nega 38 tasi yo'qoldi?" deb o'ylardi — D-15 bu xulqni
 *     ATAYIN tanlagan va UI buni ataylab deb ko'rsatishi shart.
 *
 * FAYL SERVERDA TEKSHIRILADI (T-02-121): bu yerda hech qanday parse yo'q,
 * klient faqat baytlarni yuboradi. Brauzerdagi tekshiruv chetlab o'tiladi
 * va u xavfsizlik chegarasi bo'la olmaydi.
 * =============================================================================
 */

/** Import turi -> tugallangandan keyingi reestr marshruti. */
const LIST_PATHS = {
  stalls: "/stalls",
  vendors: "/vendors",
  staff: "/users",
} as const;

/**
 * Turga qarab O'ZGARADIGAN matn kalitlari.
 *
 * ⚠ `staff` uchun UCHALA kalit ham boshqa va bu ATAYIN:
 *
 *   `title` — "Excel fayldan yuklash" xodimlar sahifasida qaysi ro'yxat
 *     haqida ekanini aytmasdi (sahifada boshqa yuklash yo'li ham bor);
 *   `hint`  — qator chegarasi 5000 EMAS, `import_max_staff_rows` (200);
 *   `skippedExplanation` — "o'zgartirilmadi" degan umumiy ibora bu yerda
 *     YETARLI EMAS. Admin aynan "parolni qayta oldimmi?" deb o'ylaydi,
 *     ya'ni matn parol ham, rol ham tegilmaganini ANIQ aytishi kerak.
 */
const TEXTS = {
  stalls: {
    title: "import.title",
    hint: "import.hint",
    skipped: "import.skippedExplanation",
    goTo: "import.goToStalls",
  },
  vendors: {
    title: "import.title",
    hint: "import.hint",
    skipped: "import.skippedExplanation",
    goTo: "import.goToVendors",
  },
  staff: {
    title: "import.staffTitle",
    hint: "import.staffHint",
    skipped: "import.staffSkippedExplanation",
    goTo: "import.goToUsers",
  },
} as const;

export function ImportPanel({ kind }: { kind: ImportKind }) {
  const t = useTranslations();

  const importFile = useImportMutation(kind);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const inputId = `import-file-${kind}`;

  function upload(file: File): void {
    setFileName(file.name);
    importFile.mutate(file);
  }

  function reset(): void {
    setFileName(null);
    importFile.reset();
  }

  async function onDownloadTemplate(): Promise<void> {
    setTemplateError(null);
    try {
      await downloadTemplate(kind);
    } catch {
      setTemplateError(t("errors.generic"));
    }
  }

  const importErrors = importFile.isError
    ? importErrorsOf(importFile.error)
    : null;

  const texts = TEXTS[kind];

  return (
    <Card>
      <CardHeader className="pb-2">
        <h2 className="text-lg font-semibold">{t(texts.title)}</h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {importFile.isPending ? (
          /* --- B: tekshirilmoqda --- */
          <div aria-busy="true" className="flex flex-col gap-3" role="status">
            <p className="text-sm">
              {t("import.checking")}
              {fileName === null ? "" : ` — ${fileName}`}
            </p>
            <Skeleton className="h-4 rounded-sm" />
            <Skeleton className="h-4 rounded-sm" />
            <Skeleton className="h-4 rounded-sm" />
          </div>
        ) : importFile.isSuccess ? (
          /* --- C2: muvaffaqiyat --- */
          <div className="flex flex-col gap-3">
            <h3 className="text-base font-semibold">
              {t("import.successTitle")}
            </h3>

            <p className="text-sm">
              {t("import.insertedCount", { count: importFile.data.inserted })}
            </p>

            {/*
             * D-15: `skipped > 0` da tushuntirish MAJBURIY va u sanoq bilan
             * BIR JOYDA turadi — alohida joyga qo'yilsa admin ikkinchi
             * raqamni umuman ko'rmasdi.
             */}
            {importFile.data.skipped > 0 ? (
              <p className="text-sm text-text-muted">
                {t("import.skippedCount", { count: importFile.data.skipped })}{" "}
                {t(texts.skipped)}
              </p>
            ) : null}

            {/*
             * Vaqtinchalik parollar — FAQAT `staff` tarmog'ida va faqat
             * bir marta (D-02). `credentials` bo'sh bo'lsa komponent
             * o'zi hech nima chizmaydi (qayta import holati).
             */}
            {"credentials" in importFile.data ? (
              <StaffCredentials credentials={importFile.data.credentials} />
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button onClick={reset} variant="secondary">
                {t("import.uploadAnother")}
              </Button>

              <Link
                className="inline-flex min-h-11 items-center gap-2 rounded-md px-4 text-sm font-semibold text-text hover:bg-surface-muted"
                href={LIST_PATHS[kind]}
              >
                {t(texts.goTo)}
              </Link>
            </div>
          </div>
        ) : (
          /* --- A: tanlash (xato holatida ham shu yerdan qayta yuklanadi) --- */
          <div className="flex flex-col gap-3">
            <label
              className={`flex min-h-11 cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed px-4 py-6 text-center text-sm transition-colors ${
                dragging
                  ? "border-accent bg-surface-muted"
                  : "border-border-ui hover:bg-surface-muted"
              }`}
              htmlFor={inputId}
              onDragLeave={() => setDragging(false)}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                const dropped = event.dataTransfer.files[0];
                if (dropped) upload(dropped);
              }}
            >
              <Upload aria-hidden="true" className="size-5 text-text-muted" />
              <span>{t("import.dropzone")}</span>
              <span className="text-xs text-text-muted">{t(texts.hint)}</span>
            </label>

            {/*
             * `sr-only` — KO'RINMAYDI, lekin fokus tartibida QOLADI.
             * `hidden` yoki `display:none` bo'lsa klaviatura foydalanuvchisi
             * uchun faylni tanlash yo'li umuman qolmasdi.
             */}
            <input
              accept=".xlsx"
              className="sr-only"
              id={inputId}
              onChange={(event) => {
                const chosen = event.target.files?.[0];
                if (chosen) upload(chosen);
                // Ayni faylni qayta tanlash ham `change` bersin.
                event.target.value = "";
              }}
              type="file"
            />

            <div className="flex flex-col gap-2">
              <Button
                className="self-start"
                onClick={() => void onDownloadTemplate()}
                variant="ghost"
              >
                <Download aria-hidden="true" />
                {t("import.downloadTemplate")}
              </Button>

              {templateError !== null ? (
                <p className="text-sm text-text-muted" role="status">
                  {templateError}
                </p>
              ) : null}
            </div>
          </div>
        )}

        {/* --- C1: 422 — qator xatolari --- */}
        {importErrors !== null ? (
          <ImportErrors
            errorCounts={importErrors.error_counts}
            errors={importErrors.errors}
          />
        ) : null}

        {/*
         * Qatorlarga aloqasi yo'q xato (409 `import_conflict`, 403, tarmoq).
         * U qator ro'yxatiga aylantirilmaydi: ko'rsatadigan qator YO'Q.
         */}
        {importFile.isError && importErrors === null ? (
          <p className="text-sm text-danger-text" role="status">
            {t(marketErrorMessageKey(importFile.error))}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
