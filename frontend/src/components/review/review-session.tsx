"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { BudgetCounter } from "@/components/review/budget-counter";
import { DecisionBar } from "@/components/review/decision-bar";
import { EvidenceFrame } from "@/components/review/evidence-frame";
import type { FrameState } from "@/components/review/evidence-frame";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import type { AnswerResult, HumanAnswer, ReviewItem } from "@/lib/api-types";
import {
  useAnswerUncertainItem,
  useReviewBudget,
  useUncertainNext,
} from "@/lib/review-queries";

/*
 * =============================================================================
 * NOANIQ NAVBAT SESSIYASI — ⛔ BIR VAQTDA BITTA BAND (D-18 ning UI shakli).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ NAVBAT RO'YXAT EMAS — VA BU D-18 NING BUTUN MAZMUNI
 * -----------------------------------------------------------------------
 * «Hammasini tasdiqlash» tugmasini olib tashlash YETARLI EMAS. Har
 * qatorda ikki tugmali ro'yxat — QADAMLARI KO'PROQ BO'LGAN o'sha tugma:
 * ko'z qatordan chiqmaydi, qo'l takrorlaydi va natija MA'LUMOTGA
 * O'XSHAGAN SHOVQIN bo'ladi.
 *
 * Diqqat — bu ekranda sarflanadigan YAGONA resurs, shuning uchun
 * ekranning ENG KATTA elementi DALIL RASMI bo'ladi, ro'yxat emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ S-7 VA S-8 NING FARQI HAYOTIY (§8.3)
 * -----------------------------------------------------------------------
 *   S-7 «navbat bo'sh»    -> ISH TUGADI (yaxshi xabar)
 *   S-8 «byudjet tugadi»  -> ish QOLGAN bo'lishi mumkin
 *
 * Ikkalasini bir xil ko'rsatish nazoratchida «hammasi bajarildi» degan
 * YOLG'ON hosil qilardi. Server ham aynan shu sababdan ikki xil kod
 * beradi va byudjetni navbat bo'shligidan OLDIN tekshiradi
 * (`reviews.py::next_uncertain_item`).
 * ⛔ S-8 da «Yana ko'rish» tugmasi YO'Q (§16.2): byudjet — KVOTA emas,
 *    DIQQAT CHEGARASI. Uni ochish charchagan holda berilgan javoblarni
 *    ma'lumotga aylantirardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ TIZIM JAVOBI FAQAT JAVOBDAN KEYIN (§7.1) — VA U 1,5 SONIYA TURADI
 * -----------------------------------------------------------------------
 * Noaniq navbatda oshkor panel S-6 bo'yicha o'zi ketadi va keyingi band
 * keladi. Ko'rmasdan tekshirishda esa u QOLADI va yagona oldinga yo'l
 * `[Keyingisi →]` bo'ladi — farq ataylab: u yerda javob O'ZGARMAS va
 * nazoratchi natijani o'z vaqtida o'qishi kerak.
 * =============================================================================
 */

/** Oshkor panel ko'rinadigan vaqt (S-6) — test uni shu yerdan oladi. */
export const REVEAL_MS = 1500;

/** Sessiyaning oltita holati (§8.3 dagi S-1…S-11 ning ustki darajasi). */
export type SessionState =
  | "loading"
  | "error"
  | "queue-empty"
  | "budget-exhausted"
  | "sample-not-drawn"
  | "ready";

/**
 * Sessiya holati — SOF FUNKSIYA (`zoneEditorState()` da o'rnatilgan naqsh).
 *
 * ⚠ TARTIB AHAMIYATLI VA U SHU YERDA QULFLANADI:
 *
 *     band bor -> yuklanmoqda -> xato kodi -> umumiy xato
 *
 *   «Band bor» BIRINCHI, chunki fon yangilanishi paytida band EKRANDA
 *   qolishi kerak: uni yo'qotish nazoratchini o'zi ko'rib turgan rasmdan
 *   ayirardi va u javobni qaytadan o'ylardi.
 *
 * ⛔ UCH XATO KODI UCH XIL HOLAT BERADI va ularni bittaga yig'ish
 *    TAQIQ: «ish tugadi», «byudjet tugadi» va «namuna hali tanlanmagan»
 *    ning KEYINGI QADAMI butunlay boshqa. Uchalasini «xato» deb
 *    ko'rsatish esa NORMAL holatni nosozlik qilib ko'rsatardi.
 */
export function sessionState(input: {
  hasItem: boolean;
  isPending: boolean;
  isError: boolean;
  errorCode: string | null;
}): SessionState {
  if (input.hasItem) return "ready";
  if (input.isPending) return "loading";
  if (input.isError) {
    switch (input.errorCode) {
      case "review_budget_exhausted":
        return "budget-exhausted";
      case "review_queue_empty":
        return "queue-empty";
      case "review_sample_not_drawn":
        return "sample-not-drawn";
      default:
        return "error";
    }
  }
  return "loading";
}

