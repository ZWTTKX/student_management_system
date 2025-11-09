# routes/teacher.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta,date
import os
from models import db, Course, Announcement, CourseMaterial, User, Class,Grade,SelectedCourse

from werkzeug.utils import secure_filename

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


# 添加 allowed_file 函数
def allowed_file(filename):
    """检查文件类型是否允许上传"""
    allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 在 teacher.py 中更新 dashboard 路由

@teacher_bp.route('/dashboard')
@login_required
def dashboard():
    """教师仪表板"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    user_info = {
        'name': current_user.real_name,
        'role': current_user.role,
        'username': current_user.username
    }

    # 获取教师统计数据
    try:
        # 负责课程数量
        courses_count = Course.query.filter_by(teacher_id=current_user.id).count()

        # 发布公告数量
        announcements_count = Announcement.query.filter_by(teacher_id=current_user.id).count()

        # 课程资料数量
        materials_count = CourseMaterial.query.filter_by(teacher_id=current_user.id).count()

        # 最近发布的公告（用于最近活动）- 只获取当前用户的公告
        recent_announcements = Announcement.query.filter_by(
            teacher_id=current_user.id  # 确保只获取当前用户的公告
        ).order_by(Announcement.created_at.desc()).limit(5).all()

        # 最近上传的资料
        recent_materials = CourseMaterial.query.filter_by(
            teacher_id=current_user.id
        ).order_by(CourseMaterial.created_at.desc()).limit(5).all()

    except Exception as e:
        print(f"获取教师统计数据失败: {e}")
        courses_count = 0
        announcements_count = 0
        materials_count = 0
        recent_announcements = []
        recent_materials = []

    # 合并最近活动
    recent_activities = []

    # 添加公告活动 - 确保URL正确
    for announcement in recent_announcements:
        recent_activities.append({
            'type': 'announcement',
            'icon': 'fa-bullhorn',
            'color': 'success',
            'title': f'发布了 "{announcement.title}"',
            'course_name': announcement.course.course_name if announcement.course else '未知课程',
            'time': announcement.created_at,
            'url': url_for('teacher.announcement_detail', announcement_id=announcement.id)  # 确认这里正确
        })

    # 添加资料活动
    for material in recent_materials:
        recent_activities.append({
            'type': 'material',
            'icon': 'fa-file-upload',
            'color': 'primary',
            'title': f'上传了 "{material.file_name}"',
            'course_name': material.course.course_name if material.course else '未知课程',
            'time': material.created_at,
            'url': url_for('teacher.material_manage', course_id=material.course_id)
        })

    # 按时间排序
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    # 只取最近5个活动
    recent_activities = recent_activities[:5]

    return render_template('teacher/dashboard.html',
                           title='教师仪表板',
                           user=user_info,
                           role='teacher',
                           now=datetime.now(),
                           courses_count=courses_count,
                           announcements_count=announcements_count,
                           materials_count=materials_count,
                           recent_activities=recent_activities)


@teacher_bp.route('/courses')
@login_required
def course_manage():
    """课程管理页面"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取教师所教的课程
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

    return render_template('teacher/course_manage.html', courses=courses)


