from pydantic import BaseModel, ConfigDict, model_validator, Field, FilePath
from pydantic_string_url import HttpUrl
from typing import Optional, Literal

from .importer import json, pathlib


class ConfiguredBaseModel(BaseModel):
        model_config = ConfigDict(
            frozen=True,
            extra='forbid',
            strict=True,
            str_strip_whitespace=True,
            validate_assignment=True,
            populate_by_name=True,
        )


class BaseConfig(ConfiguredBaseModel):
    @classmethod
    def load(cls, file: pathlib.Path | str):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls.model_validate(data)


class _Config(BaseConfig):
    class _FrameServerConfig(BaseModel):
        host: HttpUrl
        token: str

    class _SqlConfig(ConfiguredBaseModel):
        host: str
        user: str
        password: str
        database: str

    class _BotConfig(ConfiguredBaseModel):
        available_ids: list[int] = Field(min_length=1)
        must_at: bool = False
        command_prefixes: Optional[list[str]] = Field(default=None, min_length=1)
        operators: list[int] = Field(min_length=1)

    class _CommandsConfig(ConfiguredBaseModel):
        class _RandomPic(ConfiguredBaseModel):
            default_tags: str = 'tag=萝莉|少女&tag=白丝|黑丝'

        class _PicSearching(ConfiguredBaseModel):
            ascii2d_proxy: Optional[HttpUrl] = None

        class _ChatAIConfig(ConfiguredBaseModel):
            class _Character(ConfiguredBaseModel):
                class _Prompt(ConfiguredBaseModel):
                    role: Literal['system', 'assistant']
                    content: str

                vision: bool = False
                r18: bool = False
                prompts: list[_Prompt]

            api_key: Optional[str] = None
            base_url: Optional[HttpUrl] = None
            characters: dict[str, _Character] = Field(default_factory=dict)

            @model_validator(mode='after')
            def check_ai_config_consistency(self) -> '_Config._CommandsConfig._ChatAIConfig':
                # 判断各字段是否“有效”
                has_api_key = bool(self.api_key)  # 非空字符串
                has_base_url = self.base_url is not None
                has_characters = bool(self.characters)  # 非空字典

                # 三者有效状态必须相同：全 True 或全 False
                if not (has_api_key == has_base_url == has_characters):
                    raise ValueError(
                        'Either all of api_key, base_url, and characters must be provided (non-empty), '
                        'or all must be empty (api_key="", base_url=None, characters={}).'
                    )
                return self

        chat_ai: _ChatAIConfig = Field(default_factory=_ChatAIConfig)
        random_pic: _RandomPic = Field(default_factory=_RandomPic)
        pic_searching: _PicSearching = Field(default_factory=_PicSearching)

    frame_server_config: _FrameServerConfig
    sql_config: _SqlConfig
    bot_config: _BotConfig
    commands_configs: _CommandsConfig = Field(default_factory=_CommandsConfig)
    log_level: Literal['DEB', 'INF', 'WAR', 'ERR'] = 'INF'
    zh_font_path: FilePath = Field(default='C:/Windows/Fonts/msyh.ttc', strict=False)


CONFIG = _Config.load('./config.json')
