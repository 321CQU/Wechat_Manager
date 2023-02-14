import hashlib
from enum import StrEnum
from typing import Dict, Optional

import httpx
from sanic import Sanic, Request, text, json
from sanic.exceptions import Unauthorized
from sanic_ext import openapi
from sanic_ext.extensions.openapi.definitions import Parameter

from pydantic import BaseModel, Field

from utils.log_config import LogConfig
from utils.Settings import ConfigManager
from utils.tools import handle_wechat_server_event
from utils.WechatManager import WechatManager

app = Sanic('API_Gateway', log_config=LogConfig)

app.config.CORS_ORIGINS = ["http://321cqu.com", "https://321cqu.com", "http://api.321cqu.com", "https://api.321cqu.com"]
app.config.CORS_SUPPORTS_CREDENTIALS = True


@app.get('/wechat')
async def handle_wechat_verify(request: Request):
    data = request.args

    signature = data.get('signature')
    timestamp = data.get('timestamp')
    nonce = data.get('nonce')
    echostr = data.get('echostr')

    token = ConfigManager().get_config('Key', 'wechat_token')

    temp_arr = [timestamp, nonce, token]
    temp_arr.sort()
    temp_str = ''.join(temp_arr)
    temp = hashlib.sha1(temp_str.encode("utf-8")).hexdigest()
    if temp == signature:
        return text(echostr)


@app.post('/wechat')
async def handle_wechat_post(request: Request):
    try:
        openid = request.json['FromUserName']
        event = request.json['Event']
        payload = request.json['List']

        if isinstance(payload, Dict):
            payload = [payload]

        app.add_task(handle_wechat_server_event(openid, event, payload))
    finally:
        return text('success')


@app.get('/token')
@openapi.parameter(parameter=Parameter('token', str, description='请求密钥'))
async def get_token(request: Request):
    """
    获取小程序access token
    """
    token = request.args.get('token')
    if token is None or token != ConfigManager().get_config('Key', 'secret'):
        raise Unauthorized(message='Unauthorized')

    return text(await WechatManager().get_token())


@app.get('/openid/<code:str>')
@openapi.parameter(parameter=Parameter('code', str, 'path', '小程序端获取的临时代码'))
@openapi.parameter(parameter=Parameter('token', str, description='请求密钥'))
async def get_openapi(request: Request, code: str):
    """
    获取用户openid
    """
    token = request.args.get('token')
    if token is None or token != ConfigManager().get_config('Key', 'secret'):
        raise Unauthorized(message='Unauthorized')

    return text(await WechatManager().get_openid(code))


class NotificationRequest(BaseModel):
    class JumpTarget(StrEnum):
        Developer = 'developer'
        Formal = 'formal'

    template_id: str = Field(title='模版ID')
    page: Optional[str] = Field(title='点击后跳转页面')
    data: Dict = Field(title='需要传递给模版的数据')
    miniprogram_state: Optional[JumpTarget] = Field(JumpTarget.Formal, title='需要跳转的小程序版本')


@app.post('/notification/<openid>')
@openapi.parameter(parameter=Parameter('openid', str, 'path', '用户openid'))
@openapi.parameter(parameter=Parameter('token', str, description='请求密钥'))
@openapi.body({'application/json': NotificationRequest.schema()}, validate=True)
async def push_notification(request: Request, openid: str, body: NotificationRequest):
    """
    发送小程序通知
    """
    token = request.args.get('token')
    if token is None or token != ConfigManager().get_config('Key', 'secret'):
        raise Unauthorized(message='Unauthorized')

    manager = WechatManager()
    data = {
        'template_id': body.template_id,
        'page': body.page,
        'touser': openid,
        'data': body.data,
        'miniprogram_state': body.miniprogram_state.value,
        'lang': 'zh_CN'
    }
    if body.page is None:
        data.pop('page')

    async with httpx.AsyncClient() as client:
        res = await client.post('https://api.weixin.qq.com/cgi-bin/message/subscribe/send', params={
            'access_token': await manager.get_token()
        }, json=data)
        return json({
            'error_code': res.json()['errcode'],
            'error_msg': res.json()['errmsg']
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8321, access_log=True)
