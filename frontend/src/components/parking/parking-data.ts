import { businessDayIn } from "@/components/snapshots/day-picker";
import type {
  EdgeParkingReportHour,
  EdgeParkingReportSession,
} from "@/lib/api-types";

/*
 * =============================================================================
 * AVTOTURARGOH HISOBOTINING SOF YORDAMCHILARI (261102).
 *
 * Komponentlar faqat chizadi; nimani chizish kerakligi shu yerda hal
 * qilinadi va u testda React'siz o'lchanadi (`director/chart-data.ts`
 * bilan bir xil qaror).
 *
 * ⛔ YIG'INDI QAYTA HISOBLANMAYDI: pul va sanoq yig'indilari serverdan
 *    (`parking_report.py`). Bu yerda qatorlar faqat SANALADI, SARALANADI,
 *    FILTRLANADI yoki ULUSHGA aylantiriladi.
 * =============================================================================
 */

/* -------------------------------------------------------------------------- */
/* Davlat raqami                                                              */
/* -------------------------------------------------------------------------- */

export type PlateParts = {
  /** Hudud kodi — raqamning chap katagi (`01`). */
  region: string;
  /** Qolgan qism, guruhlarga bo'lingan (`A 123 BC`). */
  body: string;
};

/**
 * Namuna raqam — matnlarga `{example}` bo'lib qo'yiladi. Katalogga yozilmaydi:
 * raqam-harf aralash token kirillga o'girilib buzilardi (`gen-cyrillic`
 * darvozasi), raqam esa har yozuvda lotin.
 */
export const PLATE_EXAMPLE = "01A123BC";

const PRIVATE_PLATE = /^(\d{2})([A-Z])(\d{3})([A-Z]{2})$/u;
const COMPANY_PLATE = /^(\d{2})(\d{3})([A-Z]{3})$/u;

/**
 * O'zbekiston raqamini katakchalarga bo'ladi: `01A123BC` -> `01 | A 123 BC`,
 * yuridik shaxs `01123ABC` -> `01 | 123 ABC`.
 *
 * ⛔ Tanilmagan shakl (xorijiy, diplomatik, qisman o'qilgan) `null` —
 *    raqam BUTUNICHA, bo'linmasdan ko'rsatiladi. Taxminiy bo'lish
 *    o'qilgan matnni o'zgartirib ko'rsatgan bo'lardi.
 */
export function splitUzPlate(plate: string): PlateParts | null {
  const personal = PRIVATE_PLATE.exec(plate);
  if (personal !== null) {
    return {
      region: personal[1],
      body: `${personal[2]} ${personal[3]} ${personal[4]}`,
    };
  }
  const company = COMPANY_PLATE.exec(plate);
  if (company !== null) {
    return { region: company[1], body: `${company[2]} ${company[3]}` };
  }
  return null;
}

/** Kirill klaviaturada terilgan, lotinga o'xshash harflar — raqamlar lotin yozuvida. */
const CYRILLIC_LOOKALIKES: Readonly<Record<string, string>> = {
  А: "A",
  В: "B",
  Е: "E",
  К: "K",
  М: "M",
  Н: "H",
  О: "O",
  Р: "P",
  С: "C",
  Т: "T",
  У: "Y",
  Х: "X",
};

/**
 * Qidiruv matni — agentning `NormalizePlate` i kabi: bo'shliq va
 * chiziqchasiz, katta harf. Kirillcha «А», «В», «С» ... lotinga o'giriladi:
 * kirill sahifasidagi namuna («01А123») va kirill klaviatura ham topsin.
 */
export function normalizePlateQuery(raw: string): string {
  return raw
    .toUpperCase()
    .replace(/[\s\-.]/gu, "")
    .replace(/[АВЕКМНОРСТУХ]/gu, (letter) => CYRILLIC_LOOKALIKES[letter] ?? letter);
}

/* -------------------------------------------------------------------------- */
/* Davomiylik                                                                 */
/* -------------------------------------------------------------------------- */

export type DurationParts = { days: number; hours: number; minutes: number };

/** Daqiqa -> kun / soat / daqiqa. Manfiy yoki son bo'lmagan qiymat nolga tushadi. */
export function durationParts(totalMinutes: number): DurationParts {
  const safe = Number.isFinite(totalMinutes) ? Math.max(0, Math.floor(totalMinutes)) : 0;
  return {
    days: Math.floor(safe / 1440),
    hours: Math.floor((safe % 1440) / 60),
    minutes: safe % 60,
  };
}

