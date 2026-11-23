/* NAME: student_db
   DESC: Student management system with binary file storage: add, list, search by roll, update, delete. Safe input with fgets.
   KEYWORDS: student management, record, file handling, fopen, fread, fwrite, binary file, crud, database, struct, menu, project */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DB_FILE "students.dat"
#define NAME_LEN 50

typedef struct {
    int roll;
    char name[NAME_LEN];
    float marks;
} Student;

static void read_line(const char *prompt, char *buf, size_t size) {
    printf("%s", prompt);
    if (!fgets(buf, (int)size, stdin)) { buf[0] = '\0'; return; }
    buf[strcspn(buf, "\r\n")] = '\0';
}

static int read_int(const char *prompt) {
    char line[32];
    read_line(prompt, line, sizeof line);
    return (int)strtol(line, NULL, 10);
}

static float read_float(const char *prompt) {
    char line[32];
    read_line(prompt, line, sizeof line);
    return strtof(line, NULL);
}

static int load_all(Student **out, size_t *count) {
    *out = NULL; *count = 0;
    FILE *f = fopen(DB_FILE, "rb");
    if (!f) return 1;                       /* no file yet = empty database */
    Student s;
    while (fread(&s, sizeof s, 1, f) == 1) {
        Student *tmp = realloc(*out, (*count + 1) * sizeof **out);
        if (!tmp) { free(*out); fclose(f); return 0; }
        *out = tmp;
        (*out)[(*count)++] = s;
    }
    fclose(f);
    return 1;
}

static int save_all(const Student *list, size_t count) {
    FILE *f = fopen(DB_FILE, "wb");
    if (!f) { perror("fopen"); return 0; }
    int ok = count == 0 || fwrite(list, sizeof *list, count, f) == count;
    fclose(f);
    return ok;
}

static void add_student(void) {
    Student s;
    s.roll = read_int("Roll no: ");
    read_line("Name: ", s.name, sizeof s.name);
    s.marks = read_float("Marks: ");
    Student *list; size_t n;
    if (!load_all(&list, &n)) { puts("Memory error."); return; }
    for (size_t i = 0; i < n; i++)
        if (list[i].roll == s.roll) { puts("Roll number already exists."); free(list); return; }
    Student *tmp = realloc(list, (n + 1) * sizeof *list);
    if (!tmp) { free(list); puts("Memory error."); return; }
    list = tmp; list[n++] = s;
    puts(save_all(list, n) ? "Saved." : "Could not save.");
    free(list);
}

static void list_students(void) {
    Student *list; size_t n;
    if (!load_all(&list, &n)) return;
    if (n == 0) puts("No records.");
    else {
        printf("%-6s %-20s %s\n", "Roll", "Name", "Marks");
        for (size_t i = 0; i < n; i++) printf("%-6d %-20s %.2f\n", list[i].roll, list[i].name, list[i].marks);
    }
    free(list);
}

static void search_student(void) {
    int roll = read_int("Roll to search: ");
    Student *list; size_t n;
    if (!load_all(&list, &n)) return;
    int found = 0;
    for (size_t i = 0; i < n; i++)
        if (list[i].roll == roll) { printf("%d | %s | %.2f\n", list[i].roll, list[i].name, list[i].marks); found = 1; }
    if (!found) puts("Not found.");
    free(list);
}

static void update_student(void) {
    int roll = read_int("Roll to update: ");
    Student *list; size_t n;
    if (!load_all(&list, &n)) return;
    for (size_t i = 0; i < n; i++) {
        if (list[i].roll == roll) {
            read_line("New name: ", list[i].name, sizeof list[i].name);
            list[i].marks = read_float("New marks: ");
            puts(save_all(list, n) ? "Updated." : "Could not save.");
            free(list);
            return;
        }
    }
    puts("Not found.");
    free(list);
}

static void delete_student(void) {
    int roll = read_int("Roll to delete: ");
    Student *list; size_t n;
    if (!load_all(&list, &n)) return;
    size_t keep = 0;
    for (size_t i = 0; i < n; i++) if (list[i].roll != roll) list[keep++] = list[i];
    if (keep == n) puts("Not found.");
    else puts(save_all(list, keep) ? "Deleted." : "Could not save.");
    free(list);
}

int main(void) {
    for (;;) {
        puts("\n=== Student Management ===\n1 Add  2 List  3 Search  4 Update  5 Delete  0 Exit");
        switch (read_int("Choice: ")) {
            case 1: add_student(); break;
            case 2: list_students(); break;
            case 3: search_student(); break;
            case 4: update_student(); break;
            case 5: delete_student(); break;
            case 0: return 0;
            default: puts("Invalid choice.");
        }
    }
}
