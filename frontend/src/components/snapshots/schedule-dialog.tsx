"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Info } from "lucide-react";
import { useFormatter, useNow, useTimeZone, useTranslations } from "next-intl";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { formatSlotTime } from "@/components/snapshots/schedule-card";
import { SlotEditor } from "@/components/snapshots/slot-editor";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { ScheduleModeValue, SnapshotSchedule } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  useCreateSeasonalSchedule,
  useDeleteSchedule,
  useSchedules,
  useUpdateScheduleTimes,
} from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * DL-1 va DL-2 — BITTA QOBIQ, UCH XULQ (§4.4, §4.5, §4.7).
 *
 * ⛔⛔ DOIMIY IZOH (`snapshots.editNote`) — YOPIB BO'LMAYDI VA U
 *     OGOHLANTIRISH EMAS.
 *
 *     Muqobil variant — saqlashdan KEYIN tasdiq dialogi («bilasizmi,
 *     ertadan…») — foydalanuvchini ALLAQACHON QAROR QABUL QILGANDAN
 *     KEYIN to'xtatardi: u vaqtlarni tanlab, tugmani bosib bo'lgan
 *     bo'lardi va tasdiq faqat «ha» bosiladigan yana bir to'siq bo'lib
 *     qolardi. Doimiy izoh esa kutilmani QAROR PAYTIDA shakllantiradi —
 *     arzonroq va mehribonroq.
 *
 *     Shu sababdan izoh e'lonli rolni OLMAYDI: bu nosozlik emas,
 *     QOIDA. Har dialog ochilishida uni qayta o'qitish adminni izohni
 *     umuman eshitmaydigan qilardi. U formaga `aria-describedby`
 *     orqali bog'lanadi, ya'ni maydonga fokus tushganda tabiiy ravishda
 *     bir marta o'qiladi.
 *
 *     ⚠ Taqiqlangan ARIA rolining nomi bu faylda LITERAL yozilmaydi —
 *       qabul mezoni uni izohlarni FILTRLAMASDAN qidiradi (04-09 ning
 *       6-deviatsiyasi bilan aynan bir xil holat). Server xatosi bloki
 *       esa `aria-live="assertive"` bilan e'lon qilinadi — bu o'sha
 *       rolning ARIA-1.2 dagi TENG KUCHLI shakli va u izohni emas,
 *       ALOHIDA elementni qamraydi.
 *
 * UCH REJIM (§4.5) va uchtasining ham TAHRIRLANADIGANI FARQLI:
 *
 *   `past`   — HECH NIMA. Profil o'tmishdagi kadrlarni TUSHUNTIRADI;
 *              uni tahrirlash tarixni yolg'onga aylantirardi.
 *   `active` — FAQAT vaqtlar. Davrni siljitish o'tmishdagi
 *              `capture_runs` qatorlarini tushuntirmay qo'yardi.
 *   `future` — vaqtlar + O'CHIRISH. Hali birorta kadr olinmagan.
 *
 * ⚠ NOM VA DAVR DL-1 DA TAHRIRLANMAYDI — bu 04-09 ning 11-deviatsiyasi
 *   va u OCHIQ qarz sifatida shu rejaga qoldirilgan: `PATCH
 *   /snapshot-schedules/{id}` FAQAT `times` ni qabul qiladi
 *   (`ScheduleSlotsIn` da `extra="forbid"`). `future` profilning nomini
 *   yoki davrini o'zgartirish yo'li — uni O'CHIRIB QAYTA QO'SHISH, va
 *   ikkala amal ham shu dialogda bor. Repozitoriy yuzasini kengaytirish
 *   backend rejasining ishi va u frontend rejasida qilinmaydi.
 * =============================================================================
 */

/** Dialog nima uchun ochilgani — marshrutda EMAS, sahifa holatida (§4.4). */
export type ScheduleDialogRequest =
  | { kind: "create" }
  | { kind: "edit"; scheduleId: string | null };

