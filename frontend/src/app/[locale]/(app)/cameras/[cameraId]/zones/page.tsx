"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";

import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ZoneEditor } from "@/components/camera-zones/zone-editor";
import {
  businessDayIn,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Link, useRouter } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/auth-store";
import {
  useCameraFrame,
  useCameraZones,
  useFrameImageHref,
  zoneEditorState,
} from "@/lib/camera-zone-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * ZONA MUHARRIRI — `/cameras/{id}/zones` (AI-01, UI-SPEC §4.2).
 *
 * ⚠ NEGA `/cameras` OSTIDA, MUSTAQIL BO'LIM EMAS (§4.2): zona kameraning
 *   ustiga chizilgan kontur, u kamerasiz mavjud emas. Alohida bo'lim
 *   navigatsiyaga yozuv qo'shardi va admin «kameralar» bilan «zonalar»
 *   orasida nima farq borligini har safar o'ylardi.
 *
 * ⚠ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`cameras/page.tsx:85-94` naqshi):
 *   huquqsiz foydalanuvchi uchun ish maydoni UMUMAN render qilinmaydi,
 *   ya'ni `GET /camera-zones` ga so'rov ham ketmaydi. Haqiqiy nazorat
 *   serverda: `require_permission(CAMERA_MANAGE)`.
 *
 * ⛔ `camera_manage` — `camera_view` EMAS. Direktor zonalarni KO'RADI
 *    (bandlik hisobotining rasm-dalili zonalarsiz ma'nosiz), lekin
 *    o'zgartira olmaydi (05-06 router docstringi). Muharrir — YOZUV
 *    yuzasi, ya'ni uning darvozasi ham yozuv huquqi.
 *
 * ⚠ `Suspense` MAJBURIY (`cameras/page.tsx:102-108`): ish maydoni klient
 *   hooklariga tayanadi. Chegara bo'lmasa Next 16 butun sahifani statik
 *   prerender ro'yxatidan chiqarardi va build yiqilardi.
 *
 * ⛔ URL HOLATI: bu sahifada `nuqs` bilan yuritiladigan holat YO'Q.
 *   Chizish rejimi, zoom/pan va undo steki — SESSIYA holati (§4.5):
 *   ularni URL'ga yozish yarim tahrirlangan poligonni ulashiladigan
 *   qilardi va «orqaga» tugmasi undo'ga aylanardi.
 * =============================================================================
 */

export default function CameraZonesPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "camera_manage")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("cameraZones.title")}
      </h1>

      <Suspense
        fallback={
          <BrandLoader />
        }
      >
        <ZonesWorkspace />
      </Suspense>
    </div>
  );
}

function ZonesWorkspace() {
  const t = useTranslations();
  const router = useRouter();
  const params = useParams<{ cameraId: string }>();
  const cameraId = params.cameraId;

  /*
   * ⚠ BIZNES-KUN KO'RSATISH MINTAQASIDA hisoblanadi (`day-picker.tsx:59`):
   *   brauzerning o'z mintaqasiga tushib qolish Toshkentdan boshqa
   *   mintaqadagi foydalanuvchida kunni bir kunga siljitardi va kadr
   *   izlash noto'g'ri kunga tushardi.
   */
  const todayIso = businessDayIn("Asia/Tashkent", new Date());
  const yesterdayIso = shiftIsoDay(todayIso, -1);

  const zones = useCameraZones(cameraId);
  const frame = useCameraFrame(cameraId, todayIso, yesterdayIso);
  const frameHref = useFrameImageHref(frame.frame?.snapshot_id ?? null);

  const state = zoneEditorState({
    frameSnapshotId: frame.frame?.snapshot_id ?? null,
    frameWidth: zones.data?.frame_width,
    isError: zones.isError || frame.isError,
    isPending: zones.isPending || frame.isPending,
  });

  /* Z-1 — kadr va zonalar yuklanmoqda. */
  if (state === "loading") {
    return (
      <div aria-busy="true" className="flex flex-col gap-4" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="aspect-video w-full" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>
    );
  }

  /* Z-8 — yuklashda xato. Meros blok + [Qayta urinish]. */
  if (state === "load-failed") {
    return (
      <div
        className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
        role="alert"
      >
        <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
        <p className="text-sm">{t("errors.loadFailedBody")}</p>
        <Button onClick={() => void zones.refetch()} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  /*
   * ⛔ Z-2 — MUHARRIR OCHILMAYDI. Fonsiz chizish ma'nosiz: admin bo'sh
   *    to'rtburchakka poligonlar qo'yib, ular kadrda qayerga tushishini
   *    KO'RMASDI va natijani faqat birinchi bandlik hisobotida sezardi.
   *    Keyingi qadam ANIQ — kadr olish bo'limi (E-1).
   */
  if (state === "no-frame") {
    return (
      <EmptyState
        action={
          /*
           * `Button` `asChild` ni QO'LLAB-QUVVATLAMAYDI (u har doim
           * `<button>` chizadi), shuning uchun havola `snapshots/page.tsx:165`
           * dagi naqsh bilan stillanadi: `min-h-11` — barmoq nishoni.
           */
          <Link
            className="inline-flex min-h-11 items-center rounded-md border border-border bg-surface px-6 text-sm font-semibold text-text hover:bg-surface-muted"
            href="/snapshots"
          >
            {t("cameraZones.goToCapture")}
          </Link>
        }
        description={t("cameraZones.emptyNoFrameHint")}
        title={t("cameraZones.emptyNoFrame")}
      />
    );
  }

  /*
   * ⚠ `key={cameraId}` — kamera almashganda muharrir QAYTA MONTAJ
   *   qilinadi. Muqobil variant (effektda `setState`) React Compiler
   *   qoidasiga uriladi va undan ham muhimi: fonda kelgan javob admin
   *   TAHRIRLAYOTGAN poligonlarni bosib ketardi
   *   (`camera-rename-dialog.tsx:30-37` da o'rnatilgan qaror).
   */
  return (
    <ZoneEditor
      cameraId={cameraId}
      frameHeight={zones.data?.frame_height ?? 9}
      frameHref={frameHref}
      frameTakenAt={frame.frame?.scheduled_at ?? null}
      frameWidth={zones.data?.frame_width ?? 16}
      initialZones={zones.data?.items ?? []}
      key={cameraId}
      onLeave={() => router.push("/cameras")}
    />
  );
}
