# C++ errors, idioms and design recipes

## Reading compiler errors
- Start at the FIRST error; later ones are often consequences. Read "note:" lines: they show candidates and the template instantiation chain.
- `no match for 'operator<<'`: type has no stream operator; add `friend std::ostream& operator<<(std::ostream&, const T&)`.
- `cannot bind non-const lvalue reference to an rvalue`: you passed a temporary to `T&`; use `const T&`, `T&&` or a named variable.
- `use of deleted function`: copying a `unique_ptr`/`thread`/stream. Move it: `std::move(x)`.
- `call to non-static member function without an object`: need an instance, or make the function `static`.
- `invalid use of incomplete type`: forward-declared class used where the full definition is required; include the header.
- `undefined reference to vtable for X`: a virtual function was declared but not defined (also forgot the destructor or pure-virtual override).
- `undefined reference to 'X::f()'`: member defined nowhere or the .cpp not compiled. Also `static` data members need an out-of-class definition (or `inline` in C++17).
- `conversion from 'double' to 'int' changes value` (brace init narrowing): use `static_cast<int>(x)` deliberately.
- `ISO C++ forbids variable length array`: use `std::vector` or `std::array`.
- `'x' was not declared in this scope`: typo, missing `#include`, or `std::` prefix.
- `multiple definition`: non-inline function or variable defined in a header; mark `inline`/`static` or move to a .cpp.
- `expected primary-expression before ...`/`dependent name`: inside templates use `typename T::value_type` and `obj.template f<int>()`.
- `deduced conflicting types for parameter 'T'`: `max_of(1, 2.5)`; specify `max_of<double>(1, 2.5)`.

## Runtime failures
- `terminate called after throwing an instance of 'std::out_of_range'`: `.at()` or `stoi` failed and nothing caught it. Catch it or validate first.
- `std::bad_alloc`: absurd size (often from an uninitialised or negative-converted-to-huge `size_t`).
- Segfault with vectors: index past `size()`, using an iterator/reference after `push_back` reallocated, empty `back()/front()`. Use `.at()` or ASan.
- Segfault with smart pointers: using a moved-from `unique_ptr`; `shared_ptr` cycle leaks (use `weak_ptr`).
- Stack overflow: deep recursion or giant local arrays; use `std::vector`.
- Deadlock: two mutexes locked in different orders; use `std::scoped_lock(m1, m2)`.
- Dangling reference: returning `const T&` to a local, storing `std::string_view` of a temporary string, capturing locals by reference in a lambda that outlives them.
- Iterator invalidation: erasing in a range-for, inserting into a vector while iterating.
- Uninitialised variable / UB: run `-fsanitize=undefined,address`, and `-Wall -Wextra -Wshadow -Wconversion` for hints.

## Idioms
- RAII everywhere; no manual cleanup. Pass `const std::string&` / `std::string_view`. Return by value.
- Prefer algorithms over raw loops when they read better. Use `const` and `constexpr` by default.
- Pimpl for hiding implementation, Factory function returning `std::unique_ptr<Base>`, Strategy via `std::function`/virtual interface, Observer via vector of callbacks, Singleton via function-local static (`static Foo& instance() { static Foo f; return f; }`).
- Copy-and-swap assignment (see smart_pointers_raii example). Non-copyable: `Foo(const Foo&) = delete;`.
- CRTP, SFINAE, tag dispatch are advanced; use `if constexpr` and concepts first.
- Header layout: `.hpp` with include guard or `#pragma once`, declarations only (except templates/inline); `.cpp` includes its own header first.
- Project layout: `src/`, `include/`, `tests/`, `CMakeLists.txt`. Tests with doctest/Catch2/GoogleTest; or plain `assert` for small projects.

## Project recipes (what to implement)
- Bank / ATM: abstract `Account`, derived accounts, `std::map<id, unique_ptr<Account>>`, custom exceptions, transaction log vector (see bank_system).
- Library/Student/Employee/Hospital/Hotel/Inventory management: struct + `std::vector` or `std::map`, CRUD menu, CSV persistence with fstream (see library_mgmt, student_mgmt).
- Games: tic-tac-toe with minimax, snake/maze on console (grid `std::vector<std::string>`), hangman (`std::set<char>` guesses), number guess (`<random>`).
- Text tools: word counter, CSV parser, JSON-like parser, calculator with shunting-yard, to-do CLI, log analyser (see text_parser).
- Data structures: linked list, BST, graph (BFS/DFS/Dijkstra, see graph_algos), LRU cache (`list` + `unordered_map`), trie, heap, matrix class, big-integer addition with strings.
- Systems: thread pool (queue + condition_variable + workers), producer/consumer (see threads), simple TCP chat (Winsock on Windows, POSIX sockets on Linux).
- Always deliver: build instructions, sample input/output, README with usage, and compile with `-Wall -Wextra -Werror` clean.
