from typing import Literal

from pydantic import IPvAnyAddress

from abstract.apis.receiver import WSMessageReceiver
from abstract.apis.ws_manager import WSManager
from abstract.bases.importer import abc, requests, dispatch, base64, time, threading
from abstract.bases.exceptions import *
from abstract.bases.config import CONFIG
from abstract.bases.log import LOG


class BaseOneBotServer(abc.ABC):
    @abc.abstractmethod
    def __init__(self, host: str, port: int, token: str, **_):
        self.host = host
        self.port = port

    @abc.abstractmethod
    def get_msg(self, message_id: int) -> dict: ...
    """
    获取消息
    
    :param message_id: 消息ID
    :type message_id: int
    
    :return: 消息内容
    """

    @abc.abstractmethod
    def send_group_msg(self, message) -> int: ...
    """
    发送群消息
    
    :param message: 信息
    :type message: abstract.message.GroupMessage
    
    :return: 消息目标
    :rtype: abstract.target.Group
    """

    @abc.abstractmethod
    def send_private_msg(self, message) -> int: ...
    """
    发送私聊消息
    
    :param message: 信息
    :type message: abstract.message.PrivateMessage
    
    :return: 消息目标
    :rtype: abstract.target.User
    """

    @abc.abstractmethod
    def get_stranger_info(self, id: int) -> dict: ...
    """
    获取陌生人信息
    
    :param id: 用户ID
    :type id: int
    
    :return: 用户信息
    :rtype: dict
    """

    @abc.abstractmethod
    def get_friend_list(self) -> list: ...
    """
    获取好友列表
    
    :return: 好友列表
    :rtype: list
    """

    @abc.abstractmethod
    def set_friend_add_request(self, flag: str, approve: bool = True): ...
    """
    设置好友添加请求
    
    :param flag: 请求标识
    :type flag: str
    :param approve: 是否同意
    :type approve: bool
    
    :return: None
    """

    @abc.abstractmethod
    def set_group_add_request(self, flag: str, approve: bool = True): ...
    """
    设置群添加请求
    
    :param flag: 请求标识
    :type flag: str
    :param approve: 是否同意
    :type approve: bool
    
    :return: None
    """

    @abc.abstractmethod
    def get_group_list(self) -> list: ...
    """
    获取群列表
    
    :return: 群列表
    :rtype: list
    """

    @abc.abstractmethod
    @dispatch
    def send_poke(self, user_id: int, group_id: int) -> None: ...
    """
    群内戳一戳
    
    :param user_id: 用户ID
    :type user_id: int
    :param group_id: 群ID
    :type group_id: int
    
    :return: None
    """

    @abc.abstractmethod
    @dispatch
    def send_poke(self, user_id: int) -> None: ...
    """
    私聊戳一戳
    
    :param user_id: 用户ID
    :type user_id: int
    
    :return: None
    """

    @abc.abstractmethod
    def get_record(self, file_id: str) -> bytes: ...
    """
    获取语音文件内容
    
    :param file_id: 语音文件ID
    :type file_id: str
    
    :return: 语音文件内容
    :rtype: bytes
    """

    @abc.abstractmethod
    def get_forward_msg(self, message_id: str) -> list[dict]: ...
    """
    获取合并转发内容
    
    :param message_id: 消息ID
    :type message_id: str
    
    :return: 合并转发内容
    :rtype: list[dict]
    """

    @abc.abstractmethod
    def get_login_info(self) -> dict: ...
    """
    获取登录信息
    
    :return: 登录信息
    :rtype: dict
    """

    @abc.abstractmethod
    def delete_msg(self, message_id: int) -> None: ...
    """
    撤回消息
    
    :param message_id: 消息ID
    :type message_id: int
    """

    @abc.abstractmethod
    def get_group_member_list(self, group_id: int) -> list[dict]:
        """
        获取群人员列表

        :param group_id: 群ID

        :return: 人员列表
        :rtype: list[dict]
        """

    @abc.abstractmethod
    def get_group_info(self, group_id: int) -> dict:
        """
        获取群信息

        :param group_id: 群ID
        :type group_id: int

        :return: 群信息（包含 group_id/group_name/member_count 等字段的 data dict）
        :rtype: dict
        """
        ...


