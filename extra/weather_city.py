from abstract.bases.importer import datetime, time, itertools, io, pandas
from abstract.bases.importer import matplotlib
from PIL import Image
import matplotlib.pyplot
import matplotlib.dates
from typing import Optional, Callable, Dict, TypeVar, MutableMapping, Iterator, KeysView, ValuesView, ItemsView

from extra.weather import WEATHER_API, WeatherAPI
from abstract.apis.table import *
from abstract.bases.exceptions import *
from abstract.message import *
from abstract.bases.config import CONFIG

matplotlib.pyplot.rcParams["font.family"] = CONFIG['zh_font']


class WeatherCity:
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
        search_result = api.search_city(city)
        self.city_id = search_result['location'][0]['id']
        self.city_name = search_result['location'][0]['name']
        self.coo: tuple[float, float] = (
            float(search_result['location'][0]['lon']), float(search_result['location'][0]['lat'])
        )
        self.predicted = False
        self.cache = {}

    def flush_cache(self, function: Callable = None):
        if function is None:
            self.cache = {}
            return self
        
        # 获取方法名称，处理绑定方法
        method_name = function.__name__
        if method_name in self.cache:
            del self.cache[method_name]
        
        # 返回原函数，因为它已经是绑定方法，会自动传入 self
        return function

    def get_weather_day(self, delay = 0) -> dict[str, tuple[int, int] | tuple[str, str, bool] | tuple[int, str]]:
        """
        Fetches today's weather information including temperature, weather conditions, and UV index.
        {
        temp: (tuple): Minimum and maximum temperatures.
        weather: (tuple): Weather conditions for day and night, and whether it is raining.
        uv: (tuple): UV index and its description.
        }

        :return: A dictionary containing today's weather details.
        """
        if self.cache.get(self.get_weather_day.__name__) is None:
            response = self.api.get_weather_prediction(3, self.city_id)
            max_temp = int(response['daily'][delay]['tempMax'])
            min_temp = int(response['daily'][delay]['tempMin'])
            weather_day = response['daily'][delay]['textDay']
            weather_night = response['daily'][delay]['textNight']
            uv = int(response['daily'][delay]['uvIndex'])

            match uv:
                case _ if uv in range(0, 3):
                    uv_text = '最弱'
                case _ if uv in range(3, 5):
                    uv_text = '弱'
                case _ if uv in range(5, 7):
                    uv_text = '中等'
                case _ if uv in range(7, 10):
                    uv_text = '强'
                case _:
                    uv_text = '极强'

            self.cache[self.get_weather_day.__name__] = {
                'temp': (min_temp, max_temp),
                'weather': (weather_day, weather_night, '雨' in itertools.chain(*weather_day, *weather_night)),
                'uv': (uv, uv_text, uv >= 7)
            }

        return self.cache[self.get_weather_day.__name__]

    def get_weather_day_text(self, delay = 0):
        if self.cache.get(self.get_weather_day_text.__name__) is None:
            weather = self.get_weather_day(delay)
            match delay:
                case 0:
                    delay_text = '今日'
                case 1:
                    delay_text = '明天'
                case 2:
                    delay_text = '后天'
                case _:
                    delay_text = f'{delay}天后'

            self.cache[self.get_weather_day_text.__name__] = (
                    delay_text +
                    '天气:'
                    f'\n  城市: {self.city_name}'
                    f'\n  温度: {" - ".join(map(str, weather["temp"]))}℃'
                    f'\n  天气: 白天{weather["weather"][0]}, 晚上{weather["weather"][1]}'
                    f'\n  紫外线强度: {weather["uv"][1]}({weather["uv"][0]})' +
                    ('\n有雨, 出门注意带伞' if weather['weather'][2] else '') +
                    ('\n紫外线较强, 出门注意防晒' if weather['uv'][2] else '')
            )

        return self.cache[self.get_weather_day_text.__name__]

    def get_weather_now(self) -> dict[str, tuple[time.struct_time] | tuple[int, int] | tuple[int] | tuple[str, bool]]:
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
        if self.cache.get(self.get_weather_now.__name__) is None:
            response = self.api.get_weather(self.city_id)

            time_obs = datetime.datetime.fromisoformat(response['now']['obsTime']).timetuple()
            temp = int(response['now']['temp'])
            temp_feel = int(response['now']['feelsLike'])
            weather = response['now']['text']
            humidity = int(response['now']['humidity'])

            self.cache[self.get_weather_now.__name__] = {
                'time': (time_obs,),
                'temp': (temp, temp_feel),
                'weather': (weather, '雨' in weather),
                'humidity': (humidity,)
            }

        return self.cache[self.get_weather_now.__name__]

    def get_weather_now_text(self):
        if self.cache.get(self.get_weather_now_text.__name__) is None:
            weather = self.get_weather_now()
            self.cache[self.get_weather_now_text.__name__] = (
                    '现在天气'
                    f'\n  城市: {self.city_name}'
                    f'\n  数据时间: {time.strftime("%H时%M分%S秒", weather["time"][0])}'
                    f'\n  温度: {weather["temp"][0]}℃'
                    f'\n  体感温度: {weather["temp"][1]}℃'
                    f'\n  天气: {weather["weather"][0]}'
                    f'\n  湿度: {weather["humidity"][0]}%' +
                    ('\n现在有雨, 出门注意带伞' if weather['weather'][1] else '')
            )
        return self.cache[self.get_weather_now_text.__name__]

    @staticmethod
    def _parse_common_weather_data(raw_data: list, data_type: str) -> pandas.DataFrame:
        """
        通用天气数据解析函数（适配hourly/daily数据）
        :param raw_data: 原始接口数据（hourly/daily列表）
        :param data_type: 数据类型（'hourly'/'daily'）
        :return: 标准化DataFrame
        """
        if not raw_data:
            raise ValueError("没有可用的天气数据")

        data_list = []
        for item in raw_data:
            row = {}
            if data_type == 'hourly':
                # 24小时数据解析（复用原有逻辑，供原接口调用）
                row['time'] = datetime.datetime.fromisoformat(item['fxTime'].replace('+08:00', ''))
                row['temp'] = float(item['temp'])
                row['humidity'] = float(item['humidity'])
                row['pop'] = float(item['pop'])
                row['icon'] = int(item['icon'])
            elif data_type == 'daily':
                # 7天数据解析（新增逻辑）
                row['date'] = datetime.datetime.strptime(item['fxDate'], '%Y-%m-%d')
                row['temp_max'] = float(item['tempMax'])
                row['temp_min'] = float(item['tempMin'])
                row['humidity'] = float(item['humidity'])
                row['precip'] = float(item['precip'])
                row['uv_index'] = int(item['uvIndex']) if item['uvIndex'].strip() else 0
                row['icon_day'] = int(item['iconDay'])

            data_list.append(row)

        return pandas.DataFrame(data_list)

    @staticmethod
    def _get_uv_text(uv_index: int) -> str:
        """紫外线强度指数转文字描述（通用逻辑）"""
        match uv_index:
            case _ if uv_index in range(0, 3):
                return '最弱'
            case _ if uv_index in range(3, 5):
                return '弱'
            case _ if uv_index in range(5, 7):
                return '中等'
            case _ if uv_index in range(7, 10):
                return '强'
            case _:
                return '极强'

    @staticmethod
    def _add_weather_icon(
            fig: matplotlib.pyplot.Figure,
            ax: matplotlib.pyplot.Axes,
            raw_x_pos: float,  # 原始数据点的x坐标（如时间/日期的数值）
            xlim: tuple,  # 新增参数：x轴范围 (x_min, x_max)
            icon_y_pos: float,  # 新增参数：图标y轴位置
            icon_code: int,
            api
    ) -> None:
        """
        新增参数说明：
        - raw_x_pos：原始数据点的x坐标（如时间的数值化结果）
        - xlim：x轴的范围 (x_min, x_max)，用于计算相对位置
        - icon_y_pos：图标在y轴的固定位置
        """
        try:
            icon_bytes = api.get_icon(icon_code)
            icon_img = Image.open(io.BytesIO(icon_bytes))

            # 计算图标x轴的相对位置（核心公式，使用传入的xlim）
            adjusted_x_pos = (raw_x_pos - xlim[0]) / (xlim[1] - xlim[0]) * 0.91 + 0.023

            # 创建图标子图（使用新的位置和尺寸）
            ax_icon = fig.add_axes((
                adjusted_x_pos,  # 计算后的x位置
                icon_y_pos,  # 传入的y位置
                0.04,  # 宽度（缩小）
                0.04  # 高度（缩小）
            ), anchor='C')

            ax_icon.imshow(icon_img, interpolation='nearest')
            ax_icon.axis('off')
            icon_img.close()
        except Exception as e:
            LOG.WAR(f"加载天气图标失败：{e}")

    @staticmethod
    def _save_figure_to_binary(fig: matplotlib.pyplot.Figure) -> bytes:
        """通用图表保存为二进制函数（复用图片存储逻辑）"""
        buffer = io.BytesIO()
        fig.savefig(
            buffer,
            format='png',
            dpi=300,
            bbox_inches='tight',  # 改回官方支持的'tight'模式
            pad_inches=0.1
        )
        buffer.seek(0)
        png_binary = buffer.getvalue()
        buffer.close()
        matplotlib.pyplot.close(fig)
        return png_binary

    def get_weather_daily(self):
        """生成7天天气预报图表（包含图标、温湿度、降水量、紫外线）"""
        if self.cache.get(self.get_weather_daily.__name__) is None:
            # 1. 数据获取与解析（调用通用解析函数）
            raw_daily_data = self.api.get_weather_prediction(7, self.city_id, False)['daily']
            data = self._parse_common_weather_data(raw_daily_data, data_type='daily')

            # 2. 处理紫外线文字描述（调用通用转换函数）
            data['uv_text'] = data['uv_index'].apply(self._get_uv_text)

            # 3. 创建基础画布（复用布局逻辑，调整尺寸适配7天数据）
            fig, ax1 = matplotlib.pyplot.subplots(figsize=(14, 8))
            matplotlib.pyplot.subplots_adjust(top=0.85, bottom=0.15, left=0.08, right=0.92)

            # 设置标题
            ax1.set_title(self.city_name, fontsize=14, pad=10)
            fig.suptitle('未来24小时天气趋势', fontsize=16, y=0.98)
            ax1.set_xlabel('日期', fontsize=12, labelpad=10)
            ax1.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=1))
            ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d日'))

            # 4. 绘制主轴：温度范围（最高温/最低温）
            dates = data['date']  # 真实日期数据
            width = 0.35  # 柱状图宽度（天数）

            # 计算全局温度极值（含所有最高温和最低温）
            all_temps = pandas.concat([data['temp_max'], data['temp_min']])
            global_min = all_temps.min()  # 所有温度中的最小值（可能为负）
            global_max = all_temps.max()  # 所有温度中的最大值

            # 设置y轴范围（预留缓冲，确保所有温度都在范围内）
            buffer = 2  # 上下缓冲值（℃）
            ax1.set_ylim(
                bottom=global_min - buffer,  # 下限：比最低温度还低一点
                top=global_max + 5  # 上限：比最高温度高5℃（避免碰图标）
            )

            # 最高温（红色柱状）：从y轴下限向上延伸到最高温
            ax1.bar(
                dates + pandas.Timedelta(days=width / 2),  # 右偏位置
                height=data['temp_max'] - (global_min - buffer),  # 高度=最高温 - y轴下限（确保为正）
                bottom=global_min - buffer,  # 底部从y轴下限开始
                width=width,
                color='tab:red',
                alpha=0.7,
                label='最高温'
            )

            # 最低温（蓝色柱状）：从y轴下限向上延伸到最低温
            ax1.bar(
                dates - pandas.Timedelta(days=width / 2),  # 左偏位置
                height=data['temp_min'] - (global_min - buffer),  # 高度=最低温 - y轴下限（即使最低温为负，此处也为正）
                bottom=global_min - buffer,  # 底部从y轴下限开始
                width=width,
                color='tab:blue',
                alpha=0.7,
                label='最低温'
            )

            # 温度数值标注
            for i, (max_t, min_t) in enumerate(zip(data['temp_max'], data['temp_min'])):
                ax1.text(dates[i] + pandas.Timedelta(days=width / 2), max_t + 0.3, f'{max_t:.0f}°C', ha='center',
                         fontsize=9, color='tab:red')
                ax1.text(dates[i] - pandas.Timedelta(days=width / 2), min_t + 0.3, f'{min_t:.0f}°C', ha='center',
                         fontsize=9, color='tab:blue')

            # 5. 创建副轴1：湿度（折线图）
            ax2 = ax1.twinx()
            ax2.plot(dates, data['humidity'], color='tab:green', marker='s',
                     linestyle='-', linewidth=2, label='湿度', alpha=0.8)
            ax2.set_ylabel('湿度 (%) / 降水量 (mm)', fontsize=12, labelpad=10)
            ax2.tick_params(axis='y', labelcolor='tab:green')
            ax2.set_ylim(0, 110)  # 湿度最大100%

            # 湿度数值标注
            for i, hum in enumerate(data['humidity']):
                ax2.text(dates[i], hum + 3, f'{hum:.0f}%', ha='center', fontsize=9, color='tab:green')

            # 6. 创建副轴2：降水量（柱状图）
            ax3 = ax1.twinx()
            ax3.spines['right'].set_position(('outward', 60))  # 偏移避免与ax2重叠
            ax3.bar(dates, data['precip'], width=0.2, color='tab:cyan', alpha=0.6, label='降水量')
            ax3.tick_params(axis='y', labelcolor='tab:cyan')
            ax3.set_ylim(0, max(data['precip'].max() * 1.5, 5))  # 适配无降水场景

            # 降水量数值标注（无降水显示"无"）
            for i, prec in enumerate(data['precip']):
                text = f'{prec:.1f}mm' if prec > 0 else '无'
                ax3.text(
                    dates[i],
                    prec + 0.1,
                    text,
                    ha='center',
                    fontsize=13,
                    color='tab:cyan',
                    path_effects=[
                        matplotlib.patheffects.Stroke(linewidth=1.5, foreground='black'),  # 黑色边框
                        matplotlib.patheffects.Normal()  # 原始文字颜色
                    ]
                )

            # 7. 添加紫外线强度标注（文本形式）
            # 先获取y轴范围（确保在绘制完温度柱后获取，此时y轴范围已确定）
            ylim = ax1.get_ylim()  # 格式：(y_min, y_max)，包含所有温度的范围
            # 计算紫外线标注的基础位置（占y轴总高度的70%，可根据需要调整）
            # 确保在柱子上方且远离顶部图标（假设图标在85%高度以上）
            uv_base_ratio = 0.7  # 基础比例（70%高度）
            uv_text_offset = 0.05  # 文字间的垂直偏移比例

            # 计算具体y坐标
            uv_label_y = ylim[0] + (ylim[1] - ylim[0]) * uv_base_ratio  # “紫外线”文字位置
            uv_value_y = ylim[0] + (ylim[1] - ylim[0]) * (uv_base_ratio - uv_text_offset)  # 强度文字位置

            for i, (uv_text, uv_idx) in enumerate(zip(data['uv_text'], data['uv_index'])):
                # 根据紫外线强度设置文字颜色
                color = 'green' if uv_idx < 3 else 'orange' if uv_idx < 7 else 'red'

                # 强度文字（如“中等”“强”）
                ax1.text(
                    dates[i], uv_value_y, uv_text,
                    ha='center', fontsize=13, color=color, fontweight='bold'
                )
                # “紫外线”标签文字
                ax1.text(
                    dates[i], uv_label_y, f'紫外线',
                    ha='center', fontsize=13, color=color, fontweight='bold'
                )

            # 8. 添加天气图标（调用通用图标函数）
            # 1. 获取x轴范围和图标y位置（在绘制图标前定义）
            xlim = ax1.get_xlim()  # x轴范围 (x_min, x_max)
            icon_y_pos = 0.80  # 图标y轴位置（可根据图表调整）

            # 使用真实日期作为x轴位置
            for i, (date, icon_code) in enumerate(zip(data['date'], data['icon_day'])):
                raw_x_pos = dates[i]  # 使用真实日期
                self._add_weather_icon(
                    fig=fig,
                    ax=ax1,
                    raw_x_pos=raw_x_pos,
                    xlim=xlim,
                    icon_y_pos=icon_y_pos,
                    icon_code=icon_code,
                    api=self.api
                )

            # 9. 合并图例（适配三个轴的图例）
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            lines3, labels3 = ax3.get_legend_handles_labels()
            ax1.legend(
                lines1 + lines2 + lines3,
                labels1 + labels2 + labels3,
                loc='upper right',  # 锚点为右上角
                bbox_to_anchor=(1.05, 1.2),  # 向右偏移5%，向上偏移20%（完全在图像外上方）
                fontsize=10,
                ncol=1
            )

            # 10. 保存为二进制（调用通用保存函数）
            self.cache[self.get_weather_daily.__name__] = self._save_figure_to_binary(fig)
        return self.cache[self.get_weather_daily.__name__]

    def get_weather_hourly(self):
        """生成包含温度、湿度、降水概率和天气图标的24小时折线图（降冗版）"""
        if self.cache.get(self.get_weather_hourly.__name__) is None:
            # 1. 数据获取与解析（复用通用解析函数）
            hourly_raw_data = self.api.get_weather_prediction(24, self.city_id, True)['hourly']
            data = self._parse_common_weather_data(hourly_raw_data, data_type='hourly')

            # 2. 温度轴范围计算（保留原逻辑，适配小时级数据）
            temp_data = data['temp']
            mean_temp = temp_data.mean()
            max_temp = temp_data.max()
            min_temp = temp_data.min()
            max_deviation = max(max_temp - mean_temp, mean_temp - min_temp)
            temp_upper = mean_temp + max_deviation + 1
            temp_lower = mean_temp - max_deviation - 1

            # 确保温度轴范围合理
            if temp_upper <= temp_lower:
                temp_upper = mean_temp + 1
                temp_lower = mean_temp - 1

            # 3. 创建画布和主轴（保留原布局，复用通用样式逻辑）
            fig, ax1 = matplotlib.pyplot.subplots(figsize=(16, 10))
            matplotlib.pyplot.subplots_adjust(top=0.85)
            ax1.set_title(self.city_name, fontsize=14, pad=10)

            # 小时级时间刻度设置
            ax1.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=1))
            ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H点'))

            # 4. 绘制温度折线（主纵轴，保留原样式）
            color1 = 'tab:red'
            ax1.set_xlabel('时间', fontsize=12, labelpad=10)
            ax1.set_ylabel('温度 (°C)', color=color1, fontsize=12, labelpad=10)
            ax1.plot(data['time'], data['temp'], color=color1, marker='o',
                     linestyle='-', label='温度', linewidth=2)
            ax1.tick_params(axis='y', labelcolor=color1)
            ax1.set_ylim(temp_lower, temp_upper)

            # 温度数值标注（保留原偏移逻辑）
            for i, (x, y) in enumerate(zip(data['time'], data['temp'])):
                prev_diff = data['temp'][i - 1] - y if i > 0 else 0
                next_diff = data['temp'][i + 1] - y if i < len(data['temp']) - 1 else 0
                offset = max(prev_diff, next_diff)
                ax1.text(
                    x, y + (0.125 if offset == 0 else offset / 3),
                    f'{y:.0f}°C', color=color1, fontsize=9, ha='center'
                )

            # 5. 创建副纵轴（湿度和降水概率，保留原逻辑）
            color2 = 'tab:blue'
            ax2 = ax1.twinx()
            ax2.set_ylabel('湿度 / 降水概率 (%)', color=color2, fontsize=12, labelpad=10)

            # 湿度折线
            ax2.plot(
                data['time'], data['humidity'], color=color2, marker='s',
                linestyle='--', label='湿度', linewidth=2, alpha=0.7
            )
            for x, y in zip(data['time'], data['humidity']):
                ax2.text(x, y + 3, f'{y:.0f}%', color=color2, fontsize=9, ha='center')

            # 降水概率折线
            ax2.plot(
                data['time'], data['pop'], color='tab:green', marker='^',
                linestyle='-.', label='降水概率', linewidth=2, alpha=0.7
            )
            for x, y in zip(data['time'], data['pop']):
                ax2.text(x, y + 3, f'{y:.0f}%', color='tab:green', fontsize=9, ha='center')

            ax2.tick_params(axis='y', labelcolor=color2)
            ax2.set_ylim(0, 110)

            # 6. 合并图例（保留原位置）
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(
                lines1 + lines2, labels1 + labels2,
                loc='upper right', bbox_to_anchor=(1, 1.1), fontsize=10
            )

            # 7. 添加天气图标（复用通用图标函数）
            # 1. 获取x轴范围和图标y位置（在绘制图标前定义）
            xlim = ax1.get_xlim()  # x轴范围 (x_min, x_max)
            icon_y_pos = 0.82  # 图标y轴位置（可根据图表调整）

            # 2. 遍历数据，调用修改后的_add_weather_icon
            for i, (time, icon_code) in enumerate(zip(data['time'], data['icon'])):
                # 原始x坐标（日期的索引，或日期的数值化结果）
                raw_x_pos = matplotlib.dates.date2num(time)  # 7天预报用索引作为原始x坐标（更简单）

                # 传递所有必要参数
                self._add_weather_icon(
                    fig=fig,
                    ax=ax1,
                    raw_x_pos=raw_x_pos,  # 原始x坐标（索引i）
                    xlim=xlim,  # 传递x轴范围
                    icon_y_pos=icon_y_pos,  # 传递y位置
                    icon_code=icon_code,
                    api=self.api
                )

            # 8. 图表格式美化（保留原设置）
            fig.suptitle('未来24小时天气趋势', fontsize=16, y=0.98)
            ax1.grid(True, linestyle='--', alpha=0.5)
            matplotlib.pyplot.tight_layout()

            # 9. 保存为二进制（复用通用保存函数）
            self.cache[self.get_weather_hourly.__name__] = self._save_figure_to_binary(fig)
        return self.cache[self.get_weather_hourly.__name__]

    def get_minutely_rain_change(self) -> Optional[str]:
        """
        获取未来30分钟内的降水情况变化
        
        该方法检查未来30分钟内的降水情况是否会发生变化。
        如果30分钟内降水情况有改变，返回描述变化的字符串；
        否则返回None。
        
        :return: 描述降水变化的字符串，或None表示无变化
        """
        if self.cache.get(self.get_minutely_rain_change.__name__) is None:
            # 获取分钟级预报数据
            response = self.api.get_weather_prediction_minutely(self.coo)
            translation = {'snow': '下雪', 'rain': '下雨'}
            
            # 将当前时间转换为带时区的datetime对象（UTC）
            now = datetime.datetime.now(datetime.timezone.utc)
            # 计算30分钟后的时间
            future_time = now + datetime.timedelta(minutes=30)
            
            # 解析API返回的时间，并过滤出30分钟内的预报
            predicts: list[dict['str', datetime.datetime | str | None]] = []
            for predict in response['minutely']:
                fx_time = datetime.datetime.fromisoformat(predict['fxTime'])
                # 只保留未来30分钟内的预报
                if now <= fx_time <= future_time:
                    predicts.append({
                        'fxTime': fx_time,
                        'status': translation[predict['type']] if predict['precip'] else None
                    })

            if not predicts:
                LOG.WAR(f"No valid minutely rain data available for city {self.city_name}")
                return None

            nearest_status = predicts[0]['status']
            for predict in predicts:
                if predict['status'] != nearest_status:
                    predicted_data = predict
                    break
            else:
                return

            output = '根据天气预报, '
            if predicted_data['status'] != self.predicted:
                output += '刚才预报有误, '
            self.predicted = predicted_data['status']
            # 计算时间差（分钟）
            time_diff = int((predicted_data['fxTime'] - now).total_seconds() / 60)
            output += f'约{time_diff}分钟后将会'
            output += ('停止' + nearest_status) if predicted_data['status'] is None else predicted_data['status']
            self.cache[self.get_minutely_rain_change.__name__] = output + '.'
        return self.cache[self.get_minutely_rain_change.__name__]

