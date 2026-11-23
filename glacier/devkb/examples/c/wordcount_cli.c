/* NAME: wordcount_cli
   DESC: Command-line wc clone: counts lines, words, bytes for files given in argv (or stdin), with error handling.
   KEYWORDS: argc, argv, command line, wc, word count, file, stdin, getc, cli tool, fopen, error handling */
#include <ctype.h>
#include <stdio.h>

typedef struct { unsigned long lines, words, bytes; } Counts;

static int count_stream(FILE *f, Counts *c) {
    int ch, in_word = 0;
    c->lines = c->words = c->bytes = 0;
    while ((ch = getc(f)) != EOF) {
        c->bytes++;
        if (ch == '\n') c->lines++;
        if (isspace((unsigned char)ch)) in_word = 0;
        else if (!in_word) { in_word = 1; c->words++; }
    }
    return ferror(f) ? -1 : 0;
}

int main(int argc, char **argv) {
    Counts total = {0, 0, 0};
    int status = 0;
    if (argc == 1) {
        Counts c;
        if (count_stream(stdin, &c) != 0) { perror("stdin"); return 1; }
        printf("%7lu %7lu %7lu\n", c.lines, c.words, c.bytes);
        return 0;
    }
    for (int i = 1; i < argc; i++) {
        FILE *f = fopen(argv[i], "rb");
        if (!f) { perror(argv[i]); status = 1; continue; }
        Counts c;
        if (count_stream(f, &c) != 0) { perror(argv[i]); status = 1; }
        else {
            printf("%7lu %7lu %7lu %s\n", c.lines, c.words, c.bytes, argv[i]);
            total.lines += c.lines; total.words += c.words; total.bytes += c.bytes;
        }
        fclose(f);
    }
    if (argc > 2) printf("%7lu %7lu %7lu total\n", total.lines, total.words, total.bytes);
    return status;
}
