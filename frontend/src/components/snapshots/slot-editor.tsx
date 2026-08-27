"use client";

import { useId, useState } from "react";
import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

/*
 * =============================================================================
 * VAQTLAR MUHARRIRI — §4.6 NING BARCHA QOIDALARI.
 *
 * SAQLANADIGAN SHAKL — TEKIS VAQTLAR RO'YXATI. Oraliq SAQLANMAYDI, UI
 * uni kengaytiradi (04-RESEARCH §A.1): ikki shakl ikki kod yo'lini
 * tug'dirardi va «06:00–08:00/30» ni tahrirlash «bitta vaqtni olib
 * tashlash» amali bilan nima qilishini hech kim ayta olmasdi.
 *
 * ⚠⚠ 12 LIK CHEGARA — KLIENTDA QULAYLIK, XAVFSIZLIK CHEGARASI EMAS
 *    (§4.6 [TALAB]). Haqiqiy shift SERVERDA:
 *    `Settings.snapshot_max_times_per_day` ni `ScheduleRepository.
 *    _normalize()` majburlaydi (04-05/04-09) va u DevTools bilan
 *    chetlab o'tilmaydi.
 *
 *    Bu izoh ATAYIN yozilgan: usiz keyingi tahrirlovchi klientdagi
 *    chegarani «yetarli» deb hisoblab, server tomonini bo'shashtirardi.
 *    Arifmetika esa shafqatsiz — chegarasiz «06:00–20:00 har 5
 *    daqiqada» = 169 vaqt × 25 kamera = 4 225 kadr/kun va Contabo diski
 *    bir necha oyda to'lardi.
 *
 * ⚠ ERKIN RAQAMLI QADAM MAYDONI QURILMAYDI. `Select` faqat 15/30/60
 *   beradi: 1 daqiqalik qadam chegarani DARHOL yeb qo'yardi va xato
 *   holatini normal ish jarayoniga aylantirardi — ya'ni admin har
 *   to'ldirishda qizil matn ko'rishga o'rganardi.
 *
 * ⚠ CHEGARADA `aria-disabled` ISHLATILADI. Muqobil variant fokusni ham,
 *   e'lonni ham yo'q qilardi va «nega bosilmayapti?» savoliga javob
 *   beradigan joy qolmasdi (§12.3, 02-UI-SPEC §6.6 dan meros).
 *   Taqiqlangan atributning nomi bu yerda LITERAL yozilmaydi — qabul
 *   mezoni uni grep bilan qidiradi va izohdagi nusxa darvozani o'z
 *   hujjati ustida qizartirardi.
 *
 * ⚠ ORALIQ CHEGARADAN OSHSA HECH NIMA QO'SHILMAYDI. Qisman to'ldirish
 *   «qaysilari qo'shildi?» savolini tug'dirardi va admin ro'yxatni
 *   qo'lda solishtirishga majbur bo'lardi.
 * =============================================================================
 */

/** §4.6 — kuniga eng ko'p vaqt. Server juftisi: `snapshot_max_times_per_day`. */
export const MAX_TIMES_PER_DAY = 12;

/** Oraliq generatorining qadamlari — daqiqada (§4.6). */
const RANGE_STEPS = [15, 30, 60] as const;
type RangeStep = (typeof RANGE_STEPS)[number];

/**
 * Qadam -> yorliq kaliti.
 *
 * `as const satisfies` (`schedule-card.tsx` dagi bilan bir xil sabab):
 * dinamik kalit next-intl ning tip xavfsizligidan chiqib ketardi.
 */
const STEP_KEYS = {
  15: "snapshots.rangeStep15",
  30: "snapshots.rangeStep30",
  60: "snapshots.rangeStep60",
} as const satisfies Record<RangeStep, string>;

/** Muharrir e'lon qiladigan yagona xabarlar to'plami. */
type SlotMessageKey =
  | "snapshots.rangeInvalid"
  | "snapshots.rangeTooMany"
  | "snapshots.slotDuplicate"
  | "snapshots.slotInvalid"
  | "snapshots.slotLimitReached";

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/u;

/** `HH:mm` -> yarim tundan boshlab daqiqa. */
function toMinutes(time: string): number {
  const [hours, minutes] = time.split(":");
  return Number(hours) * 60 + Number(minutes);
}

