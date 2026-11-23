/* NAME: hash_table
   DESC: Hash table with separate chaining (string key -> int), resize-free simple version: put, get, delete, free.
   KEYWORDS: hash table, hash map, dictionary, chaining, djb2, string key, collision, data structure */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUCKETS 64

typedef struct Entry { char *key; int value; struct Entry *next; } Entry;
typedef struct { Entry *slot[BUCKETS]; } Table;

static unsigned long hash(const char *s) {
    unsigned long h = 5381;
    for (; *s; s++) h = h * 33 + (unsigned char)*s;
    return h;
}

static char *dup_str(const char *s) {
    size_t n = strlen(s) + 1;
    char *p = malloc(n);
    if (!p) { perror("malloc"); exit(EXIT_FAILURE); }
    memcpy(p, s, n);
    return p;
}

static void put(Table *t, const char *key, int value) {
    size_t i = hash(key) % BUCKETS;
    for (Entry *e = t->slot[i]; e; e = e->next)
        if (strcmp(e->key, key) == 0) { e->value = value; return; }
    Entry *e = malloc(sizeof *e);
    if (!e) { perror("malloc"); exit(EXIT_FAILURE); }
    e->key = dup_str(key);
    e->value = value;
    e->next = t->slot[i];
    t->slot[i] = e;
}

static int get(const Table *t, const char *key, int *out) {
    for (const Entry *e = t->slot[hash(key) % BUCKETS]; e; e = e->next)
        if (strcmp(e->key, key) == 0) { *out = e->value; return 1; }
    return 0;
}

static int del(Table *t, const char *key) {
    for (Entry **cur = &t->slot[hash(key) % BUCKETS]; *cur; cur = &(*cur)->next) {
        if (strcmp((*cur)->key, key) == 0) {
            Entry *dead = *cur;
            *cur = dead->next;
            free(dead->key);
            free(dead);
            return 1;
        }
    }
    return 0;
}

static void destroy(Table *t) {
    for (size_t i = 0; i < BUCKETS; i++) {
        Entry *e = t->slot[i];
        while (e) { Entry *n = e->next; free(e->key); free(e); e = n; }
        t->slot[i] = NULL;
    }
}

int main(void) {
    Table t = {0};
    put(&t, "apple", 3); put(&t, "banana", 5); put(&t, "cherry", 7); put(&t, "apple", 10);
    const char *keys[] = {"apple", "banana", "cherry", "durian"};
    for (size_t i = 0; i < 4; i++) {
        int v;
        if (get(&t, keys[i], &v)) printf("%s = %d\n", keys[i], v);
        else printf("%s not found\n", keys[i]);
    }
    printf("delete banana: %s\n", del(&t, "banana") ? "ok" : "missing");
    int v;
    printf("banana now %s\n", get(&t, "banana", &v) ? "present" : "absent");
    destroy(&t);
    return 0;
}
