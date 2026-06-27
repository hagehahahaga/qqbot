from .importer import matplotlib, PIL
from .config import CONFIG


# 系统自带字体路径
sys_font_path = CONFIG.zh_font_path

# 1. 注册系统字体（matplotlib 会识别该文件）
matplotlib.font_manager.FontManager().addfont(sys_font_path)

# 2. 全局设置（后续所有图表无需再指定字体）
matplotlib.pyplot.rcParams["font.family"] = matplotlib.font_manager.FontProperties(fname=sys_font_path).get_name()

PIL_FONT = PIL.ImageFont.truetype(sys_font_path, 16)