/** Daqiqa -> `HH:mm` (har doim ikki xonali — leksik saralash uchun). */
function toTime(minutes: number): string {
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}

/**
 * `from`..`to` oralig'ini `step` daqiqa bilan kengaytiradi — IKKALA CHET
 * HAM KIRADI.
 *
 * ⚠ SOF FUNKSIYA va u ATAYIN eksport qilinadi: chegara arifmetikasini
 *   DOM orqali o'lchash 49 ta chipni sanashni talab qilardi.
 *
 * `to === from` bo'lsa bitta vaqt qaytadi — bu xato emas, admin bitta
 * vaqtni oraliq orqali qo'shishi mumkin.
 */
export function expandRange(
  from: string,
  to: string,
  stepMinutes: number,
): string[] {
  const start = toMinutes(from);
  const end = toMinutes(to);
  if (end < start || stepMinutes <= 0) return [];

  const out: string[] = [];
  for (let minute = start; minute <= end; minute += stepMinutes) {
    out.push(toTime(minute));
  }
  return out;
}

/**
 * Mavjud va yangi vaqtlarni BIRLASHTIRADI — almashtirmaydi (§4.6).
 *
 * ⚠ ALMASHTIRISH qo'lda kiritilgan `16:00` ni JIMGINA yo'qotardi va
 *   admin buni faqat ertasi kuni, kadr olinmaganda sezardi.
 *
 * Tartib har doim o'sish bo'yicha: `HH:mm` nol bilan to'ldirilgani
 * uchun leksik saralash vaqt bo'yicha saralash bilan bir xil.
 */
export function mergeTimes(
  current: readonly string[],
  incoming: readonly string[],
): string[] {
  return [...new Set([...current, ...incoming])].sort();
}

