"use client";

import { useCallback, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { BlindBanner } from "@/components/blind-audit/blind-banner";
import { RevealPanel } from "@/components/blind-audit/reveal-panel";
import { DecisionBar } from "@/components/review/decision-bar";
import { EvidenceFrame } from "@/components/review/evidence-frame";
import type { FrameState } from "@/components/review/evidence-frame";
import { errorCodeOf, sessionState } from "@/components/review/review-session";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnswerResult, BlindAuditItem, HumanAnswer } from "@/lib/api-types";
import {
  useAnswerBlindItem,
  useBlindBudget,
  useBlindNext,
} from "@/lib/blind-audit-queries";

/*
 * =============================================================================
 * ⛔⛔ KO'RMASDAN TEKSHIRISH SESSIYASI — OLDINGA-FAQAT (UI-SPEC §7.6, §7.7).
 *
 * -----------------------------------------------------------------------
 * ⛔ SESSIYADA AYNAN BITTA YO'NALISH BOR
 * -----------------------------------------------------------------------
 * Javobni qaytaradigan yoki oldingi bandga olib boradigan BIRORTA
 * boshqaruv qurilmaydi — na tugma, na havola, na klaviatura yorlig'i.
 * Va gap faqat boshqaruvda emas: marshrutda band identifikatori ham YO'Q
 * (§4.5), ya'ni «orqaga qaytish» YO'LINING O'ZI mavjud emas. Uchinchi
 * qatlam — server: ikkinchi `POST` `409` bilan rad etiladi.
 *
 * Sabab o'lchovga oid: yozilgan javobni keyin tahrirlash imkoniyati
 * nazoratchiga o'z javobini TIZIMNIKIGA MOSLAB QO'YISH yo'lini ochardi
 * va aniqlik 100% ga intilardi — ya'ni hisobot o'zi o'lchayotgan
 * narsani o'zgartirardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ JAVOB BERILGAN BAND EKRANDA MUZLAB QOLADI
 * -----------------------------------------------------------------------
 * Javob yozilgach so'rov qatlami keshni tozalaydi va KEYINGI band
 * yuklana boshlaydi (bu ruxsat — u ham ko'r payload). Lekin ekranda
 * javob berilgan bandning O'ZI qoladi, aks holda oshkor panel
 * BOSHQA bandning rasmi ustida ko'rinardi va nazoratchi o'z javobini
 * noto'g'ri rastaga bog'lardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ NIMA UCHUN `sessionState` VA `DecisionBar` NOANIQ NAVBATDAN OLINADI
 * -----------------------------------------------------------------------
 * Ular tizimning javobini UMUMAN olib yurmaydi: birinchisi xato kodini
 * holatga aylantiradi, ikkinchisi uchta tugma chizadi. Ularni bu yerda
 * qayta yozish ikki nusxa hosil qilardi va ikkalasi ham darvozadan
 * o'tardi — ya'ni takrorlash HECH QANDAY himoya bermas edi, faqat
 * «dalil rasmi qaror darvozasi» qoidasining ikkinchi, ajralib
 * ketadigan nusxasini yaratardi. Ajratilgani — MA'LUMOT QATLAMI
 * (`lib/blind-audit-queries.ts`) va PAYLOAD TIPI, chunki xavf aynan
 * o'sha yerda (§5.3).
 * =============================================================================
 */

export type BlindSessionProps = {
  /** `/review` uyiga qaytish manzili — til prefiksi bilan. */
  exitHref: string;
};

type Frozen = { item: BlindAuditItem; result: AnswerResult };

