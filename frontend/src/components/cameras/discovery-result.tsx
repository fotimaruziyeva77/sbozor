"use client";

import { CheckCircle2, Minus, Plus, WifiOff } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { BadgeTone } from "@/components/ui/badge";
import type { DiscoveryRun } from "@/lib/api-types";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * KASHFIYOT NATIJASI — SC#2 NING UI TOMONDAGI BUTUN MAZMUNI (UI-SPEC §6.3).
 *
 * ⚠ HECH NARSA O'ZGARMAGAN SKAN BUZUQ SKANDAN FARQLANMASA, IDEMPOTENTLIK
 *   ISBOTLANMAGAN HISOBLANADI. Shu sababdan uchala hisoblagich HAM DOIM
 *   ko'rinadi — noli bilan birga.
 *
 *   Nol qatorni yashirish «bu skan hech narsa qilmadi» degan YOLG'ON
 *   signal beradi: nol — NATIJA, uning yo'qligi emas. «0 ta yangi
 *   kamera» va «hisoblagich umuman yo'q» ikki butunlay boshqa da'vo, va
 *   birinchisi aynan shu ekranda aytilishi kerak.
 *
 * ⚠ SARLAVHA AMALNING natijasini aytadi («Skanerlash yakunlandi»), BIRINCHI
 *   HISOBLAGICHNI TAKRORLAMAYDI («0 ta kamera qo'shildi» EMAS). Yonidagi
 *   vaqt belgisi — bu skan HOZIR bo'lganini isbotlaydigan IKKINCHI,
 *   mustaqil kanal.
 *
 * ⚠ YASHIL RANG (`success`) `added === 0` BO'LGANDA HAM: u «yangi kamera»
 *   ni emas, «amal bajarildi» ni bildiradi.
 *
 * ⚠ `role="status"`, `alert` EMAS — muvaffaqiyat ogohlantirish emas va u
 *   foydalanuvchining ishini uzmasligi kerak.
 *
 * ⚠ HISOBLAGICH `<dl>`/`<dt>`/`<dd>` BILAN BOG'LANADI: aks holda
 *   skrinriderda «0» YOLG'IZ eshitilardi va u hech qanday ma'no
 *   tashimasdi.
 *
 * ⚠ RANG YAGONA SIGNAL EMAS (UI-SPEC §2.5): har hisoblagichda rang +
 *   ikonka + TO'LIQ SO'Z yorlig'i — uchala kanal ham bor.
 * =============================================================================
 */

/**
 * Uch hisoblagichning qiymatlari (UI-SPEC §6.3 formulasi).
 *
 * ⚠ `unchanged = channels_found − channels_added` VA `channels_found` —
 *   shu yugurishda SANAB CHIQILGAN kanallar soni, onlayn/oflayn
 *   holatidan QAT'I NAZAR (UI-SPEC §6.3 [TALAB]). Aks holda formula
 *   manfiy yoki noto'g'ri chiqardi: oflayn kanal ham sanoqqa kiradi,
 *   chunki u ro'yxatda BOR.
 *
 * ⚠ `null` — «worker bu maydonni hali yozmagan», ya'ni nol bilan bir xil
 *   emas. Terminal `succeeded` holatida u kelmasligi kutilmaydi, lekin
 *   kelib qolsa `0` ko'rsatish YOLG'ON dalildan ko'ra xavfsizroq: panel
 *   yiqilmaydi va admin baribir vaqt belgisini ko'radi.
 */
export function discoveryCounts(run: DiscoveryRun): {
  added: number;
  offline: number;
  unchanged: number;
} {
  const found = run.channels_found ?? 0;
  const added = run.channels_added ?? 0;
  return {
    added,
    offline: run.channels_marked_offline ?? 0,
    // Salbiy qiymat imkonsiz bo'lishi kerak, lekin u serverdagi xatoda
    // ekranga «-2» bo'lib chiqishi mumkin edi — bu esa hisoblagichning
    // butun ishonchini yo'qotardi.
    unchanged: Math.max(0, found - added),
  };
}

/**
 * «Bu skan hech narsani O'ZGARTIRMADI» — anti-«buzuq ko'rinadi» sharti.
 *
 * ⚠ ZIDDIYAT VA UNING YECHIMI (rejaga yozildi). Rejaning `<action>` bandi
 *   «uchala nol bo'lganda» deydi, `<behavior>` bandi va UI-SPEC §6.3 ning
 *   ESKIZI esa AYNAN `added=0, offline=0, unchanged=6` holatida shu
 *   jumlani talab qiladi. Ikkalasi bir vaqtda faqat bitta shakl bilan
 *   bajariladi: `added === 0 && offline === 0`.
 *
 *   Bu shakl SEMANTIK JIHATDAN ham to'g'ri: `unchanged` — O'ZGARISH EMAS,
 *   uning teskarisi. «Uchala nol» ni harfma-harf olish jumlani faqat
 *   `channels_found === 0` bo'lganda (NVR'da umuman kanal yo'q)
 *   chiqarardi — ya'ni ishlab turgan 6 kanalli NVR'ning idempotent
 *   qayta skani AYNAN «hech narsa qilmadi» ko'rinishida qolardi. Bu esa
 *   SC#2 ning va reja maqsadining teskarisi.
 *
 *   `added === 0 && offline === 0` uchala nol holatini ham QAMRAYDI,
 *   ya'ni rejaning ikkala da'vosi ham bajariladi.
 */
export function runNoChanges(counts: { added: number; offline: number }): boolean {
  return counts.added === 0 && counts.offline === 0;
}

type CounterTone = Extract<BadgeTone, "success" | "warning" | "neutral">;

export function DiscoveryResult({
  className,
  onClose,
  run,
}: {
  className?: string;
  onClose: () => void;
  run: DiscoveryRun;
}) {
  const t = useTranslations();
  const format = useFormatter();

  const counts = discoveryCounts(run);
  const noChanges = runNoChanges(counts);

  /*
   * Vaqt belgisi — SARLAVHANING bir qismi (UI-SPEC §6.3). `finished_at`
   * yo'q bo'lsa `started_at` olinadi: ikkalasi ham serverdan keladi va
   * `Date.now()` ishlatish «hozir ochilgan panel = hozir bo'lgan skan»
   * degan YOLG'ON dalil bo'lardi (sahifa `?run=` bilan ertasiga ham
   * ochilishi mumkin).
   */
  const stamp = Date.parse(run.finished_at ?? run.started_at);

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-md border border-border bg-surface p-4",
        className,
      )}
      role="status"
    >
      <div className="flex flex-wrap items-center gap-2">
        {/*
         * Ikonka + matn + yashil tint — uch kanal. `tone="success"`
         * `added === 0` bo'lganda HAM (UI-SPEC §6.3).
         */}
        <Badge className="gap-1" tone="success">
          <CheckCircle2 aria-hidden="true" className="size-3" />
          {t("cameras.runDone")}
        </Badge>
        {Number.isFinite(stamp) ? (
          <span className="text-xs text-text-muted">
            {format.dateTime(new Date(stamp), {
              dateStyle: "medium",
              timeStyle: "short",
            })}
          </span>
        ) : null}
      </div>

      {/*
       * ⚠ NOL QATOR YASHIRILMAYDI — shart yo'q va bo'lmaydi ham.
       *   Bu yerda `{count > 0 && …}` shaklidagi har qanday shart SC#2
       *   ning UI isbotini o'ldiradi (rejaning sabotaj bandi shuni
       *   o'lchaydi).
       */}
      <dl className="flex flex-col gap-2">
        <Counter
          icon={<Plus aria-hidden="true" className="size-3" />}
          label={t("cameras.runAdded")}
          tone="success"
          value={counts.added}
        />
        <Counter
          icon={<WifiOff aria-hidden="true" className="size-3" />}
          label={t("cameras.runOffline")}
          tone="warning"
          value={counts.offline}
        />
        <Counter
          icon={<Minus aria-hidden="true" className="size-3" />}
          label={t("cameras.runUnchanged")}
          tone="neutral"
          value={counts.unchanged}
        />
      </dl>

      {/*
       * ANTI-«BUZUQ KO'RINADI» JUMLASI va u BOSHQA HECH QACHON
       * chiqmaydi: uning mavjudligi «skan ishladi, lekin o'zgartiradigan
       * narsa topmadi» degan da'voni matn bilan ham aytadi.
       */}
      {noChanges ? (
        <p className="text-sm text-text-muted">{t("cameras.runNoChanges")}</p>
      ) : null}

      {/*
       * QISMAN MUVAFFAQIYAT (UI-SPEC §6.4) — bu XATO EMAS va shuning
       * uchun bu yerda xato bloki CHIQMAYDI: `channel_offline` sahifa
       * darajasidagi nosozlik emas, kamera yozuvi baribir yaratiladi.
       */}
      {counts.offline > 0 ? (
        <p className="text-sm text-text-muted">
          {t("cameras.runSomeOffline", { count: counts.offline })}
        </p>
      ) : null}

      <div>
        <Button onClick={onClose} size="sm" variant="secondary">
          {t("cameras.runClose")}
        </Button>
      </div>
    </div>
  );
}

/**
 * Bitta hisoblagich — raqam va yorliq DASTURIY jihatdan bog'langan.
 *
 * ⚠ VIZUAL TARTIB `order-*` BILAN: razmetkada `<dt>` `<dd>` dan OLDIN
 *   turadi (HTML `<dl>` ning talabi va skrinrider shu tartibda o'qiydi),
 *   ekranda esa raqam yorliqdan oldin ko'rinadi (UI-SPEC §6.3 eskizi).
 *   Ikkalasi ham bir xil ma'no beradi, shuning uchun WCAG 1.3.2
 *   buzilmaydi.
 */
function Counter({
  icon,
  label,
  tone,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  tone: CounterTone;
  value: number;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <dt className="order-2 text-sm">{label}</dt>
      <dd className="order-1 m-0">
        <Badge className="min-w-12 justify-center gap-1 tabular-nums" tone={tone}>
          {icon}
          {value}
        </Badge>
      </dd>
    </div>
  );
}
