"use client";

import { useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Archive,
  ArchiveRestore,
  MoreHorizontal,
  Pencil,
  Shapes,
  SquarePen,
} from "lucide-react";
import { useFormatter, useLocale, useNow, useTranslations } from "next-intl";

import { CameraStatusBadge } from "@/components/cameras/camera-status-badge";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Camera } from "@/lib/api-types";
import { cn } from "@/lib/cn";
/*
 * Locale prefiksli manzil — `@/i18n/navigation` GA TEGMASDAN. Uzun
 * sabab (o'lchangan: o'sha zanjir vitest ostida to'rtta faylni «0 test»
 * bilan yiqitgan) endi modulning O'ZIDA, `src/lib/locale-href.ts` da:
 * funksiya YETTI joydan bittaga yig'ildi.
 */
import { localeHref } from "@/lib/locale-href";
import { useRelativePast } from "@/lib/format-relative";

/*
 * =============================================================================
 * KAMERA QATORI — ZICH KARTA QATORI, JADVAL EMAS (UI-SPEC §6.1).
 *
 * Jadval telefon ekranida gorizontal skroll talab qilardi va bozor
 * admini bu ekranni ko'pincha telefonda ochadi [MEROS: `user-list.tsx`].
 *
 * SEMANTIKA: `<li>`; qator O'ZI BOSILADIGAN EMAS — faqat ichidagi
 * tugmalar fokuslanadi. Eng ko'pi 32 qator, ya'ni roving tabindex
 * kerak emas va u ortiqcha murakkablik bo'lardi.
 *
 * ⚠ `last_seen_at` META QATORIDA MAJBURIY (UI-SPEC §6.3). U skan
 *   haqiqatan ishlaganining IKKINCHI, MUSTAQIL dalil kanali: admin
 *   natija panelini o'qimasa ham «2 daqiqa oldin» -> «hozir»
 *   o'zgarishini ko'radi. Natija paneli va bu qator bir-birini
 *   tasdiqlaydi.
 *
 * ⚠ NOM DB KONTENTI — TARJIMA QILINMAYDI [MEROS: 1-faza D-16].
 *   `truncate` + `title`: faqat DB kontenti qisqartiriladi, badge va
 *   amallar HECH QACHON qisqartirilmaydi (UI-SPEC §11.7 Qoida 4).
 *
 * ⚠ QATOR `flex-wrap`: ru tilida «Не в сети» + «Смотреть» 360px'da tor.
 *   Kontrakt — badge va amallar bir-birini SIQMAYDI; kerak bo'lsa
 *   amallar keyingi qatorga tushadi.
 * =============================================================================
 */

/**
 * Kanal raqami — HAR DOIM IKKI XONALI (`01`, `07`, `16`).
 *
 * Ro'yxat shu bilan ustunlashadi va u NVR monitoridagi tartibga mos
 * tushadi. Uch xonali kanal (32 kanalli NVR'da bo'lmaydi, lekin
 * kontrakt buni taqiqlamaydi) o'z uzunligida qoladi.
 */
export function channelLabel(channelNo: number): string {
  return String(channelNo).padStart(2, "0");
}

export type CameraRowProps = {
  camera: Camera;
  /** `camera_manage` — usiz nom, arxiv va qaytarish amallari YO'Q. */
  canManage: boolean;
  onArchive: (camera: Camera) => void;
  onRename: (camera: Camera) => void;
  onRestore: (camera: Camera) => void;
  onView: (camera: Camera) => void;
};

