/* NAME: smart_pointers_raii
   DESC: RAII, unique_ptr, shared_ptr, weak_ptr, custom deleter, rule of five, move semantics.
   KEYWORDS: smart pointer, unique_ptr, shared_ptr, weak_ptr, raii, move semantics, rule of five, memory leak, ownership, deleter */
#include <cstdio>
#include <iostream>
#include <memory>
#include <string>
#include <utility>
#include <vector>

class Buffer {
public:
    explicit Buffer(std::size_t n) : size_(n), data_(new int[n]()) { std::cout << "Buffer(" << n << ")\n"; }
    ~Buffer() { delete[] data_; std::cout << "~Buffer\n"; }
    Buffer(const Buffer& o) : size_(o.size_), data_(new int[o.size_]) { std::copy(o.data_, o.data_ + size_, data_); std::cout << "copy\n"; }
    Buffer& operator=(const Buffer& o) { Buffer tmp(o); swap(tmp); return *this; }
    Buffer(Buffer&& o) noexcept : size_(std::exchange(o.size_, 0)), data_(std::exchange(o.data_, nullptr)) { std::cout << "move\n"; }
    Buffer& operator=(Buffer&& o) noexcept { Buffer tmp(std::move(o)); swap(tmp); return *this; }
    void swap(Buffer& o) noexcept { std::swap(size_, o.size_); std::swap(data_, o.data_); }
    std::size_t size() const { return size_; }
private:
    std::size_t size_;
    int* data_;
};

struct Node {
    std::string name;
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;  // weak breaks the reference cycle
    explicit Node(std::string n) : name(std::move(n)) {}
    ~Node() { std::cout << "~Node " << name << '\n'; }
};

int main() {
    {
        auto p = std::make_unique<Buffer>(4);
        auto q = std::move(p);
        std::cout << "p is " << (p ? "set" : "null") << ", q size " << q->size() << '\n';
    }
    {
        Buffer a(2);
        Buffer b = std::move(a);
        std::vector<Buffer> v;
        v.reserve(1);
        v.push_back(std::move(b));
    }
    {
        auto a = std::make_shared<Node>("A");
        auto b = std::make_shared<Node>("B");
        a->next = b;
        b->prev = a;
        std::cout << "use_count(a)=" << a.use_count() << " use_count(b)=" << b.use_count() << '\n';
    }
    {
        std::unique_ptr<std::FILE, int (*)(std::FILE*)> f(std::fopen("/dev/null", "r"), &std::fclose);
        std::cout << "file " << (f ? "opened" : "failed") << ", closes automatically\n";
    }
}
