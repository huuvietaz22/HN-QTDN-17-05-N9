# -*- coding: utf-8 -*-

import logging
import json
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    _logger.warning("google-generativeai library not installed. Gemini AI features will be disabled.")


class GeminiAIProvider(models.Model):
    """
    Google Gemini AI Provider cho Risk Management
    
    Tính năng:
    - Phân tích mô tả dự án để tìm risks tiềm ẩn
    - Generate mitigation plans thông minh
    - Phân tích đa chiều từ data dự án
    - Root cause analysis nâng cao
    """
    _name = 'gemini.ai.provider'
    _description = 'Google Gemini AI Provider for Risk Management'
    
    name = fields.Char(string='Provider Name', default='Google Gemini AI', readonly=True)
    api_key = fields.Char(string='API Key', help='Google AI Studio API Key')
    model_name = fields.Selection([
        ('gemini-pro', 'Gemini Pro'),
        ('gemini-1.5-flash', 'Gemini 1.5 Flash'),
        ('gemini-1.5-pro', 'Gemini 1.5 Pro'),
    ], string='Model', default='gemini-pro', required=True)
    is_active = fields.Boolean(string='Active', default=True)
    temperature = fields.Float(string='Temperature', default=0.7, help='0.0-1.0: Controls randomness')
    max_tokens = fields.Integer(string='Max Output Tokens', default=2048)
    last_used = fields.Datetime(string='Last Used')
    total_requests = fields.Integer(string='Total Requests', default=0, readonly=True)
    
    _sql_constraints = [
        ('unique_provider', 'UNIQUE(name)', 'Only one Gemini provider can exist!')
    ]
    
    @api.model
    def get_provider(self):
        """Lấy provider instance (singleton pattern)"""
        provider = self.search([], limit=1)
        if not provider:
            provider = self.create({
                'name': 'Google Gemini AI',
                'model_name': 'gemini-pro',
            })
        return provider
    
    def _configure_gemini(self):
        """Configure Gemini API với API key"""
        if not GEMINI_AVAILABLE:
            raise UserError("Thư viện google-generativeai chưa được cài đặt. Vui lòng chạy: pip install google-generativeai")
        
        if not self.api_key:
            raise UserError("API Key chưa được cấu hình. Vui lòng vào Cấu hình > AI Settings để thêm API Key.")
        
        try:
            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(self.model_name)
        except Exception as e:
            _logger.error(f"Error configuring Gemini: {str(e)}")
            raise UserError(f"Lỗi khi cấu hình Gemini API: {str(e)}")
    
    def _update_usage_stats(self):
        """Cập nhật thống kê sử dụng"""
        self.write({
            'last_used': fields.Datetime.now(),
            'total_requests': self.total_requests + 1
        })
    
    @api.model
    def analyze_project_description(self, project):
        """
        Sử dụng Gemini để phân tích mô tả dự án và tìm risks tiềm ẩn
        
        Args:
            project: recordset của model projects
            
        Returns:
            list: Danh sách risks dưới dạng dict
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            _logger.warning("Gemini AI provider is not active")
            return []
        
        if not project.description:
            return []
        
        try:
            model = provider._configure_gemini()
            
            prompt = f"""
Bạn là chuyên gia quản lý rủi ro dự án. Hãy phân tích thông tin dự án sau và xác định các rủi ro tiềm ẩn:

**Thông tin dự án:**
- Tên dự án: {project.projects_name}
- Mô tả: {project.description or 'Không có'}
- Ngày bắt đầu: {project.start_date or 'Chưa xác định'}
- Ngày kết thúc dự kiến: {project.actual_end_date or 'Chưa xác định'}
- Tiến độ hiện tại: {project.progress:.1f}%
- Số lượng công việc: {len(project.task_ids)}
- Ngân sách: {sum(project.budget_ids.mapped('budget_planned')) if project.budget_ids else 0:,.0f} VND

**Yêu cầu:**
Trả về JSON với cấu trúc sau (KHÔNG thêm markdown hoặc text khác):
{{
    "risks": [
        {{
            "type": "schedule" hoặc "budget" hoặc "resource" hoặc "quality" hoặc "scope",
            "name": "Tên rủi ro ngắn gọn (dưới 80 ký tự)",
            "description": "Mô tả chi tiết rủi ro",
            "probability": 0-100 (số nguyên),
            "impact": 1-10 (số thập phân),
            "root_cause": "Nguyên nhân gốc rễ",
            "mitigation_plan": "Kế hoạch khắc phục chi tiết",
            "confidence": 60-95 (độ tin cậy)
        }}
    ]
}}

