from abstract.bases.importer import abc

from config import CONFIG
from abstract.bases.log import LOG
from abstract.bases.exceptions import *
from abstract.bases.iterruptible_tasks.iterruptible_request import InterruptibleRequest


class WeatherAPI(abc.ABC):
    def __init__(self, api_key: str, api_host: str = "https://devapi.qweather.com"):
        """
        Initializes the QWeather client with the provided API key.

        :param api_key: Your QWeather API key.
        """
        self.api_key = api_key
        self.api_host = api_host

    @abc.abstractmethod
    def get_weather(self, location: str, session=None) -> dict: ...
    """
    Fetches the current weather data for a specific location.
    
    :param session: The session object for managing state.
    :type session: abstract.session.Session 
    :param location: The location ID or name.
    
    :return: A dictionary containing the current weather data.
    """

    @abc.abstractmethod
    def get_weather_prediction(self, days: str, location: str, hourly: bool = False, session=None) -> dict: ...
    """
    Fetches weather predictions for a specific location.
    
    :param session: The session object for managing state.
    :type session: abstract.session.Session
    :param days: The number of days or hours for the forecast (3, 7, 10, 15, 30 for days; 24, 48, 72 for hours).
    :param location: The location ID or name.
    :param hourly: If True, fetches hourly predictions; otherwise, fetches daily predictions.
    
    :return: A dictionary containing the weather predictions.
    """

    @abc.abstractmethod
    def search_city(self, city_name: str, session=None) -> dict: ...
    """
    Searches for a city by name and returns its location ID.
    
    :param session: The session object for managing state.
    :type session: abstract.session.Session
    :param city_name: The name of the city to search for.
    
    :return: A dictionary containing the search results.
    """


class QWeatherAPI(WeatherAPI):
    """
    A class to interact with the QWeather API for weather data.
    """

    def get_weather(self, location: str, session=None) -> dict:
        if not location.isdigit():
            location = self.search_city(location, session)['location'][0]['id']

        url = f"{self.api_host}/v7/weather/now"
        params = {
            'key': self.api_key,
            'location': location
        }

        return InterruptibleRequest(session).run(url, params=params).json()

    def get_weather_prediction(self, time: int, location: str, hourly: bool = False, session=None) -> dict:
        if not location.isdigit():
            location = self.search_city(location, session)['location'][0]['id']

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

        return InterruptibleRequest(session).run(url, params=params).json()

    def search_city(self, city_name: str, session=None) -> dict:
        url = f"{self.api_host}/geo/v2/city/lookup"
        params = {
            'key': self.api_key,
            'location': city_name
        }

        result = InterruptibleRequest(session).run(url, params=params).json()
        if result['code'] != '200':
            match result['title'].upper():
                case 'NOT FOUND':
                    raise CityNotFound(city_name)
                case other:
                    LOG.WAR('Unsupported error title: ', other)
                    raise Exception(f"Error searching city: {result['title']}")

        return result


LOG.INF('Loading weather API...')
WEATHER_API = QWeatherAPI(**CONFIG['weather_api'])
LOG.INF('Weather API loaded successfully.')
