/*
 * Pul olinmaydigan mashinalar — `config.parking.exempt_plates` ustidagi
 * SOF yordamchilar. Chegaralar agentning `config.schema.json` bilan AYNAN
 * bir xil (raqam 4–12 belgi, yorliq ≤ 60, ro'yxat ≤ 500): server 422 bilan
 * rad etishidan OLDIN forma o'zi aytadi.
 *
 * Raqam agentdagi `NormPlate` kabi normallashtiriladi — katta harf, faqat
 * lotin harf va raqam. «85 c525 oa» va «85C525OA» bitta mashina; aks holda
 * kamera o'qigan raqam ro'yxatdagisiga mos kelmay, xodimdan pul olinardi.
 */
export const PLATE_MIN = 4;
export const PLATE_MAX = 12;
export const LABEL_MAX = 60;
export const EXEMPT_MAX = 500;

export type ExemptPlate = { plate: string; label?: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function normalizePlate(raw: string): string {
  return raw.toUpperCase().replace(/[^0-9A-Z]/g, "");
}

export function isPlateValid(plate: string): boolean {
  return plate.length >= PLATE_MIN && plate.length <= PLATE_MAX;
}

/** Sozlama hujjatidan ro'yxat; bo'lmasa yoki buzilgan bo'lsa — bo'sh. */
export function exemptPlatesOf(doc: Record<string, unknown>): ExemptPlate[] {
  const parking = doc.parking;
  if (!isRecord(parking) || !Array.isArray(parking.exempt_plates)) return [];
  const out: ExemptPlate[] = [];
  for (const item of parking.exempt_plates) {
    if (!isRecord(item) || typeof item.plate !== "string") continue;
    const label =
      typeof item.label === "string" && item.label.trim() !== ""
        ? item.label
        : undefined;
    out.push(label === undefined ? { plate: item.plate } : { plate: item.plate, label });
  }
  return out;
}

/**
 * Hujjatning FAQAT `parking.exempt_plates` qismi almashadi — tarif,
 * kassirlar va boshqa bo'limlar so'zma-so'z saqlanadi (server butun
 * hujjatni yangi versiya sifatida yozadi).
 */
export function withExemptPlates(
  doc: Record<string, unknown>,
  list: readonly ExemptPlate[],
): Record<string, unknown> {
  const parking = isRecord(doc.parking) ? doc.parking : {};
  return {
    ...doc,
    parking: {
      ...parking,
      exempt_plates: list.map((item) =>
        item.label === undefined || item.label.trim() === ""
          ? { plate: item.plate }
          : { plate: item.plate, label: item.label.trim() },
      ),
    },
  };
}
