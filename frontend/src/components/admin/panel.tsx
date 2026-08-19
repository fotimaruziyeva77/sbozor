"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import {
  Banknote,
  CalendarDays,
  Check,
  ScanLine,
  Store,
  TriangleAlert,
  UserRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  attentionItems,
  setupPercent,
  setupSteps,
} from "@/components/admin/setup-view";
import type { Attention, SetupStep } from "@/components/admin/setup-view";
import { PanelTile } from "@/components/panel/tile";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/cn";
import { isAuditAction, isAuditTable } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { useSetupStatusQuery } from "@/lib/market-queries";
import { EMPTY_AUDIT_FILTERS, useAuditQuery, useUsersQuery } from "@/lib/queries";
import { roleLabelKey } from "@/lib/rbac";

/*
 * =============================================================================
 * BOZOR ADMINI PANELI — Stitch «Admin paneli» maketining tuzilmasi.
 *
 * ⛔⛔ NEGA ALOHIDA PANEL, DIREKTORNIKI EMAS.
 *
 *     Bugungacha bozor admini `/dashboard` da DIREKTOR panelini
 *     ko'rardi (ikkalasida ham `report_view` bor). Lekin ular BOSHQA
 *     ikki savolga javob beradi:
 *
 *       direktor      -> «pul to'liq yig'ilyaptimi?»   (hisobdorlik)
 *       bozor admini  -> «bozorim ishlashga tayyormi?» (sozlash)
 *
 *     Bitta ekranda ikkalasini ko'rsatish har ikkisini ham
 *     susaytiradi. Stitch maketida ham admin panelida PUL YO'Q — u
 *     sozlash, reestr, xodim va o'zgarishlar haqida. Bu to'g'ri
 *     qaror va biz uni AYNAN ko'chiramiz.
 *
 *     ⚠ Bozor admini pulni yo'qotmaydi: `report_view` unda qoladi va
 *       `/reports` menyuda turadi.
 *
 * ⛔⛔ TARTIB IERARXIYA BO'YICHA VA U TASODIFIY EMAS:
 *
 *       1. SOZLASH      — «tayyormanmi?» Bosh javob, butun qator.
 *       2. DIQQAT       — «nima buzuq?» FAQAT haqiqiy bandlar.
 *       3. REESTR       — «nimam bor?» To'rtta joyga eshik.
 *       4. XODIM + JURNAL — «kim ishlayapti, kim nima o'zgartirdi?»
 *
 *     Yuqoridan pastga: holat -> muammo -> mulk -> odam. Bozor admini
 *     ertalab ekranni ochganda birinchi savoli aynan birinchisi.
 *
 * ⛔ RANGLAR STITCHDAN (foydalanuvchi qarori, 260819): yashil zumrad
 *    (`oklch(… 162)`), sariq amber (`oklch(… 70)`). Ular BIZNING
 *    semantik tokenlarimiz — ya'ni «bajarildi» va «diqqat» ma'nosi
 *    butun mahsulotda bir xil qoladi, faqat ohang Stitchnikiga keldi.
 *
 * ⛔ RANG YOLG'IZ SIGNAL EMAS: har holat ikonka VA matn bilan ham
 *    keladi. Rang ko'rmaydigan odam ekranni to'liq o'qiy oladi.
 * =============================================================================
 */

/** Sozlash qadamlarining yorlig'i — `setup-view.ts` dagi `key` bo'yicha. */
const STEP_LABEL: Record<SetupStep["key"], string> = {
  zones: "Zonalar",
  stalls: "Rastalar",
  categories: "Toifalar",
  tariffs: "Toifa tariflari",
  vendors: "Sotuvchilar",
  calendar: "Ish kunlari",
  cameras: "Kameralar",
};

/**
 * Diqqat bandlarining matni — sarlavha, sabab va amal.
 *
 * ⛔ HAR BANDDA «NIMA BO'LADI» QATORI BOR va u eng muhim qism:
 *    «16 rasta» o'zi hech narsa demaydi, «bu rastalarga patta
 *    hisoblanmaydi» esa odamni harakatga keltiradi. Muammoni sanash
 *    oson, OQIBATINI aytish esa mahsulotning ishi.
 */
const ATTENTION_TEXT: Record<
  Attention["key"],
  { title: string; unit: string | null; why: string; action: string }
