# -*- coding: utf-8 -*-
{
    'name': "Quản lý Dự án",

    'summary': """
        Quản lý dự án, công việc, ngân sách, chi phí và rủi ro""",

    'description': """
        Module quản lý dự án bao gồm:
        - Quản lý thông tin dự án và phê duyệt dự án
        - Kết nối công việc/nhiệm vụ từ module Quản lý Công việc
        - Theo dõi tiến độ dự án tự động theo công việc
        - Quản lý ngân sách, chi phí và chênh lệch ngân sách
        - Theo dõi rủi ro dự án và hỗ trợ phân tích AI tuỳ chọn
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Project Management',
    'version': '1.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'nhan_su', 'mail', 'quan_ly_cong_viec'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/sample_project_data.xml',
        'report/report_action.xml',
        'report/project_approval_report.xml',
        # Load các view/actions trước
        'views/projects.xml',
        'views/employees.xml',
        'views/budgets.xml',
        'views/expenses.xml',
        'views/labor_cost_views.xml',
        'views/project_governance_views.xml',
        'views/project_team_views.xml',
        'views/chart.xml',
        'views/chartoftasks.xml',
        'views/cong_viec_extend.xml',
        'views/nhan_vien_extend.xml',
        'views/risk_management.xml',
        'views/gemini_ai_views.xml',
        # Cuối cùng mới load menu, vì menu tham chiếu tới các action ở trên
        'views/menu.xml',
    ],

    # 'assets': {
    #     'web.assets_backend': [
    #         'project_management\static\src\projects.css',
    #     ],
    # },

    'installable': True,
    'application': True,
    'auto_install': False,
}
