# -*- coding: utf-8 -*-

from odoo import fields, models, _, api
import calendar
from datetime import datetime , date

month_range = {
    '1': [1,2,3],
    '2': [4,5,6],
    '3': [7,8,9],
    '4': [10,11,12],
}

month_to_trimester = {
    "1": 1,
    "2": 1,
    "3": 1,
    "4": 2,
    "5": 2,
    "6": 2,
    "7": 3,
    "8": 3,
    "9": 3,
    "10": 4,
    "11": 4,
    "12": 4,
}

TRIMESTRES = [
    {'number': 1, 'description': 'Enero-Marzo'},
    {'number': 2, 'description': 'Abril-Junio'},
    {'number': 3, 'description': 'Julio-Setiembre'},
    {'number': 4, 'description': 'Octubre-Diciembre'},
]

timbre = 0.02 #TIMBRE 2 POR CIENTO
timbre_licor = 5000 #TIMBRE PARA LICORES 5000 COLONES

class L10ncrRecaudacion(models.Model):
    _name = "l10n_cr.recaudacion"
    _description = "Recaudacion de patentes"
    _order = 'trimestre asc'
    _rec_name = 'trimestre'

    trimestre = fields.Integer(string='Trimestre')
    descripcion = fields.Char(string='Comprende')
    aprobadas = fields.Integer('Patentes aprobadas')
    currency_id = fields.Many2one('res.currency',string='Moneda')
    monto_o = fields.Monetary(string='Monto a recaudar')
    monto_recaudado = fields.Monetary(string='Monto recaudado')
    porcentaje = fields.Char(string='Porcentaje')
    monto_interes = fields.Monetary(string='Monto interés')
    monto_recaudado_interes = fields.Monetary(string='Recaudado + Interés')
    monto_timbres = fields.Monetary(string='Monto timbres')
    #patent_ids = fields.Many2many('l10n_cr.patent','recaudacion_patents_rel','recaudacion_id','patent_id')
    #invoice_ids = fields.Many2many('account.move','recaudacion_invoices_rel','recaudacion_id','invoice_id')


    def _get_data(self):
        self._cr.execute("delete from l10n_cr_recaudacion")
        #self._cr.execute("delete from recaudacion_patents_rel")
        #self._cr.execute("delete from recaudacion_invoices_rel")
        paids_lines = self.env['l10n_cr.patent.lines'].sudo().search([])
        patent_ids = self.env['l10n_cr.patent'].sudo().search([('state','=','approved')])

        PATENTES = [
            self.env.ref('l10n_cr_municipality.product_patent').id,
            self.env.ref('l10n_cr_municipality.product_patent_advance').id,
            self.env.ref('l10n_cr_municipality.product_patent_liqueur').id,
            self.env.ref('l10n_cr_municipality.product_patent_liqueur_advance').id
        ]

        product_timbre_id = self.env.ref('l10n_cr_municipality.product_timbre').id
        product_timbre_licor_id = self.env.ref('l10n_cr_municipality.product_timbre_licores').id

        for t in TRIMESTRES:
            monto_a_recaudar = 0.0
            monto_recaudado = 0.0
            monto_interes = 0.0
            monto_timbres = 0.0


            def _get_range(fecha_aprobacion):
                meses = month_range[str(t['number'])]
                monthRange = calendar.monthrange(datetime.now().year, meses[2])
                first_date = date(datetime.now().year, meses[0], 1)
                last_date = date(datetime.now().year,  meses[2], monthRange[1])
                total_day = (last_date - first_date).days
                days_to_end = (last_date - fecha_aprobacion).days
                return days_to_end / total_day

            patentes_aprobadas = 0
            for patent in patent_ids:
                if patent.id == 8:
                    a=1
                pago_trimestral = patent.trimester_payment
                fecha_aprobacion = patent.date_approved
                mes_aprobacion = fecha_aprobacion.month
                trimestre_aprobacion = month_to_trimester[str(mes_aprobacion)]

                if t['number'] == trimestre_aprobacion:
                    percentage = _get_range(fecha_aprobacion)
                    monto_a_recaudar += pago_trimestral * percentage
                    patentes_aprobadas+=1
                elif t['number'] < trimestre_aprobacion:
                    monto_a_recaudar += 0.0
                elif t['number'] > trimestre_aprobacion:
                    monto_a_recaudar += pago_trimestral
                else:
                    monto_a_recaudar += 0.0

                invoices = patent.invoices_ids
                if invoices:
                    for inv in invoices:
                        #if inv.state == 'posted' and inv.payment_state in ('partial','paid'):
                        if inv.state == 'posted' and inv.payment_state == 'paid' and inv.move_type == 'out_invoice' and not inv.reversal_move_id and not inv.reversed_entry_id:
                            for line in inv.invoice_line_ids:
                                if line.trimestre == t['number'] and line.product_id.id in PATENTES:
                                    monto_recaudado += line.price_subtotal

                                if line.interes > 0 and line.trimestre == t['number']:
                                    monto_interes += line.interes

                            lines_timbres = inv.invoice_line_ids.filtered(lambda l: l.product_id.id == product_timbre_id).mapped('move_id').mapped('invoice_line_ids')
                            amount_timbres = sum(lines_timbres.filtered(lambda l: l.trimestre == t['number'] and
                                                                      l.product_id.id in PATENTES).mapped('price_subtotal')) * timbre

                            invoice_licor_timbres = inv.invoice_line_ids.filtered(lambda l: l.product_id.id == product_timbre_licor_id).mapped('move_id')

                            amount_timbre_licor = 0.0
                            for inv_licor in invoice_licor_timbres:
                                lines_patent = inv_licor.invoice_line_ids.filtered(lambda l: l.product_id.id in PATENTES)
                                monto_por_trimestre = timbre_licor / len(lines_patent)
                                if lines_patent:
                                    for line2 in lines_patent:
                                        if line2.trimestre == t['number']:
                                            amount_timbre_licor += monto_por_trimestre

                            monto_timbres += (amount_timbre_licor + amount_timbres)

            #patents_ids = paids_lines.mapped('patent_id').ids
            #invoice_ids = pagos.mapped('factura_id').ids
            dict_rec = {
                'trimestre': t['number'],
                'descripcion': t['description'],
                'aprobadas': patentes_aprobadas,
                'currency_id': self.env.company.currency_id.id,
                'monto_o': monto_a_recaudar,
                'monto_recaudado': monto_recaudado,
                'porcentaje': str(round(((monto_recaudado*100)/monto_a_recaudar),2))+' %',
                'monto_interes': monto_interes,
                'monto_recaudado_interes': monto_recaudado + monto_interes,
                'monto_timbres': monto_timbres,
                #'patent_ids': [(6, 0, patents_ids)],
                #'invoice_ids': [(6, 0, invoice_ids)],
            }

            self.env['l10n_cr.recaudacion'].sudo().create(dict_rec)


