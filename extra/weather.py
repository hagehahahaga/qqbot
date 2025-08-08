from abstract.bases.importer import datetime, time, itertools

from abstract.apis.weather import WEATHER_API, WeatherAPI
from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.bases.log import LOG
from abstract.bases.exceptions import *
from abstract.session import Session


class Weather:
    """
    A class to fetch and manage weather information for a specified city using the WeatherAPI.
    It provides methods to retrieve today's weather and current weather conditions.

    Attributes:
        api (WeatherAPI): An instance of the WeatherAPI to interact with the weather service.
        city_id (int): The unique identifier for the specified city.
    Methods:
        today_weather() -> dict: Fetches today's weather information including temperature, weather conditions, and UV index.
        get_weather() -> dict: Fetches the current weather information including temperature, humidity, weather conditions, and rain status.
    """
    def __init__(self, city: str | int, api: WeatherAPI = WEATHER_API):
        self.api = api
        self.city_id = api.search_city(city)['location'][0]['id'] if isinstance(city, str) else city

        self.city_name = api.search_city(self.city_id)['location'][0]['name']

    def today_weather(self, session) -> dict[str: tuple[int, int] | tuple[str, str, bool] | tuple[int, str]]:
        """
        Fetches today's weather information including temperature, weather conditions, and UV index.
        {
        temp: (tuple): Minimum and maximum temperatures.
        weather: (tuple): Weather conditions for day and night, and whether it is raining.
        uv: (tuple): UV index and its description.
        }

        :return: A dictionary containing today's weather details.
        """
        response = self.api.get_weather(self.city_id, session)
        max_temp = int(response['daily'][0]['tempMax'])
        min_temp = int(response['daily'][0]['tempMin'])
        weather_day = response['daily'][0]['textDay']
        weather_night = response['daily'][0]['textNight']
        uv = int(response['daily'][0]['uvIndex'])

        rain = '雨' in weather_night or '雨' in weather_day
        match uv:
            case range(0, 3):
                uv_text = '最弱'
            case range(3, 5):
                uv_text = '弱'
            case range(5, 7):
                uv_text = '中等'
            case range(7, 10):
                uv_text = '强'
            case _:
                uv_text = '极强'

        return {
            'temp': (min_temp, max_temp),
            'weather': (weather_day, weather_night, rain),
            'uv': (uv, uv_text)
        }

    def get_weather(self, session: Session) -> dict[str: tuple[time.struct_time] | tuple[int, int] | tuple[int] | tuple[str, bool]]:
        """
        Fetches the current weather information including temperature, humidity, weather conditions, and rain status.
        {
        time: (tuple): Current time in a structured format.
        temp: (tuple): Current temperature and feels like temperature.
        humidity: (tuple): Current humidity percentage.
        weather: (tuple): Current weather condition and whether it is raining.
        }

        :return: A dictionary containing current weather details.
        """
        response = self.api.get_weather(self.city_id, session)

        time_obs = datetime.datetime.fromisoformat(response['now']['obsTime']).timetuple()
        temp = int(response['now']['temp'])
        temp_feel = int(response['now']['feelsLike'])
        weather = response['now']['text']
        humidity = int(response['now']['humidity'])

        rain = '雨' in weather

        return {
            'time': (time_obs, ),
            'temp': (temp, temp_feel),
            'weather': (weather, rain),
            'humidity': (humidity, )
        }


LOG.INF('Loading weather modules...')

groups = set(itertools.chain(*GROUP_OPTION_TABLE.get_all('where city is not NULL', attr='city')))
weather_modules = {}
for city in groups:
    try:
        weather_modules[city] = Weather(city, WEATHER_API)
    except CityNotFound:
        LOG.WAR(Exception)
        GROUP_OPTION_TABLE.set('city', city, 'city', None)
        LOG.WAR(f'City {city} not found, removed from group options.')

LOG.INF('Weather modules loaded.')