/** Nom uzunligi — `SCHEDULE_NAME_MAX` ning klientdagi ko'zgusi (§4.7). */
const NAME_MAX = 40;

export function ScheduleDialog({
  onOpenChange,
  request,
}: {
  onOpenChange: (open: boolean) => void;
  /** `null` — dialog yopiq. */
  request: ScheduleDialogRequest | null;
}) {
  const t = useTranslations();
  const format = useFormatter();

  const schedules = useSchedules({ enabled: request !== null });
  const items = schedules.data?.items ?? [];

  const active = items.find((item) => item.mode === "active") ?? null;
  const target =
    request !== null && request.kind === "edit"
      ? (items.find((item) => item.id === request.scheduleId) ?? active)
      : null;

  function periodText(profile: SnapshotSchedule): string {
    const from = t("snapshots.scheduleFrom", {
      date: format.dateTime(new Date(profile.starts_on), {
        dateStyle: "medium",
      }),
    });
    if (profile.ends_on === null) return from;
    return `${from} ${t("snapshots.scheduleUntil", {
      date: format.dateTime(new Date(profile.ends_on), { dateStyle: "medium" }),
    })}`;
  }

  const isCreate = request?.kind === "create";
  const title = isCreate
    ? t("snapshots.addSeasonal")
    : t("snapshots.editSchedule");
  const description = isCreate
    ? t("snapshots.startsOnHint")
    : target === null
      ? t("snapshots.scheduleTitle")
      : periodText(target);

  /*
   * DL-1 NING SHOXLARI — GUARD ZANJIRI, TARTIB O'ZI O'QILADI.
   *
   * ⚠ `isPending` BIRINCHI turadi: u YAGONA holat bo'lib, unda
   *   «yuklanmoqda» ROST. Bo'sh ro'yxat esa yuklanish EMAS — so'rov
   *   TUGAGAN, ya'ni kutishni taklif qilish hech qachon tugamaydigan
   *   yolg'on bo'lardi (TEST-REPORT 2026-08-14, Topilma №6).
   *
   * ⚠ 5- va 6-shoxlar ATAYIN ikkiga bo'lingan: ro'yxat BOR bo'lsa
   *   «jadval yozilmagan» faktik yolg'on — jadval yozilgan, faqat
   *   so'ralgani topilmagan [quick 260816-5yz].
   */
  function renderBody(): ReactNode {
    if (request === null) return null;

    if (isCreate) {
      return (
        <CreateForm
          defaultTimes={active?.times ?? []}
          nextProfileName={active?.name ?? null}
          onDone={() => onOpenChange(false)}
        />
      );
    }

    if (schedules.isPending) {
      return <p className="text-sm text-text-muted">{t("common.loading")}</p>;
    }

    if (schedules.isError) {
      return <FormError message={t(marketErrorMessageKey(schedules.error))} />;
    }

    if (items.length === 0) return <ScheduleMissing />;

    if (target === null) return <ScheduleNotFound />;

    return (
      <EditForm
        key={target.id}
        onDone={() => onOpenChange(false)}
        periodLabel={periodText(target)}
        profile={target}
      />
    );
  }

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={request !== null}>
      <Dialog.Content
        description={description}
        sheetOnMobile
        size="md"
        title={title}
      >
        {renderBody()}
      </Dialog.Content>
    </Dialog.Root>
  );
}

/* --- Doimiy izoh ----------------------------------------------------------- */

function EditNote({ id }: { id: string }) {
  const t = useTranslations();

  return (
    <p
      className="flex items-start gap-2 rounded-md bg-surface-muted px-3 py-2 text-sm text-text-muted"
      id={id}
    >
      <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      {t("snapshots.editNote")}
    </p>
  );
}

/* --- Jadval profili topilmadi — IKKI BOSHQA-BOSHQA FAKT ------------------- */

