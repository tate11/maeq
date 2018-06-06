# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

class Supplies(models.Model):
    _name = 'eliterp.maintenance.machines.supplies'
    _description = 'Insumos para el mantenimiento de máquinas'

    product_id = fields.Many2one('product.product', domain=[('purchase_ok', '=', True)], string='Producto')
    product_quantity = fields.Float('Cantidad', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', string='Unidad de medida')
    maintenance_machines_id = fields.Many2one('eliterp.maintenance.machines', string='Mantenimiento')

class MaintenanceMachines(models.Model):
    _name = 'eliterp.maintenance.machines'
    _description = 'Mantenimiento de máquinas'

    name = fields.Char('Nombre', default='Nuevo')
    date = fields.Date('Fecha', default=fields.Date.context_today, required=True)
    machine_id = fields.Many2one('eliterp.machine', string='Máquina', domain=[('state', '!=', 'in maintenance')], required=True)
    responsable = fields.Selection([('internal', 'Interno'), ('external', 'Externo')], string='Tipo gestor', default='internal')
    type = fields.Selection([('preventive', 'Preventivo'), ('corrective', 'Correctivo')], string='Tipo de mantenimiento')
    employee_id = fields.Many2one('hr.employee', string='Responsable')
    customer_id = fields.Many2one('res.partner', string='Responsable', domain=[('supplier', '=', True)])
    horometro_real = fields.Float('Horómetro actual', related='machine_id.horometro_real')
    next_maintenance_horometro = fields.Float('Horómetro siguiente mantenimiento', required=True)
    invoice_id = fields.Many2one('account.invoice', string='Factura relacionada')
    file = fields.Binary('Adjunto')
    file_name = fields.Char('Nombre del adjunto')
    supplies = fields.One2many('eliterp.maintenance.machines.supplies', 'maintenance_machines_id', string='Insumos')
    state = fields.Selection([('draft', 'Borrador'), ('validate', 'Validado')], string='Estado', default='draft')
    comment = fields.Text('Notas y comentarios')