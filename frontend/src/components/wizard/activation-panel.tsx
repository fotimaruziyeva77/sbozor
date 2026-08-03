"use client";

import { useRef, useState } from "react";
import { ArrowRight, Check, Dot, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ACTIVATION_STEP,
  WIZARD_SETUP_PATH,
  type WizardStepLabelKey,
} from "@/components/wizard/wizard-steps";
import { Link, useRouter } from "@/i18n/navigation";
import type { BlockingItem, SetupStatusResponse } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  activationBlockingOf,
  useActivateMarket,
  useSetupStatusQuery,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Faollashtirish paneli — 409 XATO EMAS, YO'L KO'RSATKICHI (UI-SPEC §6.6).
 *
 * Bu fazaning eng muhim UX qarori va uning olti bandi shu faylda AYNAN
 * bajariladi:
 *
 *  1. RO'YXAT DOIM KO'RINADI — `can_activate === true` bo'lganda ham. U
 *     "nima qoldi" emas, "bozor nimadan iborat" degan ma'noni beradi va
 *     faollashtirishdan oldin oxirgi ko'z yugurtirish imkonini beradi.
 *
 *  2. TUGMA `disabled` QILINMAYDI. O'chirilgan tugma fokus OLMAYDI,
 *     skrinrider uni O'QIMAYDI va "nega?" savoliga javob beradigan joy
 *     qolmaydi. `aria-disabled` esa fokuslanadi va e'lon qilinadi.
 *
 *  3. Bosilganda (chala bozor): so'rov YUBORILMAYDI, fokus birinchi
 *     bajarilmagan bandga ko'chadi va `aria-live` uni e'lon qiladi.
 *
 *  4. Har bajarilmagan band — o'sha qadamga havola.
 *
 *  5. Server 409 qaytarsa uning `blocking[]` i shu ro'yxatni ALMASHTIRADI:
 *     alohida xato UI'si ham, toast ham yo'q — AYNI render yo'li.
 *
 *  6. Muvaffaqiyatda toast + boshqaruv paneliga o'tish.
 *
 * ⚠ QAT'IY TAQIQ (D-16, §6.7): ogohlantirish ikonkalari, ogohlantirish/xavf
 * fon sinflari va shoshilinch e'lon roli bu faylda ISHLATILMAYDI. Bozorning
 * chala bo'lishi — NORMAL ish jarayoni holati, nosozlik emas. Taqiq mexanik
 * grep bilan qulflangan, shuning uchun taqiqlangan atamalar bu izohda ham
 * LITERAL yozilmaydi.
 * =============================================================================
 */

type ChecklistLabelKey =
  | WizardStepLabelKey
  | "wizard.itemStallCategories"
  | "wizard.step.cameras";

type ChecklistRow = {
  readonly labelKey: ChecklistLabelKey;
  /** Bajarilmagan band shu qadamga havola qiladi; `null` — havola yo'q. */
  readonly step: number | null;
  /** Shu bandga tegishli server to'siq kodlari. */
  readonly codes: readonly string[];
  /** O'ng ustundagi sanoq matni. */
  readonly value: string;
  /**
   * Neytral band (D-11 / D-16): u HECH QACHON bloklovchi bo'lib
   * ko'rsatilmaydi va `·` belgisi bilan chiziladi.
   */
  readonly neutral: boolean;
  /**
   * Ustadan TASHQARIDAGI bo'limga havola (UI-SPEC §3.4, U-3).
   *
   * `step` dan AJRATILGAN va bu ataylab: `step` ustaning O'Z marshrutiga
   * (`?step=N`) ketadi va faqat BAJARILMAGAN bandda ochiladi; bu esa
   * doimiy yo'l ko'rsatkichi va u band "bajarilmagan" bo'lishini talab
   * QILMAYDI. Ikkalasini bitta maydonga yig'ish neytral bandni to'siqqa
   * aylantirardi.
   */
  readonly href?: string;
};