class WeatherCityManager(MutableMapping[str, 'WeatherCity']):
    """
    城市天气管理器，键为城市名，值为WeatherCity对象
    
    A manager class for handling multiple WeatherCity instances.
    It allows easy access to weather data for different cities.
    """
    
    def __init__(self):
        self._data: dict[str, 'WeatherCity'] = {}
    
    def __setitem__(self, key: str, value: 'WeatherCity') -> None:
        """Set a WeatherCity instance for a city."""
        self._data[key] = value
    
    def __getitem__(self, item: str) -> 'WeatherCity':
        """Get the WeatherCity instance for the specified city."""
        if item not in self._data:
            self._data[item] = WeatherCity(item)
        return self._data[item]
    
    def __delitem__(self, key: str) -> None:
        """Delete a WeatherCity instance for a city."""
        del self._data[key]
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over city names."""
        return iter(self._data)
    
    def __len__(self) -> int:
        """Get the number of cities."""
        return len(self._data)
    
    def keys(self) -> KeysView[str]:
        """Get all city names."""
        return self._data.keys()
    
    def values(self) -> ValuesView[WeatherCity]:
        """Get all WeatherCity instances."""
        return self._data.values()
    
    def items(self) -> ItemsView[str, WeatherCity]:
        """Get all (city, WeatherCity) pairs."""
        return self._data.items()
    
    def get(self, key: str, default: WeatherCity = None) -> WeatherCity:
        """Get the WeatherCity instance for the specified city, or default if not found."""
        if key not in self._data:
            if default is not None:
                return default
            self._data[key] = WeatherCity(key)
        return self._data[key]


LOG.INF('Loading weather modules...')

_groups = set(itertools.chain(*GROUP_OPTION_TABLE.get_all('where city is not NULL', attr='city')))
WEATHER_CITY_MANAGER = WeatherCityManager()
for city in _groups:
    try:
        WEATHER_CITY_MANAGER[city] = WeatherCity(city)
    except CityNotFound:
        for id, city in GROUP_OPTION_TABLE.get_all('where city is not NULL', attr='id, city'):
            id = int(id)
            GroupMessage(
                f'未能找到此群默认城市 {city}, 已重置天气选项.',
                Group(id)
            ).send()
        GROUP_OPTION_TABLE.set('city', city, 'weather_notice', 0)
        GROUP_OPTION_TABLE.set('city', city, 'city', None)
        LOG.WAR(f'City {city} not found, reset weather option of groups.')

LOG.INF(
    'Loaded Weather modules:\n' +
    ',\n'.join(WEATHER_CITY_MANAGER)
)
