/* NAME: matrix
   DESC: Dynamic 2D matrices: create, fill, add, multiply, transpose, print, free.
   KEYWORDS: matrix, 2d array, dynamic memory, malloc, multiplication, transpose, struct, calloc */
#include <stdio.h>
#include <stdlib.h>

typedef struct { int rows, cols; double *data; } Matrix;

static Matrix mat_new(int rows, int cols) {
    Matrix m = {rows, cols, calloc((size_t)rows * (size_t)cols, sizeof(double))};
    if (!m.data) { perror("calloc"); exit(EXIT_FAILURE); }
    return m;
}
static double *at(Matrix m, int r, int c) { return &m.data[(size_t)r * (size_t)m.cols + (size_t)c]; }
static void mat_free(Matrix *m) { free(m->data); m->data = NULL; }

static int mat_add(Matrix a, Matrix b, Matrix *out) {
    if (a.rows != b.rows || a.cols != b.cols) return 0;
    *out = mat_new(a.rows, a.cols);
    for (int i = 0; i < a.rows; i++) for (int j = 0; j < a.cols; j++) *at(*out, i, j) = *at(a, i, j) + *at(b, i, j);
    return 1;
}

static int mat_mul(Matrix a, Matrix b, Matrix *out) {
    if (a.cols != b.rows) return 0;
    *out = mat_new(a.rows, b.cols);
    for (int i = 0; i < a.rows; i++)
        for (int j = 0; j < b.cols; j++) {
            double s = 0;
            for (int k = 0; k < a.cols; k++) s += *at(a, i, k) * *at(b, k, j);
            *at(*out, i, j) = s;
        }
    return 1;
}

static Matrix mat_transpose(Matrix a) {
    Matrix t = mat_new(a.cols, a.rows);
    for (int i = 0; i < a.rows; i++) for (int j = 0; j < a.cols; j++) *at(t, j, i) = *at(a, i, j);
    return t;
}

static void mat_print(const char *title, Matrix m) {
    printf("%s (%dx%d)\n", title, m.rows, m.cols);
    for (int i = 0; i < m.rows; i++) {
        for (int j = 0; j < m.cols; j++) printf("%8.2f", *at(m, i, j));
        printf("\n");
    }
}

int main(void) {
    Matrix a = mat_new(2, 3), b = mat_new(3, 2), sum = {0}, prod = {0};
    for (int i = 0; i < 2; i++) for (int j = 0; j < 3; j++) *at(a, i, j) = i + j + 1;
    for (int i = 0; i < 3; i++) for (int j = 0; j < 2; j++) *at(b, i, j) = i * 2 - j;
    mat_print("A", a);
    mat_print("B", b);
    if (mat_mul(a, b, &prod)) mat_print("A x B", prod);
    Matrix at_ = mat_transpose(a);
    mat_print("A^T", at_);
    if (!mat_add(a, b, &sum)) puts("A + B: dimensions do not match");
    mat_free(&a); mat_free(&b); mat_free(&prod); mat_free(&at_);
    return 0;
}
