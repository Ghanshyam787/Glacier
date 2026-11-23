/* NAME: calculator
   DESC: Expression calculator using a recursive-descent parser: + - * / ^ parentheses, unary minus, decimals, error handling.
   KEYWORDS: calculator, expression parser, recursive descent, parsing, math, evaluate, operator precedence, project */
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { const char *p; int error; } Parser;

static double expr(Parser *ps);

static void skip(Parser *ps) { while (isspace((unsigned char)*ps->p)) ps->p++; }

static double primary(Parser *ps) {
    skip(ps);
    if (*ps->p == '(') {
        ps->p++;
        double v = expr(ps);
        skip(ps);
        if (*ps->p != ')') { ps->error = 1; return 0; }
        ps->p++;
        return v;
    }
    char *end;
    double v = strtod(ps->p, &end);
    if (end == ps->p) { ps->error = 1; return 0; }
    ps->p = end;
    return v;
}

static double unary(Parser *ps) {
    skip(ps);
    if (*ps->p == '-') { ps->p++; return -unary(ps); }
    if (*ps->p == '+') { ps->p++; return unary(ps); }
    return primary(ps);
}

static double power(Parser *ps) {
    double base = unary(ps);
    skip(ps);
    if (*ps->p == '^') { ps->p++; return pow(base, power(ps)); }
    return base;
}

static double term(Parser *ps) {
    double v = power(ps);
    for (;;) {
        skip(ps);
        if (*ps->p == '*') { ps->p++; v *= power(ps); }
        else if (*ps->p == '/') {
            ps->p++;
            double d = power(ps);
            if (d == 0) { ps->error = 2; return 0; }
            v /= d;
        } else return v;
    }
}

static double expr(Parser *ps) {
    double v = term(ps);
    for (;;) {
        skip(ps);
        if (*ps->p == '+') { ps->p++; v += term(ps); }
        else if (*ps->p == '-') { ps->p++; v -= term(ps); }
        else return v;
    }
}

int main(void) {
    char line[256];
    puts("Enter an expression (blank line to quit), e.g. 2 + 3 * (4 - 1) ^ 2");
    while (printf("> "), fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (!line[0]) break;
        Parser ps = {line, 0};
        double v = expr(&ps);
        skip(&ps);
        if (ps.error == 2) puts("Error: division by zero");
        else if (ps.error || *ps.p) puts("Error: invalid expression");
        else printf("= %.10g\n", v);
    }
    return 0;
}
