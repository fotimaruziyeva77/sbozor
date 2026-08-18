"use client";

import { useCallback, useId, useState } from "react";
import { CircleCheckBig, Loader2 } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { parseSoumInput } from "@/lib/api-types";
import { formatAmount } from "@/lib/format-number";
import { useCloseShift } from "@/lib/shift-queries";
import type { ShiftCloseResult } from "@/lib/shift-queries";

/*
 * =============================================================================
 * ⛔⛔ KO'R NAQD DEKLARATSIYASI — BU KOMPONENTNING BUTUN MA'NOSI KO'RMASLIK.
 *
 * Kassir smenani yopganda qo'lidagi naqdni SANAB kiritadi va tizim unga
 * o'z raqamini KO'RSATMAYDI. Ya'ni bu yerdagi qiymat — o'lchov emas,
 * SHAHODAT: kassir nima sanagan bo'lsa, o'shani yozadi.
 *
 * ⛔ SHUNING UCHUN BU FORMA `ui/` PRIMITIVIGA KO'TARILMAYDI (§3.2).
 *    Umumiy «summa kiritish formasi» ertaga tizim raqamini `prop`
 *    sifatida qabul qilardi va ko'rlik BITTA `props` uzatilishi bilan
 *    buzilardi — kod-ko'rikda esa bu o'zgarish bir qatorlik va begunoh
 *    ko'rinardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KO'RLIK UCH QATLAM, VA BU FAYL UCHINCHISI
 * -----------------------------------------------------------------------
 *   1. SXEMA   — yopish javobida sakkiz maydon E'LON QILINMAYDI (06-10);
 *   2. KLIENT  — `shiftCloseResponseSchema` `z.strictObject` bilan AYNAN
 *                to'rt kalit (06-03);
 *   3. EKRAN   — shu fayl: yopilgandan keyin AYNAN UCHTA narsa.
 *
 * ⛔ Nega CSS yoki shartli render MEXANIZM EMAS: brauzerga yetgan maydon
 *    O'QILADI — DevTools, tarmoq paneli, React DevTools, `JSON.stringify`.
 *    «Ko'rsatmayapmiz» — kod-ko'rik DA'VOSI, o'lchov emas.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ YOPILGANDAN KEYIN — TAQIQ RO'YXATI (§10.3)
 * -----------------------------------------------------------------------
 * Ekranda AYNAN uchta narsa bo'ladi: «Deklaratsiya yozildi» belgisi ·
 * kiritilgan naqd · [Yangi smena ochish]. ⛔ Quyidagilarning BIRORTASI
 * ham chizilmaydi — na raqam, na so'z, na rang bilan:
 *
 *   · tizim hisoblagan naqd;
 *   · kutilgan naqd;
 *   · deklaratsiya bilan tizim orasidagi FARQ (ikkala nomda ham);
 *   · «to'g'ri» / «noto'g'ri» / «mos keldi» degan baho;
 *   · foiz, ulush yoki har qanday ikkinchi son.
 *
 * ⛔ FARQ AYNIQSA: `tizim = deklaratsiya − farq` — BITTA AYIRISH. Ya'ni
 *    farqni ko'rsatish tizim raqamini ko'rsatish bilan MATEMATIK JIHATDAN
 *    bir xil. Undan tashqari har kun farqni ko'rgan kassir bir haftada
 *    «tizim odatda shuncha deydi» degan LANGAR hosil qiladi va sanashdan
 *    OLDIN taxmin qiladi.
 *
 * ⚠ OCHIQ YOZILGAN NARX: kassir o'z kamomadini DARHOL bilmaydi. Bu qabul
 *   qilinadi — naqdni topshirish paytida direktor farqni ko'radi va
 *   suhbat o'sha yerda, IKKI TOMON ishtirokida bo'ladi (D-02 ning nizo
 *   modeli). Bu smenada tuzatish yo'li baribir YO'Q: deklaratsiya
 *   o'zgarmas (D-25), farq avtomatik to'g'rilanmaydi (D-26) — ya'ni
 *   ko'rsatish HECH QANDAY harakatni ochmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ KO'RLIK EKRANDA TUSHUNTIRILADI (§10.2) — `collect.shiftBlindNotice`
 * -----------------------------------------------------------------------
 * Tushuntirilmagan ko'rlik «tizim buzuq» deb o'qiladi va kassir raqamni
 * TAXMIN QILIB kiritardi — ya'ni ko'r deklaratsiya o'z maqsadini
 * yo'qotardi. Shuning uchun yo'riqnoma jumlasi MAJBURIY va u maydonning
 * `aria-describedby` iga ham bog'lanadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ NOL RUXSAT, MANFIY RAD (§10.2)
 * -----------------------------------------------------------------------
 * Butun smenasi terminal bo'lgan kun — REAL holat va unda qo'lda naqd
 * bo'lmaydi. Nolni rad etish kassirni YOLG'ON son kiritishga majburlardi,
 * ya'ni butun o'lchovni buzardi. Manfiy qiymat esa ma'nosiz: naqd
 * qutisida minus bo'lmaydi.
 *
 * ⛔ NOTO'G'RI KIRITISH ENDI NOMLANADI — `collect.declaredInvalid`.
 *
 *   Ilgari bu yerda faqat `aria-invalid` bor edi va ko'radigan
 *   foydalanuvchi uchun ekran JIM qolardi: maydon qizarardi-yu, NEGA
 *   qizargani aytilmasdi. `tariffs.amountInvalid` bu yerda YOLG'ON
 *   bo'lardi — u «noldan katta butun son bo'lsin» deydi, §10.2 esa
 *   nolni AYNAN ruxsat etadi. Shuning uchun kalit ALOHIDA va uning
 *   matni nolning qonuniyligini OCHIQ aytadi.
 *
 * ⚠ MATN IKKI JOYDA EMAS, BITTA: u `aria-describedby` orqali maydonga
 *   bog'lanadi va `role="status"` bilan e'lon qilinadi — ikkinchi
 *   nusxa skrinriderda ikki marta o'qilardi.
 * =============================================================================
 */

