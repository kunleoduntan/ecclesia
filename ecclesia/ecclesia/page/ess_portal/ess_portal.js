frappe.pages['ess-portal'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Ess Portal',
		single_column: true
	});
}