export function CameraRow({
  camera,
  canManage,
  onArchive,
  onRename,
  onRestore,
  onView,
}: CameraRowProps) {
  const t = useTranslations();
  const format = useFormatter();

  /*
   * ⚠ `useNow()`, `Date.now()` EMAS: render paytida soatni o'qish sof
   *   emas (`react-hooks/purity`) va SSR bilan klient orasida farq
   *   tug'dirardi. `next-intl` ning hooki qiymatni provayderdan oladi.
   */
  const now = useNow();
  const relativePast = useRelativePast();

  /*
   * Sabab BOSILGANDA e'lon qilinadi (UI-SPEC §8.6). `aria-describedby`
   * uni fokusda ham beradi, lekin sichqoncha bilan bosgan foydalanuvchi
   * uchun jonli hudud kerak — aks holda bosish HECH QANDAY javob
   * bermasdi va bu «buzuq tugma» ta'surotini berardi.
   */
  const [reasonAnnounced, setReasonAnnounced] = useState(false);

  const reasonId = `cam-${camera.id}-offline`;
  const blocked = camera.status !== "online";

  /*
   * IP dan KEYINGI bo'laklar. Model `null` bo'lsa qator qisqaradi,
   * lekin `last_seen_at` HECH QACHON tushib qolmaydi — u majburiy
   * maydon va ayni paytda skanning ikkinchi dalil kanali.
   */
  const metaTail = [
    camera.source_model,
    t("cameras.lastSeen", {
      time: relativePast(new Date(camera.last_seen_at), now),
    }),
  ].filter((part): part is string => Boolean(part));

  return (
    <li>
      <div
        className={cn(
          "flex flex-wrap items-center gap-x-3 gap-y-2 rounded-md border border-border p-3",
          camera.is_archived ? "bg-surface-muted" : "bg-surface",
        )}
      >
        {/*
         * `font-mono text-xs` — HUJJATLASHTIRILGAN ISTISNO (UI-SPEC
         * §2.2): ustunlashgan ro'yxat.
         */}
        <Badge className="font-mono text-xs" tone="neutral">
          {channelLabel(camera.channel_no)}
        </Badge>

        <div className="min-w-0 flex-1">
          <p
            className={cn(
              "flex items-center gap-1 text-sm font-semibold",
              camera.is_archived && "text-text-muted",
            )}
          >
            {/* D-16: kamera nomi DB kontenti — tarjima qilinmaydi. */}
            <span className="truncate" title={camera.name}>
              {camera.name}
            </span>
            {camera.name_overridden ? (
              /*
               * §6.5 — admin nomini qayta skan almashtirmasligini
               * BILISHI SHART, aks holda u nomini yo'qotishdan qo'rqib
               * qayta skanerlamaydi. Uch kanal: ikonka + `sr-only`
               * matn + `title`.
               */
              <span
                className="inline-flex shrink-0 items-center"
                title={t("cameras.nameOverridden")}
              >
                <Pencil
                  aria-hidden="true"
                  className="size-3 text-text-muted"
                />
                <span className="sr-only">{t("cameras.nameOverridden")}</span>
              </span>
            ) : null}
          </p>

          <p className="text-xs text-text-muted">
            {/* IP `font-mono` — qurilma interfeysi bilan solishtiriladi. */}
            <span className="font-mono">{camera.source_ip ?? "—"}</span>
            {metaTail.map((part, index) => (
              <span key={`${index}-${part}`}> · {part}</span>
            ))}
          </p>
        </div>

        <CameraStatusBadge
          isArchived={camera.is_archived}
          status={camera.status}
        />

        {camera.is_archived ? (
          /*
           * ⚠ ARXIVLANGAN QATORDA «Ko'rish» UMUMAN RENDER QILINMAYDI
           *   (UI-SPEC §6.6) — arxivlangan kameraning oqimi go2rtc'da
           *   ro'yxatga OLINMAYDI, ya'ni tugma har doim yiqilardi. Bu
           *   ulanmagan kameradan BOSHQA holat: u yerda oqim printsipial
           *   ravishda mavjud (kamera qaytsa ishlaydi), bu yerda esa
           *   yo'q.
           */
          canManage ? (
            <Button
              onClick={() => onRestore(camera)}
              size="sm"
              variant="secondary"
            >
              <ArchiveRestore aria-hidden="true" />
              {t("cameras.restore")}
            </Button>
          ) : null
        ) : (
          <>
            {blocked ? (
              /*
               * ⚠ TUGMA YASHIRILMAYDI, SABABI AYTILADI (UI-SPEC §8.6).
               *   Yo'qolgan tugma «bu kamerada ko'rish umuman yo'q»
               *   degan YOLG'ON xabar berardi.
               *
               * ⚠ ARIA holati, oddiy `disabled` propi EMAS: `disabled`
               *   tugma fokus olmaydi va skrinrider uni umuman
               *   o'qimaydi — «nega bosilmayapti?» savoliga javob
               *   qoladigan joy yo'qolardi.
               *
               * ⚠ IKKI SHOX, BITTA ELEMENTDA UCHTA TERNARY EMAS: bu
               *   ikki tugmaning ATRIBUTI ham, HANDLERI ham, MA'NOSI
               *   ham boshqa. Ochiq bo'lish ularni bir elementga
               *   siqishdan o'qilishliroq va qabul mezonining
               *   (`disabled` propi yo'q) niyatini ham to'liq bajaradi.
               */
              <Button
                aria-describedby={reasonId}
                aria-disabled="true"
                className="opacity-60"
                onClick={() => setReasonAnnounced(true)}
                size="sm"
                variant="secondary"
              >
                {t("cameras.view")}
              </Button>
            ) : (
              <Button
                onClick={() => onView(camera)}
                size="sm"
                variant="secondary"
              >
                {t("cameras.view")}
              </Button>
            )}

            {canManage ? (
              <RowActions
                camera={camera}
                onArchive={onArchive}
                onRename={onRename}
              />
            ) : null}
          </>
        )}

        {blocked && !camera.is_archived ? (
          <>
            <span className="sr-only" id={reasonId}>
              {t("cameras.viewDisabledOffline")}
            </span>
            <span className="sr-only" role="status">
              {reasonAnnounced ? t("cameras.viewDisabledOffline") : ""}
            </span>
          </>
        ) : null}
      </div>
    </li>
  );
}

