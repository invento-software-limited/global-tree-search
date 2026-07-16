# 📖 Global Tree View - User Guide

## 🏁 Getting Started

### Prerequisites
*   Frappe/ERPNext v15+ or newer instance with administrator access.
*   Administrative privileges (`System Manager` role) to modify the `Tree Search Setting` document.

---

### 🚀 Installation

Install the app using the Bench CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/invento-software-limited/global-tree-search --branch main
bench --site your-site.com install-app global_tree_view
```

After installation, run migration to initialize the settings DocType, and restart the server:

```bash
bench site your-site.com migrate
bench restart
```

---

## ⚙️ Configuration

To customize how hierarchical path suggestions appear, configure the settings:

### 1. Navigating to Settings
1.  Log into the Frappe/ERPNext Desk as a **System Manager**.
2.  Use the awesomebar (search bar) to look for **Tree Search Setting**.
3.  Click on the document to open it.

---

### 2. Configuration Fields Reference

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **Active** | Check | `1` (Checked) | Master switch. When unchecked, standard Frappe link search suggestions are displayed. |
| **Separator** | Data | ` -> ` | The character string used to join tree levels. E.g., `Root -> Parent -> Child`. |
| **Maximum Tree Levels** | Int | `0` | Limit the path depth. `0` means show full paths. A positive value (e.g. `2`) displays only the latest `N` levels (older ancestors are replaced by `...`). |
| **Show Child Node** | Check | `1` (Checked) | Include the leaf node itself at the end of the path. When unchecked, only ancestors are displayed. |
| **Remove Company Abbreviation** | Check | `0` (Unchecked) | Strip company abbreviations (e.g., ` - AB` or ` - COMP`) from node names for cleaner paths. |
| **Ignore User Permissions** | Check | `0` (Unchecked) | Ignore database permission checks when constructing ancestor trees. Useful if users lack access to root groups. |
| **Ignore Doctypes** | Table | None | A child table listing DocTypes to exclude from the custom path suggestions. |

---

### 3. Excluded DocTypes Setup (Ignore list)
If you want to disable hierarchical path formatting for specific tree doctypes (such as `Department` or `Asset Category`):
1.  Under **Ignore Doctypes**, click **Add Row**.
2.  Select the DocType you want to exclude (e.g., `Department`).
3.  Save the changes.

---

## 🎯 Usage Examples

### Example 1: Chart of Accounts
In a default ERPNext setup, search suggestions for an Account (a tree DocType) look like this:
*   Value: `Cash - USD - US`
*   Description: `Cash - USD - US`

With **Global Tree View** active:
*   Value: `Cash - USD - US`
*   Description: `Application of Funds (Assets) -> Current Assets -> Bank Accounts -> Cash - USD - US`

*(If **Remove Company Abbreviation** is enabled, it becomes: `Application of Funds (Assets) -> Current Assets -> Bank Accounts -> Cash - USD`)*

---

### Example 2: Warehouse Suggestion
When selecting warehouse locations in stock documents:
*   Standard Description: `Finished Goods - WH`
*   Enhanced Description: `All Warehouses -> Main Site -> Store Room -> Finished Goods - WH`

---

## 🔍 Troubleshooting

### 1. Suggestions Are Not Enhancing
*   **Verify Active Status**: Ensure the **Active** checkbox in **Tree Search Setting** is checked.
*   **Check DocType Meta**: The target DocType must be configured as a tree. Verify that "Is Tree" is enabled in DocType settings.
*   **Ignore List**: Ensure the DocType is not listed in the **Ignore Doctypes** child table.
*   **Permissions**: If some levels are missing, check user permissions on root documents, or check **Ignore User Permissions** in settings.

### 2. Investigating Failures
Any unexpected failure during path construction is caught gracefully, falling back to the default search suggestions. The traceback is logged under **Error Logs**:
1.  Search for **Error Log List** in the awesomebar.
2.  Look for logs with the subject **Tree Search Override Failed**.
3.  Inspect the traceback to pinpoint database structure anomalies or missing parent link configurations.
