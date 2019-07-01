# Copyright 2019 Camptocamp (https://www.camptocamp.com)

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    warehouse_view_location_id = fields.Many2one(
        related='warehouse_id.view_location_id',
        readonly=True,
    )

    def action_show_details(self):
        action = super().action_show_details()

        if self.picking_id.picking_type_id.sticky_destination:
            # We allow to have a destination which is not in necessarily
            # a children of the move's destination location, as in such
            # case, we'll create a linked move between existing moves.
            # Add a context key that will be used by fields_view_get()
            # of move lines to remove the domain.
            action['context'] = dict(
                action['context'],
                allow_outside_dest_locations=True,
            )

        return action
