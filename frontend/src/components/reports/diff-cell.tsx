"use client";

import { Diff, NotebookPen, TrendingDown } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { DIFF_CLASSES } from "@/lib/api-types";
import type { DiffClassValue } from "@/lib/api-types";

/*
 * =============================================================================
 * FARQ SINFI — ⛔ UCH A'ZO, ⛔ UCH KANAL, ⛔ «MOS» UCHUN HECH NIMA (§10.5, §13.4).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. «MOS» QATORI ⛔ BEZAK OLMAYDI — VA BU MUZOKARASIZ
 * -----------------------------------------------------------------------
 * ⛔ 287 ta yashil belgi 13 ta farqni ⛔ KO'MIB yuborardi. Imzolanadigan
 *    varaqda ko'z ⛔ FARQNI qidiradi, mos qatorlarni emas — «hammasi
 *    joyida» degan 287 ta signal esa aynan o'sha 13 ta qatorni
 *    ko'rinmas qilardi.
 *
 * ⛔ Shuning uchun `match` ⛔ REYESTRDA HAM YO'Q (`DIFF_CLASSES` aynan
 *    uch a'zo, `api-types.ts`): unga `tone` berish uchun avval kalit
 *    kerak bo'lardi, kalit esa komponentda ishlatilishni TALAB qilardi.
 *    Ya'ni taqiq tip tizimida yashaydi, intizomda emas.
 *
 * ⚠ Qatorning O'ZI esa jadvalda ⛔ QOLADI — u MAXRAJ (§10.5): maxrajsiz
 *   13 qatorli varaq «bozorda 13 ta rasta bor» bo'lib o'qilardi (07 G-32
 *   darsi). Bu yerda faqat BEZAK yo'q, qator emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ 2. UCH KANAL — RANG YOLG'IZ SIGNAL EMAS (WCAG 1.4.1)
 * -----------------------------------------------------------------------
 * Har sinf RANG + IKONKA + MATN oladi. Rangni yolg'iz qoldirish rang
 * ko'rmaydigan foydalanuvchi uchun uchala sinfni ⛔ BIR XIL qilardi —
 * holbuki ular uch TURLI harakat talab qiladi («pulni qidiring» /
 * «daftarni tuzating» / «detektorni tekshiring»).
 *
 * ⚠ `warning` MATN sifatida ISHLATILMAYDI (§13.2): `Badge` ning
 *   `tone="warning"` i `bg-warning/20 text-text` beradi (o'lchangan
 *   15,64:1). `--color-warning` oq fonda 2,03:1 — falokat.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. NOMA'LUM SINF ⛔ ZAXIRA YORLIQ OLADI, JIMGINA YO'QOLMAYDI
 * -----------------------------------------------------------------------
 * `diff_class` javobda `z.string()` (04-10 darsi: enum bilan qulflash
 * bitta yangi backend a'zosida butun sahifani PARSE chegarasida
 * yiqitardi). Demak reyestrda yo'q qiymat BU YERGA yetib keladi va u
 * ⛔ BO'SH KATAK bo'lib chizilsa «mos» dan ⛔ FARQ QILMASDI — ya'ni
 * o'lchangan farq imzolanadigan varaqdan JIMGINA yo'qolardi.
 * =============================================================================
 */

type DiffView = {
  tone: BadgeTone;
  Icon: LucideIcon;
  /** ⛔ Kalit LITERAL: `compare.diff.*` camelCase, sinf nomi esa snake_case. */
  labelKey: "compare.diff.ledgerOver" | "compare.diff.systemOver" | "compare.diff.aiMismatch";
};

/**
 * Sinf -> ko'rinish. ⛔ `Record<DiffClassValue, …>` ATAYIN: `DIFF_CLASSES`
 * ga a'zo qo'shilsa bu jadval `tsc` da qizaradi, ya'ni yangi sinf
 * yorliqsiz, ikonkasiz va rangsiz ekranga chiqib keta olmaydi.
 *
 * ⚠ Sanoqlar ham SHU reyestrdan iteratsiya qilinadi (`compare-table.tsx`)
 *   — ikkinchi ro'yxat yozilsa ular bir kun ajralib ketardi.
 */
export const DIFF_VIEW: Record<DiffClassValue, DiffView> = {
  /* ⛔ `danger` — YO'QOTISH SHUBHASI: daftarda pul bor, tizimda yo'q. */
  ledger_over: {
    tone: "danger",
    Icon: TrendingDown,
    labelKey: "compare.diff.ledgerOver",
  },
  /* Daftar kamchiligi / yozuv xatosi — pul yo'qolmagan, qog'oz to'liq emas. */
  system_over: {
    tone: "warning",
    Icon: NotebookPen,
    labelKey: "compare.diff.systemOver",
  },
  /* Bandlik–billing farqi: detektor bir narsa dedi, hisob boshqa. */
  ai_mismatch: {
    tone: "neutral",
    Icon: Diff,
    labelKey: "compare.diff.aiMismatch",
  },
};

/** ⛔ Reyestr AYNAN uch a'zo — sanoqlar ham, badge'lar ham shundan. */
export const DIFF_ORDER: readonly DiffClassValue[] = DIFF_CLASSES;

function isDiffClass(value: string): value is DiffClassValue {
  return Object.hasOwn(DIFF_VIEW, value);
}

export type DiffCellProps = {
  /** Xom qiymat — ⛔ `null` = «uchala manba MOS», reyestrda yo'q ham bo'lishi mumkin. */
  diffClass: string | null;
};

export function DiffCell({ diffClass }: DiffCellProps) {
  const t = useTranslations();

  /*
   * ⛔ MOS -> HECH NIMA. Na rang, na ikonka, na matn, na `data-diff`
   *   atributi (yuqoridagi 1-band). Bo'sh katak bu yerda TO'G'RI natija:
   *   varaqda faqat FARQ ko'zga tashlanadi.
   */
  if (diffClass === null) return null;

  if (!isDiffClass(diffClass)) {
    /*
     * ⛔ ZAXIRA YORLIQ: qator ro'yxatda QOLADI va u «mos» dan
     *   FARQLANADI. Xom mexanik nom ekranga chiqmaydi — u foydalanuvchi
     *   uchun ma'nosiz, lekin «bu yerda nimadir bor» degan signal
     *   MAJBURIY.
     */
    return (
      <Badge data-diff="unknown" tone="muted">
        {t("compare.diffUnknown")}
      </Badge>
    );
  }

  const view = DIFF_VIEW[diffClass];

  return (
    <Badge className="gap-1" data-diff={diffClass} tone={view.tone}>
      <view.Icon aria-hidden="true" className="size-3" />
      {t(view.labelKey)}
    </Badge>
  );
}
