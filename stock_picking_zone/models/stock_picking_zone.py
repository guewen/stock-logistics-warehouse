# Copyright 2019 Camptocamp (https://www.camptocamp.com)

from odoo import fields, models


class StockPickingZone(models.Model):
    _name = 'stock.picking.zone'
    _description = 'Stock Picking Zone'

    name = fields.Char(required=True)
    active = fields.Boolean(
        default=True,
        help="By unchecking the active field, you may hide"
        " a zone without deleting it."
    )
    # When we assign a move, from the source location, search
    # the first location (going up through the locations) which
    # has a zone. Change the destination and picking type of the zone
    # to the zone's
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Source Location',
        index=True,
        required=True,
    )
    location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string='Destination Location',
        index=True,
        required=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        required=True,
    )
