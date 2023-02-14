# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields,_
from odoo.exceptions import UserError,ValidationError
TYPE = [('all','Hasta la fecha'),('range','Rango de Fechas')]
TYPE_DISTRICT = [('all','Todos'),('selected',u'Prefiero seleccionar')]
from odoo.tests import common, Form
from datetime import date, datetime
class PantetInteresWizard(models.TransientModel):
    _name = "patent.interes.wizard"

    invoice_id = fields.Many2one('account.move', store=True, readonly=True,string='Factura')
    patent_id = fields.Many2one('l10n_cr.patent',store=True, readonly=True, string='Patente',compute='_compute_amount')
    invoice_line_ids = fields.Many2many('account.move.line')

    currency_id = fields.Many2one('res.currency',related='invoice_id.currency_id')
    amount_interes_total = fields.Monetary()
    amount_patente_total = fields.Monetary()
    amount_patente_mas_interes = fields.Monetary()

    check_project = fields.Boolean(string='Proyectar interes')
    date_interes = fields.Date('Fecha a proyectar')

    def procces_default_values(self):
        product_intereses_id = self.env.ref('l10n_cr_municipality_extend.product_intereses').id
        if 'active_ids' in self.env.context:
            invoice_ids = self.env['account.move'].sudo().browse(self.env.context['active_ids'])
        else:
            invoice_ids = self.env['account.move'].sudo().browse(self.invoice_id.ids)
        for inv in invoice_ids:
            self.invoice_id = inv
            self.patent_id = inv.patent_id
            self.patent_id._caculate_interes_by_move(inv,'not_assign',self.invoice_id.date_interes)
            self.invoice_line_ids = [(6,0,inv.invoice_line_ids.filtered(lambda l: l.trimestre > 0).ids)]
            self.amount_interes_total += sum(line.interes for line in self.invoice_line_ids)
            self.amount_patente_total += sum(inv.invoice_line_ids.filtered(lambda l: l.product_id.id != product_intereses_id).mapped('price_subtotal'))
            #self.amount_patente_total += sum(line.price_subtotal for line in inv.invoice_line_ids)
            self.amount_patente_mas_interes = self.amount_interes_total + self.amount_patente_total
            #self.amount_interes_total = inv.invoice_line_ids.filtered(lambda l: l.product_id.id == product_intereses_id).price_unit
    #        #inv._caculate_interes()
    #
    #
    # @api.model
    # def default_get(self, fields):
    #     res = super(PantetInteresWizard, self).default_get(fields)
    #     if 'active_ids' in self.env.context:
    #         invoice_ids = self.env['account.move'].sudo().browse(self.env.context['active_ids'])
    #     else:
    #         invoice_ids = self.env['account.move'].sudo().browse(self.invoice_id.ids)
    #
    #     res['patent_id'] = self.invoice_id.patent_id
    #     #self.patent_id =
    #     self._calculate_totals(self.invoice_id.date_interes)
    #
    #     return res


    @api.depends('invoice_id')
    def _compute_amount(self):
        self.procces_default_values()

    def process_rate(self):
        if self.invoice_id and self.patent_id:
            self.patent_id._caculate_interes_by_move(self.invoice_id, 'assign',self.invoice_id.date_interes)
            pass
            #self.invoice_id._caculate_interes()
            #Por ahora se comenta


    def project_interes_calculate(self):
        if self.invoice_id and self.patent_id and self.check_project and self.date_interes:
            return self._calculate_totals(self.date_interes)

    def project_interes_re_calculate(self):
        self.check_project = False
        self.date_interes = False
        if self.invoice_id and self.patent_id and not self.check_project and not self.date_interes:
            return self._calculate_totals(self.invoice_id.date_interes)



    # @api.onchange('check_project')
    # def _onchange_check_project(self):
    #     if not self.check_project:
    #         return self._calculate_totals(self.invoice_id.date_interes)


    def _calculate_totals(self,date):
        inv = self.invoice_id
        self.patent_id = inv.patent_id
        # Todo en cero
        #self.write({'invoice_line_ids': [(6,0,[])]})
        self.amount_interes_total = 0.0
        self.amount_patente_total = 0.0
        self.amount_patente_mas_interes = 0.0

        # Calculo
        self.patent_id._caculate_interes_by_move(self.invoice_id, 'not_assign', date)

        # Asignacion de totales
        #self.write({'invoice_line_ids': [(6, 0, inv.invoice_line_ids.filtered(lambda l: l.trimestre > 0).ids)]})
        product_intereses_id = self.env.ref('l10n_cr_municipality_extend.product_intereses').id

        self.invoice_line_ids = [(6,0,inv.invoice_line_ids.filtered(lambda l: l.trimestre > 0).ids)]
        self.amount_interes_total += sum(line.interes for line in self.invoice_line_ids)
        self.amount_patente_total += sum(inv.invoice_line_ids.filtered(lambda l: l.product_id.id != product_intereses_id).mapped('price_subtotal'))
        #self.amount_patente_total += sum(line.price_subtotal for line in inv.invoice_line_ids)
        self.amount_patente_mas_interes = self.amount_interes_total + self.amount_patente_total

        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_id": self.id,
            "res_model": "patent.interes.wizard",
            #"context": context,
            "target": "new",
        }