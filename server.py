import hashlib
from typing import Dict

from sanic import Sanic, Request, text

from utils.log_config import LogConfig
from utils.Settings import ConfigManager
from utils.tools import handle_wechat_server_event

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8321, access_log=True)
