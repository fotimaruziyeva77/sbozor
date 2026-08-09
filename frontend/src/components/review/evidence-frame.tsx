"use client";

import { useEffect, useRef, useState } from "react";
import { ImageOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvidenceImageHref } from "@/lib/review-queries";

/*
 * =============================================================================
 * DALIL KADRI — VA U QARORNING DARVOZASI (UI-SPEC §7.4).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ RASM YUKLANMASDAN QAROR YOZILMAYDI
 * -----------------------------------------------------------------------
 * Bu shunchaki UX emas: rasm ko'rilmagan qaror — MA'LUMOT EMAS, TAXMIN,
 * va u trening to'plamiga ham, aniqlik hisobotiga ham KIRADI
 * [MEROS: 05-RESEARCH §C.9, 2-band]. Ya'ni ochilmagan rasmda berilgan
 * javob keyinchalik «nazoratchi shunday dedi» degan DALIL bo'lib
 * ishlatilardi.
 *
 * Darvoza SOF FUNKSIYADA (`frameState`) yashaydi va u DOM'siz o'lchanadi
 * (`zoneEditorState()` da o'rnatilgan naqsh). Komponent uni faqat
 * CHAQIRADI.
 *
 * -----------------------------------------------------------------------
 * ⚠ UCHINCHI NOSOZLIK MANBAI: BAYTLARNI OLISH SO'ROVINING O'ZI
 * -----------------------------------------------------------------------
 * §7.4 ikki hodisani sanaydi (`onLoad` / `onError`), lekin kadr
 * `<img src="...">` bilan to'g'ridan-to'g'ri olinmaydi: marshrut sessiya
 * tokenini talab qiladi, `<img>` esa sarlavha qo'sha olmaydi. Baytlar
 * `apiRequest` bilan olinadi, ya'ni so'rovning O'ZI ham yiqilishi mumkin
 * — masalan sof `inspector` roli uchun **403** bilan (05-10/05-11
 * `threat_flag`). Shuning uchun darvoza UCH manbani ham hisobga oladi va
 * uchalasida ham natija BIR XIL: javob tugmalari `aria-disabled` bo'lib
 * QOLADI. Bu HALOL xulq — taxminiy javob yozilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ ZONA KONTURI KLIENTDA CHIZILADI (§7.4)
 * -----------------------------------------------------------------------
 * Serverda chizilgan kontur kadrni O'ZGARTIRARDI, ya'ni Y-2, Y-3 va Y-4
 * bir xil rastaning bir xil kadrini UCH XIL baytlar to'plami sifatida
 * olardi va kesh uchga bo'linardi. Klient overlayi kadrga TEGMAYDI.
 *
 * ⚠ POLIGON NORMALANGAN (0..1) va javobda kadr O'LCHAMI YO'Q (05-10,
 *   5-band). Shuning uchun overlay `viewBox="0 0 1000 1000"` +
 *   `preserveAspectRatio="none"` bilan quriladi va u ELEMENT QUTISIGA
 *   cho'ziladi. Element qutisi esa rasmning O'ZI (o'rovchi element
 *   rasmga siqiladi), ya'ni letterbox bo'shlig'i overlayga UMUMAN
 *   tushmaydi va koordinatalar uchun tuzatish kerak emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ YUKLAB OLISH, ULASHISH, NUSXALASH — YO'Q (§14.2)
 * -----------------------------------------------------------------------
 * Kadr tashrifchining shaxsiy ma'lumoti. Havola VAQTINCHALIK va u
 * komponent yopilganda bekor qilinadi (`review-queries.ts`). Rastr
 * yuzaga chizib eksport qiladigan yo'l bu yerda QURILMAYDI — taqiqlangan
 * API nomi bu izohda ATAYIN yozilmagan (03-07 qoidasi: skanerlanadigan
 * faylning izohidagi token darvozani o'zi qizartiradi).
 * =============================================================================
 */

