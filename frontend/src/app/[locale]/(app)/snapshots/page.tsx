"use client";

import { Suspense, useState } from "react";
import { useTranslations } from "next-intl";

import { ScheduleCard } from "@/components/snapshots/schedule-card";
import { ScheduleDialog } from "@/components/snapshots/schedule-dialog";
import type { ScheduleDialogRequest } from "@/components/snapshots/schedule-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { EMPTY_CAMERA_FILTERS, useCamerasQuery } from "@/lib/camera-queries";
import { useAuthStore } from "@/lib/auth-store";
import { Link } from "@/i18n/navigation";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * KADR OLISH — 4-FAZANING YAGONA SAHIFASI (UI-SPEC §4.1 [QAROR]).
 *
 * `/schedule`, `/snapshots/[id]`, `/alerts` QURILMAYDI. ⚠ Bu
 * `04-PATTERNS.md` §1.7 dan ATAYIN chekinish va sabab UI-SPEC §4.1 da:
 * jadval — bu fazaning ENG KICHIK yuzasi (uch qator), ijro jurnali esa
 * asosiysi; marshrutni «schedule» deb nomlash sahifaning nomini uning
 * eng kichik qismidan olardi.
 *
 * TO'RT VERTIKAL ZONA (§4.2) va ular HECH QACHON ALMASHMAYDI:
 *   (A) jadval kartasi        — SHU REJADA;
 *   (B) ogohlantirishlar      — 04-11;
 *   (C) kun tanlagichi + xulosa — 04-11;
 *   (D) ijro jurnali          — 04-11.
 *
 * ⛔ (B), (C), (D) UCHUN JOY EGALLANMAYDI VA «TEZ ORADA» BLOKI
 *    YOZILMAYDI. Bo'sh platsholder UI-SPEC ning birorta holatida yo'q:
 *    u foydalanuvchiga hech qachon kelmaydigan va'da berardi va zona
 *    holatlari jadvalining (§6.2) o'n bandidan hech biriga to'g'ri
 *    kelmasdi. Zona shunchaki MAVJUD EMAS.
 *
 * ⚠ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`cameras/page.tsx:85-94` naqshi):
 *   huquqsiz foydalanuvchi uchun ish maydoni UMUMAN render qilinmaydi,
 *   ya'ni `GET /snapshot-schedules/today` ga so'rov ham ketmaydi. Bu 403
 *   ni yashirish uchun emas (u baribir bo'lardi), balki jurnalga
 *   ma'nosiz rad etilgan urinishlar yozilmasligi uchun. Haqiqiy nazorat
 *   serverda: `require_permission(CAMERA_VIEW)`.
 *
 * ⚠ AKSENT BUDJETI (§9.3): bu sahifada birlamchi (aksent fonli) tugma
 *   UMUMAN YO'Q va bu 3-fazadan ATAYIN farq — `/cameras` bir va'dani
 *   bajaradigan HARAKAT sahifasi edi («tugmani bos — kameralar paydo
 *   bo'lsin»), `/snapshots` esa KUZATUV sahifasi va uning to'g'ri
 *   javobi «hamma narsa joyida». E-1 dagi havola ham ikkilamchi.
 *
 * ⚠ USTAGA QADAM QO'SHILMAYDI (§4.9, D-01): admin jadval uchun HECH
 *   NIMA kiritmaydi va usta qadami bo'lsa, hech nima kiritmagan bozor
 *   «chala» ko'rinardi — D-01 ning aynan teskarisi.
 * =============================================================================
 */

export default function SnapshotsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "camera_view")) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("snapshots.title")}
      </h1>

      {/*
       * `Suspense` MAJBURIY (`audit/page.tsx` va `cameras/page.tsx`
       * naqshi): ish maydoni kun tanlagichi bilan birga `?day=` ni
       * `nuqs` orqali o'qiydigan bo'ladi, ya'ni daraxtning shu qismi
       * klient tomonda render qilinadi. Chegara bo'lmasa Next 16 butun
       * marshrutni statik prerender ro'yxatidan chiqarib, BUILD ni
       * yiqitadi.
       *
       * ⚠ CHEGARA HOZIRDAN QO'YILADI, 04-11 da emas: u yerda qo'shilsa
       *   o'zgarish hook qo'shish emas, sahifaning TUZILISHINI qayta
       *   qurish bo'lardi — va oradagi commit build'da yiqilardi.
       */}
      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <SnapshotsWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function SnapshotsWorkspace() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const canManage = hasPermission(principal?.roles ?? [], "camera_manage");

  /*
   * E-1 ning sharti (§10.4). ⚠ `isSuccess` MAJBURIY: `items.length === 0`
   * ni yuklanish paytida ham to'g'ri deb o'qish har ochilishda bir
   * lahzalik «kamera yo'q» chaqnashini berardi — va u aynan eng yomon
   * yolg'on, chunki admin buni nosozlik deb qabul qilardi.
   */
  const cameras = useCamerasQuery(EMPTY_CAMERA_FILTERS);
  const hasNoCameras = cameras.isSuccess && cameras.data.items.length === 0;

  /*
   * ⚠ DIALOG HOLATI URL'DA EMAS (§4.4, 02-UI-SPEC §7.1 dan meros):
   *   URL'da faqat `?day=`, `?issues=`, `?closed=` yashaydi. Jadval
   *   tahririni ulashiladigan havolaga aylantirish uni sahifa holatidan
   *   marshrutga ko'chirardi va «orqaga» tugmasi yarim to'ldirilgan
   *   formani qaytarardi.
   */
  const [dialog, setDialog] = useState<ScheduleDialogRequest | null>(null);

  /*
   * ⛔ E-1 ZONALARNING O'RNINI EGALLAYDI, ular yonida turmaydi.
   *
   * Kamerasiz bozorda jadval kartasi «Bugun 7 marta» deb turardi,
   * holbuki 0 kamera × 7 vaqt = 0 kadr. Ya'ni ekran REJANI ko'rsatib,
   * NATIJA nolligini yashirардi — bu fazaning butun maqsadi esa
   * yo'qlikni ko'rinadigan qilish (§1.2).
   *
   * ⚠ «Jadval qo'shing» bo'sh holati HECH QACHON chiqmaydi (§10.4):
   *   D-01 bo'yicha jadval usta tomonidan avtomatik yoziladi.
   */
  if (hasNoCameras) {
    return (
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center rounded-md border border-border bg-surface px-6 text-sm font-semibold text-text hover:bg-surface-muted"
            href="/cameras"
          >
            {t("snapshots.goToCameras")}
          </Link>
        }
        description={t("snapshots.emptyNoCamerasHint")}
        title={t("snapshots.emptyNoCameras")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* --- ZONA (A): jadval kartasi ------------------------------------ */}
      <section aria-label={t("snapshots.scheduleTitle")}>
        <ScheduleCard
          canManage={canManage}
          onAddSeasonal={() => setDialog({ kind: "create" })}
          onEdit={(profile) =>
            setDialog({ kind: "edit", scheduleId: profile?.id ?? null })
          }
        />
      </section>

      {/*
       * DL-1 va DL-2 — bitta qobiq. Dialog ZONA EMAS: u sahifa holati
       * bo'lib, zonalarning tartibiga umuman ta'sir qilmaydi (§4.2 —
       * zonalar hech qachon almashmaydi).
       */}
      <ScheduleDialog
        onOpenChange={(open) => {
          if (!open) setDialog(null);
        }}
        request={dialog}
      />
    </div>
  );
}
