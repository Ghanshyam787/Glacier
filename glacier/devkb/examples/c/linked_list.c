/* NAME: linked_list
   DESC: Singly linked list with menu: insert front/back, delete by value, search, reverse, print, free all.
   KEYWORDS: linked list, node, pointer, malloc, free, reverse, singly, data structure, menu */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Node {
    int value;
    struct Node *next;
} Node;

static Node *node_new(int value) {
    Node *n = malloc(sizeof *n);
    if (!n) {
        perror("malloc");
        exit(EXIT_FAILURE);
    }
    n->value = value;
    n->next = NULL;
    return n;
}

static void push_front(Node **head, int value) {
    Node *n = node_new(value);
    n->next = *head;
    *head = n;
}

static void push_back(Node **head, int value) {
    Node *n = node_new(value);
    Node **cur = head;
    while (*cur) cur = &(*cur)->next;
    *cur = n;
}

static int remove_value(Node **head, int value) {
    for (Node **cur = head; *cur; cur = &(*cur)->next) {
        if ((*cur)->value == value) {
            Node *dead = *cur;
            *cur = dead->next;
            free(dead);
            return 1;
        }
    }
    return 0;
}

static int contains(const Node *head, int value) {
    for (; head; head = head->next)
        if (head->value == value) return 1;
    return 0;
}

static void reverse(Node **head) {
    Node *prev = NULL, *cur = *head;
    while (cur) {
        Node *next = cur->next;
        cur->next = prev;
        prev = cur;
        cur = next;
    }
    *head = prev;
}

static void print_list(const Node *head) {
    printf("[");
    for (; head; head = head->next) printf("%d%s", head->value, head->next ? " -> " : "");
    printf("]\n");
}

static void free_list(Node **head) {
    while (*head) {
        Node *next = (*head)->next;
        free(*head);
        *head = next;
    }
}

static int read_int(const char *prompt, int *out) {
    char line[64];
    printf("%s", prompt);
    if (!fgets(line, sizeof line, stdin)) return 0;
    char *end;
    long v = strtol(line, &end, 10);
    if (end == line) return 0;
    *out = (int)v;
    return 1;
}

int main(void) {
    Node *head = NULL;
    for (;;) {
        printf("\n1) Insert front  2) Insert back  3) Delete  4) Search  5) Reverse  6) Print  0) Exit\n");
        int choice, v;
        if (!read_int("Choice: ", &choice)) break;
        if (choice == 0) break;
        switch (choice) {
            case 1: if (read_int("Value: ", &v)) push_front(&head, v); break;
            case 2: if (read_int("Value: ", &v)) push_back(&head, v); break;
            case 3: if (read_int("Value: ", &v)) printf(remove_value(&head, v) ? "Deleted.\n" : "Not found.\n"); break;
            case 4: if (read_int("Value: ", &v)) printf(contains(head, v) ? "Found.\n" : "Not found.\n"); break;
            case 5: reverse(&head); puts("Reversed."); break;
            case 6: print_list(head); break;
            default: puts("Invalid choice.");
        }
    }
    free_list(&head);
    return 0;
}
