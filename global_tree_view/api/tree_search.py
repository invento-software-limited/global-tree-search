import frappe
from frappe.desk.search import search_link as original_search_link, build_for_autosuggest

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
):
	# 1. Check if it's a tree doctype
	meta = frappe.get_meta(doctype)
	if meta.is_tree:
		# Find the parent field (a Link field pointing to the same doctype)
		parent_field = None
		for field in meta.fields:
			if field.fieldtype == "Link" and field.options == doctype:
				parent_field = field.fieldname
				break
		
		if not parent_field:
			# Fallback
			fallback = f"parent_{frappe.scrub(doctype)}"
			if meta.has_field(fallback):
				parent_field = fallback

		if parent_field:
			# Parse filters if necessary
			target_filters = {"is_group": 0}
			if filters:
				if isinstance(filters, str):
					import json
					try:
						filters = json.loads(filters)
					except Exception:
						pass
				if isinstance(filters, dict):
					target_filters.update(filters)
				elif isinstance(filters, list):
					# Handle list filters
					for f in filters:
						if isinstance(f, (list, tuple)) and len(f) >= 3:
							if f[1] == "is_group":
								target_filters["is_group"] = f[3]
							else:
								target_filters[f[1]] = f[3]

			try:
				# Fetch all nodes to build hierarchy map in memory
				all_nodes = frappe.get_all(
					doctype,
					fields=["name", parent_field, "is_group"],
					limit=10000,
					ignore_permissions=ignore_user_permissions
				)
				parent_map = {node.name: node[parent_field] for node in all_nodes}

				# Fetch target matching leaf nodes
				target_nodes = frappe.get_all(
					doctype,
					fields=["name"],
					filters=target_filters,
					limit=10000,
					ignore_permissions=ignore_user_permissions
				)

				# Build path function
				def get_path(name):
					path = []
					curr = name
					visited = set()
					while curr and curr not in visited:
						visited.add(curr)
						path.insert(0, curr)
						curr = parent_map.get(curr)
					return " -> ".join(path)

				# Filter and build results
				result = []
				for node in target_nodes:
					path = get_path(node.name)
					if not txt or txt.lower() in path.lower():
						result.append((node.name, path))

				# Sort results by name
				result.sort(key=lambda x: x[0])

				# Paginate
				paginated_result = result[start : start + page_length]

				return build_for_autosuggest(paginated_result, doctype=doctype)
			except Exception as e:
				# Log exception and fallback
				frappe.log_error(message=str(e), title="Tree Search Override Failed")
				
	# Fallback to the original search_link
	return original_search_link(
		doctype,
		txt,
		query,
		filters,
		page_length,
		searchfield,
		reference_doctype,
		ignore_user_permissions,
		link_fieldname=link_fieldname,
	)
