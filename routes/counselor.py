# routes/counselor.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import json
from models import db, User, Class, Course, AcademicAlert, CounselingRecord, Exam
from werkzeug.utils import secure_filename

counselor_bp = Blueprint('counselor', __name__, url_prefix='/counselor')


@counselor_bp.route('/dashboard')
@login_required
def dashboard():
    """辅导员仪表板"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    user_info = {
        'name': current_user.real_name,
        'role': current_user.role,
        'username': current_user.username
    }

    # 获取辅导员负责的班级
    classes = Class.query.filter_by(counselor_id=current_user.id).all()

    # 统计预警信息
    total_alerts = AcademicAlert.query.filter_by(counselor_id=current_user.id).count()
    active_alerts = AcademicAlert.query.filter_by(counselor_id=current_user.id, status='active').count()

    return render_template('counselor/dashboard.html',
                           title='辅导员仪表板',
                           user=user_info,
                           role='counselor',
                           classes=classes,
                           total_alerts=total_alerts,
                           active_alerts=active_alerts,
                           now=datetime.now())


@counselor_bp.route('/academic-alerts')
@login_required
def academic_alerts():
    """学业预警页面"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取筛选条件
    alert_level = request.args.get('alert_level', '')
    class_id = request.args.get('class_id', '')
    status = request.args.get('status', 'active')

    # 构建查询
    query = AcademicAlert.query.filter_by(counselor_id=current_user.id)

    if alert_level:
        query = query.filter_by(alert_level=alert_level)

    if class_id:
        query = query.join(User).filter(User.class_id == class_id)

    if status:
        query = query.filter_by(status=status)

    alerts = query.order_by(AcademicAlert.created_at.desc()).all()

    # 预处理数据，解析JSON字符串
    for alert in alerts:
        try:
            # 如果failed_courses是JSON字符串，解析它
            if alert.failed_courses and alert.failed_courses.startswith('['):
                import json
                alert.parsed_courses = json.loads(alert.failed_courses)
            else:
                alert.parsed_courses = [alert.failed_courses] if alert.failed_courses else []
        except:
            alert.parsed_courses = [alert.failed_courses] if alert.failed_courses else []

    # 获取辅导员负责的班级
    classes = Class.query.filter_by(counselor_id=current_user.id).all()

    return render_template('counselor/academic_alert.html',
                           alerts=alerts,
                           classes=classes,
                           alert_level=alert_level,
                           class_id=class_id,
                           status=status)


