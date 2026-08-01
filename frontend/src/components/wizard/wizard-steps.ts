import type { SetupStatusResponse } from "@/lib/api-types";

/*
 * =============================================================================
 * Ustaning YETTI qadami — YAGONA manba (UI-SPEC §6.2).
 *
 * Stepper, qobiq va faollashtirish paneli qadam ro'yxatini TAKRORLAMAYDI —
 * uchalasi ham shu moduldan o'qiydi. Ikkinchi nusxa bir kun ajralib ketardi
 * va o'shanda stepper "bajarilgan" deb ko'rsatgan qadam panelda "qoldi"
 * bo'lib turardi.
 *
 * TARTIB DID EMAS, BOG'LIQLIK — uchtasi ham DB darvozasi:
 *   toifa tarifdan OLDIN     — `tariffs` -> `stall_categories` FK;
 *   zona+toifa rastadan OLDIN — import ularni NOM bo'yicha qidiradi (02-12),
 *     ya'ni ular oldindan bo'lmasa 1000 qatorlik fayl BUTUNLAY rad etiladi
 *     (`zone_not_found` / `category_not_found` + D-14 all-or-nothing);
 *   rasta sotuvchidan OLDIN  — `stall_assignments` -> `stalls` FK.
 * Bu tartibni "qulayroq" qilib o'zgartirish server darvozalariga urilardi.
 *
 * BAJARILGANLIK SERVERDAN: har qadamning `isFilled` i AYNAN `setup-status`
 * javobini o'qiydi. Klientda hech qanday xotira yo'q va bo'lmasligi ham
 * kerak — sahifa yangilash, boshqa qurilmadan davom ettirish va uzilishdan
 * tiklanish shu tanlov tufayli TEKIN keladi (UI-SPEC §6.1).
 * =============================================================================
 */

/** Ustaning ikkinchi marshruti — 2–7-qadamlar shu yerda yashaydi. */
export const WIZARD_SETUP_PATH = "/markets/setup";

/** Ustaning birinchi marshruti — hali `market_id` yo'q, ya'ni `?step` ham yo'q. */
export const WIZARD_NEW_PATH = "/markets/new";

/**
 * `?step` yo'q yoki diapazondan tashqarida bo'lganda tushiladigan qadam.
 *
 * 1 EMAS: birinchi qadam `/markets/new` ga tegishli va bu marshrutda uning
 * formasi qayta ochilmaydi (rekvizitlarni tahrirlash endpointi 02-11 da
 * ATAYIN ochilmagan).
 */
export const DEFAULT_SETUP_STEP = 2;

/**
 * Faollashtirish qadami — `blocking[]` bo'sh bo'lganda yagona ma'noli manzil.
 *
 * Chala bozorda foydalanuvchi `blocking[0].step` ga tushadi; to'liq bozorda
 * esa qiladigan yagona ish — faollashtirish, ya'ni uni 2-qadamga tushirish
 * "endi nima?" savolini javobsiz qoldirardi.
 */
export const ACTIVATION_STEP = 7;

/**
 * `wizard.step.*` kalitlari — LITERAL union.
 *
 * `t(\`wizard.step.${id}\`)` shaklidagi dinamik kalit tip xavfsizligini
 * buzadi: nomi noto'g'ri yozilgan kalit kompilyatsiyadan o'tib, ekranda
 * xom kalit bo'lib chiqardi (02-15 da o'rnatilgan konvensiya).
 */
export type WizardStepLabelKey =
  | "wizard.step.1"
  | "wizard.step.2"
  | "wizard.step.3"
  | "wizard.step.4"
  | "wizard.step.5"
  | "wizard.step.6"
  | "wizard.step.7";

export type WizardStep = {
  readonly id: number;
  readonly labelKey: WizardStepLabelKey;
  /** Shu qadam ochilishidan OLDIN bajarilishi shart bo'lgan qadamlar. */
  readonly blockedBy: readonly number[];
  /** D-11: ixtiyoriy qadam `blocking[]` ga HECH QACHON tushmaydi. */
  readonly optional?: boolean;
  /** Qadam mazmuni serverda BORMI — javob AYNAN `setup-status` dan. */
  readonly isFilled: (status: SetupStatusResponse) => boolean;
};

export const WIZARD_STEPS: readonly WizardStep[] = [
  {
    id: 1,
    labelKey: "wizard.step.1",
    blockedBy: [],
    /*
     * Har doim bajarilgan: `market_profile` qatori bozor bilan BIRGA
     * tug'iladi (02-11 `market_create()`), ya'ni `setup-status` javobi
     * mavjud bo'lsa 1-qadam allaqachon o'tilgan.
     */
    isFilled: () => true,
  },
  {
    id: 2,
    labelKey: "wizard.step.2",
    blockedBy: [1],
    isFilled: (status) => status.zones > 0,
  },
  {
    id: 3,
    labelKey: "wizard.step.3",
    blockedBy: [1],
    isFilled: (status) => status.categories > 0,
  },
  {
    id: 4,
    labelKey: "wizard.step.4",
    blockedBy: [3],
    isFilled: (status) =>
      status.categories_total > 0 &&
      status.tariffs_covered >= status.categories_total,
  },
  {
    id: 5,
    labelKey: "wizard.step.5",
    blockedBy: [2, 3],
    isFilled: (status) =>
      status.stalls > 0 && status.stalls_with_category >= status.stalls,
  },
  {
    id: 6,
    labelKey: "wizard.step.6",
    blockedBy: [5],
    optional: true,
    isFilled: (status) => status.vendors > 0,
  },
  {
    id: 7,
    labelKey: "wizard.step.7",
    blockedBy: [1],
    isFilled: (status) => status.calendar_configured,
  },
];

