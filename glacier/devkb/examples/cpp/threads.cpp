/* NAME: threads
   DESC: std::thread, mutex, lock_guard, atomic, condition_variable producer/consumer, async/future.
   KEYWORDS: thread, mutex, atomic, condition variable, producer consumer, async, future, concurrency, race condition, lock_guard, parallel */
#include <atomic>
#include <condition_variable>
#include <future>
#include <iostream>
#include <mutex>
#include <numeric>
#include <queue>
#include <thread>
#include <vector>

int main() {
    // 1. data race avoided with atomic and with mutex
    std::atomic<int> atomic_counter{0};
    int plain_counter = 0;
    std::mutex m;
    std::vector<std::thread> ts;
    for (int i = 0; i < 4; ++i)
        ts.emplace_back([&] {
            for (int k = 0; k < 10000; ++k) {
                ++atomic_counter;
                std::lock_guard<std::mutex> lock(m);
                ++plain_counter;
            }
        });
    for (auto& t : ts) t.join();
    std::cout << "atomic=" << atomic_counter << " mutex=" << plain_counter << '\n';

    // 2. producer / consumer
    std::queue<int> q;
    std::mutex qm;
    std::condition_variable cv;
    bool done = false;
    std::thread consumer([&] {
        long total = 0;
        for (;;) {
            std::unique_lock<std::mutex> lock(qm);
            cv.wait(lock, [&] { return !q.empty() || done; });
            if (q.empty() && done) break;
            total += q.front();
            q.pop();
        }
        std::cout << "consumer total=" << total << '\n';
    });
    for (int i = 1; i <= 100; ++i) {
        { std::lock_guard<std::mutex> lock(qm); q.push(i); }
        cv.notify_one();
    }
    { std::lock_guard<std::mutex> lock(qm); done = true; }
    cv.notify_all();
    consumer.join();

    // 3. async parallel sum
    std::vector<int> data(1000);
    std::iota(data.begin(), data.end(), 1);
    auto half = data.begin() + 500;
    auto f1 = std::async(std::launch::async, [&] { return std::accumulate(data.begin(), half, 0L); });
    long second = std::accumulate(half, data.end(), 0L);
    std::cout << "parallel sum=" << f1.get() + second << '\n';
}
