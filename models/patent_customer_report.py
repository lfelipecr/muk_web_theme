# -*- coding: utf-8 -*-

from odoo import fields, models, _


class PatentCustomerReport(models.Model):
    _name = "l10ncr.patent.customer.report"
    _description = "Lista de Patentados"
    _order = 'patent_id desc'
    _rec_name = 'patent_id'

    company_id = fields.Many2one(comodel_name="res.company",default=lambda self: self.env.user.company_id.id, string=u'Compañia')
    patent_id = fields.Many2one('l10n_cr.patent',string='Patente')
    currency_id = fields.Many2one('res.currency',related="company_id.currency_id", string='Moneda')
    t_identificacion = fields.Char('Sol.Identificación')
    titular = fields.Char('Solicitante')
    r_legal = fields.Char('Representante Legal')
    r_identificacion = fields.Char('N° Identificación')
    t_tipo_i = fields.Char('Sol.Tipo Identificación')
    t_celular = fields.Char('Sol.Celular')
    t_fono = fields.Char('Sol.Tél.Fijo')
    t_mail = fields.Char('Sol.Correo Electrónico')
    t_actividad = fields.Char('Sol.Actividad Económica')
    direccion = fields.Char('Dirección')
    p_identificacion = fields.Char('Prop.Identificación')
    p_name = fields.Char('Propietario')
    p_tipo_i = fields.Char('Prop.Tipo Identificación')
    p_celular = fields.Char('Prop.Celular')
    p_fono = fields.Char('Prop.Tél.Fijo')
    p_mail = fields.Char('Prop.Correo Electrónico')
    p_actividad = fields.Char('Prop.Actividad Económica')
    finca = fields.Char('N° Finca')
    duplicado = fields.Char('Duplicado')
    horizontal = fields.Char('Horizontal')
    derecho = fields.Char('Derecho')
    provincia = fields.Char('Provincia')
    canton = fields.Char('Cantón')
    distrito = fields.Char('Distrito')
    direccion_f = fields.Char('Dirección física')
    patente_tipo = fields.Char('Tipo Patente')
    patente_temporalidad = fields.Char('Tipo Temporalidad')
    costo_trimestral = fields.Monetary('Costo trimestral')
    aprobacion = fields.Date('Fecha Aprobación')
    cierre = fields.Date('Fecha Cierre')
    state = fields.Char('Estado')


    # negocio = fields.Char('Negocio')
    # actividad = fields.Char('Actividad comercial')
    # telefono = fields.Char('Teléfono')
    # mail = fields.Char('Correo electrónic')