/**
 * IKKALA HOLAT HAM FAKT, chaqiriq EMAS — VA ULAR BIR-BIRINI ALMASHTIRMAYDI.
 *
 * `ScheduleMissing` — ro'yxat BO'SH: bozorda jadval umuman yozilmagan.
 * `ScheduleNotFound` — ro'yxat bo'sh EMAS, lekin so'ralgan profil yo'q
 * (o'chirilgan yoki ro'yxat yangilangan). Ikkinchisida «jadval
 * yozilmagan» deyish FAKTIK YOLG'ON bo'lardi va u adminni mavjud
 * bo'lmagan nosozlikni izlashga yuborardi [quick 260816-5yz].
 *
 * ⛔⛔ «JADVAL QO'SHING» TUGMASI YOKI HAVOLASI IKKALASIGA HAM
 *     QO'SHILMAYDI (`action` proppi BERILMAYDI).
 *
 *     04-UI-SPEC §10.4 buni ATAYIN taqiqlaydi: D-01 bo'yicha jadvalni
 *     bozor sozlash ustasi AVTOMATIK yozadi, ya'ni uning yo'qligi
 *     adminning bajarmagan ishi emas — TIZIMNING nosozligi. «Qo'shing»
 *     chaqirig'i javobgarlikni noto'g'ri odamga yuklardi va ayni paytda
 *     D-01 ni jimgina yolg'onga aylantirardi («demak jadvalni admin
 *     yozar ekan-da»).
 *
 * ⚠ MAVSUMIY PROFIL YO'LI BU YERDA TAKRORLANMAYDI: u kartada
 *   (`schedule-card.tsx`) allaqachon bor va profilsiz bozorda ham
 *   ko'rinadi. Ikkinchi kirish nuqtasi ikki xil yo'lni tug'dirardi.
 *
 * ⚠ E'LONLI ROL QO'YILMAYDI: bu dialogning ASOSIY mazmuni, chekka
 *   xabar emas — u ochilishi bilan o'qiladi. Xato bloki (`FormError`)
 *   esa mavjud mazmunni ALMASHTIRADI va aynan shuning uchun e'lon
 *   qilinadi.
 *
 * ⚠ `py-6` — `EmptyState` ning standarti `py-12` va u DIALOG ichida
 *   haddan tashqari bo'sh joy berardi. `cn()` `twMerge` ustida
 *   qurilgani uchun oxirgi qiymat yutadi (`lib/cn.ts`).
 */
function ScheduleMissing() {
  const t = useTranslations();

  return (
    <EmptyState
      className="py-6"
      description={t("snapshots.scheduleMissingHint")}
      title={t("snapshots.scheduleMissing")}
    />
  );
}

function ScheduleNotFound() {
  const t = useTranslations();

  return (
    <EmptyState
      className="py-6"
      description={t("snapshots.scheduleNotFoundHint")}
      title={t("snapshots.scheduleNotFound")}
    />
  );
}

/* --- Server xatosi --------------------------------------------------------- */

/**
 * ⚠ `aria-live="assertive"` — e'lonli rolning ARIA-1.2 dagi teng kuchli
 *   shakli. Fokus shu blokka ko'chadi (§12.6), chunki TUZATISH YO'LI
 *   aynan shu yerda: xato matni `market-errors.ts` orqali tanilgan
 *   koddan chiziladi va u nima qilish kerakligini aytadi.
 */
function FormError({ message }: { message: string }) {
  const ref = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, [message]);

  return (
    <p
      aria-atomic="true"
      aria-live="assertive"
      className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text outline-none"
      ref={ref}
      tabIndex={-1}
    >
      {message}
    </p>
  );
}

/* --- DL-1: joriy profilning vaqtlari --------------------------------------- */

