# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
{
    "name": "Stock Putaway Recursive",
    "summary": "Apply putaway strategies recursively",
    "version": "12.0.1.0.0",
    "development_status": "Alpha",
    "category": "Warehouse Management",
    "website": "https://github.com/OCA/stock-logistics-warehouse",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        # FIXME should depend on stock, however, stock_putaway_rule
        # overrides StockLocation.get_putaway_strategy without calling
        # super(), so until we have an alternative, add a dependency
        # there.
        "stock_putaway_rule",
    ],
}
