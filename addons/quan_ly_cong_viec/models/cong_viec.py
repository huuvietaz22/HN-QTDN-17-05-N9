# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CongViec(models.Model):
    _name = 'cong_viec'
    _description = 'Bảng quản lý công việc'
    _rec_name = 'ten_cong_viec'

    # Mã công việc - tự động tạo bằng sequence
    ma_cong_viec = fields.Char(
        string="Mã công việc",
        readonly=True,
        copy=False,
        default=lambda self: 'Mới'
    )
    
    ten_cong_viec = fields.Char(string="Tên công việc", required=True)
    mo_ta = fields.Text(string="Mô tả")
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu")
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")
    muc_do_uu_tien = fields.Selection(
        selection=[
            ('thap', 'Thấp'),
            ('trung_binh', 'Trung bình'),
            ('cao', 'Cao'),
            ('khan_cap', 'Khẩn cấp'),
        ],
        string="Mức độ ưu tiên",
        default='trung_binh'
    )
    trang_thai = fields.Selection(
        selection=[
            ('moi', 'Mới'),
            ('dang_thuc_hien', 'Đang thực hiện'),
            ('hoan_thanh', 'Hoàn thành'),
            ('tam_dung', 'Tạm dừng'),
        ],
        string="Trạng thái",
        default='moi'
    )

    nhiem_vu_ids = fields.One2many(
        'nhiem_vu',
        'cong_viec_id',
        string='Nhiệm vụ'
    )
    
    # ============ TÍCH HỢP VỚI MODULE NHÂN SỰ ============
    # Người phụ trách công việc
    nguoi_phu_trach_id = fields.Many2one(
        'nhan_vien',
        string='Người phụ trách',
        required=True,
        ondelete='restrict',
        help='Nhân viên chịu trách nhiệm công việc này'
    )
    
    # Nhân viên được phân công (Many2many)
    nhan_vien_phan_cong_ids = fields.Many2many(
        'nhan_vien',
        'cong_viec_nhan_vien_rel',
        'cong_viec_id',
        'nhan_vien_id',
        string='Nhân viên thực hiện',
        help='Danh sách nhân viên được phân công'
    )
    
    # Giờ làm dự kiến và thực tế
    gio_lam_du_kien = fields.Float(string='Giờ làm dự kiến')
    gio_lam_thuc_te = fields.Float(string='Giờ làm thực tế', default=0.0)
    
    # Tỷ lệ hoàn thành - người dùng nhập thủ công
    ti_le_hoan_thanh = fields.Float(
        string='Tỷ lệ hoàn thành (%)',
        default=0.0,
        help='Tỷ lệ hoàn thành công việc (0-100%)'
    )

    tong_nhiem_vu = fields.Integer(
        string='Tổng nhiệm vụ',
        compute='_compute_nhiem_vu_stats',
        store=True
    )
    nhiem_vu_hoan_thanh = fields.Integer(
        string='Nhiệm vụ hoàn thành',
        compute='_compute_nhiem_vu_stats',
        store=True
    )

    @api.depends('nhiem_vu_ids.trang_thai')
    def _compute_nhiem_vu_stats(self):
        for record in self:
            record.tong_nhiem_vu = len(record.nhiem_vu_ids)
            record.nhiem_vu_hoan_thanh = len(
                record.nhiem_vu_ids.filtered(lambda task: task.trang_thai == 'hoan_thanh')
            )

    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_dates(self):
        for record in self:
            if record.ngay_bat_dau and record.ngay_ket_thuc and record.ngay_bat_dau > record.ngay_ket_thuc:
                raise ValidationError('Ngày bắt đầu công việc không được lớn hơn ngày kết thúc.')

    @api.constrains('ti_le_hoan_thanh', 'gio_lam_du_kien', 'gio_lam_thuc_te')
    def _check_numeric_values(self):
        for record in self:
            if record.ti_le_hoan_thanh < 0 or record.ti_le_hoan_thanh > 100:
                raise ValidationError('Tỷ lệ hoàn thành công việc phải nằm trong khoảng 0-100%.')
            if record.gio_lam_du_kien < 0 or record.gio_lam_thuc_te < 0:
                raise ValidationError('Số giờ làm việc không được âm.')

    def _sync_progress_from_nhiem_vu(self):
        """Đồng bộ tiến độ công việc từ các nhiệm vụ con khi đã có nhiệm vụ."""
        for record in self:
            if not record.nhiem_vu_ids:
                continue

            progress = sum(record.nhiem_vu_ids.mapped('ti_le_hoan_thanh')) / len(record.nhiem_vu_ids)
            vals = {'ti_le_hoan_thanh': progress}
            if progress >= 100:
                vals['trang_thai'] = 'hoan_thanh'
            elif progress > 0 and record.trang_thai in ('moi', 'hoan_thanh'):
                vals['trang_thai'] = 'dang_thuc_hien'
            record.with_context(skip_task_progress_sync=True).write(vals)

    @api.model
    def create(self, vals):
        """Tạo công việc mới"""
        # Đồng bộ tỷ lệ hoàn thành với trạng thái khi tạo mới
        trang_thai = vals.get('trang_thai')
        ti_le = vals.get('ti_le_hoan_thanh')
        # Nếu tạo mới đã chọn trạng thái hoàn thành nhưng chưa nhập % thì tự set 100%
        if trang_thai == 'hoan_thanh' and (ti_le is None or ti_le == 0.0):
            vals['ti_le_hoan_thanh'] = 100.0

        # Xử lý Mã công việc (Sequence)
        if vals.get('ma_cong_viec', 'Mới') == 'Mới':
            # Dùng 'or' để phòng trường hợp chưa có sequence thì lấy tạm CV001
            vals['ma_cong_viec'] = self.env['ir.sequence'].next_by_code('cong_viec.sequence') or 'CV001'
        
        return super(CongViec, self).create(vals)

    def write(self, vals):
        """Đồng bộ trạng thái và tỷ lệ hoàn thành khi cập nhật công việc

        - Khi trạng thái được chuyển sang 'hoan_thanh' mà % đang nhỏ hơn 100 -> tự động set 100
        - Không ép ngược lại (không tự giảm %) để tránh làm mất dữ liệu người dùng nhập tay
        - Trigger AI re-scan khi có thay đổi quan trọng
        """
        res = super(CongViec, self).write(vals)

        # Chỉ xử lý khi có thay đổi trạng_thai
        if 'trang_thai' in vals:
            for record in self:
                if record.trang_thai == 'hoan_thanh' and record.ti_le_hoan_thanh < 100.0:
                    record.ti_le_hoan_thanh = 100.0
        
        # Trigger AI re-scan cho dự án khi task có thay đổi quan trọng
        important_fields = {'trang_thai', 'ti_le_hoan_thanh', 'ngay_ket_thuc', 'nguoi_phu_trach_id'}
        if 'du_an_id' in self._fields and any(field in vals for field in important_fields):
            # Lấy danh sách dự án liên quan
            projects = self.mapped('du_an_id').filtered(lambda p: p)
            for project in projects:
                try:
                    # Gọi AI re-scan (chạy async nếu có thể)
                    project._auto_detect_risks()
                except Exception as e:
                    # Không để lỗi AI làm gián đoạn việc cập nhật task
                    _logger.warning(f"Không thể chạy AI re-scan cho dự án {project.projects_id}: {str(e)}")

        return res

    def name_get(self):
        """Hiển thị mã và tên công việc"""
        result = []
        for record in self:
            if record.ten_cong_viec:
                name = f"{record.ma_cong_viec} - {record.ten_cong_viec}"
            else:
                name = record.ma_cong_viec or f'Công việc #{record.id}'
            result.append((record.id, name))
        return result
