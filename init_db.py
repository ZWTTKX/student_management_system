# init_db.py
from app import create_app
from models import db, User, Class, Course, Schedule, Exam, LeaveApplication, Classroom, ClassroomBooking, Announcement, \
    CourseMaterial, AcademicAlert, CounselingRecord, SelectedCourse, Grade
from werkzeug.security import generate_password_hash
from datetime import datetime, date, time, timedelta
import os
import json


def init_database():
    app = create_app()

    with app.app_context():
        # 先检查数据库文件是否存在，如果存在则删除
        db_path = 'student_management.db'
        if os.path.exists(db_path):
            print(f"删除已存在的数据库文件: {db_path}")
            os.remove(db_path)

        # 删除所有表并重新创建
        print("创建数据库表...")
        db.drop_all()
        db.create_all()
        print("数据库表创建完成")

        print("开始创建测试数据...")

        # 创建班级
        print("创建班级...")
        class1 = Class(class_name="计算机科学与技术2023-1班")
        class2 = Class(class_name="软件工程2023-1班")
        db.session.add(class1)
        db.session.add(class2)
        db.session.commit()
        print("班级创建完成")

        # 创建用户
        print("创建用户...")
        student1 = User(
            username="stu001",
            email="stu001@university.edu",
            real_name="张三",
            role="student",
            class_id=class1.id
        )
        student1.set_password("password123")

        student2 = User(
            username="stu002",
            email="stu002@university.edu",
            real_name="李四",
            role="student",
            class_id=class1.id
        )
        student2.set_password("password123")

        teacher1 = User(
            username="tea001",
            email="tea001@university.edu",
            real_name="王教授",
            role="teacher"
        )
        teacher1.set_password("password123")

        teacher2 = User(
            username="tea002",
            email="tea002@university.edu",
            real_name="李教授",
            role="teacher"
        )
        teacher2.set_password("password123")

        counselor1 = User(
            username="coun001",
            email="coun001@university.edu",
            real_name="刘辅导员",
            role="counselor"
        )
        counselor1.set_password("password123")

        db.session.add_all([student1, student2, teacher1, teacher2, counselor1])
        db.session.commit()
        print("用户创建完成")

        # 设置班级辅导员
        print("设置班级辅导员...")
        class1.counselor_id = counselor1.id
        db.session.commit()
        print("班级辅导员设置完成")

        # 创建课程
        print("创建课程...")
        course1 = Course(
            course_code="CS101",
            course_name="Python程序设计",
            teacher_id=teacher1.id,
            class_id=class1.id,
            credit=3
        )

        course2 = Course(
            course_code="CS102",
            course_name="数据结构",
            teacher_id=teacher1.id,
            class_id=class1.id,
            credit=4
        )

        course3 = Course(
            course_code="MATH201",
            course_name="高等数学",
            teacher_id=teacher2.id,
            class_id=class1.id,
            credit=5
        )

        db.session.add_all([course1, course2, course3])
        db.session.commit()
        print("课程创建完成")

        # 创建选课数据
        print("创建选课数据...")
        selected_courses = [
            SelectedCourse(
                student_id=student1.id,
                course_id=course1.id,
                academic_year="2023-2024",
                semester="秋季"
            ),
            SelectedCourse(
                student_id=student1.id,
                course_id=course2.id,
                academic_year="2023-2024",
                semester="秋季"
            ),
            SelectedCourse(
                student_id=student1.id,
                course_id=course3.id,
                academic_year="2023-2024",
                semester="秋季"
            ),
            SelectedCourse(
                student_id=student2.id,
                course_id=course1.id,
                academic_year="2023-2024",
                semester="秋季"
            ),
            SelectedCourse(
                student_id=student2.id,
                course_id=course2.id,
                academic_year="2023-2024",
                semester="秋季"
            )
        ]
        db.session.add_all(selected_courses)
        db.session.commit()
        print("选课数据创建完成")

        # 创建成绩数据
        print("创建成绩数据...")
        grades = [
            Grade(
                student_id=student1.id,
                course_id=course1.id,
                teacher_id=teacher1.id,
                score=85.5,
                grade_point=3.5,
                grade_level="B",
                exam_type="期末",
                exam_date=date(2024, 1, 15),
                academic_year="2023-2024",
                semester="秋季",
                comments="表现良好，编程能力较强"
            ),
            Grade(
                student_id=student1.id,
                course_id=course2.id,
                teacher_id=teacher1.id,
                score=78.0,
                grade_point=2.8,
                grade_level="C",
                exam_type="期末",
                exam_date=date(2024, 1, 18),
                academic_year="2023-2024",
                semester="秋季",
                comments="基础概念掌握不够牢固"
            ),
            Grade(
                student_id=student1.id,
                course_id=course3.id,
                teacher_id=teacher2.id,
                score=45.0,
                grade_point=0.0,
                grade_level="F",
                exam_type="期末",
                exam_date=date(2024, 1, 20),
                academic_year="2023-2024",
                semester="秋季",
                comments="需要加强数学基础学习"
            ),
            Grade(
                student_id=student2.id,
                course_id=course1.id,
                teacher_id=teacher1.id,
                score=92.0,
                grade_point=4.0,
                grade_level="A",
                exam_type="期末",
                exam_date=date(2024, 1, 15),
                academic_year="2023-2024",
                semester="秋季",
                comments="优秀，编程思维清晰"
            ),
            Grade(
                student_id=student2.id,
                course_id=course2.id,
                teacher_id=teacher1.id,
                score=88.5,
                grade_point=3.8,
                grade_level="B",
                exam_type="期末",
                exam_date=date(2024, 1, 18),
                academic_year="2023-2024",
                semester="秋季",
                comments="数据结构理解较好"
            )
        ]
        db.session.add_all(grades)
        db.session.commit()
        print("成绩数据创建完成")

        # 创建课表数据
        print("创建课表数据...")
        schedules = [
            Schedule(
                course_id=course1.id,
                class_id=class1.id,
                day_of_week=1,
                start_time=time(8, 0),
                end_time=time(10, 0),
                location="教学楼A101",
                teacher_id=teacher1.id
            ),
            Schedule(
                course_id=course2.id,
                class_id=class1.id,
                day_of_week=1,
                start_time=time(14, 0),
                end_time=time(16, 0),
                location="实验楼B201",
                teacher_id=teacher1.id
            ),
            Schedule(
                course_id=course3.id,
                class_id=class1.id,
                day_of_week=2,
                start_time=time(10, 15),
                end_time=time(12, 15),
                location="教学楼A203",
                teacher_id=teacher2.id
            ),
            Schedule(
                course_id=course1.id,
                class_id=class1.id,
                day_of_week=3,
                start_time=time(8, 0),
                end_time=time(10, 0),
                location="教学楼A101",
                teacher_id=teacher1.id
            ),
            Schedule(
                course_id=course2.id,
                class_id=class1.id,
                day_of_week=4,
                start_time=time(16, 15),
                end_time=time(18, 15),
                location="实验楼B201",
                teacher_id=teacher1.id
            ),
            Schedule(
                course_id=course3.id,
                class_id=class1.id,
                day_of_week=5,
                start_time=time(14, 0),
                end_time=time(16, 0),
                location="教学楼A203",
                teacher_id=teacher2.id
            )
        ]

        db.session.add_all(schedules)
        db.session.commit()
        print("课表数据创建完成")

        # 创建考试安排数据
        print("创建考试安排数据...")
        exams = [
            Exam(
                course_id=course1.id,
                class_id=class1.id,
                exam_name="Python程序设计期末考试",
                exam_time=datetime(2024, 1, 15, 9, 0),
                location="教学楼A101-A105",
                seat_number="A001",
                duration=120
            ),
            Exam(
                course_id=course2.id,
                class_id=class1.id,
                exam_name="数据结构期中考试",
                exam_time=datetime(2024, 1, 18, 14, 0),
                location="实验楼B201",
                seat_number="B015",
                duration=90
            ),
            Exam(
                course_id=course3.id,
                class_id=class1.id,
                exam_name="高等数学期末考试",
                exam_time=datetime(2024, 1, 20, 9, 0),
                location="教学楼C301-C305",
                seat_number="C023",
                duration=150
            )
        ]

        db.session.add_all(exams)
        db.session.commit()
        print("考试安排创建完成")

        # 创建请假申请测试数据
        print("创建请假申请数据...")
        leave_applications = [
            LeaveApplication(
                student_id=student1.id,
                leave_type="事假",
                start_time=datetime(2024, 1, 10, 8, 0),
                end_time=datetime(2024, 1, 12, 18, 0),
                reason="家庭事务需要处理",
                status="approved",
                approver_id=counselor1.id
            ),
            LeaveApplication(
                student_id=student1.id,
                leave_type="病假",
                start_time=datetime(2024, 1, 5, 0, 0),
                end_time=datetime(2024, 1, 7, 0, 0),
                reason="感冒发烧，需要休息",
                status="approved",
                approver_id=counselor1.id
            ),
            LeaveApplication(
                student_id=student2.id,
                leave_type="事假",
                start_time=datetime(2024, 1, 8, 0, 0),
                end_time=datetime(2024, 1, 9, 0, 0),
                reason="参加学术竞赛",
                status="pending"
            )
        ]

        db.session.add_all(leave_applications)
        db.session.commit()
        print("请假申请数据创建完成")

        print("创建教室数据...")
        # 创建教室数据
        classrooms = [
            Classroom(
                room_number="A101",
                building="教学楼A",
                capacity=60,
                equipment="投影仪, 白板, 空调"
            ),
            Classroom(
                room_number="A102",
                building="教学楼A",
                capacity=45,
                equipment="投影仪, 白板"
            ),
            Classroom(
                room_number="B201",
                building="实验楼B",
                capacity=30,
                equipment="投影仪, 实验台, 空调"
            ),
            Classroom(
                room_number="C301",
                building="教学楼C",
                capacity=100,
                equipment="投影仪, 音响, 空调"
            ),
            Classroom(
                room_number="B202",
                building="实验楼B",
                capacity=25,
                equipment="实验台",
                status="maintenance"
            )
        ]

        db.session.add_all(classrooms)
        db.session.commit()
        print("教室数据创建完成")

        # 创建教室借用数据
        print("创建教室借用数据...")
        classroom_bookings = [
            ClassroomBooking(
                student_id=student1.id,
                classroom_id=classrooms[0].id,
                booking_date=date(2024, 1, 25),
                start_time=time(14, 0),
                end_time=time(16, 0),
                purpose="班级会议",
                participants=25,
                status="approved"
            ),
            ClassroomBooking(
                student_id=student2.id,
                classroom_id=classrooms[1].id,
                booking_date=date(2024, 1, 26),
                start_time=time(19, 0),
                end_time=time(21, 0),
                purpose="社团活动",
                participants=20,
                status="pending"
            )
        ]
        db.session.add_all(classroom_bookings)
        db.session.commit()
        print("教室借用数据创建完成")

        print("创建公告数据...")
        # 创建公告数据
        announcements = [
            Announcement(
                course_id=course1.id,
                teacher_id=teacher1.id,
                title="Python课程第一次作业通知",
                content="<p>请同学们在<strong>本周五前</strong>完成第一次作业提交。</p><p>作业要求：</p><ul><li>完成基础语法练习</li><li>编写一个简单的计算器程序</li><li>提交到学习平台</li></ul>",
                is_pinned=True,
                pin_duration=3
            ),
            Announcement(
                course_id=course2.id,
                teacher_id=teacher1.id,
                title="数据结构期中考试安排",
                content="<p>数据结构期中考试将于<u>下周三</u>举行。</p><p>考试地点：教学楼A101</p><p>考试时间：14:00-15:30</p>",
                is_pinned=True,
                pin_duration=7
            )
        ]

        db.session.add_all(announcements)
        db.session.commit()
        print("公告数据创建完成")

        print("创建课程资料数据...")
        # 创建课程资料数据
        materials_dir = os.path.join('uploads', 'course_materials')
        os.makedirs(materials_dir, exist_ok=True)

        # 创建示例文件内容
        sample_files = [
            {
                'name': 'Python基础语法讲义.pdf',
                'content': '这是一个示例PDF文件内容',
                'course_id': course1.id,
                'category': '课件'
            },
            {
                'name': '数据结构作业要求.docx',
                'content': '这是一个示例DOC文件内容',
                'course_id': course2.id,
                'category': '作业'
            },
            {
                'name': '高等数学参考书目.xlsx',
                'content': '这是一个示例Excel文件内容',
                'course_id': course3.id,
                'category': '参考资料'
            }
        ]

        materials = []
        for sample in sample_files:
            filename = f"{sample['course_id']}_{int(datetime.now().timestamp())}_{sample['name']}"
            filepath = os.path.join(materials_dir, filename)

            # 创建示例文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sample['content'])

            material = CourseMaterial(
                course_id=sample['course_id'],
                teacher_id=teacher1.id if sample['course_id'] in [course1.id, course2.id] else teacher2.id,
                file_name=sample['name'],
                file_path=filename,
                file_size=len(sample['content']),
                file_type=sample['name'].split('.')[-1],
                category=sample['category'],
                description=f"{sample['category']} - 示例文件"
            )
            materials.append(material)

        db.session.add_all(materials)
        db.session.commit()
        print("课程资料数据创建完成")

        print("创建学业预警数据...")
        # 创建学业预警数据
        academic_alerts = [
            AcademicAlert(
                student_id=student1.id,
                counselor_id=counselor1.id,
                alert_level='一级',
                failed_courses=json.dumps(["高等数学", "数据结构", "Python程序设计"]),
                total_failed=3,
                reason='连续两学期挂科≥2门，需要重点关注',
                semester='2023-2024-1',
                status='active'
            ),
            AcademicAlert(
                student_id=student2.id,
                counselor_id=counselor1.id,
                alert_level='二级',
                failed_courses=json.dumps(["高等数学", "数据结构"]),
                total_failed=2,
                reason='挂科2门，需要及时辅导',
                semester='2023-2024-1',
                status='active'
            )
        ]

        db.session.add_all(academic_alerts)
        db.session.commit()
        print("学业预警数据创建完成")

        print("创建辅导记录数据...")
        # 创建辅导记录数据
        counseling_records = [
            CounselingRecord(
                alert_id=academic_alerts[0].id,
                counselor_id=counselor1.id,
                counseling_time=datetime(2024, 1, 15, 14, 30),
                content='与学生进行了深入交流，了解学习困难原因。学生表示数学基础薄弱，编程练习不足。',
                plan='1. 建议参加数学辅导班\n2. 增加编程练习时间\n3. 每周进行一次学习进度检查'
            ),
            CounselingRecord(
                alert_id=academic_alerts[1].id,
                counselor_id=counselor1.id,
                counseling_time=datetime(2024, 1, 16, 10, 0),
                content='了解学生时间管理问题，发现学生课外活动过多影响学习。',
                plan='1. 帮助学生制定合理的时间表\n2. 减少不必要的课外活动\n3. 重点关注数据结构学习'
            )
        ]

        db.session.add_all(counseling_records)
        db.session.commit()
        print("辅导记录数据创建完成")

        print("=" * 50)
        print("数据库初始化完成！")
        print("=" * 50)
        print("测试账号信息：")
        print("学生账号: stu001 / password123")
        print("学生账号: stu002 / password123")
        print("教师账号: tea001 / password123")
        print("教师账号: tea002 / password123")
        print("辅导员账号: coun001 / password123")
        print("=" * 50)
        print("测试数据统计：")
        print(f"- 班级: {Class.query.count()} 个")
        print(f"- 用户: {User.query.count()} 个")
        print(f"- 课程: {Course.query.count()} 门")
        print(f"- 选课: {SelectedCourse.query.count()} 条")
        print(f"- 成绩: {Grade.query.count()} 条")
        print(f"- 课表: {Schedule.query.count()} 条")
        print(f"- 考试: {Exam.query.count()} 场")
        print(f"- 请假: {LeaveApplication.query.count()} 条")
        print(f"- 教室: {Classroom.query.count()} 间")
        print(f"- 教室借用: {ClassroomBooking.query.count()} 条")
        print(f"- 公告: {Announcement.query.count()} 条")
        print(f"- 资料: {CourseMaterial.query.count()} 个")
        print(f"- 学业预警: {AcademicAlert.query.count()} 条")
        print(f"- 辅导记录: {CounselingRecord.query.count()} 条")
        print("=" * 50)


if __name__ == '__main__':
    init_database()