from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Expenses(models.Model):
    _name = 'expenses'
    _description = 'Chi phí thực tế'

    expenses_name = fields.Char(string="Tên Khoản Chi", required=True)
    # projects_id = fields.Many2one('projects', string="Dự án", ondelete='cascade')
    cong_viec_id = fields.Many2one('cong_viec', string="Công việc", ondelete='cascade', help='Công việc từ module quản lý công việc')
    budgets_id = fields.Many2one('budgets', string="Ngân sách")
    amount = fields.Float(string="Số tiền", required=True)
    date = fields.Date(string="Ngày chi tiêu", required=True, default=fields.Date.today)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Số tiền chi phí phải lớn hơn 0.')
