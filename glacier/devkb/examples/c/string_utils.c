/* NAME: string_utils
   DESC: Safe string helpers: reverse, palindrome, word count, trim, to upper, split by delimiter, strtol parsing.
   KEYWORDS: string, strings, reverse, palindrome, word count, trim, toupper, strtok, tokenize, char array, safe, snprintf */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void reverse(char *s) {
    size_t n = strlen(s);
    for (size_t i = 0; i < n / 2; i++) { char t = s[i]; s[i] = s[n - 1 - i]; s[n - 1 - i] = t; }
}

static int is_palindrome(const char *s) {
    size_t i = 0, j = strlen(s);
    while (i < j) {
        while (i < j && !isalnum((unsigned char)s[i])) i++;
        while (i < j && !isalnum((unsigned char)s[j - 1])) j--;
        if (i >= j) break;
        if (tolower((unsigned char)s[i]) != tolower((unsigned char)s[j - 1])) return 0;
        i++; j--;
    }
    return 1;
}

static int word_count(const char *s) {
    int count = 0, in_word = 0;
    for (; *s; s++) {
        if (isspace((unsigned char)*s)) in_word = 0;
        else if (!in_word) { in_word = 1; count++; }
    }
    return count;
}

static char *trim(char *s) {
    while (isspace((unsigned char)*s)) s++;
    char *end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1])) end--;
    *end = '\0';
    return s;
}

static void to_upper(char *s) { for (; *s; s++) *s = (char)toupper((unsigned char)*s); }

int main(void) {
    char text[] = "  A man, a plan, a canal: Panama  ";
    char *t = trim(text);
    printf("trimmed   : '%s'\n", t);
    printf("palindrome: %s\n", is_palindrome(t) ? "yes" : "no");
    printf("words     : %d\n", word_count(t));

    char word[32];
    snprintf(word, sizeof word, "%s", "glacier");
    reverse(word);
    printf("reversed  : %s\n", word);
    to_upper(word);
    printf("upper     : %s\n", word);

    char csv[] = "red,green,blue";
    printf("split     :");
    for (char *tok = strtok(csv, ","); tok; tok = strtok(NULL, ",")) printf(" [%s]", tok);
    printf("\n");

    const char *num = "1234xyz";
    char *end;
    long v = strtol(num, &end, 10);
    printf("strtol    : value=%ld, rest='%s'\n", v, end);
    return 0;
}
