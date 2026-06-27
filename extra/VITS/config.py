import pathlib
from pydantic_string_url import HttpUrl

from abstract.bases.config import BaseConfig, ConfiguredBaseModel


class _Config(BaseConfig):
    class _Speaker(ConfiguredBaseModel):
        tts_name: str
        svc_name: str
    tts_url: HttpUrl
    svc_url: HttpUrl
    speakers: dict[str, _Speaker]


CONFIG = _Config.load(pathlib.Path(__file__).parent / 'config.json')
