# -*- coding: utf-8 -*-
{
    'name': "Quản lý Nhân sự",

    'summary': """
        Module quản lý nhân sự, chức vụ, phòng ban và lịch sử làm việc""",

    'description': """
        Module quản lý nhân sự bao gồm:
        - Quản lý thông tin nhân viên
        - Quản lý chức vụ
        - Quản lý phòng ban
        - Quản lý lịch sử làm việc
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '1.0',
    'license': 'LGPL-3',

    'depends': ['base', 'web'],

    # Data files được load theo thứ tự
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data (sequences phải load trước views)
        'data/sequence_data.xml',
        # Views
        'views/chuc_vu.xml',
        'views/phong_ban.xml',
        'views/nhan_vien.xml',
        'views/lich_su_lam_viec.xml',
        'views/menu.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'nhan_su/static/src/css/nhan_vien.css',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}
