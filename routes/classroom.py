# routes/classroom.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, time, timedelta
import os
from models import db, Classroom, ClassroomBooking, User
from werkzeug.utils import secure_filename

classroom_bp = Blueprint('classroom', __name__, url_prefix='/classroom')


@classroom_bp.route('/booking')
@login_required
def booking():
    """教室借用页面"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('student/classroom_booking.html')


@classroom_bp.route('/available-classrooms', methods=['POST'])
@login_required
def available_classrooms():
    """获取可用教室列表"""
    if not current_user.is_student():
        return jsonify({'error': '无权访问'}), 403

    data = request.get_json()
    booking_date = data.get('booking_date')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    try:
        booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        return jsonify({'error': '时间格式错误'}), 400

    # 验证时间合法性
    if start_time >= end_time:
        return jsonify({'error': '结束时间必须晚于开始时间'}), 400

    if booking_date < date.today():
        return jsonify({'error': '不能借用过去的日期'}), 400

    # 查询已被占用的教室
    booked_classrooms = ClassroomBooking.query.filter(
        ClassroomBooking.booking_date == booking_date,
        ClassroomBooking.status == 'approved',
        db.or_(
            db.and_(
                ClassroomBooking.start_time <= start_time,
                ClassroomBooking.end_time > start_time
            ),
            db.and_(
                ClassroomBooking.start_time < end_time,
                ClassroomBooking.end_time >= end_time
            ),
            db.and_(
                ClassroomBooking.start_time >= start_time,
                ClassroomBooking.end_time <= end_time
            )
        )
    ).with_entities(ClassroomBooking.classroom_id).all()

    booked_classroom_ids = [bc[0] for bc in booked_classrooms]

    # 查询可用教室（排除已被占用和维修中的教室）
    available_classrooms = Classroom.query.filter(
        Classroom.status == 'available',
        ~Classroom.id.in_(booked_classroom_ids) if booked_classroom_ids else True
    ).all()

    classrooms_data = []
    for classroom in available_classrooms:
        classrooms_data.append({
            'id': classroom.id,
            'room_number': classroom.room_number,
            'building': classroom.building,
            'capacity': classroom.capacity,
            'equipment': classroom.equipment
        })

    return jsonify({'classrooms': classrooms_data})


@classroom_bp.route('/submit-booking', methods=['POST'])
@login_required
def submit_booking():
    """提交教室借用申请"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    classroom_id = request.form.get('classroom_id')
    booking_date = request.form.get('booking_date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    purpose = request.form.get('purpose')
    participants = request.form.get('participants')

    # 验证数据
    if not all([classroom_id, booking_date, start_time_str, end_time_str, purpose, participants]):
        flash('请填写所有必填字段', 'danger')
        return redirect(url_for('classroom.booking'))

    try:
        booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        participants = int(participants)
    except ValueError:
        flash('数据格式错误', 'danger')
        return redirect(url_for('classroom.booking'))

    # 验证时间合法性
    if start_time >= end_time:
        flash('结束时间必须晚于开始时间', 'danger')
        return redirect(url_for('classroom.booking'))

    if booking_date < date.today():
        flash('不能借用过去的日期', 'danger')
        return redirect(url_for('classroom.booking'))

    # 检查教室是否存在且可用
    classroom = Classroom.query.get(classroom_id)
    if not classroom or classroom.status != 'available':
        flash('所选教室不可用', 'danger')
        return redirect(url_for('classroom.booking'))

    # 检查参与人数是否超过教室容量
    if participants > classroom.capacity:
        flash(f'参与人数不能超过教室容量（{classroom.capacity}人）', 'danger')
        return redirect(url_for('classroom.booking'))

    # 检查时间冲突
    existing_booking = ClassroomBooking.query.filter(
        ClassroomBooking.classroom_id == classroom_id,
        ClassroomBooking.booking_date == booking_date,
        ClassroomBooking.status == 'approved',
        db.or_(
            db.and_(
                ClassroomBooking.start_time <= start_time,
                ClassroomBooking.end_time > start_time
            ),
            db.and_(
                ClassroomBooking.start_time < end_time,
                ClassroomBooking.end_time >= end_time
            ),
            db.and_(
                ClassroomBooking.start_time >= start_time,
                ClassroomBooking.end_time <= end_time
            )
        )
    ).first()

    if existing_booking:
        flash('该时间段教室已被占用，请选择其他时间', 'danger')
        return redirect(url_for('classroom.booking'))

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

    flash('教室借用申请提交成功，等待管理员审核', 'success')
    return redirect(url_for('classroom.booking_records'))


@classroom_bp.route('/records')
@login_required
def booking_records():
    """借用记录"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    bookings = ClassroomBooking.query.filter_by(student_id=current_user.id) \
        .order_by(ClassroomBooking.created_at.desc()).all()

    return render_template('student/booking_records.html', bookings=bookings)


@classroom_bp.route('/download-voucher/<int:booking_id>')
@login_required
def download_voucher(booking_id):
    """下载借用凭证"""
    if not current_user.is_student():
        flash('无权访问此页面', 'danger')
        return redirect(url_for('auth.login'))

    booking = ClassroomBooking.query.get_or_404(booking_id)

    if booking.student_id != current_user.id:
        flash('无权访问此记录', 'danger')
        return redirect(url_for('classroom.booking_records'))

    if booking.status != 'approved':
        flash('只有已批准的申请才能下载凭证', 'warning')
        return redirect(url_for('classroom.booking_records'))

    # 生成简单的借用凭证（这里简化处理，实际可以生成PDF）
    voucher_content = f"""
    教室借用凭证
    ====================

    学生姓名：{booking.student.real_name}
    教室编号：{booking.classroom.room_number}
    教学楼：{booking.classroom.building}
    借用日期：{booking.booking_date.strftime('%Y年%m月%d日')}
    借用时间：{booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}
    借用事由：{booking.purpose}
    参与人数：{booking.participants}

    审批状态：已批准
    凭证生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}

    请凭此凭证使用教室，使用时请遵守教室使用规定。
    """

    from io import BytesIO
    buffer = BytesIO(voucher_content.encode('utf-8'))

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'教室借用凭证_{booking.classroom.room_number}_{booking.booking_date.strftime("%Y%m%d")}.txt',
        mimetype='text/plain'
    )