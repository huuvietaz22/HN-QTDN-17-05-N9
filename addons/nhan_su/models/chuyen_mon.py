# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ChuyenMon(models.Model):
    _name = 'chuyen_mon'
    _description = 'Chuyên môn nhân sự'
    _rec_name = 'ten_chuyen_mon'
    _order = 'nhom_chuyen_mon, ten_chuyen_mon'

    ma_chuyen_mon = fields.Char(
        string='Mã chuyên môn',
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    ten_chuyen_mon = fields.Char(string='Tên chuyên môn', required=True)
    nhom_chuyen_mon = fields.Selection([
        ('business', 'Nghiệp vụ'),
        ('dev', 'Phát triển phần mềm'),
        ('qa_qc', 'QA/QC'),
        ('operations', 'Vận hành'),
        ('management', 'Quản lý'),
        ('other', 'Khác'),
    ], string='Nhóm chuyên môn', default='other', required=True)
    mo_ta = fields.Text(string='Mô tả')
    nhan_vien_ids = fields.Many2many(
        'nhan_vien',
        'nhan_vien_chuyen_mon_rel',
        'chuyen_mon_id',
        'nhan_vien_id',
        string='Nhân viên'
    )

    @api.model
    def create(self, vals):
        if vals.get('ma_chuyen_mon', 'Mới') == 'Mới':
            vals['ma_chuyen_mon'] = self.env['ir.sequence'].next_by_code('chuyen_mon.sequence') or 'CM001'
        return super(ChuyenMon, self).create(vals)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.ma_chuyen_mon} - {record.ten_chuyen_mon}" if record.ma_chuyen_mon else record.ten_chuyen_mon
            result.append((record.id, name))
        return result
