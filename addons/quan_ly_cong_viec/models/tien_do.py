# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TienDo(models.Model):
    _name = 'tien_do'
    _description = 'Bảng theo dõi tiến độ'
    _rec_name = 'ma_tien_do'

    # Mã tiến độ - tự động tạo bằng sequence
    ma_tien_do = fields.Char(
        string="Mã tiến độ",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    ngay_cap_nhat = fields.Datetime(string="Ngày cập nhật", default=fields.Datetime.now)
    noi_dung = fields.Text(string="Nội dung cập nhật", required=True)
    ti_le_hoan_thanh = fields.Float(string="Tỷ lệ hoàn thành (%)")
    
    # ============ TÍCH HỢP VỚI MODULE NHÂN SỰ ============
    # Thay Char bằng Many2one
    nguoi_cap_nhat_id = fields.Many2one(
        'nhan_vien',
        string='Người cập nhật',
        default=lambda self: self.env.context.get('default_nguoi_cap_nhat_id'),
        ondelete='set null',
        help='Nhân viên cập nhật tiến độ'
    )
    
    ghi_chu = fields.Text(string="Ghi chú")
    file_dinh_kem = fields.Binary(string="File đính kèm")
    ten_file = fields.Char(string="Tên file")
    
    # Liên kết Many2one - suffix _id
    nhiem_vu_id = fields.Many2one('nhiem_vu', string='Nhiệm vụ', ondelete='cascade', required=True)
    
    @api.model
    def create(self, vals):
        """Tự động tạo mã tiến độ và cập nhật tỷ lệ hoàn thành cho nhiệm vụ"""
        # Tạo mã tiến độ tự động
        if vals.get('ma_tien_do', 'Mới') == 'Mới':
            vals['ma_tien_do'] = self.env['ir.sequence'].next_by_code('tien_do.sequence') or 'TD001'
        
        # Tạo record
        res = super(TienDo, self).create(vals)
        
        # Cập nhật tỷ lệ hoàn thành cho nhiệm vụ
        if res.nhiem_vu_id and 'ti_le_hoan_thanh' in vals:
            res.nhiem_vu_id.ti_le_hoan_thanh = vals['ti_le_hoan_thanh']
        
        return res

    def write(self, vals):
        res = super(TienDo, self).write(vals)
        if 'ti_le_hoan_thanh' in vals:
            for record in self.filtered('nhiem_vu_id'):
                record.nhiem_vu_id.ti_le_hoan_thanh = vals['ti_le_hoan_thanh']
        return res

    @api.constrains('ti_le_hoan_thanh')
    def _check_ti_le_hoan_thanh(self):
        for record in self:
            if record.ti_le_hoan_thanh < 0 or record.ti_le_hoan_thanh > 100:
                raise ValidationError('Tỷ lệ hoàn thành tiến độ phải nằm trong khoảng 0-100%.')

    def name_get(self):
        """Hiển thị mã tiến độ"""
        result = []
        for record in self:
            name = record.ma_tien_do or f'Tiến độ #{record.id}'
            result.append((record.id, name))
        return result
