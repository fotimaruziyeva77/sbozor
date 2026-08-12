"use client";

import { useRef, useState } from "react";
import { History } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { EvidenceLink } from "@/components/reconciliation/evidence-link";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { CASE_STATUSES, RESOLUTION_NOTE_MAX } from "@/lib/api-types";
import type { CaseStatusValue } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { ApiError } from "@/lib/api-client";
import { hasPermission } from "@/lib/rbac";
import { reconErrorView } from "@/lib/reconciliation-errors";
import type { CaseDetail } from "@/lib/reconciliation-queries";
import {
  isCaseStatus,
  useCaseDetail,
  useCaseUpdate,
} from "@/lib/reconciliation-queries";
import { useAssigneeLabels } from "@/lib/vendor-labels";

/*
 * =============================================================================
 * DL-5 — NOMUVOFIQLIK TAFSILOTI VA HUKM (RECON-02, §9.3/§9.4).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. NEGA DIALOG, MARSHRUT ⛔ EMAS
 * -----------------------------------------------------------------------
 * Muqobil `/reconciliation/{id}` ⛔ RAD ETILDI va sabab mahsulotda:
 * bu yerda ⛔ ERKIN MATNLI yechim maydoni bor, ya'ni marshrut
 * ⛔ YARIM YOZILGAN YECHIM MATNI ULASHILADIGAN URL yaratardi. Havolani
 * nusxalab yuborgan direktor qabul qiluvchining ⛔ BOSHQA HOLATDAGI
 * formani ko'rishini bilmasdi.
 *
 * ⛔ Shuning uchun dialog holati URL'da ⛔ UMUMAN saqlanmaydi: kun
 *    ulashiladi (u HISOBOT), bitta nomuvofiqlik esa ⛔ JARAYON va u
 *    ulashilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. HUQUQ YO'Q -> YOZUV YUZASI ⛔ UMUMAN CHIZILMAYDI
 * -----------------------------------------------------------------------
 * ⛔ O'CHIRILGAN TUGMA ⛔ EMAS, tooltip ⛔ EMAS: o'chirilgan boshqaruv
 *    ⛔ MAVJUD IMKONIYATNI E'LON QILARDI va bozor admini «nega menga
 *    ruxsat yo'q?» degan savol bilan qolardi. Uning uchun bu dialog
 *    ⛔ HISOBOT bo'lib ko'rinadi: subyekt, dalil, holat, mas'ul va
 *    o'zgarmas audit izi — hammasi O'QISH uchun.
 *
 * ⛔ YANGI HUQUQ QO'SHILMAYDI: hukm MAVJUD huquq ostida va u
 *    ⛔ FAQAT DIREKTORDA. Huquq matritsasining ikkala nusxasi ham
 *    (server va klient) bu rejada ⛔ TEGILMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. HOLAT — YOPIQ RO'YXAT, YECHIM — ERKIN MATN. ARALASHMAYDI
 * -----------------------------------------------------------------------
 * `<option>` qiymatlari ⛔ REYESTRDAN ITERATSIYA bilan quriladi, qo'lda
 * yozilgan ro'yxatdan EMAS. Va holat uchun ⛔ ERKIN MATNLI MAYDON
 * YO'Q: beshinchi «boshqa» a'zosi hisobotda ⛔ GURUHLANMASDI va u
 * amalda ENG KATTA guruh bo'lib qolardi — ⛔ aniqlik ulushining
 * MAXRAJI esa aniqlanmagan bo'lib qolardi.
 *
 * ⛔⛔ `<textarea>` — BU TAQIQNING ISTISNOSI VA SABAB YOZILISHI SHART:
 *    6-fazada erkin matn TAQIQLANGAN edi, chunki sabab-kod YOPIQ
 *    to'plam bo'lishi kerak edi va erkin matn guruhlanmasdi. Bu yerda
 *    vaziyat BOSHQA: guruhlash ⛔ ALLAQACHON yopiq to'plamda (holat),
 *    ya'ni erkin matn ⛔ HECH QANDAY METRIKANI BUZMAYDI. Va nizoda
 *    (D-02) hukmning ⛔ SABABI kerak — «asossiz» degan bir so'zni
 *    sotuvchiga tushuntirib bo'lmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 4. AUDIT IZI ⛔ TAHRIRLANMAYDI VA O'CHIRILMAYDI
 * -----------------------------------------------------------------------
 * O'zgarish — ⛔ YANGI QATOR (append-only, D-14). Shuning uchun
 * `[Tahrirlash]` / `[O'chirish]` ⛔ UMUMAN YOZILMAYDI va bu fazada
 * ⛔ BIRORTA destruktiv amal yo'q: holat orqaga QAYTARILADI, qator
 * o'chirilmaydi, xabar bekor qilinmaydi. Shuning uchun ⛔ tasdiq
 * dialogi ham ⛔ ISHLATILMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 5. «BITTA SO'ROV = BITTA QAROR» QULFI
 * -----------------------------------------------------------------------
 * Qulf ⛔ BAND IDENTIFIKATORINI saqlaydi, bayroqni emas: render
 * paytida hisoblangan bayroqni bir hodisa oqimidagi ikki bosish
 * IKKALASI ham ESKI qiymatda ko'rardi. Ikki so'rov ⛔ IKKI AUDIT
 * QATORI yozardi va tarix ⛔ YOLG'ON ko'rinardi — D-14 ning butun
 * mazmuni «kim, qachon, nima qildi» ekanini hisobga olsak, bu eng
 * qimmat nosozlik.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 6. NOL O'TISHDA TUGMA ⛔ FAOL EMAS — VA BU YOLG'ONNING OLDINI OLADI
 * -----------------------------------------------------------------------
 * Server BIR XIL holatga o'tishni ⛔ **409** bilan rad etadi va klient
 * o'sha kodni «Holatni boshqa foydalanuvchi allaqachon o'zgartirgan»
 * matniga xaritalaydi. Nol o'tishda esa ⛔ HECH KIM HECH NIMA
 * QILMAGAN, ya'ni matn ⛔ YOLG'ON bo'lardi.
 *
 * ⛔ Shuning uchun tanlangan holat joriysiga TENG bo'lganda tugma
 *    ⛔ `aria-disabled` (⛔ `disabled` EMAS — u fokusni yo'qotadi va
 *    skrinrider foydalanuvchisi sababni umuman eshitmasdi). Poyga
 *    shoxi esa OCHIQ qoladi: boshqa direktor allaqachon o'sha holatga
 *    o'tkazgan bo'lsa, 409 keladi va o'shanda matn ⛔ ROST bo'ladi.
 *
 * ⚠ OCHIQ NARX: ⛔ FAQAT mas'ulni o'zgartirish bugun mumkin emas —
 *   server `status` ni MAJBURIY talab qiladi va nol o'tishni rad
 *   etadi (07-10 kontrakti). Mas'ul holat o'zgarishi BILAN BIRGA
 *   yoziladi. To'g'ri tuzatish — serverda alohida biriktirish amali,
 *   klientda nol o'tishni «jimgina o'tkazish» EMAS.
 * =============================================================================
 */

