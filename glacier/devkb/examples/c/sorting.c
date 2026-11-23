/* NAME: sorting
   DESC: Bubble, selection, insertion, merge and quick sort with timing on random data.
   KEYWORDS: sorting, bubble sort, selection sort, insertion sort, merge sort, quick sort, algorithm, complexity, recursion, qsort */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void swap(int *a, int *b) { int t = *a; *a = *b; *b = t; }

static void bubble(int *a, int n) {
    for (int i = 0; i < n - 1; i++) {
        int swapped = 0;
        for (int j = 0; j < n - 1 - i; j++)
            if (a[j] > a[j + 1]) { swap(&a[j], &a[j + 1]); swapped = 1; }
        if (!swapped) break;
    }
}

static void selection(int *a, int n) {
    for (int i = 0; i < n - 1; i++) {
        int m = i;
        for (int j = i + 1; j < n; j++) if (a[j] < a[m]) m = j;
        if (m != i) swap(&a[i], &a[m]);
    }
}

static void insertion(int *a, int n) {
    for (int i = 1; i < n; i++) {
        int key = a[i], j = i - 1;
        while (j >= 0 && a[j] > key) { a[j + 1] = a[j]; j--; }
        a[j + 1] = key;
    }
}

static void merge_sort(int *a, int *tmp, int lo, int hi) {
    if (hi - lo < 1) return;
    int mid = lo + (hi - lo) / 2;
    merge_sort(a, tmp, lo, mid);
    merge_sort(a, tmp, mid + 1, hi);
    int i = lo, j = mid + 1, k = lo;
    while (i <= mid && j <= hi) tmp[k++] = a[i] <= a[j] ? a[i++] : a[j++];
    while (i <= mid) tmp[k++] = a[i++];
    while (j <= hi) tmp[k++] = a[j++];
    memcpy(a + lo, tmp + lo, (size_t)(hi - lo + 1) * sizeof *a);
}

static void quick(int *a, int lo, int hi) {
    while (lo < hi) {
        int pivot = a[lo + (hi - lo) / 2], i = lo, j = hi;
        while (i <= j) {
            while (a[i] < pivot) i++;
            while (a[j] > pivot) j--;
            if (i <= j) swap(&a[i++], &a[j--]);
        }
        if (j - lo < hi - i) { quick(a, lo, j); lo = i; }
        else { quick(a, i, hi); hi = j; }
    }
}

static int is_sorted(const int *a, int n) {
    for (int i = 1; i < n; i++) if (a[i - 1] > a[i]) return 0;
    return 1;
}

static void run(const char *name, void (*fn)(int *, int), const int *src, int n) {
    int *a = malloc((size_t)n * sizeof *a);
    if (!a) return;
    memcpy(a, src, (size_t)n * sizeof *a);
    clock_t t0 = clock();
    fn(a, n);
    double ms = 1000.0 * (double)(clock() - t0) / CLOCKS_PER_SEC;
    printf("%-10s %8.2f ms  %s\n", name, ms, is_sorted(a, n) ? "sorted" : "WRONG");
    free(a);
}

static void merge_wrap(int *a, int n) {
    int *tmp = malloc((size_t)n * sizeof *tmp);
    if (!tmp) return;
    merge_sort(a, tmp, 0, n - 1);
    free(tmp);
}
static void quick_wrap(int *a, int n) { quick(a, 0, n - 1); }

int main(void) {
    int n = 5000;
    int *data = malloc((size_t)n * sizeof *data);
    if (!data) return 1;
    srand(42);
    for (int i = 0; i < n; i++) data[i] = rand() % 100000;
    printf("Sorting %d random numbers\n", n);
    run("bubble", bubble, data, n);
    run("selection", selection, data, n);
    run("insertion", insertion, data, n);
    run("merge", merge_wrap, data, n);
    run("quick", quick_wrap, data, n);
    free(data);
    return 0;
}
