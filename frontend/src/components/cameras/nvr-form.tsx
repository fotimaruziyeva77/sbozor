"use client";

import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useForm, useWatch } from "react-hook-form";
import type { UseFormRegisterReturn } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { NvrErrorBlock } from "@/components/cameras/nvr-error-block";
import { NvrTestResult } from "@/components/cameras/nvr-test-result";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { NvrDevice, NvrTestConnectionResponse } from "@/lib/api-types";
import {
  discoveryRunIdOf,
  useCreateNvr,
  useStartDiscovery,
  useTestConnection,
} from "@/lib/camera-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useNvrAuthLock } from "@/lib/use-nvr-auth-lock";

/*
 * =============================================================================
 * NVR FORMASI — D-01 ning HARFMA-HARF bajarilishi (UI-SPEC §4).
 *
 * D-01: *«Admin saytga FAQAT NVR manzili + login/parolni kiritadi.»*
 * Ekranda AYNAN UCHTA maydon turadi va uchalasi ham adminda BOR (manzil
 * o'rnatuvchining qog'ozida, login/parol o'sha yerda).
 *
 * PORT VA TLS UCHUN ALOHIDA MAYDON YO'Q — ular manzil maydonidan
 * AJRATILADI (UI-SPEC §4.1). Rad etilgan muqobillar:
 *   * `port` + `use_tls` alohida maydon — ekranda BESHTA maydon bo'lardi
 *     va `use_tls` ni tasodifan yoqib qo'ygan admin `nvr_tls_untrusted`
 *     xatosini SABABSIZ olardi;
 *   * yashirin «Qo'shimcha sozlamalar» — ekranda TO'RTINCHI affordans
 *     hosil qiladi va admin «nega ishlamayapti? balki shu yerdadir» deb
 *     uni ochishga majbur bo'lgan lahzada D-01 ning ruhi buziladi.
 * Odamlar NVR manzilini ALLAQACHON `192.168.1.64:8080` shaklida yozadi.
 *
 * ⚠ AJRATISH BU YERDA VALIDATSIYA UCHUN, YUBORISH UCHUN EMAS.
 *   `useCreateNvr`/`useTestConnection` serverga XOM `address` yuboradi
 *   (03-06 kontrakti: `NvrDeviceCreateRequest.address`), server esa uni
 *   `nvr_host.split_address()` bilan o'zi ajratadi. Klientdagi ajratish
 *   §4.7 validatsiyasini bajaradi: ommaviy IP va port oralig'i ADMINGA
 *   TUSHUNTIRISH bilan ko'rsatiladi. Ikki grammatika emas — bitta
 *   kontrakt (server) va uning klientdagi KO'ZGUSI.
 *
 * ⚠ OMMAVIY IP BLOKI — QULAYLIK, XAVFSIZLIK CHEGARASI EMAS (T-03-67).
 *   Haqiqiy darvoza serverda: `assert_private_host()` (03-04) SSRF
 *   yuzasini yopadi. Bu yerdagi tekshiruv adminni TUSHUNTIRISH bilan
 *   to'xtatadi; serverda esa u quruq 4xx bo'lardi va sabab yo'qolardi.
 *   Klientdagi tekshiruvni xavfsizlik chegarasi deb hisoblash server
 *   tomonini bo'shashtirardi — shuning uchun chegara shu yerda ochiq
 *   yozilgan.
 *
 * ⚠ PAROL FAQAT KIRITILADI, HECH QACHON KO'RSATILMAYDI (D-12).
 *   `temp-password-dialog.tsx:18-27` dagi «ATAYIN QILINMAYDI» bloki bu
 *   yerda TESKARI yo'nalishda amal qiladi:
 *     - forma parolni `useQuery` bilan SO'RAMAYDI (javob sxemasida
 *       bunday maydon umuman yo'q — `api-types.ts::nvrDeviceSchema`);
 *     - uchala chaqiruv ham `useMutation` — argument kesh grafiga
 *       tushmaydi (T-03-65);
 *     - saqlangandan keyin `reset()` qiymatni forma holatidan chiqaradi;
 *     - parol toast, jurnal, URL yoki brauzer omboriga HECH QACHON
 *       tushmaydi.
 * =============================================================================
 */

