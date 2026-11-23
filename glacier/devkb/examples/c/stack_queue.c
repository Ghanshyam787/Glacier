/* NAME: stack_queue
   DESC: Array-based stack and circular queue plus balanced-parentheses checker.
   KEYWORDS: stack, queue, circular queue, push, pop, enqueue, dequeue, parentheses, balanced, array, data structure */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define CAP 64

typedef struct { int data[CAP]; int top; } Stack;
typedef struct { int data[CAP]; int head, size; } Queue;

static void stack_init(Stack *s) { s->top = 0; }
static bool stack_push(Stack *s, int v) { if (s->top == CAP) return false; s->data[s->top++] = v; return true; }
static bool stack_pop(Stack *s, int *v) { if (s->top == 0) return false; *v = s->data[--s->top]; return true; }

static void queue_init(Queue *q) { q->head = q->size = 0; }
static bool enqueue(Queue *q, int v) { if (q->size == CAP) return false; q->data[(q->head + q->size++) % CAP] = v; return true; }
static bool dequeue(Queue *q, int *v) { if (q->size == 0) return false; *v = q->data[q->head]; q->head = (q->head + 1) % CAP; q->size--; return true; }

static bool balanced(const char *s) {
    Stack st; stack_init(&st);
    for (; *s; s++) {
        if (*s == '(' || *s == '[' || *s == '{') { if (!stack_push(&st, *s)) return false; }
        else if (*s == ')' || *s == ']' || *s == '}') {
            int open;
            if (!stack_pop(&st, &open)) return false;
            if ((*s == ')' && open != '(') || (*s == ']' && open != '[') || (*s == '}' && open != '{')) return false;
        }
    }
    return st.top == 0;
}

int main(void) {
    Stack s; stack_init(&s);
    for (int i = 1; i <= 3; i++) stack_push(&s, i * 10);
    int v;
    printf("Stack pops:");
    while (stack_pop(&s, &v)) printf(" %d", v);
    printf("\n");

    Queue q; queue_init(&q);
    for (int i = 1; i <= 3; i++) enqueue(&q, i * 100);
    printf("Queue dequeues:");
    while (dequeue(&q, &v)) printf(" %d", v);
    printf("\n");

    const char *tests[] = {"{[()]}", "(]", "((())", "a(b)c[d]"};
    for (size_t i = 0; i < sizeof tests / sizeof *tests; i++)
        printf("%-10s -> %s\n", tests[i], balanced(tests[i]) ? "balanced" : "NOT balanced");
    return 0;
}
