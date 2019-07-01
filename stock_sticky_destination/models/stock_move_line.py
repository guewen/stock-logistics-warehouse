# Copyright 2019 Camptocamp (https://www.camptocamp.com)

from lxml import etree

from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        result = super().fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu
        )
        op_xmlid = 'stock.view_stock_move_line_operation_tree'
        op_view = self.env.context.get('tree_view_ref') == op_xmlid
        allow_outside_dest_locations = self.env.context.get(
            'allow_outside_dest_locations'
        )
        if (op_view and allow_outside_dest_locations):
            view_arch = result['arch']
            result['arch'] = self._apply_view_dest_domain_outside(view_arch)
        return result

    @api.model
    def _apply_view_dest_domain_outside(self, view_arch):
        doc = etree.XML(view_arch)

        for node in doc.xpath("//field[@name='location_dest_id']"):
            node.set(
                "domain",
                "[('id', 'child_of', parent.warehouse_view_location_id)]"
            )

        return etree.tostring(doc, encoding='unicode')

    def _action_done(self):
        super()._action_done()
        # super may delete lines
        lines = self.exists()
        lines._insert_sticky_moves()

    def _insert_sticky_moves(self):
        for line in self:
            move = line.move_id
            picking = move.picking_id
            if not picking.picking_type_id.sticky_destination:
                continue
            dest_moves = move.move_dest_ids
            for dest_move in dest_moves:
                dest_location = dest_move.location_id
                line_dest_location = line.location_dest_id
                if dest_location == line_dest_location:
                    # shortcircuit to avoid a query checking if it is a child
                    continue
                child_locations = self.env['stock.location'].search([
                    ('id', 'child_of', move.location_dest_id.id)
                ])
                if line_dest_location in child_locations:
                    # normal behavior, we don't need a move between A and B
                    continue
                # Insert move between the source and destination for the new
                # operation
                middle_move = self.env['stock.move'].create({
                    'name': move.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty_done,
                    'product_uom': move.product_uom.id,
                    'picking_id': picking.id,
                    'location_id': line_dest_location.id,
                    'location_dest_id': dest_location.id,
                    'procure_method': move.procure_method,
                    'move_dest_ids': [(4, dest_move.id)],
                    'move_orig_ids': [(4, move.id)],
                    'state': 'waiting',
                    'picking_type_id': picking.picking_type_id.id,
                    'group_id': move.group_id.id,
                })
                dest_move.write({
                    'move_orig_ids': [(3, move.id)],
                })
                # FIXME: if we have more than one move line on a move,
                # the move will only have the dest of the last one
                move.write({
                    'move_dest_ids': [(3, dest_move.id)],
                    'location_dest_id': line_dest_location.id
                })
                middle_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                })
                middle_move.picking_id = middle_picking
