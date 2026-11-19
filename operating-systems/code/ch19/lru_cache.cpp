// ch19/lru_cache.cpp: a least-recently-used cache with O(1) get and put.
#include <iostream>
#include <list>
#include <optional>
#include <unordered_map>
#include <utility>

/// Keeps at most `capacity` entries and evicts the one used longest ago.
class LruCache {
public:
    explicit LruCache(size_t capacity) : capacity_(capacity) {}

    /// Returns the value for `key` and marks it as most recently used.
    std::optional<int> get(int key) {
        auto found = index_.find(key);
        if (found == index_.end()) return std::nullopt;

        entries_.splice(entries_.begin(), entries_, found->second);
        return found->second->second;
    }

    /// Inserts or updates `key`, evicting the oldest entry when the cache is full.
    void put(int key, int value) {
        auto found = index_.find(key);

        if (found != index_.end()) {
            found->second->second = value;
            entries_.splice(entries_.begin(), entries_, found->second);
            return;
        }

        if (capacity_ == 0) return;   // a cache with no room stores nothing

        if (entries_.size() == capacity_) evict_oldest();

        entries_.emplace_front(key, value);
        index_[key] = entries_.begin();
    }

private:
    void evict_oldest() {
        index_.erase(entries_.back().first);
        entries_.pop_back();
    }

    size_t capacity_;
    std::list<std::pair<int, int>> entries_;   // front = most recently used
    std::unordered_map<int, std::list<std::pair<int, int>>::iterator> index_;
};

void show(const char* label, std::optional<int> value) {
    std::cout << label << (value ? std::to_string(*value) : "miss") << "\n";
}

int main() {
    LruCache cache(2);

    cache.put(1, 10);
    cache.put(2, 20);
    show("get 1 -> ", cache.get(1));   // 1 becomes most recent

    cache.put(3, 30);                  // evicts 2, the least recent
    show("get 2 -> ", cache.get(2));
    show("get 3 -> ", cache.get(3));

    cache.put(4, 40);                  // evicts 1
    show("get 1 -> ", cache.get(1));
    show("get 4 -> ", cache.get(4));
}
