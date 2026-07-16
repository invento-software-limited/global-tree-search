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
	# Load settings
	settings = None
	try:
		settings = frappe.get_cached_doc("Tree Search Setting")
	except Exception:
		pass

	# Fallback if settings are inactive
	if settings and not settings.active:
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

	# Fallback if doctype is ignored in settings
	if settings and settings.ignore_doctypes:
		ignored = [d.doctype_to_ignore for d in settings.ignore_doctypes if d.doctype_to_ignore]
		if doctype in ignored:
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

	# Respect ignore_user_permissions setting
	ignore_permissions = ignore_user_permissions
	if settings and settings.ignore_user_permissions:
		ignore_permissions = True

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
						if isinstance(f, (list, tuple)):
							fieldname = None
							value = None
							if len(f) == 2:
								fieldname = f[0]
								value = f[1]
							elif len(f) == 3:
								fieldname = f[0]
								value = f[2]
							elif len(f) >= 4:
								fieldname = f[1]
								value = f[3]

							if fieldname and isinstance(fieldname, str):
								if fieldname == "is_group":
									target_filters["is_group"] = value
								else:
									target_filters[fieldname] = value
						elif isinstance(f, dict):
							for k, v in f.items():
								if k == "is_group":
									target_filters["is_group"] = v
								else:
									target_filters[k] = v

			try:
				# Fetch all nodes to build hierarchy map in memory
				all_nodes = frappe.get_all(
					doctype,
					fields=["name", parent_field, "is_group"],
					limit=10000,
					ignore_permissions=ignore_permissions
				)
				parent_map = {node.name: node[parent_field] for node in all_nodes}

				# Fetch target matching leaf nodes
				target_nodes = frappe.get_all(
					doctype,
					fields=["name"],
					filters=target_filters,
					limit=10000,
					ignore_permissions=ignore_permissions
				)

				# Build path function
				def get_path(name):
					path_parts = []
					curr = name
					visited = set()
					while curr and curr not in visited:
						visited.add(curr)
						
						# Clean name if remove_company_abbreviation is set
						cleaned_name = curr
						if settings and settings.remove_company_abbreviation and " - " in curr:
							parts = curr.rsplit(" - ", 1)
							if len(parts) > 1 and parts[1].isupper() and 2 <= len(parts[1]) <= 5:
								cleaned_name = parts[0]
								
						path_parts.insert(0, cleaned_name)
						curr = parent_map.get(curr)
					
					# Handle show_child_node setting
					if settings and not settings.show_child_node and len(path_parts) > 1:
						path_parts = path_parts[:-1]

					# Handle maximum_tree_levels setting
					max_levels = settings.maximum_tree_levels if settings else 0
					is_truncated = False
					if max_levels > 0 and len(path_parts) > max_levels:
						path_parts = path_parts[-max_levels:]
						is_truncated = True

					# Join using separator setting
					sep = settings.separator if (settings and settings.separator) else " -> "
					path_str = sep.join(path_parts)
					
					if is_truncated:
						path_str = "..." + sep + path_str
						
					return path_str

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
