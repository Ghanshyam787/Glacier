/* NAME: graph_algos
   DESC: Graph with adjacency list: BFS, DFS, Dijkstra shortest path (priority_queue), topological sort, cycle detection.
   KEYWORDS: graph, bfs, dfs, dijkstra, shortest path, topological sort, adjacency list, priority_queue, algorithm, data structure, cycle */
#include <functional>
#include <iostream>
#include <limits>
#include <queue>
#include <utility>
#include <vector>

using Edge = std::pair<int, int>;  // (to, weight)

std::vector<int> bfs(const std::vector<std::vector<Edge>>& g, int s) {
    std::vector<int> order, seen(g.size(), 0);
    std::queue<int> q;
    q.push(s); seen[static_cast<std::size_t>(s)] = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (auto [v, w] : g[static_cast<std::size_t>(u)]) {
            (void)w;
            if (!seen[static_cast<std::size_t>(v)]) { seen[static_cast<std::size_t>(v)] = 1; q.push(v); }
        }
    }
    return order;
}

void dfs(const std::vector<std::vector<Edge>>& g, int u, std::vector<int>& seen, std::vector<int>& order) {
    seen[static_cast<std::size_t>(u)] = 1;
    order.push_back(u);
    for (auto [v, w] : g[static_cast<std::size_t>(u)]) { (void)w; if (!seen[static_cast<std::size_t>(v)]) dfs(g, v, seen, order); }
}

std::vector<long long> dijkstra(const std::vector<std::vector<Edge>>& g, int s) {
    const long long INF = std::numeric_limits<long long>::max();
    std::vector<long long> dist(g.size(), INF);
    using P = std::pair<long long, int>;
    std::priority_queue<P, std::vector<P>, std::greater<>> pq;
    dist[static_cast<std::size_t>(s)] = 0;
    pq.push({0, s});
    while (!pq.empty()) {
        auto [d, u] = pq.top(); pq.pop();
        if (d > dist[static_cast<std::size_t>(u)]) continue;
        for (auto [v, w] : g[static_cast<std::size_t>(u)])
            if (d + w < dist[static_cast<std::size_t>(v)]) { dist[static_cast<std::size_t>(v)] = d + w; pq.push({dist[static_cast<std::size_t>(v)], v}); }
    }
    return dist;
}

// Kahn's algorithm; returns empty vector if the graph has a cycle
std::vector<int> topo_sort(const std::vector<std::vector<Edge>>& g) {
    std::vector<int> indeg(g.size(), 0), order;
    for (const auto& adj : g) for (auto [v, w] : adj) { (void)w; ++indeg[static_cast<std::size_t>(v)]; }
    std::queue<int> q;
    for (std::size_t i = 0; i < g.size(); ++i) if (indeg[i] == 0) q.push(static_cast<int>(i));
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (auto [v, w] : g[static_cast<std::size_t>(u)]) { (void)w; if (--indeg[static_cast<std::size_t>(v)] == 0) q.push(v); }
    }
    return order.size() == g.size() ? order : std::vector<int>{};
}

int main() {
    std::vector<std::vector<Edge>> g(6);
    auto add = [&](int a, int b, int w) { g[static_cast<std::size_t>(a)].push_back({b, w}); };
    add(0, 1, 7); add(0, 2, 9); add(0, 5, 14); add(1, 2, 10); add(1, 3, 15);
    add(2, 3, 11); add(2, 5, 2); add(3, 4, 6); add(5, 4, 9);
    std::cout << "BFS:";
    for (int x : bfs(g, 0)) std::cout << ' ' << x;
    std::vector<int> seen(g.size(), 0), order;
    dfs(g, 0, seen, order);
    std::cout << "\nDFS:";
    for (int x : order) std::cout << ' ' << x;
    std::cout << "\nDijkstra from 0:";
    for (long long d : dijkstra(g, 0)) std::cout << ' ' << d;
    auto t = topo_sort(g);
    std::cout << "\nTopological order:";
    for (int x : t) std::cout << ' ' << x;
    std::cout << (t.empty() ? " (cycle!)" : "") << '\n';
}
