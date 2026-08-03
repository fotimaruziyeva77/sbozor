"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

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
      <Dialog.Content
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

  const [name, setName] = useState(() => camera.name);
  const [error, setError] = useState<string | null>(null);

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

  const busy = rename.isPending;
  const invalid = name.trim().length === 0;

  function save(): void {
    if (invalid || busy) return;
    void run({ cameraId: camera.id, name: name.trim() });
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        save();
      }}
    >
      <Field
        hint={t("cameras.renameHint")}
        id={fieldId}
        label={t("cameras.nameLabel")}
      >
        <Input
          aria-describedby={`${fieldId}-hint`}
          autoComplete="off"
          id={fieldId}
          onChange={(event) => setName(event.target.value)}
          value={name}
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
        <Button
          aria-disabled={invalid || busy ? true : undefined}
          className="sm:flex-1"
          onClick={save}
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
