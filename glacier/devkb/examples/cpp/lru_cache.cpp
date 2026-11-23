/* NAME: lru_cache
   DESC: Generic LRU cache using std::list + std::unordered_map for O(1) get/put, with hit/miss statistics.
   KEYWORDS: lru, cache, list, unordered_map, template, iterator, splice, data structure, interview, o(1) */
#include <iostream>
#include <list>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>

template <typename K, typename V>
class LruCache {
public:
    explicit LruCache(std::size_t capacity) : cap_(capacity) {
        if (capacity == 0) throw std::invalid_argument("capacity must be > 0");
    }
    std::optional<V> get(const K& key) {
        auto it = index_.find(key);
        if (it == index_.end()) { ++misses_; return std::nullopt; }
        items_.splice(items_.begin(), items_, it->second);   // move to front, iterators stay valid
        ++hits_;
        return it->second->second;
    }
    void put(const K& key, V value) {
        auto it = index_.find(key);
        if (it != index_.end()) {
            it->second->second = std::move(value);
            items_.splice(items_.begin(), items_, it->second);
            return;
        }
        if (items_.size() == cap_) {
            index_.erase(items_.back().first);
            items_.pop_back();
        }
        items_.emplace_front(key, std::move(value));
        index_[key] = items_.begin();
    }
    std::size_t hits() const { return hits_; }
    std::size_t misses() const { return misses_; }
private:
    std::size_t cap_, hits_ = 0, misses_ = 0;
    std::list<std::pair<K, V>> items_;
    std::unordered_map<K, typename std::list<std::pair<K, V>>::iterator> index_;
};

int main() {
    LruCache<std::string, int> cache(2);
    cache.put("a", 1);
    cache.put("b", 2);
    cache.get("a");          // a becomes most recent
    cache.put("c", 3);       // evicts b
    for (const char* k : {"a", "b", "c"}) {
        auto v = cache.get(k);
        std::cout << k << ": " << (v ? std::to_string(*v) : "missing") << '\n';
    }
    std::cout << "hits=" << cache.hits() << " misses=" << cache.misses() << '\n';
}
