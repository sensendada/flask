from flask import request,jsonify,current_app,make_response,session

from . import passport_blue
# 导入自定义的状态码
from info.utils.response_code import RET
# 导入生成图片验证码的工具
from info.utils.captcha.captcha import captcha
# 导入redis实例,常量文件
from info import redis_store,constants,db
# 导入正则
import re,random
# 导入云通讯
from info.libs.yuntongxun import sms
# 导入模型类User
from info.models import User

"""
生成图片验证码
uuid:全局唯一的标识符，redis.setex('ImagCode_' + uuid)
1.获取前段生成的uuid
request。args.get("image_code_id")
2.判断参数是否存在，如果不存在直接return
3.使用工具captcha生成图片验证码，name,text,image
4.保存图片验证码的text文本，redis数据库中
5.返回图片
发送短信
注册
登录
退出

"""


@passport_blue.route("/image_code")
def generate_image_code():
    """
    生成图片验证码
    uuid：全局唯一的标识符，redis.setex('ImageCode_' + uuid )
    1、获取前端生成的uuid
    request.args.get("image_code_id")
    2、判断参数是否存在，如果不存在直接return
    3、使用工具captcha生成图片验证码,name,text,image
    4、保存图片验证码的text文本，redis数据库中
    5、返回图片

    :return:
    """
    # 获取前段传入的图片验证码的编号uuid
    image_code_id = request.args.get('image_code_id')
    # 判断参数是否存在
    if not image_code_id:
        return jsonify(errno=RET.PARAMERR, errmsg='参数缺失')
    # 调用captcha工具，生成图片验证码
    name, text, image = captcha.generate_captcha()
    # 保存图片验证码的文本到redis数据库中
    try:
        redis_store.setex('ImageCode_' + image_code_id,constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg='保存数据异常')
    else:
        response = make_response(image)
        # 修改默认的响应类型, text/html
        response.headers['Content-Type'] = 'image/jpg'
        return response


@passport_blue.route("/sms_code", methods=['POST'])
def send_sms_code():
    """
    发送短信：web开发：写接口，调接口
    获取参数-----检查参数-----业务处理 ----返回结果
    1.获取参数就mobile,image_code, image_code_id
    2.检查参数的完整性
    3.检查手机号的格式，正则
    4.尝试从redis数据库中获取正确的图片验证码
    image_code = redis_store.get(imagecode)
    5.判断获取结果，如果不存在，书名图片验证码已过期
    6.删除redis数据库中存储的图片验证码，因为无论图片验证码正确与否，只能比较一次
    7.比较图片验证码是否正确
    8.构造短信随机码，6位数
    9.使用云通讯发送短信，保存发送结果
    10.返回结果
    :return:
    """
    # 从前端获取参数
    mobile = request.json.get('mobile')
    image_code = request.json.get('image_code')
    image_code_id = request.jsonify.get('image_code_id')
    # 检查参数的完整性
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    # 使用正则校验手机号格式
    if not re.match(r'1[3456789]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式错误')
    # 检查手机号是否可以注册
    # 获取redis中存储的真实的图片验证码
    try:
        real_image_code = redis_store.get('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取数据失败')
    # 判断获取结果
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='图片验证码已经过期')
    # 删除redis中的图片验证码
    try:
        redis_store.delete('ImageCode' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 比较图片验证码手机否一致，忽略大小写
    if real_image_code.lower() != image_code_id():
        return jsonify(errno=RET.DATAERR, errmsg='图片验证码不一致')
    # 判断 手机号是否可以注册
    try:
        user = User.query.filter_by(moblie=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户上数据时报')
    else:
        if user:
            return jsonify(errno=RET.DATAERR, errmsg='手机号已经注册了')

    # 构造六位数的短信验证码
        sms_code = '%06d' % random.randint(0, 999999)
        print(sms_code)
        # 存入redis数据库中
        try:
            redis_store.setex('SMSCode_' + mobile,constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='保存数据异常')
        # 使用云通讯发送短信
        try:
            ccp = sms.CCP()
            results = ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES/60], 1)
        except Exception as e:
            current_app.looger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg='发送短信异常')
        # 判断发送结果
        if results == 0:
            return jsonify(errno=RET.OK, errmsg='发送成功')
        else:
            return jsonify(errno=RET.THIRDERR, errmsg='发送失败')


