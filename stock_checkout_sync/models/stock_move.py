# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def sync_checkout_destination(self, location):
        moves = self.filtered(lambda m: m.state != "done")
        # Normally the move destination does not change. But when using other
        # addons, such as stock_dynamic_routing, the source location of the
        # destination move can change, so handle this case too. (there is a
        # glue module stock_dynamic_routing_common_dest_sync).
        moves_to_update = self.filtered(lambda m: m.location_dest_id != location)
        moves_to_update.write({"location_dest_id": location.id})
        # Sync the source of the destination move too, if it's still waiting.
        moves_to_update.move_dest_ids.filtered(
            lambda m: (
                m.state == "waiting"
                or m.state == "assigned"
                and m in self.move_dest_ids
            )
            and m.location_id != location
        ).write({"location_id": location.id})
        lines = moves.mapped("move_line_ids")
        lines.filtered(
            lambda l: l.location_dest_id != location and l.state != "done"
        ).write({"location_dest_id": location.id})
