# SBOZOR design system — build conventions

Bozor (bazaar) administration SaaS for Uzbekistan. Screens are used by cashiers standing in a market, inspectors walking rows, and directors reading reports.

## Setup

**No provider is required.** Components hold no state, no data fetching, and **no text of their own** — every label, hint and error arrives as a prop or as children. Render them directly.

**Theming is an attribute on any ancestor**, and tokens re-resolve inside that subtree:

- **light** — the default. There is **no** `data-theme="light"` rule; setting it does nothing. Omit the attribute.
- `data-theme="dark"` — dark surfaces.
- `data-theme="sun"` — direct-sunlight mode: pure white, pure black text, **no shadows**. Cashiers use this outdoors.

⚠ A light card inside a `data-theme="dark"` subtree is **not** achievable by nesting `data-theme="light"`. Paint the dark background on a separate layer and keep the card outside that subtree.

⚠ `color` is resolved once on `body`. A subtree that changes theme must also restate `color: var(--color-text)` (the shipped `.landing-night` class does this).

## Styling idiom

Tailwind v4 utilities bound to the tokens below. **Never hard-code a hex/oklch value and never invent a token name** — everything below is verified present in the shipped CSS.

| Family | Utilities |
|---|---|
| Surfaces | `bg-bg` `bg-surface` `bg-surface-muted` |
| Text | `text-text` `text-text-muted` |
| Borders | `border-border` (decorative) · `border-border-ui` (form controls — meets contrast) |
| Accent (only one per screen) | `bg-accent` `text-accent-fg` `hover:bg-accent-hover` `text-accent-text` |
| Success | `bg-success` `text-success-text` (tint: `bg-success/12`) |
| Warning | `bg-warning` `text-warning-text` (tint: `bg-warning/20`) — **never a text colour on its own** |
| Danger | `bg-danger` `text-danger-fg` `hover:bg-danger-hover` `text-danger-text` |
| Radius | `rounded-sm` (inputs) `rounded-md` (buttons) `rounded-lg` (cards) `rounded-xl` |
| Shadow | `shadow-card` `shadow-raised` (both become `none` under `sun`) |
| Type | `text-xs` `text-sm` `text-base` `text-lg` `text-xl` · `text-display` (money) · `text-hero` (landing h1 only) |
| Motion | `duration-(--motion-fast)` `duration-(--motion-base)` `duration-(--motion-slow)` · `ease-(--ease-out)` |

Ready-made classes in the bundle: `.landing-kicker`, `.landing-h2`, `.landing-h3`, `.landing-shell`, `.landing-night`, `.landing-card`, `.landing-proof`, `.landing-demo-card`, `.motion-enter`, `.motion-shake`, `.motion-check-draw`, `.motion-ring-pulse`, `.motion-row-land`.

## House rules that override generic taste

1. **Money**: integers only, so'm, thousands separated by a space, always `font-mono tabular-nums` — e.g. `8 000 so'm`. On a payment screen the amount is the largest element (`text-display`).
2. **Tap targets**: `min-h-11` (44px) minimum; primary confirm actions `min-h-14` (56px).
3. **One filled accent button per screen.** Everything else is `variant="secondary"` or `"ghost"`.
4. **Blocked actions use `aria-disabled`, not `disabled`** — a disabled button takes no focus and screen readers skip it.
5. **Colour is never the only signal** — pair every status colour with text or an icon.
6. **No invented numbers, no percentages, no superlatives** in any copy. Unmeasured claims are forbidden.
7. Three locales (uz-Latn, uz-Cyrl, ru): never bind a control's width to its label.

## Where the truth lives

`styles.css` and its `@import` closure (tokens + component CSS). Per-component API and examples: each component's `.prompt.md` and `.d.ts`.

## Idiomatic example

```jsx
<Card>
  <CardHeader>
    <h3 className="landing-h3">Kutilayotgan patta</h3>
    <p className="text-sm text-text-muted">Bu kutilayotgan summa — hisob hali yozilmagan.</p>
  </CardHeader>
  <CardContent className="flex flex-col items-start gap-3">
    <p className="font-mono text-display font-semibold tabular-nums">8 000 so'm</p>
    <Badge tone="success">Qarzi yo'q</Badge>
    <Button className="w-full" size="lg">To'lovni tasdiqlash</Button>
  </CardContent>
</Card>
```