class OneBotHttpServer(BaseOneBotServer):
    """
    OneBot HTTP 服务器接口实现。
    该类提供了与 OneBot HTTP 服务器交互的基本方法，包括获取登录信息、发送消息、获取用户和群组信息等。
    详情查看 https://docs.go-cqhttp.org/api

    :param host: 主机地址，格式为 "http://<ip>:<port>" 或 "https://<ip>:<port>"
    :type host: str

    :raises SendFailure: 发送消息失败时抛出
    """
    def __init__(self, host: IPvAnyAddress, port: int, token: str, **_):
        self._url = f'http://{host}:{port}'
        self._headers = {"Authorization": token}
        while True:
            try:
                self.login_id = self.get_login_info()['user_id']
            except (requests.ConnectionError, KeyError):
                LOG.WAR('Frame server connection failed, retrying...')
                time.sleep(1)
                continue
            break

    def delete_msg(self, message_id: int) -> None:
        requests.get(
            headers=self._headers,
            url=self._url + '/delete_msg',
            params={
                'message_id': message_id
            }
        )

    def get_login_info(self) -> dict:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_login_info'
        ).json()['data']

    def get_record(self, file_id: str) -> bytes:
        return base64.urlsafe_b64decode(
            requests.post(
                headers=self._headers,
                url=self._url + '/get_record',
                json={
                    'file_id': file_id,
                    'out_format': 'wav'
                }
            ).json()['data']['base64']
        )

    def get_msg(self, message_id: int) -> dict:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_msg',
            params={
                'message_id': message_id
            }
        ).json()['data']

    def send_group_msg(self, message) -> int:
        data = requests.post(
            headers=self._headers,
            url=self._url + '/send_group_msg',
            json={
                'group_id': message.target.id,
                'message': message.get_json()
            }
        ).json()
        if data['status'] == 'failed':
            error_message = data['message']
            if "\"result\": 110" in error_message:
                raise GroupNotJoined(message.target)
            raise SendFailure(data['message'], message)
        return data['data']['message_id']

    def send_private_msg(self, message) -> int:
        data = requests.post(
            headers=self._headers,
            url=self._url + '/send_private_msg',
            json={
                'user_id': message.target.id,
                'message': message.get_json()
            }
        ).json()
        if data['status'] == 'failed':
            error_message = data['message']
            if "无法获取用户信息" in error_message:
                raise PrivateChatFailed(message.target)
            raise SendFailure(data['message'], message)
        return data['data']['message_id']

    def get_stranger_info(self, id: int):
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_stranger_info',
            params={
                'user_id':  id
            }
        ).json()['data']

    def get_group_info(self, group_id: int) -> dict:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_group_info',
            params={
                'group_id':  group_id
            }
        ).json()['data']

    def set_friend_add_request(self, flag: str, approve: bool = True):
        return requests.get(
            headers=self._headers,
            url=self._url + '/set_friend_add_request',
            params={
                'flag': flag,
                'approve': approve
            }
        ).json()['data']

    def set_group_add_request(self, flag: str, approve: bool = True):
        return requests.get(
            headers=self._headers,
            url=self._url + '/set_group_add_request',
            params={
                'flag': flag,
                'approve': approve
            }
        ).json()['data']

    def get_friend_list(self) -> list:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_friend_list'
        ).json()['data']

    def get_group_list(self) -> list:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_group_list'
        ).json()['data']

    @dispatch
    def send_poke(self, user_id: int, group_id: int) -> None:
        requests.get(
            headers=self._headers,
            url=self._url + '/send_poke',
            params={
                'group_id': group_id,
                'user_id': user_id,
            }
        )

    @dispatch
    def send_poke(self, user_id: int) -> None:
        requests.get(
            headers=self._headers,
            url=self._url + '/send_poke',
            params={
                'user_id': user_id,
            }
        )

    def get_forward_msg(self, message_id: str) -> list[dict]:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_forward_msg',
            params={
                'message_id': message_id
            }
        ).json()['data'].get('messages', [])

    def get_group_member_list(self, group_id: int) -> list[dict]:
        return requests.get(
            headers=self._headers,
            url=self._url + '/get_group_member_list',
            params={
                'group_id': group_id
            }
        ).json()['data']


