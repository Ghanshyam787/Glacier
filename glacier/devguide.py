"""
Glacier - Coding expert guide (HTML/CSS/JS, C, C++, C#)
Jab user coding ka kaam maangta hai to ye guidance us turn ke message mein jud jaati hai (is_coding_request / guide_for).
Isse model Codex/Claude jaise workflow follow karta hai: plan -> poora code likho -> compile -> errors fix -> run/test -> summary.
"""

import re

_LANG_WORDS = {
    "html": r"\b(html5?|css3?|javascript|js|webpage|web ?page|website|web ?site|landing page|navbar|flexbox|dom|frontend|front-end|responsive|portfolio site)\b",
    "c": r"(?<![\w+#])c(?![\w+#])\s*(language|program|code|mein|me\b|programming|file|project|compiler)|\b(gcc|printf|scanf|malloc|stdio\.h|stdlib\.h)\b",
    "cpp": r"(?<![\w+#])(c\+\+|cpp)(?![\w+#])|\b(g\+\+|stl|iostream|cout|cmake|clang)\b|std::",
    "csharp": r"(?<![\w+#])(c#|c sharp|csharp|c\+)(?![\w+#])|\b(dotnet|linq|winforms)\b|\.net\b",
}
_GENERIC = (r"\b(code|coding|program|programming|compile|compiler|debug|bug|error fix|algorithm|project (banao|bana)|"
            r"app (banao|bana)|source|function|variable|loop|array|syntax|segmentation|undefined reference)\b")


def detect_languages(text: str) -> list:
    t = (text or "").lower()
    return [k for k, rx in _LANG_WORDS.items() if re.search(rx, t, re.I)]


def is_coding_request(text: str) -> bool:
    t = (text or "").lower()
    if detect_languages(t):
        return True
    return bool(re.search(_GENERIC, t))


WORKFLOW = """\
[CODING MODE - tum ek expert software engineer ho (Codex / Claude Code jaise). Is request ko poori tarah pakka karo.]
WORKFLOW (project / program banane ka kaam):
0. KNOWLEDGE BASE: pehle dev_reference(query) / list_examples() dekho. Agar koi tested example kaam se milta ho to use_example(name) se uski copy lo
   aur edit_file se user ki zarurat ke hisaab se badlo (zero se likhne se behtar aur tez). Kisi function/tag ki exact detail chahiye to lookup_docs(topic, language).
1. Chhoti baat samajh lo; zyada sawal mat pucho - samajhdar defaults chuno aur ek line mein bata do (language standard, features).
2. Project banane ke liye create_project(name, kind, ...) (html / c / cpp / csharp), phir write_file/edit_file se POORA kaam karne wala code likho.
   Koi placeholder nahi: "TODO", "...", "yahan code likho" KABHI nahi. Har file complete ho. Default folder: Documents\\Glacier Projects\\<name>.
3. C/C++/C#: compile_code(path) chalao. Errors/warnings padho, root cause theek karo (edit_file), dobara compile karo - jab tak 0 error AUR 0 warning
   na ho (max 6 round). Phir run_program(path, stdin_text=<sample input>) se chalake output verify karo (user se haan lagega - normal hai).
   Multi-file project ho to build_project(folder).
4. HTML/CSS/JS: check_html(path) se errors dekho, theek karo; html_screenshot(path) lo aur describe_image se dekho ki sach mein achha dikh raha hai;
   preview_html(path) se browser mein khol do.
5. KABHI mat bolo ki "compile ho gaya / chal gaya" jab tak tool ke output mein wahi na dikhe. Compiler na mile to dev_toolchain() dekho aur
   install_compiler offer karo.
6. Last mein chhota summary: kya banaya, kahan hai (full path), kaise chalana hai, 2-3 design points. Poora code chat mein tabhi do jab user maange
   ya file na bani ho. Code ke comments chhote aur kaam ke rakho. Jawab bolke sunaya jaata hai, isliye summary chhoti aur saaf rakho.
SAWAAL / CONCEPT: seedha, sahi jawab + chhota chalta hua example + 1-2 common galtiyan. Bina zarurat tools mat chalao.
DEBUG (user ne code ya error diya): pehle compile_code se reproduce karo (agar file hai), root cause batao, POORA theek kiya hua code do, ek line mein kyun.
Compiler error ka matlab Hinglish mein samjhao, jaise "undefined reference = linker ko function ki body nahi mili".
"""

C_GUIDE = """\
[C expert rules]
- Standard: C11 (-std=c11 -Wall -Wextra -Wpedantic). main: int main(void). Headers sahi include karo; non-standard (conio.h, gets, void main) KABHI nahi.
- Safety: input ke liye fgets + sscanf/strtol (scanf ka return check karo); gets() nahi; strcpy/sprintf ki jagah snprintf/strncpy-safe; buffer size pe dhyan.
- malloc/calloc/realloc ka return check; har allocation ka free; free ke baad pointer NULL; realloc ka result alag pointer mein lo.
- Undefined behavior se bacho: uninitialized variables, out-of-bounds, signed overflow, use-after-free, NULL dereference, format-specifier mismatch (%zu size_t, %d int, %lf double scanf mein).
- Structure: header (.h) + source (.c), include guards, static helper functions, const correctness, typedef struct, enum, function pointers, bit operations jahan jaruri.
- File I/O: fopen ka check, fclose, binary vs text, fread/fwrite sizes. Data structures: linked list, stack, queue, BST, hash table - memory freeing ke saath.
- Windows: UTF-8 output chahiye to SetConsoleOutputCP(65001). Makefile ya build.bat do (gcc main.c -o main.exe -Wall -Wextra).
- Errors: "implicit declaration" = include/prototype missing; "undefined reference" = linker (file/-l missing); segfault = invalid pointer/array bounds - code padhke dhundo.
- Typical projects: calculator, bank/student/library management (file storage), tic-tac-toe, snake (console), quiz, to-do, matrix ops, sorting visualiser (console).
"""

