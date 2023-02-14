# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields,_
from datetime import date
import calendar
from odoo.exceptions import UserError,ValidationError
TYPE = [('range','Rango de Fechas'),('all','Hasta la fecha')]

class CashFinancialDownloadWizard(models.TransientModel):
    _name = "cash.financial.download.wizard"
    _description = 'Reportes financiero caja'

    mode = fields.Selection(TYPE, string='Tipo', default='all')
    date_from = fields.Date('Fecha inicio', default=fields.Date.context_today)
    date_to = fields.Date('Fecha fin', default=fields.Date.context_today)

    export_file = fields.Binary(string='File', readonly=True,
                                help="Generated XML file")
    export_filename = fields.Char(string='File name', readonly=True,
                                  help="Name of the generated XML file")

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        if self.mode == 'range':
            if not self.date_from <= self.date_to:
                raise ValidationError(_('La fecha de inicio debe ser menor a la fecha de fin.'))

    # @api.constrains('month_start', 'month_end')
    # def _check_date(self):
    #     if self.month_start and self.month_end:
    #         if int(self.month_start) > int(self.month_end):
    #             raise ValidationError(_('El mes de inicio debe ser menor o igual mes final.'))

    def print_report(self):
        self.ensure_one()

        if self.mode == 'all':
            domain = [('move_id.state', '=', 'posted'), ('move_type', '=', 'entry')]
        else:
            domain = [('move_id.state', '=', 'posted'), ('move_type', '=', 'entry'), ('move_id.date', '>=', self.date_from), ('move_id.date', '<=', self.date_to)]

        account_payment_ids = self.env['account.payment'].sudo().search(domain)

        if not account_payment_ids or account_payment_ids == False or len(account_payment_ids.ids) == 0:
            raise ValidationError(_('No se econtraron datos'))

        data = {
            'account_payment_ids': account_payment_ids.ids,
            'mode': self.mode,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.env.user.display_name or self.env.user.partner_id.display_name
        }
        response = self.env.ref('l10n_cr_municipality_extend.action_print_cash_payment').report_action(account_payment_ids, data=data)
        return response


