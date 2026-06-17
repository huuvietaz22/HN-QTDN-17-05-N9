# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _description = 'Mốc nghiệm thu dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_date, id'

    name = fields.Char(string='Tên mốc', required=True, tracking=True)
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade', tracking=True)
    responsible_id = fields.Many2one('nhan_vien', string='Người phụ trách', tracking=True)
    planned_date = fields.Date(string='Ngày kế hoạch', required=True, tracking=True)
    actual_date = fields.Date(string='Ngày hoàn thành thực tế', tracking=True)
    completion_percent = fields.Float(string='Tỷ lệ hoàn thành (%)', default=0.0, tracking=True)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
        ('late', 'Trễ hạn'),
        ('cancelled', 'Hủy'),
    ], string='Trạng thái', default='draft', tracking=True)
    deliverable = fields.Text(string='Sản phẩm bàn giao')
    acceptance_criteria = fields.Text(string='Tiêu chí nghiệm thu')
    note = fields.Text(string='Ghi chú')

    @api.constrains('completion_percent')
    def _check_completion_percent(self):
        for record in self:
            if record.completion_percent < 0 or record.completion_percent > 100:
                raise ValidationError('Tỷ lệ hoàn thành mốc dự án phải nằm trong khoảng 0-100%.')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_mark_done(self):
        for record in self:
            record.write({
                'state': 'done',
                'completion_percent': 100.0,
                'actual_date': record.actual_date or fields.Date.context_today(record),
            })

    def action_mark_late(self):
        self.write({'state': 'late'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class ProjectChangeRequest(models.Model):
    _name = 'project.change.request'
    _description = 'Yêu cầu thay đổi dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    _rec_name = 'code'

    code = fields.Char(string='Mã yêu cầu', readonly=True, copy=False, default='Mới')
    name = fields.Char(string='Tên yêu cầu thay đổi', required=True, tracking=True)
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade', tracking=True)
    requested_by = fields.Many2one('nhan_vien', string='Người yêu cầu', tracking=True)
    request_date = fields.Date(string='Ngày yêu cầu', default=fields.Date.context_today, required=True)
    change_type = fields.Selection([
        ('scope', 'Phạm vi'),
        ('schedule', 'Tiến độ'),
        ('budget', 'Ngân sách'),
        ('resource', 'Nguồn lực'),
        ('quality', 'Chất lượng'),
    ], string='Loại thay đổi', required=True, default='scope', tracking=True)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
        ('implemented', 'Đã triển khai'),
    ], string='Trạng thái', default='draft', tracking=True)
    reason = fields.Text(string='Lý do thay đổi', required=True)
    impact_analysis = fields.Text(string='Phân tích ảnh hưởng')
    extra_budget = fields.Float(string='Ngân sách phát sinh')
    extra_days = fields.Integer(string='Số ngày phát sinh')
    approver_id = fields.Many2one('nhan_vien', string='Người phê duyệt', readonly=True)
    approval_date = fields.Datetime(string='Ngày phê duyệt', readonly=True)
    rejection_reason = fields.Text(string='Lý do từ chối')

    @api.model
    def create(self, vals):
        if vals.get('code', 'Mới') == 'Mới':
            vals['code'] = self.env['ir.sequence'].next_by_code('project.change.request.sequence') or 'CR001'
        return super(ProjectChangeRequest, self).create(vals)

    @api.constrains('extra_budget', 'extra_days')
    def _check_impact_values(self):
        for record in self:
            if record.extra_budget < 0 or record.extra_days < 0:
                raise ValidationError('Ngân sách và số ngày phát sinh không được âm.')

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        for record in self:
            if record.state != 'submitted':
                raise UserError('Chỉ có thể duyệt yêu cầu đang ở trạng thái Chờ duyệt.')
            record.write({
                'state': 'approved',
                'approver_id': record.project_id.manager_name.id,
                'approval_date': fields.Datetime.now(),
            })

    def action_reject(self):
        for record in self:
            if not record.rejection_reason:
                raise UserError('Vui lòng nhập lý do từ chối trước khi từ chối yêu cầu.')
            record.write({'state': 'rejected'})

    def action_implement(self):
        self.write({'state': 'implemented'})


class ProjectMeeting(models.Model):
    _name = 'project.meeting'
    _description = 'Biên bản họp dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_date desc, id desc'

    name = fields.Char(string='Chủ đề họp', required=True, tracking=True)
    project_id = fields.Many2one('projects', string='Dự án', required=True, ondelete='cascade', tracking=True)
    meeting_date = fields.Datetime(string='Thời gian họp', default=fields.Datetime.now, required=True)
    organizer_id = fields.Many2one('nhan_vien', string='Người chủ trì')
    attendee_ids = fields.Many2many(
        'nhan_vien',
        'project_meeting_nhan_vien_rel',
        'meeting_id',
        'nhan_vien_id',
        string='Người tham dự'
    )
    state = fields.Selection([
        ('planned', 'Đã lên lịch'),
        ('done', 'Đã họp'),
        ('cancelled', 'Hủy'),
    ], string='Trạng thái', default='planned', tracking=True)
    agenda = fields.Text(string='Nội dung dự kiến')
    minutes = fields.Text(string='Biên bản họp')
    decisions = fields.Text(string='Quyết định')
    action_items = fields.Text(string='Việc cần làm sau họp')
    next_meeting_date = fields.Datetime(string='Lịch họp tiếp theo')

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
