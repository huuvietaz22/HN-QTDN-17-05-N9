# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BaoCaoHieuQua(models.Model):
    _name = 'bao_cao_hieu_qua'
    _description = 'Báo cáo hiệu quả làm việc của nhân viên'
    _rec_name = 'nhan_vien_id'

    # Thông tin báo cáo
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )
    
    thang = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True)
    
    nam = fields.Integer(string='Năm', required=True, default=2026)
    
    # Thống kê
    tong_nhiem_vu = fields.Integer(
        string='Tổng nhiệm vụ',
        compute='_compute_thong_ke',
        store=True
    )
    
    nhiem_vu_hoan_thanh = fields.Integer(
        string='Nhiệm vụ hoàn thành',
        compute='_compute_thong_ke',
        store=True
    )
    
    nhiem_vu_tre_han = fields.Integer(
        string='Nhiệm vụ trễ hạn',
        compute='_compute_thong_ke',
        store=True
    )
    
    ty_le_hoan_thanh = fields.Float(
        string='Tỷ lệ hoàn thành (%)',
        compute='_compute_thong_ke',
        store=True
    )
    
    diem_trung_binh = fields.Float(
        string='Điểm đánh giá TB',
        compute='_compute_diem_danh_gia',
        store=True
    )
    
    xep_loai = fields.Selection([
        ('a', 'A - Xuất sắc'),
        ('b', 'B - Khá'),
        ('c', 'C - Trung bình'),
        ('d', 'D - Yếu'),
    ], string='Xếp loại', compute='_compute_xep_loai', store=True)
    
    # Liên kết đến nhiệm vụ
    nhiem_vu_ids = fields.Many2many(
        'nhiem_vu',
        compute='_compute_nhiem_vu_ids',
        string='Danh sách nhiệm vụ'
    )
    
    ghi_chu = fields.Text(string='Ghi chú')
    
    def _get_period_nhiem_vu(self):
        self.ensure_one()
        if not (self.nhan_vien_id and self.thang and self.nam):
            return self.env['nhiem_vu']

        start_date = f"{self.nam}-{self.thang.zfill(2)}-01"
        if int(self.thang) == 12:
            end_date = f"{self.nam + 1}-01-01"
        else:
            end_date = f"{self.nam}-{str(int(self.thang) + 1).zfill(2)}-01"

        return self.env['nhiem_vu'].search([
            ('nguoi_thuc_hien_id', '=', self.nhan_vien_id.id),
            ('ngay_bat_dau', '>=', start_date),
            ('ngay_bat_dau', '<', end_date),
        ])

    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_nhiem_vu_ids(self):
        """Lấy danh sách nhiệm vụ của nhân viên trong tháng"""
        for record in self:
            record.nhiem_vu_ids = record._get_period_nhiem_vu()
    
    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_thong_ke(self):
        """Tính toán thống kê nhiệm vụ"""
        for record in self:
            nhiem_vu_ids = record._get_period_nhiem_vu()
            record.tong_nhiem_vu = len(nhiem_vu_ids)
            record.nhiem_vu_hoan_thanh = len(
                nhiem_vu_ids.filtered(lambda n: n.trang_thai == 'hoan_thanh')
            )
            record.nhiem_vu_tre_han = len(
                nhiem_vu_ids.filtered(lambda n: n.trang_thai == 'qua_han')
            )
            
            if record.tong_nhiem_vu > 0:
                record.ty_le_hoan_thanh = (record.nhiem_vu_hoan_thanh / record.tong_nhiem_vu) * 100
            else:
                record.ty_le_hoan_thanh = 0.0
    
    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_diem_danh_gia(self):
        """Tính điểm đánh giá trung bình"""
        diem_map = {
            'xuat_sac': 10,
            'tot': 8,
            'trung_binh': 6,
            'yeu': 4
        }
        for record in self:
            nhiem_vu_co_danh_gia = record._get_period_nhiem_vu().filtered(lambda n: n.danh_gia)
            if nhiem_vu_co_danh_gia:
                tong_diem = sum(diem_map.get(n.danh_gia, 0) for n in nhiem_vu_co_danh_gia)
                record.diem_trung_binh = tong_diem / len(nhiem_vu_co_danh_gia)
            else:
                record.diem_trung_binh = 0.0
    
    @api.depends('ty_le_hoan_thanh', 'diem_trung_binh')
    def _compute_xep_loai(self):
        """Xếp loại dựa trên tỷ lệ hoàn thành và điểm đánh giá"""
        for record in self:
            if record.ty_le_hoan_thanh >= 90 and record.diem_trung_binh >= 8:
                record.xep_loai = 'a'
            elif record.ty_le_hoan_thanh >= 75 and record.diem_trung_binh >= 6:
                record.xep_loai = 'b'
            elif record.ty_le_hoan_thanh >= 60:
                record.xep_loai = 'c'
            else:
                record.xep_loai = 'd'
