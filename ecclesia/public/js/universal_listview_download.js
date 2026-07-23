// universal_listview_download.js
//
// Place in:   your_app/public/js/universal_listview_download.js
// Add to hooks.py:
//   app_include_js = ["assets/your_app/js/universal_listview_download.js"]
//
// ── Optional per-doctype override ────────────────────────────────────────────
// To keep your existing Church Attendance custom export:
//
//   frappe.universal_export.register("Church Attendance", {
//       url: "church.church.doctype.church_attendance.church_attendance.export_attendance_excel"
//   });
// ─────────────────────────────────────────────────────────────────────────────

frappe.provide("frappe.universal_export");
frappe.universal_export._registry = {};

frappe.universal_export.register = function (doctype, config) {
    frappe.universal_export._registry[doctype] = config;
};

// ── Download logic ────────────────────────────────────────────────────────────
frappe.universal_export.download = function (doctype, options) {
    options = options || {};
    const override = frappe.universal_export._registry[doctype];

    // Filters: prefer caller's, then list view, then empty
    let filters = options.filters;
    if (!filters) {
        try {
            const lv = cur_list;
            filters = (lv && lv.get_filters_for_args && lv.get_filters_for_args())
                   || (lv && lv.filter_area && lv.filter_area.get && lv.filter_area.get())
                   || {};
        } catch (e) {
            filters = {};
        }
    }

    // Fields: prefer caller's, then visible list columns
    let fields = options.fields;
    if (!fields) {
        try {
            const lv = cur_list;
            if (lv && lv.columns && lv.columns.length) {
                const extracted = lv.columns
                    .map(function (c) { return (c.df && c.df.fieldname) || c.fieldname; })
                    .filter(function (fn) { return fn && fn !== "name"; });
                if (extracted.length) fields = extracted;
            }
        } catch (e) { /* ignore */ }
    }

    const params = {
        doctype:     doctype,
        filters:     JSON.stringify(filters || {}),
        order_by:    options.order_by    || "modified desc",
        page_length: options.page_length || 10000,
        title:       doctype,
    };
    if (fields && fields.length) {
        params.fields = JSON.stringify(fields);
    }
    if (override && override.extra_params) {
        Object.assign(params, override.extra_params);
    }

    // !! Replace "your_app" with your actual app name !!
    const endpoint = (override && override.url)
        || "ecclesia.utils.universal_excel_export.universal_export_excel";

    const qs = Object.keys(params)
        .map(function (k) {
            return encodeURIComponent(k) + "=" + encodeURIComponent(params[k]);
        })
        .join("&");

    window.open("/api/method/" + endpoint + "?" + qs, "_blank");

    frappe.show_alert({ message: __("Preparing Excel export…"), indicator: "green" });
};

// ── Button injection ──────────────────────────────────────────────────────────
frappe.universal_export._attach = function (lv) {
    if (!lv || !lv.page || lv.__ue_attached) return;
    lv.__ue_attached = true;

    lv.page.add_inner_button(__("⬇ Export Excel"), function () {
        frappe.universal_export.download(lv.doctype);
    });
};

// ── Strategy 1: frappe.router page-change event (reliable on all versions) ───
$(document).on("page-change", function () {
    // Give Frappe a tick to finish rendering the list view
    setTimeout(function () {
        if (cur_list && cur_list.page) {
            frappe.universal_export._attach(cur_list);
        }
    }, 300);
});

// ── Strategy 2: patch ListView.setup() — fires after page & toolbar exist ────
// We defer until frappe.views.ListView is defined (it loads asynchronously).
frappe.universal_export._patch_listview = function () {
    if (!frappe.views || !frappe.views.ListView) return false;

    const _orig_setup = frappe.views.ListView.prototype.setup;
    frappe.views.ListView.prototype.setup = function () {
        const result = _orig_setup && _orig_setup.apply(this, arguments);
        const self = this;
        // Use setTimeout so the page toolbar is fully rendered
        setTimeout(function () {
            frappe.universal_export._attach(self);
        }, 300);
        return result;
    };
    return true;
};

// Try immediately; if ListView isn't ready yet, retry until it is
if (!frappe.universal_export._patch_listview()) {
    let attempts = 0;
    const interval = setInterval(function () {
        attempts++;
        if (frappe.universal_export._patch_listview() || attempts > 20) {
            clearInterval(interval);
        }
    }, 300);
}

// ── Strategy 3: MutationObserver — catches any re-renders the above miss ─────
(function () {
    let _lastHref = location.href;

    const observer = new MutationObserver(function () {
        // Only act when on a List route  (/app/<doctype>/list  or  ?view=List)
        const href = location.href;
        const onList = /\/app\/[^/]+$/.test(location.pathname)
                    && (document.querySelector(".list-row-container") !== null
                        || document.querySelector(".result-list")      !== null);

        if (onList && cur_list && cur_list.page && !cur_list.__ue_attached) {
            frappe.universal_export._attach(cur_list);
        }

        _lastHref = href;
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();