@counselor_bp.route('/alert-detail/<int:alert_id>')
@login_required
def alert_detail(alert_id):
    """预警详情"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    alert = AcademicAlert.query.get_or_404(alert_id)

    # 检查权限
    if alert.counselor_id != current_user.id:
        flash('无权访问此记录', 'danger')
        return redirect(url_for('counselor.academic_alerts'))

    # 预处理挂科科目数据
    alert.parsed_courses = alert.get_failed_courses_list()

    # 获取辅导记录
    counseling_records = CounselingRecord.query.filter_by(alert_id=alert_id) \
        .order_by(CounselingRecord.counseling_time.desc()).all()

    return render_template('counselor/alert_detail.html',
                           alert=alert,
                           counseling_records=counseling_records)


@counselor_bp.route('/add-counseling-record/<int:alert_id>', methods=['POST'])
@login_required
def add_counseling_record(alert_id):
    """添加辅导记录"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    alert = AcademicAlert.query.get_or_404(alert_id)

    # 检查权限
    if alert.counselor_id != current_user.id:
        flash('无权操作此记录', 'danger')
        return redirect(url_for('counselor.academic_alerts'))

    counseling_time_str = request.form.get('counseling_time')
    content = request.form.get('content')
    plan = request.form.get('plan')

    if not all([counseling_time_str, content]):
        flash('请填写辅导时间和内容', 'danger')
        return redirect(url_for('counselor.alert_detail', alert_id=alert_id))

    try:
        counseling_time = datetime.strptime(counseling_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('时间格式错误', 'danger')
        return redirect(url_for('counselor.alert_detail', alert_id=alert_id))

    # 创建辅导记录
    record = CounselingRecord(
        alert_id=alert_id,
        counselor_id=current_user.id,
        counseling_time=counseling_time,
        content=content,
        plan=plan
    )

    db.session.add(record)
    db.session.commit()

    flash('辅导记录添加成功', 'success')
    return redirect(url_for('counselor.alert_detail', alert_id=alert_id))


@counselor_bp.route('/update-alert-status/<int:alert_id>', methods=['POST'])
@login_required
def update_alert_status(alert_id):
    """更新预警状态"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    alert = AcademicAlert.query.get_or_404(alert_id)

    # 检查权限
    if alert.counselor_id != current_user.id:
        flash('无权操作此记录', 'danger')
        return redirect(url_for('counselor.academic_alerts'))

    status = request.form.get('status')
    if status in ['active', 'resolved']:
        alert.status = status
        db.session.commit()
        flash('预警状态更新成功', 'success')
    else:
        flash('状态值无效', 'danger')

    return redirect(url_for('counselor.alert_detail', alert_id=alert_id))


@counselor_bp.route('/export-alerts')
@login_required
def export_alerts():
    """导出预警名单"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取筛选条件
    alert_level = request.args.get('alert_level', '')
    class_id = request.args.get('class_id', '')

    # 构建查询
    query = AcademicAlert.query.filter_by(counselor_id=current_user.id)

    if alert_level:
        query = query.filter_by(alert_level=alert_level)

    if class_id:
        query = query.join(User).filter(User.class_id == class_id)

    alerts = query.order_by(AcademicAlert.alert_level, AcademicAlert.created_at).all()

    # 生成Excel格式内容（简化版，实际可以使用openpyxl等库）
    excel_content = "学号,姓名,班级,预警等级,挂科数量,挂科科目,预警原因,学期\n"

    for alert in alerts:
        student = alert.student
        class_name = student.class_info.class_name if student and student.class_info else ''

        excel_content += f'{student.username},{student.real_name},{class_name},'
        excel_content += f'{alert.alert_level},{alert.total_failed},'
        excel_content += f'"{alert.failed_courses}","{alert.reason}",{alert.semester}\n'

    from io import BytesIO
    buffer = BytesIO(excel_content.encode('utf-8'))

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'学业预警名单_{datetime.now().strftime("%Y%m%d")}.csv',
        mimetype='text/csv'
    )


@counselor_bp.route('/generate-alerts')
@login_required
def generate_alerts():
    """生成学业预警（测试用）"""
    if not current_user.is_counselor():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取辅导员负责的班级
    classes = Class.query.filter_by(counselor_id=current_user.id).all()

    if not classes:
        flash('您目前没有负责的班级', 'warning')
        return redirect(url_for('counselor.dashboard'))

    # 模拟生成预警数据（实际应该根据成绩数据自动生成）
    sample_alerts = [
        {
            'student_username': 'stu001',
            'alert_level': '一级',
            'failed_courses': '["高等数学", "数据结构", "Python程序设计"]',
            'total_failed': 3,
            'reason': '连续两学期挂科≥2门',
            'semester': '2023-2024-1'
        },
        {
            'student_username': 'stu002',
            'alert_level': '二级',
            'failed_courses': '["高等数学", "数据结构"]',
            'total_failed': 2,
            'reason': '挂科2门',
            'semester': '2023-2024-1'
        }
    ]

    created_count = 0
    for alert_data in sample_alerts:
        student = User.query.filter_by(username=alert_data['student_username']).first()
        if student and student.class_info and student.class_info.counselor_id == current_user.id:
            # 检查是否已存在相同预警
            existing_alert = AcademicAlert.query.filter_by(
                student_id=student.id,
                semester=alert_data['semester']
            ).first()

            if not existing_alert:
                alert = AcademicAlert(
                    student_id=student.id,
                    counselor_id=current_user.id,
                    alert_level=alert_data['alert_level'],
                    failed_courses=alert_data['failed_courses'],
                    total_failed=alert_data['total_failed'],
                    reason=alert_data['reason'],
                    semester=alert_data['semester']
                )
                db.session.add(alert)
                created_count += 1

    if created_count > 0:
        db.session.commit()
        flash(f'成功生成 {created_count} 条学业预警', 'success')
    else:
        flash('没有新的预警需要生成', 'info')

    return redirect(url_for('counselor.academic_alerts'))