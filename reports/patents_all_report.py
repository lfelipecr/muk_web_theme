# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from datetime import date, datetime

PAY_LINES_PER_PAGE = 20
date_month = {
    '1': 'Enero',
    '2': 'Febrero',
    '3': 'Marzo',
    '4': 'Abril',
    '5': 'Mayo',
    '6': 'Junio',
    '7': 'Julio',
    '8': 'Agosto',
    '9': 'Setiembre',
    '10': 'Octubre',
    '11': 'Noviembre',
    '12': 'Diciembre',
}

class PrintReportPatentsAllFinancial(models.AbstractModel):
    _name = 'report.l10n_cr_municipality_extend.report_patent_financial'
    _description = 'Reporte de Patentes'


    def _get_report_data(self, data):
        #El campo ocultar permite mostrar o no según sea el caso, el campo TOTAL PAGADO HOY
        ocultar = False
        if data['form']['mode']=='all':
            dates = 'Hasta hoy'
        else:
            dates = 'Del ' + str(data['form']['date_from']) + ' / al ' + str(data['form']['date_to'])

        date_hoy = str(date.today().day)+' de ' + str(date_month[str(date.today().month)]) + ' del ' + str(date.today().year)

        if data['form']['regime_id']=='all':
            regimen='Todos'
        elif data['form']['regime_id']=='traditional':
            regimen = 'Tradicional'
        else:
            regimen = 'Simplificado'

        response = {
            'pages': 1,
            'fechas': dates,
            'fecha_hoy': date_hoy,
            'distrito': 'Todos' if data['form']['tipo_distrito'] == 'all' else (self._get_name_distrito(data['form']['district_ids']) if len(data['form']['district_ids'])==1 else 'Algunos seleccionados'),
            'actividad': 'Todas' if data['form']['tipo_actividad'] == 'all' else (self._get_name_actividad(data['form']['activity_ids']) if len(data['form']['activity_ids'])==1 else 'Algunas seleccionadas'),
            'regimen': regimen,
            'datas': self._response_sql(data['form']),
            'usuario': data['user']
        }
        return response


    @api.model
    def _get_report_values(self, docids, data=None):
        return {'data': self._get_report_data(data)}


    def _response_sql(self,data):
        p_fecha = '0' if data['mode'] == 'all' else 1
        p_fecha1 = data['date_from']
        p_fecha2 = data['date_to']
        p_distrito = 0 if data['tipo_distrito']=='all' else 1
        if data['tipo_distrito'] == 'all':
            p_distrito_ids = '(' + str(1) + ')'
        else:
            p_distrito_ids = '(' + str(data['district_ids'][0]) + ')' if len(data['district_ids']) == 1 else tuple(data['district_ids'])

        p_actividad = 0 if data['tipo_actividad'] == 'all' else 1
        if data['tipo_actividad'] == 'all':
            p_actividad_ids = '(' + str(1) + ')'
        else:
            p_actividad_ids = '(' + str(data['activity_ids'][0]) + ')' if len(data['activity_ids']) == 1 else tuple(data['activity_ids'])

        p_regimen = data['regime_id']


        sql = """
                select
                    p.id, 
                    p."name" as numero,
                    pt."name" as tipo,
                    rp."name" as patentado,
                    p.fantasy_name as negocio,
                    (case when p.regimen='traditional' then 'Tradicional' else 'Simplificado' end) as regimen,
                    coalesce(rcd."name",'No especificado') as distrito,
                    p.yearly_payment/4 as trimestre_payment ,
                    p.yearly_payment
                    from l10n_cr_patent p 
                    inner join l10n_cr_patent_type pt on p.type_id = pt.id
                    inner join res_partner rp on p.partner_id = rp.id
                    left join res_country_district rcd on p.district_id = rcd.id
                    inner join l10n_cr_ciiu_l10n_cr_patent_rel rel on rel.l10n_cr_patent_id = p.id
                    --inner join l10n_cr_ciiu ciiu on ciiu.id = rel.l10n_cr_ciiu_id  
                    where p.state = 'approved'
                    and (case when '{0}' = '0' then True else (p.resolution_date between '{1}' and '{2}') end)
                    and (case when {3} = 0 then True else rcd.id in {4} end)
                    and (case when {5} = 0 then True else rel.l10n_cr_ciiu_id in {6} end) 
                    and (case when '{7}' = 'all' then true else p.regimen = '{7}' end)
                    group by p.id, 
                    p."name" ,
                    pt."name" ,
                    rp."name" ,
                    p.fantasy_name ,
                    p.regimen ,
                    rcd."name",
                    p.yearly_payment/4 ,
                    p.yearly_payment
                    order by 1 asc
              """.format(p_fecha, p_fecha1, p_fecha2, p_distrito, p_distrito_ids, p_actividad, p_actividad_ids, p_regimen)
        self.env.cr.execute(sql)
        response = self.env.cr.dictfetchall()
        return response

    def _get_name_actividad(self,id):
        act = self.env['l10n_cr.ciiu'].sudo().browse(id)
        return act.name

    def _get_name_distrito(self,id):
        dis = self.env['res.country.district'].sudo().browse(id)
        return dis.name


