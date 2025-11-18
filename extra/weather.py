from abstract.bases.importer import abc, pathlib, cairosvg, io, requests
from PIL import Image

from config import CONFIG
from abstract.bases.log import LOG
from abstract.bases.exceptions import *


class WeatherAPI(abc.ABC):
    def __init__(self, api_key: str, api_host: str = "https://devapi.qweather.com"):
        """
        Initializes the QWeather client with the provided API key.

        :param api_key: Your QWeather API key.
        """
        self.api_key = api_key
        self.api_host = api_host

    @abc.abstractmethod
    def get_weather(self, location: str) -> dict:
        """
        Fetches the current weather data for a specific location.

        :param location: The location ID or name.

        :return: A dictionary containing the current weather data.
        """

    @abc.abstractmethod
    def get_weather_prediction(self, time: int, location: str, hourly: bool = False) -> dict:
        """
        Fetches weather predictions for a specific location.

        :param time: The number of days or hours for the forecast (3, 7, 10, 15, 30 for days; 24, 48, 72 for hours).
        :param location: The location ID or name.
        :param hourly: If True, fetches hourly predictions; otherwise, fetches daily predictions.

        :return: A dictionary containing the weather predictions.
        """

    @abc.abstractmethod
    def search_city(self, city_name: str) -> dict:
        """
        Searches for a city by name and returns its location ID.

        :param city_name: The name of the city to search for.

        :return: A dictionary containing the search results.
        """

    @abc.abstractmethod
    def get_icon(self, icon: int) -> bytes:
        """
        Fetches the weather icon image for a specific icon code.

        :param icon: The icon code representing the weather condition.

        :return: The binary content of the icon image(SVG).
        """


class QWeatherAPI(WeatherAPI):
    """
    A class to interact with the QWeather API for weather data.
    """

    def get_weather(self, location: str) -> dict:
        if not location.isdigit():
            location = self.search_city(location)['location'][0]['id']

        url = f"{self.api_host}/v7/weather/now"
        params = {
            'key': self.api_key,
            'location': location
        }

        return requests.get(url, params=params).json()

    def get_weather_prediction(self, time: int, location: str, hourly: bool = False) -> dict:
        if not location.isdigit():
            location = self.search_city(location)['location'][0]['id']

        url = f"{self.api_host}/v7/weather/{time}"
        if hourly:
            url += 'h'
            assert time in (24, 48, 72)
        else:
            url += 'd'
            assert time in (3, 7, 10, 15, 30)

        params = {
            'key': self.api_key,
            'location': location
        }

        return requests.get(url, params=params).json()

    def search_city(self, city_name: str) -> dict:
        url = f"{self.api_host}/geo/v2/city/lookup"
        params = {
            'key': self.api_key,
            'location': city_name
        }

        result = requests.get(url, params=params).json()
        if result.get('code') != '200':
            match result['error']['title'].upper():
                case 'NOT FOUND':
                    raise CityNotFound(city_name)
                case other:
                    LOG.WAR('Unsupported error title: ', other)
                    raise Exception(f"Error searching city: {result['error']['title']}")

        return result

    def get_icon(self, icon: int) -> bytes:
        try:
            # 1. 调用你的API获取SVG二进制数据（替换为实际API调用）
            svg_bytes = (
                    pathlib.Path().cwd() / 'abstract' / 'apis' / 'weather_icons' / f'{icon}.svg'
            ).read_bytes()

            # 2. 转换SVG为PNG
            png_bytes = cairosvg.svg2png(
                bytestring=svg_bytes,
                dpi=300,               # 保持高DPI
                output_width=200,      # 像素宽度（根据需要调整，如100-200）
                output_height=200      # 像素高度（与宽度一致，避免拉伸）
            )

            # 3. 转换为PIL图像
            return png_bytes

        except Exception as e:
            LOG.WAR(f"SVG处理失败: {e}")
            # 创建内存缓冲区
            buffer = io.BytesIO()
            try:
                # 将图像保存到缓冲区，格式为PNG
                Image.new('RGB', (30, 30), color='gray').save(buffer, format='PNG')

                # 将缓冲区指针移到开始位置，读取字节数据
                buffer.seek(0)
                png_bytes = buffer.getvalue()  # 默认图

                return png_bytes
            finally:
                # 确保缓冲区关闭，释放资源
                buffer.close()


LOG.INF('Loading weather API...')
WEATHER_API = QWeatherAPI(**CONFIG['weather_api'])
LOG.INF('Weather API loaded successfully.')
