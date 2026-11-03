/**
 * BOZOR LOGOTIPI — fayl bor bo'lsa rasm, bo'lmasa bozor nomi (261103).
 *
 * ⛔ Da'vo: buzilgan rasm belgisi HECH QACHON qolmaydi. jsdom rasm
 *    yuklamaydi — `error` hodisasi qo'lda yuboriladi (brauzerdagi 404).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { MarketLogo, marketLogoSrc } from "@/components/ui/market-logo";

const MARKET_ID = "01a01f40-69e4-7c73-9096-c3b93c053403";

describe("MarketLogo", () => {
  test("fayl nomi — bozor identifikatorining o'zi (xarita yo'q)", () => {
    expect(marketLogoSrc(MARKET_ID)).toBe(`/markets/${MARKET_ID}.webp`);
    render(<MarketLogo marketId={MARKET_ID} marketName="Karmana bozor" />);

    const img = screen.getByRole("img", { name: "Karmana bozor" });
    expect(img).toHaveAttribute("src", `/markets/${MARKET_ID}.webp`);
  });

  test("fayl yo'q (404) — bozor NOMI matn bo'lib chiqadi", () => {
    render(
      <MarketLogo
        fallbackClassName="dir-eyebrow"
        marketId={MARKET_ID}
        marketName="Karmana bozor"
      />,
    );

    fireEvent.error(screen.getByRole("img"));

    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByText("Karmana bozor")).toHaveClass("market-logo-text", "dir-eyebrow");
  });

  test("bezak rejimi: skrinriderga o'qilmaydi; `fallback={null}` — hech narsa", () => {
    const { container } = render(
      <MarketLogo decorative fallback={null} marketId={MARKET_ID} marketName="Karmana bozor" />,
    );

    const img = container.querySelector("img");
    expect(img).toHaveAttribute("alt", "");
    expect(screen.queryByRole("img")).toBeNull();

    fireEvent.error(img as HTMLImageElement);
    expect(container).toBeEmptyDOMElement();
  });

  test("bozor almashsa yangi logo qayta so'raladi (xato manzil bilan eslanadi)", () => {
    const { rerender } = render(<MarketLogo marketId="aaa" marketName="A bozor" />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByText("A bozor")).toBeInTheDocument();

    rerender(<MarketLogo marketId="bbb" marketName="B bozor" />);
    expect(screen.getByRole("img", { name: "B bozor" })).toHaveAttribute(
      "src",
      "/markets/bbb.webp",
    );
  });
});
