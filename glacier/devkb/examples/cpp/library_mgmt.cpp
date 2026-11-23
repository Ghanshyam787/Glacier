/* NAME: library_mgmt
   DESC: Library system with vector of books, members, borrow/return, search by title, std::optional, algorithms.
   KEYWORDS: library, management, vector, optional, find_if, class, struct, borrow, return, search, project, stl */
#include <algorithm>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

struct Book {
    int id;
    std::string title, author;
    bool available = true;
};

class Library {
public:
    void add(std::string title, std::string author) {
        books_.push_back({next_id_++, std::move(title), std::move(author)});
    }
    std::optional<Book*> find(int id) {
        auto it = std::find_if(books_.begin(), books_.end(), [id](const Book& b) { return b.id == id; });
        if (it == books_.end()) return std::nullopt;
        return &*it;
    }
    std::vector<const Book*> search(const std::string& word) const {
        auto lower = [](std::string s) { std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); }); return s; };
        std::vector<const Book*> out;
        for (const auto& b : books_)
            if (lower(b.title).find(lower(word)) != std::string::npos) out.push_back(&b);
        return out;
    }
    bool borrow(int id) {
        auto b = find(id);
        if (!b || !(*b)->available) return false;
        (*b)->available = false;
        return true;
    }
    bool give_back(int id) {
        auto b = find(id);
        if (!b || (*b)->available) return false;
        (*b)->available = true;
        return true;
    }
    void list() const {
        for (const auto& b : books_)
            std::cout << b.id << ". " << b.title << " by " << b.author << (b.available ? "" : " [borrowed]") << '\n';
    }
private:
    std::vector<Book> books_;
    int next_id_ = 1;
};

int main() {
    Library lib;
    lib.add("The C Programming Language", "Kernighan & Ritchie");
    lib.add("Effective Modern C++", "Scott Meyers");
    lib.add("Clean Code", "Robert Martin");
    std::cout << std::boolalpha << "borrow 2: " << lib.borrow(2) << ", again: " << lib.borrow(2) << '\n';
    lib.list();
    std::cout << "search 'c++':\n";
    for (const auto* b : lib.search("c++")) std::cout << "  " << b->title << '\n';
    std::cout << "return 2: " << lib.give_back(2) << ", return 9: " << lib.give_back(9) << '\n';
}
