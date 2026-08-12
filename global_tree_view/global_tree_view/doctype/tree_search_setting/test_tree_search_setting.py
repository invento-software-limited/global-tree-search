# Copyright (c) 2026, na and Contributors
# See license.txt

import frappe
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

		# Create a test department with custom_short_code if it doesn't exist
		dept_name = "Test Dept Override - CO"
		if not frappe.db.exists("Department", dept_name):
			self.dept = frappe.get_doc({
				"doctype": "Department",
				"department_name": "Test Dept Override",
				"custom_short_code": "TDO",
				"company": "Corporate Office",
				"is_group": 0
			})
			self.dept.insert(ignore_permissions=True)
			self.dept_name = self.dept.name
		else:
			self.dept_name = dept_name

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

	def test_fallback_non_tree_doctype(self):
		# User is a non-tree doctype
		res = search_link(doctype="User", txt="Administrator")
		# Check that we got results and it contains Administrator
		self.assertTrue(any(r["value"] == "Administrator" for r in res))

	def test_standard_tree_search_warehouse(self):
		# Warehouse is a tree doctype
		res = search_link(doctype="Warehouse", txt="Stores")
		self.assertTrue(len(res) > 0)
		for r in res:
			if "Stores" in r["value"]:
				# Should have hierarchical path in description
				self.assertIn(" -> ", r["description"])

	def test_toggle_active_setting(self):
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
		# Employee is a tree doctype (is_tree=1) but doesn't have is_group
		# Create test employee records
		# 1. Boss
		boss = frappe.get_doc({
			"doctype": "Employee",
			"employee_number": "EMP-BOSS-TEST-001",
			"first_name": "Boss",
			"gender": "Male",
			"status": "Active",
			"company": "Corporate Office",
			"department": self.dept_name,
			"date_of_birth": "1980-01-01",
			"date_of_joining": "2020-01-01"
		})
		boss.insert(ignore_permissions=True)

		# 2. Staff reporting to Boss
		staff = frappe.get_doc({
			"doctype": "Employee",
			"employee_number": "EMP-STAFF-TEST-001",
			"first_name": "Staff",
			"gender": "Female",
			"status": "Active",
			"company": boss.company,
			"department": self.dept_name,
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2021-01-01",
			"reports_to": boss.name
		})
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
		# Create a dummy employee record to be returned by dummy query
		boss = frappe.get_doc({
			"doctype": "Employee",
			"employee_number": "EMP-BOSS-TEST-002",
			"first_name": "Boss2",
			"gender": "Male",
			"status": "Active",
			"company": "Corporate Office",
			"department": self.dept_name,
			"date_of_birth": "1980-01-01",
			"date_of_joining": "2020-01-01"
		})
		boss.insert(ignore_permissions=True)

		emp = frappe.get_doc({
			"doctype": "Employee",
			"employee_number": "EMP-STAFF-TEST-002",
			"first_name": "Staff2",
			"gender": "Female",
			"status": "Active",
			"company": boss.company,
			"department": self.dept_name,
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2021-01-01",
			"reports_to": boss.name
		})
		emp.insert(ignore_permissions=True)

		# Populate mock query results
		global mock_query_results
		mock_query_results = [[emp.name, "Original Description"]]

		try:
			res = search_link(
				doctype="Employee",
				txt="Staff2",
				query="global_tree_view.global_tree_view.doctype.tree_search_setting.test_tree_search_setting.mock_query"
			)
			self.assertTrue(len(res) > 0)
			emp_res = next((r for r in res if r["value"] == emp.name), None)
			self.assertIsNotNone(emp_res)
			# Description should be modified to tree path: Boss2 -> Staff2
			expected_path = f"{boss.name} -> {emp.name}"
			self.assertEqual(emp_res["description"], expected_path)
		finally:
			mock_query_results = []
