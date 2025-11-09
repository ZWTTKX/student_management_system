# routes/schedule.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import db, Schedule  # 直接从 models 导入

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/api/schedule/week/<int:week_offset>')
@login_required
def api_schedule_by_week(week_offset):
    """API: 按周获取课表数据"""
    if not current_user.is_student():
        return jsonify({'error': '无权访问'}), 403

    schedules = Schedule.query.filter_by(class_id=current_user.class_id).all()

    schedule_data = {}
    for schedule in schedules:
        day_data = schedule_data.get(schedule.day_of_week, [])
        day_data.append(schedule.to_dict())
        schedule_data[schedule.day_of_week] = day_data

    return jsonify(schedule_data)