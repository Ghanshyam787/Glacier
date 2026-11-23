# C language core (C11)

## Program skeleton and build
- Minimal: `#include <stdio.h>` then `int main(void) { puts("hi"); return 0; }`.
- Compile: `gcc -std=c11 -Wall -Wextra -Wpedantic -g main.c -o main` (add `-lm` for math.h, `-fsanitize=address,undefined` while debugging).
- Multi-file: header `foo.h` (declarations + include guard), `foo.c` (definitions). Compile each to `.o` then link, or `gcc *.c`.
- Include guard: `#ifndef FOO_H` / `#define FOO_H` / ... / `#endif`.
- Never use `void main`, `conio.h`, `gets`, `fflush(stdin)`, `clrscr`, `getch` in portable code.

## Types and sizes
- `char` (1 byte), `short`, `int` (usually 4), `long` (4 on Windows, 8 on Linux 64-bit), `long long` (8), `float`, `double`, `long double`.
- Fixed width: `#include <stdint.h>` gives `int8_t..int64_t`, `uint8_t..uint64_t`; `size_t` for sizes and indices; `bool` from `<stdbool.h>`.
- printf specifiers: `%d` int, `%u` unsigned, `%ld` long, `%lld` long long, `%zu` size_t, `%f`/`%lf` double (printf), `%c` char, `%s` string, `%p` pointer (cast to `void*`), `%x` hex, `%5.2f` width/precision.
- scanf specifiers: `%d`, `%f` float, `%lf` double (NOT `%f`), `%s` (stops at whitespace, needs width `%49s`), `%c`.
- Integer division truncates toward zero. `/` on ints never gives decimals: cast one operand `(double)a / b`.
- Signed overflow is undefined behaviour. Unsigned wraps around modulo 2^n.
- Integer promotion: `char` and `short` become `int` in expressions. Mixing signed and unsigned converts signed to unsigned (classic bug: `-1 < 1u` is false).

## Operators and control flow
- Precedence traps: `==` binds tighter than `&`, so write `(x & mask) == 0`. `a = b == c` assigns the comparison. `if (x = 5)` is an assignment bug (the compiler warns with -Wall).
- `&&` and `||` short-circuit. `++i` vs `i++`. Ternary `c ? a : b`.
- `switch` falls through without `break`; use `/* fallthrough */` comments when intended. `case` labels must be integer constants.
- Loops: `for`, `while`, `do..while`, `break`, `continue`. `goto cleanup;` is acceptable for single-exit error cleanup.
- Bitwise: `& | ^ ~ << >>`. Set bit `x |= 1u << n`, clear `x &= ~(1u << n)`, toggle `x ^= 1u << n`, test `(x >> n) & 1u`. Shifting by >= width or shifting negative values is undefined.

## Functions
- Pass by value always. To modify the caller's variable pass a pointer: `void inc(int *p) { (*p)++; }` called as `inc(&x)`.
- Prototype before use. `static` on a function = file-private. `inline` hint. Recursion needs a base case; deep recursion overflows the stack.
- Arrays decay to pointers when passed; the callee cannot know the length, so pass `size_t n` too. `sizeof` of a parameter array is the pointer size.
- Function pointers: `int (*op)(int,int) = add;` `op(2,3)`; used for callbacks like `qsort` comparators and dispatch tables.
- Variadic: `<stdarg.h>` with `va_list`, `va_start`, `va_arg`, `va_end`.

## Arrays and strings
- Array of N elements has indices 0..N-1. No bounds checking: out-of-bounds is undefined behaviour.
- A string is a `char` array ending in `'\0'`. `char s[] = "hi";` is a modifiable copy (3 bytes); `char *p = "hi";` points to read-only memory (use `const char *`).
- `<string.h>`: `strlen` (excludes NUL), `strcmp` (0 when equal), `strncmp`, `strchr`, `strstr`, `memcpy` (no overlap), `memmove` (overlap ok), `memset`, `strncpy` (does NOT always NUL-terminate), `strcat`.
- Safe formatting: `snprintf(buf, sizeof buf, "%s-%d", name, n);` returns the length that would have been written.
- Never compare strings with `==`. Never `sizeof(ptr)` expecting the array length.
- `<ctype.h>` functions need `unsigned char` casts: `isalpha((unsigned char)c)`.