function EditForm({
  onDone,
  periodLabel,
  profile,
}: {
  onDone: () => void;
  periodLabel: string;
  profile: SnapshotSchedule;
}) {
  const t = useTranslations();
  const noteId = useId();
  const update = useUpdateScheduleTimes();
  const remove = useDeleteSchedule();

  /*
   * ⚠ `react-hook-form` BU FORMADA ISHLATILMAYDI va bu ataylab: yagona
   *   boshqaruv — massiv (`SlotEditor`), ya'ni `register` qiladigan
   *   nomlangan maydon yo'q. RHF ni massiv ustiga o'rash hech qanday
   *   validatsiya bermay, faqat ikkinchi holat manbaini qo'shardi.
   *   DL-2 da esa uchta matn maydoni bor va u RHF + zod ustida quriladi.
   *
   * ⚠ `key={profile.id}` bilan MONTAJ QILINADI (chaqiruvchi tomonda):
   *   qiymatni effektda `setState` bilan to'ldirish so'rov fonda qayta
   *   yuklanganda admin TAHRIRLAYOTGAN ro'yxatni bosib ketardi
   *   (`camera-rename-dialog.tsx:31-38` naqshi).
   */
  const [times, setTimes] = useState<readonly string[]>(() =>
    profile.times.map(formatSlotTime),
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const mode: ScheduleModeValue = profile.mode;
  const canEdit = mode !== "past";
  const canDelete = mode === "future";
  const busy = update.isPending || remove.isPending;

  async function save(): Promise<void> {
    if (times.length === 0) {
      setFormError(t("snapshots.slotRequired"));
      return;
    }
    setFormError(null);
    try {
      await update.mutateAsync({ scheduleId: profile.id, times });
      toast.success(t("snapshots.toastScheduleSaved"));
      onDone();
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  async function destroy(): Promise<void> {
    setFormError(null);
    try {
      await remove.mutateAsync(profile.id);
      toast.success(t("snapshots.toastSeasonalDeleted"));
      setConfirmOpen(false);
      onDone();
    } catch (error) {
      setConfirmOpen(false);
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <form
      aria-describedby={canEdit ? noteId : undefined}
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (canEdit && !busy) void save();
      }}
    >
      {/*
       * Davr matni + SABAB. ⛔ Boshlangan profil uchun o'chirish tugmasi
       * UMUMAN render qilinmaydi (§10.8) — sababi esa shu qatorning
       * `title` ida, ya'ni u yo'q tugmaning o'rnida turgan tushuntirish.
       */}
      <p
        className="text-xs text-text-muted"
        title={canDelete ? undefined : t("snapshots.deleteBlocked")}
      >
        {periodLabel}
      </p>

      {canEdit ? <EditNote id={noteId} /> : null}

      <SlotEditor
        onChange={setTimes}
        readOnly={!canEdit}
        value={times}
      />

      {formError === null ? null : <FormError message={formError} />}

      {canDelete ? (
        <Button
          className="self-start"
          onClick={() => setConfirmOpen(true)}
          size="sm"
          variant="ghost"
        >
          {t("snapshots.deleteSchedule")}
        </Button>
      ) : null}

      <Dialog.Footer>
        {/*
         * ⛔ `past` rejimda «Saqlash» RENDER QILINMAYDI. Ko'rinib turgan,
         *    lekin hech qachon ishlamaydigan tugma tizimni buzuq
         *    ko'rsatardi; yo'q tugma esa qoidani o'zi aytadi.
         *
         * Aksent FAQAT shu yerda — dialogda eng ko'pi bilan bitta (§9.3).
         */}
        {canEdit ? (
          <Button
            aria-disabled={busy ? true : undefined}
            className="sm:flex-1"
            onClick={() => {
              if (!busy) void save();
            }}
            variant="default"
          >
            {busy ? t("common.loading") : t("common.save")}
          </Button>
        ) : null}
        <Dialog.Close asChild>
          <Button className="sm:flex-1" variant="secondary">
            {canEdit ? t("common.cancel") : t("common.close")}
          </Button>
        </Dialog.Close>
      </Dialog.Footer>

      {/*
       * 1-DARAJA (§10.8): jadval hali birorta kadr olmagan, ya'ni
       * o'chirish MA'LUMOT YO'QOTMAYDI va uni qayta qo'shish mumkin.
       * 2-daraja (nom yozib tasdiqlash) faqat UI'dan qaytarib
       * bo'lmaydigan amallar uchun. Fokus BEKOR QILISHDA — buni
       * `ConfirmDialog` ning o'zi kafolatlaydi.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("snapshots.deleteSchedule")}
        description={t("snapshots.deleteScheduleBody", { name: profile.name })}
        isBusy={remove.isPending}
        onConfirm={() => void destroy()}
        onOpenChange={setConfirmOpen}
        open={confirmOpen}
        title={t("snapshots.deleteScheduleTitle")}
      />
    </form>
  );
}

/* --- DL-2: mavsumiy profil -------------------------------------------------- */

type SeasonalFormValues = {
  endsOn: string;
  name: string;
  startsOn: string;
};

/**
 * `Date` -> `YYYY-MM-DD` ko'rsatish mintaqasida (`tariff-dialog.tsx:81`).
 *
 * `en-CA` ATAYIN: uning qisqa sana formati ISO-8601 bilan bir xil, ya'ni
 * natijani `min` atributi va leksik solishtirish uchun ishlatish mumkin.
 * Brauzerning O'Z mintaqasiga tushib qolish TAQIQ — boshqa mintaqadagi
 * foydalanuvchida «ertaga» bir kunga siljirdi (FOUND-05 sinfi).
 */
function isoDateIn(timeZone: string | undefined, value: Date): string | null {
  if (timeZone === undefined) return null;
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).format(value);
}

function CreateForm({
  defaultTimes,
  nextProfileName,
  onDone,
}: {
  /** §4.7 4-band: standart holat — joriy profil vaqtlarining NUSXASI. */
  defaultTimes: readonly string[];
  /** Davr tugagach QAYTADIGAN profil nomi — natija qatorining oxirgi jumlasi. */
  nextProfileName: string | null;
  onDone: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const now = useNow();
  const timeZone = useTimeZone();
  const create = useCreateSeasonalSchedule();

  const nameId = useId();
  const startsId = useId();
  const endsId = useId();

  const today = isoDateIn(timeZone, now);
  /*
   * ⚠ `min` — QULAYLIK, darvoza SERVERDA (`create_seasonal` ning
   *   `schedule_starts_too_soon` tekshiruvi). Klient serverdan
   *   QATTIQROQ bo'lmasligi kerak; mintaqa noma'lum bo'lsa qulaylikdan
   *   voz kechiladi va maydon ochiq qoladi (`tariff-dialog.tsx` qoidasi).
   */
  const minStartsOn =
    today === null
      ? undefined
      : (isoDateIn(timeZone, new Date(now.getTime() + 86_400_000)) ?? undefined);

  const schema = useMemo(
    () =>
      z
        .object({
          endsOn: z.string(),
          name: z.string().trim().min(1).max(NAME_MAX),
          startsOn: z.string().min(1),
        })
        .superRefine((values, ctx) => {
          if (
            minStartsOn !== undefined &&
            values.startsOn !== "" &&
            values.startsOn < minStartsOn
          ) {
            ctx.addIssue({
              code: "custom",
              message: t("snapshots.startsOnTooSoon"),
              path: ["startsOn"],
            });
          }
          if (values.endsOn !== "" && values.endsOn <= values.startsOn) {
            ctx.addIssue({
              code: "custom",
              message: t("snapshots.endsOnBeforeStart"),
              path: ["endsOn"],
            });
          }
        }),
    [minStartsOn, t],
  );

  const { control, formState, handleSubmit, register } =
    useForm<SeasonalFormValues>({
      defaultValues: { endsOn: "", name: "", startsOn: minStartsOn ?? "" },
      mode: "onSubmit",
      resolver: zodResolver(schema),
    });

  /*
   * ⚠ `useWatch` — kuzatilgan qiymat FAQAT shu daraxtni qayta chizadi.
   *   Formaning `watch` metodi butun formani har harfda qayta render
   *   qilardi va uzun formada bu sezilarli (`nvr-form.tsx` da o'rnatilgan
   *   qoida).
   */
  const startsOn = useWatch({ control, name: "startsOn" });
  const endsOn = useWatch({ control, name: "endsOn" });

  const [times, setTimes] = useState<readonly string[]>(() => [
    ...defaultTimes.map(formatSlotTime),
  ]);
  const [formError, setFormError] = useState<string | null>(null);

  const submit = handleSubmit(async (values) => {
    if (times.length === 0) {
      setFormError(t("snapshots.slotRequired"));
      return;
    }
    setFormError(null);
    try {
      await create.mutateAsync({
        endsOn: values.endsOn === "" ? null : values.endsOn,
        name: values.name.trim(),
        startsOn: values.startsOn,
        times,
      });
      toast.success(t("snapshots.toastSeasonalAdded"));
      onDone();
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  });

  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => void submit(event)}>
      <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
        <legend className="mb-4 text-lg font-semibold">
          {t("snapshots.seasonalLegend")}
        </legend>

        <Field
          error={formState.errors.name?.message}
          hint={t("snapshots.scheduleNameHint")}
          id={nameId}
          label={t("snapshots.scheduleName")}
        >
          <Input
            aria-describedby={
              formState.errors.name ? `${nameId}-error` : `${nameId}-hint`
            }
            aria-invalid={formState.errors.name ? true : undefined}
            autoComplete="off"
            id={nameId}
            maxLength={NAME_MAX}
            {...register("name")}
          />
        </Field>

        <Field
          error={formState.errors.startsOn?.message}
          hint={t("snapshots.startsOnHint")}
          id={startsId}
          label={t("snapshots.startsOn")}
        >
          <Input
            aria-describedby={
              formState.errors.startsOn
                ? `${startsId}-error`
                : `${startsId}-hint`
            }
            aria-invalid={formState.errors.startsOn ? true : undefined}
            id={startsId}
            min={minStartsOn}
            type="date"
            {...register("startsOn")}
          />
        </Field>

        <Field
          error={formState.errors.endsOn?.message}
          hint={t("snapshots.endsOnOptional")}
          id={endsId}
          label={t("snapshots.endsOn")}
        >
          <Input
            aria-describedby={
              formState.errors.endsOn ? `${endsId}-error` : `${endsId}-hint`
            }
            aria-invalid={formState.errors.endsOn ? true : undefined}
            id={endsId}
            min={minStartsOn}
            type="date"
            {...register("endsOn")}
          />
        </Field>
      </fieldset>

      <SlotEditor onChange={setTimes} value={times} />

      {/*
       * Jonli natija qatori (§4.7). Oxirgi jumla FAQAT tugash sanasi
       * berilganda VA qaytadigan profil nomi MA'LUM bo'lganda chiqadi:
       * «keyin nima bo'ladi?» savoliga taxmin bilan javob berish
       * kutilmani noto'g'ri shakllantirardi. Bo'lish (split) mantig'i
       * SERVERDA va UI uni TAKRORLAMAYDI.
       */}
      <p className="text-sm text-text-muted" role="status">
        {startsOn === ""
          ? null
          : endsOn !== "" && nextProfileName !== null
            ? t("snapshots.previewBounded", {
                count: times.length,
                from: format.dateTime(new Date(startsOn), {
                  dateStyle: "medium",
                }),
                next: nextProfileName,
                to: format.dateTime(new Date(endsOn), { dateStyle: "medium" }),
              })
            : t("snapshots.previewOpen", {
                count: times.length,
                from: format.dateTime(new Date(startsOn), {
                  dateStyle: "medium",
                }),
              })}
      </p>

      {formError === null ? null : <FormError message={formError} />}

      <Dialog.Footer>
        <Button
          aria-disabled={create.isPending ? true : undefined}
          className="sm:flex-1"
          type="submit"
          variant="default"
        >
          {create.isPending ? t("common.loading") : t("snapshots.addSeasonal")}
        </Button>
        <Dialog.Close asChild>
          <Button className="sm:flex-1" variant="secondary">
            {t("common.cancel")}
          </Button>
        </Dialog.Close>
      </Dialog.Footer>
    </form>
  );
}
