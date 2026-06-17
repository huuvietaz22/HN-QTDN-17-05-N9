from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Budgets(models.Model):
    _name = 'budgets'
    _description = 'Ngân sách dự án'

    # Mã ngân sách - tự động tạo bằng sequence
    budgets_id = fields.Char(
        string='Mã ngân sách',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    budgets_name = fields.Char(string="Tên Ngân Sách")
    projects_id = fields.Many2one('projects', string='Dự Án')

    # total_budget = fields.Float(string='Ngân Sách Dự Án', required=True)
    # actual_expense = fields.Float(string='Chi Phí Thực Tế', compute='_compute_expense')

    expense_ids = fields.One2many('expenses', 'budgets_id', string='Chi Phí')

    budget_planned = fields.Float(string="Ngân sách Dự toán", required=True)
    budget_allocated = fields.Float(string="Ngân sách Phân bổ", required=True)
    budget_reserved = fields.Float(string="Ngân sách Dự trù")
    budget_spent = fields.Float(string="Chi phí Thực tế", compute="_compute_budget_spent", store=True)
    budget_difference = fields.Float(string="Chênh lệch Ngân sách", compute="_compute_budget_difference", store=True)

    @api.depends('expense_ids.amount')  # Sửa lại depend field
    def _compute_budget_spent(self):
        for record in self:
            record.budget_spent = sum(record.expense_ids.mapped('amount'))

    @api.depends('budget_planned', 'budget_spent')
    def _compute_budget_difference(self):
        #Tính toán chênh lệch ngân sách
        for record in self:
            record.budget_difference = record.budget_planned - record.budget_spent

    @api.constrains('budget_planned', 'budget_allocated', 'budget_reserved')
    def _check_budget_values(self):
        for record in self:
            if record.budget_planned < 0 or record.budget_allocated < 0 or record.budget_reserved < 0:
                raise ValidationError('Các giá trị ngân sách không được âm.')

    @api.model
    def create(self, vals):
        """Tự động tạo mã ngân sách khi tạo mới"""
        if vals.get('budgets_id', 'Mới') == 'Mới':
            # Dùng 'or' để phòng trường hợp chưa có sequence thì lấy tạm BG001
            vals['budgets_id'] = self.env['ir.sequence'].next_by_code('budgets.sequence') or 'BG001'
        return super(Budgets, self).create(vals)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.budgets_id} - {record.budgets_name}" if record.budgets_name else record.budgets_id
            result.append((record.id, name))
        return result