/**
 * Qator amallari — `DropdownMenu` naqshi [KOD: `user-list.tsx:215-251`].
 *
 * ⚠ «Ko'rish» MENYUGA TUSHMAYDI: u eng ko'p ishlatiladigan amal va uni
 *   ikki bosish ortiga yashirish har kuni takrorlanadigan ishni
 *   qimmatlashtirardi.
 *
 * ⚠ 5-FAZA MENYUGA AYNAN BITTA YOZUV QO'SHADI — «Kamera zonalari»
 *   (UI-SPEC §5.5, navigatsiya byudjeti §4.2). U menyuda va qatorda
 *   emas, chunki zona chizish — BIR MARTALIK sozlash ishi: «Ko'rish»
 *   har kuni bosiladi, zonalar esa kamerani ulagandan keyin bir marta.
 *   Ikkalasini yonma-yon qo'yish kundalik amalni sekinlashtirardi.
 *
 * ⚠ ARXIVLANGAN KAMERADA MENYU UMUMAN YO'Q (yuqoridagi shox), ya'ni
 *   zonalarga yo'l ham yopiq. Bu to'g'ri: arxivlangan kamera kadr
 *   bermaydi, ya'ni muharrir baribir Z-2 da to'xtardi.
 */
function RowActions({
  camera,
  onArchive,
  onRename,
}: {
  camera: Camera;
  onArchive: (camera: Camera) => void;
  onRename: (camera: Camera) => void;
}) {
  const t = useTranslations();
  const locale = useLocale();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={`${t("cameras.actions")}: ${camera.name}`}
        className="inline-flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface transition-colors hover:bg-surface-muted"
      >
        <MoreHorizontal aria-hidden="true" className="size-4" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          className="z-50 mt-1 min-w-48 rounded-md border border-border bg-surface p-1 shadow-raised"
          sideOffset={4}
        >
          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            onSelect={() => onRename(camera)}
          >
            <SquarePen aria-hidden="true" className="size-4" />
            {t("cameras.rename")}
          </DropdownMenu.Item>

          {/*
           * `asChild` — havola SEMANTIKASI saqlanadi: skrinrider «havola»
           * deb o'qiydi, o'rta tugma yangi tabda ochadi va manzil holat
           * satrida ko'rinadi. `onSelect` + dasturiy o'tish bularning
           * uchalasini ham yo'qotardi.
           */}
          <DropdownMenu.Item asChild>
            <a
              className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
              href={localeHref(locale, `/cameras/${camera.id}/zones`)}
            >
              <Shapes aria-hidden="true" className="size-4" />
              {t("cameraZones.title")}
            </a>
          </DropdownMenu.Item>

          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            onSelect={() => onArchive(camera)}
          >
            <Archive aria-hidden="true" className="size-4" />
            {t("cameras.archive")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
