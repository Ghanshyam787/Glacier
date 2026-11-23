# Web project blueprints (HTML + CSS + JS)

Use these as a checklist when a user asks for a website or web app. Start from `use_example` when one fits.

## Structure for any site
```
project/
  index.html
  css/style.css
  js/script.js
  images/
```
- Single-file is fine for small demos (inline `<style>`/`<script>`); split for anything larger.
- Mobile-first, semantic markup, CSS variables for theme, system fonts (no external requests) unless the user wants Google Fonts.
- Finish with `check_html`, a screenshot at desktop and phone width, and a short note on how to open it (double-click index.html).

## Blueprints
- **Portfolio / resume**: sticky nav with anchors, hero (name, role, CTA), about, skills tags, project cards grid, contact form (demo handler), dark/light toggle persisted in localStorage. Example: `portfolio`.
- **Landing page**: hero + CTA, 3 feature cards, pricing grid with featured plan, FAQ via `<details>`, footer. Example: `landing_page`.
- **Business / company site** (like a shop or factory): header with logo and phone, hero with offer, product categories grid, services, gallery, about, testimonials only if real, contact with address/map link (`<iframe>` Google Maps embed or link), WhatsApp link `https://wa.me/<number>`, opening hours, footer. Add JSON-LD `LocalBusiness` for SEO.
- **Todo / notes app**: array state, `render()` function rebuilding the list, event delegation, localStorage. Example: `todo_app`.
- **Calculator**: button grid + keyboard support; never use `eval`, parse with shunting-yard. Example: `calculator`.
- **Quiz app**: questions array, shuffle, radio inputs, score, progress. Example: `quiz_app`.
- **Games**: canvas + fixed-timestep loop (snake, pong, breakout, flappy, 2048, memory cards using CSS grid). Example: `snake_game`.
- **Form + validation**: constraint validation attributes + live custom messages with `aria-describedby`. Example: `form_validation`.
- **Dashboard**: sidebar + stat cards + SVG/canvas charts + sortable table. Example: `dashboard`.
- **Weather / API app**: `fetch` JSON from a public API (e.g. Open-Meteo needs no key), loading and error states, `Intl` formatting. Never embed secret keys in client code.
- **Chat UI / blog / e-commerce cart**: list rendering from an array, cart total in integer cents, `localStorage` persistence, checkout form stub.
- **Image gallery / slider / lightbox**: CSS grid, `<dialog>` for lightbox, `scroll-snap` for carousels, keyboard arrows.
- **Timer / stopwatch / pomodoro**: `setInterval` drift-free using `Date.now()` differences.
- **Markdown/Text tools**: `textarea` + live preview via `input` event; sanitise any HTML output.

## Quality bar (ChatGPT/Claude-level output)
1. Complete working code, no placeholders, realistic sample content.
2. Accessible: labels, alt text, focus styles, contrast, semantic landmarks.
3. Responsive: no horizontal scroll at 360px; `clamp()` type sizes; grid auto-fit.
4. Robust JS: guard null elements, try/catch around storage/JSON, no globals leaks (`"use strict"` or module).
5. Clean visuals: consistent spacing scale (0.5/1/1.5/2/3rem), one accent colour, soft shadows, radius 10-16px, hover/focus states.
6. Tested: `check_html` passes, screenshot reviewed.