/** Terminal holatlar — ⛔ ULARDA YECHIM MATNI MAJBURIY (§9.4). */
const TERMINAL_STATUSES: ReadonlySet<CaseStatusValue> = new Set([
  "justified",
  "unjustified",
]);

/**
 * Audit izidagi holat YO'LI — ⛔ noma'lum qiymat YASHIRILMAYDI.
 *
 * ⛔ Sxema reyestr bilan qulflanmagan (04-10 darsi), ya'ni backend
 *    beshinchi a'zo qo'shsa u BU YERGA yetib keladi. Qatorni chizmaslik
 *    tarixdan bir bo'g'inni ⛔ JIMGINA yo'qotardi — va aynan o'sha
 *    bo'g'in nizoda kerak bo'lardi.
 *
 * ⛔ `from_status === null` = qator TUG'ILDI: birinchi hodisada oldingi
 *    holat FIZIK ravishda yo'q va uni «—» bilan to'ldirish TO'QILGAN
 *    qiymat bo'lardi (05-14 darsi).
 */
function StatusPath({ from, to }: { from: string | null; to: string }) {
  const t = useTranslations();

  const label = (value: string) =>
    isCaseStatus(value)
      ? t(`recon.caseStatus.${value}`)
      : t("recon.caseStatus.unknown");

  return <>{from === null ? label(to) : `${label(from)} → ${label(to)}`}</>;
}

export type CaseDetailDialogProps = {
  /** `null` — dialog yopiq; ro'yxat holatni O'ZI ushlaydi. */
  caseId: string | null;
  onOpenChange: (open: boolean) => void;
};

export function CaseDetailDialog({
  caseId,
  onOpenChange,
}: CaseDetailDialogProps) {
  const t = useTranslations();

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={caseId !== null}>
      <Dialog.Content
        description={t("recon.caseDetailHint")}
        size="lg"
        sheetOnMobile
        srOnlyDescription
        title={t("recon.caseDetailTitle")}
      >
        {caseId === null ? null : <CaseDetailBody caseId={caseId} />}

        <Dialog.Footer>
          <Dialog.Close asChild>
            <Button variant="secondary">{t("common.close")}</Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}