@teacher_bp.route('/announcement/<int:course_id>', methods=['GET', 'POST'])
@login_required
def announcement_edit(course_id):
    """发布公告"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    course = Course.query.get_or_404(course_id)

    # 检查教师是否有权管理该课程
    if course.teacher_id != current_user.id:
        flash('无权管理此课程', 'danger')
        return redirect(url_for('teacher.course_manage'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_pinned = bool(request.form.get('is_pinned'))
        pin_duration = request.form.get('pin_duration', 3, type=int)

        if not all([title, content]):
            flash('请填写标题和内容', 'danger')
            return redirect(url_for('teacher.announcement_edit', course_id=course_id))

        # 创建公告
        announcement = Announcement(
            course_id=course_id,
            teacher_id=current_user.id,
            title=title,
            content=content,
            is_pinned=is_pinned,
            pin_duration=pin_duration
        )

        db.session.add(announcement)
        db.session.commit()

        # TODO: 发送通知给课程所有学生

        flash('公告发布成功', 'success')
        return redirect(url_for('teacher.course_manage'))

    return render_template('teacher/announcement_edit.html', course=course)


@teacher_bp.route('/materials/<int:course_id>')
@login_required
def material_manage(course_id):
    """资料管理页面"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    course = Course.query.get_or_404(course_id)

    # 检查教师是否有权管理该课程
    if course.teacher_id != current_user.id:
        flash('无权管理此课程', 'danger')
        return redirect(url_for('teacher.course_manage'))

    materials = CourseMaterial.query.filter_by(course_id=course_id).all()

    return render_template('teacher/material_manage.html', course=course, materials=materials)


@teacher_bp.route('/materials/upload/<int:course_id>', methods=['POST'])
@login_required
def material_upload(course_id):
    """上传课程资料"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    course = Course.query.get_or_404(course_id)

    # 检查教师是否有权管理该课程
    if course.teacher_id != current_user.id:
        flash('无权管理此课程', 'danger')
        return redirect(url_for('teacher.course_manage'))

    if 'file' not in request.files:
        flash('请选择文件', 'danger')
        return redirect(url_for('teacher.material_manage', course_id=course_id))

    file = request.files['file']
    if file.filename == '':
        flash('请选择文件', 'danger')
        return redirect(url_for('teacher.material_manage', course_id=course_id))

    if file and allowed_file(file.filename):
        # 生成安全的文件名
        filename = secure_filename(f"{course_id}_{int(datetime.now().timestamp())}_{file.filename}")
        file_path = os.path.join('uploads', 'course_materials', filename)

        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)

        # 获取文件信息
        file_size = os.path.getsize(file_path)
        file_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

        # 创建资料记录
        material = CourseMaterial(
            course_id=course_id,
            teacher_id=current_user.id,
            file_name=file.filename,
            file_path=filename,
            file_size=file_size,
            file_type=file_type,
            category=request.form.get('category', '课件'),
            description=request.form.get('description', '')
        )

        db.session.add(material)
        db.session.commit()

        flash('资料上传成功', 'success')
    else:
        flash('文件类型不支持', 'danger')

    return redirect(url_for('teacher.material_manage', course_id=course_id))


@teacher_bp.route('/materials/delete/<int:material_id>')
@login_required
def material_delete(material_id):
    """删除课程资料"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    material = CourseMaterial.query.get_or_404(material_id)

    # 检查教师是否有权管理该资料
    if material.teacher_id != current_user.id:
        flash('无权删除此资料', 'danger')
        return redirect(url_for('teacher.material_manage', course_id=material.course_id))

    # 删除文件
    file_path = os.path.join('uploads', 'course_materials', material.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(material)
    db.session.commit()

    flash('资料删除成功', 'success')
    return redirect(url_for('teacher.material_manage', course_id=material.course_id))


@teacher_bp.route('/materials/download/<int:material_id>')
@login_required
def material_download(material_id):
    """下载课程资料"""
    material = CourseMaterial.query.get_or_404(material_id)

    # 更新下载次数
    material.download_count += 1
    db.session.commit()

    file_path = os.path.join('uploads', 'course_materials', material.file_path)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=material.file_name
    )


# 在 teacher.py 中添加以下成绩管理功能

