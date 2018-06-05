# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        """
        Modificamos la creación de usuario
        :param vals:
        :return: object
        """
        self = self.with_context(no_users=True)
        res = super(Users, self).create(vals)
        return res
