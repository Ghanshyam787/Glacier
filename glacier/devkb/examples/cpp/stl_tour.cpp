/* NAME: stl_tour
   DESC: Tour of the STL: vector, array, deque, list, set, map, unordered_map, stack, queue, priority_queue, algorithms, lambdas, ranges-free.
   KEYWORDS: stl, vector, map, set, unordered_map, deque, stack, queue, priority_queue, sort, accumulate, algorithm, lambda, iterator, containers, tutorial */
#include <algorithm>
#include <array>
#include <deque>
#include <iostream>
#include <map>
#include <numeric>
#include <queue>
#include <set>
#include <stack>
#include <string>
#include <unordered_map>
#include <vector>

int main() {
    std::vector<int> v{5, 2, 9, 1, 7};
    std::sort(v.begin(), v.end(), std::greater<>());
    std::cout << "sorted desc:";
    for (int x : v) std::cout << ' ' << x;
    std::cout << "\nsum=" << std::accumulate(v.begin(), v.end(), 0)
              << " max=" << *std::max_element(v.begin(), v.end()) << '\n';
    v.erase(std::remove_if(v.begin(), v.end(), [](int x) { return x % 2 == 0; }), v.end());
    std::cout << "odd only size=" << v.size() << '\n';

    std::array<int, 3> arr{1, 2, 3};
    std::deque<int> dq{2, 3};
    dq.push_front(1);
    dq.push_back(4);
    std::cout << "array size=" << arr.size() << " deque front=" << dq.front() << " back=" << dq.back() << '\n';

    std::set<std::string> s{"pear", "apple", "fig", "apple"};
    std::cout << "set (unique, ordered):";
    for (const auto& x : s) std::cout << ' ' << x;
    std::cout << '\n';

    std::map<std::string, int> counts;
    for (const std::string w : {"a", "b", "a", "c", "a", "b"}) ++counts[w];
    for (const auto& [word, n] : counts) std::cout << word << '=' << n << ' ';
    std::cout << '\n';

    std::unordered_map<int, std::string> um{{1, "one"}, {2, "two"}};
    if (auto it = um.find(2); it != um.end()) std::cout << "found " << it->second << '\n';

    std::stack<int> st;
    std::queue<int> q;
    std::priority_queue<int, std::vector<int>, std::greater<>> minheap;
    for (int i : {3, 1, 2}) { st.push(i); q.push(i); minheap.push(i); }
    std::cout << "stack top=" << st.top() << " queue front=" << q.front() << " minheap top=" << minheap.top() << '\n';

    std::vector<int> a{1, 2, 3, 4, 5}, b(5);
    std::transform(a.begin(), a.end(), b.begin(), [](int x) { return x * x; });
    std::cout << "squares:";
    for (int x : b) std::cout << ' ' << x;
    std::cout << "\nbinary_search 16: " << std::boolalpha << std::binary_search(b.begin(), b.end(), 16) << '\n';
}