/**
 * Kamera — QADAM EMAS (D-16).
 *
 * U `WIZARD_STEPS` massivida ATAYIN yo'q. Massivga qo'shilsa avtomatik
 * ravishda progress sanog'iga, `blockedBy` grafiga va "bajarilganmi?"
 * savoliga tushardi — ya'ni bozor kamerasiz HECH QACHON "to'liq"
 * ko'rinmasdi, holbuki D-16 aynan teskarisini talab qiladi: usta
 * kamerasiz YAKUNLANADI.
 *
 * Bu — qadam emas, `aria-disabled` ko'rsatkich: u tizim kameralarni
 * "biladi" degan xabarni beradi va admin ularni izlab yurmaydi.
 */
export const CAMERA_PLACEHOLDER = {
  labelKey: "wizard.step.cameras",
} as const;

export type WizardStepState = "completed" | "current" | "blocked" | "pending";

export type WizardStepView = {
  readonly step: WizardStep;
  readonly state: WizardStepState;
  /**
   * Mazmun serverda BORMI — `state` dan MUSTAQIL.
   *
   * Joriy qadam bajarilgan bo'lishi ham mumkin; `state` o'shanda "current"
   * bo'ladi (foydalanuvchi qayerdaligi muhimroq), lekin progress sanog'i
   * baribir to'g'ri qolishi kerak.
   */
  readonly filled: boolean;
  /** Bloklovchi BIRINCHI qadamning yorlig'i; boshqa holatlarda `null`. */
  readonly blockerLabelKey: WizardStepLabelKey | null;
};

/**
 * `setup-status` javobini stepper holatlariga aylantiradi.
 *
 * `status === null` — javob hali kelmagan yoki bozor umuman yaratilmagan
 * (`/markets/new`). U holda faqat 1-qadam ochiq: qolgan hammasi undan
 * bog'liq va "bloklangan" bo'lib ko'rinadi. Bu FAIL-CLOSED emas, HALOL:
 * bozorsiz zona ham, toifa ham qo'shib bo'lmaydi.
 *
 * USTUVORLIK: `current` > `blocked` > `completed` > `pending`.
 * `current` birinchi turadi, chunki `aria-current="step"` foydalanuvchining
 * QAYERDALIGINI aytadi va uni "bajarilgan" belgisi bilan almashtirish
 * skrinrider foydalanuvchisini o'rindan mahrum qilardi.
 */
export function wizardStepViews(
  status: SetupStatusResponse | null,
  currentStep: number,
): readonly WizardStepView[] {
  /*
   * Server AYNAN shu qadamni to'siq deb belgilagan bo'lsa, klientdagi
   * sanoq nima deyishidan qat'i nazar u bajarilgan HISOBLANMAYDI: to'liqlik
   * qoidasi serverda (`_blocking()`) va u yagona hakam.
   */
  const blockedByServer = new Set(
    (status?.blocking ?? []).map((item) => item.step),
  );

  const filledById = new Map<number, boolean>();
  for (const step of WIZARD_STEPS) {
    filledById.set(
      step.id,
      status !== null && step.isFilled(status) && !blockedByServer.has(step.id),
    );
  }

  return WIZARD_STEPS.map((step) => {
    const filled = filledById.get(step.id) === true;
    const blockerId = step.blockedBy.find(
      (dependency) => filledById.get(dependency) !== true,
    );
    const blocker =
      blockerId === undefined
        ? null
        : (WIZARD_STEPS.find((item) => item.id === blockerId) ?? null);

    let state: WizardStepState;
    if (step.id === currentStep) {
      state = "current";
    } else if (blocker !== null) {
      state = "blocked";
    } else if (filled) {
      state = "completed";
    } else {
      state = "pending";
    }

    return {
      step,
      state,
      filled,
      blockerLabelKey: state === "blocked" && blocker ? blocker.labelKey : null,
    };
  });
}

/** Progress qatoridagi `{done}` — bajarilgan qadamlar soni. */
export function completedStepCount(
  views: readonly WizardStepView[],
): number {
  return views.filter((view) => view.filled).length;
}

/**
 * `?step` shu marshrutda renderlanadigan diapazonda turadimi.
 *
 * 1-qadam ATAYIN chiqarib tashlanmaydi: bozor tanlash ekrani to'liq
 * qoralama uchun `?step=1` yuborishi mumkin (`fetchFirstIncompleteStep`
 * ning fail-safe qiymati) va u yerda foydalanuvchi boshi berk ko'chaga
 * tushmasligi kerak.
 */
export function isRenderableStep(step: number): boolean {
  return WIZARD_STEPS.some((item) => item.id === step);
}

/**
 * `?step` yaroqsiz bo'lganda tushiladigan qadam (UI-SPEC §6.6 ruhida).
 *
 * Chala bozorda — birinchi to'siqning qadami; to'liq bozorda —
 * faollashtirish qadami; javob hali kelmaganda — statik standart.
 */
export function fallbackStep(status: SetupStatusResponse | null): number {
  if (status === null) return DEFAULT_SETUP_STEP;
  const steps = status.blocking.map((item) => item.step);
  return steps.length > 0 ? Math.min(...steps) : ACTIVATION_STEP;
}
