/* NAME: text_parser
   DESC: Read text from stdin, count word frequency (case-insensitive), top-N with partial_sort, string_view, getline, unordered_map.
   KEYWORDS: text, word frequency, parser, tokenizer, string_view, unordered_map, getline, partial_sort, split, string processing, stdin */
#include <algorithm>
#include <cctype>
#include <iostream>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

std::vector<std::string> split_words(std::string_view text) {
    std::vector<std::string> words;
    std::string cur;
    for (char ch : text) {
        if (std::isalnum(static_cast<unsigned char>(ch))) cur += static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
        else if (!cur.empty()) { words.push_back(cur); cur.clear(); }
    }
    if (!cur.empty()) words.push_back(cur);
    return words;
}

int main() {
    std::ostringstream all;
    std::string line;
    while (std::getline(std::cin, line)) all << line << '\n';
    const auto words = split_words(all.str());
    std::unordered_map<std::string, int> freq;
    for (const auto& w : words) ++freq[w];

    std::vector<std::pair<std::string, int>> v(freq.begin(), freq.end());
    const std::size_t n = std::min<std::size_t>(5, v.size());
    std::partial_sort(v.begin(), v.begin() + static_cast<std::ptrdiff_t>(n), v.end(),
        [](const auto& a, const auto& b) { return a.second != b.second ? a.second > b.second : a.first < b.first; });
    std::cout << "total words: " << words.size() << ", unique: " << freq.size() << '\n';
    for (std::size_t i = 0; i < n; ++i) std::cout << v[i].first << ": " << v[i].second << '\n';
}
