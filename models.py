# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time

# 创建独立的 db 实例
db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # student, teacher, counselor
    real_name = db.Column(db.String(64), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.role == 'student'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_counselor(self):
        return self.role == 'counselor'

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'


class Class(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(64), nullable=False, unique=True)
    counselor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    students = db.relationship('User', backref='class_info', foreign_keys='User.class_id')
    counselor = db.relationship('User', backref='counseled_classes', foreign_keys=[counselor_id])
    courses = db.relationship('Course', backref='class_info')


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(32), unique=True, nullable=False)
    course_name = db.Column(db.String(128), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    credit = db.Column(db.Integer, default=2)
    grades_saved = db.Column(db.Boolean, default=False)  # 成绩是否已保存
    grades_submitted = db.Column(db.Boolean, default=False)  # 新增：成绩是否已提交
    grades_submitted_at = db.Column(db.DateTime)  # 新增：成绩提交时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    teacher = db.relationship('User', backref='courses_teaching', foreign_keys=[teacher_id])

    def __repr__(self):
        return f'<Course {self.course_code} - {self.course_name}>'

class Schedule(db.Model):
    """课表模型"""
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 1-7 表示周一到周日
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(128))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系定义
    course = db.relationship('Course', backref='schedules')
    teacher = db.relationship('User', backref='teaching_schedules', foreign_keys=[teacher_id])

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course.course_name if self.course else '',
            'course_code': self.course.course_code if self.course else '',
            'teacher_name': self.teacher.real_name if self.teacher else '',
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'location': self.location
        }


class Exam(db.Model):
    """考试安排模型"""
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    exam_name = db.Column(db.String(128), nullable=False)
    exam_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(128), nullable=False)
    seat_number = db.Column(db.String(32))
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系定义
    course = db.relationship('Course', backref='exams')

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course.course_name if self.course else '',
            'exam_name': self.exam_name,
            'exam_time': self.exam_time.strftime('%Y-%m-%d %H:%M'),
            'location': self.location,
            'seat_number': self.seat_number,
            'duration': self.duration
        }


class LeaveApplication(db.Model):
    """请假申请模型"""
    __tablename__ = 'leave_applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(256))
    status = db.Column(db.String(20), default='pending')
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reject_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    student = db.relationship('User', backref='leave_applications', foreign_keys=[student_id])
    approver = db.relationship('User', backref='approved_leaves', foreign_keys=[approver_id])

    def get_duration_days(self):
        """计算请假天数"""
        delta = self.end_time - self.start_time
        return delta.days + 1

    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.student.real_name if self.student else '',
            'leave_type': self.leave_type,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M'),
            'duration_days': self.get_duration_days(),
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class Classroom(db.Model):
    """教室模型"""
    __tablename__ = 'classrooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(32), unique=True, nullable=False)
    building = db.Column(db.String(64), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    equipment = db.Column(db.String(256))
    status = db.Column(db.String(20), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Classroom {self.room_number} - {self.building}>'


class ClassroomBooking(db.Model):
    """教室借用申请模型"""
    __tablename__ = 'classroom_bookings'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    participants = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reject_reason = db.Column(db.Text)
    qr_code_path = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    student = db.relationship('User', backref='classroom_bookings', foreign_keys=[student_id])
    classroom = db.relationship('Classroom', backref='bookings')
    admin = db.relationship('User', backref='approved_bookings', foreign_keys=[admin_id])

    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.student.real_name if self.student else '',
            'classroom_number': self.classroom.room_number if self.classroom else '',
            'building': self.classroom.building if self.classroom else '',
            'booking_date': self.booking_date.strftime('%Y-%m-%d'),
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'purpose': self.purpose,
            'participants': self.participants,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class Announcement(db.Model):
    """课程公告模型"""
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    pin_duration = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    course = db.relationship('Course', backref='announcements')
    teacher = db.relationship('User', backref='announcements', foreign_keys=[teacher_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保内容不被意外修改
        self._original_content = self.content

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course.course_name if self.course else '',
            'teacher_name': self.teacher.real_name if self.teacher else '',
            'title': self.title,
            'content': self.content,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else ''
        }

    def update_content(self, new_content):
        """安全更新内容的方法"""
        self.content = new_content
        self.updated_at = datetime.utcnow()


class CourseMaterial(db.Model):
    """课程资料模型"""
    __tablename__ = 'course_materials'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_name = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    category = db.Column(db.String(20), default='课件')
    description = db.Column(db.Text)
    view_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    course = db.relationship('Course', backref='materials')
    teacher = db.relationship('User', backref='materials', foreign_keys=[teacher_id])

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course.course_name if self.course else '',
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'category': self.category,
            'description': self.description,
            'view_count': self.view_count,
            'download_count': self.download_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class SelectedCourse(db.Model):
    """学生选课模型"""
    __tablename__ = 'selected_courses'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    selected_at = db.Column(db.DateTime, default=datetime.utcnow)
    academic_year = db.Column(db.String(20))  # 学年，如 2024-2025
    semester = db.Column(db.String(10))  # 学期，如 秋季、春季

    # 修正关系定义
    student = db.relationship('User', backref='selected_courses', foreign_keys=[student_id])
    course = db.relationship('Course', backref='selected_courses', foreign_keys=[course_id])

    # 唯一约束：一个学生不能重复选同一门课程
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', name='unique_student_course'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.student.real_name if self.student else '',
            'course_name': self.course.course_name if self.course else '',
            'course_code': self.course.course_code if self.course else '',
            'teacher_name': self.course.teacher.real_name if self.course and self.course.teacher else '',
            'credit': self.course.credit if self.course else 0,
            'selected_at': self.selected_at.strftime('%Y-%m-%d %H:%M')
        }


# 在 models.py 末尾添加 Grade 模型
class Grade(db.Model):
    """学生成绩模型"""
    __tablename__ = 'grades'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Float)  # 百分制成绩
    grade_point = db.Column(db.Float)  # 绩点
    grade_level = db.Column(db.String(2))  # 等级：A, B, C, D, F
    exam_type = db.Column(db.String(20), default='期末')  # 考试类型
    exam_date = db.Column(db.Date)
    academic_year = db.Column(db.String(20))
    semester = db.Column(db.String(10))
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    student = db.relationship('User', backref='grades', foreign_keys=[student_id])
    course = db.relationship('Course', backref='grades')
    teacher = db.relationship('User', backref='given_grades', foreign_keys=[teacher_id])

    def calculate_grade_point(self):
        """根据百分制成绩计算绩点"""
        if self.score >= 90:
            return 4.0
        elif self.score >= 80:
            return 3.0
        elif self.score >= 70:
            return 2.0
        elif self.score >= 60:
            return 1.0
        else:
            return 0.0

    def calculate_grade_level(self):
        """根据百分制成绩计算等级"""
        if self.score >= 90:
            return 'A'
        elif self.score >= 80:
            return 'B'
        elif self.score >= 70:
            return 'C'
        elif self.score >= 60:
            return 'D'
        else:
            return 'F'

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course.course_name if self.course else '',
            'course_code': self.course.course_code if self.course else '',
            'teacher_name': self.teacher.real_name if self.teacher else '',
            'score': self.score,
            'grade_point': self.grade_point,
            'grade_level': self.grade_level,
            'exam_type': self.exam_type,
            'exam_date': self.exam_date.strftime('%Y-%m-%d') if self.exam_date else '',
            'credit': self.course.credit if self.course else 0,
            'comments': self.comments
        }


