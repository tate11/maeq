# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from datetime import datetime
from odoo import api, models

class ReportWithholdPurchase(models.AbstractModel):
    _name = 'report.eliterp_treasury.eliterp_report_withhold_purchase'

    @staticmethod
    def _get_total(lines):
        return sum(line.amount for line in lines)

    @staticmethod
    def _get_fiscal_year(date):
        object_datetime = datetime.strptime(date, "%Y-%m-%d")
        return object_datetime.year

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('eliterp_treasury.eliterp_report_withhold_purchase')
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self,
        }
        return report_obj.render('eliterp_treasury.eiterp_report_withhold_purchase', docargs)

    # 'get_fiscal_year': self._get_fiscal_year,
    # 'get_total': self._get_total,
