# Copyright 2019 Camptocamp (https://www.camptocamp.com)

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    sticky_destination = fields.Boolean(
        help="When checked, if the destination location is changed, "
        "a new \"link\" move is inserted before the next move instead"
        " of changing it's source location (only applies on chained moves)."
    )
