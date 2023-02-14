# -*- coding: utf-8 -*-
from odoo import _, fields, models


class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    payment_methods_id = fields.Many2one(comodel_name="payment.methods",string=u'Método de Pago')
    representante_name = fields.Char(string='Representante legal ')
    representante_identity = fields.Char(string=u'Identificación ')

