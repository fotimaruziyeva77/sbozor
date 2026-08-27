"use client";

import { useState } from "react";
import { Check, Copy, Download } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { StaffCredential } from "@/lib/api-types";
import { saveBlob } from "@/lib/market-queries";
import type { RoleLabelKey } from "@/lib/rbac";
import { roleLabelKey } from "@/lib/rbac";

/*
 * =============================================================================
 * VAQTINCHALIK PAROLLAR — BIR MARTA KO'RSATILADI (D-02, MARKET-07).
 *
 * `temp-password-dialog.tsx` bilan AYNI qoidalar, faqat miqyosi boshqa:
 * u yerda bitta parol, bu yerda o'nlab. Parollarning butun umri ikki
 * joyda o'tadi — HTTP javobining tanasida va shu komponentning `props`
 * ida. Panel `reset()` bilan yopilganda mutatsiya holati tozalanadi va
 * qiymatlar React holatidan butunlay chiqib ketadi.
 *
 * ATAYIN QILINMAYDI:
 *   - diagnostika chiqishiga yozish (grep darvozasi bilan qulflangan);
 *   - URL yoki so'rov parametriga qo'yish — u brauzer tarixida va server
 *     kirish jurnalida qolib ketardi;
 *   - brauzer omboriga saqlash;
 *   - React Query keshiga tushirish (shuning uchun `useMutation`).
 *
 * Nusxa olish va faylga saqlash bundan ISTISNO EMAS: ikkalasi ham
 * foydalanuvchining ANIQ harakati va ular brauzerdan tashqariga
 * chiqmaydi.
 *
 * ⚠ FAYL KLIENTDA QURILADI VA SERVERGA QAYTA YUBORILMAYDI.
 * `POST /imports/errors.xlsx` naqshi (xatolar ro'yxatini serverga
 * qaytarib, `.xlsx` olish) bu yerda ATAYIN ishlatilmaydi: parollar bilan
 * u ularni IKKINCHI marta tarmoqqa va server kirish jurnaliga
 * chiqarardi — ya'ni "bir martalik" kafolati javob bilan tugamas edi.
 * =============================================================================
 */

const CSV_SEPARATOR = ";";
/**
 * ⚠ `,` EMAS VA BU DID MASALASI EMAS.
 *
 * CIS lokalidagi Excel ustun ajratgichi sifatida `;` ni o'qiydi, `,` ni
 * esa o'qimaydi — vergulli fayl ochilganda BUTUN qator bitta katakka
 * tushardi va admin uni qo'lda bo'lishga majbur bo'lardi.
 */

const UTF8_BOM = "﻿";
/**
 * BOM MAJBURIY: usiz Excel faylni cp1251 deb o'qib, kirill va o'zbek
 * apostrofli harflarini buzardi (`Ф.И.Ш.` -> tanib bo'lmas belgilar).
 */

/** CSV katagini xavfsiz o'raydi (ajratgich yoki qo'shtirnoq bo'lsa). */
function csvCell(value: string): string {
  if (
    value.includes(CSV_SEPARATOR) ||
    value.includes('"') ||
    value.includes("\n")
  ) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
}

/**
 * Parollar ro'yxatini CSV matniga aylantiradi — SOF FUNKSIYA.
 *
 * DOM'dan ajratilgan, chunki uning ikkita da'vosi (ajratgich va BOM)
 * render bilan hech qanday aloqasi yo'q va ularni jsdom orqali
 * tekshirish testni sababsiz mo'rt qilardi.
 *
 * ⚠ Sarlavha qatori TARJIMA QILINMAYDI: fayl adminning O'ZIGA, bir
 * martalik yetkazish uchun. Tarjima qilinganda u kirillcha sarlavhali
 * bo'lib, ruscha Excelda yana boshqa ko'rinardi — foyda esa nol.
 */
export function buildCredentialsCsv(
  credentials: readonly StaffCredential[],
): string {
  const header = ["F.I.Sh.", "telefon", "rol", "parol"];
  const lines = [
    header.join(CSV_SEPARATOR),
    ...credentials.map((item) =>
      [
        csvCell(item.full_name ?? ""),
        csvCell(item.phone),
        csvCell(item.roles.join(" ")),
        csvCell(item.temporary_password),
      ].join(CSV_SEPARATOR),
    ),
  ];
  return UTF8_BOM + lines.join("\r\n") + "\r\n";
}

