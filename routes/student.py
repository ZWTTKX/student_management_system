# routes/student.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import os
from models import db, Schedule, Exam, LeaveApplication, User, Class, Course, SelectedCourse, Grade, Classroom, \
    ClassroomBooking,Announcement
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
def dashboard():
    """学生仪表板"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    user_info = {
        'name': current_user.real_name,
        'role': current_user.role,
        'username': current_user.username
    }

    # 获取各种统计信息
    try:
        selected_courses_count = SelectedCourse.query.filter_by(student_id=current_user.id).count()
    except:
        selected_courses_count = 0

    try:
        # 待审批请假数量
        pending_leaves_count = LeaveApplication.query.filter_by(
            student_id=current_user.id,
            status='pending'
        ).count()
    except:
        pending_leaves_count = 0

    try:
        # 活跃的教室借用数量
        active_bookings_count = ClassroomBooking.query.filter_by(
            student_id=current_user.id
        ).filter(
            ClassroomBooking.status.in_(['pending', 'approved'])
        ).count()
    except:
        active_bookings_count = 0

    try:
        # 近期考试数量（未来7天内）
        upcoming_exams_count = Exam.query.filter_by(
            class_id=current_user.class_id
        ).filter(
            Exam.exam_time >= datetime.now(),
            Exam.exam_time <= datetime.now() + timedelta(days=7)
        ).count()
    except:
        upcoming_exams_count = 0

    try:
        # 未读公告数量（最近7天）
        seven_days_ago = datetime.now() - timedelta(days=7)
        unread_announcements_count = Announcement.query.join(
            SelectedCourse, Announcement.course_id == SelectedCourse.course_id
        ).filter(
            SelectedCourse.student_id == current_user.id,
            Announcement.created_at >= seven_days_ago
        ).count()
    except:
        unread_announcements_count = 0

    return render_template('student/dashboard.html',
                           title='学生仪表板',
                           user=user_info,
                           selected_courses_count=selected_courses_count,
                           pending_leaves_count=pending_leaves_count,
                           active_bookings_count=active_bookings_count,
                           upcoming_exams_count=upcoming_exams_count,
                           now=datetime.now())


@student_bp.route('/schedule')
@login_required
def schedule():
    """学生课表查询页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取当前周次（默认显示当前周）
    week_offset = request.args.get('week', 0, type=int)
    current_date = date.today() + timedelta(weeks=week_offset)

    # 计算当前周的周一
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # 查询学生课表
    schedules = Schedule.query.filter_by(class_id=current_user.class_id).all()

    # 按星期几分组
    schedule_by_day = {}
    for schedule in schedules:
        day_schedules = schedule_by_day.get(schedule.day_of_week, [])
        day_schedules.append(schedule)
        schedule_by_day[schedule.day_of_week] = day_schedules

    return render_template('student/schedule.html',
                           schedules=schedule_by_day,
                           current_week=week_offset,
                           start_of_week=start_of_week,
                           end_of_week=end_of_week)


@student_bp.route('/schedule/export-pdf')
@login_required
def export_schedule_pdf():
    """导出课表为PDF"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 这里模拟PDF导出功能
    week_offset = request.args.get('week', 0, type=int)

    try:
        # 创建简单的PDF内容（模拟）
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # 添加PDF内容
        p.drawString(100, 750, f"学生课表 - {current_user.real_name}")
        p.drawString(100, 730, f"班级: {current_user.class_info.class_name if current_user.class_info else '未知'}")
        p.drawString(100, 710, f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # 查询课表数据
        schedules = Schedule.query.filter_by(class_id=current_user.class_id).all()

        y_position = 680
        for schedule in schedules:
            if y_position < 100:
                p.showPage()
                y_position = 750

            course_info = f"{schedule.course.course_name} - {schedule.location} - {schedule.start_time.strftime('%H:%M')}"
            p.drawString(100, y_position, course_info)
            y_position -= 20

        p.save()
        buffer.seek(0)

        return send_file(buffer,
                         as_attachment=True,
                         download_name=f"课表_{current_user.real_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                         mimetype='application/pdf')
    except ImportError:
        # 如果 reportlab 没有安装，返回错误信息
        flash('PDF导出功能暂不可用，请安装 reportlab 库', 'warning')
        return redirect(url_for('student.schedule'))


@student_bp.route('/exam-schedule')
@login_required
def exam_schedule():
    """考试安排页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取筛选条件
    course_name = request.args.get('course_name', '')
    exam_date = request.args.get('exam_date', '')

    # 构建查询
    query = Exam.query.filter_by(class_id=current_user.class_id)

    if course_name:
        query = query.join(Exam.course).filter(
            db.or_(
                Course.course_name.contains(course_name),
                Course.course_code.contains(course_name)
            )
        )

    if exam_date:
        try:
            exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Exam.exam_time) == exam_date_obj)
        except ValueError:
            pass

    exams = query.order_by(Exam.exam_time).all()

    return render_template('student/exam_schedule.html',
                           exams=exams,
                           course_name=course_name,
                           exam_date=exam_date)