/** `unknown` xatodan domen kodi — xom `detail` EKRANGA hech qachon chiqmaydi. */
export function errorCodeOf(error: unknown): string | null {
  return error instanceof ApiError ? error.detail : null;
}

export type ReviewSessionProps = {
  /** `/review` uyiga qaytish manzili — til prefiksi bilan. */
  exitHref: string;
};

export function ReviewSession({ exitHref }: ReviewSessionProps) {
  const t = useTranslations();
  const todayIso = businessDayIn("Asia/Tashkent", new Date());

  const next = useUncertainNext();
  const budget = useReviewBudget(todayIso);
  const answer = useAnswerUncertainItem(todayIso);

  const [frame, setFrame] = useState<FrameState>("loading");
  const [reveal, setReveal] = useState<AnswerResult | null>(null);
  const [notice, setNotice] = useState<string>("");
  const [exitOpen, setExitOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /*
   * =======================================================================
   * ⛔ IKKI BOSISH ORASIDA RENDER BO'LMASLIGI MUMKIN — VA BU O'LCHANDI.
   *
   * `blocked` render paytida hisoblanadi, `answer.isPending` esa faqat
   * KEYINGI renderda `true` bo'ladi. Bir hodisa oqimida ketma-ket uch
   * bosish (yoki `1`,`2`,`3` ni tez bosish) UCHALASI HAM eski `blocked`
   * qiymatini ko'rardi va UCHTA javob yuborilardi — birinchisi yozilib,
   * qolgan ikkitasi `409` bo'lardi.
   *
   * Bu D-18 ning eng tabiiy chetlab o'tish yo'li: «bitta so'rov = bitta
   * qaror» kafolati holat emas, POYGA masalasi. `useRef` DARHOL yopiladi
   * va render kutmaydi.
   *
   * ⚠ QULF BAYROQ EMAS, BAND IDENTIFIKATORI. Bayroq bo'lganda uni band
   *   almashganda RENDER PAYTIDA nollash kerak bo'lardi, ref'ga esa
   *   render paytida tegib bo'lmaydi (`react-hooks/refs`). Identifikator
   *   bilan nollash UMUMAN KERAK EMAS: yangi bandning identifikatori
   *   boshqa, ya'ni qulf o'zi ochiladi. Shu bilan «nollashni unutish»
   *   sinfidagi xato ham yo'qoladi.
   * =======================================================================
   */
  const submittedRef = useRef<string | null>(null);

  const item: ReviewItem | null = next.data ?? null;

  /*
   * Band almashganda oshkor panel, e'lon va yuborish qulfi TOZALANADI.
   *
   * ⛔ `useEffect` EMAS, RENDER PAYTIDA MOSLASH (React: «adjusting state
   *    when a prop changes»). Effekt varianti kaskad render berardi va
   *    `react-hooks/set-state-in-effect` uni xato sifatida rad etadi;
   *    undan ham muhimi — effekt BIR RENDER KECHIKARDI, ya'ni yangi band
   *    bir kadr davomida ESKI oshkor panel bilan ko'rinardi.
   */
  const [shownItemId, setShownItemId] = useState<string | null>(null);
  if (item !== null && item.assignment_id !== shownItemId) {
    setShownItemId(item.assignment_id);
    setReveal(null);
    setNotice("");
  }

  useEffect(
    () => () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    },
    [],
  );

  const state = sessionState({
    hasItem: item !== null,
    isPending: next.isPending,
    isError: next.isError,
    errorCode: errorCodeOf(next.error),
  });

  const onFrameState = useCallback((value: FrameState) => {
    setFrame(value);
    if (value === "ready") setNotice("frame-ready");
  }, []);

  const onBlockedPress = useCallback(() => {
    setNotice("image-required");
  }, []);

  const submit = useCallback(
    (value: HumanAnswer) => {
      if (item === null || submittedRef.current === item.assignment_id) return;
      submittedRef.current = item.assignment_id;
      answer.mutate(
        { assignmentId: item.assignment_id, answer: value },
        {
          /*
           * ⚠ XATODA QULF OCHILADI: tarmoq uzilishi javobni YOZMAGAN,
           *   ya'ni nazoratchi qayta urina olishi SHART. Muvaffaqiyatda
           *   esa qulf o'sha bandga BOG'LANGAN holda qoladi — o'sha
           *   bandga ikkinchi javob serverda `409` bo'lardi.
           */
          onError: () => {
            submittedRef.current = null;
          },
          onSuccess: (result) => {
            setReveal(result);
            setNotice("answer-saved");
            toast.success(t("review.toastAnswerSaved"));
            /*
             * ⚠ S-6: oshkor panel 1,5 s ko'rinadi va O'ZI ketadi.
             *   Keyingi band mutatsiyaning `invalidate` idan keladi,
             *   ya'ni bu taymer NAVIGATSIYA emas — u faqat panelni
             *   yopadi.
             */
            timerRef.current = setTimeout(() => setReveal(null), REVEAL_MS);
          },
        },
      );
    },
    [answer, item, t],
  );

  /*
   * ⛔ DARVOZA: rasm tayyor bo'lmaguncha va javob yuborilayotganda uchala
   *    tugma ham bloklangan. Javob yozilgandan keyin ham (oshkor panel
   *    ko'rinib turganda) — ikkinchi bosish `409` bo'lardi.
   */
  const blocked = frame !== "ready" || answer.isPending || reveal !== null;
  /*
   * N-5: kadr allaqachon javob berilgan bo'lsa. Kod ham, uchala tildagi
   * matn ham ALLAQACHON bor edi — faqat hech qayerda chizilmasdi, ya'ni
   * nazoratchi javobi o'tmaganini bilmay qolardi (o'lchandi 2026-08-18).
   * Blind navbatidagi bilan bir xil shakl — ikkala navbat bir xil
   * tushuntirish beradi.
   */
  const alreadyAnswered =
    errorCodeOf(answer.error) === "review_already_answered";

  const counters = budget.data?.uncertain ?? null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("review.uncertainTitle")}
          </h1>
          {counters === null ? null : (
            <BudgetCounter
              answered={counters.answered}
              budget={counters.budget}
            />
          )}
        </div>

        {/*
         * §7.8 — JAVOBSIZ BAND BO'LSA DL-4 TASDIG'I; javob berilgan
         * bo'lsa tasdiqsiz chiqiladi. Ikkinchi holatda boshqaruv
         * HAVOLA bo'ladi: havola semantikasi (o'rta tugma, manzil
         * satri) dasturiy o'tishda yo'qolardi.
         */}
        {state === "ready" && reveal === null ? (
          <Button onClick={() => setExitOpen(true)} size="sm" variant="ghost">
            {t("review.exit")}
          </Button>
        ) : (
          <a
            className="inline-flex items-center rounded-md px-3 py-2 text-sm font-medium underline underline-offset-2"
            href={exitHref}
          >
            {t("review.exit")}
          </a>
        )}
      </header>

      {/*
       * SESSIYA HOLATI — YAGONA jonli hudud (§13.6: bir vaqtda ikkitadan
       * ortiq faol bo'lmaydi). Uchala e'lon ham shu yerdan o'qiladi,
       * ya'ni ular bir-birini bosib ketmaydi.
       */}
      <p className="sr-only" role="status">
        {notice === "frame-ready" ? t("review.frameReady") : null}
        {notice === "answer-saved" ? t("review.answerSaved") : null}
        {notice === "image-required" ? t("review.imageRequired") : null}
      </p>

      {state === "loading" ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="aspect-video w-full" />
        </div>
      ) : null}

      {state === "queue-empty" ? (
        <EmptyState
          description={t("review.emptyUncertainHint")}
          title={t("review.emptyUncertain")}
        />
      ) : null}

      {/*
       * ⛔ S-8 — «Yana ko'rish» tugmasi YO'Q va `action` ham berilmaydi.
       *    Byudjet DIQQAT chegarasi; uni ochish charchagan javoblarni
       *    ma'lumotga aylantirardi (§16.2).
       */}
      {state === "budget-exhausted" && counters !== null ? (
        <EmptyState
          description={t("review.emptyBudgetHint", { max: counters.budget })}
          title={t("review.emptyBudget")}
        />
      ) : null}

      {state === "error" || state === "sample-not-drawn" ? (
        <div
          className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
          role="alert"
        >
          <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
          <p className="text-sm">{t("errors.loadFailedBody")}</p>
          <Button onClick={() => void next.refetch()} size="sm" variant="secondary">
            {t("common.retry")}
          </Button>
        </div>
      ) : null}

      {item === null ? null : (
        <div className="flex flex-col gap-4">
          {/*
           * ⛔ `key` — KADR HOLATINI NOLLASHNING YAGONA MEXANIZMI
           *    (`evidence-frame.tsx` izohiga qarang): band almashganda
           *    komponent qayta tug'iladi va «rasm yuklandi» bayrog'i
           *    yangi bandga meros bo'lib o'tmaydi.
           */}
          <EvidenceFrame
            key={item.snapshot_id}
            onStateChange={onFrameState}
            polygon={item.polygon}
            snapshotId={item.snapshot_id}
          />

          <div className="flex flex-col gap-1">
            <p className="text-sm font-semibold">
              {t("review.stallLine", {
                stall: item.stall_code,
                zone: item.zone_name,
              })}
            </p>
            <p className="text-xs text-text-muted">
              {/*
               * N-3: kamera NOMI asosiy, kanal raqami yordamchi. «Kanal 11»
               * nazoratchiga jismonan hech nima demaydi — u kamerani nomi
               * bilan taniydi. Nom ma'lumotda ALLAQACHON bor edi, lekin
               * ekranga chiqarilmasdi (o'lchandi 2026-08-18).
               */}
              {t("review.frameLine", {
                camera: item.camera_name,
                channel: item.channel_no,
                date: item.business_date,
                time: item.slot_time.slice(0, 5),
              })}
            </p>
            {/*
             * ⚠ «Sotuvchi biriktirilgan» — MOTIVATSIYA, ANKOR EMAS: u
             *   bandlik haqida hech nima demaydi (§7.3). ⛔ Bu qator
             *   KO'RMASDAN TEKSHIRISHDA CHIZILMAYDI va u yerda payloadda
             *   maydonning O'ZI yo'q (05-11).
             */}
            {item.has_active_vendor ? (
              <p className="text-xs text-text-muted">
                {t("review.vendorAttached")}
              </p>
            ) : null}
          </div>

          {reveal === null ? null : (
            <UncertainReveal result={reveal} />
          )}

          <DecisionBar
            blocked={blocked}
            locked={reveal !== null}
            onAnswer={submit}
            onBlockedPress={onBlockedPress}
            pendingAnswer={answer.isPending ? answer.variables?.answer : null}
          />

          {frame === "failed" ? (
            <p className="text-sm text-danger-text">
              {t("review.imageRequired")}
            </p>
          ) : null}

          {alreadyAnswered ? (
            <div
              className="flex flex-col items-start gap-3 rounded-md bg-warning/20 p-4 text-text"
              role="alert"
            >
              <p className="text-sm font-semibold">
                {t("review.errorCause.review_already_answered")}
              </p>
              <p className="text-sm">
                {t("review.errorFix.review_already_answered")}
              </p>
            </div>
          ) : null}
        </div>
      )}

      {/*
       * DL-4 — fokus [Bekor qilish] da, HECH QACHON destruktiv tugmada
       * (§13.5). `ConfirmDialog` buni o'zi bajaradi.
       *
       * ⚠ Tasdiq NAVIGATSIYA qiladi. Sinovda bu shox bosilmaydi (jsdom
       *   navigatsiyani bajarmaydi); test dialogning OCHILISHINI va
       *   fokusni o'lchaydi.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("review.exit")}
        confirmVariant="secondary"
        description={t("review.exitBody")}
        onConfirm={() => {
          window.location.assign(exitHref);
        }}
        onOpenChange={setExitOpen}
        open={exitOpen}
        title={t("review.exitTitle")}
      />
    </div>
  );
}

/* --- S-6 ning oshkor paneli ------------------------------------------------ */

/**
 * Noaniq navbatning QISQA oshkor paneli — 1,5 soniya.
 *
 * ⚠ `reveal-panel.tsx` (ko'rmasdan tekshirish) BILAN BIR XIL EMAS va
 *   nusxa ham emas: u yerda panel QOLADI, «o'zgartirib bo'lmaydi»
 *   jumlasini olib yuradi va sessiyaning YAGONA oldinga yo'lini
 *   (`[Keyingisi →]`) tashiydi. Bu yerda esa panel o'zi ketadi va hech
 *   qanday boshqaruv bermaydi — ikki xil XULQ, ikki xil komponent.
 *
 * ⚠ MA'LUMOT `useMutation` NATIJASIDAN keladi (prop sifatida) — birorta
 *   `GET` marshrut bu ma'lumotni bermaydi (`AnswerResponse` docstringi).
 */
function UncertainReveal({ result }: { result: AnswerResult }) {
  const t = useTranslations();
  const LABEL: Record<
    HumanAnswer,
    "review.answerOccupied" | "review.answerEmpty" | "review.answerUnclear"
  > = {
    occupied: "review.answerOccupied",
    empty: "review.answerEmpty",
    uncertain: "review.answerUnclear",
  };

  return (
    <div className="flex flex-col gap-1 rounded-md bg-surface-muted p-4">
      <p className="text-sm">
        {t("review.yourAnswer")}: <strong>{t(LABEL[result.human_answer])}</strong>
      </p>
      <p className="text-sm">
        {t("review.systemAnswer")}:{" "}
        <strong>{t(LABEL[result.system_answer])}</strong>
      </p>
      <p className="text-sm font-semibold">
        {result.matched ? t("review.answersMatch") : t("review.answersDiffer")}
      </p>
    </div>
  );
}
