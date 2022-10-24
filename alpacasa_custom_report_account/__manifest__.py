# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reportes de finanzas hechos a medida por Alpacasa',
    'version': '1.0.1',
    'author': 'ALPACASA',
    'category': 'Accounting/Accounting',
    'website': 'www.alpacasa.com.py',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'py_ctrm_base', 'sale','py_ctrm_alpacasa_mods'],

    # always loaded
    'data': [

        'reports/reporte_billed_summary.xml',
        'reports/reporte_billed_summary_resu.xml',
        'reports/reporte_billed_summary_cate.xml',
        'reports/reporte_billed_summary_resu_cate.xml',
        'wizard/billed_summary.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,

}
