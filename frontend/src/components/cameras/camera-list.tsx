"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";
import { toast } from "sonner";

import { ArchiveCameraDialog } from "@/components/cameras/archive-camera-dialog";
import { cameraEmptyKind } from "@/components/cameras/camera-page-state";
import { CameraRenameDialog } from "@/components/cameras/camera-rename-dialog";
import { CameraRow } from "@/components/cameras/camera-row";
import { LiveViewDialog } from "@/components/cameras/live-view-dialog";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { Camera } from "@/lib/api-types";
import { useCamerasQuery, useRestoreCamera } from "@/lib/camera-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";

/*
 * =============================================================================
 * KAMERALAR REESTRI (UI-SPEC §6.1, §6.6, §10).
 *
 * ⚠ TARTIB `channel_no` BO'YICHA O'SISH — HAR DOIM, va SARALASH
 *   BOSHQARUVI YO'Q. Kanal raqami NVR dagi JISMONIY uyaga mos keladi va
 *   admin uni shu tartibda ko'radi (NVR monitorida ham shunday). Boshqa
 *   saralash uni chalkashtirardi. Tartib SERVERDA hal qilinadi
 *   (`camera-queries.ts` — klientda qayta saralash uchala tilda boshqa
 *   natija berardi).
 *
 * ⚠ QIDIRUV MAYDONI YO'Q: 16/32 kanalli NVR'da eng ko'pi 32 qator va
 *   ular kanal bo'yicha saralangan. Qidiruv ekranga affordans qo'shib,
 *   hech narsa bermasdi.
 *
 * TO'RTLIK [KOD: `user-list.tsx:80-133`]: `isPending` / `isError` /
 * bo'sh / natija. Har biri BOSHQA keyingi qadamni ko'rsatadi.
 *
 * ⚠ ARXIV SANOG'I ALOHIDA SO'ROV BILAN OLINADI va bu ataylab. Standart
 *   filtr arxivlanganlarni YASHIRADI, ya'ni asosiy javobda ular
 *   umuman yo'q — sanoqni undan hisoblab bo'lmaydi. Muqobil variant
 *   (har doim arxiv bilan so'rab, klientda filtrlash) audit izini
 *   BUZARDI: `camera-queries.ts` izohi «admin checkbox'ni ataylab
 *   yoqdi» va «umuman tegmadi» ni ikki xil hodisa deb ataydi va bu
 *   farq `audit_log.new_value.filters` da ko'rinadi.
 * =============================================================================
 */

/** URL parametrlari (`stall-filters.tsx` naqshi). */
const cameraFilterParsers = {
  status: parseAsString.withDefault(""),
  archived: parseAsString.withDefault(""),
};

