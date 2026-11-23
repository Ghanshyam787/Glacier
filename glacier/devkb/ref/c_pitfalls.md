# C pitfalls, compiler errors and debugging

## Common compiler/linker messages and what they mean
- `undefined reference to 'foo'` (linker): declaration exists but no definition was linked. Add the .c file to the build, or the library flag (`-lm`, `-lpthread`).
- `implicit declaration of function 'foo'`: missing `#include` or prototype. In C99+ this is an error with `-pedantic-errors`.
- `expected ';' before ...`: the error is usually on the previous line.
- `format '%d' expects argument of type 'int', but argument has type 'long'`: wrong printf specifier. Use `%ld`, `%zu`, `%lld`.
- `warning: control reaches end of non-void function`: missing return on some path.
- `assignment to expression with array type`: arrays cannot be assigned; use `strcpy`/`memcpy` or `snprintf`.
- `incompatible pointer type`: types differ (e.g. `int**` vs `int(*)[N]`). Do not silence with a cast until you understand it.
- `variable-sized object may not be initialized`: VLAs cannot have initializers; use `memset` or heap.
- `multiple definition of 'x'`: a definition (not declaration) sits in a header included by several .c files. Use `extern` in the header and define once in a .c file.
- `segmentation fault`: invalid memory access. Run with `-g -fsanitize=address` to get the exact line.
- Windows exit code `0xC0000005` = access violation (same idea as segfault). `0xC00000FD` = stack overflow (runaway recursion or huge local array).

## Bugs that compile fine
1. Off-by-one: `for (i = 0; i <= n; i++)` over an array of n elements.
2. `scanf("%d", x)` instead of `&x`. `scanf("%s", name)` with no width.
3. `if (x = 0)` instead of `==`. Semicolon after `if (...);` or `for(...);`.
4. `sizeof(arr)` inside a function that received `arr` as parameter.
5. Using uninitialised locals. Returning a pointer to a local array.
6. `char c = getchar();` cannot hold `EOF`; use `int c`.
7. `strcpy(dest, src)` with `dest` too small. Forgetting space for `'\0'`.
8. Comparing floats with `==`. Use `fabs(a - b) < 1e-9`.
9. `free` of memory then using it; freeing twice; leaking in early-return paths.
10. Modifying a string literal: `char *s = "abc"; s[0] = 'x';` crashes.
11. `printf(userString)` format-string vulnerability: always `printf("%s", s)`.
12. Integer overflow in size calculation: `malloc(n * m)`.
13. Returning `int` from `main` implicitly is fine in C99+, but not from `void main`.
14. Mixing `scanf` and `fgets` without flushing the leftover newline.
15. Macro side effects: `SQ(i++)`.

## Debugging workflow
1. Compile with `-Wall -Wextra -Wpedantic -g`. Fix every warning.
2. Reproduce with the smallest input. Print state with `fprintf(stderr, ...)`.
3. Run with `-fsanitize=address,undefined`: it reports heap/stack overflow, use-after-free, leaks, signed overflow, bad shifts with file:line.
4. Use a debugger: `gdb ./prog` then `run`, `bt` (backtrace), `frame N`, `print var`, `break file.c:42`, `watch var`.
5. `assert(cond)` for invariants (disabled by `-DNDEBUG`).
6. Static analysis: `cppcheck --enable=all file.c`, `clang-tidy`.

## Style that avoids bugs
- One declaration per line, initialise at declaration, smallest scope.
- Check every return value that can fail (`fopen`, `malloc`, `fgets`, `scanf`, `fclose` on write).
- Prefer `size_t` for sizes, `const` for read-only parameters, `static` for private functions.
- Pair allocation and release in the same module; document ownership in comments ("caller frees").
- Keep functions short; return error codes and use `goto cleanup` for multiple resources.

## Typical beginner projects and the key technique
- Student/employee management: struct array or file of structs + menu loop + `fgets` input (see student_db example).
- Bank/ATM: struct + balance checks + file persistence.
- Tic-tac-toe, hangman, number guessing: 2D array / string handling + `rand`.
- Library system: struct + linked list or dynamic array.
- Calculator: recursive descent parser (see calculator example) or stack-based evaluation.
- Linked list, stack, queue, BST, hash table: pointer practice (see examples).
