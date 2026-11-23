/* NAME: tictactoe
   DESC: Two-player console Tic-Tac-Toe with input validation and win/draw detection.
   KEYWORDS: tic tac toe, game, board, 2d array, console game, input validation, project */
#include <stdio.h>
#include <stdlib.h>

static char board[3][3];

static void reset(void) {
    for (int r = 0; r < 3; r++) for (int c = 0; c < 3; c++) board[r][c] = (char)('1' + r * 3 + c);
}

static void draw(void) {
    printf("\n");
    for (int r = 0; r < 3; r++) {
        printf(" %c | %c | %c\n", board[r][0], board[r][1], board[r][2]);
        if (r < 2) printf("---+---+---\n");
    }
    printf("\n");
}

static char winner(void) {
    for (int i = 0; i < 3; i++) {
        if (board[i][0] == board[i][1] && board[i][1] == board[i][2]) return board[i][0];
        if (board[0][i] == board[1][i] && board[1][i] == board[2][i]) return board[0][i];
    }
    if (board[0][0] == board[1][1] && board[1][1] == board[2][2]) return board[0][0];
    if (board[0][2] == board[1][1] && board[1][1] == board[2][0]) return board[0][2];
    return 0;
}

int main(void) {
    reset();
    char player = 'X';
    for (int moves = 0; moves < 9; moves++) {
        draw();
        for (;;) {
            char line[16];
            printf("Player %c, choose 1-9: ", player);
            if (!fgets(line, sizeof line, stdin)) return 0;
            int cell = atoi(line);
            if (cell >= 1 && cell <= 9 && board[(cell - 1) / 3][(cell - 1) % 3] == (char)('0' + cell)) {
                board[(cell - 1) / 3][(cell - 1) % 3] = player;
                break;
            }
            puts("Invalid or taken. Try again.");
        }
        char w = winner();
        if (w) { draw(); printf("Player %c wins!\n", w); return 0; }
        player = player == 'X' ? 'O' : 'X';
    }
    draw();
    puts("It's a draw.");
    return 0;
}
