from functools import wraps
from flask import current_app, g, request
from itsdangerous import TimestampSigner
from strong.api.errors import api_abort, invalid_token, token_missing
from strong.models import User


def get_s():
    '''据secret_key生成一个用于签名的对象'''
    return TimestampSigner(current_app.config['SECRET_KEY'])


def generate_token(user_id: int | str):
    # 用户ID 编码成一个令牌(二进制串)：根据key，在id后附加一串字符
    # TimestampSigner只对字节签名，将对象序列化为字符串后前面有其它的接口。
    s = get_s()
    token = s.sign(str(user_id)).decode('ascii')  # 解码为字符串，方便返回给客户端
    return token


def validate_token(token):
    '''会设置g.current_user'''
    s = get_s()
    try:
        user_id = s.unsign(token)
        user = User.query.get(user_id)
    except:
        print(f'[{__name__}]验证令牌失败')
        return False
    if user is None:
        return False
    g.current_user = user
    return True


def get_token():
    '''自己解析Authorization字段'''
    # Flask/Werkzeug do not recognize any authentication types
    # other than Basic or Digest, so here we parse the header by hand.
    if 'Authorization' in request.headers:
        try:
            token_type, token = request.headers['Authorization'].split(None, 1)
        except ValueError:
            # The Authorization header is either empty or has no token
            token_type = token = None
    else:
        token_type = token = None

    return token_type, token


def auth_required(f):
    '''据token验证登录，后可据g.current_user访问用户信息。'''
    @wraps(f)
    def decorated(*args, **kwargs):
        token_type, token = get_token()
        # 备注：暂不考虑CORS的事先请求使用OPTIONS方法（也暂不知道干嘛的）
        if token_type is None or token_type.lower() != 'bearer':
            return api_abort(400, 'The token type must be bearer.')
        if token is None:
            return token_missing()
        if not validate_token(token):
            return invalid_token()
        return f(*args, **kwargs)

    return decorated
