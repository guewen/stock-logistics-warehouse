# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals:
            # We cannot have fields to depends on to invalidate these computed
            # fields on vertical.lift.shuttle. But we know that when the state
            # of any move line changes, we can invalidate them as the count of
            # assigned move lines may change (and we track this in stock.move,
            # not stock.move.line, becaus the state of the lines is a related
            # to this one).
            self.env['vertical.lift.shuttle'].invalidate_cache(
                ['number_of_ops', 'number_of_ops_all']
            )
        return result
