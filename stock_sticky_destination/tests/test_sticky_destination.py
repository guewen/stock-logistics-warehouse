# Copyright 2019 Camptocamp (https://www.camptocamp.com)

from odoo.tests import common


class TestStickyDestination(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_delta = cls.env.ref('base.res_partner_4')
        cls.wh = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'pick_ship',
            'code': 'WHTEST',
        })

        # important: location_a is not a sublocation of wh.wh_pack_stock_loc_id
        cls.location_a = cls.env['stock.location'].create({
            'name': 'Location A',
            'location_id': cls.wh.lot_stock_id.id,
        })

        cls.location_pack_sub = cls.env['stock.location'].create({
            'name': 'Sub-Packing Zone',
            'location_id': cls.wh.wh_pack_stock_loc_id.id,
        })

        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A', 'type': 'product',
        })

    def _update_product_qty_in_location(self, location, product, quantity):
        self.env['stock.quant']._update_available_quantity(
            product, location, quantity
        )

    def _create_picking_out(self, warehouse, **vals):
        picking_values = {
            'picking_type_id': self.wh.out_type_id.id,
            'location_id': self.env.ref('stock.stock_location_customers').id,
            'location_dest_id': warehouse.lot_stock_id.id,
        }
        picking_values.update(**vals)
        return self.env['stock.picking'].create(picking_values)

    def _create_move(self, picking, product, src, dest, **vals):
        # simulate create + onchange
        move = self.env['stock.move'].new({
            'picking_id': picking.id,
            'product_id': product.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
        })
        move.onchange_product_id()
        move_values = move._convert_to_write(move._cache)
        move_values.update(**vals)
        return self.env['stock.move'].create(move_values)

    def _create_pick_ship(self, wh):
        customer_loc = self.env.ref('stock.stock_location_customers')
        customer_picking = self.env['stock.picking'].create({
            'location_id': wh.wh_pack_stock_loc_id.id,
            'location_dest_id': customer_loc.id,
            'partner_id': self.partner_delta.id,
            'picking_type_id': wh.out_type_id.id,
        })
        dest = self.env['stock.move'].create({
            'name': self.product_a.name,
            'product_id': self.product_a.id,
            'product_uom_qty': 10,
            'product_uom': self.product_a.uom_id.id,
            'picking_id': customer_picking.id,
            'location_id': wh.wh_pack_stock_loc_id.id,
            'location_dest_id': customer_loc.id,
            'state': 'waiting',
            'procure_method': 'make_to_order',
        })

        pick_picking = self.env['stock.picking'].create({
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': wh.wh_pack_stock_loc_id.id,
            'partner_id': self.partner_delta.id,
            'picking_type_id': wh.out_type_id.id,
        })

        self.env['stock.move'].create({
            'name': self.product_a.name,
            'product_id': self.product_a.id,
            'product_uom_qty': 10,
            'product_uom': self.product_a.uom_id.id,
            'picking_id': pick_picking.id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': wh.wh_pack_stock_loc_id.id,
            'move_dest_ids': [(4, dest.id)],
            'state': 'confirmed',
        })
        return pick_picking, customer_picking

    def test_normal_case(self):
        """Test the normal Odoo use case, don't use sticky destination"""
        pick_picking, customer_picking = self._create_pick_ship(self.wh)
        move_a = pick_picking.move_lines
        move_b = customer_picking.move_lines

        self._update_product_qty_in_location(
            move_a.location_id, move_a.product_id, 100
        )

        pick_picking.action_confirm()
        pick_picking.action_assign()
        self.assertFalse(move_b.move_line_ids)

        move_a.move_line_ids.location_dest_id = self.location_a
        move_a.move_line_ids.qty_done = move_a.move_line_ids.product_uom_qty
        pick_picking.action_done()

        self.assertEqual(move_a.move_dest_ids, move_b)

        # the move stays on the same location
        self.assertEqual(move_b.location_id, self.wh.wh_pack_stock_loc_id)
        # but the next move line starts from the location A; as the previous
        # move line moved the product to location A
        self.assertEqual(move_b.move_line_ids.location_id, self.location_a)

    def test_sticky_pick_ship(self):
        """Change destination on source picking type with sticky destination"""
        pick_picking, customer_picking = self._create_pick_ship(self.wh)
        pick_picking.picking_type_id.sticky_destination = True
        move_a = pick_picking.move_lines
        move_b = customer_picking.move_lines

        self._update_product_qty_in_location(
            move_a.location_id, move_a.product_id, 100
        )

        pick_picking.action_confirm()
        pick_picking.action_assign()
        self.assertFalse(move_b.move_line_ids)

        # We have:
        # Move A ('Stock' → 'Packing Zone') →
        # Move B ('Packing Zone' → 'Customers')

        # The destination we set on the move_a's move line is not
        # a sublocation of 'Packing Zone', it matters!
        # If it was a sublocation, we would not insert a move between A and B.
        move_a.move_line_ids.location_dest_id = self.location_a
        move_a.move_line_ids.qty_done = move_a.move_line_ids.product_uom_qty
        pick_picking.action_done()

        # We expect:
        # Move A ('Stock' → 'Location A') →
        # Move Middle ('Location A' → 'Packing Zone') →
        # Move B ('Packing Zone' → 'Customers')

        self.assertNotEqual(move_a.move_dest_ids, move_b)
        # we expect the move A to be changed to the same location than
        # the move line
        # TODO what if we have more than one move line with different
        # locations?
        self.assertEqual(move_a.location_dest_id, self.location_a)
        # the move stays B stays on the same source location (sticky)
        self.assertEqual(move_b.location_id, self.wh.wh_pack_stock_loc_id)

        move_middle = move_a.move_dest_ids
        self.assertEqual(move_middle.location_id, move_a.location_dest_id)
        self.assertEqual(move_middle.location_dest_id, move_b.location_id)

        # the ship move line should stick on the same source
        self.assertFalse(move_b.move_line_ids)

        self.assertEqual(move_a.state, 'done')
        self.assertEqual(move_middle.state, 'assigned')
        self.assertEqual(move_b.state, 'waiting')

    def test_sticky_pick_ship_child_location(self):
        """Change destination but is sublocation"""
        pick_picking, customer_picking = self._create_pick_ship(self.wh)
        pick_picking.picking_type_id.sticky_destination = True
        move_a = pick_picking.move_lines
        move_b = customer_picking.move_lines

        self._update_product_qty_in_location(
            move_a.location_id, move_a.product_id, 100
        )

        pick_picking.action_confirm()
        pick_picking.action_assign()
        self.assertFalse(move_b.move_line_ids)

        # We have:
        # Move A ('Stock' → 'Packing Zone') →
        # Move B ('Packing Zone' → 'Customers')

        # The destination we set on the move_a's move line is a sublocation of
        # 'Packing Zone', it matters!
        # We don't have to create a move in the middle in this case
        move_a.move_line_ids.location_dest_id = self.location_pack_sub
        move_a.move_line_ids.qty_done = move_a.move_line_ids.product_uom_qty
        pick_picking.action_done()

        # We expect:
        # Move A ('Stock' → 'Packing Zone') →
        # Move B ('Packing Zone' → 'Customers')

        # As you can see, no change. The move lines will have this though
        # which the default behavior of Odoo:
        # Move Line A ('Stock' → 'Sub-Packing Zone') →
        # Move Line B ('Sub-Packing Zone' → 'Customers')

        self.assertEqual(move_a.move_dest_ids, move_b)

        # the moves stays on the same location
        self.assertEqual(move_a.location_dest_id, self.wh.wh_pack_stock_loc_id)
        self.assertEqual(move_b.location_id, self.wh.wh_pack_stock_loc_id)
        self.assertEqual(move_a.move_line_ids.location_dest_id,
                         self.location_pack_sub)
        self.assertEqual(move_b.move_line_ids.location_id,
                         self.location_pack_sub)
