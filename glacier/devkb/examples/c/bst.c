/* NAME: bst
   DESC: Binary search tree: insert, search, delete, inorder/preorder, height, free.
   KEYWORDS: binary search tree, bst, tree, recursion, inorder, delete node, height, data structure */
#include <stdio.h>
#include <stdlib.h>

typedef struct Tree { int key; struct Tree *left, *right; } Tree;

static Tree *insert(Tree *t, int key) {
    if (!t) {
        t = malloc(sizeof *t);
        if (!t) { perror("malloc"); exit(EXIT_FAILURE); }
        t->key = key; t->left = t->right = NULL;
        return t;
    }
    if (key < t->key) t->left = insert(t->left, key);
    else if (key > t->key) t->right = insert(t->right, key);
    return t;
}

static const Tree *find(const Tree *t, int key) {
    while (t && t->key != key) t = key < t->key ? t->left : t->right;
    return t;
}

static Tree *min_node(Tree *t) { while (t->left) t = t->left; return t; }

static Tree *remove_key(Tree *t, int key) {
    if (!t) return NULL;
    if (key < t->key) t->left = remove_key(t->left, key);
    else if (key > t->key) t->right = remove_key(t->right, key);
    else {
        if (!t->left || !t->right) {
            Tree *child = t->left ? t->left : t->right;
            free(t);
            return child;
        }
        Tree *m = min_node(t->right);
        t->key = m->key;
        t->right = remove_key(t->right, m->key);
    }
    return t;
}

static int height(const Tree *t) {
    if (!t) return 0;
    int l = height(t->left), r = height(t->right);
    return 1 + (l > r ? l : r);
}

static void inorder(const Tree *t) { if (t) { inorder(t->left); printf("%d ", t->key); inorder(t->right); } }
static void preorder(const Tree *t) { if (t) { printf("%d ", t->key); preorder(t->left); preorder(t->right); } }
static void destroy(Tree *t) { if (t) { destroy(t->left); destroy(t->right); free(t); } }

int main(void) {
    Tree *root = NULL;
    int keys[] = {50, 30, 70, 20, 40, 60, 80, 35};
    for (size_t i = 0; i < sizeof keys / sizeof *keys; i++) root = insert(root, keys[i]);
    printf("Inorder:  "); inorder(root); printf("\n");
    printf("Preorder: "); preorder(root); printf("\n");
    printf("Height: %d\n", height(root));
    printf("Find 60: %s, find 65: %s\n", find(root, 60) ? "yes" : "no", find(root, 65) ? "yes" : "no");
    root = remove_key(root, 30);
    printf("After deleting 30: "); inorder(root); printf("\n");
    destroy(root);
    return 0;
}