@teacher_bp.route('/grades')
@login_required
def grade_manage():
    """成绩管理主页面"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取教师所教的课程
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

    # 为每个课程添加统计信息
    for course in courses:
        # 获取选课学生数量
        course.enrollment_count = SelectedCourse.query.filter_by(course_id=course.id).count()

        # 检查是否有保存的成绩
        grades = Grade.query.filter_by(course_id=course.id).all()
        course.grades_saved = len(grades) > 0

    return render_template('teacher/grade_manage.html', courses=courses)


@teacher_bp.route('/grades/<int:course_id>')
@login_required
def course_grades(course_id):
    """课程成绩管理页面"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    course = Course.query.get_or_404(course_id)

    # 检查教师是否有权管理该课程
    if course.teacher_id != current_user.id:
        flash('无权管理此课程', 'danger')
        return redirect(url_for('teacher.grade_manage'))

    # 获取已选该课程的学生
    selected_students = SelectedCourse.query.filter_by(course_id=course_id).all()

    # 获取已有成绩
    existing_grades = Grade.query.filter_by(course_id=course_id).all()
    grade_dict = {grade.student_id: grade for grade in existing_grades}

    return render_template('teacher/course_grades.html',
                           course=course,
                           students=selected_students,
                           grade_dict=grade_dict)


@teacher_bp.route('/grades/update/<int:course_id>', methods=['POST'])
@login_required
def update_grades(course_id):
    """更新学生成绩"""
    if not current_user.is_teacher():
        return jsonify({'success': False, 'message': '无权操作'})

    course = Course.query.get_or_404(course_id)

    # 检查教师是否有权管理该课程
    if course.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '无权管理此课程'})

    try:
        data = request.get_json()
        student_id = data.get('student_id')
        score = data.get('score')
        exam_type = data.get('exam_type', '期末')
        exam_date = data.get('exam_date')
        comments = data.get('comments', '')

        if not student_id or score is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})

        # 验证学生是否选了这门课
        selected_course = SelectedCourse.query.filter_by(
            student_id=student_id, course_id=course_id
        ).first()

        if not selected_course:
            return jsonify({'success': False, 'message': '学生未选此课程'})

        # 查找或创建成绩记录
        grade = Grade.query.filter_by(
            student_id=student_id, course_id=course_id
        ).first()

        if not grade:
            grade = Grade(
                student_id=student_id,
                course_id=course_id,
                teacher_id=current_user.id,
                academic_year='2024-2025',  # 可根据需要动态获取
                semester='秋季'
            )

        # 更新成绩信息
        grade.score = float(score) if score else None
        if grade.score is not None:
            grade.grade_point = grade.calculate_grade_point()
            grade.grade_level = grade.calculate_grade_level()

        grade.exam_type = exam_type
        grade.comments = comments

        if exam_date:
            grade.exam_date = datetime.strptime(exam_date, '%Y-%m-%d').date()

        if not grade.id:
            db.session.add(grade)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '成绩更新成功',
            'grade_point': grade.grade_point,
            'grade_level': grade.grade_level
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'成绩更新失败: {str(e)}'})


@teacher_bp.route('/grades/batch-update/<int:course_id>', methods=['POST'])
@login_required
def batch_update_grades(course_id):
    """批量更新成绩"""
    if not current_user.is_teacher():
        return jsonify({'success': False, 'message': '无权操作'})

    course = Course.query.get_or_404(course_id)

    if course.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '无权管理此课程'})

    try:
        data = request.get_json()
        grades_data = data.get('grades', [])
        exam_type = data.get('exam_type', '期末')
        exam_date = data.get('exam_date')

        success_count = 0
        error_count = 0

        for grade_data in grades_data:
            student_id = grade_data.get('student_id')
            score = grade_data.get('score')

            if student_id and score is not None:
                # 查找或创建成绩记录
                grade = Grade.query.filter_by(
                    student_id=student_id, course_id=course_id
                ).first()

                if not grade:
                    grade = Grade(
                        student_id=student_id,
                        course_id=course_id,
                        teacher_id=current_user.id,
                        academic_year='2024-2025',
                        semester='秋季'
                    )

                grade.score = float(score)
                grade.grade_point = grade.calculate_grade_point()
                grade.grade_level = grade.calculate_grade_level()
                grade.exam_type = exam_type

                if exam_date:
                    grade.exam_date = datetime.strptime(exam_date, '%Y-%m-%d').date()

                if not grade.id:
                    db.session.add(grade)

                success_count += 1
            else:
                error_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'批量更新完成：成功 {success_count} 条，失败 {error_count} 条'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'批量更新失败: {str(e)}'})