/* --- Manzilni ajratish (UI-SPEC §4.1 jadvali) ----------------------------- */

const DEFAULT_HTTP_PORT = 80;
const DEFAULT_HTTPS_PORT = 443;
const MIN_PORT = 1;
const MAX_PORT = 65535;

export type NvrAddressParts = {
  host: string;
  port: number;
  use_tls: boolean;
};

/**
 * Ajratish natijasi — UCHTA xato turi ATAYIN ajratilgan.
 *
 * Adminning harakati uchalasida BUTUNLAY boshqa: `invalid_address` —
 * terish xatosi (qayta yozish); `invalid_port` — raqamni tuzatish;
 * `public_blocked` — arxitektura qoidasi, va unga javob boshqa manzil
 * sinash EMAS, tunnel ichidagi manzilni topish. Backend ham aynan shu
 * sababdan `NvrAddressError` va `NvrHostNotPrivateError` ni ikki sinfga
 * ajratgan (`nvr_host.py`).
 */
export type NvrAddressResult =
  | { kind: "ok"; parts: NvrAddressParts }
  | { kind: "invalid_address" }
  | { kind: "invalid_port" }
  | { kind: "public_blocked" };

/**
 * `192.168.1.64:8080` -> `{host, port, use_tls}` (UI-SPEC §4.1).
 *
 * Server tomonidagi juftisi — `app/services/nvr_host.py::split_address`,
 * va bu funksiya uning qadamma-qadam ko'zgusi: sxema, yo'l qismini
 * tashlash, IPv6 kvadrat qavslari, port oralig'i.
 */
export function splitNvrAddress(raw: string): NvrAddressResult {
  let candidate = raw.trim();
  if (candidate.length === 0) return { kind: "invalid_address" };

  let useTls = false;
  const schemeAt = candidate.indexOf("://");
  if (schemeAt !== -1) {
    const scheme = candidate.slice(0, schemeAt).toLowerCase();
    /*
     * ISAPI HTTP(S) USTIDA ishlaydi. Boshqa sxemani o'tkazish eng
     * ehtimolli chalkashlik bo'lardi: admin oqim URL'ini NVR manzili
     * deb kiritib, `use_tls` ni ham noto'g'ri olardi (`nvr_host.py`
     * bilan bir xil qaror).
     */
    if (scheme !== "http" && scheme !== "https") {
      return { kind: "invalid_address" };
    }
    useTls = scheme === "https";
    candidate = candidate.slice(schemeAt + 3);
  }

  // `nvr.local:8443/doc/index.html` — brauzerdan ko'chirilgan odatiy shakl.
  candidate = candidate.split("/")[0] ?? "";
  if (candidate.length === 0) return { kind: "invalid_address" };

  let host = candidate;
  let port = useTls ? DEFAULT_HTTPS_PORT : DEFAULT_HTTP_PORT;

  if (candidate.startsWith("[")) {
    // IPv6: qavslarsiz oxirgi ikki nuqta bo'yicha bo'lish manzilning
    // O'ZINI bo'lib yuborardi.
    const closeAt = candidate.indexOf("]");
    if (closeAt === -1) return { kind: "invalid_address" };
    host = candidate.slice(1, closeAt);
    const rest = candidate.slice(closeAt + 1);
    if (rest.length > 0) {
      if (!rest.startsWith(":")) return { kind: "invalid_address" };
      const parsed = parsePort(rest.slice(1));
      if (parsed === null) return { kind: "invalid_port" };
      port = parsed;
    }
  } else {
    const colonAt = candidate.lastIndexOf(":");
    if (colonAt !== -1) {
      host = candidate.slice(0, colonAt);
      const parsed = parsePort(candidate.slice(colonAt + 1));
      if (parsed === null) return { kind: "invalid_port" };
      port = parsed;
    }
  }

  if (host.length === 0 || !isValidHost(host)) {
    return { kind: "invalid_address" };
  }
  if (isGloballyRoutable(host)) return { kind: "public_blocked" };

  return { kind: "ok", parts: { host, port, use_tls: useTls } };
}

