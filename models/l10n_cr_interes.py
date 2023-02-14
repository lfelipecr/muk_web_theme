# -*- coding: utf-8 -*-

from odoo import fields, models, _


class L10ncrInteres(models.Model):
    _name = "l10n_cr.interes"
    _description = "Interes diario para facturas de patentes"
    _order = 'date desc'
    _rec_name = 'date'

    date = fields.Date(string=u'Fecha de validez', store=True)
    rate = fields.Float(string='Tasa diaria', store=True,digits=(12, 6),)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="cascade",
        required=True,
        default=lambda self: self.env["res.company"]._company_default_get("l10n_cr.interes")
    )

