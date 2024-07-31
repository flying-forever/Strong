from flask import jsonify


def api_abort(code, message=None, **kwargs):
    # 客户端可以在错误的response部分看见message
    response = jsonify(code=code, message=message, **kwargs)
    return response, code


def invalid_token():
    # WWW-Authenticate响应头是 HTTP 协议的一部分，告诉客户端需要进行何种身份验证才能访问资源。
    # error参数为OAUTH 2.0定义的错误类型可选值之一
    # 401响应，浏览器会弹出填写用户id和密码的窗口
    response = api_abort(401, error='invalid_token', error_description='Either the token was expired or invalid.')
    response.headers['WWW-Authenticate'] = 'Bearer'
    return response


def token_missing():
    response = api_abort(401)
    response.headers['WWW-Authenticate'] = 'Bearer'
    return response
