"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, KeyRound, RefreshCw, Stethoscope } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { NvrErrorBlock } from "@/components/cameras/nvr-error-block";
import { NvrPasswordDialog } from "@/components/cameras/nvr-password-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { NvrDevice } from "@/lib/api-types";
import { useNvrAuthLock } from "@/lib/use-nvr-auth-lock";

/*
 * =============================================================================
 * NVR KARTASI — saqlangan qurilmaning pasporti va uchta amali (UI-SPEC §4.6).
 *
 * ⚠ MANZILNI TAHRIRLASH BU FAZADA YO'Q. Manzil `UNIQUE (market_id, host,
 *   port)` kalitining BIR QISMI (03-04 sxemasi), ya'ni uni tahrirlash
 *   idempotentlik semantikasini ochib yuborardi: «bu o'sha qurilmami
 *   yoki yangisimi?» degan savolga na kod, na admin javob bera olardi.
 *   Manzil o'zgarsa NVR QAYTA QO'SHILADI va bu ataylab sodda.
 *
 * ⚠ QURILMA HOLATI BADGE'I («Onlayn») RENDER QILINMAYDI. UI-SPEC §4.6
 *   ning eskizida u bor, LEKIN `nvrDeviceSchema` da bunday maydon YO'Q
 *   (03-06 kontrakti) va oxirgi skan vaqtidan «hozir onlayn» degan
 *   xulosa chiqarish YOLG'ON DALIL bo'lardi — muvaffaqiyatli skan uch
 *   soat oldin bo'lishi mumkin. O'rniga oxirgi skan VAQTI ko'rsatiladi:
 *   u o'lchangan qiymat va admin xulosani o'zi chiqaradi.
 *   (03-08 dagi «faollashtirish panelida `—`, `0 ta` emas» qarorining
 *   aynan bir xil mantiqi.)
 *
 * ⚠ AUTH QULFI BU YERDA HAM ISHLAYDI (§4.4). Kartada login/parol
 *   maydoni yo'q, ya'ni qulfning ochilish YAGONA yo'li — «Parolni
 *   yangilash» dialogining muvaffaqiyati. Bu tasodifiy emas: rekvizit
 *   o'zgarmasdan qayta urinish AYNAN qurilmadagi qulflash hisoblagichini
 *   oshiradigan harakat.
 * =============================================================================
 */

export type NvrCardProps = {
  className?: string;
  device: NvrDevice;
  /**
   * Oxirgi NVR-darajali xato kodi (kashfiyot yugurishidan).
   *
   * 03-09 da chaqiruvchi uni uzatmaydi — kashfiyot paneli 03-10 da
   * keladi. Kontrakt bugundan turadi: yugurish `nvr_bad_credentials`
   * bilan yiqilganda karta AYNAN shu prop orqali qulflanadi va
   * «Qayta skanerlash» tugmasi hisobni qulflashda davom etmaydi.
   */
  errorCode?: string | null;
  errorDetail?: Record<string, unknown> | null;
  /** Diagnostika — chaqiruvchi formani rekvizitlar bilan ochadi. */
  onDiagnose: () => void;
  onRescan: () => void;
};

