from datetime import datetime
from typing import Optional, Dict

import httpx
from _321CQU.tools import Singleton

from utils.Settings import ConfigManager


class CannotGetToken(Exception):
    def __init__(self, res: Dict):
        super().__init__('无法获取AccessToken')
        self.extra = res


class CannotGetOpenid(Exception):
    def __init__(self, error_code: int, error_msg: str):
        super().__init__('无法获取openid')
        self.error_code = error_code
        self.error_msg = error_msg


class WechatManager(metaclass=Singleton):
    def __init__(self):
        self._token: Optional[str] = None
        self._refresh_time: int = 0

    async def get_token(self) -> str:
        if self._token is None:
            self._token = await self.refresh_token()

        return self._token

    async def refresh_token(self) -> str:
        now = int(datetime.now().timestamp())
        reader = ConfigManager()

        async with httpx.AsyncClient() as client:
            res = await client.get('https://api.weixin.qq.com/cgi-bin/token', params={
                'grant_type': 'client_credential',
                'appid': reader.get_config('WechatMiniAppSetting', 'appid'),
                'secret': reader.get_config('WechatMiniAppSetting', 'secret'),
            })
            data: Dict = res.json()
            access_token = data.get('access_token')
            expires_time = data.get('expires_in')

            if access_token is not None:
                self._refresh_time = now + expires_time - 300
                return access_token
            else:
                raise CannotGetToken(data)

    async def get_openid(self, code: str):
        reader = ConfigManager()

        async with httpx.AsyncClient() as client:
            res = await client.get('https://api.weixin.qq.com/sns/jscode2session', params={
                'grant_type': 'authorization_code',
                'appid': reader.get_config('WechatMiniAppSetting', 'appid'),
                'secret': reader.get_config('WechatMiniAppSetting', 'secret'),
                'js_code': code
            })

            data: Dict = res.json()
            error_code = data.get('errcode')
            if error_code is None:
                return data.get('openid')
            else:
                error_msg = data.get('errmsg')
                raise CannotGetOpenid(error_code, error_msg)
