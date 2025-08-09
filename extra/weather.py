from abstract.bases.importer import datetime, time, itertools, io, pandas
from abstract.bases.importer import matplotlib, warnings
from PIL import Image
import matplotlib.pyplot
import matplotlib.dates

from abstract.apis.weather import WEATHER_API, WeatherAPI
from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.bases.log import LOG
from abstract.bases.exceptions import *
from abstract.session import Session


matplotlib.pyplot.rcParams["font.family"] = ["SimHei", "Microsoft YaHei"]
warnings.filterwarnings("ignore", message="This figure includes Axes that are not compatible with tight_layout")


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

    def get_weather_daily(self, session: Session) -> dict[str: tuple[time.struct_time] | tuple[int, int] | tuple[int] | tuple[str, bool]]:
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

    def get_weather_hourly(self, session: Session):
        """生成包含温度、湿度、降水概率和天气图标的折线图"""
        # 1. 准备数据
        # 解析天气数据并转换为可绘图格式
        hourly_data = self.api.get_weather_prediction(24, self.city_id, True, session)['hourly']

        # 提取需要的字段并转换数据类型
        data_list = []
        for item in hourly_data:
            # 时间格式转换：字符串 -> datetime
            fx_time = datetime.datetime.fromisoformat(item['fxTime'].replace('+08:00', ''))
            # 数值字段转换为float/int
            data_list.append({
                'fxTime': fx_time,
                'temp': float(item['temp']),         # 温度
                'humidity': float(item['humidity']),  # 湿度
                'pop': float(item['pop']),           # 降水概率
                'icon': int(item['icon'])            # 天气图标代码
            })

        # 转换为DataFrame便于处理
        data = pandas.DataFrame(data_list)

        if data.empty:
            raise ValueError("没有可用的天气数据")

        temp_data = data['temp']
        mean_temp = temp_data.mean()  # 平均值
        max_temp = temp_data.max()    # 最大值
        min_temp = temp_data.min()    # 最小值

        # 计算最大偏差（取最大值与平均值的差、平均值与最小值的差中的较大者）
        max_deviation = max(max_temp - mean_temp, mean_temp - min_temp)

        # 根据公式计算温度轴范围：平均值 ± (最大偏差 + 1)
        temp_upper = mean_temp + max_deviation + 1
        temp_lower = mean_temp - max_deviation - 1

        # 确保范围合理性（避免上下限相等或倒置）
        if temp_upper <= temp_lower:
            temp_upper = mean_temp + 1
            temp_lower = mean_temp - 1

        # 2. 创建画布和主轴（温度）
        fig, ax1 = matplotlib.pyplot.subplots(figsize=(16, 10))
        matplotlib.pyplot.subplots_adjust(top=0.85)  # 减少顶部空间占用（为图标预留位置）
        ax1.set_title(self.city_name, fontsize=14, pad=10)

        # 每1小时显示一个刻度（根据你的数据间隔调整，如30分钟用interval=30）
        ax1.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=1))
        ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H点'))

        # 3. 绘制温度折线（主纵轴）
        color1 = 'tab:red'
        ax1.set_xlabel('时间', fontsize=12, labelpad=10)
        ax1.set_ylabel('温度 (°C)', color=color1, fontsize=12, labelpad=10)
        ax1.plot(data['fxTime'], data['temp'], color=color1, marker='o',
                 linestyle='-', label='温度', linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.tick_params(axis='x', rotation=45)
        ax1.set_ylim(temp_lower, temp_upper)  # 固定温度最大值为50度（确保折线不会太高）
        for x, y in zip(data['fxTime'], data['temp']):
            ax1.text(
                x, y + 0.25,  # 位置：在数据点上方偏移0.5单位
                f'{y:.0f}°C',    # 显示温度值+单位
                color='tab:red',  # 与折线同色
                fontsize=9,
                ha='center'  # 水平居中对齐
            )

        # 4. 创建副纵轴（湿度和降水概率，共享x轴）
        color2 = 'tab:blue'
        ax2 = ax1.twinx()
        ax2.set_ylabel('湿度 / 降水概率 (%)', color=color2, fontsize=12, labelpad=10)
        ax2.plot(
            data['fxTime'], data['humidity'], color=color2, marker='s',
            linestyle='--', label='湿度', linewidth=2, alpha=0.7
        )
        for x, y in zip(data['fxTime'], data['humidity']):
            ax2.text(
                x, y - 3,    # 位置：在数据点下方偏移3单位（避免与折线重叠）
                f'{y:.0f}%',     # 显示湿度值+单位
                color='tab:blue',
                fontsize=9,
                ha='center'
            )
        ax2.plot(
            data['fxTime'], data['pop'], color='tab:green', marker='^',
            linestyle='-.', label='降水概率', linewidth=2, alpha=0.7
        )
        for x, y in zip(data['fxTime'], data['pop']):
            ax2.text(
                x, y - 3,    # 位置：在数据点上方偏移3单位
                f'{y:.0f}%',     # 显示降水概率+单位
                color='tab:green',
                fontsize=9,
                ha='center'
            )
        ax2.tick_params(axis='y', labelcolor=color2)
        ax2.set_ylim(0, 110)  # 固定湿度/降水概率最大值100%

        # 5. 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(
            lines1 + lines2, labels1 + labels2,
            loc='upper right',  # 图例移至右上角
            bbox_to_anchor=(1, 1.1),  # 微调图例位置
            fontsize=10
        )

        # 6. 添加天气图标（在每个时间点顶部）
        xlim = ax1.get_xlim()
        icon_y_pos = 0.84

        for idx, row in data.iterrows():
            # 获取图标并调整大小
            icon_bytes = self.api.get_icon(row['icon'])
            icon_img = Image.open(io.BytesIO(icon_bytes))
            x_pos = matplotlib.dates.date2num(row['fxTime'])

            # 图标尺寸缩小，避免占用过多空间
            ax_icon = fig.add_axes((
                (x_pos - xlim[0])/(xlim[1]-xlim[0])*0.91 + 0.023,  # x位置
                icon_y_pos,  # 下移后的y位置
                0.04,  # 宽度缩小为2.5%
                0.04   # 高度缩小为4%
            ), anchor='C')
            ax_icon.imshow(icon_img, interpolation='nearest')  # 保持图标清晰
            ax_icon.axis('off')
            icon_img.close()

        # 7. 设置标题和格式
        fig.suptitle('未来24小时天气趋势', fontsize=16, y=0.98)
        ax1.grid(True, linestyle='--', alpha=0.5)
        matplotlib.pyplot.tight_layout()

        # 8. 保存为二进制数据
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        png_binary = buffer.getvalue()

        # 清理资源
        buffer.close()
        matplotlib.pyplot.close(fig)

        return png_binary


LOG.INF('Loading weather modules...')

groups = set(itertools.chain(*GROUP_OPTION_TABLE.get_all('where city is not NULL', attr='city')))
weather_modules: dict[str: Weather] = {}
for city in groups:
    try:
        weather_modules[city] = Weather(city, WEATHER_API)
    except CityNotFound:
        LOG.WAR(Exception)
        GROUP_OPTION_TABLE.set('city', city, 'city', None)
        LOG.WAR(f'City {city} not found, removed from group options.')

LOG.INF('Weather modules loaded.')