@student_bp.route('/exam-schedule/calendar-sync/<int:exam_id>')
@login_required
def calendar_sync(exam_id):
    """日历同步功能"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    exam = Exam.query.get_or_404(exam_id)

    # 生成日历文件内容（iCalendar格式）
    ical_content = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:{exam.course.course_name} - {exam.exam_name}
DTSTART:{exam.exam_time.strftime('%Y%m%dT%H%M%S')}
DTEND:{(exam.exam_time + timedelta(minutes=exam.duration or 120)).strftime('%Y%m%dT%H%M%S')}
LOCATION:{exam.location}
DESCRIPTION:考试科目：{exam.course.course_name}\\n座位号：{exam.seat_number or '未分配'}
END:VEVENT
END:VCALENDAR"""

    from io import BytesIO
    buffer = BytesIO(ical_content.encode('utf-8'))

    return send_file(buffer,
                     as_attachment=True,
                     download_name=f"{exam.course.course_name}_考试.ics",
                     mimetype='text/calendar')


@student_bp.route('/leave/apply', methods=['GET', 'POST'])
@login_required
def leave_apply():
    """请假申请"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # 获取表单数据
        leave_type = request.form.get('leave_type')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        reason = request.form.get('reason')

        # 验证数据
        if not all([leave_type, start_time_str, end_time_str, reason]):
            flash('请填写所有必填字段', 'danger')
            return redirect(url_for('student.leave_apply'))

        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('时间格式错误', 'danger')
            return redirect(url_for('student.leave_apply'))

        if start_time >= end_time:
            flash('结束时间必须晚于开始时间', 'danger')
            return redirect(url_for('student.leave_apply'))

        # 处理文件上传
        attachment_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = secure_filename(f"{current_user.id}_{int(datetime.now().timestamp())}_{file.filename}")
                    file_path = os.path.join('uploads', 'leave_attachments', filename)

                    # 确保目录存在
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    attachment_path = filename

        # 创建请假申请
        leave_app = LeaveApplication(
            student_id=current_user.id,
            leave_type=leave_type,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            attachment_path=attachment_path
        )

        # 自动分配审批人（根据请假时长）
        duration_days = (end_time - start_time).days
        if duration_days <= 3:
            # 班主任审批
            class_info = Class.query.get(current_user.class_id)
            if class_info and class_info.counselor_id:
                leave_app.approver_id = class_info.counselor_id
        else:
            # 辅导员审批（这里简化处理，实际可能更复杂）
            class_info = Class.query.get(current_user.class_id)
            if class_info and class_info.counselor_id:
                leave_app.approver_id = class_info.counselor_id

        db.session.add(leave_app)
        db.session.commit()

        flash('请假申请提交成功，等待审批', 'success')
        return redirect(url_for('student.leave_records'))

    return render_template('student/leave_apply.html')


@student_bp.route('/leave/records')
@login_required
def leave_records():
    """请假记录"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    leaves = LeaveApplication.query.filter_by(student_id=current_user.id) \
        .order_by(LeaveApplication.created_at.desc()).all()

    return render_template('student/leave_records.html', leaves=leaves)


