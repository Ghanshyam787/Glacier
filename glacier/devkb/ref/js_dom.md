# JavaScript for the browser: language essentials and DOM

## Language essentials (ES2022+)
- `const` by default, `let` when reassigning, never `var`. Strict equality `===`. Falsy: `false, 0, "", null, undefined, NaN`. Optional chaining `a?.b?.[0]`, nullish `x ?? default` (keeps 0 and "").
- Types: `typeof`, `Number("12")`, `parseInt(s, 10)`, `parseFloat`, `Number.isNaN`, `String(x)`, template literals `` `Hi ${name}` ``. Floats: `0.1 + 0.2 !== 0.3`; money in integer cents, `toFixed(2)` for display.
- Functions: declarations are hoisted; arrow `(a, b) => a + b` (no own `this`). Default params, rest `...args`, spread `[...a, ...b]`, `{...obj, x: 1}`, destructuring `const { a, b = 2 } = obj; const [x, y] = arr;`.
- Arrays: `map`, `filter`, `reduce`, `find`, `findIndex`, `some`, `every`, `includes`, `flat`, `flatMap`, `sort((a, b) => a - b)` (default sort is string order and mutates), `slice` (copy) vs `splice` (mutates), `at(-1)`, `Array.from({length: n}, (_, i) => i)`, `structuredClone(obj)` deep copy.
- Objects: `Object.keys/values/entries`, `Object.fromEntries`, `Map`/`Set` for non-string keys/uniqueness, shorthand properties, computed keys `{[k]: v}`.
- Classes: `class A extends B { #private = 1; constructor() { super(); } static make() {} get x() {} }`.
- Modules: `<script type="module">`, `export`/`import`. Needs a server (not `file://`) for imports.
- Closures capture variables, `this` depends on call site (arrow functions keep outer `this`; `addEventListener` passes element as `this` for normal functions).
- Dates: `new Date()`, `Intl.DateTimeFormat`, `Intl.NumberFormat`; store UTC/ISO strings.
- Errors: `try { } catch (e) { } finally { }`, `throw new Error("msg")`. JSON: `JSON.parse` (throws on bad input), `JSON.stringify(obj, null, 2)`.

## Async
- Promises, `async/await`:
```js
async function load(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error("HTTP " + res.status);   // fetch does not reject on 404/500
  return res.json();
}
try { const data = await load("/api/items"); } catch (e) { showError(e.message); }
```
- Parallel: `await Promise.all([a(), b()])`; first-wins `Promise.race`; `Promise.allSettled`. `setTimeout(fn, ms)`, `setInterval`, `clearTimeout`; `requestAnimationFrame(fn)` for animation; debounce input handlers.
- `fetch` POST: `fetch(url, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(obj) })`. Cross-origin requests need CORS headers from the server.
- Forgotten `await` gives a Promise instead of data (printed as `Promise {<pending>}`).

## DOM
- Select: `document.querySelector(".x")`, `querySelectorAll` (NodeList; `[...list]` to use array methods), `getElementById`, `el.closest(sel)`, `el.matches(sel)`, `el.children`, `el.parentElement`.
- Change: `el.textContent = text` (safe), `el.append(...nodes)`, `el.replaceChildren()`, `document.createElement("li")`, `el.remove()`, `el.classList.add/remove/toggle/contains`, `el.dataset.id` (data-id), `el.setAttribute`, `el.style.setProperty("--x", v)`, `el.hidden`.
- `innerHTML` only for trusted static markup; with user data it is an XSS hole. Build nodes or use `textContent`.
- Events: `el.addEventListener("click", (e) => {...})`, `e.preventDefault()` (stop form submit/link), `e.target` vs `e.currentTarget`, event delegation (one listener on the parent, check `e.target.closest(...)`), `submit`, `input` (every keystroke), `change`, `keydown` (`e.key`), `pointerdown`, `DOMContentLoaded`, `resize`, `scroll` (use `{ passive: true }`).
- Forms: `new FormData(form)`, `Object.fromEntries(new FormData(form))`, `input.value` is always a string.
- Observers: `IntersectionObserver` (lazy load / reveal on scroll), `ResizeObserver`, `MutationObserver`.
- Script placement: use `defer` or put at the end of body; otherwise `querySelector` returns null (error "Cannot read properties of null").

## Browser storage and APIs
- `localStorage.setItem(key, JSON.stringify(obj))` / `JSON.parse(localStorage.getItem(key) ?? "null")` (strings only, ~5MB, same-origin, wrap in try/catch). `sessionStorage` per tab. `IndexedDB` for big data. Cookies for server sessions (`HttpOnly; Secure; SameSite`).
- `navigator.clipboard.writeText`, `Notification`, `geolocation`, `URL`, `URLSearchParams`, `history.pushState`, `matchMedia`, `crypto.randomUUID()`, `AbortController` (cancel fetch), `Web Workers` (heavy computation), `canvas.getContext("2d")`, `Audio`.

## Canvas game loop pattern
```js
let last = 0, acc = 0; const STEP = 1000 / 60;
function frame(t) { acc += t - last; last = t; while (acc >= STEP) { update(); acc -= STEP; } draw(); requestAnimationFrame(frame); }
requestAnimationFrame((t) => { last = t; frame(t); });
```
- Fixed timestep keeps speed identical on all monitors. Collision: AABB `a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y`.

## Common bugs
- `TypeError: Cannot read properties of null/undefined`: element not found or data not loaded yet.
- `ReferenceError: x is not defined`: typo/scope/script order. `Uncaught SyntaxError`: missing bracket/quote; `node --check file.js` finds it.
- `NaN` from `Number(undefined)`/`parseInt("")`; string concatenation instead of addition (`"1" + 2`).
- Event listener added in a loop with `var`; listeners added repeatedly on re-render (use delegation).
- CORS error, `file://` limitations (fetch, modules). Mixed content on https.
- Memory leaks: intervals/listeners never removed.

## Tooling
- `node --check file.js` for syntax, `node file.js` to run non-DOM logic, ESLint, Prettier, browser DevTools (Console, Network, Sources breakpoints). Frameworks (React, Vue, Svelte) are optional; plain HTML/CSS/JS is enough for most projects here.
