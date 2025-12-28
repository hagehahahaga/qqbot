from abstract.bases.exceptions import CommandCancel
from abstract.bases.importer import threading, requests, functools

from abstract.bases.log import LOG
from config import CONFIG


class Speaker:
    TTS_URL = CONFIG.get('vits', {}).get('tts', '').removesuffix('/')
    SVC_URL = CONFIG.get('vits', {}).get('svc', '').removesuffix('/')
    TTS_LOCK = threading.Lock()
    SVC_LOCK = threading.Lock()

    def __init__(self, name: str, supports: dict[str, str]):
        self.name = name
        self.supports = supports

    @staticmethod
    def error_handler(type: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs) -> bytes:
                # 检查支持的功能类型
                assert type in self.supports, f'此Speaker不支持{type}功能.'
                
                try:
                    # 调用原始函数
                    response = func(self, *args, **kwargs)
                    
                    # 处理响应
                    assert response.status_code == 200, f'{self.name}服务端出错, 可能是参数问题.'
                    try:
                        json = response.json()
                        assert json['status'] == 0, f'{self.name}推理出错: {json["detail"]}'
                    except requests.JSONDecodeError:
                        pass
                    
                    assert response, f'{self.name}推理结果为空'
                    return response.content
                    
                except requests.ConnectionError as error:
                    LOG.WAR('无法连接VITS服务端.')
                    raise CommandCancel('无法连接VITS服务端. 多半是没开机.')
                except requests.JSONDecodeError as error:
                    LOG.WAR(f'{self.name}: vits主机信息无法解析.')
                    raise CommandCancel('vits主机信息无法解析.')

            return wrapper
        return decorator

    @error_handler('tts')
    def TTS(self, text: str):
        with self.TTS_LOCK:
            return requests.post(
                self.TTS_URL + '/voiceChangeModel',
                data={
                    'speaker': self.supports['tts'],
                    'text': text
                }
            )

    @error_handler('svc')
    def SVC(self, audio: bytes, pitch: float = None):
        with self.SVC_LOCK:
            return requests.post(
                self.SVC_URL + '/voiceChangeModel',
                files={
                    'audio': audio
                },
                data={
                    'speaker': self.supports['svc'],
                    'pitch': pitch
                }
            )


class SpeakerManager(dict):
    def __init__(self, speakers: dict[str, dict[str, str]]):
        super().__init__(
            {
                key: Speaker(key, value) for key, value in speakers.items()
            }
        )

    def __getitem__(self, item) -> Speaker:
        try:
            return super().__getitem__(item)
        except KeyError:
            raise CommandCancel(f'不存在的Speaker: {item}')


LOG.INF('Loading VITS speaker modules...')
SPEAKER_MANAGER: SpeakerManager[str, Speaker] = SpeakerManager(
    CONFIG.get("vits", {}).get("speakers", [])
)
LOG.INF(
    f'Loaded {len(SPEAKER_MANAGER)} VITS speaker modules:'
    f'{", ".join(SPEAKER_MANAGER.keys())}'
)
