import type { CaptureDaySummary, MapZone, ReceivablesReportRow } from "@/lib/api-types";
import type { MapDayRow, MapDayState } from "@/lib/map-day-queries";
import { groupDigits } from "@/lib/format-number";

/*
 * =============================================================================
 * PANEL GRAFIKLARINING SOF HISOBLARI (261016).
 *
 * Komponentlar faqat chizadi; nimani chizish kerakligi shu yerda hal
 * qilinadi va u testda React'siz o'lchanadi.
 *
 * ⛔ PUL QAYTA HISOBLANMAYDI: bu yerda serverning qiymatlari faqat
 *    SANALADI, SARALANADI yoki ULUSHGA aylantiriladi. Ayirma (`diff`),
 *    qarz qoldig'i va yig'indilar — serverniki.
 * =============================================================================
 */

/* -------------------------------------------------------------------------- */
/* Ixcham summa — o'q yorliqlari uchun                                        */
/* -------------------------------------------------------------------------- */

export type CompactUnits = {
  thousand: string;
  million: string;
  billion: string;
};

/**
 * `1 250 000` -> `1,3 mln` — FAQAT o'q va ustun uchidagi yorliq uchun.
 *
 * ⛔ `Intl` ning `compact` yozuvi ISHLATILMAYDI: brauzer ICU'sida o'zbek
 *    tili uchun qisqartmalar yo'q va u jimgina `1.3M` chizadi (nisbiy
 *    vaqtdagi aynan o'sha bo'shliq). Birliklar katalogdan keladi.
 *
 * ⛔ Kasr ajratgichi VERGUL — o'zbek va rus yozuvida shunday. Aniq summa
 *    baribir tooltip va jadvalda TO'LIQ yoziladi; bu yorliq taxminiy.
 */
export function compactSoum(value: number, units: CompactUnits): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : "";

  const scaled = (divisor: number, unit: string): string => {
    const raw = abs / divisor;
    /* 10 dan katta qiymatda kasr shovqin — «12,4 mln» emas, «12 mln». */
    const text =
      raw >= 10 ? String(Math.round(raw)) : raw.toFixed(1).replace(/\.0$/, "");
    return `${sign}${text.replace(".", ",")} ${unit}`;
  };

  if (abs >= 1_000_000_000) return scaled(1_000_000_000, units.billion);
  if (abs >= 1_000_000) return scaled(1_000_000, units.million);
  if (abs >= 1_000) return `${sign}${groupDigits(Math.round(abs / 1_000))} ${units.thousand}`;
  return groupDigits(value);
}

/* -------------------------------------------------------------------------- */
/* O'q shifti — «chiroyli qadam»                                              */
/* -------------------------------------------------------------------------- */

/**
 * Shiftni «chiroyli qadam» ga keltiradi: `max / lines` BUTUN bo'ladi.
 *
 * ⛔ Qadam faqat 1 · 2 · 3 · 4 · 5 · 6 · 8 · 10 ×10ⁿ dan tanlanadi — odam
 *    o'qiydigan qadamlar shular.
 *
 * ⛔ Bo'sh ma'lumotda (`peak <= 0`) shift `lines` ga teng bo'ladi,
 *    ya'ni o'q 0 · 1 · 2 · 3 bo'lib chiqadi va nolga bo'linish yo'q.
 */
export function niceMax(peak: number, lines: number): number {
  if (!Number.isFinite(peak) || peak <= 0) return lines;

  const rough = peak / lines;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;

  /*
   * ⛔ ZINAPOYA {1,2,3,4,5,6,8,10} — {1,2,5,10} DAN QAYTA TANLANDI.
   *    Dag'al zinapoyada 16 000 lik ustun uchun shift 30 000 bo'lardi —
   *    diagrammaning YARMI bo'sh qolardi. 2.5 va 7.5 yo'q: kichik
   *    oraliqda ular «2.5 so'm» degan ma'nosiz yorliq berardi.
   */
  const ladder = [1, 2, 3, 4, 5, 6, 8, 10];
  const chosen = ladder.find((value) => normalized <= value) ?? 10;

  /* ⛔ Qadam kamida 1: juda kichik ustunda o'qda kasr son yozilmasin. */
  const step = Math.max(1, Math.round(chosen * magnitude));

  return step * lines;
}

/* -------------------------------------------------------------------------- */
/* Bugungi rasta holati                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Grafikdagi segmentlar TARTIBI — ma'no bo'yicha, kattalik bo'yicha emas.
 *
 * ⛔ `mismatch` (sariq) `paid` (yashil) va `due` (qizil) ORASIDA: rang
 *    ko'rligida yashil va qizil bir-biriga yaqin ko'rinadi va ular
 *    yonma-yon tursa farqni faqat oraliq va ikonka ko'tarib turardi.
 *
 * ⛔ Tartib BARQAROR: holat yo'qolsa qolganlari o'z rangini saqlaydi
 *    (rang segmentning o'rniga emas, holatga bog'langan).
 */
export const STALL_DAY_ORDER: readonly MapDayState[] = [
  "paid",
  "mismatch",
  "due",
  "fair",
  "free",
  "no_billing",
];

export type StallDayCounts = Record<MapDayState, number>;

export function emptyStallDayCounts(): StallDayCounts {
  return { paid: 0, mismatch: 0, due: 0, fair: 0, free: 0, no_billing: 0 };
}

