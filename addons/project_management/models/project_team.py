# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProjectTeamRole(models.Model):
    _name = 'project.team.role'
    _description = 'Phân công vai trò nhân sự trong dự án'
    _order = 'project_id, role_code, employee_id'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Phân công', compute='_compute_display_name', store=True)
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade')
    employee_id = fields.Many2one('nhan_vien', string='Nhân sự', required=True, ondelete='restrict')
    role_code = fields.Selection([
        ('owner', 'Chủ dự án'),
        ('pm', 'PM - Project Manager'),
        ('leader', 'Leader'),
        ('dev', 'Dev'),
        ('qa', 'QA'),
        ('qc', 'QC'),
        ('co', 'CO - Coordinator'),
        ('ba', 'BA'),
        ('tester', 'Tester'),
        ('devops', 'DevOps'),
        ('designer', 'Designer'),
        ('stakeholder', 'Stakeholder'),
    ], string='Vai trò', required=True, default='dev')
    responsibility = fields.Text(string='Trách nhiệm')
    allocation_percent = fields.Float(string='Tỷ lệ tham gia (%)', default=100.0)
    start_date = fields.Date(string='Ngày bắt đầu')
    end_date = fields.Date(string='Ngày kết thúc')
    is_main_role = fields.Boolean(string='Vai trò chính')
    state = fields.Selection([
        ('planned', 'Dự kiến'),
        ('active', 'Đang tham gia'),
        ('done', 'Đã kết thúc'),
    ], string='Trạng thái', default='active')

    _sql_constraints = [
        (
            'unique_project_employee_role',
            'UNIQUE(project_id, employee_id, role_code)',
            'Nhân sự này đã có vai trò tương tự trong dự án.'
        )
    ]

    @api.depends('project_id.projects_name', 'employee_id.ho_ten', 'role_code')
    def _compute_display_name(self):
        role_labels = dict(self._fields['role_code'].selection)
        for record in self:
            role = role_labels.get(record.role_code, '')
            employee = record.employee_id.ho_ten or record.employee_id.ma_nhan_vien or ''
            project = record.project_id.projects_name or record.project_id.projects_id or ''
            record.display_name = f"{employee} - {role} - {project}"

    @api.constrains('allocation_percent')
    def _check_allocation_percent(self):
        for record in self:
            if record.allocation_percent < 0 or record.allocation_percent > 100:
                raise ValidationError('Tỷ lệ tham gia phải nằm trong khoảng 0-100%.')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError('Ngày bắt đầu vai trò không được lớn hơn ngày kết thúc.')