@student_bp.route('/classroom/booking', methods=['GET', 'POST'])
@login_required
def classroom_booking():
    """教室借用申请"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # 获取表单数据
        classroom_id = request.form.get('classroom_id')
        booking_date_str = request.form.get('booking_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        purpose = request.form.get('purpose')
        participants = request.form.get('participants', type=int)

        # 验证数据
        if not all([classroom_id, booking_date_str, start_time_str, end_time_str, purpose, participants]):
            flash('请填写所有必填字段', 'danger')
            return redirect(url_for('student.classroom_booking'))

        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            flash('日期或时间格式错误', 'danger')
            return redirect(url_for('student.classroom_booking'))

        if start_time >= end_time:
            flash('结束时间必须晚于开始时间', 'danger')
            return redirect(url_for('student.classroom_booking'))

        # 检查教室是否可用
        classroom = Classroom.query.get_or_404(classroom_id)

        # 检查时间冲突
        existing_booking = ClassroomBooking.query.filter_by(
            classroom_id=classroom_id,
            booking_date=booking_date
        ).filter(
            or_(
                and_(ClassroomBooking.start_time <= start_time, ClassroomBooking.end_time > start_time),
                and_(ClassroomBooking.start_time < end_time, ClassroomBooking.end_time >= end_time),
                and_(ClassroomBooking.start_time >= start_time, ClassroomBooking.end_time <= end_time)
            )
        ).first()

        if existing_booking:
            flash('该时间段教室已被占用，请选择其他时间', 'warning')
            return redirect(url_for('student.classroom_booking'))

        # 创建借用申请
        booking = ClassroomBooking(
            student_id=current_user.id,
            classroom_id=classroom_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            participants=participants
        )

        db.session.add(booking)
        db.session.commit()

        flash('教室借用申请提交成功，等待审批', 'success')
        return redirect(url_for('student.booking_records'))

    # 获取可用教室列表
    classrooms = Classroom.query.filter_by(status='available').all()

    return render_template('student/classroom_booking.html', classrooms=classrooms)


@student_bp.route('/classroom/booking-records')
@login_required
def booking_records():
    """教室借用记录"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    bookings = ClassroomBooking.query.filter_by(
        student_id=current_user.id
    ).order_by(ClassroomBooking.created_at.desc()).all()

    return render_template('student/booking_records.html', bookings=bookings)


@student_bp.route('/course-selection')
@login_required
def course_selection():
    """学生选课页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取可选课程（排除已选和冲突课程）
    available_courses = get_available_courses(current_user.id)

    # 获取已选课程 - 添加关联加载
    selected_courses = SelectedCourse.query.filter_by(
        student_id=current_user.id
    ).options(
        db.joinedload(SelectedCourse.course).joinedload(Course.teacher),
        db.joinedload(SelectedCourse.course).joinedload(Course.schedules)
    ).all()

    return render_template('student/course_selection.html',
                           available_courses=available_courses,
                           selected_courses=selected_courses)


@student_bp.route('/select-course/<int:course_id>', methods=['POST'])
@login_required
def select_course(course_id):
    """学生选课"""
    if not current_user.is_student():
        return jsonify({'success': False, 'message': '无权操作'})

    try:
        course = Course.query.get_or_404(course_id)
        print(f"调试: 选课请求 - 学生 {current_user.id} 尝试选择课程 {course_id} ({course.course_name})")

        # 检查是否已选该课程
        existing = SelectedCourse.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()

        if existing:
            print(f"调试: 选课失败 - 已选择该课程")
            return jsonify({'success': False, 'message': '已选择该课程'})

        # 检查选课冲突
        conflict = check_course_conflict(current_user.id, course_id)
        if conflict:
            print(f"调试: 选课失败 - 课程时间冲突")
            return jsonify({'success': False, 'message': '课程时间冲突'})

        # 检查学分限制
        if not check_credit_limit(current_user.id, course.credit):
            print(f"调试: 选课失败 - 超过学分限制")
            return jsonify({'success': False, 'message': '超过学分限制'})

        # 创建选课记录
        selected_course = SelectedCourse(
            student_id=current_user.id,
            course_id=course_id,
            selected_at=datetime.now()
        )

        db.session.add(selected_course)
        db.session.commit()

        print(f"调试: 选课成功 - 学生 {current_user.id} 成功选择课程 {course_id}")

        return jsonify({'success': True, 'message': '选课成功'})

    except Exception as e:
        db.session.rollback()
        print(f"调试: 选课异常 - {str(e)}")
        return jsonify({'success': False, 'message': f'选课失败: {str(e)}'})


@student_bp.route('/drop-course/<int:course_id>', methods=['POST'])
@login_required
def drop_course(course_id):
    """学生退课"""
    if not current_user.is_student():
        return jsonify({'success': False, 'message': '无权操作'})

    selected_course = SelectedCourse.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()

    if not selected_course:
        return jsonify({'success': False, 'message': '未找到选课记录'})

    db.session.delete(selected_course)
    db.session.commit()

    return jsonify({'success': True, 'message': '退课成功'})


@student_bp.route('/grades')
@login_required
def grades():
    """学生成绩查询页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取学生成绩
    try:
        grades_list = Grade.query.filter_by(student_id=current_user.id).all()
    except Exception as e:
        print(f"成绩查询失败: {e}")
        grades_list = []

    # 计算统计信息
    total_credits = sum(grade.course.credit for grade in grades_list if grade.course)
    total_gpa = sum(grade.grade_point or 0 for grade in grades_list)
    course_count = len(grades_list)
    average_gpa = total_gpa / course_count if course_count > 0 else 0

    return render_template('student/grades.html',
                           grades=grades_list,
                           total_credits=total_credits,
                           average_gpa=round(average_gpa, 2),
                           course_count=course_count)


