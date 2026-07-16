# 📘 Global Tree View - Product Overview

## 👋 Introduction
Welcome to **Global Tree View** (global-tree-search) for Frappe and ERPNext — built and maintained by **Invento Software Limited**.

In Frappe/ERPNext, selection inputs for tree structures (such as the Chart of Accounts, Warehouse Locations, Customer/Supplier Groups, and Departments) default to showing only the final node name. This can be confusing for organizations with deep hierarchies, duplicate node names across branches, or complex nested structures.

**Global Tree View** intercepts and enhances link field searches across the Frappe Desk. When a user queries a tree DocType, the search suggestion description is enriched to display the entire ancestral path leading to the node (e.g. `All Territories -> Americas -> North America -> United States`).

---

## 👥 Target Audience
This application is designed for medium-to-large enterprises, multi-company setups, and systems administrators who want to streamline data entry and reduce selection errors in hierarchical link fields.

### Key Users
*   **Accountants & Finance Managers**: Easily select specific accounts in journals or invoices by viewing the full Chart of Accounts lineage.
*   **Warehouse Managers**: Differentiate identical rack or bin names across different physical warehouses.
*   **HR Managers**: Seamlessly navigate nested departments and cost centers.
*   **Frappe/ERPNext Administrators**: Configure system-wide search settings from a single, unified interface.

---

## 🛠️ Features & Capabilities

### 🔗 Whitelisted Link Search Override
*   Automatically hooks into the standard whitelisted method `frappe.desk.search.search_link`.
*   Directly resolves queries via `global_tree_view.api.tree_search.search_link` without modifying core Frappe code.
*   Detects if the target DocType is a tree (`is_tree = 1`) and resolves parent fields dynamically.

### ⚙️ Centralized Settings Control
All settings are stored in a single, secure DocType: `Tree Search Setting`.

#### 1. Master Activation Switch
*   Quickly enable or disable the override globally. When disabled, the search falls back to Frappe's default mechanism immediately.

#### 2. Customizable Path Separator
*   Change the join character between path levels (default is ` -> `). Customize it to `/`, `>`, or any custom string.

#### 3. Ancestor Level Truncation
*   Specify a maximum level of ancestors to display (e.g., set to `2` to only show parent and grandparent). Longer paths are elegantly prefixed with `...`.

#### 4. Company Abbreviation Suffix Removal
*   Automatically strips the trailing company suffix (e.g., ` - AB` or ` - COMP`) from node names for cleaner, more readable paths.

#### 5. User Permissions Bypass
*   Optionally query the database bypassing user permissions if users lack read permission on top-level root groups but need to see path lineage to select leaf nodes.

#### 6. Dynamic Ignore List
*   Add specific DocTypes to an ignore table to use standard Frappe search behavior for those types, while keeping the override active for others.

---

## 🔒 Safe Fallback Mechanism
Global Tree View is built with stability in mind. The whitelisted endpoint automatically returns to standard search suggestions under any of the following conditions:
*   The `Tree Search Setting` DocType is not active.
*   The target DocType is explicitly configured in the ignore list.
*   The target DocType is not marked as a tree in metadata.
*   An unexpected error occurs (logged as an error log in Frappe for investigation).
