# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NhanVienExtend(models.Model):
    """Kế thừa model nhan_vien để thêm thông tin từ module project_management"""
    _inherit = 'nhan_vien'
    
    # Computed field để kiểm tra xem model projects có tồn tại không
    has_project_management = fields.Boolean(
        string='Có module Project Management',
        compute='_compute_has_project_management',
        store=False
    )
    
    # Field Many2many với projects - định nghĩa tĩnh để view có thể validate
    # Field này chỉ hoạt động khi model 'projects' tồn tại
    du_an_tham_gia_ids = fields.Many2many(
        'projects',
        'projects_nhan_vien_rel',
        'nhan_vien_id',
        'projects_id',
        string='Dự án tham gia',
        help='Danh sách dự án mà nhân viên tham gia (nếu có module Project Management)'
    )
    project_role_ids = fields.One2many(
        'project.team.role',
        'employee_id',
        string='Vai trò trong dự án'
    )
    
    @api.depends()
    def _compute_has_project_management(self):
        """Kiểm tra xem model projects có tồn tại trong registry không"""
        for record in self:
            try:
                record.has_project_management = 'projects' in self.env.registry
            except (AttributeError, KeyError):
                record.has_project_management = False

