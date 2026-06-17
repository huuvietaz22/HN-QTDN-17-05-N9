# -*- coding: utf-8 -*-
{
    'name': "Quản lý Công việc",

    'summary': """
        Module quản lý công việc, nhiệm vụ, tiến độ và hiệu quả nhân viên""",

    'description': """
        Module quản lý công việc bao gồm:
        - Quản lý công việc
        - Phân công nhiệm vụ
        - Theo dõi tiến độ
        - Báo cáo hiệu quả làm việc
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Project Management',
    'version': '1.0',
    'license': 'LGPL-3',

    'depends': ['base', 'nhan_su'],  # Phụ thuộc vào module nhan_su
    # Note: project_management là soft dependency - không cần khai báo ở đây
    # Field du_an_id trong cong_viec sẽ tự động tham chiếu đến model 'projects' nếu module project_management được cài đặt

    # Data files được load theo thứ tự
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data (sequences phải load trước views)
        'data/sequence_data.xml',
        # Views
        'views/cong_viec.xml',
        'views/nhiem_vu.xml',
        'views/tien_do.xml',
        'views/bao_cao_hieu_qua.xml',
        'views/menu.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
