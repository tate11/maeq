# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError

STATES = [
    ('operative', 'Operativa'),
    ('operative_failures', 'Operativa con fallas'),
    ('repair', 'Reparación'),
    ('out_of_service', 'Fuera de servicio')
]


class MachinesModel(models.Model):
    _name = 'eliterp.table.maintenance'
    _description = 'Tabla de mantenimiento por modelo'

    name = fields.Char('Nombre', required=True)
    model_id = fields.Many2one('eliterp.machines.model', string='Modelo')


class MachinesModel(models.Model):
    _name = 'eliterp.machines.model'
    _description = 'Modelo de máquinas'

    name = fields.Char('Nombre', required=True)
    use = fields.Char('Uso')
    description = fields.Text('Descripción')
    machines_brand_id = fields.Many2one('eliterp.machines.brand', string='Máquina')
    table_maintenance = fields.One2many('eliterp.table.maintenance', 'model_id',
                                        string='Tabla de mantenimientos')

    _sql_constraints = [
        ('name_uinque', 'unique (name)', 'El Nombre del modelo debe ser único.')
    ]


class MachinesBrand(models.Model):
    _name = 'eliterp.machines.brand'
    _description = 'Marca de máquinas'

    @api.multi
    def action_view_machines(self):
        """
        Mostramos las máquinas asignadas a marca
        """
        self.ensure_one()
        action = self.env.ref('eliterp_operations.eliterp_action_operations_machines').read()[0]
        action['domain'] = [('machines_brand_id', '=', self.id)]
        return action

    name = fields.Char('Nombre', required=True)
    image = fields.Binary('Logo')
    short_name = fields.Char('Nombre corto', size=3, required=True)
    machines_quantity = fields.Integer('Nº máquinas', compute='_compute_machines_quantity')
    machines_ids = fields.One2many('eliterp.machine', 'machines_brand_id', string='Máquinas')
    models_ids = fields.One2many('eliterp.machines.model', 'machines_brand_id', string='Modelos')
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')

    @api.one
    def _compute_machines_quantity(self):
        """
        Calculamos la cantidad de máquinas por marca
        """
        self.machines_quantity = len(self.machines_ids)

    _sql_constraints = [
        ('short_name_uinque', 'unique (short_name)', 'El Nombre corto de la marca debe ser único.')
    ]


class LinesHistoryMachine(models.Model):
    _name = 'eliterp.lines.history.machine'
    _description = 'Líneas de historial de la máquinas'

    type = fields.Selection([
        ('horometro', 'Horómetro'),
        ('piece', 'Pieza'),
        ('operator', 'Operador')
    ], string='Tipo de historial', required=True)
    description = fields.Text('Descripción', required=True)
    machine_id = fields.Many2one('eliterp.machine', 'Máquina')


class Machine(models.Model):
    _name = 'eliterp.machine'
    _description = 'Máquinas'
    _inherit = ['mail.thread']

    @api.depends('cmc_ids', 'horometro_initial')
    @api.one
    def _get_horometro_real(self):
        """
        Obtenemos el horometro real de la máquina
        """
        cmc_ids = self.cmc_ids.filtered(lambda x: x.state == 'validate')
        if cmc_ids:
            self.horometro_real = cmc_ids[-1]['final_horometro']
        else:
            self.horometro_real = self.horometro_initial

    @api.multi
    def toggle_active(self):
        """
        Activar o inactivar máquina
        """
        for record in self:
            record.active = not record.active

    @api.depends('cmc_ids')
    @api.one
    def _get_count_cmc(self):
        """
        Obtenemos la cantidad de cmc's
        """
        if self.cmc_ids:
            self.count_cmc = len(self.cmc_ids)

    def _default_new_currency(self):
        return self.env['res.currency'].search([('name', '=', 'USD')])[0].id

    name = fields.Char('Nombre', copy=False, size=6, required=True)
    machines_brand_id = fields.Many2one('eliterp.machines.brand', string='Marca', required=True)
    machines_model_id = fields.Many2one('eliterp.machines.model', string='Modelo', required=True)
    state = fields.Selection(STATES, string="Estado", default='operative')
    image = fields.Binary('Imagen')
    horometro_initial = fields.Float('Horómetro inicial', default=0)
    horometro_real = fields.Float('Horómetro actual', compute='_get_horometro_real')
    type = fields.Selection([('own', 'Propia'), ('rented', 'Alquilada')], default='own', string="Tipo de activo")
    serie = fields.Char("Serie")
    registration = fields.Char("Matrícula", required=True)
    acquisition_date = fields.Date('Fecha de adquisición', required=True)

    catalog_value = fields.Monetary('Valor de catálogo', currency_field='currency_id')
    residual_value = fields.Monetary('Valor residual', currency_field='currency_id')

    model_motor = fields.Char('Modelo del motor')
    year_motor = fields.Integer('Año del motor', size=4)
    power = fields.Float('Potencia')

    cabin_weight = fields.Float('Peso con cabina')
    roof_weight = fields.Float('Peso con techo')

    currency_id = fields.Many2one('res.currency', string='Moneda', default=_default_new_currency)
    height = fields.Float('Altura')
    width = fields.Float('Ancho')
    longitude = fields.Float('Longitud')

    active = fields.Boolean(default=True, help="Se debe poner cómo inactiva cuando la máquina no se va a usar "
                                               "o se vendío.")
    cmc_ids = fields.One2many('eliterp.cmc', 'machine_id', string="Listado de CMC's")
    count_cmc = fields.Integer("'Nº de CMC's", compute='_get_count_cmc')
    lines_history = fields.One2many('eliterp.lines.history.machine', 'machine_id', string="Historial de la máquinas")

    _sql_constraints = [
        ('name_uinque', 'unique (machines_brand_id, name, active)', 'El Nombre debe ser único por marca y estado.')
    ]
