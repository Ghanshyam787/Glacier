# Modern C++ core (C++17, notes for C++20)

## Build
- `g++ -std=c++17 -Wall -Wextra -Wpedantic -g main.cpp -o main` (add `-pthread` for threads, `-O2` for release, `-fsanitize=address,undefined` to debug).
- CMake: `cmake_minimum_required(VERSION 3.16)`, `project(app CXX)`, `set(CMAKE_CXX_STANDARD 17)`, `add_executable(app src/main.cpp)`.
- Use `<iostream>`, `<string>`, `<vector>`. Not `<bits/stdc++.h>` (non-portable) and not `using namespace std;` in headers.
- `int main()`; no `void main`, no `conio.h`, no `system("pause")` in portable code.

## I/O
- `std::cout << x << '\n';` (`'\n'` instead of `std::endl` unless a flush is needed). `std::cin >> n;` check `if (!(std::cin >> n))`.
- Read a line: `std::getline(std::cin, s);` after `>>` call `std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');`.
- Formatting: `<iomanip>` `std::setw`, `std::setprecision`, `std::fixed`, `std::left`, `std::boolalpha`. C++20 has `std::format`.
- Fast competitive I/O: `std::ios::sync_with_stdio(false); std::cin.tie(nullptr);`.
- Files: `std::ifstream in(path); std::ofstream out(path); std::fstream`; check `if (!in)`. Closing happens automatically (RAII).
- String streams: `std::istringstream ss(line); ss >> a >> b;` and `std::ostringstream`.

## Types and deduction
- `auto x = expr;` `const auto& ref`, `auto&& fwd`. `decltype(expr)`. Structured bindings: `auto [key, value] = *it;`.
- `nullptr` not `NULL`. `enum class Color { Red, Green };` (scoped, no implicit int). `constexpr` for compile-time values/functions. `static_assert`.
- Initialisation: brace init `int x{5};` prevents narrowing. `std::vector<int> v(5, 0)` is size 5; `std::vector<int> v{5, 0}` is two elements.
- Casts: `static_cast<T>` (normal), `dynamic_cast` (polymorphic downcast), `const_cast`, `reinterpret_cast` (avoid). Avoid C-style casts.
- `std::string`: `+`, `substr`, `find` (returns `npos`), `std::to_string`, `std::stoi/stod` (throw on bad input), `std::string_view` for non-owning read-only views (do not return views to temporaries).
- `std::optional<T>`, `std::variant<A,B>` with `std::visit`, `std::any`, `std::pair`, `std::tuple` (`std::get`, `std::tie`).

## Functions
- Pass cheap types by value, expensive by `const T&`, sinks by value then `std::move`. Output parameters: prefer returning a struct/tuple.
- Default arguments, overloads, `noexcept`, `[[nodiscard]]`, `[[maybe_unused]]`. Return values use copy elision/move; do not `return std::move(local)`.
- Lambdas: `[captures](params) -> ret { body }`. `[=]` copy, `[&]` reference, `[this]`, `[x = std::move(y)]`. A lambda returned from a function must not capture locals by reference. `mutable` lets a by-copy capture change.
- `std::function<R(Args)>` type-erased callable (heap cost); templates/`auto` parameters are faster.

## Classes and OOP
- `class` default private, `struct` default public. Constructors with member-init lists (`: a_(a), b_(b)`); members initialise in declaration order.
- `explicit` on single-argument constructors. `= default`, `= delete`. `const` member functions for read-only access. `mutable` for caches. `static` members.
- Inheritance: base needs a `virtual ~Base() = default;` if deleted via base pointer. Use `override` and `final`. Pure virtual `virtual void f() = 0;` makes an abstract class. Object slicing happens when passing derived by value; pass by reference/pointer.
- Rule of zero: let members (`std::string`, `std::vector`, smart pointers) manage resources. Rule of five: if you write one of destructor / copy ctor / copy assign / move ctor / move assign, consider all five (see smart_pointers_raii example).
- Operator overloading: members for `=`, `[]`, `()`, `->`, compound assignment; free/friend functions for `<<`, `>>` and symmetric binary operators (see operator_overload example). C++20 `operator<=>` generates all comparisons.
- Access: `private`, `protected`, `public`, `friend`. Prefer composition over inheritance. Interfaces = abstract classes with only pure virtuals.

## Memory and ownership
- Default to values and containers. Use `std::make_unique<T>()` for exclusive ownership, `std::make_shared<T>()` for shared, `std::weak_ptr` to break cycles. Raw pointers/references are non-owning observers only.
- No `new`/`delete` in application code. If unavoidable: `new[]` pairs with `delete[]`.
- RAII: acquire in constructor, release in destructor (files, locks, sockets). `std::lock_guard`, `std::unique_lock`, `std::ifstream` all follow this.
- Move semantics: `std::move(x)` only casts to rvalue; the moved-from object stays valid but unspecified. Mark move operations `noexcept` so `std::vector` uses them on reallocation.

## Templates
- `template <typename T> T max_of(T a, T b)`. Class templates need definitions in headers. Variadic: `template <typename... Ts>`, fold expression `(args + ...)`.
- `if constexpr` for compile-time branches; `<type_traits>` (`std::is_integral_v`, `std::enable_if_t`). C++20 `concepts`: `template <std::integral T>`.
- Template error messages are long: read the first error and the "required from here" line.

## Exceptions and errors
- `throw std::invalid_argument("..."); catch (const std::exception& e) { e.what(); }`. Catch by const reference. Derive custom errors from `std::runtime_error`.
- Destructors must not throw. Use `noexcept` carefully. For expected failures consider `std::optional`/return codes; exceptions for exceptional cases.
- `std::stoi` throws `std::invalid_argument` / `std::out_of_range`. `vector::at(i)` throws, `operator[]` does not check.

## Concurrency (summary, see threads example)
- `std::thread t(fn, args...); t.join();` (must join or detach before destruction). `std::mutex` + `std::lock_guard`, `std::atomic<T>`, `std::condition_variable` (always wait with a predicate), `std::async`/`std::future`. C++20: `std::jthread`.
- A data race (two threads, one writes, no synchronisation) is undefined behaviour. Compile with `-fsanitize=thread` to detect.

## C++20/23 highlights (only when compiler supports `-std=c++20`)
- Ranges (`std::ranges::sort(v)`, views `| std::views::filter(...)`), concepts, `std::format`, `std::span`, three-way comparison, designated initializers, `contains()` on maps/sets, `std::jthread`, coroutines, modules (poor tooling support), C++23 `std::print`, `std::expected`.
