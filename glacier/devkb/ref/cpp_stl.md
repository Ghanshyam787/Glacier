# C++ STL cheat sheet

## Containers (what to pick)
- `std::vector<T>`: default sequence. Contiguous, O(1) `push_back` (amortised), `[]`, `at`, `size`, `empty`, `back`, `pop_back`, `insert`, `erase`, `reserve`, `clear`, `emplace_back`. Invalidates iterators on reallocation/erase.
- `std::array<T,N>`: fixed size on stack. `std::deque<T>`: O(1) push/pop at both ends. `std::list<T>`: O(1) insert/erase at iterator, no random access. `std::forward_list`.
- `std::map<K,V>` (sorted, O(log n), red-black tree), `std::set<K>`, `std::multimap`, `std::multiset`. `m[k]` inserts a default value if missing; use `m.find(k)`, `m.count(k)`, `m.contains(k)` (C++20), `m.at(k)` (throws), `m.emplace`, `m.try_emplace`, `m.insert_or_assign`.
- `std::unordered_map<K,V>`, `std::unordered_set<K>`: hash tables, average O(1), no order. Custom key types need `std::hash` and `operator==`.
- Adaptors: `std::stack` (push/pop/top), `std::queue` (push/pop/front/back), `std::priority_queue<T>` (max-heap; min-heap: `priority_queue<T, vector<T>, greater<T>>`). None has iterators.
- `std::string`, `std::string_view`, `std::bitset<N>`, `std::pair`, `std::tuple`.

## Iterating
- Range-for: `for (const auto& x : v)`, modify: `for (auto& x : v)`, map: `for (const auto& [k, val] : m)`.
- Iterators: `v.begin()`, `v.end()` (one past the last), `rbegin/rend`, `std::next`, `std::prev`, `std::advance`, `std::distance`.
- Erase while iterating a map: `it = m.erase(it);` else `++it`.
- Erase-remove idiom (pre C++20): `v.erase(std::remove_if(v.begin(), v.end(), pred), v.end());` C++20: `std::erase_if(v, pred)`.

## `<algorithm>` and `<numeric>` essentials
- Sorting: `std::sort(b, e)`, `sort(b, e, cmp)`, `stable_sort`, `partial_sort`, `nth_element`, `is_sorted`, `reverse`, `rotate`, `shuffle(b, e, std::mt19937{seed})`.
- Searching: `find`, `find_if`, `count`, `count_if`, `any_of`, `all_of`, `none_of`, `binary_search`, `lower_bound`, `upper_bound` (sorted range), `min_element`, `max_element`, `minmax_element`, `adjacent_find`, `search`.
- Transforming: `transform`, `for_each`, `copy`, `copy_if`, `fill`, `iota`, `replace`, `unique` (after sort, with erase), `partition`, `remove`/`remove_if`.
- Numeric: `std::accumulate(b, e, init)` (use `0LL` or `0.0` for the right type), `reduce`, `inner_product`, `partial_sum`, `std::gcd`, `std::lcm`, `std::clamp`, `std::min`, `std::max`, `std::swap`.
- Comparators must be strict weak ordering (`<` not `<=`), else undefined behaviour/crash.
- Sort by multiple keys: `return std::tie(a.x, a.y) < std::tie(b.x, b.y);`.

## Complexity cheat sheet
- vector: access O(1), push_back O(1) amortised, insert middle O(n). list: insert O(1) at iterator, find O(n). map/set: O(log n). unordered_*: O(1) average, O(n) worst. priority_queue: push/pop O(log n), top O(1). sort O(n log n). binary_search O(log n).

## Random numbers and time
- `std::mt19937 rng{std::random_device{}()}; std::uniform_int_distribution<int> d(1, 6); d(rng);` (not `rand()` % n).
- Timing: `auto t0 = std::chrono::steady_clock::now(); ... std::chrono::duration<double, std::milli>(now - t0).count();`
- Sleep: `std::this_thread::sleep_for(std::chrono::milliseconds(100));`

## Strings and text recipes
- Split by delimiter: use `std::getline(ss, token, ',')` on an `istringstream`.
- Trim, lower: `std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return std::tolower(c); });`
- Join: loop with `ostringstream`. Replace: `s.replace(pos, len, text)`. Contains: `s.find(x) != std::string::npos` (C++23 `contains`).
- Numbers: `std::to_string(n)`, `std::stoi(s)`, `std::stod(s)`, `std::from_chars` (fast, no exceptions).
- `std::filesystem` (C++17, `<filesystem>`): `exists`, `is_directory`, `directory_iterator`, `create_directories`, `file_size`, `path::extension()`. Link `-lstdc++fs` only on very old GCC.
