# ecclesia/utils/link_validator.py

import frappe


def prefetch_links(rows, link_fields, field_map):

    cache = {}

    for df in link_fields:

        col = field_map.get(df.fieldname)

        if not col:
            continue

        values = set()

        for r in rows:

            v = r.get(col)

            if v:
                values.add(v)

        if not values:
            continue

        existing = frappe.get_all(
            df.options,
            filters={"name": ["in", list(values)]},
            pluck="name"
        )

        cache[df.options] = set(existing)

    return cache