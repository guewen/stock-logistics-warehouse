# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = "stock.move"

    def _update_reserved_quantity(
        self,
        need,
        available_quantity,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=True,
    ):
        """Create or update move lines."""
        if strict:
            # chained moves must take what was reserved by the previous move
            return super()._update_reserved_quantity(
                need,
                available_quantity,
                location_id=location_id,
                lot_id=lot_id,
                package_id=package_id,
                owner_id=owner_id,
                strict=strict,
            )
        rules = self.env["stock.reserve.rule"]._rules_for_location(location_id)
        if not rules:
            return super()._update_reserved_quantity(
                need,
                available_quantity,
                location_id=location_id,
                lot_id=lot_id,
                package_id=package_id,
                owner_id=owner_id,
                strict=strict,
            )

        still_need = need

        forced_package_id = self.package_level_id.package_id or None
        rounding = self.product_id.uom_id.rounding
        for rule in rules:
            # 1st check if rule is applicable from the move
            if not rule._is_rule_applicable(self):
                continue

            quants = self.env["stock.quant"]._gather(
                self.product_id,
                rule.location_id,
                lot_id=lot_id,
                package_id=forced_package_id,
                owner_id=owner_id,
                strict=strict,
            )

            # get quants allowed by the rule
            rule_quants = rule._filter_quants(self, quants)
            if not rule_quants:
                continue

            # Apply the advanced removal strategy, if any. Even within the
            # application of the removal strategy, the original company's one
            # should be respected (eg. if we remove quants that would empty
            # bins first, in case of equality, we should remove the fifo or
            # fefo first depending of the configuration).
            strategy = rule._apply_strategy(rule_quants)
            next(strategy)
            while True:
                try:
                    next_quant = strategy.send(still_need)
                    if not next_quant:
                        continue
                    location, location_quantity, to_take = next_quant
                    taken_in_loc = super()._update_reserved_quantity(
                        # in this strategy, we take as much as we can
                        # from this bin
                        to_take,
                        location_quantity,
                        location_id=location,
                        lot_id=lot_id,
                        package_id=package_id,
                        owner_id=owner_id,
                        strict=strict,
                    )
                    still_need -= taken_in_loc
                except StopIteration:
                    break

            need_zero = (
                float_compare(still_need, 0, precision_rounding=rounding) != 1
            )
            if need_zero:
                # useless to eval the other rules when still_need <= 0
                break

        reserved = need - still_need
        return reserved + super()._update_reserved_quantity(
            still_need,
            available_quantity - reserved,
            location_id=location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
        )