# 在 models.py 末尾添加以下新模型

class AcademicAlert(db.Model):
    """学业预警模型"""
    __tablename__ = 'academic_alerts'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    counselor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_level = db.Column(db.String(20), nullable=False)  # 一级/二级/三级
    failed_courses = db.Column(db.Text, nullable=False)  # 挂科科目（JSON格式存储）
    total_failed = db.Column(db.Integer, nullable=False)  # 总挂科数
    reason = db.Column(db.Text)  # 预警原因分析
    semester = db.Column(db.String(20), nullable=False)  # 学期
    status = db.Column(db.String(20), default='active')  # active/resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    student = db.relationship('User', backref='academic_alerts', foreign_keys=[student_id])
    counselor = db.relationship('User', backref='managed_alerts', foreign_keys=[counselor_id])

    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.student.real_name if self.student else '',
            'student_id': self.student.username if self.student else '',
            'class_name': self.student.class_info.class_name if self.student and self.student.class_info else '',
            'alert_level': self.alert_level,
            'total_failed': self.total_failed,
            'failed_courses': self.failed_courses,
            'reason': self.reason,
            'semester': self.semester,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

    def get_failed_courses_list(self):
        """获取挂科科目列表（解析JSON并处理Unicode）"""
        try:
            import json
            if self.failed_courses and self.failed_courses.startswith('['):
                courses = json.loads(self.failed_courses)
                # 确保返回的是列表
                if isinstance(courses, list):
                    return courses
                else:
                    return [courses]
            else:
                return [self.failed_courses] if self.failed_courses else []
        except Exception as e:
            print(f"解析挂科科目失败: {e}")
            return [self.failed_courses] if self.failed_courses else []


class CounselingRecord(db.Model):
    """辅导记录模型"""
    __tablename__ = 'counseling_records'

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('academic_alerts.id'), nullable=False)
    counselor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    counseling_time = db.Column(db.DateTime, nullable=False)
    content = db.Column(db.Text, nullable=False)  # 辅导内容
    plan = db.Column(db.Text)  # 后续计划
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    alert = db.relationship('AcademicAlert', backref='counseling_records')
    counselor = db.relationship('User', backref='counseling_records', foreign_keys=[counselor_id])

    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.alert.student.real_name if self.alert and self.alert.student else '',
            'counseling_time': self.counseling_time.strftime('%Y-%m-%d %H:%M'),
            'content': self.content,
            'plan': self.plan,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }