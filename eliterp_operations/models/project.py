# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _
import json


class Work(models.Model):
    _name = 'eliterp.work'

    _description = 'Obra'

    name = fields.Char('Nombre', required=True)

    _sql_constraints = [
        ('name_unique', 'unique (name)', "El Nombre de la obra debe ser único.")
    ]


class Location(models.Model):
    _name = 'eliterp.location'

    _description = 'Ubicaciones'

    name = fields.Char('Nombre ubicación', required=True)
    project_id = fields.Many2one('eliterp.project', string='Proyecto')


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    project_id = fields.Many2one('eliterp.project', 'Proyecto', states={'draft': [('readonly', False)]})


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Centro de costo")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Centro de costo")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')


class EliterpProject(models.Model):
    _name = 'eliterp.project'

    _description = 'Proyecto'

    name = fields.Char('Nombre de proyecto', required=True)
    code = fields.Char('Código', required=True)
    reference = fields.Char('Referencia')
    customer = fields.Many2one('res.partner', string="Cliente",
                               domain=[('is_contact', '=', False), ('customer', '=', True)])
    account_analytic_id = fields.Many2one('account.analytic.account', string="Centro de costo", required=True)
    lines_location = fields.One2many('eliterp.location', 'project_id', string='Ubicaciones')

    _sql_constraints = [
        ('code_unique', 'unique (code)', "El Código del proyecto debe ser único.")
    ]
