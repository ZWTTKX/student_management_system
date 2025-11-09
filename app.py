# app.py
from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from config import Config
import os

# 创建扩展实例
db = None
login_manager = LoginManager()


def create_app():
    global db

    app = Flask(__name__)
    app.config.from_object(Config)

    # 延迟导入以避免循环导入
    from models import db as models_db
    db = models_db

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)

    # 登录管理配置
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面。'
    login_manager.login_message_category = 'warning'

    # 配置用户加载器
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 注册蓝图
    register_blueprints(app)

    # 创建必要的目录
    create_directories(app)

    # Favicon 路由
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # 主页路由
    @app.route('/')
    def index():
        return render_template('index.html')

    # 错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    return app


def register_blueprints(app):
    """注册所有蓝图"""
    try:
        # 首先注册认证蓝图
        from auth import auth_bp
        app.register_blueprint(auth_bp)

        # 然后注册其他功能蓝图
        from routes.student import student_bp
        app.register_blueprint(student_bp)

        from routes.teacher import teacher_bp
        app.register_blueprint(teacher_bp)

        from routes.counselor import counselor_bp
        app.register_blueprint(counselor_bp)

        from routes.schedule import schedule_bp
        app.register_blueprint(schedule_bp)

        from routes.classroom import classroom_bp
        app.register_blueprint(classroom_bp)

        print("所有蓝图注册成功")

    except ImportError as e:
        print(f"蓝图导入错误: {e}")
        import traceback
        traceback.print_exc()



def create_directories(app):
    """创建必要的上传目录"""
    upload_dirs = [
        'course_materials',
        'leave_attachments',
        'avatars',
        'qrcodes'
    ]

    for dir_name in upload_dirs:
        dir_path = os.path.join(app.config['UPLOAD_FOLDER'], dir_name)
        os.makedirs(dir_path, exist_ok=True)




# 创建应用实例
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # 确保数据库表存在
        from models import db

        db.create_all()

        print("=" * 50)
        print("学生管理系统启动成功！")
        print(f"访问地址: http://127.0.0.1:5000")
        print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)