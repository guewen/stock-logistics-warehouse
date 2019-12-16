# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools import float_compare

from odoo.addons.base_sparse_field.models.fields import Serialized

# TODO handle autofocus + easy way to validate for the input field


class VerticalLiftOperationInventory(models.Model):
    _name = "vertical.lift.operation.inventory"
    _inherit = "vertical.lift.operation.base"
    _description = "Vertical Lift Operation Inventory"

    current_inventory_line_id = fields.Many2one(
        comodel_name="stock.inventory.line", readonly=True
    )

    quantity_input = fields.Float()
    # if the quantity is wrong, user has to write 2 times
    # the same quantity to really confirm it's correct
    last_quantity_input = fields.Float()
    state = fields.Selection(
        selection=[
            ("quantity", "Inventory, please enter the amount"),
            ("confirm_wrong_quantity", "The quantity does not match, are you sure?"),
            ("save", "Save"),
        ],
        default="quantity",
    )

    tray_location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_tray_data",
        string="Tray Location",
    )
    tray_name = fields.Char(compute="_compute_tray_data", string="Tray Name")
    tray_type_id = fields.Many2one(
        comodel_name="stock.location.tray.type",
        compute="_compute_tray_data",
        string="Tray Type",
    )
    tray_type_code = fields.Char(compute="_compute_tray_data", string="Tray Code")
    tray_x = fields.Integer(string="X", compute="_compute_tray_data")
    tray_y = fields.Integer(string="Y", compute="_compute_tray_data")
    tray_matrix = Serialized(string="Cells", compute="_compute_tray_data")
    tray_qty = fields.Float(string="Stock Quantity", compute="_compute_tray_qty")

    # current operation information
    inventory_id = fields.Many2one(
        related="current_inventory_line_id.inventory_id", readonly=True
    )
    product_id = fields.Many2one(
        related="current_inventory_line_id.product_id", readonly=True
    )
    product_uom_id = fields.Many2one(
        related="current_inventory_line_id.product_uom_id", readonly=True
    )
    product_qty = fields.Float(
        related="current_inventory_line_id.product_qty", readonly=True
    )
    product_packagings = fields.Html(
        string="Packaging", compute="_compute_product_packagings"
    )
    package_id = fields.Many2one(
        related="current_inventory_line_id.package_id", readonly=True
    )
    lot_id = fields.Many2one(
        related="current_inventory_line_id.prod_lot_id", readonly=True
    )

    @api.depends("current_inventory_line_id")
    def _compute_tray_data(self):
        for record in self:
            location = record.current_inventory_line_id.location_id
            tray_type = location.location_id.tray_type_id
            # this is the current cell
            record.tray_location_id = location.id
            # name of the tray where the cell is
            record.tray_name = location.location_id.name
            record.tray_type_id = tray_type.id
            record.tray_type_code = tray_type.code
            record.tray_x = location.posx
            record.tray_y = location.posy
            record.tray_matrix = location.tray_matrix

    @api.depends("current_inventory_line_id.product_id.packaging_ids")
    def _compute_product_packagings(self):
        for record in self:
            if not record.current_inventory_line_id:
                record.product_packagings = ""
                continue
            product = record.current_inventory_line_id.product_id
            content = self._render_product_packagings(product)
            record.product_packagings = content

    @api.depends("tray_location_id", "current_inventory_line_id.product_id")
    def _compute_tray_qty(self):
        for record in self:
            if not (record.tray_location_id and record.current_inventory_line_id):
                record.tray_qty = 0.0
                continue
            product = record.current_inventory_line_id.product_id
            location = record.tray_location_id
            record.tray_qty = self._get_tray_qty(product, location)

    def _compute_number_of_ops(self):
        for record in self:
            line_model = self.env["stock.inventory.line"]
            record.number_of_ops = line_model.search_count(
                self._domain_inventory_lines_to_do()
            )

    def _compute_number_of_ops_all(self):
        for record in self:
            line_model = self.env["stock.inventory.line"]
            record.number_of_ops_all = line_model.search_count(
                self._domain_inventory_lines_to_do_all()
            )

    def _domain_inventory_lines_to_do(self):
        return [
            ("location_id", "child_of", self.location_id.id),
            ("state", "=", "confirm"),
            ("vertical_lift_done", "=", False),
        ]

    def _domain_inventory_lines_to_do_all(self):
        shuttle_locations = self.env["stock.location"].search(
            [("vertical_lift_kind", "=", "view")]
        )
        return [
            ("location_id", "child_of", shuttle_locations.ids),
            ("state", "=", "confirm"),
            ("vertical_lift_done", "=", False),
        ]

    def on_screen_open(self):
        """Called when the screen is open"""
        self.select_next_inventory_line()

    def reset(self):
        self.write(
            {"quantity_input": 0.0, "last_quantity_input": 0.0, "state": "quantity"}
        )
        self.update_step_description()

    def step(self):
        return self.state

    def step_to(self, state):
        self.state = state
        self.update_step_description()

    def step_description(self):
        state_field = self._fields["state"]
        return state_field.convert_to_export(self.state, self)

    def update_step_description(self):
        if self.current_inventory_line_id:
            descr = self.step_description()
        else:
            descr = _("No operations")
        self.operation_descr = descr

    def button_save(self):
        if not self.current_inventory_line_id:
            return
        self.ensure_one()
        self.process_current()
        if self.step() == "save":
            self.select_next_inventory_line()
            if not self.current_inventory_line_id:
                # sorry not sorry
                return {
                    "effect": {
                        "fadeout": "slow",
                        "message": _("Congrats, you cleared the queue!"),
                        "img_url": "/web/static/src/img/smile.svg",
                        "type": "rainbow_man",
                    }
                }

    def button_release(self):
        raise NotImplementedError

    def _has_identical_quantity(self):
        line = self.current_inventory_line_id
        return (
            float_compare(
                line.theoretical_qty,
                self.quantity_input,
                precision_rounding=line.product_uom_id.rounding,
            )
            == 0
        )

    def _process_quantity(self):
        if self.step() == "quantity":
            if self._has_identical_quantity():
                self.step_to("save")
                return True
            else:
                self.last_quantity_input = self.quantity_input
                self.quantity_input = 0.0
                self.step_to("confirm_wrong_quantity")
                return False
        if self.step() == "confirm_wrong_quantity":
            if self.quantity_input == self.last_quantity_input:
                # confirms the previous input
                self.step_to("save")
                return True
            else:
                # cycle back to the first quantity check
                self.step_to("quantity")
                return self._process_quantity()

    def process_current(self):
        line = self.current_inventory_line_id
        if self._process_quantity() and not line.vertical_lift_done:
            line.vertical_lift_done = True
            if self.quantity_input != line.product_qty:
                line.product_qty = self.quantity_input
            inventory = line.inventory_id
            if all(line.vertical_lift_done for line in inventory.line_ids):
                inventory.action_validate()

    def fetch_tray(self):
        location = self.current_inventory_line_id.location_id
        location.fetch_vertical_lift_tray()

    def select_next_inventory_line(self):
        self.ensure_one()
        next_line = self.env["stock.inventory.line"].search(
            self._domain_inventory_lines_to_do(),
            limit=1,
            order="vertical_lift_tray_id, location_id, id",
        )
        previous_line = self.current_inventory_line_id
        self.current_inventory_line_id = next_line
        self.reset()
        if (
            next_line
            and previous_line.vertical_lift_tray_id != next_line.vertical_lift_tray_id
        ):
            self.fetch_tray()
