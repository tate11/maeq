# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def print_picking(self):
        """
        Imprimimo operación de bodega
        """
        self.ensure_one()
        if self.picking_type_code == 'outgoing':  # Egreso
            return self.env.ref('eliterp_inventory.eliterp_action_report_stock_picking_egre').report_action(self)
        elif self.picking_type_code == 'incoming':  # Ingreso
            return self.env.ref('eliterp_inventory.eliterp_action_report_stock_picking_ingr').report_action(self)
        else:  # Transferencia
            return self.env.ref('eliterp_inventory.eliterp_action_report_stock_picking_trans').report_action(self)