function parsePort(text: string): number | null {
  if (!/^\d+$/u.test(text)) return null;
  const value = Number(text);
  return value >= MIN_PORT && value <= MAX_PORT ? value : null;
}

/** RFC 1123 hostname (IPv4 ham aynan shu shaklga to'g'ri keladi). */
const HOSTNAME_PATTERN =
  /^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\.?$/iu;

function isValidHost(host: string): boolean {
  // IPv6 (kvadrat qavslardan chiqqan) — to'liq shakl serverda tekshiriladi.
  if (host.includes(":")) return /^[0-9a-f:.]+$/iu.test(host);
  return HOSTNAME_PATTERN.test(host);
}

function parseIpv4(host: string): readonly number[] | null {
  const groups = host.split(".");
  if (groups.length !== 4) return null;

  const octets: number[] = [];
  for (const group of groups) {
    if (!/^\d{1,3}$/u.test(group)) return null;
    const value = Number(group);
    if (value > 255) return null;
    octets.push(value);
  }
  return octets;
}

/**
 * Manzil INTERNETDAN yetib boriladigan IP mi (T-03-67).
 *
 * ⚠ SAVOL AYNAN SHU SHAKLDA QO'YILADI — «xususiymi?» EMAS. Backend ham
 *   `is_global` bo'yicha tekshiradi va sabab O'LCHANGAN (03-04 qarori):
 *   «xususiy emas» bo'yicha tekshirish CGNAT (`100.64.0.0/10`) ni RAD
 *   ETARDI, holbuki aynan o'sha oraliq bozor tomonidagi operator
 *   tarmog'ida uchraydi.
 *
 * ⚠ HOSTNAME QABUL QILINADI. Nom qanday manzilga yechilishini bu qatlam
 *   BILMAYDI — DNS so'rovi formani tarmoqqa bog'lab qo'yardi (sekin,
 *   ishonchsiz va o'zi SSRF vektori). `nvr.local`, `.internal` va
 *   compose tarmog'idagi xizmat nomlari o'tadi (`nvr_host.py` modul
 *   docstringi).
 */
function isGloballyRoutable(host: string): boolean {
  const octets = parseIpv4(host);
  if (octets === null) return false;

  const [a = 0, b = 0, c = 0] = octets;

  // IANA maxsus-maqsadli reyestrining marshrutlanMAYDIGAN bloklari.
  if (a === 0) return false; // 0.0.0.0/8
  if (a === 10) return false; // 10.0.0.0/8
  if (a === 100 && b >= 64 && b <= 127) return false; // 100.64.0.0/10 (CGNAT)
  if (a === 127) return false; // 127.0.0.0/8
  if (a === 169 && b === 254) return false; // 169.254.0.0/16
  if (a === 172 && b >= 16 && b <= 31) return false; // 172.16.0.0/12
  if (a === 192 && b === 0 && (c === 0 || c === 2)) return false; // 192.0.0/24, 192.0.2/24
  if (a === 192 && b === 168) return false; // 192.168.0.0/16
  if (a === 198 && (b === 18 || b === 19)) return false; // 198.18.0.0/15
  if (a === 198 && b === 51 && c === 100) return false; // 198.51.100.0/24
  if (a === 203 && b === 0 && c === 113) return false; // 203.0.113.0/24
  if (a >= 224) return false; // 224.0.0.0/4 (multicast) + 240.0.0.0/4

  return true;
}

