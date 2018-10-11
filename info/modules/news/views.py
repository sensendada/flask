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


@news_blue.route('/news_list')
def get_news_list():

    """
    新闻列表
    1.获取参数， cid， page， per_page
    2.检查参数
    3.根据cid来检查mysql数据库
    如果用户选择最新，默认查询所有
     News.query.filter().order_by(News.create_time.desc()).paginate(page,per_page,False)
    News.query.filter(News.category_id==cid).order_by(News.create_time.desc()).paginate(page,per_page,False)
    4.获取分页后的数据
    总页数 当前页数 新闻页数
    5.返回结果

    :return:
    """
    # 获取参数
    cid = request.args.get('cid', '1')
    page = request.args.get('page', '1')
    per_page = request.args.get('per_page', '10')
    # 转换参数的数据类型
    try:
        cid, page, per_page = int(cid), int(page), int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg='参数格式错误')
    # 定义容器，存储查询的过滤条件
    filters = []
    if cid > 1:
        filters.append(News.category_id == cid)
    # 使用过滤条件查询mysql，按照新闻发布时间排序
    print(filters)
    try:
        # *filters表示python中拆包，News.category_id == cid, *filters里面存储的是sqlalchemy对象
        # 在python中测试添加的数据为True或False
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻数据失败')
    # 获取分页后的数据
    news_list = paginate.items
    total_page = paginate.pages
    current_page = paginate.page
    # 定义容器，存储查询到的新闻数据
    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_dict())
    data = {
        'news_dict_list':news_dict_list,
        'total_page':total_page,
        'current_page':current_page
    }
    # 返回数据
    return jsonify(errno=RET.OK,errmsg='OK', data=data)

@news_blue.route('/<int:news_id>')
@login_required
def get_news_detail(news_id):
    """
    新闻详情
        用户数据展示
        点击排行展示
        新闻数据展示
    :param news_id:
    :return:
    """
    # 从登陆验证装饰器中获取用户的信息
    user = g.user
    # 新闻点击排行
    try:
        news_list = News.query.order_by(News.clicks.desc().limit(constants.CLICK_RANK_MAX_NEWS))
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻排行数据失败')
    if not news_list:
        return jsonify(errno=RET.NODATA,errmsg='无新闻排行数据')
    news_click_list = []
    for news in news_list:
        news_click_list.append(news.to_dict())

    # 新闻详情数据
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询新闻详情数据失败')
    if not news:
        return jsonify(errno=RET.NODATA,errmsg='无新闻排行数据')
    # 收藏或取消收藏标记
    is_collected = False
    # 判断用户是否收藏过， 用户登录后才能显示新闻是否收藏过
    if news in g.user.collection_news:
        is_collected = True
    data = {
        'user_info':user.to_dict() if user else None,
        'news_click_list':news_click_list,
        'news_detail':news.to_dict(),
        'is_collected':is_collected
    }
    return render_template('news/detail.html', data = data)

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