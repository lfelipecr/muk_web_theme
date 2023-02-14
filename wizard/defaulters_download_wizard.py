# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields,_
from datetime import date, datetime
from odoo.exceptions import UserError,ValidationError
TYPE = [('all','Hasta la fecha'),('select','Fecha determinada')]
month_to_trimester = {
    "1": "1",
    "2": "1",
    "3": "1",
    "4": "2",
    "5": "2",
    "6": "2",
    "7": "3",
    "8": "3",
    "9": "3",
    "10": "4",
    "11": "4",
    "12": "4",
}
trimester_to_letter = {
    '1': 'Primer trimestre',
    '2': 'Segundo trimestre',
    '3': 'Tercer trimestre',
    '4': 'Cuarto trimestre',
}
class DefaulterFinancialDownloadWizard(models.TransientModel):
    _name = "defaulter.financial.download.wizard"
    _description = 'Reportes financiero para morosos de patentes'

    # def _default_trimester(self):
    #     month_now = datetime.now().date().month
    #     return month_to_trimester[str(month_now)]
    #
    # mode = fields.Selection(TYPE, string='Tipo', default='all')
    # date_from = fields.Date('Fecha inicio')
    # date_to = fields.Date('Fecha fin')
    #
    # trimester = fields.Selection(
    #     selection=[
    #         ("t1", "Primer Trimestre"),
    #         ("t2", "Segundo Trimestre"),
    #         ("t3", "Tercer Trimestre"),
    #         ("t4", "Cuarto Trimestre"),
    #     ],string="Trimestre actual",required=True,default=_default_trimester,)
    def _default_trimester(self):
        month_now = datetime.now().date().month
        return int(month_to_trimester[str(month_now)])

    def _default_trimester_title(self):
        month_now = datetime.now().date().month
        trimester = month_to_trimester[str(month_now)]
        msg = 'Nos encontramos en el ' + trimester_to_letter[trimester] + '.'
        return msg

    trimestre_actual = fields.Integer(default=_default_trimester)
    title = fields.Char(default=_default_trimester_title)

    mode = fields.Selection(TYPE, string='Tipo', default='all')
    date = fields.Date('Fecha fin', default=fields.Date.context_today)




    # @api.constrains('date_from', 'date_to')
    # def _check_date(self):
    #     if self.mode == 'range':
    #         if not self.date_from <= self.date_to:
    #             raise ValidationError(_('La fecha de inicio debe ser menor a la fecha de fin.'))

    def print_report(self):
        self.ensure_one()

        # if self.mode == 'all':
        #     domain = [('move_id.state','=','posted'),('move_type','=','entry')]
        # else:
        #     domain = [('move_id.state', '=', 'posted'),('move_type','=','entry'),('move_id.date', '>=', self.date_from), ('move_id.date', '<=', self.date_to)]
        #
        # account_payment_ids = self.env['account.payment'].sudo().search(domain)

        data = {
            'user': self.env.user.display_name or self.env.user.partner_id.display_name,
            'trimester': trimester_to_letter[str(self.trimestre_actual)],
            'mode': self.mode,
            'date': self.date,
        }
        response = self.env.ref('l10n_cr_municipality_extend.action_print_patent_defaulter_payment').report_action([], data=data)
        return response