> = {
  stallsWithoutCategory: {
    title: "Toifasi belgilanmagan rasta",
    unit: "rasta",
    why: "Bu rastalarga patta hisoblanmaydi — savdo bo'lsa ham pul yozilmaydi.",
    action: "Rastalarni ochish",
  },
  categoriesWithoutTariff: {
    title: "Narxi qo'yilmagan toifa",
    unit: "toifa",
    why: "Bu toifadagi rastalarga kunlik patta summasi yo'q.",
    action: "Tariflarni ochish",
  },
  noCalendar: {
    title: "Ish kunlari belgilanmagan",
    unit: null,
    why: "Qaysi kunlar patta hisoblanishi noma'lum — kunlik hisob yurmaydi.",
    action: "Kalendarni ochish",
  },
  noCameras: {
    title: "Kamera ulanmagan",
    unit: null,
    why: "Bandlik o'lchanmaydi — «band, lekin to'lovsiz» rastalar ko'rinmaydi.",
    action: "Kameralarni ochish",
  },
};

/** Reestr kataklarining ikonkalari — Stitch `Material Symbols` mosligi. */
const REGISTRY_ICON: Record<string, LucideIcon> = {
  vendors: UserRound,
  stalls: Store,
  tariffs: Banknote,
  calendar: CalendarDays,
};

