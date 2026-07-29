import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Tailwind sinflarini xavfsiz birlashtiradi.
 *
 * `clsx` shartli sinflarni yig'adi, `twMerge` esa ziddiyatli utilitalarni
 * (masalan `px-3` va `px-6`) oxirgisi foydasiga hal qiladi — variant ustidan
 * `className` bilan yozish shu tufayli ishlaydi.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
