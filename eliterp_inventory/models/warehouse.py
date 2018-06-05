# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    # Cambiar las secuencias a la creación de bodegas
    def _get_sequence_values(self):
        return {
            'in_type_id': {'name': self.name + ' ' + _('Sequence in'), 'prefix': self.code + '-ING-', 'padding': 5},
            'out_type_id': {'name': self.name + ' ' + _('Sequence out'), 'prefix': self.code + '-EGR-',
                            'padding': 5},
            'pack_type_id': {'name': self.name + ' ' + _('Sequence packing'), 'prefix': self.code + '-PAC-',
                             'padding': 5},
            'pick_type_id': {'name': self.name + ' ' + _('Sequence picking'), 'prefix': self.code + '-PIC-',
                             'padding': 5},
            'int_type_id': {'name': self.name + ' ' + _('Sequence internal'), 'prefix': self.code + '-INT-',
                            'padding': 5},
        }
