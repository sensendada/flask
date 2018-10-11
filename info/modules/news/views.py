# 使用蓝图对象
from flask import session, render_template, current_app, jsonify, request, g

from info import constants, db
from info.models import User, Category, News
from info.utils.commons import login_required
from info.utils.response_code import RET
from . import news_blue

import hashlib
from werkzeug.security import generate_password_hash,check_password_hash


# 首页模板数据加载
@news_blue.route('/')
# @login_required
def index():
    """
    首页
        右上角用户信息展示：检查用户登陆状态
    :return:
    """
    # 尝试从redis缓存中获取用户id
    user_id = session.get('user_id')
    user = None
    # 判断获取结果
    if user_id:
        # 根据user_id，查询mysql获取用户信息
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)

    # 新闻分类数据展示
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询新闻分类数据失败')
    # 判断查询结果
    if not categories:
        return jsonify(errno=RET.NODATA, errmsg='无新闻分类数据')
    category_list = []
    # 遍历查询新闻分类结果，存入列表
    for category in categories:
        category_list.append(category.to_dict())

    # 新闻点击排行
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询新闻排行失败')
    if not news_list:
        return jsonify(errno=RET.NODATA, errmsg='无新闻排行数据')
    news_click_list = []
    for news in news_list:
        news_click_list.append(news.to_dict())




    data = {
        'user_info': user.to_dict() if user else None,
        'category_list': category_list,
        'news_click_list': news_click_list

    }

    return render_template('news/index.html', data=data)
    # user = g.user


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