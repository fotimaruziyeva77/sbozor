"use client";

import { useCallback, useState } from "react";

import type { NvrErrorCode } from "@/lib/nvr-errors";
import { AUTH_LOCKING_CODES, isNvrErrorCode } from "@/lib/nvr-errors";

/*
 * =============================================================================
 * AUTH-XATO QULFI — 3-fazaning eng muhim interaksiya qoidasi (UI-SPEC §4.4).
 *
 * SABAB RAQAM BILAN (D-03, `03-RESEARCH.md` A.3): Hikvision NVR ketma-ket
 * ~5 ta xato autentifikatsiya urinishidan keyin hisobni 30 DAQIQAGA
 * qulflaydi va undan keyin TO'G'RI PAROL HAM ISHLAMAYDI. Ya'ni odatiy UI
 * naqshi — «xato -> [Qayta urinish] tugmasi» — bu yerda ZARARLI: admin
 * tugmani uch marta bosadi va bozorni yarim soatga to'xtatadi.
 *
 * SHUNING UCHUN:
 *   * qulf ostida «Qayta urinish» affordansi RENDER QILINMAYDI —
 *     yashirilmaydi, u UMUMAN YO'Q;
 *   * ikkala tugma ham `aria-disabled` (`disabled` EMAS: o'chirilgan
 *     tugma fokus olmaydi va skrinrider uni o'qimaydi, ya'ni «nega
 *     bosilmayapti?» savoliga javob qolmasdi);
 *   * qulf FAQAT `username` yoki `password` maydonining QIYMATI
 *     o'zgarganda ochiladi.
 *
 * RAD ETILGAN MUQOBILLAR (ikkalasi ham UI-SPEC §4.4 da):
 *   * «30 daqiqadan keyin AVTOMATIK qayta urinish» — avtomatik urinish
 *     adminning ko'zi oldida bo'lmaydi va u qulflanish sababini
 *     bilmasdan uni QAYTA TUG'DIRADI. Har urinish ODAMNING ANIQ
 *     QARORI bo'lishi shart.
 *   * «[Qulfni ochish] tugmasi» — u qulfni bir bosishlik bezakka
 *     aylantirardi.
 *
 * NEGA HOOK, `<form>` NING ICHKI HOLATI EMAS: qoidani IKKI yuza iste'mol
 * qiladi — NVR formasi (§4.3) va NVR kartasi («Diagnostika», «Qayta
 * skanerlash», §4.6). Formaga yashirilganda karta tomonida qoida
 * unutilardi va admin o'sha yerdan hisobni qulflardi.
 * =============================================================================
 */

type NvrAuthLockState = {
  /** Qulfni tug'dirgan kod — UI xato blokini shu bo'yicha chizadi. */
  readonly code: NvrErrorCode;
  /**
   * `nvr_account_locked` uchun `error_detail.unlock_at` (ISO-8601).
   *
   * `null` — vaqt sharti YO'Q, ya'ni qulf rekvizit o'zgarishi bilan
   * ochiladi. Qiymat bo'lsa IKKALA shart ham talab qilinadi.
   */
  readonly unlockAt: string | null;
};

export type NvrAuthLock = {
  /** Qulf yoqilganmi — ikkala tugma ham shu bo'yicha bloklanadi. */
  readonly authLocked: boolean;
  /** Qulfni tug'dirgan kod; `null` — qulf yo'q. */
  readonly lockedCode: NvrErrorCode | null;
  /** `nvr_account_locked` taymerining maqsad vaqti; `null` — taymer yo'q. */
  readonly unlockAt: string | null;
  /** Javobdagi `error_code` ni uzatadi; auth-qulflovchi bo'lmasa e'tiborsiz. */
  readonly lock: (
    code: string | null | undefined,
    detail?: Record<string, unknown> | null,
  ) => void;
  /**
   * Login yoki parol maydonining QIYMATI o'zgarganda chaqiriladi.
   *
   * ⚠ FOKUS, BOSISH yoki `blur` HODISASIDAN chaqirilMAYDI — faqat
   *   QIYMAT o'zgarishidan (`react-hook-form` `useWatch`). Aks holda
   *   admin maydonga tegib, hech narsani o'zgartirmay qulfni ochib
   *   yuborardi va o'sha noto'g'ri parolni QAYTA yuborardi.
   */
  readonly unlockOnCredentialChange: () => void;
  /** Yangi qurilma / yopilgan forma — qulf tarixisiz boshlanadi. */
  readonly reset: () => void;
};

function readUnlockAt(detail: Record<string, unknown> | null | undefined) {
  const value = detail?.unlock_at;
  return typeof value === "string" && value.length > 0 ? value : null;
}

/**
 * `unlock_at` o'tdimi.
 *
 * Parse qilib bo'lmaydigan qiymat «vaqt o'tmagan» deb hisoblanadi:
 * buzuq sanani «qulf ochildi» deb o'qish aynan qulflashni qayta
 * tug'diradigan yo'l edi (fail-closed).
 */
function unlockTimePassed(unlockAt: string | null): boolean {
  if (unlockAt === null) return true;
  const target = Date.parse(unlockAt);
  return Number.isFinite(target) && Date.now() >= target;
}

export function useNvrAuthLock(): NvrAuthLock {
  const [state, setState] = useState<NvrAuthLockState | null>(null);

  const lock = useCallback(
    (code: string | null | undefined, detail?: Record<string, unknown> | null) => {
      if (typeof code !== "string" || !isNvrErrorCode(code)) return;
      if (!AUTH_LOCKING_CODES.includes(code)) return;

      setState({ code, unlockAt: readUnlockAt(detail) });
    },
    [],
  );

  const unlockOnCredentialChange = useCallback(() => {
    setState((previous) => {
      if (previous === null) return previous;
      /*
       * `nvr_account_locked` da IKKALA shart ham kerak: rekvizit
       * o'zgargan VA qulf muddati o'tgan. Faqat rekvizitni tekshirish
       * adminni «yangi parol yozdim, endi ishlaydi» degan xulosaga olib
       * kelardi — holbuki qurilma qulf tugagunicha TO'G'RI parolni ham
       * rad etadi va har urinish qulfni UZAYTIRADI.
       */
      if (!unlockTimePassed(previous.unlockAt)) return previous;
      return null;
    });
  }, []);

  const reset = useCallback(() => setState(null), []);

  return {
    authLocked: state !== null,
    lockedCode: state?.code ?? null,
    unlockAt: state?.unlockAt ?? null,
    lock,
    unlockOnCredentialChange,
    reset,
  };
}
