// Copyright (c) 2026, na and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tree Search Setting", {
	setup: function (frm) {
		frm.set_query("doctype_to_ignore", "ignore_doctypes", function () {
			return {
				filters: {
					is_tree: 1,
				},
			};
		});
	},
});
