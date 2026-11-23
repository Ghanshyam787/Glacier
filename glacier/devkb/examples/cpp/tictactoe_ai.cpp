/* NAME: tictactoe_ai
   DESC: Tic-Tac-Toe human vs unbeatable AI using minimax, std::array board, enum class.
   KEYWORDS: tic tac toe, minimax, ai, game, array, enum class, recursion, unbeatable, game ai, algorithm */
#include <array>
#include <iostream>
#include <string>

enum class Cell : char { Empty = ' ', X = 'X', O = 'O' };
using Board = std::array<Cell, 9>;

static Cell winner(const Board& b) {
    static const int lines[8][3] = {{0,1,2},{3,4,5},{6,7,8},{0,3,6},{1,4,7},{2,5,8},{0,4,8},{2,4,6}};
    for (const auto& l : lines)
        if (b[l[0]] != Cell::Empty && b[l[0]] == b[l[1]] && b[l[1]] == b[l[2]]) return b[l[0]];
    return Cell::Empty;
}
static bool full(const Board& b) { for (Cell c : b) if (c == Cell::Empty) return false; return true; }

static int minimax(Board& b, bool ai_turn) {
    Cell w = winner(b);
    if (w == Cell::O) return 1;
    if (w == Cell::X) return -1;
    if (full(b)) return 0;
    int best = ai_turn ? -2 : 2;
    for (auto& c : b) {
        if (c != Cell::Empty) continue;
        c = ai_turn ? Cell::O : Cell::X;
        int score = minimax(b, !ai_turn);
        c = Cell::Empty;
        best = ai_turn ? std::max(best, score) : std::min(best, score);
    }
    return best;
}

static int best_move(Board& b) {
    int move = -1, best = -2;
    for (int i = 0; i < 9; ++i) {
        if (b[i] != Cell::Empty) continue;
        b[i] = Cell::O;
        int s = minimax(b, false);
        b[i] = Cell::Empty;
        if (s > best) { best = s; move = i; }
    }
    return move;
}

static void draw(const Board& b) {
    for (int r = 0; r < 3; ++r) {
        std::cout << ' ';
        for (int c = 0; c < 3; ++c) {
            Cell x = b[r * 3 + c];
            std::cout << (x == Cell::Empty ? static_cast<char>('1' + r * 3 + c) : static_cast<char>(x)) << (c < 2 ? " | " : "");
        }
        std::cout << (r < 2 ? "\n---+---+---\n" : "\n");
    }
}

int main() {
    Board b;
    b.fill(Cell::Empty);
    std::cout << "You are X. The AI is O.\n";
    while (true) {
        draw(b);
        int pos = 0;
        std::cout << "Your move (1-9): ";
        if (!(std::cin >> pos)) return 0;
        if (pos < 1 || pos > 9 || b[pos - 1] != Cell::Empty) { std::cout << "Invalid.\n"; continue; }
        b[pos - 1] = Cell::X;
        if (winner(b) == Cell::X || full(b)) break;
        b[best_move(b)] = Cell::O;
        if (winner(b) == Cell::O || full(b)) break;
    }
    draw(b);
    Cell w = winner(b);
    std::cout << (w == Cell::X ? "You win!" : w == Cell::O ? "AI wins." : "Draw.") << '\n';
}