@teacher_bp.route('/grades/export/<int:course_id>')
@login_required
def export_grades(course_id):
    """导出成绩为Excel"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    course = Course.query.get_or_404(course_id)

    if course.teacher_id != current_user.id:
        flash('无权管理此课程', 'danger')
        return redirect(url_for('teacher.grade_manage'))

    try:
        import pandas as pd
        from io import BytesIO

        # 获取课程成绩数据
        grades = Grade.query.filter_by(course_id=course_id).all()

        # 创建DataFrame
        data = []
        for grade in grades:
            data.append({
                '学号': grade.student.username,
                '姓名': grade.student.real_name,
                '班级': grade.student.class_info.class_name if grade.student.class_info else '',
                '成绩': grade.score,
                '绩点': grade.grade_point,
                '等级': grade.grade_level,
                '考试类型': grade.exam_type,
                '考试日期': grade.exam_date.strftime('%Y-%m-%d') if grade.exam_date else '',
                '评语': grade.comments or ''
            })

        df = pd.DataFrame(data)

        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'{course.course_name}成绩', index=False)

            # 调整列宽
            worksheet = writer.sheets[f'{course.course_name}成绩']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f'{course.course_name}_成绩表_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except ImportError:
        flash('请安装 pandas 和 openpyxl 库以支持Excel导出', 'warning')
        return redirect(url_for('teacher.course_grades', course_id=course_id))
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'danger')
        return redirect(url_for('teacher.course_grades', course_id=course_id))


@teacher_bp.route('/grades/import/<int:course_id>', methods=['POST'])
@login_required
def import_grades(course_id):
    """从Excel导入成绩"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    course = Course.query.get_or_404(course_id)

    if course.teacher_id != current_user.id:
        flash('无权管理此课程', 'danger')
        return redirect(url_for('teacher.grade_manage'))

    if 'file' not in request.files:
        flash('请选择文件', 'danger')
        return redirect(url_for('teacher.course_grades', course_id=course_id))

    file = request.files['file']
    if file.filename == '':
        flash('请选择文件', 'danger')
        return redirect(url_for('teacher.course_grades', course_id=course_id))

    try:
        import pandas as pd

        # 读取Excel文件
        df = pd.read_excel(file)

        # 验证必要的列
        required_columns = ['学号', '成绩']
        if not all(col in df.columns for col in required_columns):
            flash('Excel文件必须包含"学号"和"成绩"列', 'danger')
            return redirect(url_for('teacher.course_grades', course_id=course_id))

        success_count = 0
        error_count = 0

        for _, row in df.iterrows():
            try:
                student_username = str(row['学号']).strip()
                score = row['成绩']

                if pd.isna(score) or pd.isna(student_username):
                    error_count += 1
                    continue

                # 查找学生
                student = User.query.filter_by(username=student_username).first()
                if not student:
                    error_count += 1
                    continue

                # 检查学生是否选了这门课
                selected_course = SelectedCourse.query.filter_by(
                    student_id=student.id, course_id=course_id
                ).first()

                if not selected_course:
                    error_count += 1
                    continue

                # 更新或创建成绩记录
                grade = Grade.query.filter_by(
                    student_id=student.id, course_id=course_id
                ).first()

                if not grade:
                    grade = Grade(
                        student_id=student.id,
                        course_id=course_id,
                        teacher_id=current_user.id,
                        academic_year='2024-2025',
                        semester='秋季'
                    )

                grade.score = float(score)
                grade.grade_point = grade.calculate_grade_point()
                grade.grade_level = grade.calculate_grade_level()
                grade.exam_type = '期末'  # 默认值

                if not grade.id:
                    db.session.add(grade)

                success_count += 1

            except Exception as e:
                error_count += 1
                continue

        db.session.commit()
        flash(f'导入完成：成功 {success_count} 条，失败 {error_count} 条', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'导入失败: {str(e)}', 'danger')

    return redirect(url_for('teacher.course_grades', course_id=course_id))


