from abstract.bases.importer import abc, requests, dispatch, base64

from abstract.bases.exceptions import *
from abstract.bases.config import CONFIG
from abstract.bases.log import LOG


class FrameServer(abc.ABC):
    def __init__(self, host: str, token: str):
        self.host = host.removesuffix('/')
        self.token = token

    @abc.abstractmethod
    def get_msg(self, message_id: int) -> dict: ...
    """
    获取消息
    
    :param message_id: 消息ID
    :type message_id: int
    
    :return: 消息内容
    """

    @abc.abstractmethod
    def send_group_msg(self, message) -> dict: ...
    """
    发送群消息
    
    :param message: 信息
    :type message: Base.GroupMessage
    
    :return: 消息目标
    :rtype: Base.Group
    """

    @abc.abstractmethod
    def send_private_msg(self, message) -> dict: ...
    """
    发送私聊消息
    
    :param message: 信息
    :type message: Base.PrivateMessage
    
    :return: 消息目标
    :rtype: Base.User
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
    def poke(self, user_id: int, group_id: int) -> None: ...
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
    def poke(self, user_id: int) -> None: ...
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
    def delete_message(self, message_id: int) -> None: ...
    """
    撤回消息
    
    :param message_id: 消息ID
    :type message_id: int
    """


class OneBotHttpServer(FrameServer):
    """
    OneBot HTTP 服务器接口实现。
    该类提供了与 OneBot HTTP 服务器交互的基本方法，包括获取登录信息、发送消息、获取用户和群组信息等。
    详情查看 https://docs.go-cqhttp.org/api

    :param host: 主机地址，格式为 "http://<ip>:<port>" 或 "https://<ip>:<port>"
    :type host: str

    :raises SendFailure: 发送消息失败时抛出
    """

    def delete_message(self, message_id: int) -> None:
        requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/delete_msg',
            params={
                'message_id': message_id
            }
        )

    def get_login_info(self) -> dict:
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_login_info'
        ).json()['data']

    def get_record(self, file_id: str) -> bytes:
        return base64.urlsafe_b64decode(
            requests.post(
                headers={"Authorization": self.token},
                url=self.host + '/get_record',
                json={
                    'file_id': file_id,
                    'out_format': 'wav'
                }
            ).json()['data']['base64']
        )

    def get_msg(self, message_id: int) -> dict:
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_msg',
            params={
                'message_id': message_id
            }
        ).json()['data']

    def send_group_msg(self, message) -> int:
        data = requests.post(
            headers={"Authorization": self.token},
            url=self.host + '/send_group_msg',
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
            headers={"Authorization": self.token},
            url=self.host + '/send_private_msg',
            json={
                'user_id': message.target.id,
                'message': message.get_json()
            }
        ).json()
        if not data['data']:
            raise SendFailure(data['message'], message)
        return data['data']['message_id']

    def get_stranger_info(self, id: int):
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_stranger_info',
            params={
                'user_id':  id
            }
        ).json()['data']

    def get_group_info(self, id: int):
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_group_info',
            params={
                'group_id':  id
            }
        ).json()['data']

    def set_friend_add_request(self, flag: str, approve: bool = True):
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/set_friend_add_request',
            params={
                'flag': flag,
                'approve': approve
            }
        ).json()['data']

    def set_group_add_request(self, flag: str, approve: bool = True):
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/set_group_add_request',
            params={
                'flag': flag,
                'approve': approve
            }
        ).json()['data']

    def get_friend_list(self) -> list:
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_friend_list'
        ).json()['data']

    def get_group_list(self) -> list:
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_group_list'
        ).json()['data']

    @dispatch
    def poke(self, user_id: int, group_id: int) -> None:
        requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/send_poke',
            params={
                'group_id': group_id,
                'user_id': user_id,
            }
        )

    @dispatch
    def poke(self, user_id: int) -> None:
        requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/send_poke',
            params={
                'user_id': user_id,
            }
        )

    def get_forward_msg(self, message_id: str) -> list[dict]:
        return requests.get(
            headers={"Authorization": self.token},
            url=self.host + '/get_forward_msg',
            params={
                'message_id': message_id
            }
        ).json()['data'].get('messages', [])


LOG.INF('Loading Frame Server API...')
FRAME_SERVER = OneBotHttpServer(**CONFIG['frame_server_config'])
LOG.INF(f'Frame Server API loaded: {FRAME_SERVER.host}')
