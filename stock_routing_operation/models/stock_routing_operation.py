# Copyright 2019 Camptocamp (https://www.camptocamp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class StockRoutingOperation(models.Model):
    _name = "stock.routing.operation"
    _order = "sequence, id"
    _rec_name = "picking_type_id"

    sequence = fields.Integer()
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type", required=True
    )
    direction = fields.Selection(
        selection=[("in", "Incoming"), ("out", "Outgoing")], required=True
    )
    location_src_id = fields.Many2one(
        related="picking_type_id.default_location_src_id", readonly=True
    )
    location_dest_id = fields.Many2one(
        related="picking_type_id.default_location_dest_id", readonly=True
    )
    domain = fields.Char(default="[]")