export function ActivationPanel() {
  const t = useTranslations();
  const router = useRouter();
  const { principal } = useAuthStore();

  const marketId = principal?.marketId ?? null;

  /*
   * Panel `setup-status` ni O'ZI o'qiydi (qobiq bilan AYNI `queryKey`,
   * ya'ni TanStack ikkinchi tarmoq so'rovini yubormaydi). Sabab: 409 dan
   * keyin ro'yxat SERVER javobiga almashadi va bu almashinuv panelning
   * o'z holati — uni propga bog'lash haqiqat manbaini ikkiga bo'lardi.
   */
  const statusQuery = useSetupStatusQuery(marketId);
  const activate = useActivateMarket();

  /** 409 dan kelgan to'siqlar; `null` — hali 409 bo'lmagan. */
  const [conflict, setConflict] = useState<readonly BlockingItem[] | null>(
    null,
  );
  /** Faollashtirishga URINILDIMI — e'lon faqat shundan keyin chiqadi. */
  const [attempted, setAttempted] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const firstUnmetRef = useRef<HTMLAnchorElement | null>(null);

  if (statusQuery.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-64 rounded-lg" />
      </div>
    );
  }

  if (statusQuery.isError) {
    return (
      <p className="text-sm text-text-muted" role="status">
        {t(marketErrorMessageKey(statusQuery.error))}
      </p>
    );
  }

  const status = statusQuery.data;
  const blocking = conflict ?? status.blocking;

  const count = (value: number): string =>
    t("wizard.countUnit", { count: value });
  const coverage = (done: number, total: number): string =>
    t("wizard.coverage", { done, total });

  /*
   * Ro'yxat bandlari — sanoqlar `setup-status` dan, matnlar QADAM
   * nomlarining O'ZIDAN.
   *
   * Yorliqlar ataylab qadam nomlari: panel foydalanuvchini o'sha qadamga
   * yuboradi va u yerda BOSHQA sarlavhani ko'rsa "noto'g'ri joyga
   * tushdimmi?" degan savol tug'ilardi.
   *
   * Ro'yxat komponent ICHIDA quriladi — `t` ni tashqi funksiyaga uzatish
   * uning tipini bo'shashtirishni (`key: string`) talab qilardi va o'shanda
   * mavjud bo'lmagan kalit kompilyatsiyadan bemalol o'tardi.
   */
  const rows: readonly ChecklistRow[] = [
    {
      labelKey: "wizard.step.2",
      step: 2,
      codes: ["zones_missing"],
      value: count(status.zones),
      neutral: false,
    },
    {
      labelKey: "wizard.step.3",
      step: 3,
      codes: ["categories_missing"],
      value: count(status.categories),
      neutral: false,
    },
    {
      /*
       * ⚠ Bu band boshlang'ich narx kiritilmaganda chiqadi va uni yopish
       * yo'li — 4-qadamdagi MAVJUD tarif dialogi. Dialog sana chegarasini
       * SERVERNING `min_valid_from` idan oladi (02-15), ya'ni qoralama
       * bozorda o'tmishdagi sanaga yozish MUMKIN. Agar u yerda ikkinchi,
       * o'z chegarasini hisoblaydigan forma paydo bo'lsa, bu havola
       * foydalanuvchini yopib bo'lmaydigan qadamga — cheksiz siklga —
       * olib borardi.
       */
      labelKey: "wizard.step.4",
      step: 4,
      codes: ["tariff_missing_for_category"],
      value: coverage(status.tariffs_covered, status.categories_total),
      neutral: false,
    },
    {
      labelKey: "wizard.step.5",
      step: 5,
      codes: ["stalls_missing"],
      value: count(status.stalls),
      neutral: false,
    },
    {
      labelKey: "wizard.itemStallCategories",
      step: 5,
      codes: ["stalls_without_category"],
      value: coverage(status.stalls_with_category, status.stalls),
      neutral: false,
    },
    {
      labelKey: "wizard.step.7",
      step: ACTIVATION_STEP,
      codes: ["calendar_missing"],
      value: status.calendar_configured ? t("wizard.calendarSet") : "—",
      neutral: false,
    },
    {
      // D-11: sotuvchilar faollashtirishni HECH QACHON to'smaydi.
      labelKey: "wizard.step.6",
      step: 6,
      codes: [],
      value: count(status.vendors),
      neutral: true,
    },
    {
      /*
       * D-16: kamera qadam ham emas, to'siq ham emas. 3-fazadan keyin u
       * MAVJUD BO'LIM, shuning uchun qator havolaga aylandi (U-3).
       *
       * ⚠ SANOQ ATAYIN `—`, `status.cameras` EMAS. Server bu maydonni
       * HAR DOIM `0` qaytaradi (`markets.py::_setup_status_response` —
       * u D-16 ning "ilgagi" bo'lib qo'yilgan va haqiqiy sanoq hali
       * ulanmagan). "0 ta" yozish kameralar ulangandan keyin ham
       * ekranda turar va u YOLG'ON dalil bo'lardi; `—` esa "hali
       * o'lchanmagan" degan halol qiymat (UI-SPEC §3.4 U-3 ikkalasiga
       * ham ruxsat beradi). Sanoq ulanganda shu qatorning bitta
       * qiymatini almashtirish kifoya.
       */
      labelKey: "wizard.step.cameras",
      step: null,
      codes: [],
      value: "—",
      neutral: true,
      href: "/cameras",
    },
  ];

  const blockedCodes = new Set(blocking.map((item) => item.code));
  const knownCodes = new Set(rows.flatMap((row) => row.codes));

  /*
   * Server ro'yxatidagi NOTANISH kod — jimgina yo'qolmaydi.
   *
   * 3-fazada yangi to'siq qo'shilsa va u shu yerdagi bandlarga bog'lanmasa,
   * foydalanuvchi "hammasi bajarilgan" ro'yxatini ko'rib turib, tugmadan
   * javob ololmasdi. Notanish kod alohida qator bo'lib chiqadi va o'z
   * qadamiga havola qiladi.
   */
  const extras = blocking.filter((item) => !knownCodes.has(item.code));

  /*
   * `can_activate` — SERVER qarori. U sanoqlardan QAYTA HISOBLANMAYDI:
   * to'liqlik qoidasi ikki joyda yashasa bir kun `activate` darvozasi
   * bilan ajralib ketardi (02-11 kontrakti).
   *
   * 409 kelgan bo'lsa qaror ham eskirgan — o'shanda javobning O'ZI hakam.
   */
  const canActivate = conflict === null ? status.can_activate : false;

  const unmetRows = rows.filter(
    (row) => !row.neutral && row.codes.some((code) => blockedCodes.has(code)),
  );
  const firstUnmetLabel =
    unmetRows.length > 0
      ? t(unmetRows[0].labelKey)
      : extras.length > 0
        ? t("wizard.incomplete")
        : null;

  /*
   * Birinchi bajarilmagan band RENDER'DAN OLDIN aniqlanadi.
   *
   * Muqobil variant — sikl ichida "ko'rilgan" bayrog'ini o'zgartirish —
   * React Compiler qoidasi (`react-hooks/immutability`) tomonidan rad
   * etiladi va u haq: bayroq render tugagandan keyin ham o'zgarib,
   * keyingi renderda boshqa bandga fokus berardi.
   *
   * Kalitlar to'qnashmaydi: band kalitlari `wizard.` bilan boshlanadi,
   * server kodlari esa hech qachon nuqta ishlatmaydi.
   */
  const firstUnmetKey: string | null =
    unmetRows[0]?.labelKey ?? extras[0]?.code ?? null;

  function focusFirstUnmet(): void {
    setAttempted(true);
    firstUnmetRef.current?.focus();
  }

  async function onActivate(): Promise<void> {
    setFailure(null);

    // 3-band: chala bozorda so'rov UMUMAN yuborilmaydi.
    if (!canActivate) {
      focusFirstUnmet();
      return;
    }

    try {
      await activate.mutateAsync(marketId ?? "");
      toast.success(t("wizard.activated"));
      router.replace("/dashboard");
    } catch (error) {
      const serverBlocking = activationBlockingOf(error);
      if (serverBlocking !== null) {
        // 5-band: ro'yxat ALMASHADI, alohida xato yo'li ochilmaydi.
        setConflict(serverBlocking);
        focusFirstUnmet();
        return;
      }
      /*
       * To'liqlikka aloqasi yo'q xato (`market_is_active`, tarmoq, 403).
       * U ham AYNI e'lon konteynerida chiqadi: alohida xato bloki §6.6 ning
       * "chala bozor nosozlik emas" xabarini bulg'ardi, javobsiz tugma esa
       * boshi berk ko'cha bo'lardi.
       */
      setFailure(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <h2 className="text-lg font-semibold">{t("wizard.checklistTitle")}</h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* 1-band: ro'yxat `can_activate === true` bo'lganda ham chiziladi. */}
        <ul className="flex flex-col gap-1">
          {rows.map((row) => {
            const unmet =
              !row.neutral && row.codes.some((code) => blockedCodes.has(code));

            return (
              <ChecklistLine
                href={row.href}
                key={row.labelKey}
                label={t(row.labelKey)}
                linkRef={
                  row.labelKey === firstUnmetKey ? firstUnmetRef : undefined
                }
                neutral={row.neutral}
                step={row.step}
                unmet={unmet}
                value={row.value}
              />
            );
          })}

          {extras.map((item) => (
            <ChecklistLine
              key={item.code}
              label={t("wizard.incomplete")}
              linkRef={item.code === firstUnmetKey ? firstUnmetRef : undefined}
              neutral={false}
              step={item.step}
              unmet
              value={item.detail}
            />
          ))}
        </ul>

        <div className="flex flex-col gap-2">
          {/*
           * 2-band: `disabled` atributi YO'Q. Tugma har doim fokuslanadi va
           * bosiladi; chala bozorda u so'rov yubormay, sababni e'lon qiladi.
           */}
          <Button
            aria-disabled={canActivate ? undefined : true}
            className="self-start"
            onClick={() => void onActivate()}
            size="lg"
            variant={canActivate ? "default" : "secondary"}
          >
            {t("wizard.activate")}
          </Button>

          {/*
           * Konteyner DOIM mavjud: `aria-live` faqat MAVJUD elementga
           * qo'shilgan matnni e'lon qiladi — bo'sh joyga birdan paydo
           * bo'lgan konteyner e'lon qilinmay qolishi mumkin.
           */}
          <p aria-live="polite" className="text-sm text-text-muted" role="status">
            {failure ??
              (attempted && firstUnmetLabel !== null
                ? `${t("wizard.blockedReason")} ${firstUnmetLabel}`
                : "")}
          </p>
        </div>

        {/*
         * §6.7: kamera haqidagi bitta NEYTRAL jumla — ramkasiz, fonsiz,
         * ikonkasiz.
         *
         * 3-FAZA DELTASI: kalit `wizard.cameraLater` dan `wizard.cameraNote`
         * ga ko'chdi va matn "keyinroq ulanadi" dan "istalgan vaqtda
         * ulanadi" ga o'zgardi (UI-SPEC §11.5). "Keyinroq" bo'lim
         * mavjud bo'lmaganda ROST edi; endi u kutish holatini bildirib,
         * kamerasiz bozorni chala ko'rsatardi.
         */}
        <p className="text-sm text-text-muted">{t("wizard.cameraNote")}</p>
      </CardContent>
    </Card>
  );
}