/* -------------------------------------------------------------------------- */
/* Ish kuni va soatlar                                                        */
/* -------------------------------------------------------------------------- */

/**
 * Avtoturargoh ish kuni shu soatda boshlanadi (Toshkent): D kuni —
 * [D 06:00, D+1 06:00). Serverdagi `parking_report.DAY_START_HOUR` va agent
 * kassasi bilan AYNI chegara (261103) — uchala ekran bir kunni bir xil sanaydi.
 */
export const PARKING_DAY_START_HOUR = 6;

/**
 * Hozirgi avtoturargoh ish kuni (ISO). 00:00–06:00 orasida — KECHAGI sana.
 *
 * ⛔ `businessDayIn` (kalendar kuni) bilan almashtirilmaydi: tunda server
 *    kalendar «bugun» ni kelajak deb `422 report_period_future` qaytaradi.
 *    Toshkentda yozgi vaqt yo'q — 6 soat ayirish aniq.
 */
export function parkingBusinessDay(timeZone: string, now: Date): string {
  return businessDayIn(
    timeZone,
    new Date(now.getTime() - PARKING_DAY_START_HOUR * 3_600_000),
  );
}

/** Soatning ish kunidagi o'rni: 06 -> 0, 23 -> 17, 00 -> 18, 05 -> 23. */
export function businessHourIndex(hour: number): number {
  return (((hour - PARKING_DAY_START_HOUR) % 24) + 24) % 24;
}

/**
 * Soat qatorlari ish kuni tartibida: 06, 07, …, 23, 00, …, 05.
 *
 * Server soatlarni kalendar tartibida (0..23) beradi — tartib ekranniki.
 * Yetishmagan soat nol qator bo'ladi: o'q hamisha 24 ta katak.
 */
export function hoursFromDayStart(
  hours: readonly EdgeParkingReportHour[],
): EdgeParkingReportHour[] {
  const byHour = new Map(hours.map((row) => [row.hour, row]));
  return Array.from({ length: 24 }, (_, index) => {
    const hour = (PARKING_DAY_START_HOUR + index) % 24;
    return byHour.get(hour) ?? { hour, entries: 0, exits: 0 };
  });
}

/** `8` -> `08:00`. */
export function hourLabel(hour: number): string {
  return `${String(hour % 24).padStart(2, "0")}:00`;
}

/**
 * Eng ko'p kirish bo'lgan soat. Teng bo'lsa ISH KUNIDA ERTAROG'I (06:00 dan
 * sanaladi) — kun boshidagi gavjumlik keyingisidan oldin ko'rinadi. Kirish
 * umuman bo'lmasa `null`.
 */
export function peakHour(
  hours: readonly EdgeParkingReportHour[],
): EdgeParkingReportHour | null {
  const ordered = [...hours].sort(
    (a, b) => businessHourIndex(a.hour) - businessHourIndex(b.hour),
  );
  let best: EdgeParkingReportHour | null = null;
  for (const row of ordered) {
    if (row.entries > 0 && (best === null || row.entries > best.entries)) best = row;
  }
  return best;
}

/* -------------------------------------------------------------------------- */
/* Seans holati                                                               */
/* -------------------------------------------------------------------------- */

export const SESSION_STATUSES = [
  "open",
  "paid",
  "online",
  "free",
  "exempt",
  "manual",
  "other",
] as const;
export type SessionStatus = (typeof SESSION_STATUSES)[number];

const CLOSED_STATUSES: ReadonlySet<string> = new Set([
  "paid",
  "online",
  "free",
  "exempt",
  "manual",
]);

/**
 * Chiqish sababi -> holat. Noma'lum sabab `other` — serverdagi
 * `EXIT_REASONS` bilan bir xil qoida (agentning yangi sababi yo'qolmaydi).
 */
export function reasonStatus(reason: string | null): SessionStatus {
  return reason !== null && CLOSED_STATUSES.has(reason) ? (reason as SessionStatus) : "other";
}

/** Seansning holati: chiqishi yo'q -> `open`; aks holda `closed.reason`. */
export function sessionStatus(session: EdgeParkingReportSession): SessionStatus {
  return session.exited_at === null ? "open" : reasonStatus(session.reason);
}

export const STAY_BUCKET_KEYS = [
  "under_15m",
  "under_1h",
  "under_2h",
  "under_4h",
  "under_8h",
  "over_8h",
] as const;
export type StayBucketKey = (typeof STAY_BUCKET_KEYS)[number];

