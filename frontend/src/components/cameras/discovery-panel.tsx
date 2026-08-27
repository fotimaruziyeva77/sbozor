"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { DiscoveryResult } from "@/components/cameras/discovery-result";
import { NvrErrorBlock } from "@/components/cameras/nvr-error-block";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { DiscoveryRunStatusValue } from "@/lib/api-types";
import {
  DISCOVERY_POLL_MAX_FAILURES,
  DISCOVERY_POLL_TIMEOUT_MS,
  useDiscoveryRunQuery,
} from "@/lib/camera-queries";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * KASHFIYOT PANELI — HAR HOLAT NOMLANADI (UI-SPEC §5.2, §5.3).
 *
 * ⚠ KASHFIYOT HECH QACHON «TUGAMASLIGI MUMKIN BO'LGAN SPINNER»
 *   KO'RINISHIDA BO'LMAYDI. Har bosqich o'z nomi bilan chiqadi va poll
 *   chegaralangan.
 *
 * ⚠ SOXTA BOSQICH KO'RSATKICHI QURILMAYDI [MEROS: `import-panel.tsx` —
 *   «soxta ko'rsatkich yolg'on bo'lardi»]. Foiz MA'LUM EMAS: ISAPI
 *   byudjeti 17–60 s va u qurilmadan qurilmaga uch barobar farq qiladi.
 *   O'ylab topilgan foiz — yolg'on. Uning o'rniga ikkita HAQIQIY narsa
 *   ko'rsatiladi:
 *     * BOSQICH NOMI  — haqiqiy ma'lumot (serverdan keladi);
 *     * O'TGAN VAQT   — haqiqiy o'lchov (soatdan keladi).
 *
 * ⚠ O'TGAN VAQT `aria-hidden`: har soniyada e'lon qilinsa panel
 *   skrinrider foydalanuvchisi uchun o'qib bo'lmas holga kelardi
 *   (UI-SPEC §5.2). E'lon qilinadigan YAGONA narsa — bosqich nomi.
 *
 * ⚠ BEKOR QILISH YO'Q (UI-SPEC §5.5): kashfiyot hech narsani buzmaydi —
 *   u faqat o'qiydi va idempotent upsert qiladi. Bekor qilish faqat
 *   KUTISHNI qisqartirardi, sahifadan chiqib ketish esa xuddi shuni
 *   beradi. Shu sababdan panelda bitta meta qator turadi: kashfiyot
 *   sahifa yopilganda ham davom etadi.
 *
 * ⚠ JONLI HUDUDLAR REYESTRI (UI-SPEC §12.3 — bir vaqtda ikkitadan
 *   ortiq faol bo'lmaydi): konteynerda rol YO'Q. `role="status"` faqat
 *   bosqich matnida (S1/S2/S5) yoki natija panelida; `role="alert"`
 *   esa xato blokining O'ZIDA. Konteynerga `status` qo'yish S4 da
 *   `alert` ni `status` ichiga joylashtirardi va e'lonlar bir-birini
 *   bosardi.
 * =============================================================================
 */

/** O'tgan vaqt hisoblagichi shu chegaradan keyin PAYDO bo'ladi. */
export const ELAPSED_VISIBLE_AFTER_MS = 5_000;

/** Shu chegaradan keyin «sekin tarmoq» izohi qo'shiladi. */
export const SLOW_HINT_AFTER_MS = 60_000;

/** Panelning ko'rinadigan bosqichlari (UI-SPEC §5.2 — S1…S5). */
export type DiscoveryStage =
  | "queued" // S1
  | "detecting" // S2a
  | "probing" // S2b
  | "succeeded" // S3
  | "failed" // S4
  | "timeout"; // S5

export type DiscoveryStageInput = {
  /** Yugurishning serverdagi holati; `undefined` — birinchi javob hali yo'q. */
  status: DiscoveryRunStatusValue | undefined;
  /** Sanab chiqilgan kanallar soni; `null` — worker hali yozmagan. */
  channelsFound: number | null;
  /** Yugurishning SERVERDAGI boshlanish vaqti (ISO). */
  startedAt: string | null;
  /** Panel montaj bo'lgan lahza — `startedAt` HALI YO'Q holatning zaxirasi. */
  mountedAt: number;
  /** Ketma-ket yiqilgan so'rovlar soni (`useQuery().failureCount`). */
  failureCount: number;
  now: number;
};

/**
 * Bosqich qarori — SOF FUNKSIYA (`camera-queries.ts::discoveryPollInterval`
 * bilan aynan bir xil sabab).
 *
 * ⚠ NEGA KOMPONENTDAN AJRATILGAN: uchta chegaraning ikkitasi VAQTGA
 *   bog'langan va ularni komponent ichida qoldirish testni real soatga
 *   qadab qo'yardi. Bundan tashqari 03-09 ning sabotaji S3 aynan shu
 *   sinfni o'lchagan: komponent ichida yashagan qaror darvozadan JIMGINA
 *   o'tib ketadi.
 *
 * ⚠ TARTIB — QARORNING O'ZI:
 *   1. TERMINAL HOLAT TIMEOUTDAN USTUN. Natija kelgan bo'lsa u
 *      ko'rsatiladi, garchi javob kech kelgan bo'lsa ham — «javob
 *      bermayapti» deb turish qo'lда turgan natijani yashirardi.
 *   2. Ketma-ket yiqilishlar — server umuman javob bermayapti.
 *   3. Vaqt chegarasi. ⚠ `startedAt` HALI YO'Q bo'lsa MONTAJ LAHZASI
 *      olinadi: birinchi javob umuman kelmasa `started_at` hech qachon
 *      to'lmaydi va chegara MANGU ochiq qolardi — ya'ni panel S1 da
 *      abadiy qotib, «tugamasligi mumkin bo'lgan spinner» ning aynan
 *      o'zi bo'lardi.
 *   4. S2b faqat `channelsFound > 0` bo'lganda: nol bilan «0 ta kanal
 *      topildi — oqimlar tekshirilmoqda» degan ma'nosiz matn chiqardi.
 */
export function discoveryStageOf(input: DiscoveryStageInput): DiscoveryStage {
  if (input.status === "succeeded") return "succeeded";
  if (input.status === "failed") return "failed";

  if (input.failureCount >= DISCOVERY_POLL_MAX_FAILURES) return "timeout";

  const since =
    input.startedAt === null ? input.mountedAt : Date.parse(input.startedAt);
  const anchor = Number.isFinite(since) ? since : input.mountedAt;
  if (input.now - anchor >= DISCOVERY_POLL_TIMEOUT_MS) return "timeout";

  if (input.status === "running") {
    return input.channelsFound !== null && input.channelsFound > 0
      ? "probing"
      : "detecting";
  }

  return "queued";
}

/**
 * O'tgan vaqtning ko'rinadigan shakli (UI-SPEC §5.2).
 *
 * `null` — hali ko'rsatilmaydi: tez yugurishda hisoblagichning
 * miltillashi bezovta qiladi va hech qanday ma'lumot bermaydi.
 */
export function elapsedLabel(
  elapsedMs: number,
  seconds: (value: number) => string,
): string | null {
  if (elapsedMs < ELAPSED_VISIBLE_AFTER_MS) return null;
  const total = Math.floor(elapsedMs / 1000);
  if (total < 60) return seconds(total);
  // Bir daqiqadan keyin `m:ss` — bu shaklda so'z yo'q, ya'ni tarjima
  // ham talab qilinmaydi.
  const mm = Math.floor(total / 60);
  const ss = String(total % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function DiscoveryPanel({
  className,
  nvrId,
  onClose,
  runId,
}: {
  className?: string;
  nvrId: string;
  onClose: () => void;
  runId: string;
}) {
  const t = useTranslations();
  const runQuery = useDiscoveryRunQuery(nvrId, runId);
  const run = runQuery.data ?? null;

  /*
   * SOAT — TASHQI TIZIM [MEROS: 03-09 `nvr-error-block.tsx`]. Holat
   * FAQAT interval callback'ida yangilanadi, boshlang'ich qiymat esa
   * `useState` ning DANGASA initsializatorida: effekt tanasida
   * `setState` chaqirish React Compiler qoidasiga uriladi
   * (`react-hooks/set-state-in-effect`) va birinchi kadrda noto'g'ri
   * qiymat ko'rsatardi.
   */
  const [mountedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const stage = discoveryStageOf({
    channelsFound: run?.channels_found ?? null,
    failureCount: runQuery.failureCount,
    mountedAt,
    now,
    startedAt: run?.started_at ?? null,
    status: run?.status,
  });

  if (stage === "succeeded" && run !== null) {
    return <DiscoveryResult className={className} onClose={onClose} run={run} />;
  }

  if (stage === "failed" && run !== null) {
    /*
     * ⚠ FOKUS KO'CHMAYDI (UI-SPEC §7.6): kashfiyot 60 soniya davom
     *   etgan bo'lishi mumkin va foydalanuvchi allaqachon boshqa ish
     *   qilayotgandir. `autoFocus` STANDART holda `false` — bu yerda u
     *   ATAYIN berilmaydi. E'lonni blokning o'z `role="alert"` i
     *   qiladi.
     */
    return (
      <NvrErrorBlock
        className={className}
        code={run.error_code}
        detail={run.error_detail}
      />
    );
  }

  if (stage === "timeout") {
    return (
      <TimeoutPanel
        className={className}
        onCheck={() => void runQuery.refetch()}
      />
    );
  }

  const stageText =
    stage === "probing"
      ? t("cameras.runProbing", { count: run?.channels_found ?? 0 })
      : stage === "detecting"
        ? t("cameras.runDetecting")
        : t("cameras.runQueued");

  const startedMs = run === null ? mountedAt : Date.parse(run.started_at);
  const elapsedMs = now - (Number.isFinite(startedMs) ? startedMs : mountedAt);
  const elapsed = elapsedLabel(elapsedMs, (value) =>
    t("cameras.runElapsed", { seconds: value }),
  );

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-md border border-border bg-surface p-4",
        className,
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        {/* E'LON QILINADIGAN YAGONA MATN — bosqich nomi. */}
        <p className="text-sm font-semibold" role="status">
          {stageText}
        </p>
        {elapsed !== null ? (
          <span
            aria-hidden="true"
            className="text-xs text-text-muted tabular-nums"
          >
            {elapsed}
          </span>
        ) : null}
      </div>

      {/* Kontent uchun skelet — real bosqich matni ustida (§10.1). */}
      <Skeleton className="h-16" />

      {elapsedMs >= SLOW_HINT_AFTER_MS ? (
        <p className="text-xs text-text-muted">{t("cameras.runSlowHint")}</p>
      ) : null}

      <p className="text-xs text-text-muted">{t("cameras.runLeaveHint")}</p>
    </div>
  );
}

/**
 * S5 — TIMEOUT. ⚠ BU XATO EMAS (UI-SPEC §5.3).
 *
 * Job fonda hamon ishlayotgan bo'lishi mumkin: chegara BIZNING
 * poll'imizga tegishli, worker'ga emas. Shuning uchun bu yerda XATO
 * RANGI ISHLATILMAYDI (`danger` tinti yo'q) va rol `status`, `alert`
 * emas — qizil ramka adminni mavjud bo'lmagan nosozlikni qidirishga
 * yuborardi.
 *
 * Yagona amal — BITTA qo'lda tekshirish. Avtomatik qayta urinish
 * qo'yilmaydi: u aynan biz endigina to'xtatgan cheksiz poll'ni
 * tiklardi.
 */
function TimeoutPanel({
  className,
  onCheck,
}: {
  className?: string;
  onCheck: () => void;
}) {
  const t = useTranslations();

  return (
    <div
      className={cn(
        "flex flex-col items-start gap-3 rounded-md border border-border bg-surface-muted p-4",
        className,
      )}
      role="status"
    >
      <p className="text-sm">{t("cameras.runTimeout")}</p>
      <Button onClick={onCheck} size="sm" variant="secondary">
        {t("cameras.checkStatus")}
      </Button>
    </div>
  );
}
