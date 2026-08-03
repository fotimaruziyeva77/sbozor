"use client";

import { Suspense, useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryState } from "nuqs";

import {
  cameraEmptyKind,
  isDiscoveryRunId,
} from "@/components/cameras/camera-page-state";
import { NvrCard } from "@/components/cameras/nvr-card";
import { NvrForm } from "@/components/cameras/nvr-form";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { NvrDevice } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import {
  discoveryRunIdOf,
  EMPTY_CAMERA_FILTERS,
  useCamerasQuery,
  useNvrDevicesQuery,
  useStartDiscovery,
} from "@/lib/camera-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * KAMERALAR — 3-FAZANING YAGONA SAHIFASI (UI-SPEC §3.1 [QAROR]).
 *
 * `/cameras/new`, `/cameras/[id]`, `/cameras/nvr` QURILMAYDI. Sabablar:
 *   1. MVP'da bitta NVR — qurilmalar ro'yxati marshruti bitta elementli
 *      ro'yxatni ko'rsatardi;
 *   2. SC#1 ning va'dasi «forma -> tugma -> kameralar», ya'ni OQIM
 *      UZLUKSIZ bo'lishi kerak; uch marshrutga bo'lish uni uch
 *      navigatsiyaga bo'lardi va har o'tishda «endi nima?» savolini
 *      tug'dirardi;
 *   3. «6 ta kamera qo'shildi» natijasi kameralar ro'yxatining YONIDA
 *      turishi kerak — boshqa sahifada u kontekstini yo'qotardi.
 *
 * UCH VERTIKAL ZONA (§3.2) va ular HECH QACHON ALMASHMAYDI:
 *   (A) NVR kartasi yoki formasi;
 *   (B) kashfiyot paneli;
 *   (C) kameralar ro'yxati.
 *
 * ⚠ (B) PAYDO BO'LGANDA (C) O'Z JOYIDA QOLADI. Qayta skanerlash paytida
 *   mavjud ro'yxatning yo'qolishi «kameralarim yo'qolib ketdimi?» degan
 *   qo'rquv tug'diradi — shuning uchun ro'yxat almashtirilmaydi, u
 *   faqat `aria-busy="true"` oladi va yangilanishdan keyin joyida
 *   yangilanadi (§10.1).
 *
 * ⚠ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`users/page.tsx:54-63` naqshi):
 *   huquqsiz foydalanuvchi uchun ish maydoni UMUMAN render qilinmaydi,
 *   ya'ni `GET /nvr-devices` va `GET /cameras` ga so'rov ham ketmaydi.
 *   Bu 403 ni yashirish uchun emas (u baribir bo'lardi), balki jurnalga
 *   ma'nosiz rad etilgan urinishlar yozilmasligi uchun. Haqiqiy nazorat
 *   serverda: `require_permission(CAMERA_VIEW)` (T-01-70).
 *
 * ⚠ AKSENT BUDJETI (§2.4): sahifada BIRLAMCHI (aksent fonli) tugma ENG
 *   KO'PI BILAN BITTA va uning uchta holati O'ZARO ISTISNO:
 *     NVR yo'q             -> [NVR ulash]        (zona A, `device === null`)
 *     NVR bor, kamera yo'q -> [Kameralarni topish] (zona C, `hasNvr === true`)
 *     hammasi bor          -> birlamchi tugma UMUMAN YO'Q
 *   Ikkala shox ham bir vaqtda faol bo'la olmaydi: birinchisi
 *   qurilmaning YO'QLIGIGA, ikkinchisi esa uning BORLIGIGA bog'langan.
 *   Karta amallarining uchalasi ham ikkilamchi — aynan shu sababdan.
 *
 *   ⚠ Tugma variantining nomi bu izohda LITERAL yozilmaydi: qabul
 *     mezoni uni grep bilan SANAYDI va izohdagi nusxa budjetni yolg'on
 *     oshirib ko'rsatardi (bu fazada besh marta takrorlangan sinf).
 *
 * ⚠ TOAST QO'YILMAYDIGAN JOYLAR (§10.4 [QAROR]): kashfiyot tugashi
 *   (natija panelining o'zi tasdiq), ulanish testi natijasi (blokning
 *   o'zi tasdiq), 409 poyga holati va jonli ko'rishning ochilishi.
 *   Ekranda allaqachon ko'rinadigan natija ustiga toast qo'yish
 *   e'tiborni ikkiga bo'ladi. Bu sahifada YAGONA toast — T-5 («NVR
 *   saqlandi») va u formada.
 * =============================================================================
 */

export default function CamerasPage() {
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
        {t("cameras.title")}
      </h1>

      {/*
       * `Suspense` MAJBURIY (`audit/page.tsx:25-26`): ish maydoni
       * `?run=` ni `nuqs` bilan o'qiydi, ya'ni daraxtning shu qismi
       * klient tomonda render qilinadi. Chegara bo'lmasa Next 16
       * butun sahifani statik prerender ro'yxatidan chiqarardi va
       * build yiqilardi.
       */}
      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <CamerasWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function CamerasWorkspace() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const canManage = hasPermission(principal?.roles ?? [], "camera_manage");

  /*
   * `?run={uuid}` — YAGONA URL'da yashaydigan dialog/panel holati
   * (§3.1, §5.4). `history: "replace"` — kashfiyot boshlanishi brauzer
   * tarixiga yozuv qo'shmaydi: «orqaga» tugmasi adminni o'sha sahifaga
   * qaytarardi va u buni nosozlik deb tushunardi.
   */
  const [run, setRun] = useQueryState(
    "run",
    parseAsString.withDefault("").withOptions({ history: "replace" }),
  );

  const devices = useNvrDevicesQuery();
  const cameras = useCamerasQuery(EMPTY_CAMERA_FILTERS);
  const startDiscovery = useStartDiscovery();

  const [formOpen, setFormOpen] = useState(false);
  const [rescanError, setRescanError] = useState<string | null>(null);

  const device: NvrDevice | null = devices.data?.items[0] ?? null;

  /*
   * ⚠ YAROQSIZ `?run=` JIMGINA TOZALANADI va XATO KO'RSATILMAYDI
   *   (§5.4 oxirgi qatori): eski havolani ochish yoki qo'lda yozilgan
   *   parametr NOSOZLIK EMAS. Xato blokini ko'rsatish adminni mavjud
   *   bo'lmagan muammoni qidirishga majbur qilardi.
   */
  useEffect(() => {
    if (run !== "" && !isDiscoveryRunId(run)) void setRun(null);
  }, [run, setRun]);

  async function beginDiscovery(nvrId: string): Promise<void> {
    setRescanError(null);
    try {
      const started = await startDiscovery.mutateAsync(nvrId);
      void setRun(started.run_id);
    } catch (error) {
      /*
       * 409 XATO EMAS (§5.6): ikki admin (yoki bitta admin ikki tabda)
       * tugmani bir vaqtda bosishi — normal ish jarayoni. Mavjud
       * yugurish qabul qilinadi va u ham TOASTSIZ (§10.4).
       */
      const existing = discoveryRunIdOf(error);
      if (existing !== null) {
        void setRun(existing);
        return;
      }
      setRescanError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {rescanError !== null ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {rescanError}
        </p>
      ) : null}

      {/* --- ZONA (A): NVR kartasi yoki formasi -------------------------- */}
      <section aria-label={t("cameras.nvrCard")}>
        {devices.isPending ? (
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-40" />
          </div>
        ) : devices.isError ? (
          <LoadFailed onRetry={() => void devices.refetch()} />
        ) : device === null || formOpen ? (
          <NvrZoneWithoutDevice
            canManage={canManage}
            device={device}
            formOpen={formOpen}
            onCancel={() => setFormOpen(false)}
            onOpenForm={() => setFormOpen(true)}
            onSaved={(result) => {
              setFormOpen(false);
              if (result.runId !== null) void setRun(result.runId);
            }}
          />
        ) : (
          <NvrCard
            device={device}
            onDiagnose={() => setFormOpen(true)}
            onRescan={() => void beginDiscovery(device.id)}
          />
        )}
      </section>

      {/*
       * --- ZONA (B): kashfiyot paneli ---------------------------------
       *
       * ⚠ JOY QOLDIRILDI — panelning o'zi 03-10 da (UI-SPEC §5.2/§5.3:
       *   S1…S5 bosqichlari, poll va natija hisoblagichlari). Bu rejada
       *   `?run=` PARSE QILINADI, TEKSHIRILADI va SAQLANADI, ya'ni
       *   03-10 uni tayyor holatda oladi.
       *
       *   Bu yerda oraliq «Boshlanmoqda» matni ATAYIN chizilmaydi:
       *   03-09 yugurishni poll QILMAYDI, ya'ni allaqachon tugagan
       *   yugurish uchun ham «boshlanmoqda» deb turaverardi — YOLG'ON
       *   holat ko'rsatishdan ko'ra hech narsa ko'rsatmaslik halolroq.
       */}

      {/* --- ZONA (C): kameralar ro'yxati -------------------------------- */}
      <section aria-busy={cameras.isFetching} aria-label={t("cameras.title")}>
        {cameras.isPending ? (
          <div
            aria-busy="true"
            className="flex flex-col gap-3"
            role="status"
          >
            <span className="sr-only">{t("common.loading")}</span>
            {/* Uchta qator — REAL qator balandligida (§10.1). */}
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : cameras.isError ? (
          <LoadFailed onRetry={() => void cameras.refetch()} />
        ) : (
          <CameraListZone
            canManage={canManage}
            hasNvr={device !== null}
            onDiscover={() => {
              if (device !== null) void beginDiscovery(device.id);
            }}
            visibleCount={cameras.data?.items.length ?? 0}
          />
        )}
      </section>
    </div>
  );
}

/* --- Zona (A) ning qurilmasiz holati -------------------------------------- */

function NvrZoneWithoutDevice({
  canManage,
  device,
  formOpen,
  onCancel,
  onOpenForm,
  onSaved,
}: {
  canManage: boolean;
  device: NvrDevice | null;
  formOpen: boolean;
  onCancel: () => void;
  onOpenForm: () => void;
  onSaved: (result: { runId: string | null }) => void;
}) {
  const t = useTranslations();

  if (formOpen) {
    /*
     * Diagnostika rejimi: mavjud qurilmaning manzili va logini
     * oldindan to'ldiriladi, parol esa BO'SH (D-12 — u bizda ochiq
     * matnda yo'q va qaytarilmaydi ham).
     */
    return (
      <NvrForm
        defaultAddress={device === null ? "" : formatAddress(device)}
        defaultUsername={device?.username ?? ""}
        onCancel={onCancel}
        onSaved={onSaved}
      />
    );
  }

  /*
   * E-1 — «NVR umuman ulanmagan» (§10.2). ⚠ E-2 BILAN HECH QACHON
   * ARALASHMAYDI: bu shoxga faqat `device === null` bo'lganda kelinadi,
   * E-2 esa qurilma BOR bo'lgan holat. Ikkalasining keyingi qadami
   * butunlay boshqa va aynan shuning uchun matn ham, tugma ham boshqa.
   */
  return (
    <EmptyState
      action={
        canManage ? (
          <Button onClick={onOpenForm} size="lg" variant="default">
            <Plus aria-hidden="true" />
            {t("cameras.connectNvr")}
          </Button>
        ) : null
      }
      description={t("cameras.emptyNoNvrHint")}
      title={t("cameras.emptyNoNvr")}
    />
  );
}

/* --- Zona (C) ------------------------------------------------------------- */

function CameraListZone({
  canManage,
  hasNvr,
  onDiscover,
  visibleCount,
}: {
  canManage: boolean;
  hasNvr: boolean;
  onDiscover: () => void;
  visibleCount: number;
}) {
  const t = useTranslations();

  const empty = cameraEmptyKind({
    // Filtr qatori 03-10 da keladi; bugun filtr YO'Q, ya'ni E-3/E-4 ga
    // kelinmaydi — lekin qaror shu yerda, bitta joyda yashaydi.
    archivedOnly: false,
    filtersActive: false,
    hasNvr,
    visibleCount,
  });

  if (empty === "no-cameras") {
    return (
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
    );
  }

  if (empty === "filtered") {
    return (
      <EmptyState
        description={t("cameras.emptyFilteredHint")}
        title={t("cameras.emptyFiltered")}
      />
    );
  }

  if (empty === "archived") {
    return (
      <EmptyState
        description={t("cameras.emptyArchivedHint")}
        title={t("cameras.emptyArchived")}
      />
    );
  }

  /*
   * ⚠ QATORLARNING O'ZI 03-10 DA (UI-SPEC §6). Bu rejaning yuzasi —
   *   NVR ulash oqimi; kamera qatori esa o'z kontraktini (nom
   *   o'zgartirish, arxivlash, jonli ko'rish) olib keladi va uni yarim
   *   holatda chizish 03-10 uchun qayta yozishdan boshqa narsa
   *   bermasdi. `empty === "none"` shoxi ATAYIN bo'sh.
   */
  return null;
}

/* --- Yordamchilar --------------------------------------------------------- */

/**
 * Meros xato bloki (§10.3) — ro'yxat yoki karta yuklanmaganda.
 *
 * ⚠ `NvrErrorBlock` EMAS: bu NVR ning xatosi emas, BIZNING API'ning
 *   xatosi. Ikkalasini bitta blokka yig'ish adminni NVR sozlamalarini
 *   tekshirishga yuborardi, holbuki muammo tarmoqda yoki serverda.
 *   Qayta urinish bu yerda XAVFSIZ — u NVR'ga umuman bormaydi.
 */
function LoadFailed({ onRetry }: { onRetry: () => void }) {
  const t = useTranslations();

  return (
    <div
      className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
      role="alert"
    >
      <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
      <p className="text-sm">{t("errors.loadFailedBody")}</p>
      <Button onClick={onRetry} size="sm" variant="secondary">
        {t("common.retry")}
      </Button>
    </div>
  );
}

/** Qurilma pasportidan forma maydonining qiymati (`splitNvrAddress` ning teskarisi). */
function formatAddress(device: NvrDevice): string {
  const scheme = device.use_tls ? "https://" : "";
  const isDefaultPort = device.use_tls ? device.port === 443 : device.port === 80;
  return `${scheme}${device.host}${isDefaultPort ? "" : `:${device.port}`}`;
}
