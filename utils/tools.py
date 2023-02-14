from asyncio import TaskGroup
from typing import Dict, List

from _321CQU.tools.gRPCManager import gRPCManager, ServiceEnum

import micro_services_protobuf.notification_center.wechat_pb2 as wechat_model
import micro_services_protobuf.notification_center.service_pb2_grpc as notification_grpc


async def handle_wechat_server_event(openid: str, event: str, payload: List[Dict]):
    if payload[0].get('TemplateId') is None or payload[0].get('SubscribeStatusString') is None:
        return
    async with gRPCManager().get_stub(ServiceEnum.WechatService) as stub:
        stub: notification_grpc.WechatStub
        async with TaskGroup() as tg:
            for item in payload:
                tg.create_task(
                    stub.HandleWechatServerEvent(wechat_model.HandleWechatServerEventRequest(
                        openid=openid, template_id=item['TemplateId'],
                        is_accept=item['SubscribeStatusString'] == 'accept'
                    ))
                )


