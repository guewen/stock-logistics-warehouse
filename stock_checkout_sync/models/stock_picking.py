# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from collections import OrderedDict

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    can_sync_to_checkout = fields.Boolean(
        compute="_compute_can_sync_to_checkout",
        help="Technical field. Indicates if the button to synchronize "
        "the destination towards a checkout location is visible.",
    )

    @api.depends("move_lines.move_dest_ids")
    def _compute_can_sync_to_checkout(self):
        for picking in self:
            picking.can_sync_to_checkout = False
            for dest_move in picking.mapped("move_lines.move_dest_ids"):
                if dest_move.picking_type_id.checkout_sync:
                    picking.can_sync_to_checkout = True
                    break

    def _moves_to_sync_checkout(self):
        selected_pickings = OrderedDict()
        for move in self.mapped("move_lines"):
            # Excluding picking types is used to sync the moves one picking
            # type at a time from the wizard.
            dest_pickings = move.mapped("move_dest_ids.picking_id").filtered(
                lambda pick: pick.picking_type_id.checkout_sync
            )
            if not self:
                continue

            moves = (move | move.common_dest_move_ids).filtered(
                lambda move: move.state not in ("done", "cancel")
            )
            for dest_picking in dest_pickings:
                if dest_picking not in selected_pickings:
                    selected_pickings[dest_picking] = self.env["stock.move"].browse()
                selected_pickings[dest_picking] |= moves

        return selected_pickings

    def open_checkout_sync_wizard(self, done_picking_types=None):
        return self.env["stock.move.checkout.sync"]._open(self)
