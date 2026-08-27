"use client";

import type { KeyboardEventHandler } from "react";
import {
  CheckCircle2,
  CircleSlash,
  Clock,
  FileWarning,
  ImageOff,
  Loader2,
  Minus,
  MoonStar,
  XCircle,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { formatSlotTime } from "@/components/snapshots/schedule-card";
import type { CaptureRun } from "@/lib/api-types";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * BITTA HUJAYRA — TO'QQIZ HOLAT VA C6 NING BIRINCHI DARAJALILIGI (§6.4).
 *
 * ⛔⛔ HUJAYRA HECH QACHON BO'SH RENDER QILINMAYDI.
 *
 *     Bu fazaning butun sababi shu bitta qoidada. ROADMAP SC#2 «kadr
 *     olinmasa, o'tkazib yuborilgan slot jurnalda OCHIQ KO'RINADI»
 *     deydi — va «jurnalga yozilgan» bilan «jurnalda ochiq ko'rinadi»
 *     BOSHQA talab. Birinchisini backend bajardi; ikkinchisini buzish
 *     uchun esa bitta begunoh ko'rinadigan qadam yetadi: yo'q kadr
 *     uchun hech nima chizmaslik.
 *
 *     Bo'shliq «bu yerda ko'radigan narsa yo'q» deydi. Yo'q kadr esa
 *     bo'shliq emas, HODISA: u bajarilgan kadr bilan AYNI joyni
 *     egallaydi (44×44), o'z ikonkasiga, o'z so'ziga va o'z izohiga ega
 *     bo'ladi. Bu 3-fazadagi «uch hisoblagich» muammosining aynan
 *     takrori — u yerda ham yechim nol hisoblagichni MAJBURIY ko'rsatish
 *     edi.
 *
 * ⛔⛔ `CircleSlash` (C6) va `XCircle` (C5) — ATAYIN TURLI IKONKA.
 *
 *     `missed` = BIZNING TIZIMIMIZ ishlamadi (worker o'lgan, tik
 *     to'xtagan, reja bajarilmagan). `failed` = NVR JAVOB BERMADI
 *     (tarmoq, parol, oqim chegarasi). Ular operatsion jihatdan
 *     BUTUNLAY boshqa: birinchisida admin hech narsa qila olmaydi va
 *     platforma jamoasiga xabar beradi, ikkinchisida esa kabelni yoki
 *     parolni o'zi tekshiradi. Bir xil ikonka bu ikki yo'lni bir
 *     ko'rinishga yig'ib, dala diagnostikasini o'ldirardi.
 *
 * ⚠ UCH MUSTAQIL KANAL (§9.4, WCAG 1.4.1): RANG (tone) + SHAKL (ikonka)
 *   + C6/C9 uchun PUNKTIR CHEGARA. Punktir — «bu yerda nimadir bo'lishi
 *   kerak edi» ning universal shakli va u rangni ham, ikonkani ham
 *   ko'rmaydigan foydalanuvchiga ishlaydi.
 *
 * ⚠ HUJAYRADA MATN YO'Q va bu O'LCHANGAN qaror [M-4]: `Buzuq` (5 belgi)
 *   rus tilida `Повреждён` (9 belgi) — 1,80× nisbat va u 44px hujayraga
 *   SIG'MAYDI. So'z uchta joyda yashaydi: doimiy legendada (§6.5),
 *   hujayraning `aria-label` va `title` atributlarida hamda DL-3
 *   sarlavhasida. Hujayrani kengaytirish (7 × 90px = 630px) mobil
 *   aylantirishni ikki barobar oshirardi; qisqartma esa tarjima
 *   qilinmaydigan jargon tug'dirardi.
 *
 * ⚠ 44×44 KICHRAYTIRILMAYDI: hujayra bosiladi (DL-3 ni ochadi), ya'ni u
 *   barmoq nishoni va WCAG 2.5.8 unga qo'llanadi.
 * =============================================================================
 */

/** To'qqizta hujayra holati — §6.4 jadvalining C1…C9 qatorlari. */
export type CaptureCellState =
  | "ok"
  | "dark"
  | "blank"
  | "corrupt"
  | "failed"
  | "missed"
  | "pending"
  | "running"
  | "skipped";

type CellView = {
  Icon: typeof CheckCircle2;
  /** Chegara uslubi — C6 va C9 uchun UCHINCHI, rangsiz kanal. */
  dashed: boolean;
  labelKey:
    | "snapshots.cell.ok"
    | "snapshots.cell.dark"
    | "snapshots.cell.blank"
    | "snapshots.cell.corrupt"
    | "snapshots.cell.failed"
    | "snapshots.cell.missed"
    | "snapshots.cell.pending"
    | "snapshots.cell.running"
    | "snapshots.cell.skipped";
  /** Tint + matn rangi. ⚠ Ogohlantirish rangi MATN sifatida ishlatilmaydi (§9.2). */
  tint: string;
};

const CELL_VIEW = {
  ok: {
    Icon: CheckCircle2,
    dashed: false,
    labelKey: "snapshots.cell.ok",
    tint: "border-border bg-success/12 text-success-text",
  },
  dark: {
    Icon: MoonStar,
    dashed: false,
    labelKey: "snapshots.cell.dark",
    tint: "border-border bg-warning/20 text-text",
  },
  blank: {
    Icon: ImageOff,
    dashed: false,
    labelKey: "snapshots.cell.blank",
    tint: "border-border bg-warning/20 text-text",
  },
  corrupt: {
    Icon: FileWarning,
    dashed: false,
    labelKey: "snapshots.cell.corrupt",
    tint: "border-border bg-warning/20 text-text",
  },
  failed: {
    Icon: XCircle,
    dashed: false,
    labelKey: "snapshots.cell.failed",
    tint: "border-border bg-danger/12 text-danger-text",
  },
  missed: {
    Icon: CircleSlash,
    dashed: true,
    labelKey: "snapshots.cell.missed",
    tint: "border-danger/50 bg-danger/12 text-danger-text",
  },
  pending: {
    Icon: Clock,
    dashed: false,
    labelKey: "snapshots.cell.pending",
    tint: "border-border bg-surface-muted text-text-muted",
  },
  running: {
    Icon: Loader2,
    dashed: false,
    labelKey: "snapshots.cell.running",
    tint: "border-border bg-surface-muted text-text",
  },
  skipped: {
    Icon: Minus,
    dashed: true,
    labelKey: "snapshots.cell.skipped",
    tint: "border-border bg-surface-muted text-text-muted",
  },
} as const satisfies Record<CaptureCellState, CellView>;

/**
 * `status` + `quality_verdict` juftligi -> to'qqiz holatdan biri.
 *
 * ⚠ NOMA'LUM QIYMAT BITTA HUJAYRANI EGALLAYDI, KUNNI YIQITMAYDI
 *   (04-10 qarori: sxemada bu maydonlar `z.string()`, chunki bitta
 *   yangi backend a'zosi butun 175 hujayrali kunni chegarada
 *   yiqitardi). Shuning uchun bu yerda ham istisno OTILMAYDI:
 *
 *     noma'lum `status`          -> `pending` («kutilmoqda»)
 *     `succeeded` + noma'lum hukm -> `ok` («olindi»)
 *
 *   Ikkala fallback ham ATAYIN eng KAMCHILIK da'vo qiladigan tomonga
 *   qiya: noma'lum holatni `missed` deb ko'rsatish YOLG'ON OGOHLANTIRISH
 *   bo'lardi va u jimgina o'tkazib yuborishdan yomonroq — admin mavjud
 *   bo'lmagan muammoni qidirib, haqiqiy `missed` larga ishonchini
 *   yo'qotardi. `succeeded` esa kadr HAQIQATAN olinganini bildiradi;
 *   sifat hukmi noma'lum bo'lsa ham «olindi» to'g'ri qoladi.
 */
export function captureCellState(run: {
  quality_verdict: string | null;
  status: string;
}): CaptureCellState {
  switch (run.status) {
    case "succeeded":
      switch (run.quality_verdict) {
        case "dark":
          return "dark";
        case "blank":
          return "blank";
        case "corrupt":
          return "corrupt";
        default:
          return "ok";
      }
    case "failed":
      return "failed";
    case "missed":
      return "missed";
    case "running":
      return "running";
    case "skipped":
      return "skipped";
    default:
      return "pending";
  }
}

export function CaptureCell({
  cameraName,
  isActive = false,
  onKeyDown,
  onOpen,
  registerRef,
  run,
  slotTime,
}: {
  cameraName: string;
  /** Roving tabindex — matritsada AYNAN BITTA hujayra `true` bo'ladi (§12.4). */
  isActive?: boolean;
  onKeyDown?: KeyboardEventHandler<HTMLButtonElement>;
  onOpen: () => void;
  registerRef?: (node: HTMLButtonElement | null) => void;
  /**
   * ⛔ `null` — kamera×vaqt juftligi uchun qator UMUMAN yo'q (kamera kun
   *    o'rtasida qo'shilgan). Hujayra baribir CHIZILADI va «rejaga
   *    kirmagan» bo'ladi: bo'sh katak bu yerda ham «ko'radigan narsa
   *    yo'q» degan yolg'on signal bo'lardi.
   */
  run: CaptureRun | null;
  slotTime: string;
}) {
  const t = useTranslations();

  const state: CaptureCellState =
    run === null ? "skipped" : captureCellState(run);
  const view: CellView = CELL_VIEW[state];
  const { Icon } = view;

  /*
   * ⚠ TO'LIQ JUMLA, uch bo'lakdan (§6.4): «06:30 · Kiyim qatori · Kadr
   *   olinmadi». Skrinrider foydalanuvchisi uchun ikonka YO'Q — matn
   *   YAGONA kanal, va u yolg'iz holat so'zidan iborat bo'lsa 175
   *   hujayrali jadvalda hech qanday ma'no tashimasdi.
   *
   * ⚠ HUJAYRA `aria-describedby` OLMAYDI (§6.5): legenda yozuvlariga
   *   bog'lash 175 hujayrada skrinriderni bo'g'ardi — har fokusda
   *   to'qqiz yozuvli lug'at qayta o'qilardi.
   */
  const label = t("snapshots.cellLabel", {
    camera: cameraName,
    state: t(view.labelKey),
    time: formatSlotTime(slotTime),
  });

  return (
    <button
      aria-label={label}
      className={cn(
        "flex min-h-11 min-w-11 items-center justify-center rounded-sm border",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        view.tint,
        view.dashed ? "border-dashed" : "border-solid",
      )}
      onClick={onOpen}
      onKeyDown={onKeyDown}
      ref={registerRef}
      tabIndex={isActive ? 0 : -1}
      title={label}
      type="button"
    >
      {/*
       * Ikonka `aria-hidden` — so'z allaqachon `aria-label` da va u ikki
       * marta e'lon qilinmasligi kerak. `running` aylanadi, ya'ni
       * harakat ham holat kanali bo'ladi (§9.4).
       */}
      <Icon
        aria-hidden="true"
        className={cn("size-4", state === "running" ? "animate-spin motion-reduce:animate-none" : null)}
      />
    </button>
  );
}
