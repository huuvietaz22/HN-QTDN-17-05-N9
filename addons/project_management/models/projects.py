from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class Projects(models.Model):
    _name = 'projects'
    _description = 'Quản lý dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    projects_id = fields.Char("Mã dự án", required=True, copy=False, readonly=True, default='New')
    projects_name = fields.Char("Tên dự án", required=True, tracking=True)
    description = fields.Text("Mô tả dự án")
    
    manager_name = fields.Many2one('nhan_vien', string="Quản lý dự án", tracking=True)
    owner_id = fields.Many2one(
        'nhan_vien',
        string='Chủ dự án',
        tracking=True,
        help='Người chịu trách nhiệm sở hữu mục tiêu, phạm vi và kết quả cuối cùng của dự án.'
    )

    start_date = fields.Date("Ngày bắt đầu")
    actual_end_date = fields.Date("Ngày kết thúc dự kiến/thực tế")
    phuong_phap_quan_ly = fields.Selection(
        selection=[
            ('waterfall', 'Waterfall'),
            ('agile', 'Agile'),
            ('scrum', 'Scrum'),
            ('kanban', 'Kanban'),
            ('hybrid', 'Hybrid'),
        ],
        string='Phương pháp quản lý',
        default='agile',
        tracking=True
    )

    progress = fields.Float(
        "Tiến độ (%)",
        compute='_compute_progress',
        store=True,
        help="Tiến độ dự án được tự động tính từ tỷ lệ hoàn thành của các công việc trong dự án."
    )
    status = fields.Selection(
        selection=[
            ('not_started', 'Chưa bắt đầu'),
            ('in_progress', 'Đang thực hiện'),
            ('completed', 'Hoàn thành'),
            ('delayed', 'Trì hoãn'),
            ('cancelled', 'Hủy bỏ')
        ], 
        string='Trạng thái', store=True
    )

    ly_do_1 = fields.Text(string="Lý do hủy bỏ", help="Lý do hủy bỏ công việc")

    task_ids = fields.One2many(
        'cong_viec', 
        'du_an_id', 
        string='Công việc',
        help='Danh sách công việc thuộc dự án này (field du_an_id được thêm bởi module project_management)'
    )
    milestone_ids = fields.One2many('project.milestone', 'project_id', string='Mốc nghiệm thu')
    change_request_ids = fields.One2many('project.change.request', 'project_id', string='Yêu cầu thay đổi')
    meeting_ids = fields.One2many('project.meeting', 'project_id', string='Biên bản họp')
    team_role_ids = fields.One2many('project.team.role', 'project_id', string='Vai trò dự án')
    milestone_count = fields.Integer(string='Số mốc', compute='_compute_governance_counts')
    change_request_count = fields.Integer(string='Số yêu cầu thay đổi', compute='_compute_governance_counts')
    meeting_count = fields.Integer(string='Số cuộc họp', compute='_compute_governance_counts')

    @api.depends('milestone_ids', 'change_request_ids', 'meeting_ids')
    def _compute_governance_counts(self):
        for project in self:
            project.milestone_count = len(project.milestone_ids)
            project.change_request_count = len(project.change_request_ids)
            project.meeting_count = len(project.meeting_ids)

    # ============ TRƯỜNG XÉT DUYỆT DỰ ÁN ============
    approval_state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Chờ xét duyệt'),
        ('approved', 'Đã phê duyệt'),
        ('rejected', 'Từ chối')
    ], string='Trạng thái duyệt', default='draft', tracking=True)
    
    approver_id = fields.Many2one('nhan_vien', string='Người phê duyệt', readonly=True)
    approval_date = fields.Datetime(string='Ngày phê duyệt', readonly=True)
    approval_signature = fields.Binary(string='Chữ ký phê duyệt')
    rejection_reason = fields.Text(string='Lý do từ chối') 

    @api.constrains('start_date', 'actual_end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.actual_end_date and record.start_date > record.actual_end_date:
                raise ValidationError('Ngày bắt đầu dự án không được lớn hơn ngày kết thúc.')

    @api.constrains('progress')
    def _check_progress(self):
        for record in self:
            if record.progress < 0 or record.progress > 100:
                raise ValidationError('Tiến độ dự án phải nằm trong khoảng 0-100%.')

    @api.depends('task_ids.trang_thai', 'task_ids.ti_le_hoan_thanh')
    def _compute_progress(self):
        """Tính tiến độ dự án từ công việc (cong_viec)"""
        for project in self:
            if project.task_ids:
                # Tính trung bình tỷ lệ hoàn thành của tất cả công việc
                total_progress = sum(project.task_ids.mapped('ti_le_hoan_thanh'))
                project.progress = total_progress / len(project.task_ids)
            else:
                project.progress = 0.0
            if project.progress >= 100 and project.status != 'cancelled':
                project.status = 'completed'
            elif project.progress > 0 and project.status in (False, 'not_started', 'completed'):
                project.status = 'in_progress'
            elif project.progress == 0 and not project.status:
                project.status = 'not_started'

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.projects_id}"

            result.append((record.id, name))
        return result
    
    budget_ids = fields.One2many('budgets', inverse_name='projects_id', string="Ngân sách Dự án")
    tong_chi_phi_nhan_su = fields.Float(
        string='Tổng chi phí nhân sự',
        compute='_compute_project_costs',
        store=True
    )
    tong_chi_phi_phat_sinh = fields.Float(
        string='Tổng chi phí phát sinh',
        compute='_compute_project_costs',
        store=True
    )
    tong_chi_phi_du_an = fields.Float(
        string='Tổng chi phí dự án',
        compute='_compute_project_costs',
        store=True
    )

    @api.depends('task_ids.chi_phi_nhan_su_thuc_te', 'budget_ids.budget_spent')
    def _compute_project_costs(self):
        for project in self:
            project.tong_chi_phi_nhan_su = sum(project.task_ids.mapped('chi_phi_nhan_su_thuc_te'))
            project.tong_chi_phi_phat_sinh = sum(project.budget_ids.mapped('budget_spent'))
            project.tong_chi_phi_du_an = project.tong_chi_phi_nhan_su + project.tong_chi_phi_phat_sinh

    @api.model
    def _get_next_project_code(self):
        """Lấy mã dự án tiếp theo chưa sử dụng trong database"""
        sequence = self.env['ir.sequence'].search([('code', '=', 'projects.code')], limit=1)
        if sequence:
            # Lấy số tiếp theo từ sequence
            next_number = sequence.number_next
            # Tạo mã dự án dự kiến
            prefix = sequence.prefix or 'DA'
            padding = sequence.padding or 5
            next_code = f"{prefix}{str(next_number).zfill(padding)}"
            
            # Kiểm tra xem mã này đã tồn tại trong database chưa
            while self.search([('projects_id', '=', next_code)], limit=1):
                next_number += 1
                next_code = f"{prefix}{str(next_number).zfill(padding)}"
            
            return next_code
        return 'DA00001'

    @api.model
    def default_get(self, fields_list):
        """Hiển thị preview mã dự án trong form KHÔNG tăng sequence"""
        res = super(Projects, self).default_get(fields_list)
        if 'projects_id' in fields_list:
            res['projects_id'] = self._get_next_project_code()
        return res

    @api.model
    def _sync_owner_from_manager_for_existing_projects(self):
        """Gán chủ dự án mặc định cho dữ liệu cũ khi nâng cấp module."""
        projects_without_owner = self.search([
            ('owner_id', '=', False),
            ('manager_name', '!=', False),
        ])
        for project in projects_without_owner:
            project.owner_id = project.manager_name
        return True

    @api.model
    def create(self, vals):
        """Tự động sinh mã dự án khi lưu và đồng bộ sequence"""
        if not vals.get('projects_id') or vals.get('projects_id') == 'New':
            # Lấy mã tiếp theo chưa sử dụng
            next_code = self._get_next_project_code()
            vals['projects_id'] = next_code
            
            # Đồng bộ sequence với số vừa sử dụng
            sequence = self.env['ir.sequence'].search([('code', '=', 'projects.code')], limit=1)
            if sequence:
                # Lấy số từ mã vừa tạo (bỏ prefix)
                used_number = int(next_code.replace(sequence.prefix or 'DA', '', 1))
                # Cập nhật sequence để số tiếp theo là used_number + 1
                if used_number >= sequence.number_next:
                    sequence.write({'number_next': used_number + 1})
        
        project = super(Projects, self).create(vals)
        
        # Tự động phát hiện rủi ro khi tạo dự án mới (chạy async để không block)
        project.with_delay()._auto_detect_risks() if hasattr(project, 'with_delay') else project._auto_detect_risks()
        
        return project
    
    def write(self, vals):
        """Tự động phát hiện lại rủi ro khi dự án có thay đổi quan trọng"""
        result = super(Projects, self).write(vals)
        
        # Các field quan trọng trigger AI re-scan
        important_fields = {
            'progress', 'status', 'actual_end_date', 'start_date',
            'approval_state'
        }
        
        # Nếu có thay đổi về các field quan trọng, chạy lại AI
        if any(field in vals for field in important_fields):
            for project in self:
                _logger.info(f"Dự án {project.projects_id} có thay đổi quan trọng, chạy lại AI phát hiện rủi ro...")
                project._auto_detect_risks()
        
        return result

    def action_view_task_chart(self):
        """Xem biểu đồ công việc - sử dụng cong_viec"""
        self.ensure_one()  # Đảm bảo phương thức chỉ xử lý một bản ghi
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biểu Đồ Công Việc',
            'res_model': 'cong_viec',
            'view_mode': 'graph',
            'domain': [('du_an_id', '=', self.id)],  # Lọc công việc theo dự án hiện tại
            'context': {'search_default_group_by_du_an_id': self.id},
            'target': 'current',
        }

    # ============ CÁC PHƯƠNG THỨC XÉT DUYỆT ============
    def action_submit_approval(self):
        """Gửi dự án đi xét duyệt"""
        for record in self:
            if not record.manager_name:
                raise UserError('Vui lòng chọn Quản lý dự án trước khi gửi xét duyệt!')
            if not record.owner_id:
                raise UserError('Vui lòng chọn Chủ dự án trước khi gửi xét duyệt!')
            if not record.projects_name:
                raise UserError('Vui lòng nhập tên dự án trước khi gửi xét duyệt!')
            record.approval_state = 'pending'

    def action_approve(self):
        """Phê duyệt dự án - yêu cầu có chữ ký"""
        for record in self:
            if not record.approval_signature:
                raise UserError('Vui lòng ký tên trước khi phê duyệt!')
            record.write({
                'approval_state': 'approved',
                'approver_id': record.manager_name.id,
                'approval_date': fields.Datetime.now(),
                'status': 'in_progress' if record.progress < 100 else 'completed',
            })
            # Tự động tạo công việc cốt lõi khi phê duyệt
            record._create_core_tasks()

    def _create_core_tasks(self):
        """Tạo các công việc cốt lõi cho dự án đã được phê duyệt"""
        self.ensure_one()
        
        # Kiểm tra module quan_ly_cong_viec có được cài đặt
        try:
            CongViec = self.env['cong_viec']
        except KeyError:
            # Module chưa cài, bỏ qua
            _logger.warning(f"Module quan_ly_cong_viec chưa được cài đặt. Không thể tạo công việc tự động cho dự án {self.projects_id}")
            return
        
        # Kiểm tra manager_name (required field)
        if not self.manager_name:
            _logger.warning(f"Dự án {self.projects_id} không có quản lý dự án. Không thể tạo công việc tự động.")
            return  # Không có manager, không thể tạo công việc
        
        # Danh sách 5 công việc cốt lõi
        core_tasks = [
            {'ten': 'Khởi động dự án và thống nhất phạm vi', 'uu_tien': 'cao'},
            {'ten': 'Lên kế hoạch và phân bổ nguồn lực', 'uu_tien': 'cao'},
            {'ten': 'Kiểm tra chất lượng', 'uu_tien': 'trung_binh'},
            {'ten': 'Báo cáo định kỳ', 'uu_tien': 'trung_binh'},
            {'ten': 'Đóng gói và bàn giao', 'uu_tien': 'cao'},
        ]
        
        # Tạo công việc với error handling
        created_count = 0
        created_tasks = []
        for task in core_tasks:
            try:
                new_task = CongViec.create({
                    'ten_cong_viec': task['ten'],
                    'du_an_id': self.id,
                    'muc_do_uu_tien': task['uu_tien'],
                    'trang_thai': 'moi',
                    'nguoi_phu_trach_id': self.manager_name.id,
                    'ngay_bat_dau': self.start_date,
                    'ngay_ket_thuc': self.actual_end_date,
                })
                created_tasks.append(new_task)
                created_count += 1
            except Exception as e:
                # Log lỗi nhưng không dừng quá trình
                _logger.error(f"Lỗi khi tạo công việc '{task['ten']}' cho dự án {self.projects_id}: {str(e)}")
        


    def action_reject(self):
        """Từ chối dự án"""
        for record in self:
            if not record.rejection_reason:
                raise UserError('Vui lòng nhập lý do từ chối!')
            record.approval_state = 'rejected'

    def action_reset_draft(self):
        """Đặt lại trạng thái nháp"""
        for record in self:
            record.write({
                'approval_state': 'draft',
                'approval_signature': False,
                'approver_id': False,
                'approval_date': False,
                'rejection_reason': False,
            })

    def action_print_approval_pdf(self):
        """In báo cáo phê duyệt dự án dạng PDF"""
        self.ensure_one()
        if self.approval_state != 'approved':
            raise UserError('Chỉ có thể in báo cáo cho dự án đã được phê duyệt!')
        return self.env.ref('project_management.action_report_project_approval').report_action(self)
    
    def _auto_detect_risks(self):
        """Tự động phát hiện rủi ro cho dự án (gọi AI engine)"""
        self.ensure_one()
        
        try:
            # Lấy AI engine
            RiskAIEngine = self.env['risk.ai.engine']
            RiskAssessment = self.env['risk.assessment']
            
            # Nếu dự án đã hoàn thành hoặc bị hủy, tự động resolve tất cả rủi ro AI
            if self.status in ['completed', 'cancelled'] or self.progress >= 100:
                ai_risks = RiskAssessment.search([
                    ('project_id', '=', self.id),
                    ('is_ai_detected', '=', True),
                    ('status', 'not in', ['resolved', 'accepted'])
                ])
                if ai_risks:
                    ai_risks.write({
                        'status': 'resolved',
                        'resolved_date': fields.Datetime.now()
                    })
                    _logger.info(f"Dự án {self.projects_id} đã hoàn thành. Đã resolve {len(ai_risks)} rủi ro AI.")
                return  # Không phát hiện rủi ro mới
            
            # Xóa các rủi ro cũ đã được AI phát hiện để tránh duplicate
            # Chỉ xóa rủi ro chưa được xử lý (identified, analyzing)
            old_ai_risks = RiskAssessment.search([
                ('project_id', '=', self.id),
                ('is_ai_detected', '=', True),
                ('status', 'in', ['identified', 'analyzing'])
            ])
            if old_ai_risks:
                old_ai_risks.unlink()
                _logger.info(f"Đã xóa {len(old_ai_risks)} rủi ro AI cũ của dự án {self.projects_id}")
            
            # Phát hiện các loại rủi ro
            all_risks = []
            
            # 1. Rủi ro tiến độ
            schedule_risks = RiskAIEngine.detect_schedule_risk(self)
            all_risks.extend(schedule_risks)
            
            # 2. Rủi ro ngân sách
            budget_risks = RiskAIEngine.detect_budget_risk(self)
            all_risks.extend(budget_risks)
            
            # 3. Rủi ro nguồn lực
            resource_risks = RiskAIEngine.detect_resource_risk(self)
            all_risks.extend(resource_risks)
            
            # Nếu không có rủi ro nào được phát hiện, tạo một rủi ro mặc định cho dự án mới
            if not all_risks and not self.task_ids and not self.budget_ids:
                all_risks.append({
                    'name': 'Dự án mới thiếu thông tin',
                    'risk_type': 'scope',
                    'probability': 0.70,  # 70% = 0.70 trong Odoo
                    'impact_score': 6.0,
                    'description': f'Dự án "{self.projects_name}" vừa được tạo nhưng chưa có công việc và ngân sách. Cần bổ sung thông tin chi tiết.',
                    'root_cause': 'Dự án ở giai đoạn khởi tạo, chưa có kế hoạch chi tiết.',
                    'mitigation_plan': '1. Họp kickoff meeting\n2. Xác định scope và deliverables\n3. Lập danh sách công việc\n4. Phân bổ ngân sách\n5. Assign team members',
                    'ai_confidence': 0.85  # 85% = 0.85 trong Odoo
                })
            
            # Tạo bản ghi risk assessment cho mỗi rủi ro phát hiện
            created_risks = []
            for risk_data in all_risks:
                risk_data['project_id'] = self.id
                risk_data['is_ai_detected'] = True
                risk_data['status'] = 'identified'
                risk_data['assigned_to'] = self.manager_name.id if self.manager_name else False
                new_risk = RiskAssessment.create(risk_data)
                created_risks.append(new_risk)
            
            if created_risks:
                _logger.info(f"✓ AI đã phát hiện {len(created_risks)} rủi ro cho dự án {self.projects_id}")
                # Gửi notification cho user
                self.message_post(
                    body=f"AI đã tự động phát hiện {len(created_risks)} rủi ro tiềm ẩn. Vào menu 'AI Quản lý rủi ro' để xem chi tiết.",
                    subject="AI phát hiện rủi ro",
                    message_type='notification'
                )
            else:
                _logger.info(f"Không phát hiện rủi ro nào cho dự án {self.projects_id}")
            
        except Exception as e:
            # Không để lỗi AI làm gián đoạn việc tạo dự án
            _logger.warning(f"Không thể chạy AI phát hiện rủi ro cho dự án {self.projects_id}: {str(e)}", exc_info=True)
    
    def action_run_risk_detection(self):
        """Action button để chạy lại AI phát hiện rủi ro thủ công"""
        self.ensure_one()
        self._auto_detect_risks()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AI Phát hiện rủi ro',
                'message': 'Đã quét xong! Kiểm tra menu "AI Quản lý rủi ro" để xem kết quả.',
                'type': 'success',
                'sticky': False,
            }
        }