CPP_GUIDE = """\
[C++ expert rules]
- Default C++17 (-std=c++17 -Wall -Wextra -Wpedantic); user maange to C++20/23 (concepts, ranges, std::format agar compiler support kare).
- Modern style: RAII, std::unique_ptr/make_unique/shared_ptr (raw new/delete nahi), std::vector/std::array/std::string/std::string_view, range-for, auto jahan saaf ho,
  const& se pass, constexpr, enum class, std::optional/variant, structured bindings, lambdas, <algorithm>/<numeric>, std::move (rule of 0/5).
- Header mein "using namespace std" nahi. <bits/stdc++.h> sirf competitive programming mein (portable nahi) - warna sahi headers.
- Errors: exceptions (std::runtime_error), input validation (cin.fail, getline), stream state clear. Concurrency: std::thread, mutex, lock_guard, atomic, future.
- Classes: encapsulation, constructors/destructor, virtual destructor base mein, override/final, operator overloading sahi tareeke se, templates + concepts.
- Multi-file: include/ + src/, CMakeLists.txt (cmake_minimum_required 3.16, target_compile_features cxx_std_17, warnings). Single file ho to seedha g++.
- Template error ho to pehli aur aakhri lines padho; "undefined reference to vtable" = virtual function ki body missing; "no matching function" = argument types mismatch.
- Performance: pass by reference, reserve(), avoid copies, ios::sync_with_stdio(false) competitive mein; complexity batao.
- Typical projects: OOP bank/library/hospital system, inventory, text-based games, STL data structure demos, file parser, thread-pool, matrix/BigInt class, tic-tac-toe AI.
"""

CSHARP_GUIDE = """\
[C# expert rules]  (user ne "C+" likha to ise C# maano aur ek line mein bata do)
- .NET 8 console: <TargetFramework>net8.0</TargetFramework>, Nullable enable, ImplicitUsings enable. dotnet build / dotnet run.
- Modern C#: records, pattern matching, switch expressions, LINQ, async/await, using declarations, string interpolation, init-only properties, top-level statements.
- Classes/interfaces/generics/events/delegates; IDisposable; exceptions; List<T>/Dictionary<K,V>; file I/O System.IO; JSON System.Text.Json.
"""

HTML_GUIDE = """\
[HTML / CSS / JavaScript expert rules]
- HTML5: <!DOCTYPE html>, <html lang>, meta charset UTF-8, meta viewport, <title>, meta description. Semantic tags (header, nav, main, section, article, footer).
- Accessibility: alt text, label for inputs, buttons ka text, heading order (ek h1), focus styles, contrast, aria jahan zaruri, keyboard use.
- CSS: alag style.css, CSS variables (:root) + dark mode (prefers-color-scheme), mobile-first responsive (flex, grid, clamp(), media queries), reset (box-sizing),
  smooth hover/transition, prefers-reduced-motion, system font stack; internet assets par nirbhar mat raho (images ki jagah inline SVG/gradients).
- JavaScript: vanilla ES6+ (const/let, arrow, modules, template strings), DOM events, form validation, fetch with error handling, localStorage try/catch me,
  no jQuery/framework jab tak user na maange. Canvas games/animations: requestAnimationFrame.
- Files: index.html + style.css + script.js (chhota demo ho to ek file). Poora kaam karne wala, sundar, professional design - generic/boring nahi.
- Tools: check_html, html_screenshot (phir describe_image), preview_html. Dikhne mein galat ho to CSS fix karke dobara screenshot lo.
- Typical: portfolio, landing page, resume, calculator, to-do (localStorage), quiz, weather UI, login form, dashboards, tic-tac-toe/snake (canvas).
"""

_GUIDES = {"c": C_GUIDE, "cpp": CPP_GUIDE, "csharp": CSHARP_GUIDE, "html": HTML_GUIDE}


def guide_for(text: str) -> str:
    """Is request ke liye guide (kuch nahi = coding nahi)."""
    if not is_coding_request(text):
        return ""
    langs = detect_languages(text) or ["cpp"]
    # "c" aur "cpp" dono match ho to dono; C++ likha ho to C-only rules alag se jodne ki zaroorat nahi
    if "cpp" in langs and "c" in langs and re.search(r"c\+\+|cpp", (text or "").lower()):
        langs.remove("c")
    parts = [WORKFLOW] + [_GUIDES[k] for k in langs]
    return "\n".join(parts)


def guide_text(language: str) -> str:
    k = (language or "").lower().replace("c++", "cpp").replace("c#", "csharp").replace("c+", "csharp")
    if k in _GUIDES:
        return WORKFLOW + "\n" + _GUIDES[k]
    if k in ("js", "css", "javascript", "web", "website"):
        return WORKFLOW + "\n" + HTML_GUIDE
    return WORKFLOW + "\n" + "\n".join(_GUIDES.values())
