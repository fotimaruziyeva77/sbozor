"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import type { Camera } from "@/lib/api-types";
import { useArchiveCamera } from "@/lib/camera-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";

/*
 * =============================================================================
 * KAMERANI ARXIVLASH — QAYTARILADIGAN AMAL (D-10, UI-SPEC §9).
 *
 * ⚠ FE'L «ARXIVLASH» va bu HECH QAYSI TILDA muhokama qilinmaydi.
 *   Qaytarib bo'lmaydigan yo'q qilish marshruti backendда UMUMAN
 *   YOZILMAGAN: snapshot (4-faza) va zona bog'lanishlari (5-faza)
 *   `cameras.id` ga qadaladi. So'zning o'zi ham darvoza ostida
 *   (`scripts/nvr-copy.test.mjs`, G-4): u bir marta matnga kirsa
 *   tarjima orqali tarqaladi va admin arxivlashni boshqa narsa deb
 *   tushunadi.
 *
 *   ⚠ Shu sababdan taqiqlangan HTTP metodining nomi bu izohda LITERAL
 *     sifatida ham yozilmaydi: G-4 aynan shu daraxtni skanerlaydi va
 *     so'z chegarasi kod atamasini foydalanuvchi matnidan ajratmaydi.
 *     Bu fazada takrorlangan sinf — `camera-queries.ts` dagi bir xil
 *     jumla darvozadan faqat `src/lib/` da yashagani uchun o'tadi.
 *
 * ⚠ 1-DARAJALI TASDIQ, 2-DARAJALI EMAS (UI-SPEC §9.2): 2-daraja (nomni
 *   yozib tasdiqlash) FAQAT UI'dan qaytarib bo'lmaydigan amallar uchun.
 *   Arxivlash qaytariladi — «Arxivdan qaytarish» qatorda turadi. Bu
 *   juftlik MAJBURIY: usiz amal amalda qaytarilmas bo'lardi va u holda
 *   2-daraja talab qilinardi.
 *
 * ⚠ QIZIL RANG OG'IRLIKNI, MATN MA'NONI TASHIYDI. Amal oqibatli
 *   (kamera ishchi ro'yxatdan chiqadi va 4-fazada undan kadr olinmaydi),
 *   shuning uchun tasdiq tugmasi `destructive`. Yolg'on xulosaning oldi
 *   MATN bilan olinadi: `cameras.archiveBody` uchta narsani ANIQ
 *   aytadi — kamera ro'yxatdan olib qo'yiladi, kamera va uning tarixi
 *   saqlanadi, qayta skanerlashda u avtomatik qaytmaydi (§9.4).
 *
 * ⚠ TASDIQ TUGMASINING MATNI — O'Z FE'LI, generic «Tasdiqlash» EMAS:
 *   foydalanuvchi ko'pincha dialog matnini o'qimasdan tugmaga qarab
 *   qaror qiladi.
 *
 * ⚠ FOKUS BEKOR QILISHDA — `confirm-dialog.tsx` buni o'zi bajaradi
 *   (`onOpenAutoFocus`), bu yerda hech narsa qo'shilmaydi.
 * =============================================================================
 */

export function ArchiveCameraDialog({
  camera,
  onArchived,
  onOpenChange,
}: {
  /** `null` — dialog yopiq. Kamera dialog bilan birga keladi. */
  camera: Camera | null;
  onArchived: () => void;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations();
  const archive = useArchiveCamera();
  const [error, setError] = useState<string | null>(null);

  async function confirm(): Promise<void> {
    if (camera === null) return;
    setError(null);
    try {
      await archive.mutateAsync(camera.id);
      toast.success(t("cameras.toastArchived"));
      onArchived();
    } catch (cause) {
      setError(t(marketErrorMessageKey(cause)));
    }
  }

  return (
    <ConfirmDialog
      cancelLabel={t("common.cancel")}
      confirmLabel={
        archive.isPending ? t("common.loading") : t("cameras.archive")
      }
      confirmVariant="destructive"
      description={
        camera === null
          ? ""
          : t("cameras.archiveBody", {
              channel: camera.channel_no,
              // D-16: nom DB kontenti — tarjima qilinmaydi.
              name: camera.name,
            })
      }
      isBusy={archive.isPending}
      level={1}
      onConfirm={() => void confirm()}
      onOpenChange={(next) => {
        if (!next) setError(null);
        onOpenChange(next);
      }}
      open={camera !== null}
      title={t("cameras.archiveTitle")}
    >
      {error !== null ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </ConfirmDialog>
  );
}
