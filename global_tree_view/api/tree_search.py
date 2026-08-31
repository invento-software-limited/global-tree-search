import frappe
from frappe.desk.search import (
	build_for_autosuggest,
	validate_ignore_user_permissions,
)
from frappe.desk.search import (
	search_link as original_search_link,
)


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
	try:
		return _search_link_impl(
			doctype,
			txt,
			query,
			filters,
			page_length,
			searchfield,
			reference_doctype,
			ignore_user_permissions,
			link_fieldname=link_fieldname,
			start=start,
		)
	finally:
		if hasattr(frappe.local, "response_headers") and frappe.local.response_headers is not None:
			frappe.local.response_headers.set("Cache-Control", "no-cache, no-store, must-revalidate")


def _search_link_impl(
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

	# Respect ignore_user_permissions setting, mirroring core's own validation
	# (frappe.desk.search.search_widget) so a client can't unlock it unchecked.
	if ignore_user_permissions:
		if reference_doctype and link_fieldname:
			validate_ignore_user_permissions(reference_doctype, link_fieldname, doctype)
		else:
			frappe.logger().error(
				"setting ignore_user_permissions=True requires reference_doctype and "
				f"link_fieldname to be set. Got reference_doctype={reference_doctype}, "
				f"link_fieldname={link_fieldname}. Ignoring flag."
			)
			ignore_user_permissions = False

	ignore_permissions = ignore_user_permissions
	if settings and settings.ignore_user_permissions:
		ignore_permissions = True

	# 1. Check if it's a tree doctype
	meta = frappe.get_meta(doctype)
	if meta.is_tree:
		# Fail fast: frappe.get_list below only checks this when ignore_permissions
		# is False, but we want a clear PermissionError, not a silent empty result,
		# and we want it before any doctype-wide fetch happens.
		if not ignore_permissions:
			frappe.has_permission(doctype, "read", throw=True)

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
			try:
				# Search fields for the doctype
				search_fields = ["name"]
				if meta.title_field:
					search_fields.append(meta.title_field)
				if meta.search_fields:
					for f in meta.search_fields:
						if f not in search_fields:
							search_fields.append(f)

				# Fetch all nodes to build hierarchy map in memory
				fields_to_fetch = ["name", parent_field]
				if meta.has_field("is_group"):
					fields_to_fetch.append("is_group")
				for f in search_fields:
					if meta.has_field(f) and f not in fields_to_fetch:
						fields_to_fetch.append(f)

				# frappe.get_all() unconditionally forces ignore_permissions=True
				# internally, which silently discarded the value passed here and
				# bypassed both doctype-level read permission and row-level User
				# Permission restrictions for every caller. frappe.get_list() has
				# the same signature but actually respects ignore_permissions.
				all_nodes = frappe.get_list(
					doctype, fields=fields_to_fetch, limit=None, ignore_permissions=ignore_permissions
				)
				parent_map = {node.name: node[parent_field] for node in all_nodes}

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

				# If there is a custom query or standard query, run it and post-process
				standard_queries = frappe.get_hooks().standard_queries or {}
				has_custom_query = bool(query or (doctype in standard_queries))

				if has_custom_query:
					original_res = original_search_link(
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
					for item in original_res:
						val = item.get("value")
						if val:
							path = get_path(val)
							node_data = next((n for n in all_nodes if n.name == val), None)
							is_group = (
								node_data.get("is_group") if (node_data and "is_group" in node_data) else 0
							)
							if is_group:
								item["description"] = f"{path} (Group)"
							else:
								item["description"] = path
					return original_res

				# Parse filters and preserve operators
				include_disabled = False
				parsed_filters = []
				if filters:
					if isinstance(filters, str):
						import json

						try:
							filters = json.loads(filters)
						except Exception:
							pass

					if isinstance(filters, dict):
						if "include_disabled" in filters:
							if filters["include_disabled"] == 1:
								include_disabled = True
							filters = dict(filters)
							filters.pop("include_disabled", None)
						for k, v in filters.items():
							parsed_filters.append([doctype, k, "=", v])
					elif isinstance(filters, list):
						for f in filters:
							if isinstance(f, (list, tuple)):
								parsed_filters.append(list(f))
							elif isinstance(f, dict):
								for k, v in f.items():
									parsed_filters.append([doctype, k, "=", v])

				# Build target filters
				target_filters = []

				# Append user filters
				target_filters.extend(parsed_filters)

				# Handle enabled/disabled
				if not include_disabled:
					if meta.get("fields", {"fieldname": "enabled", "fieldtype": "Check"}):
						target_filters.append([doctype, "enabled", "=", 1])
					if meta.get("fields", {"fieldname": "disabled", "fieldtype": "Check"}):
						target_filters.append([doctype, "disabled", "!=", 1])

				# Fetch target matching nodes
				target_fields = ["name"]
				if meta.has_field("is_group"):
					target_fields.append("is_group")

				# Same reasoning as the all_nodes fetch above: get_list (not
				# get_all) so ignore_permissions is actually honored.
				target_nodes = frappe.get_list(
					doctype,
					fields=target_fields,
					filters=target_filters,
					limit=None,
					ignore_permissions=ignore_permissions,
				)

				# Filter and build results
				result = []
				for node in target_nodes:
					path = get_path(node.name)
					matches = False
					if not txt:
						matches = True
					elif txt.lower() in path.lower():
						matches = True
					else:
						# Find this node in all_nodes to check search fields
						node_data = next((n for n in all_nodes if n.name == node.name), None)
						if node_data:
							for sf in search_fields:
								val = node_data.get(sf)
								if val and txt.lower() in str(val).lower():
									matches = True
									break

					if matches:
						is_group = node.get("is_group") if "is_group" in node else 0
						desc = f"{path} (Group)" if is_group else path
						result.append((node.name, desc))

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