Chỉ phân tích các rủi ro thực sự quan trọng (tối đa 3-5 rủi ro). Nếu không phát hiện rủi ro nào, trả về {{"risks": []}}.
"""
            
            _logger.info(f"Sending request to Gemini for project {project.projects_id}")
            response = model.generate_content(prompt)
            
            provider._update_usage_stats()
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown code blocks nếu có
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            risks = []
            for item in result.get('risks', []):
                risks.append({
                    'risk_type': item.get('type') or item.get('risk_type') or 'scope',
                    'name': item.get('name') or 'Rủi ro từ Gemini AI',
                    'description': item.get('description') or '',
                    'probability': min(float(item.get('probability', 50.0)) / 100.0, 1.0),
                    'impact_score': float(item.get('impact') or item.get('impact_score') or 5.0),
                    'root_cause': item.get('root_cause') or '',
                    'mitigation_plan': item.get('mitigation_plan') or '',
                    'ai_confidence': min(float(item.get('confidence', 70.0)) / 100.0, 1.0),
                })
            
            _logger.info(f"Gemini analysis completed. Found {len(risks)} risks for project {project.projects_id}")
            
            return risks
            
        except json.JSONDecodeError as e:
            _logger.error(f"Failed to parse Gemini response: {str(e)}\nResponse: {response_text}")
            return []
        except Exception as e:
            _logger.error(f"Error in Gemini analysis: {str(e)}")
            return []
    
    @api.model
    def generate_mitigation_plan(self, risk_assessment):
        """
        Sử dụng Gemini để generate kế hoạch khắc phục chi tiết
        
        Args:
            risk_assessment: recordset của model risk.assessment
            
        Returns:
            str: Kế hoạch khắc phục chi tiết
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            return risk_assessment.mitigation_plan  # Fallback to existing plan
        
        try:
            model = provider._configure_gemini()
            
            prompt = f"""
Bạn là chuyên gia quản lý rủi ro dự án. Hãy tạo kế hoạch khắc phục CHI TIẾT cho rủi ro sau:

**Thông tin rủi ro:**
- Tên: {risk_assessment.name}
- Loại: {dict(risk_assessment._fields['risk_type'].selection).get(risk_assessment.risk_type)}
- Mức độ: {dict(risk_assessment._fields['risk_level'].selection).get(risk_assessment.risk_level)}
- Xác suất: {risk_assessment.probability}%
- Tác động: {risk_assessment.impact_score}/10
- Điểm rủi ro: {risk_assessment.risk_score:.1f}
- Mô tả: {risk_assessment.description}
- Nguyên nhân: {risk_assessment.root_cause}

**Yêu cầu:**
Tạo kế hoạch khắc phục THỰC TẾ, CỤ THỂ với:
1. Hành động ngay lập tức (Quick wins - 1-2 ngày)
2. Giải pháp trung hạn (1-2 tuần)
3. Giải pháp dài hạn (phòng ngừa)
4. Người chịu trách nhiệm đề xuất
5. Metrics để đo lường hiệu quả

Format: Text markdown, có bullet points, dễ đọc, KHÔNG trả về JSON.
"""
            
            response = model.generate_content(prompt)
            provider._update_usage_stats()
            
            mitigation_plan = response.text.strip()
            
            _logger.info(f"Generated mitigation plan for risk {risk_assessment.id}")
            
            return mitigation_plan
            
        except Exception as e:
            _logger.error(f"Error generating mitigation plan: {str(e)}")
            return risk_assessment.mitigation_plan
    
    @api.model
    def analyze_root_cause(self, risk_assessment):
        """
        Sử dụng Gemini để phân tích nguyên nhân gốc rễ (Root Cause Analysis)
        
        Args:
            risk_assessment: recordset của model risk.assessment
            
        Returns:
            str: Phân tích nguyên nhân chi tiết
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            return risk_assessment.root_cause
        
        try:
            model = provider._configure_gemini()
            
            project = risk_assessment.project_id
            
            prompt = f"""
Bạn là chuyên gia phân tích rủi ro. Sử dụng phương pháp 5 WHYs để phân tích nguyên nhân gốc rễ:

**Rủi ro:**
{risk_assessment.name}

**Thông tin dự án:**
- Tiến độ: {project.progress:.1f}%
- Số tasks: {len(project.task_ids)} ({len(project.task_ids.filtered(lambda t: t.trang_thai == 'hoan_thanh'))} hoàn thành)
- Budget spent: {sum(project.budget_ids.mapped('budget_spent')):,.0f} / {sum(project.budget_ids.mapped('budget_planned')):,.0f} VND
- Team size: {len(project.task_ids.mapped('nhan_vien_phan_cong_ids'))} người