/* --- Forma ---------------------------------------------------------------- */

type NvrFormValues = {
  address: string;
  username: string;
  password: string;
};

export type NvrSaveResult = {
  device: NvrDevice;
  /** `POST /{id}/discover` bergan yugurish; 409 da MAVJUD yugurishniki. */
  runId: string | null;
};

/**
 * Formaning IKKI REJIMI — YANGI PANEL EMAS (Topilma №F).
 *
 * ⚠ ILDIZ YORLIQ NOMUVOFIQLIGI EMAS, O'LIK AFFORDANS EDI. «Diagnostika»
 *   tugmasi shu formani ochardi, uning birlamchi tugmasi esa
 *   `saveAndDiscover` -> `POST /nvr-devices` ga borardi. MAVJUD
 *   qurilmaning `host:port` i uchun bu chaqiruv `UNIQUE (market_id, host,
 *   port)` ga urilib **409 `nvr_host_taken`** dan boshqa hech nima qaytara
 *   olmasdi (`nvr.py::_device_conflict`) — ya'ni tugmaning hech qanday
 *   muvaffaqiyat yo'li YO'Q edi. Yorliq nomuvofiqligi shuning ko'rinadigan
 *   qismi, xolos.
 *
 * ⚠ YANGI PANEL QURILMAYDI VA YANGI ENDPOINT YOZILMAYDI: diagnostika
 *   ma'lumoti tizimda ALLAQACHON bor — `nvr-test-result.tsx` (model,
 *   qurilma turi, kanallar soni, soat farqi) va `nvr-error-block.tsx`
 *   (xato kodi + tuzatish yo'li). Ular `POST /nvr-devices/test-connection`
 *   javobidan keyin chiziladi, ya'ni kerak bo'lgani — formaning O'ZINI
 *   o'sha chaqiruvga qaratish.
 *
 * ⚠ PROP MAJBURIY QILINMAGAN (standart `"create"`). Sabab o'lchangan:
 *   `nvr-form.test.tsx` da propsiz render chaqiruvlari bor va majburiy
 *   prop ularni SABABSIZ qizartirardi. Wiring esa prop TIPI bilan emas,
 *   `cameras/page.test.tsx` dagi ikki tomonlama o'lchov bilan qulflanadi.
 */
export type NvrFormMode = "create" | "diagnose";

export type NvrFormProps = {
  className?: string;
  /** Diagnostika rejimida mavjud qurilmaning manzili oldindan to'ldiriladi. */
  defaultAddress?: string;
  /** Diagnostika rejimida mavjud qurilmaning logini oldindan to'ldiriladi. */
  defaultUsername?: string;
  /** Standart `"create"` — yuqoridagi izohdagi sabab. */
  mode?: NvrFormMode;
  /** «Bekor qilish» — faqat berilganda render qilinadi. */
  onCancel?: () => void;
  /** Qurilma saqlanib kashfiyot boshlanganda. */
  onSaved?: (result: NvrSaveResult) => void;
};

