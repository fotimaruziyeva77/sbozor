"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useUpdateWeekdays } from "@/lib/market-queries";

/*
 * =============================================================================
 * Haftalik ish rejimi (D-17) — yetti katakcha, BITTA "Saqlash".
 *
 * HAR KATAKCHADA SO'ROV YUBORILMAYDI. Bu tushumga bevosita ta'sir qiluvchi
 * amal: belgisi olib tashlangan kunga patta HISOBLANMAYDI. Har bosishda
 * avtomatik saqlash "shoshib bosdim" holatini darhol kuchga kiritardi va
 * uni qaytarish uchun yana bir yozuv (va yana bir audit qatori) kerak
 * bo'lardi. Aniq "Saqlash" tugmasi — niyat chegarasi.
 *
 * SAQLASHDAN OLDIN TASDIQ (§10.6): dialog AYNAN qaysi kunlar yopilishini
 * nomma-nom ko'rsatadi. "Ishonchingiz komilmi?" degan mavhum savol bu
 * yerda foydasiz — admin nimani yo'qotayotganini ko'rishi kerak.
 *
 * BO'SH TO'PLAM UCH QATLAMDA TO'SILADI (T-02-116): bu yerda tugma
 * `aria-disabled` bo'ladi va SABAB yoziladi; serverda pydantic
 * `min_length=1`; DB'da `CHECK`. Bo'sh jadval "bozor hech qachon
 * ochilmaydi" degani va tushum JIMGINA nolga tushardi.
 *
 * `disabled` EMAS, `aria-disabled`: o'chirilgan tugma fokus olmaydi va
 * skrinrider uni umuman o'qimaydi — ya'ni "nega bosilmayapti?" savoliga
 * javob beradigan joy qolmasdi.
 * =============================================================================
 */

/** ISO-8601 hafta kunlari: 1 = dushanba … 7 = yakshanba (backend kontrakti). */
const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;
type Weekday = (typeof WEEKDAYS)[number];

/**
 * Kun -> tarjima kaliti.
 *
 * Xarita ATAYIN literal: `t()` next-intl'ning tip xavfsizligi ostida
 * ishlaydi va `` t(`calendar.weekday.${day}`) `` shaklidagi dinamik kalit
 * kompilyatorga noma'lum bo'lardi (kalit xatosi runtime'ga qolardi).
 */
const WEEKDAY_KEYS = {
  1: "calendar.weekday.1",
  2: "calendar.weekday.2",
  3: "calendar.weekday.3",
  4: "calendar.weekday.4",
  5: "calendar.weekday.5",
  6: "calendar.weekday.6",
  7: "calendar.weekday.7",
} as const;

