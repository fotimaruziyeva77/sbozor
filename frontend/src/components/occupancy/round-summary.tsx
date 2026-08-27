"use client";

import { useFormatter, useTranslations } from "next-intl";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { AuditRound } from "@/lib/api-types";

/*
 * =============================================================================
 * ZONA (C) — NAMUNA HOLATI (§11.6). O'LCHOVNING O'ZINI KO'RSATADI.
 *
 * ⛔⛔ NAZORATCHINING ICHKI MOSLIGI (D-16) BU BLOKDA YO'Q — VA BU BLOK
 *     AYNAN UNING «TABIIY UYI» EDI.
 *
 *     UI-SPEC §11.6 ni «Nazoratchining ichki mosligi: 94 % (takroriy 3
 *     banddan)» qatori bilan chizadi va reja ham uni so'raydi. IKKALASI
 *     HAM ESKIRGAN:
 *
 *       05-11 O'LCHADI — takroriy band bugungi sxemada IFODALAB
 *       BO'LMAYDI (`uq_review_assignments_occupancy_event_id` o'sha
 *       hodisaga ikkinchi topshiriqni, `uq_zone_reviews_review_
 *       assignment_id` esa ikkinchi javobni rad etadi). MEXANIZM
 *       QURILMAGAN, ya'ni HAR QANDAY son O'LCHANMAGAN bo'lardi.
 *
 *       05-12 shu sababdan uni javobdan NA SON, NA MAYDON sifatida
 *       chiqarib tashladi.
 *
 *     Shuning uchun bu yerda qator ham, «—» ham, `0` ham, o'chirilgan
 *     qator ham YO'Q. Har uchala shakl ham o'lchanmagan miqdorni
 *     KO'RINADIGAN qilardi va ko'ringan zahoti u o'lchangan deb
 *     o'qilardi (T-05-04).
 *
 * ⛔ SHU QOIDA MEXANIK: `roundCounters()` `null` maydon uchun QATOR
 *    QURMAYDI, `0` uchun esa QURADI. Ya'ni «o'lchanmagan» va «nolga
 *    teng» hech qachon bir xil ko'rinmaydi va bu farq sof funksiya
 *    darajasida sinaladi.
 *
 * ⛔ «NAMUNANI QAYTA TORTISH» TUGMASI YO'Q (D-17, 1-himoya). Uni
 *    qurish «bu turda xato ko'p chiqdi, qaytadan tortaman» yo'lini
 *    ochardi va u aniqlikni yuqoriga siljitardi. Server tomonda ham
 *    bunday marshrut umuman yozilmagan va uning yo'qligi 05-11 ning
 *    OpenAPI skani bilan o'lchanadi.
 *
 * ⛔ URUG'NING O'ZI KO'RSATILMAYDI — u foydalanuvchi uchun ma'nosiz va
 *    uni ko'rsatish «tanlash mumkin» degan taassurot berardi. Ko'rinadigan
 *    iz — tur raqami, tortilgan vaqt va hajm.
 *
 * ⛔ JAVOBSIZLAR SONI NOL BO'LGANDA HAM KO'RSATILADI: javobsiz band
 *    namunadan CHIQMAYDI.
 *
 * ⚠ «TEZ QAROR» SONI BOR, LEKIN CHEGARA NOMLANMAYDI. §12.6 ning
 *   matni «{seconds} soniyadan tez» deydi; chegara (2000 ms) esa
 *   SERVERDA yashaydi (`accuracy_report.is_fast_decision`) va javobda
 *   YO'Q. Uni klientda yozish server konstantasining IKKINCHI nusxasi
 *   bo'lardi — chegara o'zgargan kuni yorliq JIMGINA yolg'on gapirardi
 *   (aynan `min_sample` uchun rad etilgan yo'l). Shuning uchun matn
 *   sonni emas, MA'NONI aytadi.
 *
 * ⚠ `role="status"`: bu HISOBOT.
 * =============================================================================
 */

/** Bitta qator — yorliq kaliti va O'LCHANGAN son. */
export type RoundCounter = {
  labelKey:
    | "occupancy.answered"
    | "occupancy.unanswered"
    | "occupancy.unclearCount"
    | "occupancy.fastDecisions";
  value: number;
};

/**
 * Turning hisoblagichlari — SOF FUNKSIYA (§S-13).
 *
 * ⛔ `null` -> QATOR YO'Q. `0` -> QATOR BOR.
 *
 *    Bu ikki holat butunlay boshqa da'vo: `0` — NATIJA («hammasiga
 *    javob berildi»), `null` — O'LCHOVNING YO'QLIGI. `?? 0` yozish eng
 *    tabiiy qisqartma va u aynan o'lchanmagan miqdorni nol deb e'lon
 *    qilardi.
 *
 * ⚠ TARTIB QAT'IY: javob berildi -> javobsiz -> aniq ayta olmadi ->
 *   tez qaror. «Javobsiz» ikkinchi o'rinda, chunki u YO'QOTISH signali.
 */
export function roundCounters(round: AuditRound): RoundCounter[] {
  const rows: { labelKey: RoundCounter["labelKey"]; value: number | null }[] = [
    { labelKey: "occupancy.answered", value: round.answered },
    { labelKey: "occupancy.unanswered", value: round.unanswered },
    { labelKey: "occupancy.unclearCount", value: round.dont_know },
    { labelKey: "occupancy.fastDecisions", value: round.fast_decisions },
  ];

  return rows.filter(
    (row): row is RoundCounter => row.value !== null,
  );
}

export function RoundSummary({ round }: { round: AuditRound }) {
  const t = useTranslations();
  const format = useFormatter();

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">{t("occupancy.roundTitle")}</h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {!round.drawn ? (
          /*
           * ⛔ «TORTILMAGAN» — «HAMMASI BAJARILDI» EMAS (05-12,
           *    4-ochiq band). Ikkalasini bir xil ko'rsatish tortish jobi
           *    butunlay o'lgan kunni MUVAFFAQIYAT bo'lib ko'rsatardi.
           */
          <div className="flex flex-col gap-1" role="status">
            <p className="text-sm">{t("occupancy.roundNotDrawn")}</p>
            <p className="text-xs text-text-muted">
              {t("occupancy.roundNotDrawnHint")}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3" role="status">
            {round.round_no !== null &&
            round.drawn_at !== null &&
            round.sample_size !== null ? (
              <p className="text-sm">
                {t("occupancy.roundLine", {
                  round: round.round_no,
                  size: round.sample_size,
                  time: format.dateTime(new Date(round.drawn_at), {
                    hour: "2-digit",
                    minute: "2-digit",
                  }),
                })}
              </p>
            ) : null}

            <dl className="flex flex-wrap gap-x-6 gap-y-2">
              {roundCounters(round).map((counter) => (
                <div className="flex items-center gap-2" key={counter.labelKey}>
                  <dt className="text-xs text-text-muted">
                    {t(counter.labelKey)}
                  </dt>
                  <dd className="m-0 font-mono text-sm tabular-nums">
                    {counter.value}
                  </dd>
                </div>
              ))}
            </dl>

            <p className="text-xs text-text-muted">
              {t("occupancy.fastDecisionsWhy")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
