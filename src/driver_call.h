#ifndef FERQON_DRIVER_CALL_H
#define FERQON_DRIVER_CALL_H

#include <stdint.h>
#include <stdbool.h>

/* Argument pair for driver_call args parser */
typedef struct {
    const char *key;
    const char *value;
} dc_arg_t;

/* Parse semicolon-delimited key=value pairs.
 * Returns: number of pairs found (>=0), or -1 on malformed input.
 * Behavior for malformed strings:
 *   - Missing '=' in a segment → return -1 (malformed)
 *   - Empty segment (double semicolon) → skip silently
 *   - Trailing semicolon → skip silently
 *   - Value contains semicolon → allowed ONLY for the last key
 *   - Key longer than 31 chars → return -1 (buffer overflow guard)
 *   - Empty key or empty value → return -1 (malformed)
 */
int driver_call_parse_args(const char *args, dc_arg_t *out, uint8_t max_args);

/* Look up an argument by key in the parsed args array.
 * Returns NULL if not found.
 */
const char *driver_call_get_arg(const dc_arg_t *args, int count, const char *key);

#endif /* FERQON_DRIVER_CALL_H */