@teacher_bp.route('/grades/statistics/<int:course_id>')
@login_required
def grade_statistics(course_id):
    """成绩统计"""
    if not current_user.is_teacher():
        return jsonify({'error': '无权访问'})

    course = Course.query.get_or_404(course_id)

    if course.teacher_id != current_user.id:
        return jsonify({'error': '无权管理此课程'})

    # 获取成绩数据
    grades = Grade.query.filter_by(course_id=course_id).all()

    if not grades:
        return jsonify({'error': '暂无成绩数据'})

    scores = [grade.score for grade in grades if grade.score is not None]

    statistics = {
        'total_students': len(grades),
        'average_score': round(sum(scores) / len(scores), 2),
        'max_score': max(scores),
        'min_score': min(scores),
        'pass_count': len([s for s in scores if s >= 60]),
        'fail_count': len([s for s in scores if s < 60]),
        'score_distribution': {
            '90-100': len([s for s in scores if s >= 90]),
            '80-89': len([s for s in scores if 80 <= s < 90]),
            '70-79': len([s for s in scores if 70 <= s < 80]),
            '60-69': len([s for s in scores if 60 <= s < 70]),
            '0-59': len([s for s in scores if s < 60])
        }
    }

    return jsonify(statistics)


# 在 teacher.py 中添加一个新的路由用于选择课程发布公告

