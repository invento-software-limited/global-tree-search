# ADR 002: Implement Feature: FIX [36628d7]: fix: support advanced filter operators and prevent SQL syntax errors with empty IN clauses

Date: 2026-10-08
Status: Accepted

## Context
The existing filter parsing mechanism within the `_search_link_impl` function only supported simple equality (`=`) operations when processing filter parameters. This limitation restricted the ability of users and developers to construct advanced search queries using a wider range of comparison operators such as `IN`, `NOT IN`, `LIKE`, `NOT LIKE`, `!=`, `>`, `<`, `>=`, `<=`, `BETWEEN`, or `IS`.

Furthermore, a critical issue existed where dynamically generated SQL `IN` clauses could lead to syntax errors if the list of values provided for the `IN` operator was empty (e.g., `WHERE field IN ()`). This would result in runtime exceptions and disrupt application functionality. The need arose to both expand filter capabilities and fortify the system against these specific SQL errors.

## Decision
The `_search_link_impl` function in `global_tree_view/api/tree_search.py` has been modified to support advanced filter operators and prevent SQL syntax errors for empty `IN` clauses.

The specific decisions made are:
1.  **Operator Recognition:** When processing filter values (`v`), if `v` is a two-element list or tuple, where the first element (`v[0]`) is a string matching a predefined set of common SQL operators (e.g., "in", "not in", "like", "!=", ">", "<", ">=", "<=", "between", "is"), then `v[0]` is treated as the operator and `v[1]` as the value. The filter is then parsed as `[doctype, k, v[0], v[1]]`. Otherwise, it defaults to the equality operator `[doctype, k, "=", v]`.
2.  **Empty `IN` Clause Mitigation:** A specific conditional check was added for the `IN` operator. If `v[0]` is "in" (case-insensitive) and `v[1]` is an empty list or tuple, the filter is transformed into `[doctype, k, "=", "__NO_MATCH__"]`. This prevents the generation of invalid SQL (`WHERE field IN ()`) by creating a condition that will never match, effectively achieving the desired "no results" outcome without causing a syntax error.

This logic has been applied consistently for both dictionary-based filters and list-of-dictionary/tuple-based filters.

## Consequences
- **Benefits:**
  - **Enhanced Filtering Capabilities:** Users and developers can now leverage a comprehensive set of SQL comparison operators, enabling more precise and powerful search and filtering functionalities.
  - **Increased Application Robustness:** The explicit handling of empty `IN` clauses eliminates a significant source of potential SQL syntax errors, improving the stability and reliability of the application's data querying.
  - **Improved User Experience:** More granular control over search parameters leads to better and more relevant search results for end-users.
- **Trade-offs / Risks:**
  - **Increased Code Complexity:** The filter parsing logic within `_search_link_impl` has become more intricate due to the additional conditional checks and operator handling. This might slightly increase the cognitive load for future maintenance and debugging.
  - **Implicit API Contract:** The system now implicitly understands certain string values as SQL operators. While these are standard, this introduces an implicit contract for filter input that must be well-documented for developers consuming this API.
