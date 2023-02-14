# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    
    def _default_method_paid(self):
        r = False
        for pay in self:
            if not pay.payment_methods_id and pay.payment_type == 'inbound':
                return self.env['payment.methods'].sudo().search([('sequence','=',99)])

    payment_methods_id = fields.Many2one(comodel_name="payment.methods",string=u'Forma de Pago',default=_default_method_paid)
