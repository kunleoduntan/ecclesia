frappe.listview_settings["Journal Amortization"] = {
	add_fields: ["status", "amortized_amount", "total_amount"],
	get_indicator(doc) {
		const map = {
			"Pending": ["Pending", "gray", "status,=,Pending"],
			"Partially Created": ["Partially Created", "orange", "status,=,Partially Created"],
			"Created": ["Created", "green", "status,=,Created"],
		};
		return map[doc.status];
	},
};