/** Kadrning uch holati — S-1/S-2 (yuklanmoqda), S-3 (tayyor), xato. */
export type FrameState = "loading" | "failed" | "ready";

/**
 * Kadr darvozasi — SOF FUNKSIYA.
 *
 * ⚠ TARTIB AHAMIYATLI VA U SHU YERDA QULFLANADI:
 *
 *     xato -> yuklanmoqda -> tayyor
 *
 *   Xato pastga tushsa, yiqilgan so'rov «hali yuklanmoqda» bo'lib
 *   ko'rinardi va nazoratchi cheksiz skeletonga qarab o'tirardi —
 *   «Qayta urinish» tugmasi esa hech qachon chiqmasdi.
 *
 * ⚠ `imageLoaded` YAKUNIY SHART: baytlar kelgan bo'lsa ham brauzer
 *   ularni DEKOD QILA OLMASLIGI mumkin (buzilgan JPEG). O'sha holatda
 *   `onError` ishlaydi va `imageFailed` darvozani yopadi.
 */
export function frameState(input: {
  isPending: boolean;
  isError: boolean;
  imageLoaded: boolean;
  imageFailed: boolean;
}): FrameState {
  if (input.isError || input.imageFailed) return "failed";
  if (input.isPending || !input.imageLoaded) return "loading";
  return "ready";
}

/** Normalangan poligon -> `points` atributi (1000×1000 shartli birlik). */
export function overlayPoints(
  polygon: readonly (readonly [number, number])[],
): string {
  return polygon.map(([x, y]) => `${x * 1000},${y * 1000}`).join(" ");
}

export type EvidenceFrameProps = {
  /** Normalangan (0..1) zona konturi. */
  polygon: readonly (readonly [number, number])[];
  snapshotId: string;
  /** Kadr holati o'zgarganda — sessiya javob tugmalarini shunga qarab qulflaydi. */
  onStateChange: (state: FrameState) => void;
  /**
   * Yaqinlashtirish tugmasi ko'rsatiladimi (standart — HA).
   *
   * ⛔ JAVOB YOZILGANDAN KEYIN `false` (ko'rmasdan tekshirishda). Sabab
   *    mahsulotga oid: qaror allaqachon O'ZGARMAS, ya'ni kadrni qayta
   *    kattalashtirish faqat «to'g'ri javob berdimmi?» degan qayta
   *    o'ylashni taklif qilardi — aynan o'zgarmaslik himoya qilayotgan
   *    narsani. Qo'shimcha oqibati o'lchanadigan: javobdan keyin
   *    sessiyada FAQAT BITTA faol boshqaruv qoladi (`[Keyingisi →]`).
   */
  showZoom?: boolean;
};

