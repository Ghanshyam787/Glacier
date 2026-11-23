# CSS core: layout, responsive design, modern features

## Basics
- Selectors: `tag`, `.class`, `#id`, `a:hover`, `li:nth-child(2n)`, `.a .b` (descendant), `.a > .b` (child), `.a + .b` (next sibling), `[type="text"]`, `:not(.x)`, `:is(h1,h2)`, `:has(img)` (parent selector), `::before/::after`, `:focus-visible`.
- Specificity order: inline > id > class/attribute/pseudo-class > tag. Last rule wins on ties. Avoid `!important`; keep selectors shallow (BEM naming: `.card__title--big`).
- Always set `* { box-sizing: border-box; }` so width includes padding/border. Reset default `margin` on body/headings as needed.
- Cascade layers (`@layer`), custom properties: `:root { --brand: #1c8fd1; }` use `color: var(--brand, #000);` (can be changed per element and by JS: `el.style.setProperty("--x", "1")`).
- Units: `rem` (root font size) for type and spacing, `em` for component-relative, `%`, `vw/vh`, `dvh` (mobile-safe viewport height), `ch`, `fr` (grid). Avoid fixed `px` widths for containers.
- Colours: `#rrggbb`, `rgb(0 0 0 / .5)`, `hsl(200 80% 50%)`, `color-mix(in srgb, red 30%, white)`. `currentColor`.
- Typography: `font-family: system-ui, "Segoe UI", sans-serif; line-height: 1.6; font-size: clamp(1rem, 2vw, 1.25rem);` `max-width: 65ch` for readable lines.

## Box model and positioning
- `display: block | inline | inline-block | flex | grid | none | contents`. Margin collapses vertically between blocks; `gap` doesn't.
- `position: static | relative | absolute (relative to nearest positioned ancestor) | fixed | sticky (top: 0)`. `z-index` works on positioned/flex/grid items and stacking contexts.
- Centre horizontally: `margin-inline: auto` on a block with a width. Centre anything: `display: grid; place-items: center;`.
- `overflow: hidden | auto | scroll`, `text-overflow: ellipsis` (needs `white-space: nowrap; overflow: hidden`), `aspect-ratio: 16 / 9`, `object-fit: cover` on images, `min()`, `max()`, `clamp()`.

## Flexbox (one dimension)
```css
.row { display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.row > .grow { flex: 1 1 0; min-width: 0; }
```
- Container: `flex-direction`, `flex-wrap`, `justify-content` (main axis), `align-items` (cross axis), `gap`. Item: `flex: grow shrink basis`, `align-self`, `order`.
- Text not shrinking/overflowing in flex children: add `min-width: 0`.
- Typical uses: navbars, button rows, cards in a row, vertical centring, sticky footer (`body { min-height: 100vh; display: flex; flex-direction: column; } main { flex: 1; }`).

## Grid (two dimensions)
```css
.cards { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.layout { display: grid; grid-template-columns: 220px 1fr; grid-template-areas: "side main"; }
```
- `repeat(auto-fit, minmax(240px, 1fr))` gives responsive columns without media queries. `grid-column: span 2`, `grid-area`, `grid-template-rows`, `place-items`, `subgrid`.

## Responsive design
- Mobile-first: base styles for small screens, then `@media (min-width: 768px) { ... }`. Common breakpoints: 600px, 768px, 1024px, 1280px; choose where the layout breaks, not device names.
- Media features: `(prefers-color-scheme: dark)`, `(prefers-reduced-motion: reduce)`, `(hover: none)`, `(orientation: portrait)`, `print`.
- Container queries: `.card-wrap { container-type: inline-size; } @container (min-width: 400px) { ... }`.
- Responsive images: `max-width: 100%; height: auto;`. Test with devtools device mode.

## Visual effects
- `border-radius`, `box-shadow: 0 6px 24px rgb(0 0 0 / .1)`, `linear-gradient(135deg, #0e2a3d, #1c8fd1)`, `backdrop-filter: blur(8px)`, `filter`, `opacity`, `transform: translateY(-4px) rotate(3deg) scale(1.05)`, `transition: transform .2s ease`, `@keyframes` + `animation: spin 1s linear infinite`.
- Animate `transform` and `opacity` (GPU friendly), not `width/top/left`. Respect reduced-motion.
- Dark mode: define colour variables in `:root`, override inside `@media (prefers-color-scheme: dark)` or by `[data-theme="dark"]`; set `color-scheme: light dark;`.
- Scroll: `scroll-behavior: smooth`, `scroll-snap-type`, `position: sticky`. Custom scrollbar: `scrollbar-width`, `scrollbar-color`.
- Nesting is now native: `.card { & h3 { margin: 0 } &:hover { ... } }` (modern browsers).

## Debug checklist
- Element not styled: selector typo, specificity lost, file not linked, cache (hard reload), invalid value dropped.
- Layout overflowing: missing `box-sizing`, fixed widths, long words (`overflow-wrap: anywhere`), 100vw includes scrollbar.
- Margin collapse, inline-block whitespace gaps, `height: 100%` needs a parent height, absolute element needs positioned parent, `z-index` ignored without a stacking context.
- Use DevTools: inspect, "Computed" tab, toggle declarations, flex/grid overlays.