export function SlotEditor({
  onChange,
  readOnly = false,
  value,
}: {
  onChange: (next: string[]) => void;
  /** `past` profil — o'qish uchun (§4.5). Chiplar qoladi, boshqaruv yo'q. */
  readOnly?: boolean;
  /** `HH:mm` ro'yxati — HAR DOIM o'sish tartibida. */
  value: readonly string[];
}) {
  const t = useTranslations();
  const addId = useId();
  const fromId = useId();
  const toId = useId();
  const stepId = useId();
  const rangeLabelId = useId();

  const [draft, setDraft] = useState("");
  const [rangeFrom, setRangeFrom] = useState("");
  const [rangeTo, setRangeTo] = useState("");
  const [step, setStep] = useState<RangeStep>(30);
  const [message, setMessage] = useState<SlotMessageKey | null>(null);

  const atLimit = value.length >= MAX_TIMES_PER_DAY;

  function addDraft(): void {
    if (!TIME_PATTERN.test(draft)) {
      setMessage("snapshots.slotInvalid");
      return;
    }
    /*
     * Chegara dublikatdan OLDIN tekshiriladi: chegaraga yetgan holatda
     * takroriy vaqt kiritilsa, foydalanuvchi uchun to'sadigan HAQIQIY
     * sabab chegara bo'ladi va aynan u aytilishi kerak.
     */
    if (atLimit) {
      setMessage("snapshots.slotLimitReached");
      return;
    }
    if (value.includes(draft)) {
      setMessage("snapshots.slotDuplicate");
      return;
    }

    setMessage(null);
    setDraft("");
    onChange(mergeTimes(value, [draft]));
  }

  function applyRange(): void {
    if (!TIME_PATTERN.test(rangeFrom) || !TIME_PATTERN.test(rangeTo)) {
      setMessage("snapshots.slotInvalid");
      return;
    }
    if (toMinutes(rangeTo) < toMinutes(rangeFrom)) {
      setMessage("snapshots.rangeInvalid");
      return;
    }

    const merged = mergeTimes(value, expandRange(rangeFrom, rangeTo, step));
    /*
     * ⛔ QISMAN TO'LDIRISH YO'Q: butun natija chegaraga sig'masa RO'YXAT
     *    UMUMAN O'ZGARMAYDI. Kesib qo'shish «qaysilari qo'shildi?»
     *    savolini tug'dirardi.
     */
    if (merged.length > MAX_TIMES_PER_DAY) {
      setMessage("snapshots.rangeTooMany");
      return;
    }

    setMessage(null);
    onChange(merged);
  }

  function removeTime(time: string): void {
    setMessage(null);
    onChange(value.filter((item) => item !== time));
  }

  return (
    <fieldset className="m-0 flex flex-col gap-3 border-0 p-0">
      <legend className="mb-2 text-sm font-semibold">
        {t("snapshots.times")}
      </legend>

      {/*
       * Chegara ko'rsatkichi DOIM ko'rinadi — foydalanuvchi chegaraga
       * YETGUNICHA (§4.6). U `role="status"` ichida, ya'ni vaqt
       * qo'shilgani, olib tashlangani va rad etilgani BIR joyda e'lon
       * qilinadi (§12.6 dagi «slot muharriri holati» hududi).
       */}
      <p className="flex flex-wrap items-baseline gap-2 text-xs" role="status">
        <span className="font-mono text-text-muted">
          {t("snapshots.timesUsage", {
            max: MAX_TIMES_PER_DAY,
            used: value.length,
          })}
        </span>
        {message === null ? null : (
          <span className="text-danger-text">
            {t(message, { max: MAX_TIMES_PER_DAY })}
          </span>
        )}
      </p>

      <ul className="flex flex-wrap gap-2">
        {value.map((time) => (
          <li
            className="inline-flex min-h-11 items-center gap-1 rounded-md border border-border-ui px-3 text-sm"
            key={time}
          >
            <span className="font-mono">{time}</span>
            {readOnly ? null : (
              <button
                aria-label={`${t("snapshots.removeTime")} ${time}`}
                className="inline-flex size-6 items-center justify-center rounded-sm text-text-muted hover:bg-surface-muted hover:text-text"
                onClick={() => removeTime(time)}
                type="button"
              >
                <X aria-hidden="true" className="size-4" />
              </button>
            )}
          </li>
        ))}
      </ul>

      {readOnly ? null : (
        <>
          <div className="flex flex-wrap items-end gap-2">
            <Field className="w-36" id={addId} label={t("snapshots.time")}>
              <Input
                id={addId}
                onChange={(event) => setDraft(event.target.value)}
                type="time"
                value={draft}
              />
            </Field>
            <Button
              aria-disabled={atLimit ? true : undefined}
              className="min-h-11"
              onClick={addDraft}
              variant="secondary"
            >
              <Plus aria-hidden="true" />
              {t("snapshots.addTime")}
            </Button>
          </div>

          {/*
           * ⛔ ICHKI `fieldset` EMAS (§12.2): uch boshqaruv va tugma
           *    BITTA amalni tashkil qiladi va ular allaqachon «Vaqtlar»
           *    guruhi ichida. Ichma-ich `fieldset` skrinriderda ikki
           *    daraja e'lon qilardi va hech qanday foyda bermasdi.
           */}
          <div
            aria-labelledby={rangeLabelId}
            className="flex flex-col gap-2 rounded-md bg-surface-muted p-3"
            role="group"
          >
            <p className="text-sm font-semibold" id={rangeLabelId}>
              {t("snapshots.rangeFill")}
            </p>
            <div className="flex flex-wrap items-end gap-2">
              <Field className="w-36" id={fromId} label={t("snapshots.rangeFrom")}>
                <Input
                  id={fromId}
                  onChange={(event) => setRangeFrom(event.target.value)}
                  type="time"
                  value={rangeFrom}
                />
              </Field>
              <Field className="w-36" id={toId} label={t("snapshots.rangeTo")}>
                <Input
                  id={toId}
                  onChange={(event) => setRangeTo(event.target.value)}
                  type="time"
                  value={rangeTo}
                />
              </Field>
              <Field className="w-40" id={stepId} label={t("snapshots.rangeStep")}>
                <Select
                  id={stepId}
                  onChange={(event) =>
                    setStep(Number(event.target.value) as RangeStep)
                  }
                  value={String(step)}
                >
                  {RANGE_STEPS.map((option) => (
                    <option key={option} value={String(option)}>
                      {t(STEP_KEYS[option])}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button
                className="min-h-11"
                onClick={applyRange}
                variant="secondary"
              >
                {t("snapshots.rangeApply")}
              </Button>
            </div>
          </div>
        </>
      )}
    </fieldset>
  );
}
