# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields,_
from odoo.exceptions import UserError,ValidationError
TYPE = [('all','Hasta la fecha'),('range','Rango de Fechas')]
TYPE_DISTRICT = [('all','Todos'),('selected',u'Prefiero seleccionar')]

class DistrictFinancialDownloadWizard(models.TransientModel):
    _name = "district.financial.download.wizard"
    _description = 'Reportes financiero para Patentes por distrito'

    mode = fields.Selection(TYPE, string='Tipo', default='all')
    date_from = fields.Date('Fecha inicio',default=fields.Date.context_today)
    date_to = fields.Date('Fecha fin',default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string='Compañia', readonly=True, default=lambda self: self.env.company)
    county_id = fields.Many2one('res.country.county', related='company_id.county_id', readonly=False)
    tipo_distrito = fields.Selection(TYPE_DISTRICT,string='¿Qué distritos desea filtrar?',default='all')
    district_ids = fields.Many2many('res.country.district',string=u'Distritos')

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        if self.mode == 'range':
            if not self.date_from <= self.date_to:
                raise ValidationError(_('La fecha de inicio debe ser menor a la fecha de fin.'))


    def print_report(self):
        self.ensure_one()

        [data] = self.read()
        datas = {
            'user': self.env.user.display_name or self.env.user.partner_id.display_name,
            'form': data
        }
        response = self.env.ref('l10n_cr_municipality_extend.action_print_patent_district_payment').report_action([],data=datas)
        return response