/** Holatlar sanog'i — har qator BIR MARTA sanaladi. */
export function countStallDays(rows: readonly MapDayRow[]): StallDayCounts {
  const counts = emptyStallDayCounts();
  for (const row of rows) counts[row.state] += 1;
  return counts;
}

/**
 * Bugun patta KUTILGAN rastalar: to'langan + to'lanmagan + nomuvofiq.
 *
 * ⛔ Yarmarka, sotuvchisiz va «bugun hisob yo'q» MAXRAJGA KIRMAYDI: ular
 *    to'lashi kerak emas va maxrajda turganda «18 / 26» bozorni 8 ta
 *    qarzdor bordek ko'rsatardi.
 */
export function expectedStalls(counts: StallDayCounts): number {
  return counts.paid + counts.due + counts.mismatch;
}

export type ZoneDayRow = {
  id: string;
  name: string;
  counts: StallDayCounts;
};

/**
 * Zona kesimi — `GET /stalls/map` zonalari × `GET /billing/map` holatlari.
 *
 * ⛔ Holati kelmagan katak (qatlamda yo'q) SANALMAYDI: unga holat
 *    to'qish xaritadagi «yolg'on qizil» bilan bir xil xato bo'lardi.
 * ⛔ Bironta holati yo'q zona ro'yxatga chiqmaydi.
 */
export function zoneDayRows(
  zones: readonly MapZone[],
  byStallId: ReadonlyMap<string, MapDayRow>,
): ZoneDayRow[] {
  const result: ZoneDayRow[] = [];
  for (const zone of zones) {
    const counts = emptyStallDayCounts();
    let seen = 0;
    for (const cell of zone.cells) {
      const row = byStallId.get(cell.id);
      if (row === undefined) continue;
      counts[row.state] += 1;
      seen += 1;
    }
    if (seen > 0) result.push({ id: zone.id, name: zone.name, counts });
  }
  return result;
}

/* -------------------------------------------------------------------------- */
/* Qarzdorlar                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * Eng katta qarzdorlar — faqat MUSBAT qoldiq.
 *
 * ⛔ Manfiy qoldiq — AVANS (`report_repo` `<> 0` filtri), u qarzdorlar
 *    grafigiga tushsa ortiqcha to'lagan sotuvchi qarzdor bo'lib ko'rinardi.
 * ⛔ Teng qarzda tartib sotuvchi identifikatori bo'yicha — har yangilanishda
 *    qatorlar o'rin almashib «sakramasin».
 */
export function topDebtors(
  rows: readonly ReceivablesReportRow[],
  limit: number,
): ReceivablesReportRow[] {
  /* `filter` yangi massiv qaytaradi — `sort` serverning ro'yxatiga tegmaydi. */
  return rows
    .filter((row) => row.outstanding_soum > 0)
    .sort(
      (a, b) =>
        b.outstanding_soum - a.outstanding_soum ||
        (a.vendor_id ?? "").localeCompare(b.vendor_id ?? ""),
    )
    .slice(0, limit);
}

/* -------------------------------------------------------------------------- */
/* To'lov turlari                                                             */
/* -------------------------------------------------------------------------- */

export type MethodShares = { cash: number; terminal: number; payme: number };

/**
 * Naqd va terminal ULUSHI (foizda).
 *
 * ⛔ `null` — ulush CHIZILMAYDI:
 *    · davrda pul yo'q (0 / 0);
 *    · qismlardan biri MANFIY (o'tgan kun to'lovining bugungi stornosi) —
 *      manfiy bo'lakli «100%» ma'nosiz va u ekranda yolg'on nisbat berardi.
 */
export function methodShares(
  cash: number,
  terminal: number,
  payme = 0,
): MethodShares | null {
  if (cash < 0 || terminal < 0 || payme < 0) return null;
  const total = cash + terminal + payme;
  if (total <= 0) return null;
  return {
    cash: (cash / total) * 100,
    terminal: (terminal / total) * 100,
    payme: (payme / total) * 100,
  };
}

/* -------------------------------------------------------------------------- */
/* Kamera kadrlari                                                            */
/* -------------------------------------------------------------------------- */

export type CaptureBuckets = {
  /** Yaroqli kadr. */
  ok: number;
  /** Olingan, lekin yaroqsiz: qorong'i · bo'sh · buzilgan. */
  poor: number;
  /** Olinmadi: xato · o'tkazib yuborilgan. */
  lost: number;
  /** Hali navbatda (faqat bugun). */
  pending: number;
  planned: number;
};

/**
 * Kun xulosasidan to'rt guruh — hisoblagichlar SERVERDAN, bu yerda faqat
 * GURUHLANADI.
 *
 * ⛔ `pending` — rejadan qolgan qism va u HECH QACHON manfiy emas:
 *    server hisoblagichlari bir lahzada ko'payib ketsa ham ustun
 *    rejadan oshib ketgandek chizilmaydi.
 */
export function captureBuckets(summary: CaptureDaySummary): CaptureBuckets {
  const ok = summary.ok;
  const poor = summary.dark + summary.blank + summary.corrupt;
  const lost = summary.failed + summary.missed;
  const pending = Math.max(0, summary.planned - ok - poor - lost);
  return { ok, poor, lost, pending, planned: summary.planned };
}