export function NvrCard({
  className,
  device,
  errorCode = null,
  errorDetail = null,
  onDiagnose,
  onRescan,
}: NvrCardProps) {
  const t = useTranslations();
  const format = useFormatter();
  const [passwordOpen, setPasswordOpen] = useState(false);

  const { authLocked, lock, unlockOnCredentialChange } = useNvrAuthLock();

  /*
   * Xato kodi TASHQARIDAN keladi (kashfiyot yugurishining natijasi),
   * ya'ni uni qulfga ulash — tashqi tizim bilan sinxronlash, effektning
   * o'z vazifasi. `lock()` qulflovchi bo'lmagan kodni O'ZI e'tiborsiz
   * qoldiradi (`AUTH_LOCKING_CODES`), shuning uchun bu yerda ikkinchi
   * shart YO'Q — ikkinchi ro'yxat jadval bilan bir kun ajralib ketardi.
   */
  useEffect(() => {
    lock(errorCode, errorDetail);
  }, [errorCode, errorDetail, lock]);

  const lastScan =
    device.last_discovery_at === null
      ? "—"
      : format.dateTime(new Date(device.last_discovery_at), {
          dateStyle: "short",
          timeStyle: "short",
        });

  function guarded(action: () => void): () => void {
    return () => {
      // Qulf ostida so'rov YUBORILMAYDI — izoh `role="status"` da turadi.
      if (authLocked) return;
      action();
    };
  }

  return (
    <Card className={className}>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold">{t("cameras.nvrCard")}</h2>
          {/* DB kontenti — tarjima qilinmaydi (1-faza D-16). */}
          <p className="text-sm">{device.model ?? "—"}</p>
        </div>

        {/*
         * `font-mono text-xs` — HUJJATLASHTIRILGAN ISTISNO (UI-SPEC §2.2):
         * bu qiymatlar qurilmaning web-interfeysi bilan BELGIMA-BELGI
         * solishtiriladi.
         */}
        <dl className="flex flex-col gap-2 text-sm">
          <Row label={t("cameras.nvrAddress")}>
            <span className="font-mono text-xs">
              {device.use_tls ? "https://" : ""}
              {device.host}:{device.port}
            </span>
          </Row>

          <Row label={t("cameras.firmware")}>
            <span className="font-mono text-xs">
              {device.firmware_version ?? "—"}
            </span>
          </Row>

          <Row label={t("cameras.serial")}>
            <span className="font-mono text-xs">
              {device.serial_number ?? "—"}
            </span>
          </Row>

          {/*
           * ⚠ TAXMIN QILINGAN PORT OCHIQ BELGILANADI. 554 fallback
           *   JIMGINA ISHLAMAYDIGAN kamera yozuvlari tug'diradi:
           *   kashfiyot yashil bo'ladi, kadr olish esa qora. Badge bu
           *   gumondorni jonli ko'rish yiqilishidan OLDIN ko'rsatadi.
           */}
          <Row label={t("cameras.rtspPort")}>
            <span className="font-mono text-xs">{device.rtsp_port ?? "—"}</span>
            {device.rtsp_port_assumed ? (
              <Badge className="gap-1" tone="warning">
                <AlertTriangle aria-hidden="true" className="size-3" />
                {t("cameras.rtspPortAssumed")}
              </Badge>
            ) : null}
          </Row>

          <Row label={t("cameras.lastScan")}>
            <span>{lastScan}</span>
          </Row>
        </dl>

        {device.rtsp_port_assumed ? (
          <p className="text-xs text-text-muted">
            {t("cameras.rtspPortAssumedHint")}
          </p>
        ) : null}

        {/*
         * UCHTA AMAL VA UCHALASI HAM `secondary` (UI-SPEC §2.4 aksent
         * budjeti): NVR va kameralar mavjud bo'lgan holatda sahifada
         * birlamchi tugma UMUMAN bo'lmaydi — kundalik ish bu yerda
         * emas, kameralar ro'yxatida.
         */}
        <div className="flex flex-wrap gap-2">
          <Button
            aria-disabled={authLocked ? true : undefined}
            onClick={guarded(onRescan)}
            size="lg"
            variant="secondary"
          >
            <RefreshCw aria-hidden="true" />
            {t("cameras.rescan")}
          </Button>

          {/*
           * «Parolni yangilash» qulf ostida ham OCHIQ qoladi va bu
           * qoidaning teskarisi emas, MAZMUNI: rekvizitni o'zgartirish —
           * qulfdan chiqishning yagona yo'li.
           */}
          <Button
            onClick={() => setPasswordOpen(true)}
            size="lg"
            variant="secondary"
          >
            <KeyRound aria-hidden="true" />
            {t("cameras.updatePassword")}
          </Button>

          <Button
            aria-disabled={authLocked ? true : undefined}
            onClick={guarded(onDiagnose)}
            size="lg"
            variant="secondary"
          >
            <Stethoscope aria-hidden="true" />
            {t("cameras.diagnostics")}
          </Button>
        </div>

        {authLocked ? (
          <p className="text-sm text-text-muted" role="status">
            {t("cameras.authLockHint")}
          </p>
        ) : null}

        {errorCode !== null ? (
          <NvrErrorBlock code={errorCode} detail={errorDetail} />
        ) : null}

        <NvrPasswordDialog
          nvrId={device.id}
          onOpenChange={setPasswordOpen}
          onUpdated={unlockOnCredentialChange}
          open={passwordOpen}
        />
      </CardContent>
    </Card>
  );
}

/** Yorliq + qiymat; qiymat yo'q bo'lsa `—`, qator esa QOLADI. */
function Row({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <dt className="min-w-32 text-text-muted">{label}</dt>
      <dd className="flex items-center gap-2">{children}</dd>
    </div>
  );
}