@student_bp.route('/my-courses')
@login_required
def my_courses():
    """我的课程页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取已选课程
    try:
        selected_courses = SelectedCourse.query.filter_by(
            student_id=current_user.id
        ).all()
    except Exception as e:
        print(f"课程查询失败: {e}")
        selected_courses = []

    return render_template('student/my_courses.html',
                           selected_courses=selected_courses)


def get_available_courses(student_id):
    """获取学生可选课程列表"""
    try:
        # 获取已选课程ID
        selected_course_ids = [sc.course_id for sc in
                               SelectedCourse.query.filter_by(student_id=student_id).all()]

        print(f"调试: 学生 {student_id} 已选课程ID: {selected_course_ids}")

        # 获取学生信息
        student = User.query.get(student_id)
        if not student:
            return []

        print(f"调试: 学生班级ID: {student.class_id}")

        # 修改查询：加载教师和课表信息
        available_courses = Course.query.filter(
            Course.id.notin_(selected_course_ids) if selected_course_ids else True
        ).options(
            db.joinedload(Course.teacher),
            db.joinedload(Course.schedules)
        ).all()

        print(f"调试: 找到 {len(available_courses)} 门可选课程")
        for course in available_courses:
            print(f"调试: 可选课程 - {course.course_name} (ID: {course.id}, 教师: {course.teacher.real_name if course.teacher else '无'})")

        return available_courses

    except Exception as e:
        print(f"获取可选课程失败: {e}")
        return []

def check_course_conflict(student_id, course_id):
    """检查课程时间冲突"""
    # 获取新课程的安排
    new_course_schedules = Schedule.query.filter_by(course_id=course_id).all()

    # 获取已选课程的安排
    selected_courses = SelectedCourse.query.filter_by(student_id=student_id).all()
    selected_course_ids = [sc.course_id for sc in selected_courses]

    existing_schedules = Schedule.query.filter(
        Schedule.course_id.in_(selected_course_ids)
    ).all()

    # 检查时间冲突
    for new_schedule in new_course_schedules:
        for existing_schedule in existing_schedules:
            if (new_schedule.day_of_week == existing_schedule.day_of_week and
                    time_overlap(new_schedule.start_time, new_schedule.end_time,
                                 existing_schedule.start_time, existing_schedule.end_time)):
                return True
    return False


def check_credit_limit(student_id, new_credit):
    """检查学分限制"""
    selected_courses = SelectedCourse.query.filter_by(student_id=student_id).all()
    total_credits = sum(course.course.credit for course in selected_courses)

    return (total_credits + new_credit) <= 30  # 假设学分上限为30


def time_overlap(start1, end1, start2, end2):
    """检查时间是否重叠"""
    return max(start1, start2) < min(end1, end2)


def allowed_file(filename):
    """检查文件类型是否允许"""
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@student_bp.route('/debug/courses')
@login_required
def debug_courses():
    """调试选课数据"""
    if not current_user.is_student():
        return jsonify({'error': '无权访问'})

    # 获取实际选课数据
    selected_courses = SelectedCourse.query.filter_by(
        student_id=current_user.id
    ).all()

    # 获取可选课程数据
    available_courses = get_available_courses(current_user.id)

    debug_info = {
        'student_id': current_user.id,
        'student_name': current_user.real_name,
        'class_id': current_user.class_id,
        'selected_courses_count': len(selected_courses),
        'selected_courses': [
            {
                'course_id': sc.course_id,
                'course_name': sc.course.course_name if sc.course else '未知',
                'selected_at': sc.selected_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for sc in selected_courses
        ],
        'available_courses_count': len(available_courses),
        'available_courses': [
            {
                'course_id': course.id,
                'course_name': course.course_name,
                'course_code': course.course_code
            }
            for course in available_courses
        ],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return jsonify(debug_info)


@student_bp.route('/debug/select-course/<int:course_id>')
@login_required
def debug_select_course(course_id):
    """调试选课过程"""
    if not current_user.is_student():
        return jsonify({'error': '无权操作'})

    debug_info = {
        'step': '开始选课调试',
        'student_id': current_user.id,
        'course_id': course_id,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 1. 检查课程是否存在
    course = Course.query.get(course_id)
    if not course:
        debug_info['step'] = '课程不存在'
        return jsonify(debug_info)

    debug_info['course_info'] = {
        'course_name': course.course_name,
        'course_code': course.course_code,
        'class_id': course.class_id,
        'credit': course.credit
    }

    # 2. 检查是否已选
    existing = SelectedCourse.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()

    if existing:
        debug_info['step'] = '已选择该课程'
        return jsonify(debug_info)

    # 3. 检查选课冲突
    conflict = check_course_conflict(current_user.id, course_id)
    if conflict:
        debug_info['step'] = '课程时间冲突'
        return jsonify(debug_info)

    # 4. 检查学分限制
    if not check_credit_limit(current_user.id, course.credit):
        debug_info['step'] = '超过学分限制'
        return jsonify(debug_info)

    # 5. 尝试选课
    try:
        selected_course = SelectedCourse(
            student_id=current_user.id,
            course_id=course_id,
            selected_at=datetime.now()
        )

        db.session.add(selected_course)
        db.session.commit()

        debug_info['step'] = '选课成功'
        return jsonify(debug_info)

    except Exception as e:
        db.session.rollback()
        debug_info['step'] = '选课异常'
        debug_info['error'] = str(e)
        return jsonify(debug_info)


@student_bp.route('/course-announcements')
@login_required
def course_announcements():
    """学生查看课程公告页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取筛选条件
    course_id = request.args.get('course_id', type=int)
    show_all = request.args.get('show_all', 'false') == 'true'

    # 获取学生已选的课程
    selected_courses = SelectedCourse.query.filter_by(
        student_id=current_user.id
    ).options(
        db.joinedload(SelectedCourse.course)
    ).all()

    # 获取公告查询
    from models import Announcement  # 确保导入Announcement模型

    query = Announcement.query.join(
        Course, Announcement.course_id == Course.id
    ).join(
        SelectedCourse, Course.id == SelectedCourse.course_id
    ).filter(
        SelectedCourse.student_id == current_user.id
    )

    # 按课程筛选
    if course_id:
        query = query.filter(Announcement.course_id == course_id)

    # 如果不显示全部，只显示最近30天的公告
    if not show_all:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        query = query.filter(Announcement.created_at >= thirty_days_ago)

    announcements = query.order_by(Announcement.created_at.desc()).all()

    return render_template('student/course_announcements.html',
                           announcements=announcements,
                           selected_courses=selected_courses,
                           course_id=course_id,
                           show_all=show_all)


@student_bp.route('/announcement/<int:announcement_id>')
@login_required
def announcement_detail(announcement_id):
    """公告详情页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    announcement = Announcement.query.get_or_404(announcement_id)

    # 检查学生是否有权限查看该公告（是否选了这门课）
    has_access = SelectedCourse.query.filter_by(
        student_id=current_user.id,
        course_id=announcement.course_id
    ).first() is not None

    if not has_access:
        flash('无权查看此公告', 'danger')
        return redirect(url_for('student.course_announcements'))

    return render_template('student/announcement_detail.html',
                           announcement=announcement)
