from odoo import fields, models


class PaymentMethods(models.Model):
    _name = "payment.methods"
    _description = "Pagos - Método de pago"

    active = fields.Boolean(default=True,)
    sequence = fields.Char()
    name = fields.Char()
    notes = fields.Text()