/** Serverdagi `STAY_BUCKETS` kaliti — katalogda tarjimasi bor guruhmi. */
export function isStayBucketKey(key: string): key is StayBucketKey {
  return (STAY_BUCKET_KEYS as readonly string[]).includes(key);
}

export const PAYMENT_METHODS = ["cash", "terminal", "mixed"] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

export function isPaymentMethod(value: string | null): value is PaymentMethod {
  return value !== null && (PAYMENT_METHODS as readonly string[]).includes(value);
}

/* -------------------------------------------------------------------------- */
/* Jurnal                                                                     */
/* -------------------------------------------------------------------------- */

export const JOURNAL_FILTERS = ["all", "open", "paid", "free", "manual"] as const;
export type JournalFilter = (typeof JOURNAL_FILTERS)[number];

/** Filtr qaysi holatlarni qamraydi. «Bepul» — bepul vaqt VA imtiyozli ro'yxat. */
export function matchesFilter(status: SessionStatus, filter: JournalFilter): boolean {
  switch (filter) {
    case "all":
      return true;
    case "paid":
      return status === "paid" || status === "online";
    case "free":
      return status === "free" || status === "exempt";
    default:
      return status === filter;
  }
}

/** Saralash kaliti — kirgan vaqti, u bo'lmasa chiqqan vaqti (serverdagi `_session_anchor`). */
function anchorOf(session: EdgeParkingReportSession): string {
  return session.entered_at ?? session.exited_at ?? "";
}

/** Eng yangisi oldin. ISO vaqtlar bir xil shaklda — satr solishtiruvi yetadi. */
export function newestFirst(
  sessions: readonly EdgeParkingReportSession[],
): EdgeParkingReportSession[] {
  return [...sessions].sort((a, b) => anchorOf(b).localeCompare(anchorOf(a)));
}

/** Jurnal qatorlari: raqam bo'yicha qidiruv + holat filtri, eng yangisi oldin. */
export function filterJournal(
  sessions: readonly EdgeParkingReportSession[],
  rawQuery: string,
  filter: JournalFilter,
): EdgeParkingReportSession[] {
  const query = normalizePlateQuery(rawQuery);
  return newestFirst(sessions).filter(
    (session) =>
      matchesFilter(sessionStatus(session), filter) &&
      (query === "" || (session.plate ?? "").includes(query)),
  );
}

/** Har filtr tugmasidagi son — holatlar SANALADI, yig'indi emas. */
export function journalCounts(
  sessions: readonly EdgeParkingReportSession[],
): Record<JournalFilter, number> {
  const counts: Record<JournalFilter, number> = { all: 0, open: 0, paid: 0, free: 0, manual: 0 };
  for (const session of sessions) {
    const status = sessionStatus(session);
    for (const filter of JOURNAL_FILTERS) {
      if (matchesFilter(status, filter)) counts[filter] += 1;
    }
  }
  return counts;
}

/**
 * Galereya: KIRISH kadri bor eng yangi seanslar. Chiqishda ro'yxatga
 * olingan seansning kadri chiqish kamerasidan — «kirgan mashinalar»
 * galereyasiga tushmaydi (jurnalda bor).
 */
export function recentWithPhotos(
  sessions: readonly EdgeParkingReportSession[],
  limit: number,
): EdgeParkingReportSession[] {
  return newestFirst(sessions)
    .filter((session) => session.entry_file_id !== null && !session.opened_at_exit)
    .slice(0, limit);
}

/** Davlat raqami bo'la oladimi — agentning `NormalizePlate` qoidasi: kamida bitta son. */
export function looksLikePlate(text: string): boolean {
  return /\d/u.test(text);
}

/* -------------------------------------------------------------------------- */
/* Gorizontal ustunlar                                                        */
/* -------------------------------------------------------------------------- */

/**
 * Ustun eni foizda — eng kattasiga nisbatan. Nol emas qiymat kamida 2%
 * (ko'rinmay qolmasin); nol — nol.
 */
export function barWidth(value: number, max: number): number {
  if (value <= 0 || max <= 0) return 0;
  return Math.max(2, (value / max) * 100);
}

/** Ulush foizda — umumiy son nol bo'lsa `null` (foiz ma'nosiz). */
export function shareOf(value: number, total: number): number | null {
  if (total <= 0) return null;
  return (value / total) * 100;
}