/**
 * Kiritilgan matndan deklaratsiya qiymati — SOF funksiya.
 *
 * `null` — «hali yaroqli qiymat yo'q»: bo'sh maydon ham, manfiy son ham,
 * kasr ham, harf ham shu javobni beradi. Chaqiruvchi bo'sh va NOTO'G'RI
 * holatni alohida ajratadi (birinchisida yo'riqnoma, ikkinchisida
 * `aria-invalid`).
 *
 * ⛔ QOIDANING O'ZI `api-types.ts::parseSoumInput()` DA va u ⛔ YAGONA
 *    (WR-04): DL-1 ning chetlanish summasi ham AYNAN shu funksiyadan
 *    o'tadi. Ilgari u `Number(raw)` ishlatardi va `"1e5"`, `"0x10"`,
 *    `"+15000"` ni jimgina qabul qilardi — bitta domen tushunchasi
 *    uchun ikki qarama-qarshi qoida edi.
 *
 * ⛔ `min: 0` — §10.2: butun smenasi terminal bo'lgan kun REAL holat va
 *    nolni rad etish kassirni YOLG'ON son kiritishga majburlardi. Bu
 *    ikki chaqiruv orasidagi YAGONA farq.
 */
export function parseDeclaredSoum(raw: string): number | null {
  return parseSoumInput(raw, { min: 0 });
}

export type ShiftCloseFormProps = {
  /** Yopiladigan ochiq smenaning identifikatori — sahifadan keladi. */
  shiftId: string;
  /** [Yangi smena ochish] bosilganda: sahifa BIRINCHI holatiga qaytadi. */
  onReopen: () => void;
};