export function BlindSession({ exitHref }: BlindSessionProps) {
  const t = useTranslations();
  const todayIso = businessDayIn("Asia/Tashkent", new Date());

  const next = useBlindNext();
  const budget = useBlindBudget(todayIso);
  const answer = useAnswerBlindItem();

  const [frame, setFrame] = useState<FrameState>("loading");
  const [frozen, setFrozen] = useState<Frozen | null>(null);
  const [notice, setNotice] = useState<string>("");
  const [exitOpen, setExitOpen] = useState(false);

  /*
   * Qulf BAND IDENTIFIKATORINI saqlaydi (`review-session.tsx` dagi bilan
   * bir xil sabab): `blocked` render paytida hisoblanadi, ya'ni bir
   * hodisa oqimidagi ikki bosish ikkalasi ham eski qiymatni ko'rardi.
   * Bu yerda oqibat OG'IRROQ — ikkinchi javob serverda `409` bo'lib,
   * nazoratchi «javobim yozilmadimi?» degan xato xulosaga kelardi.
   */
  const submittedRef = useRef<string | null>(null);

  const live: BlindAuditItem | null = next.data ?? null;
  const item = frozen?.item ?? live;

  const [shownItemId, setShownItemId] = useState<string | null>(null);
  if (frozen === null && live !== null && live.assignment_id !== shownItemId) {
    setShownItemId(live.assignment_id);
    setNotice("");
  }

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
    setNotice(frozen === null ? "image-required" : "locked");
  }, [frozen]);

  const submit = useCallback(
    (value: HumanAnswer) => {
      if (item === null || submittedRef.current === item.assignment_id) return;
      submittedRef.current = item.assignment_id;
      answer.mutate(
        { assignmentId: item.assignment_id, answer: value },
        {
          onError: () => {
            submittedRef.current = null;
          },
          onSuccess: (result) => {
            setFrozen({ item, result });
            setNotice("answer-saved");
          },
        },
      );
    },
    [answer, item],
  );

  /*
   * ⛔ YAGONA OLDINGA YO'L. `frozen` tozalanadi va ekran so'rov
   *    qatlamidan kelgan KEYINGI bandga o'tadi. Javob yozilgach kesh
   *    allaqachon tozalangan, ya'ni bu yerda «eski band» qaytib
   *    kelishi mumkin emas.
   */
  const goNext = useCallback(() => {
    setFrozen(null);
    setNotice("");
    if (next.data === undefined) void next.refetch();
  }, [next]);

  const blocked = frozen !== null || frame !== "ready" || answer.isPending;

  const counters = budget.data?.blind_audit ?? null;
  const lockedError = errorCodeOf(answer.error) === "blind_answer_locked";

  return (
    <div className="flex flex-col gap-6">
      {/*
       * ⚠ `<h1>` DOM'DA BIRINCHI — skrinrider foydalanuvchisi uchun
       *   BIRINCHI eshitiladigan narsa «Ko'rmasdan tekshirish» bo'lishi
       *   kerak (§7.6, 3-kanal). Lenta undan keyin keladi va `sticky`
       *   bilan tepada qoladi.
       */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("review.blindTitle")}
        </h1>

        {state === "ready" && frozen === null ? (
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
      </div>

      <BlindBanner
        answered={counters?.answered ?? null}
        total={counters?.budget ?? null}
      />

      {/* Sessiya holati — YAGONA jonli hudud (§13.6). */}
      <p className="sr-only" role="status">
        {notice === "frame-ready" ? t("review.frameReady") : null}
        {notice === "answer-saved" ? t("review.answerSaved") : null}
        {notice === "image-required" ? t("review.imageRequired") : null}
        {notice === "locked" ? t("review.answerLockedShort") : null}
      </p>

      {state === "loading" ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="aspect-video w-full" />
        </div>
      ) : null}

      {/*
       * ⛔ S-7 (E-3) — «bugungi tekshiruv bajarildi». U S-9 dan
       *    BUTUNLAY boshqa xabar: bu yerda ish TUGADI, u yerda esa
       *    asbob HALI ISHLAMAGAN.
       */}
      {state === "queue-empty" && counters !== null ? (
        <EmptyState
          action={
            <a
              className="inline-flex items-center rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg"
              href={exitHref}
            >
              {t("review.backToReview")}
            </a>
          }
          description={t("review.emptyBlindDoneHint", {
            done: counters.answered,
            total: counters.budget,
          })}
          title={t("review.emptyBlindDone")}
        />
      ) : null}

      {/* ⛔ S-8 — «Yana ko'rish» YO'Q (§16.2). */}
      {state === "budget-exhausted" && counters !== null ? (
        <EmptyState
          description={t("review.emptyBudgetHint", { max: counters.budget })}
          title={t("review.emptyBudget")}
        />
      ) : null}

      {/*
       * ⛔ S-9 — «Hozir tanla» tugmasi YO'Q (D-17, 1-himoya). Namuna
       *    urug'i HOSILA va u tanlanmaydi; tugma bo'lsa «bu turda xato
       *    ko'p chiqdi, qaytadan boshlayman» yo'li ochilardi va u
       *    aniqlikni YUQORIGA siljitardi.
       */}
      {state === "sample-not-drawn" ? (
        <EmptyState
          description={t("review.emptySampleNotDrawnHint")}
          title={t("review.emptySampleNotDrawn")}
        />
      ) : null}

      {state === "error" ? (
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
          <EvidenceFrame
            key={item.snapshot_id}
            onStateChange={onFrameState}
            polygon={item.polygon}
            showZoom={frozen === null}
            snapshotId={item.snapshot_id}
          />

          {/*
           * ⛔ «SOTUVCHI BIRIKTIRILGAN» QATORI BU YERDA CHIZILMAYDI va
           *    payloadda maydonning O'ZI ham yo'q (05-11). Tasodifiy
           *    namunada «bu qarorning oqibati bor» qatori diqqatni
           *    NOTEKIS taqsimlardi — ya'ni o'lchov asbobining O'ZIDAGI
           *    og'ish bo'lardi.
           */}
          <div className="flex flex-col gap-1">
            <p className="text-sm font-semibold">
              {t("review.stallLine", {
                stall: item.stall_code,
                zone: item.zone_name,
              })}
            </p>
            <p className="text-xs text-text-muted">
              {t("review.frameLine", {
                channel: item.channel_no,
                date: item.business_date,
                time: item.slot_time.slice(0, 5),
              })}
            </p>
          </div>

          {/*
           * ⛔ S-10 — server javob allaqachon yozilganini aytdi.
           *    [Qayta urinish] BERILMAYDI (§4.5): taqiq STRUKTURAVIY,
           *    ya'ni qayta urinish HECH QACHON boshqacha natija
           *    bermaydi va tugma yolg'on umid berardi.
           */}
          {lockedError ? (
            <div
              className="flex flex-col items-start gap-3 rounded-md bg-warning/20 p-4 text-text"
              role="alert"
            >
              <p className="text-sm font-semibold">
                {t("review.errorCause.blind_answer_locked")}
              </p>
              <p className="text-sm">{t("review.errorFix.blind_answer_locked")}</p>
              <Button onClick={goNext} size="sm" variant="secondary">
                {t("review.next")}
              </Button>
            </div>
          ) : null}

          {frozen === null ? null : (
            <RevealPanel onNext={goNext} result={frozen.result} />
          )}

          <DecisionBar
            blocked={blocked}
            locked={frozen !== null}
            onAnswer={submit}
            onBlockedPress={onBlockedPress}
            pendingAnswer={answer.isPending ? answer.variables?.answer : null}
          />
        </div>
      )}

      {/*
       * DL-4 — matni NOANIQ NAVBATNIKIDAN BOSHQA (§7.8): bu yerda
       * javobsiz band navbatga qaytmaydi, u NAMUNADA QOLADI va kun
       * oxirigacha javob berilmasa hisobotda «javobsiz» deb sanaladi
       * (4-dushman). Nazoratchi bu farqni bilishi SHART.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("review.exit")}
        confirmVariant="secondary"
        description={t("review.exitBlindBody")}
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