export function EvidenceFrame({
  polygon,
  snapshotId,
  onStateChange,
  showZoom = true,
}: EvidenceFrameProps) {
  const t = useTranslations();
  const image = useEvidenceImageHref(snapshotId);

  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  /*
   * ⚠ BAND ALMASHGANDA HOLAT NOLLANISHI SHART: oldingi bandning
   *   «yuklandi» bayrog'i yangi bandga MEROS bo'lib o'tsa, nazoratchi
   *   hali chizilmagan kadrga javob bera olardi — ya'ni darvoza bir band
   *   davomida OCHIQ qolardi.
   *
   * ⛔ BU YERDA `useEffect` ISHLATILMAYDI: effekt ichida `setState`
   *    kaskad render beradi va `react-hooks/set-state-in-effect` uni
   *    xato sifatida rad etadi. Nollash CHAQIRUVCHIDA — `key={snapshotId}`
   *    bilan — bajariladi, ya'ni komponent butunlay QAYTA TUG'ILADI va
   *    ichki holat umuman qolmaydi. Bu React'ning o'z tavsiyasi
   *    («reset state with a key») va u effektdan kuchliroq: unutilgan
   *    bitta `setState` qolib ketishi MUMKIN EMAS.
   */
  const state = frameState({
    isPending: image.isPending,
    isError: image.isError,
    imageLoaded: loaded,
    imageFailed: failed,
  });

  useEffect(() => {
    onStateChange(state);
  }, [state, onStateChange]);

  /*
   * ⚠ FOKUS RASMDA, JAVOB TUGMASIDA EMAS (§13.5). Tugmadagi fokus «bos»
   *   degan taklif, rasmdagi fokus esa «qara» degan taklif — va bu
   *   ekranning butun mazmuni QARASH.
   */
  useEffect(() => {
    if (state === "ready") containerRef.current?.focus();
  }, [state]);

  return (
    <div className="flex flex-col gap-2">
      <div
        className="flex aspect-video items-center justify-center overflow-hidden rounded-md bg-text outline-none"
        data-testid="evidence-frame"
        ref={containerRef}
        tabIndex={-1}
      >
        {state === "loading" ? (
          <div aria-busy="true" className="w-full" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="aspect-video w-full" />
          </div>
        ) : null}

        {state === "failed" ? (
          <div className="flex flex-col items-center gap-2 p-4">
            <ImageOff aria-hidden="true" className="size-6 text-surface" />
            <p className="text-sm text-surface">
              {t("review.imageUnavailable")}
            </p>
            <Button
              onClick={() => {
                setFailed(false);
                setLoaded(false);
                image.retry();
              }}
              size="sm"
              variant="secondary"
            >
              {t("review.imageRetry")}
            </Button>
          </div>
        ) : null}

        {image.href === null ? null : (
          /*
           * ⚠ O'ROVCHI ELEMENT RASMGA SIQILADI (`inline-flex`), ya'ni
           *   overlay AYNAN rasm ustida turadi. `aspect-video` qutisidagi
           *   letterbox bo'shlig'i o'rovchidan TASHQARIDA qoladi.
           */
          <span
            className={
              state === "ready"
                ? "relative inline-flex max-h-full max-w-full"
                : "sr-only"
            }
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              alt={t("review.frameAlt")}
              className="max-h-full max-w-full object-contain"
              onError={() => setFailed(true)}
              onLoad={() => setLoaded(true)}
              src={image.href}
            />

            {/*
             * ⚠ `aria-hidden` — kontur RASMNING bir qismi, mustaqil
             *   ma'lumot emas. Skrinrider uni e'lon qilsa, «zona konturi»
             *   degan navigatsiya elementi paydo bo'lardi va u hech
             *   qayerga olib bormasdi (`zone-canvas.tsx` naqshi).
             */}
            <svg
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 size-full"
              preserveAspectRatio="none"
              viewBox="0 0 1000 1000"
            >
              <polygon
                className="fill-accent/10 stroke-accent"
                points={overlayPoints(polygon)}
                strokeWidth={6}
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          </span>
        )}
      </div>

      {/*
       * ⚠ YAQINLASHTIRISH JAVOBNI YOZMAYDI (§7.4) — u faqat kadrni
       *   kattaroq ko'rsatadi. Tugma FAQAT kadr tayyor bo'lganda
       *   chiqadi: bo'sh dialog ochish hech qanday savolga javob
       *   bermasdi.
       */}
      {state === "ready" && showZoom ? (
        <div className="flex justify-end">
          <Button onClick={() => setZoomOpen(true)} size="sm" variant="ghost">
            {t("review.zoomFrame")}
          </Button>
        </div>
      ) : null}

      <Dialog.Root onOpenChange={setZoomOpen} open={zoomOpen}>
        <Dialog.Content
          description={t("review.frameAlt")}
          size="lg"
          title={t("review.zoomFrame")}
        >
          {image.href === null ? null : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt={t("review.frameAlt")}
              className="w-full rounded-md"
              src={image.href}
            />
          )}
        </Dialog.Content>
      </Dialog.Root>
    </div>
  );
}
