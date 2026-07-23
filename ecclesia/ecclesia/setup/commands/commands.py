# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Optional custom bench command: `bench ensure-doctypes`

This is purely a nicer UX wrapper around ensure_doctypes.ensure_doctypes_exist —
functionally identical to running:
    bench --site your-site.local execute ecclesia.ecclesia.setup.ensure_doctypes.ensure_doctypes_exist
If you don't want the extra hooks.py wiring, skip this file entirely and
just use the `bench execute` form above; it needs zero registration.

To enable this command, add to hooks.py:
    commands = ["ecclesia.ecclesia.setup.commands.commands"]
(If hooks.py already has a `commands` list, append the string instead of
overwriting it.)

Usage once wired up:
    bench --site your-site.local ensure-doctypes
    bench --site your-site.local ensure-doctypes --force-update
"""

import click
import frappe

from ecclesia.ecclesia.setup.ensure_doctypes import ensure_doctypes_exist


@click.command("ensure-doctypes")
@click.option("--force-update", is_flag=True, default=False,
              help="Also re-apply the bundled schema to DocTypes that already exist "
                   "(does not touch their data, only field/layout definitions).")
@click.pass_context
def ensure_doctypes_command(ctx, force_update):
    """Recreate any of the 14 Ecclesia DocTypes that are missing from the database."""
    site = ctx.obj["sites"][0] if ctx.obj.get("sites") else None
    if not site:
        click.echo("Please specify a site: bench --site your-site.local ensure-doctypes")
        return

    frappe.init(site=site)
    frappe.connect()
    try:
        summary = ensure_doctypes_exist(force_update=force_update)
        click.echo(json_summary(summary))
    finally:
        frappe.destroy()


def json_summary(summary):
    lines = [
        f"Created: {len(summary['created'])} {summary['created']}",
        f"Updated: {len(summary['updated'])} {summary['updated']}",
        f"Already present: {len(summary['skipped'])}",
        f"Failed: {len(summary['failed'])}",
    ]
    for f in summary["failed"]:
        lines.append(f"  - {f['name']}: {f['error']}")
    return "\n".join(lines)


commands = [ensure_doctypes_command]