/** Bufer uchun matn — CSV bilan bir xil ma'lumot, lekin o'qishga qulay. */
function plainText(credentials: readonly StaffCredential[]): string {
  return credentials
    .map((item) => `${item.phone} ${item.temporary_password}`)
    .join("\n");
}

async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Buferga ruxsat berilmagan (HTTPS bo'lmagan kontekst yoki rad
    // javobi). Parollar baribir ekranda ko'rinib turibdi — oqim
    // to'xtamaydi va fayl yo'li ham ochiq qoladi.
    return false;
  }
}

export function StaffCredentials({
  credentials,
}: {
  credentials: readonly StaffCredential[];
}) {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const [copiedRow, setCopiedRow] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  // Bo'sh ro'yxat -> KOMPONENT UMUMAN CHIZILMAYDI. Qayta import
  // (D-15) aynan shu holatni beradi: hamma a'zo mavjud, ya'ni
  // ko'rsatadigan parol yo'q va "Vaqtinchalik parollar" sarlavhasi
  // ostidagi bo'sh ro'yxat adminni "parol berilmadimi?" deb
  // o'ylantirardi.
  if (credentials.length === 0) return null;

  function fileName(): string {
    const today = new Date().toISOString().slice(0, 10);
    // Fayl nomida PAROL YO'Q va bo'lishi ham mumkin emas: nom brauzer
    // yuklamalar tarixida va operatsion tizim jurnalida qoladi.
    return `sbozor-xodimlar-parollar-${today}.csv`;
  }

  function onDownload(): void {
    saveBlob(
      new Blob([buildCredentialsCsv(credentials)], {
        type: "text/csv;charset=utf-8",
      }),
      fileName(),
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-base font-semibold">{t("staffCredentials.title")}</h4>

      {/*
       * Ogohlantirish E'LON QILINADI (`role="alert"`): skrinrider
       * foydalanuvchisi parollar ro'yxatiga yetib borgunicha "bu boshqa
       * ko'rsatilmaydi" faktini bilishi shart, aks holda u ro'yxatni
       * o'qib bo'lib, panelni yopib yuborardi.
       */}
      <p className="text-sm text-danger-text" role="alert">
        {t("staffCredentials.warning")}
      </p>

      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => {
            void copy(plainText(credentials)).then(setCopiedAll);
          }}
          variant="secondary"
        >
          {copiedAll ? (
            <Check aria-hidden="true" />
          ) : (
            <Copy aria-hidden="true" />
          )}
          {copiedAll ? t("staffCredentials.copied") : t("staffCredentials.copyAll")}
        </Button>

        <Button onClick={onDownload} variant="ghost">
          <Download aria-hidden="true" />
          {t("staffCredentials.download")}
        </Button>
      </div>

      <ol className="flex flex-col gap-2">
        {credentials.map((item) => (
          <li
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
            key={item.row}
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="text-sm font-medium">
                {/* F.I.Sh. — DB kontenti, tarjima qilinmaydi (D-16). */}
                {item.full_name ?? t("staffCredentials.noName")}
              </span>
              <span className="text-xs text-text-muted">
                {item.phone}
                {" · "}
                {item.roles
                  .map((role) => roleLabelKey(role))
                  .filter((key): key is RoleLabelKey => key !== null)
                  .map((key) => tRoles(key))
                  .join(", ")}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {/*
               * `font-mono ... select-all` — HUJJATLASHTIRILGAN ISTISNO
               * (UI-SPEC §3.1, `temp-password-dialog.tsx` bilan bir xil):
               * bu qiymat ovoz chiqarib o'qiladi yoki nusxa olinadi,
               * ya'ni u tipografik ierarxiyaning bir qismi emas.
               */}
              <span className="font-mono text-sm tracking-wider break-all select-all">
                {item.temporary_password}
              </span>

              <Button
                aria-label={`${t("staffCredentials.copy")} — ${item.phone}`}
                onClick={() => {
                  void copy(item.temporary_password).then((ok) => {
                    if (ok) setCopiedRow(item.row);
                  });
                }}
                variant="ghost"
              >
                {copiedRow === item.row ? (
                  <Check aria-hidden="true" />
                ) : (
                  <Copy aria-hidden="true" />
                )}
              </Button>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
