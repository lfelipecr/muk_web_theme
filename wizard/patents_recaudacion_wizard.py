# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from io import BytesIO
import base64
from datetime import datetime
import xlsxwriter
from odoo import models, fields, api, _


class PatentRecaudacionWizard(models.TransientModel):
    _name = "patent.recaudacion.wizard"


    def view_list(self):
        self.env['l10n_cr.recaudacion'].sudo()._get_data()

        tree_id = self.env.ref('l10n_cr_municipality_extend.view_recaudacion_tree').id
        pivot_id = self.env.ref('l10n_cr_municipality_extend.view_recaudacion_pivot').id
        graph_id = self.env.ref('l10n_cr_municipality_extend.view_recaudacion_graph').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reporte de Recaudación'),
            'res_model': 'l10n_cr.recaudacion',
            'view_mode': 'tree,pivot',
            'limit': 99999999,
            'views': [[tree_id, 'list'],[pivot_id,'pivot'],[graph_id,'graph']],
        }