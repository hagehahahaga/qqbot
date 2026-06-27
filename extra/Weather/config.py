import pathlib

from pydantic_string_url import HttpUrl

from abstract.bases.config import BaseConfig


class _Config(BaseConfig):
    api_host: HttpUrl
    api_key: str


CONFIG = _Config.load(pathlib.Path(__file__).parent / 'config.json')