export function WeekdayPicker({
  canManage,
  openWeekdays,
}: {
  canManage: boolean;
  /** Serverdagi joriy jadval — `GET /calendar` javobidan. */
  openWeekdays: readonly number[];
}) {
  const t = useTranslations();
  const updateWeekdays = useUpdateWeekdays();

  /*
   * Tanlov LOKAL holatda to'planadi va faqat "Saqlash" bilan serverga
   * ketadi. Boshlang'ich qiymat serverdan keladi; komponent `key` bilan
   * qayta montaj qilinadi (chaqiruvchi), ya'ni effekt ichida `setState`
   * qilinmaydi.
   */
  const [selected, setSelected] = useState<readonly number[]>(openWeekdays);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const isEmpty = selected.length === 0;
  const isUnchanged =
    selected.length === openWeekdays.length &&
    WEEKDAYS.every(
      (day) => selected.includes(day) === openWeekdays.includes(day),
    );

  /** Saqlansa YOPILADIGAN kunlar — tasdiq matnining mazmuni. */
  const closingDays = WEEKDAYS.filter(
    (day) => openWeekdays.includes(day) && !selected.includes(day),
  );

  const blocked = isEmpty || isUnchanged;

  function toggle(day: Weekday) {
    setSaveError(null);
    setSelected((current) =>
      current.includes(day)
        ? current.filter((item) => item !== day)
        : [...current, day].sort((a, b) => a - b),
    );
  }

  async function save() {
    setSaveError(null);
    try {
      await updateWeekdays.mutateAsync(selected);
      setConfirmOpen(false);
    } catch (error) {
      setSaveError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <fieldset className="flex flex-col gap-2">
        {/*
         * ⛔ `sr-only` — VA U OLIB TASHLANMAYDI (260819).
         *
         *    Kartaning `<h2>` si ayni matnni chizadi va ekranda
         *    «Haftalik jadval» IKKI marta yozilardi [jonli ko'rildi].
         *    Lekin `<legend>` ni O'CHIRISH mumkin emas: u yetti
         *    katakchani BIR GURUH qilib nomlaydi va usiz skrinrider
         *    «Dushanba, katakcha» deb o'qib, nimaning dushanbasi
         *    ekanini aytmasdi. Shuning uchun u KO'RINMAS bo'ladi,
         *    yo'q bo'lmaydi.
         */}
        <legend className="sr-only">{t("calendar.weekdaysLabel")}</legend>
        <p className="mb-1 text-xs text-text-muted">
          {t("calendar.weekdaysHint")}
        </p>

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {WEEKDAYS.map((day) => (
            <WeekdayCheckbox
              canManage={canManage}
              checked={selected.includes(day)}
              day={day}
              key={day}
              label={t(WEEKDAY_KEYS[day])}
              onToggle={() => toggle(day)}
            />
          ))}
        </div>
      </fieldset>

      {canManage ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            aria-disabled={blocked ? true : undefined}
            onClick={() => {
              if (blocked) return;
              setSaveError(null);
              setConfirmOpen(true);
            }}
          >
            {t("common.save")}
          </Button>

          {/*
           * SABAB har doim tugma yonida: `aria-disabled` tugma bosiladi,
           * lekin hech narsa qilmaydi — izohsiz bu "buzuq" ko'rinardi.
           */}
          {isEmpty ? (
            <p className="text-sm text-danger-text" role="status">
              {t("calendar.weekdaysRequired")}
            </p>
          ) : isUnchanged ? (
            <p className="text-sm text-text-muted" role="status">
              {t("calendar.weekdaysUnchanged")}
            </p>
          ) : null}
        </div>
      ) : null}

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          updateWeekdays.isPending
            ? t("common.loading")
            : t("calendar.weekdaysConfirmAction")
        }
        /*
         * Yopiladigan kun bo'lmasa amal DESTRUKTIV emas — faqat yangi ish
         * kunlari qo'shiladi. Shunda tugma ham qizil bo'lmaydi: qizil
         * rangni har tasdiqda ishlatish uning ma'nosini yemiradi.
         */
        confirmVariant={closingDays.length > 0 ? "destructive" : "default"}
        description={
          closingDays.length > 0
            ? t("calendar.weekdaysClosing", {
                days: closingDays.map((day) => t(WEEKDAY_KEYS[day])).join(", "),
              })
            : t("calendar.weekdaysNoClosing")
        }
        isBusy={updateWeekdays.isPending}
        onConfirm={() => void save()}
        onOpenChange={(next) => {
          if (next) return;
          setConfirmOpen(false);
          setSaveError(null);
        }}
        open={confirmOpen}
        title={t("calendar.weekdaysConfirmTitle")}
      >
        {saveError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {saveError}
          </p>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}

/**
 * Bitta kun katakchasi.
 *
 * `min-h-11` — barmoq nishoni kamida 44px (WCAG 2.2 SC 2.5.5). Nishon
 * katakchaning O'ZI emas, butun YORLIQ: 16px'lik katakchani telefon
 * ekranida aniq bosish mumkin emas. `border-ui` — yorliq boshqaruv
 * elementi bo'lgani uchun kontrast ≥3:1 (SC 1.4.11).
 */
function WeekdayCheckbox({
  canManage,
  checked,
  day,
  label,
  onToggle,
}: {
  canManage: boolean;
  checked: boolean;
  day: Weekday;
  label: string;
  onToggle: () => void;
}) {
  return (
    <label
      className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-border-ui px-3 py-2 text-sm transition-colors hover:bg-surface-muted"
      htmlFor={`weekday-${day}`}
    >
      <input
        checked={checked}
        className="size-4 accent-accent"
        disabled={!canManage}
        id={`weekday-${day}`}
        onChange={onToggle}
        type="checkbox"
        value={day}
      />
      {label}
    </label>
  );
}
