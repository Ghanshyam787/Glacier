# HTML5 core, semantics and accessibility

## Document skeleton
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Page title (unique per page)</title>
  <meta name="description" content="150 character summary">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  ...
  <script src="script.js" defer></script>
</body>
</html>
```
- `<!DOCTYPE html>` first (else quirks mode). `lang` helps screen readers and translation. Viewport meta is required for responsive layouts on phones.
- `defer` runs the script after parsing, in order; `async` runs as soon as downloaded (order not guaranteed); `type="module"` is deferred by default.
- Paths: relative `images/a.png`, root `/a.png`. File names are case-sensitive on servers.

## Semantic structure (use instead of div soup)
- `<header>`, `<nav>`, `<main>` (one per page), `<section>` (with a heading), `<article>` (self-contained), `<aside>`, `<footer>`, `<figure>` + `<figcaption>`, `<address>`, `<time datetime="2026-11-17">`.
- Headings `h1..h6` in order, one `h1`. Do not choose headings for font size; style with CSS.
- Text: `p`, `strong` (importance), `em` (stress), `mark`, `code`, `pre`, `kbd`, `blockquote`, `cite`, `abbr title`, `sub`, `sup`, `br` (only for line breaks in addresses/poems), `hr`.
- Lists: `ul/ol/li`, `dl/dt/dd`. Navigation menus are lists inside `<nav>`.
- Links: `<a href="https://...">`; external with `target="_blank" rel="noopener noreferrer"`; in-page `<a href="#section-id">`; `mailto:`, `tel:`; download: `<a href="file.pdf" download>`.
- Images: `<img src="a.jpg" alt="meaningful description" width="800" height="600" loading="lazy">`. Decorative images get `alt=""`. Responsive: `<img srcset="a-480.jpg 480w, a-960.jpg 960w" sizes="(max-width: 600px) 100vw, 600px" src="a-960.jpg" alt="...">` or `<picture><source media="(min-width: 800px)" srcset="wide.webp"><img ...></picture>`.
- Media: `<video controls src poster>`, `<audio controls>`, `<track kind="captions">`. `<iframe title="...">`. `<canvas>` and inline `<svg>` for graphics.
- Tables: `<table><caption><thead><tbody><tfoot><tr><th scope="col"><td>`; use tables only for data, `colspan`/`rowspan` for merges.
- Interactive: `<details><summary>`, `<dialog>` (`showModal()`), `<button>`, `<progress>`, `<meter>`.

## Forms
```html
<form action="/submit" method="post">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required autocomplete="email">
  <label>Age <input type="number" name="age" min="1" max="120"></label>
  <fieldset><legend>Plan</legend>
    <label><input type="radio" name="plan" value="free" checked> Free</label>
    <label><input type="radio" name="plan" value="pro"> Pro</label>
  </fieldset>
  <select name="country"><option value="in">India</option></select>
  <textarea name="msg" rows="4"></textarea>
  <button type="submit">Send</button>
</form>
```
- Every control needs a `<label>` (for/id or wrapping). Placeholder is not a label.
- Types: text, email, password, number, tel, url, search, date, time, datetime-local, color, range, file (`accept`, `multiple`), checkbox, radio, hidden.
- Validation attributes: `required`, `minlength`, `maxlength`, `min`, `max`, `step`, `pattern`, `type`. JS: `form.checkValidity()`, `input.setCustomValidity("msg")`, `form.reportValidity()`. CSS: `:invalid`, `:user-invalid`, `:required`.
- `<button>` inside a form submits by default; use `type="button"` for others. Client validation is a convenience: always validate again on the server.
- Never put passwords or secrets in URLs (GET). Use `method="post"`. `autocomplete` values: `username`, `current-password`, `new-password`, `one-time-code`.

## Accessibility (a11y) checklist
- Use native elements first (button, a, input) - they come with keyboard and screen reader support. Do not attach click handlers to `div`.
- All functionality works with keyboard: Tab order follows DOM, visible `:focus-visible` outline, never `outline: none` without a replacement. Skip link `<a href="#main" class="skip">`.
- Text alternatives (alt, aria-label), colour contrast at least 4.5:1 for body text, do not rely on colour alone, `prefers-reduced-motion`.
- ARIA only when needed: `aria-label`, `aria-labelledby`, `aria-describedby`, `aria-live="polite"` for status updates, `aria-expanded`, `aria-current="page"`, `role="alert"`. "No ARIA is better than bad ARIA".
- Touch targets at least 44x44 CSS px. Don't disable zoom. Use relative units (`rem`).
- Landmarks: header, nav, main, footer let users jump around.

## SEO and meta
- Unique `<title>`, `meta description`, canonical link, Open Graph (`og:title`, `og:image`), `<link rel="icon">`, semantic headings, descriptive link text (not "click here"), alt text, fast loading.

## Security basics
- Escape user-provided text. In JS use `textContent`, never `innerHTML` with untrusted data (XSS). Add a Content-Security-Policy on real sites.
- External scripts: use `integrity` (SRI) and `crossorigin`. `rel="noopener"` for `_blank` links.
- Don't embed secrets/API keys in front-end code; anyone can read it. Proxy through a backend.

## Validation workflow
1. Run `check_html`; fix unclosed tags, duplicate ids, missing alt/lang/viewport, bad JS syntax.
2. Open in a browser, test at 360px, 768px, 1280px widths, keyboard-only, and with the console open (F12).
3. Lighthouse (Chrome DevTools) for accessibility/performance/SEO scores.
