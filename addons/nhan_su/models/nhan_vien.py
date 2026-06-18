# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'
    _rec_name = 'ho_ten'

    # Mã nhân viên - tự động tạo bằng sequence
    ma_nhan_vien = fields.Char(
        string="Mã nhân viên",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    # Thông tin cá nhân
    ho_ten_dem = fields.Char(string="Họ tên đệm")
    ten = fields.Char(string="Tên", required=True)
    ho_ten = fields.Char(
        string="Họ và tên",
        compute='_compute_ho_ten',
        store=True
    )
    
    ngay_sinh = fields.Date(string="Ngày sinh")
    gioi_tinh = fields.Selection(
        selection=[
            ('nam', 'Nam'),
            ('nu', 'Nữ'),
            ('khac', 'Khác'),
        ],
        string="Giới tính"
    )
    que_quan = fields.Char(string="Quê quán")
    email = fields.Char(string="Email")
    so_dien_thoai = fields.Char(string="Số điện thoại")
    image = fields.Binary(string="Ảnh nhân viên")

    # Thông tin phục vụ tính chi phí nhân sự cho dự án.
    loai_hop_dong = fields.Selection(
        selection=[
            ('toan_thoi_gian', 'Toàn thời gian'),
            ('ban_thoi_gian', 'Bán thời gian'),
            ('thuc_tap', 'Thực tập'),
            ('cong_tac_vien', 'Cộng tác viên'),
        ],
        string='Loại hợp đồng',
        default='toan_thoi_gian'
    )
    ngay_vao_lam = fields.Date(string='Ngày vào làm')
    luong_co_ban = fields.Float(string='Lương cơ bản/tháng')
    don_gia_gio = fields.Float(
        string='Đơn giá giờ',
        help='Dùng để tính chi phí nhân sự theo giờ làm thực tế của công việc/dự án.'
    )

    # Liên kết Many2one - suffix _id
    chuc_vu_id = fields.Many2one('chuc_vu', string='Chức vụ', ondelete='set null')
    phong_ban_id = fields.Many2one('phong_ban', string='Phòng ban', ondelete='set null')
    chuyen_mon_ids = fields.Many2many(
        'chuyen_mon',
        'nhan_vien_chuyen_mon_rel',
        'nhan_vien_id',
        'chuyen_mon_id',
        string='Chuyên môn'
    )
    trinh_do_chuyen_mon = fields.Selection([
        ('intern', 'Thực tập'),
        ('junior', 'Junior'),
        ('middle', 'Middle'),
        ('senior', 'Senior'),
        ('expert', 'Expert'),
    ], string='Trình độ chuyên môn', default='junior')
    nam_kinh_nghiem = fields.Float(string='Năm kinh nghiệm')

    # Liên kết One2many - suffix _ids
    lich_su_lam_viec_ids = fields.One2many(
        'lich_su_lam_viec',
        'nhan_vien_id',
        string='Lịch sử làm việc'
    )

    @api.depends('ho_ten_dem', 'ten')
    def _compute_ho_ten(self):
        """Tính toán họ tên đầy đủ"""
        for record in self:
            parts = []
            if record.ho_ten_dem:
                parts.append(record.ho_ten_dem)
            if record.ten:
                parts.append(record.ten)
            record.ho_ten = ' '.join(parts) if parts else ''

    @api.model
    def create(self, vals):
        """Tự động tạo mã nhân viên khi tạo mới"""
        if vals.get('ma_nhan_vien', 'Mới') == 'Mới':
            vals['ma_nhan_vien'] = self.env['ir.sequence'].next_by_code('nhan_vien.sequence') or 'NV001'
        return super(NhanVien, self).create(vals)

    @api.constrains('luong_co_ban', 'don_gia_gio', 'nam_kinh_nghiem')
    def _check_salary_values(self):
        for record in self:
            if record.luong_co_ban < 0 or record.don_gia_gio < 0:
                raise ValidationError('Lương cơ bản và đơn giá giờ không được âm.')
            if record.nam_kinh_nghiem < 0:
                raise ValidationError('Năm kinh nghiệm không được âm.')

    def name_get(self):
        """Hiển thị mã và họ tên nhân viên"""
        result = []
        for record in self:
            if record.ho_ten:
                name = f"{record.ma_nhan_vien} - {record.ho_ten}"
            else:
                name = record.ma_nhan_vien or f'Nhân viên #{record.id}'
            result.append((record.id, name))
        return result
