# Copyright (c) 2026, na and Contributors
# See license.txt

import frappe
from frappe.permissions import add_permission, add_user_permission
from frappe.tests import IntegrationTestCase

from global_tree_view.api.tree_search import search_link

mock_query_results = []


def dummy_query(doctype, txt, searchfield, start, page_length, filters, **kwargs):
	return [["emp-001", "Original Description"]]


def mock_query(doctype, txt, searchfield, start, page_length, filters, **kwargs):
	return mock_query_results


class IntegrationTestTreeSearchSetting(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		# Setup settings
		self.settings = frappe.get_doc("Tree Search Setting")
		self.old_active = self.settings.active
		self.old_separator = self.settings.separator
		self.old_maximum_tree_levels = self.settings.maximum_tree_levels
		self.old_show_child_node = self.settings.show_child_node
		self.old_remove_company_abbreviation = self.settings.remove_company_abbreviation

		self.settings.active = 1
		self.settings.separator = " -> "
		self.settings.maximum_tree_levels = 0
		self.settings.show_child_node = 1
		self.settings.remove_company_abbreviation = 0
		self.settings.save()

		# Add dummy query and mock query to whitelisted functions
		frappe.whitelisted.add(dummy_query)
		frappe.whitelisted.add(mock_query)

	def tearDown(self):
		# Restore settings
		self.settings.active = self.old_active
		self.settings.separator = self.old_separator
		self.settings.maximum_tree_levels = self.old_maximum_tree_levels
		self.settings.show_child_node = self.old_show_child_node
		self.settings.remove_company_abbreviation = self.old_remove_company_abbreviation
		self.settings.save()

		# Clean up whitelisted functions
		frappe.whitelisted.discard(dummy_query)
		frappe.whitelisted.discard(mock_query)
		super().tearDown()

	def skip_unless_doctype_exists(self, doctype):
		# This app has no tree doctype of its own to test against - Warehouse,
		# Territory, Cost Center, Employee and Department all belong to
		# erpnext/hrms. Skip rather than fail when those apps aren't installed
		# on the site the tests are running against (e.g. a bare CI site).
		if not frappe.db.exists("DocType", doctype):
			self.skipTest(f"{doctype} doctype is not installed on this site")

	def ensure_test_department(self):
		self.skip_unless_doctype_exists("Department")
		dept_name = "Test Dept Override - CO"
		if not frappe.db.exists("Department", dept_name):
			self.dept = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": "Test Dept Override",
					"custom_short_code": "TDO",
					"company": "Corporate Office",
					"is_group": 0,
				}
			)
			self.dept.insert(ignore_permissions=True)
			self.dept_name = self.dept.name
		else:
			self.dept_name = dept_name

	def test_fallback_non_tree_doctype(self):
		# User is a non-tree doctype
		res = search_link(doctype="User", txt="Administrator")
		# Check that we got results and it contains Administrator
		self.assertTrue(any(r["value"] == "Administrator" for r in res))

	def test_standard_tree_search_warehouse(self):
		self.skip_unless_doctype_exists("Warehouse")
		# Warehouse is a tree doctype
		res = search_link(doctype="Warehouse", txt="Stores")
		self.assertTrue(len(res) > 0)
		for r in res:
			if "Stores" in r["value"]:
				# Should have hierarchical path in description
				self.assertIn(" -> ", r["description"])

	def test_toggle_active_setting(self):
		self.skip_unless_doctype_exists("Warehouse")
		# 1. Deactivate settings
		self.settings.active = 0
		self.settings.save()

		# 2. Perform search
		res_deactive = search_link(doctype="Warehouse", txt="Stores")
		self.assertTrue(len(res_deactive) > 0)
		for r in res_deactive:
			if "Stores" in r["value"]:
				# Standard search link output does not put " -> " in description
				self.assertNotIn(" -> ", r.get("description") or "")

		# 3. Activate settings
		self.settings.active = 1
		self.settings.save()

		# 4. Perform search again
		res_active = search_link(doctype="Warehouse", txt="Stores")
		self.assertTrue(len(res_active) > 0)
		for r in res_active:
			if "Stores" in r["value"]:
				# Should have hierarchical path in description
				self.assertIn(" -> ", r.get("description") or "")

	def test_tree_search_without_is_group_employee(self):
		self.skip_unless_doctype_exists("Employee")
		self.ensure_test_department()
		# Employee is a tree doctype (is_tree=1) but doesn't have is_group
		# Create test employee records
		# 1. Boss
		boss = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_number": "EMP-BOSS-TEST-001",
				"first_name": "Boss",
				"gender": "Male",
				"status": "Active",
				"company": "Corporate Office",
				"department": self.dept_name,
				"date_of_birth": "1980-01-01",
				"date_of_joining": "2020-01-01",
			}
		)
		boss.insert(ignore_permissions=True)

		# 2. Staff reporting to Boss
		staff = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_number": "EMP-STAFF-TEST-001",
				"first_name": "Staff",
				"gender": "Female",
				"status": "Active",
				"company": boss.company,
				"department": self.dept_name,
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2021-01-01",
				"reports_to": boss.name,
			}
		)
		staff.insert(ignore_permissions=True)

		# Test search for Staff
		res = search_link(doctype="Employee", txt="Staff")
		self.assertTrue(len(res) > 0)

		# Find staff result
		staff_res = next((r for r in res if r["value"] == staff.name), None)
		self.assertIsNotNone(staff_res)

		# Description or label should show the hierarchy path: Boss -> Staff
		expected_path = f"{boss.name} -> {staff.name}"
		actual_path = staff_res.get("label") or staff_res.get("description")
		self.assertEqual(actual_path, expected_path)

	def test_custom_query_post_processing(self):
		self.skip_unless_doctype_exists("Employee")
		self.ensure_test_department()
		# Create a dummy employee record to be returned by dummy query
		boss = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_number": "EMP-BOSS-TEST-002",
				"first_name": "Boss2",
				"gender": "Male",
				"status": "Active",
				"company": "Corporate Office",
				"department": self.dept_name,
				"date_of_birth": "1980-01-01",
				"date_of_joining": "2020-01-01",
			}
		)
		boss.insert(ignore_permissions=True)

		emp = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_number": "EMP-STAFF-TEST-002",
				"first_name": "Staff2",
				"gender": "Female",
				"status": "Active",
				"company": boss.company,
				"department": self.dept_name,
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2021-01-01",
				"reports_to": boss.name,
			}
		)
		emp.insert(ignore_permissions=True)

		# Populate mock query results
		global mock_query_results
		mock_query_results = [[emp.name, "Original Description"]]

		try:
			res = search_link(
				doctype="Employee",
				txt="Staff2",
				query="global_tree_view.global_tree_view.doctype.tree_search_setting.test_tree_search_setting.mock_query",
			)
			self.assertTrue(len(res) > 0)
			emp_res = next((r for r in res if r["value"] == emp.name), None)
			self.assertIsNotNone(emp_res)
			# Description should be modified to tree path: Boss2 -> Staff2
			expected_path = f"{boss.name} -> {emp.name}"
			self.assertEqual(emp_res["description"], expected_path)
		finally:
			mock_query_results = []

	def test_search_link_denies_user_without_read_permission(self):
		self.skip_unless_doctype_exists("Cost Center")
		# Regression test: frappe.get_all() forces ignore_permissions=True
		# internally, so passing ignore_permissions=False to it (as the old
		# implementation did) had no effect and every caller could read every
		# tree doctype regardless of role permissions. A role with no
		# Custom DocPerm on Cost Center must be denied, not silently served
		# the full unfiltered list.
		role_name = "GTV Test No Cost Center Access"
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)

		user_email = "gtv-no-access-test@example.com"
		if not frappe.db.exists("User", user_email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": user_email,
					"first_name": "GTV No Access",
					"send_welcome_email": 0,
					"roles": [{"role": role_name}],
				}
			)
			user.insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", user_email)
			user.set("roles", [{"role": role_name}])
			user.save(ignore_permissions=True)

		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user_email)

		with self.assertRaises(frappe.PermissionError):
			search_link(doctype="Cost Center", txt="")

	def test_search_link_respects_user_permission_restriction(self):
		self.skip_unless_doctype_exists("Territory")
		# Regression test: the row-level User Permission match conditions
		# were also silently skipped by the old frappe.get_all() call, so a
		# user restricted to one Territory could still see every Territory
		# in the system. Fixed by switching to frappe.get_list().
		role_name = "GTV Test Territory Reader"
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)
			add_permission("Territory", role_name, 0, "read")

		root = frappe.db.get_value(
			"Territory", {"is_group": 1, "parent_territory": ["is", "not set"]}, "name"
		)

		def get_or_create_territory(name):
			if frappe.db.exists("Territory", name):
				return name
			frappe.get_doc(
				{
					"doctype": "Territory",
					"territory_name": name,
					"parent_territory": root,
					"is_group": 0,
				}
			).insert(ignore_permissions=True)
			return name

		allowed_territory = get_or_create_territory("GTV Test Territory Allowed")
		restricted_territory = get_or_create_territory("GTV Test Territory Restricted")

		user_email = "gtv-territory-restricted-test@example.com"
		if not frappe.db.exists("User", user_email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": user_email,
					"first_name": "GTV Territory Restricted",
					"send_welcome_email": 0,
					"roles": [{"role": role_name}],
				}
			)
			user.insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", user_email)
			user.set("roles", [{"role": role_name}])
			user.save(ignore_permissions=True)

		add_user_permission("Territory", allowed_territory, user_email)

		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user_email)

		res = search_link(doctype="Territory", txt="GTV Test Territory")
		values = {r["value"] for r in res}

		self.assertIn(allowed_territory, values)
		self.assertNotIn(restricted_territory, values)
