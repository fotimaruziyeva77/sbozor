"use client";

import { useTranslations } from "next-intl";

import type { AuditEntry } from "@/lib/api-types";

/*
 * =============================================================================
 * ESKI -> YANGI (D-12 ning to'rtinchi ustuni).
 *
 * Faqat O'ZGARGAN maydonlar ko'rsatiladi: `changed_keys` backend'da
 * hisoblangan va u "nima o'zgardi" savoliga aynan javob beradi. Butun
 * JSONB'ni yoyish nizoni hal qilayotgan odamni 20 ta o'zgarmagan maydon
 * ichida ko'mib yuborardi.
 *
 * `insert` da faqat YANGI, `delete` da faqat ESKI qiymat mavjud — bo'sh
 * ustunni "—" bilan to'ldirish "qiymat bo'sh edi" degan noto'g'ri ma'no
 * berardi, shuning uchun mavjud bo'lmagan tomon umuman render qilinmaydi.
 *
 * XAVFSIZLIK (T-01-74): qiymatlar React MATN TUGUNI sifatida chiqadi.
 * HTML sifatida talqin qiladigan React xossasi butun `frontend/src/`
 * daraxtida ishlatilmaydi va bu grep darvozasi bilan qulflangan — shu
 * sababli uning nomi bu izohda ham literal sifatida yozilmagan.
 *
 * MASKALASH: `"***"` qiymatlari backend'da (`mask_sensitive()`) qo'yilgan
 * va shundayligicha ko'rsatiladi. UI qo'shimcha sezgir maydon SO'RAMAYDI —
 * javobda nima kelsa, o'sha ko'rinadi (T-01-69).
 *
 * MAYDON NOMLARI tarjima QILINMAYDI: ular DB ustunlari, ya'ni texnik
 * identifikator (D-16 ruhida). Ularni "chiroyli" nomga o'girish jurnalni
 * DB bilan solishtirib tekshirishni imkonsiz qilardi.
 * =============================================================================
 */

/** JSON qiymatini o'qiladigan matnga aylantiradi (React matn tuguni). */
function formatValue(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

/**
 * Ko'rsatiladigan maydonlar.
 *
 * `changed_keys` bo'sh yoki yo'q bo'lsa (masalan ilova yozgan `login`
 * yozuvi) ikkala tomondagi kalitlar birlashmasi olinadi — aks holda
 * yozuvning mazmuni butunlay ko'rinmay qolardi.
 */
function diffKeys(entry: AuditEntry): string[] {
  if (entry.changed_keys && entry.changed_keys.length > 0) {
    return [...entry.changed_keys].sort();
  }
  const keys = new Set([
    ...Object.keys(entry.old_value ?? {}),
    ...Object.keys(entry.new_value ?? {}),
  ]);
  return [...keys].sort();
}

export function AuditDiff({ entry }: { entry: AuditEntry }) {
  const t = useTranslations("audit");

  const keys = diffKeys(entry);
  const showOld = entry.action !== "insert" && entry.old_value !== null;
  const showNew = entry.action !== "delete" && entry.new_value !== null;

  if (keys.length === 0 || (!showOld && !showNew)) {
    return <p className="text-xs text-text-muted">{t("noValues")}</p>;
  }

  return (
    <dl className="flex flex-col gap-2">
      {keys.map((key) => (
        <div
          className="grid grid-cols-[minmax(6rem,auto)_1fr] items-baseline gap-x-3 gap-y-1 sm:grid-cols-[minmax(8rem,auto)_1fr_1fr]"
          key={key}
        >
          {/* Maydon nomi — texnik identifikator, tarjima qilinmaydi. */}
          <dt className="font-mono text-xs text-text-muted">{key}</dt>

          {showOld ? (
            <dd className="min-w-0">
              <span className="sr-only">{t("oldValue")}: </span>
              {/* `*-text` tokenlari: `--color-danger`/`--color-success`
                  12px matn sifatida AA (4.5:1) dan o'tmaydi. */}
              <span className="font-mono text-xs break-all text-danger-text">
                {formatValue(entry.old_value?.[key] ?? null)}
              </span>
            </dd>
          ) : null}

          {showNew ? (
            <dd className="min-w-0">
              <span className="sr-only">{t("newValue")}: </span>
              <span className="font-mono text-xs break-all text-success-text">
                {formatValue(entry.new_value?.[key] ?? null)}
              </span>
            </dd>
          ) : null}
        </div>
      ))}
    </dl>
  );
}
