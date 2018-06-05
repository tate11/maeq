# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('property_account_receivable_id')
    def _onchange_property_account_receivable_id(self):
        """
        Se realiza esto para manejar cuentas seperadas de Proveedor/Cliente
        :return: self
        """
        if self.property_account_receivable_id:
            self.property_account_payable_id = self.property_account_receivable_id.id

    origen_income = fields.Selection([('b', 'Empleado Público'),
                                      ('v', 'Empleado Privado'),
                                      ('i', 'Independiente'),
                                      ('a', 'Ama de casa o Estudiante'),
                                      ('r', 'Rentista'),
                                      ('h', 'Jubilado'),
                                      ('m', 'Remesas del exterior'), ], string='Origen de ingreso')
    client_type = fields.Selection([('maeq', 'MAEQ S.A'), ('direct', 'Directo'), ('special', 'Especial')],
                                   string='Tipo de cliente')
    client_segmentation = fields.Selection([
        ('agentes_publicidad', 'Agentes de Publicidad'),
        ('agroindustrial', 'Agroindustrial'),
        ('automotriz', 'Automotriz'),
        ('autoservicios', 'Autoservicios'),
        ('cadena_comercial', 'Cadena Comercial'),
        ('centro_comercial', 'Centro Comercial'),
        ('consumo_masivo', 'Consumo Masivo'),
        ('construccion', 'Construcción'),
        ('educacion', 'Educación'),
        ('financiero', 'Financiero'),
        ('hoteleria_turismo', 'Hotelería y Turismo'),
        ('industrial', 'Industrial'),
        ('salud', 'Salud'),
        ('sector_publico', 'Sector Público'),
        ('servicios', 'Servicios'),
        ('tecnologia', 'Tecnología'),
        ('tecnologico', 'Tecnológico'),
        ('telecomunicaciones', 'Telecomunicaciones'),
        ('textil', 'Textil')],
        string='Segmentación de cliente')
    # TODO: Para que sirve
    type_seller = fields.Selection([('consultant', 'Asesor'), ('freelance', 'FreeLance')], 'Tipo de vendedor',
                                   default='consultant')
    freelance_id = fields.Many2one('res.partner', string='Freelance')
    is_contact = fields.Boolean('Es contacto?')
    credit_limit = fields.Float('Cupo de crédito')
    if_freelance = fields.Boolean('FreeLance')
    consultant_id = fields.Many2one('hr.employee', string='Asesor')

    property_account_receivable_id = fields.Many2one('account.account',
                                                     string='Cuenta a cobrar',
                                                     domain=[('account_type', '=', 'movement')])
