# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class NhiemVu(models.Model):
    _name = 'nhiem_vu'
    _description = 'Bảng quản lý nhiệm vụ'
    _rec_name = 'ten_nhiem_vu'

    # Mã nhiệm vụ - tự động tạo bằng sequence
    ma_nhiem_vu = fields.Char(
        string="Mã nhiệm vụ",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    ten_nhiem_vu = fields.Char(string="Tên nhiệm vụ", required=True)
    mo_ta = fields.Text(string="Mô tả")
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu")
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")
    ngay_hoan_thanh_thuc_te = fields.Date(string="Ngày hoàn thành thực tế")
    
    # ============ TÍCH HỢP VỚI MODULE NHÂN SỰ ============
    # Thay thế Char bằng Many2one để liên kết với nhân viên
    nguoi_thuc_hien_id = fields.Many2one(
        'nhan_vien',
        string='Người thực hiện',
        required=True,
        ondelete='restrict',
        help='Nhân viên được giao nhiệm vụ này'
    )
    
    # Người giao việc
    nguoi_giao_viec_id = fields.Many2one(
        'nhan_vien',
        string='Người giao việc',
        ondelete='set null',
        help='Nhân viên giao nhiệm vụ'
    )
    
    trang_thai = fields.Selection(
        selection=[
            ('chua_bat_dau', 'Chưa bắt đầu'),
            ('dang_thuc_hien', 'Đang thực hiện'),
            ('hoan_thanh', 'Hoàn thành'),
            ('qua_han', 'Quá hạn'),
        ],
        string="Trạng thái",
        default='chua_bat_dau',
        compute='_compute_trang_thai',
        store=True
    )
    ti_le_hoan_thanh = fields.Float(string="Tỷ lệ hoàn thành (%)", default=0.0)
    
    # Đánh giá chất lượng
    danh_gia = fields.Selection([
        ('xuat_sac', 'Xuất sắc'),
        ('tot', 'Tốt'),
        ('trung_binh', 'Trung bình'),
        ('yeu', 'Yếu'),
    ], string='Đánh giá')
    
    nhan_xet = fields.Text(string='Nhận xét')
    
    @api.depends('ngay_ket_thuc', 'ti_le_hoan_thanh')
    def _compute_trang_thai(self):
        """Tự động tính trạng thái dựa trên thời gian và tiến độ"""
        for record in self:
            if record.ti_le_hoan_thanh >= 100:
                record.trang_thai = 'hoan_thanh'
            elif record.ti_le_hoan_thanh > 0:
                if record.ngay_ket_thuc and date.today() > record.ngay_ket_thuc:
                    record.trang_thai = 'qua_han'
                else:
                    record.trang_thai = 'dang_thuc_hien'
            else:
                if record.ngay_ket_thuc and date.today() > record.ngay_ket_thuc:
                    record.trang_thai = 'qua_han'
                else:
                    record.trang_thai = 'chua_bat_dau'
    
    # Liên kết Many2one - suffix _id
    cong_viec_id = fields.Many2one('cong_viec', string='Công việc', ondelete='cascade')
    
    # Liên kết One2many - suffix _ids
    tien_do_ids = fields.One2many(
        'tien_do',
        'nhiem_vu_id',
        string='Lịch sử tiến độ'
    )

    @api.model
    def create(self, vals):
        """Tự động tạo mã nhiệm vụ khi tạo mới"""
        if vals.get('ma_nhiem_vu', 'Mới') == 'Mới':
            vals['ma_nhiem_vu'] = self.env['ir.sequence'].next_by_code('nhiem_vu.sequence') or 'NV001'
        record = super(NhiemVu, self).create(vals)
        if record.cong_viec_id:
            record.cong_viec_id._sync_progress_from_nhiem_vu()
        return record

    def write(self, vals):
        cong_viec_before = self.mapped('cong_viec_id')
        res = super(NhiemVu, self).write(vals)
        if {'ti_le_hoan_thanh', 'cong_viec_id', 'ngay_ket_thuc'} & set(vals):
            (cong_viec_before | self.mapped('cong_viec_id'))._sync_progress_from_nhiem_vu()
        return res

    def unlink(self):
        cong_viec = self.mapped('cong_viec_id')
        res = super(NhiemVu, self).unlink()
        cong_viec._sync_progress_from_nhiem_vu()
        return res

    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc', 'ngay_hoan_thanh_thuc_te')
    def _check_dates(self):
        for record in self:
            if record.ngay_bat_dau and record.ngay_ket_thuc and record.ngay_bat_dau > record.ngay_ket_thuc:
                raise ValidationError('Ngày bắt đầu nhiệm vụ không được lớn hơn ngày kết thúc.')
            if record.ngay_bat_dau and record.ngay_hoan_thanh_thuc_te and record.ngay_hoan_thanh_thuc_te < record.ngay_bat_dau:
                raise ValidationError('Ngày hoàn thành thực tế không được nhỏ hơn ngày bắt đầu.')

    @api.constrains('ti_le_hoan_thanh')
    def _check_ti_le_hoan_thanh(self):
        for record in self:
            if record.ti_le_hoan_thanh < 0 or record.ti_le_hoan_thanh > 100:
                raise ValidationError('Tỷ lệ hoàn thành nhiệm vụ phải nằm trong khoảng 0-100%.')

    def name_get(self):
        """Hiển thị mã và tên nhiệm vụ"""
        result = []
        for record in self:
            if record.ten_nhiem_vu:
                name = f"{record.ma_nhiem_vu} - {record.ten_nhiem_vu}"
            else:
                name = record.ma_nhiem_vu or f'Nhiệm vụ #{record.id}'
            result.append((record.id, name))
        return result