function ChecklistLine({
  href,
  label,
  linkRef,
  neutral,
  step,
  unmet,
  value,
}: {
  href?: string;
  label: string;
  linkRef?: React.Ref<HTMLAnchorElement>;
  neutral: boolean;
  step: number | null;
  unmet: boolean;
  value: string;
}) {
  const marker = neutral ? (
    <Dot aria-hidden="true" className="size-4 shrink-0 text-text-muted" />
  ) : unmet ? (
    <X aria-hidden="true" className="size-4 shrink-0 text-text-muted" />
  ) : (
    <Check aria-hidden="true" className="size-4 shrink-0 text-text" />
  );

  const body = (
    <>
      {marker}
      <span className="flex-1">{label}</span>
      <span className="text-text-muted">{value}</span>
    </>
  );

  // 4-band: bajarilmagan band — o'sha qadamga havola.
  if (unmet && step !== null) {
    return (
      <li>
        <Link
          className="flex min-h-11 items-center gap-2 rounded-md px-2 text-sm hover:bg-surface-muted"
          href={`${WIZARD_SETUP_PATH}?step=${step}`}
          ref={linkRef}
        >
          {body}
          <ArrowRight aria-hidden="true" className="size-4 shrink-0" />
        </Link>
      </li>
    );
  }

  /*
   * Ustadan tashqaridagi bo'limga doimiy havola (U-3).
   *
   * ⚠ `ArrowRight` ATAYIN QO'YILMAYDI. Yuqoridagi tarmoqda u "shu yerni
   * to'ldiring" degan chaqiruv; bu yerda esa band to'ldirishni TALAB
   * QILMAYDI va o'sha strelka uni to'siqqa o'xshatib qo'yardi (D-16).
   * Belgi `·` bo'lib qoladi — hech qachon `✓` yoki `✗`.
   */
  if (href !== undefined) {
    return (
      <li>
        <Link
          className="flex min-h-11 items-center gap-2 rounded-md px-2 text-sm hover:bg-surface-muted"
          href={href}
        >
          {body}
        </Link>
      </li>
    );
  }

  return (
    <li className="flex min-h-11 items-center gap-2 px-2 text-sm">{body}</li>
  );
}
