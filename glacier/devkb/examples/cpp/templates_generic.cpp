/* NAME: templates_generic
   DESC: Function and class templates, generic Stack<T>, variadic templates, if constexpr, concepts-free SFINAE alternative, fold expressions.
   KEYWORDS: template, generic, class template, function template, variadic, fold expression, if constexpr, type_traits, stack, typename */
#include <iostream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

template <typename T>
T max_of(T a, T b) { return a > b ? a : b; }

template <typename T>
class Stack {
public:
    void push(T v) { items_.push_back(std::move(v)); }
    T pop() {
        if (items_.empty()) throw std::underflow_error("stack empty");
        T v = std::move(items_.back());
        items_.pop_back();
        return v;
    }
    bool empty() const { return items_.empty(); }
    std::size_t size() const { return items_.size(); }
private:
    std::vector<T> items_;
};

template <typename... Args>
auto sum(Args... args) { return (args + ...); }

template <typename... Args>
void print_all(const Args&... args) { ((std::cout << args << ' '), ...); std::cout << '\n'; }

template <typename T>
std::string describe(const T& v) {
    if constexpr (std::is_integral_v<T>) return "integer " + std::to_string(v);
    else if constexpr (std::is_floating_point_v<T>) return "float " + std::to_string(v);
    else return "other: " + std::string(v);
}

int main() {
    std::cout << max_of(3, 7) << ' ' << max_of(2.5, 1.5) << ' ' << max_of<std::string>("abc", "abd") << '\n';
    Stack<std::string> s;
    s.push("a"); s.push("b");
    std::cout << s.pop() << s.pop() << " empty=" << std::boolalpha << s.empty() << '\n';
    try { s.pop(); } catch (const std::exception& e) { std::cout << "caught: " << e.what() << '\n'; }
    std::cout << "sum=" << sum(1, 2, 3, 4) << '\n';
    print_all("x", 42, 3.14, 'c');
    std::cout << describe(5) << " | " << describe(2.5) << " | " << describe("text") << '\n';
}