/** Dialog TANASI — so'rov FAQAT ochilganda ketadi. */
function CaseDetailBody({ caseId }: { caseId: string }) {
  const t = useTranslations();
  const detail = useCaseDetail(caseId);

  if (detail.isPending) {
    return (
      <div aria-busy="true" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (detail.isError || detail.data === undefined) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.loadFailedBody")}
      </p>
    );
  }

  return <CaseDetailContent detail={detail.data} />;
}

function CaseDetailContent({ detail }: { detail: CaseDetail }) {
  const t = useTranslations();
  const format = useFormatter();
  const { principal } = useAuthStore();

  const mayDecide = hasPermission(principal?.roles ?? [], "dispute_decide");

  return (
    <div className="flex flex-col gap-4">
      {/* --- 1: SUBYEKT ---------------------------------------------------- */}
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">
          {detail.subject_kind === "occupied_unpaid"
            ? t("recon.unpaidTitle")
            : t("recon.unregisteredTitle")}
        </h3>
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <div className="flex gap-2">
            <dt className="text-text-muted">{t("recon.dayColumn")}</dt>
            <dd className="m-0">{detail.service_date}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="text-text-muted">{t("recon.statusColumn")}</dt>
            <dd className="m-0">
              <CaseStatusBadge status={detail.status} />
            </dd>
          </div>
        </dl>
      </section>

      {/*
       * --- 2: DALIL — ⛔ MAVJUD KOMPONENT, IKKINCHI NUSXA YO'Q ------------
       *
       * ⛔ Dalilsiz qatorda element UMUMAN chizilmaydi (komponentning
       *   o'z qarori) — platsholder ham qo'yilmaydi.
       */}
      <EvidenceLink
        serviceDate={detail.service_date}
        snapshotIds={detail.evidence_snapshot_ids}
      />

      {/*
       * --- 3-5 + TUGMA: YOZUV YUZASI -------------------------------------
       *
       * ⛔ HUQUQ YO'Q -> BU BLOK UMUMAN CHIZILMAYDI (2-band).
       */}
      {mayDecide ? <DecisionForm detail={detail} /> : null}

      {/* --- 6: AUDIT IZI — ⛔ O'ZGARMAS ------------------------------------ */}
      <section className="flex flex-col gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold">
          <History aria-hidden="true" className="size-4" />
          {t("recon.auditTrailTitle")}
        </h3>
        <ol className="flex flex-col gap-2 text-sm">
          {detail.events.map((event) => (
            <li
              className="flex flex-wrap gap-x-2 gap-y-1"
              key={`${event.created_at}-${event.to_status}`}
            >
              <span className="text-text-muted">
                {format.dateTime(new Date(event.created_at), {
                  dateStyle: "short",
                  timeStyle: "short",
                })}
              </span>
              <span>
                {/*
                 * ⛔ `null` = TIZIM, «noma'lum» EMAS: navbatni cron
                 *   ochadi va unga odam biriktirish «kim qaror qildi?»
                 *   savoliga YOLG'ON javob bo'lardi.
                 */}
                {event.actor_user_id === null ? (
                  t("recon.actorSystem")
                ) : (
                  <ActorLabel userId={event.actor_user_id} />
                )}
              </span>
              <span>
                <StatusPath from={event.from_status} to={event.to_status} />
              </span>
              {event.note === null ? null : (
                <span className="w-full text-text-muted">{event.note}</span>
              )}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

/** Aktorning YORLIG'I — ism TAQIQLANGAN yuzadan TASHQARIDA o'qiladi. */
function ActorLabel({ userId }: { userId: string }) {
  const assignees = useAssigneeLabels();
  const label = assignees.labelOf(userId);

  /* ⛔ Ism kelmasa identifikatorning qisqa shakli — bo'sh katak EMAS. */
  return (
    <span className={label === null ? "font-mono text-xs" : undefined}>
      {label ?? userId.slice(0, 8)}
    </span>
  );
}

/**
 * 3-5-bo'limlar va yakuniy amal — ⛔ FAQAT hukm huquqi BOR sessiyada.
 *
 * ⛔ BU KOMPONENT `mayDecide` NI QAYTA TEKSHIRMAYDI: u umuman
 *    chaqirilmaydi. Ichkarida ikkinchi shart yozilsa, «chizilmaydi»
 *    qoidasi «ko'rinmaydi» ga aylanardi va DOM'da qoldirilgan
 *    boshqaruv darvozani jimgina o'tkazardi.
 */
function DecisionForm({ detail }: { detail: CaseDetail }) {
  const t = useTranslations();
  const assignees = useAssigneeLabels();
  const update = useCaseUpdate();

  const [status, setStatus] = useState<string>(detail.status);
  const [note, setNote] = useState<string>(detail.resolution_note ?? "");
  const [assignee, setAssignee] = useState<string>(
    detail.assignee_user_id ?? "",
  );

  /*
   * ⛔ QULF BAND IDENTIFIKATORINI SAQLAYDI (5-band): render paytida
   *   hisoblangan bayroqni bir hodisa oqimidagi ikki bosish IKKALASI
   *   ham ESKI qiymatda ko'rardi.
   */
  const submittedRef = useRef<string | null>(null);

  const noteRequired = TERMINAL_STATUSES.has(status as CaseStatusValue);
  const unchanged = status === detail.status;
  const blocked =
    unchanged || (noteRequired && note.trim() === "") || update.isPending;

  const errorView = reconErrorView(
    update.error instanceof ApiError ? update.error.detail : null,
  );

  const onSave = () => {
    if (blocked) return;
    /* ⛔ IKKINCHI BOSISH SHU YERDA TO'XTAYDI — so'rov yuborilmaydi. */
    if (submittedRef.current === detail.case_id) return;
    submittedRef.current = detail.case_id;

    update.mutate(
      {
        caseId: detail.case_id,
        status: status as CaseStatusValue,
        resolutionNote: note.trim() === "" ? null : note.trim(),
        assigneeUserId: assignee === "" ? null : assignee,
      },
      {
        /*
         * ⛔ QULF FAQAT XATODA BO'SHATILADI: muvaffaqiyatda qator
         *   ALLAQACHON o'zgargan va ikkinchi so'rov nol o'tish (409)
         *   bo'lardi.
         */
        onError: () => {
          submittedRef.current = null;
        },
      },
    );
  };

  return (
    <fieldset className="flex flex-col gap-4 border-0 p-0">
      <legend className="text-sm font-semibold">
        {t("recon.decisionLegend")}
      </legend>

      {/* --- 3: HOLAT — ⛔ YOPIQ RO'YXAT, REYESTRDAN ------------------------ */}
      <Field id="case-status" label={t("recon.caseStatusLabel")}>
        <Select
          id="case-status"
          onChange={(event) => setStatus(event.target.value)}
          value={status}
        >
          {CASE_STATUSES.map((value) => (
            <option key={value} value={value}>
              {t(`recon.caseStatus.${value}`)}
            </option>
          ))}
        </Select>
      </Field>

      {/* --- 4: MAS'UL — bozor foydalanuvchilari --------------------------- */}
      <Field id="case-assignee" label={t("recon.assigneeLabel")}>
        <Select
          id="case-assignee"
          onChange={(event) => setAssignee(event.target.value)}
          value={assignee}
        >
          {/* ⛔ `value=""` — «biriktirilmagan», reyestr a'zosi EMAS. */}
          <option value="">{t("recon.assigneeNone")}</option>
          {assignees.options.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </Select>
      </Field>

      {/* --- 5: YECHIM — ⛔ ERKIN MATN (3-bandning istisnosi) --------------- */}
      <Field
        hint={t("recon.resolutionHint")}
        id="case-resolution"
        label={t("recon.resolutionLabel")}
      >
        <textarea
          aria-describedby="case-resolution-hint"
          className="min-h-24 w-full rounded-sm border border-border-ui bg-surface px-3 py-2 text-sm text-text outline-none transition-colors focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25"
          id="case-resolution"
          maxLength={RESOLUTION_NOTE_MAX}
          onChange={(event) => setNote(event.target.value)}
          value={note}
        />
      </Field>

      {errorView === null ? null : (
        <p
          className="flex flex-col gap-1 rounded-sm bg-surface-muted px-3 py-2 text-sm"
          role="alert"
        >
          <span>{t(errorView.causeKey)}</span>
          <span className="text-text-muted">{t(errorView.fixKey)}</span>
        </p>
      )}

      {/*
       * ⛔ FAZADAGI YAGONA AKSENT FONLI TUGMA (§13.3): u TANLOV emas,
       *   OQIBAT — holat va yechim allaqachon tanlangan, tugma faqat
       *   YOZADI, ya'ni urg'u hech narsani buzmaydi.
       *
       * ⛔ `aria-disabled`, `disabled` EMAS: `disabled` element fokusni
       *   yo'qotadi va skrinrider foydalanuvchisi sababni umuman
       *   eshitmasdi.
       */}
      <Button
        aria-disabled={blocked}
        onClick={onSave}
        size="lg"
        variant="default"
      >
        {t("recon.save")}
      </Button>
    </fieldset>
  );
}