export function NvrForm({
  className,
  defaultAddress = "",
  defaultUsername = "",
  mode = "create",
  onCancel,
  onSaved,
}: NvrFormProps) {
  const t = useTranslations();

  const createNvr = useCreateNvr();
  const startDiscovery = useStartDiscovery();
  const testConnection = useTestConnection();

  const [testResult, setTestResult] = useState<NvrTestConnectionResponse | null>(
    null,
  );
  const [nvrError, setNvrError] = useState<{
    code: string | null;
    detail: Record<string, unknown> | null;
  } | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  /*
   * ⚠ QULF HOOK DARAJASIDA, `<form>` NING ICHKI HOLATIDA EMAS
   *   (UI-SPEC §4.4). Qoidani IKKI yuza iste'mol qiladi — bu forma va
   *   NVR kartasi («Qayta skanerlash», «Parolni yangilash»). Formaga
   *   yashirilganda karta tomonida qoida unutilardi va admin o'sha
   *   yerdan hisobni qulflardi.
   */
  const { authLocked, lock, unlockOnCredentialChange } = useNvrAuthLock();

  const schema = useMemo(
    () =>
      z.object({
        address: z
          .string()
          .min(1, { error: t("errors.required") })
          .refine((value) => splitNvrAddress(value).kind !== "invalid_address", {
            error: t("cameras.invalidAddress"),
          })
          .refine((value) => splitNvrAddress(value).kind !== "invalid_port", {
            error: t("cameras.invalidPort"),
          })
          .refine((value) => splitNvrAddress(value).kind !== "public_blocked", {
            error: t("cameras.publicAddressBlocked"),
          }),
        username: z.string().min(1, { error: t("errors.required") }),
        password: z.string().min(1, { error: t("errors.required") }),
      }),
    [t],
  );

  const {
    control,
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setFocus,
  } = useForm<NvrFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      address: defaultAddress,
      username: defaultUsername,
      password: "",
    },
  });

  /*
   * `useWatch`, kuzatuvning boshqariladigan varianti EMAS: ikkinchisi
   * `useForm()` qaytaradigan oddiy funksiya va React Compiler uni
   * memoizatsiya qila olmaydi (eskirgan UI xavfi —
   * `create-user-dialog.tsx:110-115`). `useWatch` esa hook bo'lib,
   * obunani to'g'ri e'lon qiladi.
   */
  const usernameValue = useWatch({ control, name: "username" });
  const passwordValue = useWatch({ control, name: "password" });

  /*
   * ⚠ QULF FAQAT SHU YERDA OCHILADI — login yoki parol QIYMATI
   *   o'zgarganda. Vaqt bo'yicha EMAS, tugma bilan EMAS, sahifa
   *   yangilash bilan EMAS (UI-SPEC §4.4).
   *
   *   Effekt AYNAN QIYMATLARGA bog'langan. Uni fokus yoki bosish
   *   hodisasiga ko'chirish admin maydonga TEGIB, hech narsani
   *   o'zgartirmasdan qulfni ochib yuborishiga va o'sha noto'g'ri
   *   parolni QAYTA yuborishiga yo'l ochardi — ya'ni D-03 ning butun
   *   mazmuni yo'qolardi.
   */
  useEffect(() => {
    unlockOnCredentialChange();
  }, [passwordValue, unlockOnCredentialChange, usernameValue]);

  const busy =
    isSubmitting ||
    createNvr.isPending ||
    startDiscovery.isPending ||
    testConnection.isPending;

  const blocked = authLocked || busy;

  /**
   * Qulf ostidagi bosish — SO'ROV YUBORILMAYDI.
   *
   * Fokus parol maydoniga ko'chadi, chunki keyingi qadam AYNAN o'sha
   * yerda; izohni esa quyidagi `role="status"` hududi e'lon qiladi
   * (UI-SPEC §7.6).
   */
  function refuseUnderLock(): void {
    setFocus("password");
  }

  async function runTestConnection(values: NvrFormValues): Promise<void> {
    if (blocked) {
      refuseUnderLock();
      return;
    }

    setFormError(null);
    setNvrError(null);
    setTestResult(null);

    try {
      const response = await testConnection.mutateAsync(values);
      setTestResult(response);
      if (!response.ok) {
        setNvrError({
          code: response.error_code ?? null,
          detail: response.error_detail ?? null,
        });
        // Qulflovchi kodmi — buni hook o'zi hal qiladi (`AUTH_LOCKING_CODES`).
        lock(response.error_code, response.error_detail);
      }
    } catch (error) {
      // 429 va boshqa HTTP xatolari — forma TEPASIDA (UI-SPEC §4.7).
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  async function saveAndDiscover(values: NvrFormValues): Promise<void> {
    if (blocked) {
      refuseUnderLock();
      return;
    }

    setFormError(null);
    setNvrError(null);

    try {
      const device = await createNvr.mutateAsync(values);
      // T-5 — yagona toast: kashfiyot boshlanishidan OLDIN (§10.4).
      toast.success(t("cameras.toastNvrSaved"));

      // ⚠ PAROL FORMA HOLATIDAN DARHOL CHIQADI (D-12).
      reset({
        address: values.address,
        password: "",
        username: values.username,
      });

      let runId: string | null = null;
      try {
        const started = await startDiscovery.mutateAsync(device.id);
        runId = started.run_id;
      } catch (error) {
        /*
         * 409 XATO EMAS (UI-SPEC §5.6): ikki admin (yoki bitta admin
         * ikki tabda) tugmani bir vaqtda bosishi — normal ish jarayoni.
         * Javob tanasidagi MAVJUD yugurishning `run_id` i qabul qilinadi.
         */
        runId = discoveryRunIdOf(error);
        if (runId === null) throw error;
      }

      onSaved?.({ device, runId });
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  /*
   * ⚠ REJIM FAQAT SHU IKKI QATORDA HAL BO'LADI: yuborish nishoni va
   *   birlamchi tugma. Auth qulfi (`authLocked`, `refuseUnderLock`,
   *   `blocked`) IKKALA rejimda ham AYNI — D-03 ning qulflanish himoyasi
   *   diagnostika rejimida ayni darajada kerak, chunki bu amal aynan
   *   noto'g'ri parol bilan bajariladi.
   */
  const diagnosing = mode === "diagnose";

  return (
    <Card className={className}>
      <CardContent className="pt-5">
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(diagnosing ? runTestConnection : saveAndDiscover)}
        >
          {/* Server 4xx — forma TEPASIDA (UI-SPEC §4.7). */}
          {formError !== null ? (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              role="alert"
            >
              {formError}
            </p>
          ) : null}

          {/*
           * `fieldset`/`legend` (UI-SPEC §12.2). `CardHeader` bu kartada
           * ISHLATILMAYDI: `<legend>` ning o'zi sarlavha va ikkitasi
           * bo'lganda ekranda ham, skrinriderda ham TAKRORIY sarlavha
           * chiqardi. `display: contents` ham ishlatilmaydi — ba'zi
           * brauzerlarda u `<legend>` semantikasini buzadi; `border-0 p-0`
           * yetarli.
           */}
          <fieldset className="m-0 border-0 p-0">
            <legend className="mb-4 text-lg font-semibold">
              {t(diagnosing ? "cameras.diagnoseLegend" : "cameras.nvrLegend")}
            </legend>

            {/*
             * Diagnostika izohi IKKI FAKTNI aytadi va ikkalasi ham
             * adminning keyingi harakatiga ta'sir qiladi:
             *   (a) parol ko'rsatilmaydi (D-12), shuning uchun uni qayta
             *       kiritish KERAK — bo'sh maydon nosozlik emas;
             *   (b) bu forma saqlangan qurilma yozuvini O'ZGARTIRMAYDI,
             *       ya'ni «tekshirsam, parolim almashib qoladimi?» degan
             *       savol tug'ilmaydi.
             */}
            {diagnosing ? (
              <p className="mb-4 text-sm text-text-muted">
                {t("cameras.diagnoseHint")}
              </p>
            ) : null}

            <div className="flex flex-col gap-4">
              <Field
                error={errors.address?.message}
                hint={t("cameras.nvrAddressHint")}
                id="nvr-address"
                label={t("cameras.nvrAddress")}
              >
                <Input
                  aria-describedby={
                    errors.address ? "nvr-address-error" : "nvr-address-hint"
                  }
                  aria-invalid={errors.address ? true : undefined}
                  autoComplete="off"
                  id="nvr-address"
                  inputMode="url"
                  {...register("address")}
                />
              </Field>

              <Field
                error={errors.username?.message}
                id="nvr-login"
                label={t("cameras.nvrLogin")}
              >
                <Input
                  aria-describedby={
                    errors.username ? "nvr-login-error" : undefined
                  }
                  aria-invalid={errors.username ? true : undefined}
                  autoComplete="username"
                  id="nvr-login"
                  {...register("username")}
                />
              </Field>

              <Field
                error={errors.password?.message}
                hint={t("cameras.passwordHint")}
                id="nvr-password"
                label={t("cameras.nvrPassword")}
              >
                <PasswordInput
                  describedBy={
                    errors.password ? "nvr-password-error" : "nvr-password-hint"
                  }
                  id="nvr-password"
                  invalid={errors.password !== undefined}
                  registration={register("password")}
                />
              </Field>
            </div>
          </fieldset>

          {/*
           * IKKI TUGMA VA IKKALASI HAM KERAK (UI-SPEC §4.3).
           *
           * «Ulanishni tekshirish» HECH NARSA SAQLAMAYDI va shuning
           * uchun XAVFSIZ SINOV MAYDONI. Usiz admin noto'g'ri parol
           * bilan darhol kashfiyot jobiga kirib, 25 kanal bo'ylab 401
           * olardi va hisobni qulflardi. Tekshiruv MAJBURIY EMAS —
           * to'g'ridan-to'g'ri ikkinchi tugma ham to'liq ishlaydi va u
           * SC#1 ning «bitta tugma» va'dasini saqlaydi.
           *
           * ⚠ ARIA HOLATI, O'CHIRILGAN TUGMA EMAS (02-UI-SPEC §6.6
           *   qoida 2): o'chirilgan tugma fokus olmaydi va skrinrider
           *   uni umuman o'qimaydi — ya'ni «nega bosilmayapti?»
           *   savoliga javob QOLMASDI. Bu yerda tugma fokuslanadi,
           *   o'qiladi va bosilganda sababni AYTADI (fokus parol
           *   maydoniga + `role="status"`).
           */}
          {/*
           * ⛔ DIAGNOSTIKA REJIMIDA «Saqlash va kameralarni topish»
           *    UMUMAN RENDER QILINMAYDI — `disabled`/`aria-disabled` bilan
           *    QOLDIRILMAYDI. 02-UI-SPEC §6.6 o'chirilgan tugmani rad
           *    etadi, chunki u «nega bosilmayapti?» savolini tug'diradi va
           *    unga javob beradigan holat bo'lishi kerak. Bu yerda esa
           *    tugmaning HECH QANDAY muvaffaqiyat yo'li yo'q (409
           *    `nvr_host_taken`), ya'ni ko'rsatib turishning ma'nosi ham
           *    yo'q — u faqat adminni saqlab qo'yish xavfi bor formaga
           *    olib borardi.
           *
           * ⛔ Ikkilamchi «Ulanishni tekshirish» ham chizilmaydi: u
           *    birlamchi tugma bilan AYNI amalni bajarardi va ekranda bir
           *    xil nomli ikki tugma paydo bo'lardi.
           */}
          <div className="flex flex-col gap-2 sm:flex-row-reverse">
            <Button
              aria-disabled={blocked ? true : undefined}
              className="sm:flex-1"
              size="lg"
              type="submit"
              variant={authLocked ? "secondary" : "default"}
            >
              {busy
                ? t("common.loading")
                : t(
                    diagnosing
                      ? "cameras.testConnection"
                      : "cameras.saveAndDiscover",
                  )}
            </Button>

            {diagnosing ? null : (
              <Button
                aria-disabled={blocked ? true : undefined}
                className="sm:flex-1"
                onClick={() => void handleSubmit(runTestConnection)()}
                size="lg"
                variant="secondary"
              >
                {t("cameras.testConnection")}
              </Button>
            )}

            {onCancel ? (
              <Button onClick={onCancel} size="lg" variant="ghost">
                {t("common.cancel")}
              </Button>
            ) : null}
          </div>

          {/*
           * Auth qulfi izohi — `role="status"` hududi (§12.3). U qulf
           * yoqilgan zahoti ko'rinadi va bloklangan tugma bosilib fokus
           * parol maydoniga kelganda ham o'sha yerda turadi.
           */}
          {authLocked ? (
            <p className="text-sm text-text-muted" role="status">
              {t("cameras.authLockHint")}
            </p>
          ) : null}

          {/*
           * NVR ULANISH XATOSI — forma OSTIDA (UI-SPEC §4.7), chunki
           * tuzatish yo'li aynan o'sha blokda yozilgan va fokus ham
           * o'sha yerga ko'chadi.
           */}
          {nvrError !== null ? (
            <NvrErrorBlock
              autoFocus
              code={nvrError.code}
              detail={nvrError.detail}
              onRetry={() => void handleSubmit(runTestConnection)()}
            />
          ) : null}

          {testResult !== null && testResult.ok ? (
            <NvrTestResult result={testResult} />
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}

/* --- Parol maydoni va ko'rsatish tugmasi ---------------------------------- */

/**
 * Parol maydoni + ko'rsatish tugmasi.
 *
 * ⚠ KO'RSATISH TUGMASI QULAYLIK UCHUN EMAS, XAVFSIZLIK UCHUN
 *   (UI-SPEC §4.2). D-03: hisob ~5 xato urinishdan keyin 30 daqiqaga
 *   qulflanadi, ya'ni BITTA TERISH XATOSI 30 DAQIQALIK TO'XTASH
 *   demakdir. Ko'rsatish tugmasi xatoni YUBORISHDAN OLDIN ushlaydi —
 *   bu qulflanish ehtimolini pasaytiradigan eng arzon chora.
 *
 * ⚠ `aria-pressed` VA o'zgaruvchan `aria-label` — IKKALASI HAM
 *   qo'yiladi, chunki ba'zi skrinriderlar faqat bittasini o'qiydi:
 *   birinchisi bosilgan HOLATNI, ikkinchisi keyingi AMALNI aytadi.
 *
 * Tugma ≥44×44px (`min-h-11 min-w-11`) — barmoq nishoni (WCAG 2.5.5).
 *
 * Eksport qilingan: parol dialogi (§4.6) AYNAN shu maydonni ishlatadi.
 * Ikkinchi nusxa ikkita a11y kontrakti yaratardi va ular bir kun
 * ajralib ketardi.
 */
export function PasswordInput({
  describedBy,
  id,
  invalid,
  registration,
}: {
  describedBy?: string;
  id: string;
  invalid: boolean;
  registration: UseFormRegisterReturn<string>;
}) {
  const t = useTranslations();
  const [visible, setVisible] = useState(false);

  return (
    <div className="flex items-center gap-2">
      <Input
        aria-describedby={describedBy}
        aria-invalid={invalid ? true : undefined}
        /*
         * ⚠ `new-password`: brauzer NVR parolini FOYDALANUVCHINING O'Z
         *   paroli deb saqlab qo'ymasligi kerak (T-03-65).
         */
        autoComplete="new-password"
        className="flex-1"
        id={id}
        type={visible ? "text" : "password"}
        {...registration}
      />
      <button
        aria-controls={id}
        aria-label={
          visible ? t("cameras.hidePassword") : t("cameras.showPassword")
        }
        aria-pressed={visible}
        className="flex min-h-11 min-w-11 items-center justify-center rounded-md border border-border-ui text-text transition-colors hover:bg-surface-muted"
        onClick={() => setVisible((current) => !current)}
        type="button"
      >
        {visible ? (
          <EyeOff aria-hidden="true" className="size-4" />
        ) : (
          <Eye aria-hidden="true" className="size-4" />
        )}
      </button>
    </div>
  );
}
