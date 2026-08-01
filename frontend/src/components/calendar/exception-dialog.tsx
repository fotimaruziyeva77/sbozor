"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCreateException } from "@/lib/market-queries";

/*
 * =============================================================================
 * Istisno kun formasi (D-18).
 *
 * `is_open` IKKI TOMONLAMA: `false` — bayram/yopiq kun, `true` — haftalik
 * jadvalda dam olish bo'lgan, lekin ISHLAYDIGAN kun. Istisno HAR DOIM
 * haftalik jadvaldan ustun turadi (`market_is_open()`), shuning uchun
 * ikkala yo'nalish ham bitta jadvalda yashaydi.
 *
 * ⚠ YOPIQ KUN — QO'SHIMCHA TASDIQ TALAB QILADI (§10.6 D-5). Sabab
 * moliyaviy: o'sha kunga patta UMUMAN hisoblanmaydi, ya'ni bitta noto'g'ri
 * bosish butun bozorning kunlik tushumini nolga tushiradi. "Istisno ish
 * kuni" esa teskari yo'nalish (tushum QO'SHADI) va u tasdiq so'ramaydi —
 * har amalda tasdiq so'rash tasdiqning ma'nosini yemiradi.
 * =============================================================================
 */

/** `<select>` qiymati — `is_open` bayrog'ining matnli ko'rinishi. */
const DAY_TYPE = { closed: "closed", open: "open" } as const;
type DayType = keyof typeof DAY_TYPE;

export function ExceptionDialog({
  onOpenChange,
  open,
}: {
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const createException = useCreateException();

  const [date, setDate] = useState("");
  const [dayType, setDayType] = useState<DayType>(DAY_TYPE.closed);
  const [note, setNote] = useState("");
  const [dateError, setDateError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [closeConfirmOpen, setCloseConfirmOpen] = useState(false);

  const isClosing = dayType === DAY_TYPE.closed;

  function reset() {
    setDate("");
    setDayType(DAY_TYPE.closed);
    setNote("");
    setDateError(null);
    setFormError(null);
    setCloseConfirmOpen(false);
  }

  function handleOpenChange(next: boolean) {
    if (!next) reset();
    onOpenChange(next);
  }

  async function submit() {
    setFormError(null);
    try {
      await createException.mutateAsync({
        exception_date: date,
        is_open: !isClosing,
        note: note.trim() === "" ? null : note.trim(),
      });
      handleOpenChange(false);
    } catch (error) {
      // 409 `calendar_exception_exists` -> `calendar.exceptionExists`.
      setCloseConfirmOpen(false);
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  function handleSave() {
    if (date === "") {
      setDateError(t("errors.required"));
      return;
    }
    setDateError(null);

    /*
     * Yopiq kun -> ikkinchi bosqich. Ochiq kun -> to'g'ridan-to'g'ri
     * yoziladi: u tushumni KAMAYTIRMAYDI.
     */
    if (isClosing) {
      setCloseConfirmOpen(true);
      return;
    }
    void submit();
  }

  const formattedDate =
    date === ""
      ? ""
      : format.dateTime(new Date(date), { dateStyle: "long" });

  return (
    <>
      <Dialog.Root onOpenChange={handleOpenChange} open={open}>
        <Dialog.Content
          description={t("calendar.addExceptionHint")}
          size="lg"
          title={t("calendar.addException")}
        >
          <Field
            error={dateError ?? undefined}
            id="exception-date"
            label={t("calendar.dateLabel")}
          >
            <Input
              aria-describedby={dateError ? "exception-date-error" : undefined}
              aria-invalid={dateError ? true : undefined}
              id="exception-date"
              onChange={(event) => {
                setDate(event.target.value);
                setDateError(null);
              }}
              type="date"
              value={date}
            />
          </Field>

          <Field id="exception-type" label={t("calendar.typeLabel")}>
            <Select
              id="exception-type"
              onChange={(event) => setDayType(event.target.value as DayType)}
              value={dayType}
            >
              <option value={DAY_TYPE.closed}>{t("calendar.typeClosed")}</option>
              <option value={DAY_TYPE.open}>{t("calendar.typeOpen")}</option>
            </Select>
          </Field>

          <Field id="exception-note" label={t("calendar.noteLabel")}>
            <Input
              autoComplete="off"
              id="exception-note"
              onChange={(event) => setNote(event.target.value)}
              value={note}
            />
          </Field>

          {formError ? (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              role="alert"
            >
              {formError}
            </p>
          ) : null}

          <Dialog.Footer>
            <Button
              className="sm:flex-1"
              disabled={createException.isPending}
              onClick={handleSave}
              size="lg"
            >
              {createException.isPending
                ? t("common.loading")
                : t("common.save")}
            </Button>
            <Dialog.Close asChild>
              <Button className="sm:flex-1" size="lg" variant="secondary">
                {t("common.cancel")}
              </Button>
            </Dialog.Close>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog.Root>

      {/*
       * §10.6 D-5: oqibat AYNIQSA aniq aytiladi — "o'sha kunga patta
       * hisoblanmaydi". Tugma yorlig'i o'z fe'li ("Yopiq deb belgilash"),
       * generic "Tasdiqlash" emas.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          createException.isPending
            ? t("common.loading")
            : t("calendar.closeDayAction")
        }
        description={t("calendar.closeDayConfirm", { date: formattedDate })}
        isBusy={createException.isPending}
        onConfirm={() => void submit()}
        onOpenChange={setCloseConfirmOpen}
        open={closeConfirmOpen}
        title={t("calendar.closeDayTitle")}
      />
    </>
  );
}
