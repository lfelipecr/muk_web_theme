from odoo import fields, models


class PatentType(models.Model):
    _inherit = "l10n_cr.patent.type"
    _description = "CR Patent Type"


    product_licor_id = fields.Many2one(
        comodel_name="product.product",
        required=False,
        # default=lambda self: self.env.ref("l10n_cr_municipality.product_patent"),
        string="Timbre Pantente Licor",
    )
