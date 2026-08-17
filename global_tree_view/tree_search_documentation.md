# Tree Search — Global Tree View

This document covers the **Tree Search** feature of the **Global Tree View** app for Frappe/ERPNext. It contains two main parts:

1. **API Endpoint** (`api/tree_search.py`) — A whitelisted API that overrides the standard Frappe link search to show full hierarchical paths in search results.
2. **Doctype Configuration** (`doctype/tree_search_setting/tree_search_setting.json`) — A **Single** DocType that stores user-configurable options for the feature.

---

## 1. API — `api/tree_search.py`

**File:** `global_tree_view/api/tree_search.py`

### Purpose

The module provides a drop-in override for Frappe's built-in `search_link` endpoint. When active, it intercepts link-field searches and:

- Builds the **full tree path** for each matching leaf node (e.g., `Root Category -> Level 1 -> Subcategory`).
- Returns these paths as the search suggestion **description**, enabling users to see the entire hierarchy at a glance.
- Falls back to the original Frappe search if the feature is disabled, the target DocType is ignored, or the DocType is not a tree.

### Function

#### `search_link(...)`

```python
@frappe.whitelist()
def search_link(
    doctype: str,
    txt: str,
    query: str | None = None,
    filters: str | dict | list | None = None,
    page_length: int = 20,
    searchfield: str | None = None,
    reference_doctype: str | None = None,
    ignore_user_permissions: bool = False,
    *,
    link_fieldname: str | None = None,
    start: int = 0,
)
```

**Returns:** A JSON structure (via `build_for_autosuggest`) containing `[(value, description), ...]`.

#### Workflow

1. **Load Settings** — Attempts to fetch a cached copy of the `"Tree Search Setting"` Single DocType. If missing or inactive, it falls back to the original `search_link`.

2. **Ignore Check** — If the current Doctype is in the setting's `ignore_doctypes` table, it also falls back.

3. **Permission Handling** — If `ignore_user_permissions` is enabled in settings, all database queries ignore permissions.

4. **Tree Detection** — Uses `frappe.get_meta(doctype)` to check if `meta.is_tree` is `True`. If not, falls back.

5. **Parent Field Discovery** — Scans fields for a `Link` field that points to the same Doctype (the parent field). If none is found, it tries a convention-based fallback: `parent_{scrubbed_doctype_name}`.

6. **Filter Building** — Merges the user-provided filters. Group nodes are not filtered out by default, allowing them to be shown when not explicitly excluded by the link field filters.

7. **Data Loading** — Fetches all nodes (limited to 10,000) to build an in-memory parent map, plus the target nodes matching the filters.

8. **Path Construction** — For each matching target node, traverses the parent map upward to build the full path:
   - Optionally **removes the company abbreviation** (e.g., `My Account - AB` → `My Account`) if the setting is enabled.
   - Optionally **hides the child node itself** (only shows ancestors) if `show_child_node` is disabled.
   - **Truncates** the path to the last N levels if `maximum_tree_levels` is set (>0). A `"..."` prefix is added when truncated.
   - Uses the configured **separator** (default ` -> `) to join path parts.
   - Appends a ` (Group)` suffix to the final path if the target node itself is a group.

9. **Filtering & Pagination** — Keeps only results where the full path (case-insensitively) contains the search text (`txt`). Sorts by name, then paginates via `start` and `page_length`.

10. **Error Handling** — Any exception during the custom logic is logged via `frappe.log_error` and triggers a clean fallback to the original `search_link`.

---

## 2. DocType — `Tree Search Setting`

**File:** `global_tree_view/global_tree_view/doctype/tree_search_setting/tree_search_setting.json`

A **Single** (settings) DocType, editable only by **System Manager**.

### Fields

| Field                         | Type       | Default       | Description |
|-------------------------------|------------|---------------|-------------|
| `active`                      | Check      | 1             | Master switch for the tree search override. When unchecked, the default Frappe link search is used for all doctypes. |
| `separator`                   | Data       | ` -> `        | The string used to join hierarchy levels in the display path (e.g., `Root -> Child -> Leaf`). |
| `maximum_tree_levels`         | Int        | 0             | Maximum number of ancestor levels to show. `0` means unlimited. Paths longer than this value will be truncated from the left (oldest ancestors removed). |
| `show_child_node`             | Check      | 1             | If enabled, the leaf (child) node name is included as the last part of the path. If disabled, only ancestor levels are shown. |
| `remove_company_abbreviation` | Check      | 0             | If enabled, strips the company abbreviation suffix (e.g., ` - AB`) from each node name in the path. The pattern expects `" - "` followed by 2–5 uppercase letters at the end of the name. |
| `ignore_user_permissions`     | Check      | 0             | If enabled, all database queries inside the tree search logic ignore user permissions. |
| `ignore_doctypes`             | Table (child) | —          | A child table (`Tree Search Ignore Doctype`) listing DocTypes for which the tree search override should **not** apply. Each row has a single field: `doctype_to_ignore` (Link → DocType). |

### Permissions

- Only the **System Manager** role can Create, Read, Write, and Share this single document.
- No custom actions or links are configured.

### Child Table — `Tree Search Ignore Doctype`

The child table (not defined within this JSON) is expected to contain a single Link field `doctype_to_ignore` linking to the `DocType` doctype. It allows users to exclude specific tree doctypes from the override.

---

## 3. Usage Example

1. Navigate to **Global Tree View > Tree Search Setting** (only visible to System Manager).
2. Check **Active** and configure the separator, levels, and other options.
3. When a user clicks on a **Link** field pointing to a **tree Doctype** (e.g., Account, Cost Center, Warehouse), the search dropdown will now show:
   - The node name as the **value**
   - The full hierarchical path (e.g., `Root -> United States -> California -> San Francisco`) as the **description**

---

## 4. Fallback Conditions

The custom behavior is bypassed (falling back to the original `search_link`) under any of these conditions:

- The `Tree Search Setting` document **does not exist** (or fails to load).
- The setting has **Active** unchecked.
- The target Doctype is listed in **Ignore Doctypes**.
- The target Doctype is **not a tree** (`is_tree` is false/not set).
- An **exception** occurs during path building (logged as "Tree Search Override Failed").