export function AdminPanel({
  marketId,
  marketName,
  roleLabel,
}: {
  marketId: string;
  marketName: string;
  roleLabel: string;
}) {
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const todayIso = businessDayIn(timeZone, now);

  const setup = useSetupStatusQuery(marketId);
  const users = useUsersQuery();
  /*
   * ⛔ Jurnal FAQAT oxirgi beshta yozuv uchun so'raladi. Panel — audit
   *    sahifasining nusxasi EMAS, u faqat «yaqinda nima o'zgardi»
   *    savoliga javob beradi va to'liq javob uchun havola qo'yadi.
   */
  const audit = useAuditQuery(EMPTY_AUDIT_FILTERS);

  const status = setup.data ?? null;
  const steps = status === null ? [] : setupSteps(status);
  const percent = status === null ? null : setupPercent(steps);
  const attention = status === null ? [] : attentionItems(status);


  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="dir-eyebrow">
            {marketName} · {roleLabel}
          </div>
          <h1 className="dir-title">Admin paneli</h1>
          {/*
           * ⛔ `formatBusinessDay` — XOM `Intl` EMAS. O'zbek lotin
           *    yozuvi uchun brauzer ICU'sida oy nomlari yo'q va u
           *    «2026 M08 19» beradi (jonli o'lchandi). Helper faqat
           *    shu til uchun jadval bilan yozadi; direktor paneli ham
           *    AYNAN shuni ishlatadi.
           */}
          <p className="dir-tile-sub">
            {formatBusinessDay(format, todayIso, locale)}
            {" · Toshkent vaqti · yangilandi "}
            {format.dateTime(now, { timeStyle: "short" })}
          </p>
        </div>
      </header>

      <div className="dir-grid">
        {/* ---------------------------------------------------------------
         * 1. SOZLASH — bosh javob, butun qatorni egallaydi.
         * ------------------------------------------------------------ */}
        <PanelTile
          action="Ustani ochish"
          className="dir-tile-hero"
          href="/markets/setup"
          label="Bozor sozlanishi"
          step={0}
          sub="Yetti qadam — bozor ishlashga tayyor bo'lishi uchun"
        >
          {setup.isPending ? (
            <Skeleton className="h-32 rounded-lg" />
          ) : percent === null ? (
            <p className="dir-tile-note">
              Sozlash holati o&apos;qilmadi — sahifani yangilab ko&apos;ring.
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-6">
              <SetupRing percent={percent} />

              <ul className="grid min-w-0 flex-1 grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
                {steps.map((item) => (
                  <li key={item.key}>
                    <Link
                      className="flex items-center gap-2.5 rounded-sm py-1 text-sm text-text hover:text-accent-text"
                      href={item.href}
                    >
                      <StepMark done={item.done} />
                      <span className="min-w-0 flex-1 truncate">
                        {STEP_LABEL[item.key]}
                      </span>
                      <span className="shrink-0 font-mono text-xs text-text-muted tabular-nums">
                        {stepCount(item, format, locale)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </PanelTile>

        {/* ---------------------------------------------------------------
         * 2. DIQQAT TALAB QILADI — bo'sh bo'lsa BUTUN BO'LIM chizilmaydi.
         *
         * ⛔ «Muammo yo'q» degan bo'sh karta CHIZILMAYDI: u ekranda joy
         *    egallab, ko'zni har kuni bo'sh javobga o'rgatardi. Bo'lim
         *    faqat aytadigan gapi bo'lganda paydo bo'ladi — shuning
         *    uchun paydo bo'lgani O'ZI signal.
         * ------------------------------------------------------------ */}
        {attention.length > 0 ? (
          <>
            <p className="dir-group-span dir-group-label">Diqqat talab qiladi</p>
            {attention.map((item, index) => (
              <AttentionCard item={item} key={item.key} step={index + 1} />
            ))}
          </>
        ) : null}

        {/* ---------------------------------------------------------------
         * 3. REESTR — to'rtta joyga eshik.
         * ------------------------------------------------------------ */}
        <p className="dir-group-span dir-group-label">Reestr</p>

        <RegistryTile
          action="Ro'yxatni ochish"
          count={status?.vendors ?? null}
          href="/vendors"
          icon="vendors"
          label="Sotuvchilar"
          step={1}
          sub="Bozorda ro'yxatdan o'tgan"
          unit="nafar"
        />
        <RegistryTile
          action="Rastalarni ochish"
          count={status?.stalls ?? null}
          href="/stalls"
          icon="stalls"
          label="Rastalar"
          step={2}
          sub={
            status === null
              ? "Zonalar bo'yicha"
              : `${formatAmount(format, status.zones, locale)} zonada`
          }
          unit="ta"
        />
        <RegistryTile
          action="Tariflarni ochish"
          count={status?.categories_total ?? null}
          href="/tariffs"
          icon="tariffs"
          label="Tariflar"
          step={3}
          sub={
            status === null
              ? "Toifa bo'yicha narx"
              : `${formatAmount(format, status.tariffs_covered, locale)} toifada narx bor`
          }
          unit="toifa"
        />
        <RegistryTile
          action="Kalendarni ochish"
          count={null}
          href="/calendar"
          icon="calendar"
          label="Ish kunlari"
          step={4}
          stateText={
            status === null
              ? null
              : status.calendar_configured
                ? "Haftalik jadval belgilangan"
                : "Hali belgilanmagan"
          }
          sub="Patta qaysi kunlarda hisoblanadi"
          unit=""
        />
      </div>

      {/* -----------------------------------------------------------------
       * 4. XODIMLAR + OXIRGI O'ZGARISHLAR — yonma-yon, teng og'irlikda.
       *
       * ⛔ Ular BIR QATORDA turishi ma'noli: «kim ishlaydi» va «kim nima
       *    qildi» bitta savolning ikki yarmi. Ajratilsa, xodim ro'yxati
       *    quruq ma'lumotnomaga aylanardi.
       * -------------------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <StaffCard
          isPending={users.isPending}
          rows={users.data?.items ?? null}
        />
        <ChangesCard
          isPending={audit.isPending}
          rows={audit.data?.pages[0]?.items ?? null}
        />
      </div>
    </div>
  );
}

/* ==========================================================================
 * Sozlash halqasi — direktor panelidagi bosh halqa bilan AYNAN bir
 * matematikada (`dasharray = 2πr`, `dashoffset = dasharray × (1 − ulush)`).
 * ======================================================================= */
function SetupRing({ percent }: { percent: number }) {
  const RADIUS = 44;
  const dash = 2 * Math.PI * RADIUS;
  const offset = dash * (1 - percent / 100);
  const complete = percent === 100;

  return (
    <div className="relative size-32 shrink-0">
      <svg className="size-full -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          fill="none"
          r={RADIUS}
          stroke="var(--color-border)"
          strokeWidth="12"
        />
        <circle
          cx="50"
          cy="50"
          fill="none"
          r={RADIUS}
          stroke={
            complete ? "var(--color-success)" : "var(--color-warning)"
          }
          strokeDasharray={dash.toFixed(2)}
          strokeDashoffset={offset.toFixed(2)}
          strokeLinecap="round"
          strokeWidth="12"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {/* ⛔ `dir-tile-value-sm` (30px mono) — direktor panelidagi
               bandlik donuti bilan AYNAN bir shkalada. O'z o'lchamimni
               yozsam (`text-3xl`), ikki panel bir xil ko'rinadigan
               halqani boshqa kattalikda chizardi. */}
        <span className="dir-tile-value-sm">{percent}%</span>
        <span className="dir-tile-unit">tayyor</span>
      </div>
    </div>
  );
}

/** Qadam belgisi — ✓ yoki ⚠. Rang YOLG'IZ signal emas, shakl ham farq qiladi. */
function StepMark({ done }: { done: boolean }) {
  const Icon = done ? Check : TriangleAlert;
  return (
    <span
      className={cn(
        "flex size-5 shrink-0 items-center justify-center rounded-full",
        done
          ? "bg-success/15 text-success-text"
          : "bg-warning/20 text-warning-text",
      )}
    >
      <Icon aria-hidden="true" className="size-3" />
      <span className="sr-only">{done ? "bajarildi" : "tugallanmagan"}</span>
    </span>
  );
}

/**
 * `6 / 6`, `284` yoki kalendar uchun «bor»/«yo'q».
 *
 * ⛔ Formatlovchi TASHQARIDAN: raqam guruhlash uz-Latn da INGICHKA
 *    bo'sh joy bilan (24 180 000), boshqa tillarda esa `Intl` bilan
 *    qilinadi (`formatAmount`). Bu yerda o'z formatimni yozsam,
 *    panel qolgan ekranlardan boshqacha raqam ko'rsatardi.
 */
function stepCount(
  step: SetupStep,
  format: ReturnType<typeof useFormatter>,
  locale: string,
): string {
  if (step.count === null) return step.done ? "bor" : "yo'q";
  if (step.total === null) return formatAmount(format, step.count, locale);
  return `${formatAmount(format, step.count, locale)} / ${formatAmount(format, step.total, locale)}`;
}

/* ==========================================================================
 * Diqqat katagi — chap chekkasida ohang chizig'i (Stitch naqshi).
 * ======================================================================= */
function AttentionCard({ item, step }: { item: Attention; step: number }) {
  const format = useFormatter();
  const locale = useLocale();
  const text = ATTENTION_TEXT[item.key];
  const danger = item.tone === "danger";

  return (
    <Link
      className="dir-tile-link"
      href={item.href}
      style={{ "--i": step } as never}
    >
      <Card
        className={cn(
          "dir-tile border-l-3",
          danger ? "border-l-danger" : "border-l-warning",
        )}
      >
        <CardHeader className="dir-tile-head">
          <div className="flex items-start justify-between gap-3">
            <p className="dir-tile-label">{text.title}</p>
            <TriangleAlert
              aria-hidden="true"
              className={cn(
                "size-4 shrink-0",
                danger ? "text-danger-text" : "text-warning-text",
              )}
            />
          </div>
        </CardHeader>

        <CardContent className="dir-tile-body">
          <div className="flex flex-col gap-3">
            {item.count === null ? (
              <Badge tone={danger ? "danger" : "warning"}>Sozlanmagan</Badge>
            ) : (
              <p className="dir-tile-value">
                {formatAmount(format, item.count, locale)}
                {text.unit === null ? null : (
                  <span className="dir-tile-unit"> {text.unit}</span>
                )}
              </p>
            )}

            <p className="dir-tile-note">{text.why}</p>

            <div className="dir-tile-foot">
              <span className="dir-tile-action">{text.action} →</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

/* ==========================================================================
 * Reestr katagi — `PanelTile` ning yupqa o'ramasi.
 * ======================================================================= */
function RegistryTile({
  action,
  count,
  href,
  icon,
  label,
  step,
  stateText = null,
  sub,
  unit,
}: {
  action: string;
  count: number | null;
  href: "/vendors" | "/stalls" | "/tariffs" | "/calendar";
  icon: keyof typeof REGISTRY_ICON;
  label: string;
  step: number;
  stateText?: string | null;
  sub: string;
  unit: string;
}) {
  const format = useFormatter();
  const locale = useLocale();
  const Icon = REGISTRY_ICON[icon] ?? ScanLine;

  return (
    <PanelTile
      action={action}
      href={href}
      icon={Icon}
      label={label}
      step={step}
      sub={sub}
    >
      <div className="flex items-center gap-3">
        {/*
         * ⛔ O'LCHANMAGAN QIYMAT O'RNIGA NOL YOZILMAYDI (T-05-04):
         *    «bozorda 0 ta sotuvchi bor» va «sotuvchilar sonini
         *    bilmayman» butunlay boshqa ikki gap.
         */}
        {count === null && stateText === null ? (
          <p className="dir-tile-value text-text-muted">—</p>
        ) : count === null ? (
          <p className="text-sm text-text">{stateText}</p>
        ) : (
          <p className="dir-tile-value">
            {formatAmount(format, count, locale)}
            <span className="dir-tile-unit"> {unit}</span>
          </p>
        )}
      </div>
    </PanelTile>
  );
}

/* ==========================================================================
 * Xodimlar — qisqa ro'yxat, to'liq boshqaruv `/users` da.
 * ======================================================================= */
const STAFF_LIMIT = 5;

function StaffCard({
  isPending,
  rows,
}: {
  isPending: boolean;
  rows: readonly {
    id: string;
    phone: string;
    full_name: string | null;
    roles: readonly string[];
    is_active: boolean;
  }[] | null;
}) {
  const format = useFormatter();
  const locale = useLocale();
  const shown = rows?.slice(0, STAFF_LIMIT) ?? [];

  return (
    <Card className="flex flex-col gap-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="dir-tile-label">Xodimlar</p>
        <Link className="dir-tile-action" href="/users">
          Barchasi →
        </Link>
      </div>

      {isPending ? (
        <Skeleton className="h-32 rounded-lg" />
      ) : rows === null ? (
        <p className="dir-tile-note">Xodimlar ro&apos;yxati o&apos;qilmadi.</p>
      ) : shown.length === 0 ? (
        <p className="dir-tile-note">Hali xodim qo&apos;shilmagan.</p>
      ) : (
        <ul className="flex flex-col">
          {shown.map((row) => (
            <li
              className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-b-0"
              key={row.id}
            >
              {/* ⛔ Ism `null` bo'lishi mumkin — o'shanda TELEFON yoziladi,
                     bo'sh katak emas: xodimni tanib bo'lmaydigan qator
                     ro'yxatni foydasiz qiladi. */}
              <span className="min-w-0 flex-1 truncate text-sm text-text">
                {row.full_name ?? row.phone}
              </span>
              <span className="shrink-0 text-xs text-text-muted">
                {row.roles
                  .map((role) => roleLabelKey(role))
                  .filter((key): key is NonNullable<typeof key> => key !== null)
                  .map((key) => ROLE_SHORT[key])
                  .join(", ")}
              </span>
              <Badge tone={row.is_active ? "success" : "danger"}>
                {row.is_active ? "Faol" : "Bloklangan"}
              </Badge>
            </li>
          ))}
        </ul>
      )}

      {rows !== null && rows.length > STAFF_LIMIT ? (
        <p className="dir-tile-note">
          Yana {formatAmount(format, rows.length - STAFF_LIMIT, locale)} xodim
        </p>
      ) : null}
    </Card>
  );
}

/** Rol nomlarining QISQA shakli — jadval qatoriga sig'ishi uchun. */
const ROLE_SHORT: Record<string, string> = {
  platformAdmin: "Platforma admini",
  director: "Direktor",
  marketAdmin: "Bozor admini",
  cashier: "Kassir",
  inspector: "Nazoratchi",
};

/* ==========================================================================
 * Oxirgi o'zgarishlar — audit jurnalining boshi.
 * ======================================================================= */
const CHANGES_LIMIT = 5;

function ChangesCard({
  isPending,
  rows,
}: {
  isPending: boolean;
  rows: readonly {
    id: number;
    action: string;
    table_name: string;
    actor_label: string | null;
    at: string;
  }[] | null;
}) {
  const format = useFormatter();
  /*
   * ⛔ Yorliqlar `/audit` SAHIFASI BILAN AYNAN BIR MANBADAN
   *    (`audit.actions.*` / `audit.tables.*`). O'z ro'yxatimni yozsam,
   *    panelda «tarif o'zgardi», jurnalda esa boshqacha yozilib, bir
   *    voqea ikki xil atalardi.
   */
  const tActions = useTranslations("audit.actions");
  const tTables = useTranslations("audit.tables");
  const shown = rows?.slice(0, CHANGES_LIMIT) ?? [];

  return (
    <Card className="flex flex-col gap-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="dir-tile-label">Oxirgi o&apos;zgarishlar</p>
        <Link className="dir-tile-action" href="/audit">
          To&apos;liq jurnal →
        </Link>
      </div>

      {isPending ? (
        <Skeleton className="h-32 rounded-lg" />
      ) : rows === null ? (
        <p className="dir-tile-note">Jurnal o&apos;qilmadi.</p>
      ) : shown.length === 0 ? (
        <p className="dir-tile-note">Hali o&apos;zgarish yozilmagan.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {shown.map((row) => (
            <li className="flex items-start gap-3" key={row.id}>
              <span
                aria-hidden="true"
                className="mt-1.5 size-1.5 shrink-0 rounded-full bg-accent"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-text">
                  {isAuditTable(row.table_name)
                    ? tTables(row.table_name)
                    : row.table_name}
                  {" · "}
                  {isAuditAction(row.action)
                    ? tActions(row.action)
                    : row.action}
                </p>
                <p className="text-xs text-text-muted">
                  {format.dateTime(new Date(row.at), { timeStyle: "short" })}
                  {row.actor_label === null ? null : ` · ${row.actor_label}`}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