export function ShiftCloseForm({ shiftId, onReopen }: ShiftCloseFormProps) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const close = useCloseShift();

  const fieldId = useId();
  const hintId = `${fieldId}-hint`;
  const errorId = `${fieldId}-error`;

  const [raw, setRaw] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(false);
  const [result, setResult] = useState<ShiftCloseResult | null>(null);

  const trimmed = raw.trim();
  const declared = parseDeclaredSoum(raw);
  const invalid = trimmed !== "" && declared === null;

  const requestConfirm = useCallback(() => {
    if (declared === null) {
      /* ⛔ §14.3: bosish RAD ETILMAYDI — u SABABNI e'lon qiladi. */
      setNotice(true);
      return;
    }
    setNotice(false);
    setConfirmOpen(true);
  }, [declared]);

  const confirmClose = useCallback(() => {
    if (declared === null) return;
    setBusy(true);

    close.mutate(
      { shift_id: shiftId, declared_soum: declared },
      {
        onError: () => {
          setBusy(false);
        },
        onSuccess: (record) => {
          setBusy(false);
          setConfirmOpen(false);
          setResult(record);
          toast.success(t("collect.declarationWritten"));
        },
      },
    );
  }, [close, declared, shiftId, t]);

  /* ------------------------------------------------------------------ */
  /* YOPILGANDAN KEYIN — AYNAN UCHTA NARSA (§10.3)                       */
  /* ------------------------------------------------------------------ */

  if (result !== null) {
    const written = `${formatAmount(format, result.declared_soum, locale)} ${t("collect.amountUnit")}`;

    return (
      <div className="flex flex-col gap-4">
        {/*
         * §14.5 ning 5-hududi. `sr-only`: u KO'RINADIGAN narsa emas —
         * ko'rinadigan uchtasi pastda. Aks holda ekranda to'rtinchi
         * element paydo bo'lardi.
         */}
        <p className="sr-only" role="status">
          {t("collect.declarationWritten")} · {written}
        </p>

        {/*
         * ⛔ AYNAN UCHTA BOLA. Har biri `data-shift-result` bilan
         *    NOMLANADI va darvoza to'plam TENGLIGI bilan o'lchaydi —
         *    to'rtinchi bola qo'shilsa (nomlangan bo'lsin, nomlanmagan
         *    bo'lsin) test O'ZI qizaradi, `not.toContain` kerak emas.
         */}
        <div
          className="flex flex-col items-start gap-4"
          data-shift-result-region=""
        >
          <Badge data-shift-result="badge" tone="success">
            <CircleCheckBig aria-hidden="true" className="mr-1 size-3" />
            {t("collect.declarationWritten")}
          </Badge>

          <p
            className="font-mono text-2xl font-semibold tabular-nums"
            data-shift-result="figure"
          >
            {written}
          </p>

          <Button
            className="min-h-11"
            data-shift-result="action"
            onClick={onReopen}
            variant="secondary"
          >
            {t("collect.shiftNew")}
          </Button>
        </div>
      </div>
    );
  }

  /* ------------------------------------------------------------------ */
  /* FORMA (§10.2 jadvali)                                              */
  /* ------------------------------------------------------------------ */

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg leading-snug font-semibold">
        {t("collect.shiftClose")}
      </h2>

      {/*
       * ⛔ YO'RIQNOMA — MAJBURIY VA KO'RINADIGAN. Uni maydonning kichik
       *    izohiga tushirish «ko'rlik tushuntirildi» degan shartni
       *    shaklan bajarib, MA'NAN buzardi: o'qilmagan tushuntirish
       *    tushuntirilmagan ko'rlik bilan bir xil.
       */}
      <p className="text-sm text-text" id={hintId}>
        {t("collect.shiftBlindNotice")}
      </p>

      <Field id={fieldId} label={t("collect.declaredLabel")}>
        <Input
          aria-describedby={invalid || notice ? `${hintId} ${errorId}` : hintId}
          aria-invalid={invalid ? true : undefined}
          autoComplete="off"
          autoFocus
          className="min-h-14 font-mono text-lg tabular-nums"
          enterKeyHint="done"
          id={fieldId}
          inputMode="numeric"
          onChange={(event) => {
            setNotice(false);
            setRaw(event.target.value);
          }}
          type="text"
          value={raw}
        />
      </Field>

      {/*
       * ⛔ `aria-disabled`, `disabled` EMAS (§14.3): o'chirilgan tugma
       *    fokus olmaydi va skrinrider uni umuman o'qimaydi — «nega
       *    bosilmayapti?» savoliga javob beradigan joy qolmaydi.
       */}
      <Button
        aria-disabled={declared === null ? true : undefined}
        className="min-h-14 w-full"
        onClick={requestConfirm}
      >
        {busy ? (
          <Loader2
            aria-hidden="true"
            className="animate-spin motion-reduce:animate-none"
          />
        ) : null}
        {t("common.close")}
      </Button>

      {/*
       * ⛔ IKKI TETIK, BITTA MATN: maydon NOTO'G'RI to'ldirilgan bo'lsa
       *    (`invalid`) yoki bo'sh maydon bilan tasdiq bosilgan bo'lsa
       *    (`notice`, §14.3 — bosish RAD ETILMAYDI, u SABABNI e'lon
       *    qiladi). Ikkala holatda ham javob AYNI: «faqat raqam, nol ham
       *    mumkin» — chunki ikkalasining ham sababi bitta.
       */}
      {invalid || notice ? (
        <p className="text-sm text-danger-text" id={errorId} role="status">
          {t("collect.declaredInvalid")}
        </p>
      ) : null}

      {/*
       * ⛔ DL-4 — 1-daraja. Fokus destruktiv tugmada EMAS (meros xulq:
       *    `confirm-dialog.tsx` bekor qilishga fokuslaydi).
       *
       * ⛔ OQIBAT SUMMANI TAKRORLAB AYTILADI: dialog matnida kiritilgan
       *    naqd YANA bir marta ko'rinadi. Deklaratsiya o'zgarmas, ya'ni
       *    «yozgandan keyin tuzataman» yo'li YO'Q va tasdiq shundan.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("collect.shiftClose")}
        description={
          <>
            {t("collect.shiftConfirmBody")} {t("collect.declaredLabel")}:{" "}
            <span className="font-mono font-semibold tabular-nums">
              {declared === null
                ? ""
                : `${formatAmount(format, declared, locale)} ${t("collect.amountUnit")}`}
            </span>
          </>
        }
        isBusy={busy}
        onConfirm={confirmClose}
        onOpenChange={setConfirmOpen}
        open={confirmOpen}
        title={t("collect.shiftClose")}
      />
    </div>
  );
}