export function CameraList({
  canManage,
  hasNvr,
  nvrId,
  onDiscover,
}: {
  canManage: boolean;
  hasNvr: boolean;
  /** Bozorning NVR qurilmasi; `null` bo'lsa filtr qo'yilmaydi. */
  nvrId: string | null;
  onDiscover: () => void;
}) {
  const t = useTranslations();
  const tStatus = useTranslations("cameras.status");

  const [urlFilters, setUrlFilters] = useQueryStates(cameraFilterParsers);

  const scope = nvrId ?? "";
  const cameras = useCamerasQuery({
    archived: urlFilters.archived,
    nvrId: scope,
    status: urlFilters.status,
  });

  /*
   * Arxiv sanog'i — filtrdan MUSTAQIL so'rov: u checkbox'ning
   * ko'rinishini hal qiladi, ya'ni checkbox o'zi hech qachon o'z
   * sanog'ini o'zgartira olmaydi.
   */
  const archivedProbe = useCamerasQuery({
    archived: "true",
    nvrId: scope,
    status: "",
  });
  const archivedCount = (archivedProbe.data?.items ?? []).filter(
    (camera) => camera.is_archived,
  ).length;

  const restore = useRestoreCamera();

  const [renaming, setRenaming] = useState<Camera | null>(null);
  const [archiving, setArchiving] = useState<Camera | null>(null);
  const [viewing, setViewing] = useState<Camera | null>(null);

  async function restoreCamera(camera: Camera): Promise<void> {
    try {
      await restore.mutateAsync(camera.id);
      // Tasdiq dialogi YO'Q (§9.3): amal zararsiz — kamera ro'yxatga
      // qaytadi, boshqa hech narsa o'zgarmaydi.
      toast.success(t("cameras.toastRestored"));
    } catch (cause) {
      toast.error(t(marketErrorMessageKey(cause)));
    }
  }

  const items = cameras.data?.items ?? [];

  const filtersActive = urlFilters.status !== "";
  const empty = cameraEmptyKind({
    /*
     * ⚠ E-4 («arxivda hech narsa yo'q») BU YUZADA YETIB BO'LMAYDIGAN
     *   holat: checkbox faqat `archivedCount > 0` bo'lganda render
     *   qilinadi, ya'ni «arxivni ko'rsat» yoqilgan bo'lsa kamida bitta
     *   arxivlangan kamera bor. Qaror sof funksiyada QOLADI —
     *   kelajakdagi «faqat arxiv» ko'rinishi uni to'ldiradi.
     */
    archivedOnly: false,
    filtersActive,
    hasNvr,
    visibleCount: items.length,
  });

  if (cameras.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {/* Uchta qator — REAL qator balandligida (§10.1). */}
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>
    );
  }

  if (cameras.isError) {
    return (
      <div
        className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
        role="alert"
      >
        <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
        <p className="text-sm">{t("errors.loadFailedBody")}</p>
        <Button onClick={() => void cameras.refetch()} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/*
       * ⚠ FILTR QATORI `fieldset` EMAS (§12.2): ikki MUSTAQIL boshqaruv
       *   va ularga umumiy yorliq berish yolg'on guruh yaratardi. Har
       *   biri o'z yorlig'iga ega.
       *
       * Qator faqat ro'yxat BO'SH BO'LMAGANDA yoki filtr allaqachon
       * qo'yilganda chiziladi: birinchi kamera topilmasdan oldin filtr
       * hech narsani filtrlamaydi.
       */}
      {items.length > 0 || filtersActive ? (
        <div className="flex flex-wrap items-end gap-4">
          <Field
            className="min-w-40"
            id="camera-status"
            label={t("cameras.filterStatus")}
          >
            <Select
              id="camera-status"
              onChange={(event) =>
                void setUrlFilters({ status: event.target.value })
              }
              value={urlFilters.status}
            >
              <option value="">{t("cameras.filterAll")}</option>
              {/* Holat — enum, ya'ni bu YAGONA joyda tarjima qilinadi. */}
              <option value="online">{tStatus("online")}</option>
              <option value="offline">{tStatus("offline")}</option>
            </Select>
          </Field>

          {archivedCount > 0 ? (
            <div className="flex flex-wrap items-center gap-3">
              {/* Yorliq `min-h-11` — barmoq nishoni (§2.1). */}
              <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
                <input
                  checked={urlFilters.archived === "true"}
                  className="size-4 accent-accent"
                  onChange={(event) =>
                    void setUrlFilters({
                      archived: event.target.checked ? "true" : "",
                    })
                  }
                  type="checkbox"
                />
                {t("cameras.showArchived")}
              </label>
              <span className="text-xs text-text-muted">
                {t("cameras.archivedCount", { count: archivedCount })}
              </span>
            </div>
          ) : null}

          {filtersActive ? (
            <Button
              className="min-h-11"
              onClick={() => void setUrlFilters({ archived: "", status: "" })}
              size="sm"
              variant="ghost"
            >
              {t("cameras.clearFilters")}
            </Button>
          ) : null}
        </div>
      ) : null}

      {empty === "no-cameras" ? (
        <EmptyState
          action={
            canManage ? (
              <Button onClick={onDiscover} size="lg" variant="default">
                <Search aria-hidden="true" />
                {t("cameras.discover")}
              </Button>
            ) : null
          }
          description={t("cameras.emptyNoCamerasHint")}
          title={t("cameras.emptyNoCameras")}
        />
      ) : empty === "filtered" ? (
        <EmptyState
          description={t("cameras.emptyFilteredHint")}
          title={t("cameras.emptyFiltered")}
        />
      ) : empty === "archived" ? (
        <EmptyState
          description={t("cameras.emptyArchivedHint")}
          title={t("cameras.emptyArchived")}
        />
      ) : empty === "no-nvr" ? (
        /*
         * E-1 zona (A) ning ishi — bu yerda ro'yxat JIM qoladi.
         * Ikkinchi «NVR ulash» taklifi ikkita birlamchi tugma
         * tug'dirardi (§2.4 — aksent budjeti).
         */
        null
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((camera) => (
            <CameraRow
              camera={camera}
              canManage={canManage}
              key={camera.id}
              newestCaptureAt={cameras.data?.newest_capture_at ?? null}
              onArchive={setArchiving}
              onRename={setRenaming}
              onRestore={(target) => void restoreCamera(target)}
              onView={setViewing}
            />
          ))}
        </ul>
      )}

      <CameraRenameDialog
        camera={renaming}
        onOpenChange={(next) => {
          if (!next) setRenaming(null);
        }}
        onSaved={() => setRenaming(null)}
      />

      <ArchiveCameraDialog
        camera={archiving}
        onArchived={() => setArchiving(null)}
        onOpenChange={(next) => {
          if (!next) setArchiving(null);
        }}
      />

      {/*
       * ⚠ DIALOG FAQAT TANLANGAN KAMERA UCHUN MONTAJ QILINADI va
       *   yopilganda butunlay chiqariladi: «dialog yopilishi = oqim
       *   to'xtashi» kafolatining strukturaviy yarmi (§8.1).
       */}
      {viewing !== null ? (
        <LiveViewDialog
          camera={viewing}
          onOpenChange={(next) => {
            if (!next) setViewing(null);
          }}
          onRefreshList={() => {
            setViewing(null);
            void cameras.refetch();
          }}
          open
        />
      ) : null}
    </div>
  );
}
