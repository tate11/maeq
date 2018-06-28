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

    project_id = fields.Many2one('eliterp.project', 'Proyecto')

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        for r in move_lines:  # Si son la misma fila actualizar proyecto
            for line in self.invoice_line_ids:
                if r[2]['analytic_account_id'] == line.account_analytic_id.id and line.project_id:
                    r[2].update({'project_id': line.project_id.id})
        return move_lines


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class TravelAllowanceRequest(models.Model):
    _inherit = 'eliterp.travel.allowance.request'

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


# Manejar esto por MAEQ (Línea dónde se seleccina la cuenta)
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')


class LinesDepositsCheck(models.Model):
    _inherit = 'eliterp.lines.deposits.check'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class LinesDepositsCash(models.Model):
    _inherit = 'eliterp.lines.deposits.cash'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class LineDepositsChecksExternal(models.Model):
    _inherit = 'eliterp.lines.deposits.checks.external'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class LinesPayment(models.Model):
    _inherit = "eliterp.lines.payment"

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")


class LinesAccount(models.Model):
    _inherit = 'eliterp.lines.account'

    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')],
                                          string="Centro de costo")