## Input
- Read a line: `if (fgets(line, sizeof line, stdin)) { line[strcspn(line, "\r\n")] = '\0'; }`.
- Parse numbers: `strtol(line, &end, 10)` and check `end != line` and `errno`; `strtod` for doubles; `sscanf(line, "%d", &x) == 1`.
- Always check scanf's return value. After `scanf("%d")` a newline stays in the buffer; this breaks the next `fgets`/`%c`. Prefer fgets + sscanf.

## Structs, unions, enums
- `typedef struct { int id; char name[32]; } Person;` Access `p.id`, via pointer `ptr->id`.
- Structs can be copied and passed by value; padding makes `sizeof` larger than the sum of members. Use `offsetof` from `<stddef.h>`.
- Designated init: `Person p = { .id = 1, .name = "Asha" };`. Zero-init: `Person p = {0};`.
- `enum Color { RED, GREEN, BLUE };` are ints. Union shares memory among members; only read the member last written.
- Flexible array member: `struct Buf { size_t n; char data[]; };` allocate `sizeof(struct Buf) + n`.

## Pointers
- `int *p = &x;` `*p` dereferences. `NULL` is the null pointer; dereferencing it crashes.
- Pointer arithmetic is scaled by element size: `p + 1` moves `sizeof *p` bytes. `a[i]` is `*(a + i)`.
- `const int *p` (data is const), `int *const p` (pointer is const), `const int *const p` (both).
- `void *` is the generic pointer; convert implicitly in C (do not cast malloc's result in C).
- Pointer to pointer lets a function change a pointer (see linked_list example `Node **head`).
- Never return the address of a local variable. Never use a pointer after `free`.
- Strict aliasing: do not access an object through an incompatible pointer type; use `memcpy` for type punning.

## Dynamic memory
- `p = malloc(n * sizeof *p);` always check for NULL. `calloc(n, size)` zeroes and checks overflow. `realloc` may move: `tmp = realloc(p, new); if (!tmp) {handle; keep p} else p = tmp;`.
- Every allocation needs exactly one `free`. After free set `p = NULL`. Free of NULL is safe. Double free and freeing non-heap pointers are bugs.
- Check multiplication overflow for sizes: `if (n > SIZE_MAX / sizeof *p) fail`.
- Find leaks: `-fsanitize=address` (prints leak report at exit) or Valgrind on Linux.

## File I/O
- `FILE *f = fopen(path, "r"|"w"|"a"|"rb"|"wb"|"r+");` check for NULL, `perror("fopen")`, always `fclose`.
- Text: `fgets`, `fprintf`, `fputs`. Binary: `fread(buf, size, count, f)` / `fwrite`, return value is the item count.
- `fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);` for file size. `feof` only becomes true after a read fails; loop on the read's return value, not on `feof`.
- Writing structs to binary files ties the file to the compiler's padding and endianness; fine for learning projects.

## Standard library quick map
- `<stdlib.h>`: `malloc/free/realloc/calloc`, `qsort`, `bsearch`, `rand/srand`, `atoi/strtol/strtod`, `exit`, `abs`, `getenv`.
- `<math.h>`: `sqrt pow sin cos fabs floor ceil round fmod log exp` (link with `-lm`).
- `<time.h>`: `time(NULL)`, `clock()`, `strftime`, `localtime`. Seed rand with `srand((unsigned)time(NULL))` once.
- `<limits.h>`: `INT_MAX`, `CHAR_BIT`. `<float.h>`: `DBL_EPSILON`. `<errno.h>`: `errno`, `strerror`. `<assert.h>`: `assert(cond)`.
- qsort comparator: `int cmp(const void *a, const void *b) { int x = *(const int*)a, y = *(const int*)b; return (x > y) - (x < y); }` (do not return `x - y`, it can overflow).

## Preprocessor
- `#define PI 3.14159`, prefer `enum` or `static const`. Macro functions need parentheses: `#define SQ(x) ((x) * (x))` and still evaluate arguments twice.
- Conditional compile: `#ifdef _WIN32`, `#if defined(__GNUC__)`. `#pragma once` is common but not standard.
- `__FILE__`, `__LINE__`, `__func__` for logging. `static_assert` (C11) for compile-time checks.
