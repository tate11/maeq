# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.exceptions import UserError
from odoo import api, fields, models, _


class ProductCode(models.Model):
    _name = 'eliterp.product.code'

    _description = 'Código de producto'

    @api.one
    def _get_count_products(self):
        """
        Obtenemos la cantidad de productos de este código
        """
        if self.products_ids:
            self.count_products = len(self.products_ids)

    name = fields.Char('Código')
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')
    products_ids = fields.One2many('product.template', 'product_code_id', 'Productos')
    count_products = fields.Char('Nº de productos', compute='_get_count_products')


class LineProduct(models.Model):
    _name = 'eliterp.line.product'

    _description = 'Línea de producto'

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        if 'default_level_upper' in context:
            if context['default_level_upper'] == False:
                raise UserError("No puede crear una Línea de producto sin escoger una categoría.")
        return super(LineProduct, self).create(vals)

    name = fields.Char('Línea')
    level_upper = fields.Many2one('product.category', string='Categoría', readonly=True)


class SubLineProduct(models.Model):
    _name = 'eliterp.sub.line.product'

    _description = 'SubLínea de producto'

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        if 'default_level_upper' in context:
            if context['default_level_upper'] == False:
                raise UserError("No puede crear una SubLínea de producto sin escoger una línea.")
        return super(SubLineProduct, self).create(vals)

    name = fields.Char(u'SubLínea')
    level_upper = fields.Many2one('eliterp.line.product', string='Línea', readonly=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('type')
    def _onchange_type(self):
        """
        MM: TODO
        """
        self.track_service = 'manual'

    @api.model
    def create(self, vals):
        category = self.env['product.category'].browse(vals['categ_id']).name
        line = self.env['eliterp.line.product'].browse(vals['line_product_id']).name
        subline = self.env['eliterp.sub.line.product'].browse(vals['sub_line_product_id']).name
        name_code = (category[:3]).upper() + "-" + (line[:3]).upper() + "-" + (subline[:3]).upper()
        product_code = self.env['eliterp.product.code'].search([('name', '=', name_code)])
        if len(product_code._ids) != 0:  # Si existe código se actualiza siguiente número
            sequence_code = (category[:3]).upper() + "." + (line[:3]).upper() + "." + (subline[:3]).upper()
            object_sequence = self.env['ir.sequence']
            sequence = object_sequence.next_by_code(sequence_code)
            vals.update({
                'default_code': sequence,
                'product_code_id': product_code.id
            })
        else:
            sequence_code = (category[:3]).upper() + "." + (line[:3]).upper() + "." + (subline[:3]).upper()
            new_sequence = self.env['ir.sequence'].create({
                'name': "Código de producto " + name_code,
                'code': sequence_code,
                'prefix': name_code,
                'padding': 5
            })
            new_code = self.env['eliterp.product.code'].create({
                'name': name_code,
                'sequence_id': new_sequence.id
            })
            object_sequence = self.env['ir.sequence']
            sequence = object_sequence.next_by_code(sequence_code)
            vals.update({
                'default_code': sequence,
                'product_code_id': new_code.id
            })
        return super(ProductTemplate, self).create(vals)

    line_product_id = fields.Many2one('eliterp.line.product', 'Línea', required=True)
    sub_line_product_id = fields.Many2one('eliterp.sub.line.product', 'SubLínea', required=True)
    product_code_id = fields.Many2one('eliterp.product.code', 'Código interno')
    measure = fields.Text('Medida del producto')
