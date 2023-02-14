# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields,_
from odoo.exceptions import UserError,ValidationError
TYPE = [('all','Hasta la fecha'),('range','Rango de Fechas')]
TYPE_DISTRICT = [('all','Todos'),('selected',u'Prefiero seleccionar')]
TYPE_ACTIVITY = [('all','Todas'),('selected',u'Prefiero seleccionar')]
REGIMEN = [("all",'Todos'),("simplified", "Simplificado"),("traditional", "Tradicional")]

class PatentFinancialDownloadWizard(models.TransientModel):
    _name = "patent.financial.download.wizard"
    _description = 'Reportes financiero para Patentes'

    mode = fields.Selection(TYPE, string='Tipo', default='all')
    date_from = fields.Date('Fecha inicio',default=fields.Date.context_today)
    date_to = fields.Date('Fecha fin',default=fields.Date.context_today)
    tipo_distrito = fields.Selection(TYPE_DISTRICT,string='¿Qué distritos desea filtrar?',default='all')
    company_id = fields.Many2one('res.company', string='Compañia', readonly=True, default=lambda self: self.env.company)
    county_id = fields.Many2one('res.country.county', related='company_id.county_id', readonly=False)
    district_ids = fields.Many2many('res.country.district',string=u'Distritos')
    tipo_actividad = fields.Selection(TYPE_ACTIVITY,string=u'¿Qué actividad desea filtrar?',default='all')
    activity_ids = fields.Many2many('l10n_cr.ciiu',string=u'Actividades')
    regime_id = fields.Selection(REGIMEN, string=u'Régimen',default='all')

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
        response = self.env.ref('l10n_cr_municipality_extend.action_print_patent_payment').report_action([],data=datas)
        return response


