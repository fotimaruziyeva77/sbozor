import { getTranslations } from "next-intl/server";

/*
 * Kirish sahnasining orqa foni — «Sbozor Login» dizayni.
 *
 * Server Component: JS ORQALI hech nima harakatlanmaydi — barcha harakat
 * CSS kadrlarida (`cellglow` / `scanbeam` / `floatup`), shuning uchun bu
 * yerda taymer ham, `use client` ham yo'q. Reduced-motion global blok bilan
 * o'chadi.
 *
 * ⛔ Butun qatlam `aria-hidden`: bu ATMOSFERA, kontent emas — ekran o'quvchi
 * uchun kirish formasi va yon ustundagi matn yetarli.
 */

/** Dizayndagi setka: 14 ustun × 9 qator. */
const COLUMNS = 14;
const ROWS = 9;

/**
 * Katak holati — dizayndagi AYNI determinal formula (tasodif YO'Q: server va
 * klient bir xil DOM chizishi shart, aks holda gidratatsiya nomuvofiqligi).
 */
function cellState(index: number): "empty" | "paid" | "flag" {
  const column = index % COLUMNS;
  const row = Math.floor(index / COLUMNS);
  const seed = (column * 7 + row * 13) % 11;
  if (seed === 5) return "flag";
  return seed % 3 === 0 ? "empty" : "paid";
}

/** Diagonal to'lqin: qo'shni kataklar ketma-ket nafas oladi. */
function cellDelaySeconds(index: number): string {
  const column = index % COLUMNS;
  const row = Math.floor(index / COLUMNS);
  return `${((column + row) * (14 / 26)).toFixed(2)}s`;
}

/* Yorliqlarning joyi va ritmi — dizayn qiymatlari. */
const CHIPS = [
  { key: "paid1", left: "4%", bottom: "7%", delay: "0s", duration: "16.2s" },
  { key: "unpaid", left: "26%", bottom: "4%", delay: "6s", duration: "19.8s" },
  { key: "paid2", left: "14%", bottom: "13%", delay: "12s", duration: "22.5s" },
] as const;

export async function LoginBackdrop() {
  const t = await getTranslations("auth");

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      <div className="login-map">
        {Array.from({ length: COLUMNS * ROWS }, (_, index) => (
          <span
            data-cell={cellState(index)}
            key={index}
            style={{ animationDelay: cellDelaySeconds(index) }}
          />
        ))}
      </div>
      <div className="login-beam" />
      {CHIPS.map((chip) => (
        <span
          className={
            chip.key === "unpaid"
              ? "login-chip text-warning-text"
              : "login-chip text-success-text"
          }
          key={chip.key}
          style={{
            animationDelay: chip.delay,
            animationDuration: chip.duration,
            bottom: chip.bottom,
            left: chip.left,
          }}
        >
          {chip.key === "unpaid"
            ? `! ${t("scene.chipUnpaid")}`
            : `✓ ${t("scene.chipPaid")}`}
        </span>
      ))}
    </div>
  );
}