**Mô tả rủi ro:**
{risk_assessment.description}

**Yêu cầu:**
1. Áp dụng 5 WHYs để tìm nguyên nhân gốc rễ
2. Xác định contributing factors (yếu tố đóng góp)
3. Đánh giá mức độ kiểm soát của từng nguyên nhân (controllable/uncontrollable)
4. Đề xuất prevention strategy

Format: Text markdown, có cấu trúc rõ ràng.
"""
            
            response = model.generate_content(prompt)
            provider._update_usage_stats()
            
            root_cause = response.text.strip()
            
            _logger.info(f"Generated root cause analysis for risk {risk_assessment.id}")
            
            return root_cause
            
        except Exception as e:
            _logger.error(f"Error in root cause analysis: {str(e)}")
            return risk_assessment.root_cause
    
    @api.model
    def comprehensive_project_analysis(self, project):
        """
        Phân tích toàn diện dự án bằng Gemini AI
        
        Returns:
            dict: {
                'risks': [...],
                'insights': str,
                'recommendations': str
            }
        """
        provider = self.get_provider()
        
        if not provider.is_active:
            return {'risks': [], 'insights': '', 'recommendations': ''}
        
        try:
            model = provider._configure_gemini()
            
            # Collect comprehensive data
            total_budget = sum(project.budget_ids.mapped('budget_planned'))
            total_spent = sum(project.budget_ids.mapped('budget_spent'))
            spent_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
            
            tasks = project.task_ids
            completed_tasks = tasks.filtered(lambda t: t.trang_thai == 'hoan_thanh')
            delayed_tasks = tasks.filtered(lambda t: t.ngay_ket_thuc and t.ngay_ket_thuc < fields.Date.today() and t.trang_thai != 'hoan_thanh')
            
            prompt = f"""
Bạn là AI chuyên gia quản lý dự án. Phân tích TOÀN DIỆN dự án sau:

**DỮ LIỆU DỰ ÁN:**

Tổng quan:
- Tên: {project.projects_name}
- Trạng thái: {dict(project._fields['status'].selection).get(project.status)}
- Tiến độ: {project.progress:.1f}%
- Ngày bắt đầu: {project.start_date}
- Deadline: {project.actual_end_date}

Công việc:
- Tổng số: {len(tasks)}
- Hoàn thành: {len(completed_tasks)} ({len(completed_tasks)/len(tasks)*100 if tasks else 0:.1f}%)
- Trễ hạn: {len(delayed_tasks)} ({len(delayed_tasks)/len(tasks)*100 if tasks else 0:.1f}%)

Ngân sách:
- Kế hoạch: {total_budget:,.0f} VND
- Đã chi: {total_spent:,.0f} VND ({spent_percentage:.1f}%)
- Còn lại: {total_budget - total_spent:,.0f} VND

Team:
- Số người: {len(project.task_ids.mapped('nhan_vien_phan_cong_ids'))}

**YÊU CẦU PHÂN TÍCH:**
Trả về JSON với cấu trúc:
{{
    "risks": [
        {{
            "type": "schedule/budget/resource/quality/scope",
            "name": "Tên ngắn gọn",
            "description": "Mô tả",
            "probability": 0-100,
            "impact": 1-10,
            "root_cause": "Nguyên nhân",
            "mitigation_plan": "Giải pháp",
            "confidence": 70-95
        }}
    ],
    "insights": "Những phát hiện quan trọng về tình hình dự án (2-3 đoạn)",
    "recommendations": "Top 3-5 khuyến nghị ưu tiên để cải thiện dự án"
}}

QUAN TRỌNG: Chỉ trả về JSON thuần, KHÔNG thêm markdown hoặc text khác.
"""
            
            _logger.info(f"Sending comprehensive analysis request to Gemini for project {project.projects_id}")
            response = model.generate_content(prompt)
            
            provider._update_usage_stats()
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            _logger.info(f"Comprehensive analysis completed for project {project.projects_id}")
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {'risks': [], 'insights': '', 'recommendations': ''}
    
    def action_test_connection(self):
        """Test Gemini API connection"""
        self.ensure_one()
        
        try:
            model = self._configure_gemini()
            response = model.generate_content("Hello! Just testing the connection. Reply with 'OK'.")
            
            if response and response.text:
                self._update_usage_stats()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Kết nối thành công!',
                        'message': f'Gemini API hoạt động bình thường. Response: {response.text[:100]}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi kết nối',
                    'message': f'Không thể kết nối Gemini API: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
