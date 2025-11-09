# auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from models import db, User

auth_bp = Blueprint('auth', __name__)


# 修正 auth.py 中的问题
@auth_bp.route('/')
@auth_bp.route('/index')
def index():
    if current_user.is_authenticated:
        # 根据用户角色重定向到对应的仪表板
        if current_user.is_student():
            return redirect(url_for('student.dashboard'))
        elif current_user.is_teacher():
            return redirect(url_for('teacher.dashboard'))
        elif current_user.is_counselor():
            return redirect(url_for('counselor.dashboard'))  # 修正：删除重复判断
        else:
            return redirect(url_for('auth.login'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # 如果已经登录，直接重定向到对应仪表板
        if current_user.is_student():
            return redirect(url_for('student.dashboard'))
        elif current_user.is_teacher():
            return redirect(url_for('teacher.dashboard'))
        elif current_user.is_counselor():
            return redirect(url_for('counselor.dashboard'))  # 修正：指向辅导员仪表板
        else:
            return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember_me)

        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            # 根据用户角色设置默认重定向页面
            if user.is_student():
                next_page = url_for('student.dashboard')
            elif user.is_teacher():
                next_page = url_for('teacher.dashboard')
            elif user.is_counselor():
                next_page = url_for('counselor.dashboard')  # 修正：指向辅导员仪表板
            else:
                next_page = url_for('auth.login')

        flash(f'欢迎回来，{user.real_name}！', 'success')
        return redirect(next_page)

    return render_template('login.html', title='登录')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('auth.index'))