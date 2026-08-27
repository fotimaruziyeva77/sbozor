"use client";

import { useId, useMemo, useState } from "react";
import { PencilLine } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { Camera } from "@/lib/api-types";
import { useRenameCamera } from "@/lib/camera-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";

/*
 * =============================================================================
 * NOMNI QO'LDA O'ZGARTIRISH VA UNING MA'NOSI (UI-SPEC §6.5, SC#2).
 *
 * `name_overridden` bayrog'i — «mavjudi tegilmaydi» qoidasining aynan
 * mazmuni. ⚠ ADMIN BUNI BILISHI SHART, aks holda u nomini qayta
 * skanerlash bosib ketishidan qo'rqib QAYTA SKANERLAMAYDI — ya'ni
 * fazaning eng muhim takroriy amali qo'rquv tufayli ishlatilmay
 * qolardi. Shuning uchun maydon ostida izoh MAJBURIY.
 *
 * ⚠ QAYTARISH YO'LI HAM SHU DIALOGDA: `[NVR qurilmasidagi nomga
 *   qaytarish]` `name_overridden` ni bekor qiladi va keyingi skan nomni
 *   qurilmadan oladi. Usiz bayroq bir tomonlama bo'lardi — qo'lda
 *   qo'yilgan nomdan qaytish yo'li qolmasdi.
 *
 * ⚠ FORMA ALOHIDA KOMPONENT VA U `key={camera.id}` BILAN MONTAJ
 *   QILINADI. Muqobil variant — maydonni effektda `setState` bilan
 *   to'ldirish — React Compiler qoidasiga uriladi
 *   (`react-hooks/set-state-in-effect`) va undan ham muhimi: so'rov
 *   fonda qayta yuklanganda yangi obyekt havolasi kelib, admin
 *   TERAYOTGAN matnni bosib ketardi. Montaj esa qiymatni AYNAN bir
 *   marta, aynan dialog ochilganda oladi. Bu 03-09 dagi taymer
 *   qarorining aynan bir xil mantiqi.
 *
 * ⛔ SAQLASH TUGMASI QANDAY QULFLANMAYDI — VA NEGA ILGARIGISI YOLG'ON EDI.
 *   Tugma bir vaqtlar bo'sh nomda ARIA holati bilan «yopilardi», lekin
 *   `Button` ning CSS'i faqat NATIVE `disabled` ni biladi
 *   (`disabled:pointer-events-none disabled:opacity-50`). Natijada tugma
 *   ko'rinishda ham, amalda ham OCHIQ turardi — skrinrider esa «yopiq»
 *   deb e'lon qilardi va bosilganda hech nima bo'lmasdi: so'rov yo'q,
 *   xato yo'q, dialog ochiq. Ikki foydalanuvchi ikki xil ilova ko'rardi.
 *
 *   Endi qoida bitta: submit tugmasi FAQAT yuborish jarayoni davomida
 *   yopiladi, bo'sh nom esa zod xabari bo'lib EKRANGA chiqadi. Mexanik
 *   darvoza — `scripts/submit-gate.test.mjs`.
 * =============================================================================
 */

export function CameraRenameDialog({
  camera,
  onOpenChange,
  onSaved,
}: {
  /** `null` — dialog yopiq. Kamera dialog bilan birga keladi. */
  camera: Camera | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const t = useTranslations();

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={camera !== null}>
      <Dialog.Content icon={PencilLine}
        description={t("cameras.renameHint")}
        size="sm"
        srOnlyDescription
        title={t("cameras.rename")}
      >
        {camera === null ? null : (
          <RenameForm camera={camera} key={camera.id} onSaved={onSaved} />
        )}
      </Dialog.Content>
    </Dialog.Root>
  );
}

type RenameValues = { name: string };

function RenameForm({
  camera,
  onSaved,
}: {
  camera: Camera;
  onSaved: () => void;
}) {
  const t = useTranslations();
  const rename = useRenameCamera();
  const fieldId = useId();

  /*
   * Server xatosi ALOHIDA holatda qoladi — u zod xatosi EMAS va forma
   * maydoniga bog'lanmaydi (`marketErrorMessageKey` domen javobini
   * tarjima qiladi). Forma tepasidagi `role="alert"` bloki uning joyi.
   */
  const [error, setError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z.object({
        name: z.string().trim().min(1, { error: t("errors.required") }),
      }),
    [t],
  );

  /*
   * `defaultValues` — montaj lahzasidagi qiymat. Komponent `key={camera.id}`
   * bilan montaj qilinadi (fayl boshidagi izoh), ya'ni urug'lanish
   * semantikasi `useState` bilan boshqarilgan eski shakl bilan AYNAN bir xil
   * qoladi: fon refetch'i admin terayotgan matnni bosib ketmaydi.
   */
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<RenameValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: camera.name },
  });

  async function run(
    input:
      | { cameraId: string; name: string }
      | { cameraId: string; resetToDeviceName: true },
  ): Promise<void> {
    setError(null);
    try {
      await rename.mutateAsync(input);
      toast.success(t("cameras.toastNameSaved"));
      onSaved();
    } catch (cause) {
      setError(t(marketErrorMessageKey(cause)));
    }
  }

  async function onSubmit(values: RenameValues): Promise<void> {
    await run({ cameraId: camera.id, name: values.name.trim() });
  }

  const busy = rename.isPending || isSubmitting;

  return (
    <form
      className="flex flex-col gap-4"
      noValidate
      onSubmit={handleSubmit(onSubmit)}
    >
      <Field
        error={errors.name?.message}
        hint={t("cameras.renameHint")}
        id={fieldId}
        label={t("cameras.nameLabel")}
      >
        {/*
         * Xato IZOHNI ALMASHTIRMAYDI, unga QO'SHILADI (`tariff-dialog.tsx`
         * naqshi): izoh `name_overridden` ning ma'nosini tushuntiradi va
         * usiz admin qayta skanerlashdan qo'rqadi (§6.5).
         */}
        <Input
          aria-describedby={
            errors.name ? `${fieldId}-error ${fieldId}-hint` : `${fieldId}-hint`
          }
          aria-invalid={errors.name ? true : undefined}
          autoComplete="off"
          id={fieldId}
          {...register("name")}
        />
      </Field>

      {error !== null ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {error}
        </p>
      ) : null}

      {/*
       * `ghost` — ikkilamchi yo'l, aksent budjetiga (§2.4) kirmaydi.
       * Tasdiq so'ralmaydi: amal qaytariladi (nomni qayta yozish mumkin)
       * va u hech qanday ma'lumotni yo'qotmaydi.
       *
       * ⚠ `type` ATAYIN yozilmaydi va bu XAVFSIZ: `Button` ning standarti
       *   `type="button"` (`ui/button.tsx`), ya'ni bu tugma formani
       *   YUBORMAYDI. Aks holda bitta bosish ikkita so'rov yuborardi.
       */}
      <Button
        className="self-start"
        onClick={() =>
          void run({ cameraId: camera.id, resetToDeviceName: true })
        }
        size="sm"
        variant="ghost"
      >
        {t("cameras.resetName")}
      </Button>

      <Dialog.Footer>
        {/*
         * ⛔ FAQAT «yuborilyapti» qulfi (fayl boshidagi izoh): bo'sh nom
         *   tugmani YOPMAYDI, u zod xabari bo'lib maydon ostida chiqadi.
         */}
        <Button
          className="sm:flex-1"
          disabled={rename.isPending}
          type="submit"
          variant="default"
        >
          {busy ? t("common.loading") : t("common.save")}
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
