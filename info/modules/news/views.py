# 使用蓝图对象
from flask import session, render_template, current_app

from . import news_blue

import hashlib
from werkzeug.security import generate_password_hash,check_password_hash


# 首页模板数据加载
@news_blue.route('/')
def index():
    session['python14'] = '2018'
    return render_template('news/index.html')


# 项目favicon.ico文件的加载
@news_blue.route('/favicon.ico')
def favicon():
    """
    http://127.0.0.1:5000/favicon.ico
    实现/favicon.ico路径下的图标加载
    1、favicon图标的加载，不是每次请求都加载，是浏览器默认实现的，如果有缓存，必须要清除缓存，
    2、把浏览器彻底关闭，重启浏览器。
    :return:
    """
    # 使用current_app调用flask内置的函数，发送静态文件给浏览器，实现logo图标的加载
    return current_app.send_static_file('news/favicon.ico')