class OneBotWebsocketServer(BaseOneBotServer, WSManager):
    def __init__(self, host: IPvAnyAddress, port: int, token: str, **_):
        WSManager.__init__(self, f'ws://{host}:{port}/?access_token={token}')
        threading.Thread(target=self._receive_loop, daemon=True).start()
        self.login_id = self.get_login_info()['user_id']
    
    def delete_msg(self, message_id: int) -> None:
        self.send(
            'delete_msg',
            {'message_id': message_id}
        )

    def get_login_info(self) -> dict:
        return self.send('get_login_info')['data']

    def get_forward_msg(self, message_id: str) -> list[dict]:
        return self.send(
            'get_forward_msg',
            {'message_id': message_id}
        )['data'].get('messages', [])

    def get_record(self, file_id: str) -> bytes:
        return self.send(
            'get_record',
            {
                'file_id': file_id,
                'out_format': 'wav'
            }
        )['data']['base64']

    @dispatch
    def send_poke(self, user_id: int, group_id: int) -> None:
        self.send(
            'send_poke',
            {
                'group_id': group_id,
                'user_id': user_id
            }
        )

    @dispatch
    def send_poke(self, user_id: int) -> None:
        self.send(
            'send_poke',
            {
                'user_id': user_id
            }
        )

    def get_group_list(self) -> list:
        return self.send('get_group_list')['data']

    def set_group_add_request(self, flag: str, approve: bool = True):
        return self.send(
            'set_group_add_request',
            {
                'flag': flag,
                'approve': approve
            }
        )['data']

    def set_friend_add_request(self, flag: str, approve: bool = True):
        return self.send(
            'set_friend_add_request',
                {
                    'flag': flag,
                    'approve': approve
                }
        )['data']

    def get_friend_list(self) -> list:
        return self.send('get_friend_list')['data']
    
    def get_stranger_info(self, id: int) -> dict:
        return self.send(
            'get_stranger_info',
            {
                'user_id': id
            }
        )['data']
    
    def send_private_msg(self, message) -> int:
        data = self.send(
            'send_private_msg',
            {
                'user_id': message.target.id,
                'message': message.get_json()
            }
        )
        if data['status'] == 'failed':
            error_message = data['message']
            if "无法获取用户信息" in error_message:
                raise PrivateChatFailed(message.target)
            raise SendFailure(data['message'], message)
        return data['data']['message_id']
    
    def send_group_msg(self, message) -> int:
        data = self.send(
            'send_group_msg',
            {
                'group_id': message.target.id,
                'message': message.get_json()
            }
        )
        if data['status'] == 'failed':
            error_message = data['message']
            if "\"result\": 110" in error_message:
                raise GroupNotJoined(message.target)
            raise SendFailure(data['message'], message)
        return data['data']['message_id']
    
    def get_msg(self, message_id: int) -> dict:
        return self.send(
            'get_msg',
            {
                'message_id': message_id
            }
        )['data']

    def get_group_member_list(self, group_id: int) -> list[dict]:
        return self.send(
            'get_group_member_list',
            {
                'group_id': group_id
            }
        )['data']

    def get_group_info(self, group_id: int) -> dict:
        return self.send(
            'get_group_info',
            {
                'group_id': group_id
            }
        )['data']


class OneBotServer:
    def __new__(cls, mode: Literal['ws', 'http'], *args, **kwargs):
        match mode:
            case 'ws':
                return OneBotWebsocketServer(*args, **kwargs)
            case 'http':
                return OneBotHttpServer(*args, **kwargs)
            case others:
                raise ValueError(f'The mode {others} is not supported.')


LOG.INF('Loading Frame Server API...')
ONEBOT_SERVER = OneBotServer(**CONFIG.frame_server_config.model_dump())
LOG.INF(f'Frame Server API loaded on mode {CONFIG.frame_server_config.mode}')
