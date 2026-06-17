# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CongViecExtend(models.Model):
    """Kế thừa model cong_viec để thêm field du_an_id từ module project_management"""
    _inherit = 'cong_viec'
    
    # Liên kết Many2one tới model projects từ project_management
    du_an_id = fields.Many2one(
        'projects', 
        string='Dự án', 
        ondelete='cascade',
        help='Dự án từ module Project Management. Mỗi công việc chỉ thuộc một dự án.'
    )

    don_gia_gio_trung_binh = fields.Float(
        string='Đơn giá giờ TB',
        compute='_compute_chi_phi_nhan_su',
        store=True
    )
    chi_phi_nhan_su_du_kien = fields.Float(
        string='Chi phí nhân sự dự kiến',
        compute='_compute_chi_phi_nhan_su',
        store=True
    )
    chi_phi_nhan_su_thuc_te = fields.Float(
        string='Chi phí nhân sự thực tế',
        compute='_compute_chi_phi_nhan_su',
        store=True
    )

    @api.depends(
        'gio_lam_du_kien',
        'gio_lam_thuc_te',
        'nguoi_phu_trach_id.don_gia_gio',
        'nhan_vien_phan_cong_ids.don_gia_gio',
    )
    def _compute_chi_phi_nhan_su(self):
        for record in self:
            employees = record.nhan_vien_phan_cong_ids
            if not employees and record.nguoi_phu_trach_id:
                employees = record.nguoi_phu_trach_id

            rates = employees.mapped('don_gia_gio') if employees else []
            avg_rate = sum(rates) / len(rates) if rates else 0.0
            record.don_gia_gio_trung_binh = avg_rate
            record.chi_phi_nhan_su_du_kien = record.gio_lam_du_kien * avg_rate
            record.chi_phi_nhan_su_thuc_te = record.gio_lam_thuc_te * avg_rate