@teacher_bp.route('/announcement/select-course')
@login_required
def announcement_select_course():
    """选择课程发布公告"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    # 获取教师所教的课程
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

    return render_template('teacher/announcement_select_course.html', courses=courses)


# 在 teacher.py 路由中添加保存成绩的逻辑
@teacher_bp.route('/course/<int:course_id>/grades/save', methods=['POST'])
def save_grades(course_id):
    course = Course.query.get_or_404(course_id)

    # 检查当前用户是否有权限管理该课程
    if course.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '无权限操作此课程'})

    try:
        # 获取提交的成绩数据
        grades_data = request.get_json()

        # 保存成绩的逻辑（这里需要根据您的具体实现来写）
        for grade_info in grades_data:
            student_id = grade_info.get('student_id')
            score = grade_info.get('score')

            # 查找或创建成绩记录
            grade = Grade.query.filter_by(
                student_id=student_id,
                course_id=course_id
            ).first()

            if grade:
                # 更新现有成绩
                grade.score = score
                grade.grade_point = grade.calculate_grade_point()
                grade.grade_level = grade.calculate_grade_level()
                grade.updated_at = datetime.utcnow()
            else:
                # 创建新成绩记录
                grade = Grade(
                    student_id=student_id,
                    course_id=course_id,
                    teacher_id=current_user.id,
                    score=score,
                    grade_point=Grade.calculate_grade_point(score),
                    grade_level=Grade.calculate_grade_level(score),
                    exam_type='期末',
                    exam_date=date.today(),
                    academic_year='2024-2025',  # 根据实际情况设置
                    semester='春季'  # 根据实际情况设置
                )
                db.session.add(grade)

        # 标记课程成绩已保存
        course.grades_saved = True
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '成绩保存成功'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'保存失败: {str(e)}'
        })


@teacher_bp.route('/course/<int:course_id>/grades/reset', methods=['POST'])
def reset_grades_status(course_id):
    course = Course.query.get_or_404(course_id)

    # 检查权限
    if course.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': '无权限操作此课程'})

    try:
        # 重置成绩保存状态
        course.grades_saved = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '状态已重置，可以重新编辑成绩'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'重置失败: {str(e)}'
        })


@teacher_bp.route('/course/<int:course_id>/grades/submit', methods=['POST'])
def submit_grades(course_id):
    """提交成绩并发布公告"""
    try:
        course = Course.query.get_or_404(course_id)

        # 检查当前用户是否有权限管理该课程
        if course.teacher_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限操作此课程'})

        # 检查成绩是否已保存
        grades = Grade.query.filter_by(course_id=course_id).all()
        if not grades:
            return jsonify({'success': False, 'message': '请先保存成绩再提交'})

        # 创建成绩公告 - 使用正确的字段名
        announcement = Announcement(
            title=f"{course.course_name} ({course.course_code}) 成绩发布",
            content=generate_grade_announcement_content(course, grades),
            teacher_id=current_user.id,  # 使用 teacher_id 而不是 author_id
            course_id=course_id,
            is_pinned=True,  # 成绩公告置顶
            pin_duration=7  # 置顶7天
        )

        db.session.add(announcement)

        # 标记课程成绩为已提交状态
        course.grades_submitted = True
        course.grades_submitted_at = datetime.utcnow()

        db.session.commit()

        return jsonify({'success': True, 'message': '成绩提交成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'提交失败: {str(e)}'})


def generate_grade_announcement_content(course, grades):
    """生成成绩公告内容 - 创建时生成完整静态HTML"""
    # 统计成绩信息
    total_students = len(grades)
    scores = [g.score for g in grades if g.score is not None]

    if scores:
        passed_students = len([s for s in scores if s >= 60])
        failed_students = total_students - passed_students
        average_score = sum(scores) / len(scores)
        pass_rate = (passed_students / total_students * 100) if total_students > 0 else 0
    else:
        passed_students = 0
        failed_students = 0
        average_score = 0
        pass_rate = 0

    # 生成完整的静态HTML内容
    content = f"""
    <div class="announcement-content">
        <p>各位同学：</p>
        <p>《{course.course_name}》课程成绩已评定完成，现将成绩公布如下：</p>

        <div class="alert alert-info">
            <strong>课程信息：</strong><br>
            课程名称：{course.course_name}<br>
            课程代码：{course.course_code}<br>
            授课教师：{course.teacher.real_name}<br>
            公布时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}
        </div>

        <div class="alert alert-success">
            <strong>成绩统计：</strong><br>
            总人数：{total_students}人<br>
            平均分：{average_score:.1f}分<br>
            及格人数：{passed_students}人<br>
            不及格人数：{failed_students}人<br>
            及格率：{pass_rate:.1f}%
        </div>

        <p>请各位同学及时查看自己的成绩，如有疑问请在3个工作日内联系授课教师。</p>
        <p><strong>注意：</strong>最终成绩以教务系统为准。</p>

        <div class="text-end">
            <p>{course.teacher.real_name}</p>
            <p>{datetime.now().strftime('%Y年%m月%d日')}</p>
        </div>
    </div>
    """
    return content


@teacher_bp.route('/announcement/<int:announcement_id>')
@login_required
def announcement_detail(announcement_id):
    """公告详情页面"""
    if not current_user.is_teacher():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    try:
        announcement = Announcement.query.get_or_404(announcement_id)

        # 检查权限：只有发布公告的教师可以查看
        # 重要：这里只检查公告的发布者，不检查课程权限
        if announcement.teacher_id != current_user.id:
            flash('无权限查看此公告', 'error')
            return redirect(url_for('teacher.dashboard'))  # 重定向到仪表盘，不是课程管理

        return render_template('teacher/announcement_detail.html',
                               announcement=announcement)

    except Exception as e:
        print(f"公告详情页面错误: {e}")
        flash('加载公告详情失败', 'error')
        return redirect(url_for('teacher.dashboard'))


@teacher_bp.route('/announcement/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    """删除公告"""
    try:
        announcement = Announcement.query.get_or_404(announcement_id)

        # 检查权限
        if announcement.teacher_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限删除此公告'})

        db.session.delete(announcement)
        db.session.commit()

        return jsonify({'success': True, 'message': '公告删除成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})