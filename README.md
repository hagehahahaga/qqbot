# QQ机器人项目

这是一个功能丰富的Python QQ机器人项目，基于无头NapCatQQ框架，使用Onebot协议进行通信。

## 功能特性

### 核心功能
- **命令系统**：支持多种命令，如搜索、随机图片、天气查询等
- **服务系统**：提供定时提醒、天气预测等服务
- **游戏系统**：实现了井字棋、五子棋等游戏
- **触发器系统**：支持自动触发功能，如机厅人数查询
- **Web界面**：提供服务状态监控和实时日志查看
- **经济系统**：基于"韭菜盒子"的经济体系，支持签到、彩票、股票交易等

### 特色功能
- **AI集成**：支持AI对话、语音合成、变音服务
- **天气服务**：提供实时天气、逐小时预报、每日预报、未来30分钟降水预报
- **搜图功能**：支持多API同时搜索，包括Ascii2d、SauceNAO、百度、Yandex等
- **机厅管理**：支持机厅添加、删除、别名管理和人数统计
- **提醒系统**：支持定时提醒，可设置每天/每周重复
- **幻影坦克**：生成幻影坦克图片

## 项目结构

```
├── abstract/           # 核心抽象层
│   ├── apis/           # API实现
│   ├── bases/          # 基础组件
│   ├── bot.py          # 机器人核心类
│   ├── command.py      # 命令系统
│   ├── message.py      # 消息处理
│   ├── service.py      # 服务系统
│   ├── session.py      # 会话管理
│   └── target.py       # 目标对象
├── extra/              # 额外功能
│   ├── say/            # 语音文件
│   ├── chat_ai.py      # AI对话
│   ├── vits_speaker.py # 语音合成
│   ├── weather.py      # 天气服务
│   └── weather_city.py # 城市管理
├── web/                # Web界面
├── main.py             # 主入口
├── commands.py         # 命令实现
├── services.py         # 服务实现
├── games.py            # 游戏实现
├── triggers.py         # 触发器实现
├── config_default.json # 默认配置
├── help_text.json      # 帮助文档
├── init.sql            # 数据库初始化脚本
├── requirements.txt    # 依赖文件
└── README.md           # 项目说明
```

## 安装部署

### 环境要求
- Python 3.8+
- MySQL/MariaDB
- 无头NapCatQQ

### 安装步骤
1. 克隆项目代码
2. 安装依赖：`pip install -r requirements.txt`
3. 配置数据库：导入`init.sql`文件到MySQL/MariaDB
4. 配置机器人：复制`config_default.json`为`config.json`并填写相关配置
5. 启动无头NapCatQQ框架
6. 启动机器人：`python main.py`

## 配置说明

### 配置文件结构

配置文件使用JSON格式，主要包含以下配置项：

### 1. 核心配置

#### frame_server_config
```json
"frame_server_config": {
  "host": "",
  "token": ""
}
```
- **用途**：配置FrameServer连接信息
- **使用位置**：`abstract/apis/frame_server.py` - 初始化OneBotHttpServer
- **说明**：`host`是FrameServer的地址，`token`是认证令牌

#### sql_config
```json
"sql_config": {
  "host": "",
  "user": "",
  "password": "",
  "database": ""
}
```
- **用途**：配置数据库连接信息
- **使用位置**：`abstract/apis/table.py` - 建立数据库连接
- **说明**：用于连接MariaDB数据库，存储用户数据、游戏数据等

#### bot_config
```json
"bot_config": {
  "id": 0,
  "must_at": false,
  "command_prefixes": [""],
  "operators": [0]
}
```
- **用途**：配置机器人基本信息
- **使用位置**：
  - `abstract/bot.py` - 初始化Bot实例
  - `abstract/message.py` - 构造消息对象
  - `abstract/game.py` - 游戏验证
- **说明**：
  - `id`：机器人的QQ号
  - `must_at`：是否需要@机器人才能触发命令
  - `command_prefixes`：命令前缀列表
  - `operators`：操作员QQ号列表，拥有最高权限

### 2. 功能配置

#### commands_configs
```json
"commands_configs": {
  "random_pic": {
    "default_tags": ""
  }
}
```
- **用途**：配置命令相关参数
- **说明**：目前主要用于配置随机图片的默认标签

#### lottery_pool
```json
"lottery_pool": 0
```
- **用途**：配置彩票奖池大小
- **使用位置**：`commands.py` - 彩票系统
- **说明**：初始奖池大小，随着彩票购买和中奖动态变化

#### next_lottery_time
```json
"next_lottery_time": "00000000000000"
```
- **用途**：配置下一次彩票时间
- **使用位置**：`commands.py` - 彩票系统
- **说明**：格式为"年月日时分秒"，当奖池为空时设置

#### log_level
```json
"log_level": "INF"
```
- **用途**：配置日志级别
- **说明**：可选值包括DEBUG、INF、WAR、ERR等

#### zh_font_path
```json
"zh_font_path": "C:/Windows/Fonts/msyh.ttc"
```
- **用途**：配置中文字体路径
- **使用位置**：`abstract/bases/text2img.py` - 文本转图片
- **说明**：用于生成包含中文的图片，如帮助信息、版本信息等

### 3. API配置

#### ai
```json
"ai": {
  "api_key": "",
  "base_url": "",
  "characters": {
    "": {
      "vision": false,
      "r18": false,
      "prompts": [
        {
          "role": "system",
          "content": ""
        }
      ]
    }
  }
}
```
- **用途**：配置AI相关参数
- **使用位置**：`extra/chat_ai.py` - 初始化AI客户端
- **说明**：
  - `api_key`：AI服务的API密钥
  - `base_url`：AI服务的基础URL
  - `characters`：AI角色配置，每个角色包含：
    - `vision`：是否支持视觉能力
    - `r18`：是否包含R18内容（如果为True，只能在r18设置大于0的群聊中使用）
    - `prompts`：系统提示列表，用于定义AI角色的行为和个性

#### vits_url
```json
"vits_url": {
  "tts": "",
  "svc": "",
  "speakers": {
    "": {
      "tts": "",
      "svc": ""
    }
  }
}
```
- **用途**：配置语音合成相关参数
- **说明**：用于AI语音合成和变音服务

#### weather_api
```json
"weather_api": {
  "api_host": "",
  "api_key": ""
}
```
- **用途**：配置天气API参数
- **使用位置**：`extra/weather.py` - 初始化天气API客户端
- **说明**：用于获取天气数据，提供天气查询服务

## 使用方法

### 命令格式
- 群聊中：`@机器人 命令 参数`
- 私聊中：`命令 参数`

### 常用命令
- `help`：查看命令列表，默认以图片格式显示
- `help <命令>`：查看特定命令的帮助
- `help <命令> -detail`：以文本格式显示详细帮助
- `sign`：签到获取韭菜盒子，每天随机获得5-14个
- `weather [城市名] [类型]`：查询天气，类型包括now/hourly/daily/today/tomorrow/minutely
- `random [标签]`：获取随机图片，标签格式参照api.lolicon.app
- `game start <游戏> @玩家...`：开始游戏，支持井字棋、五子棋
- `arcade list`：查看机厅列表
- `search`：搜图功能，支持多API同时搜索
- `compress`：一键电子包浆，降低图片质量
- `points`：查询你的韭菜盒子数量
- `transfer @收款人 <数量>`：转账韭菜盒子
- `lottery`：5个韭菜盒子购买一个彩票
- `say`：随机播放电棍语录
- `chat <character> <message>`：与AI对话
- `phantom`：生成幻影坦克图片
- `tts <speaker> <text>`：AI语音合成
- `svc <speaker> [pitch]`：AI变音，需附带语音消息
- `forge`：伪造聊天记录，交互式命令
- `notice status`：查询当前进行中的定时提醒
- `notice add [--time=] [--text=] [--every=]`：添加定时提醒
- `stock status`：查询个人状态以及股市状态
- `stock buy/sell <price> <num>`：发起股票交易
- `stock cancel`：取消委托中的交易

### 服务管理
- `service status`：查看服务状态
- `service start <服务>`：启动服务
- `service stop <服务>`：停止服务
- `service restart <服务>`：重启服务
- `service option <服务> <属性> <值>`：设置服务属性

### 服务列表
- `noticer`：提醒服务，处理定时提醒
- `weather_predictor_hourly`：每小时天气预测服务
- `weather_predictor_daily`：每日天气预测服务
- `weather_predictor_minutely`：分钟级降水预报服务
- `weather_predictor_weekly`：每周天气预测服务
- `weather_today`：今日天气提醒服务

## 经济系统

### 股票交易
- `stock status`：查询个人状态以及股市状态
- `stock buy <price> <num>`：买入股票
- `stock sell <price> <num>`：卖出股票
- `stock cancel`：取消委托中的交易

### 韭菜盒子获取方式
- **签到**：每天签到随机获得5-14个韭菜盒子
- **彩票**：5个韭菜盒子购买一张彩票，有机会获得更多韭菜盒子
- **股票交易**：通过股票买卖赚取韭菜盒子
- **转账**：其他用户转账给你

### 韭菜盒子使用方式
- **搜索图片**：每次消耗2个韭菜盒子
- **随机图片**：每次消耗2个韭菜盒子
- **AI对话**：每次消耗3个韭菜盒子
- **语音合成**：每次消耗2个韭菜盒子
- **变音服务**：每次消耗2个韭菜盒子
- **幻影坦克**：每次消耗2个韭菜盒子
- **天气查询**：每次消耗2个韭菜盒子
- **电棍语录**：每次消耗2个韭菜盒子

## 游戏系统

### 支持的游戏
- **井字棋**：需要2名玩家，游戏发起者先手，使用X
- **五子棋**：需要2名玩家，游戏发起者先手（黑棋），使用X

### 游戏规则

#### 井字棋
1. 使用`game start 井字棋 @玩家`开始游戏
2. 游戏发起者先手，输入位置编号(1-9)进行落子
3. 先连成3子的玩家获胜
4. 游戏结束后会自动记录战绩

#### 五子棋
1. 使用`game start 五子棋 @玩家`开始游戏
2. 游戏发起者先手（黑棋），输入坐标(例如: 5 5)进行落子
3. 棋盘大小为15x15，坐标范围为1-15
4. 先连成5子的玩家获胜
5. 游戏结束后会自动记录战绩

### 游戏管理
- `game list`：查看可用游戏列表
- `game info <游戏>`：查看游戏信息
- `game blacklist add @玩家`：添加游戏黑名单
- `game blacklist remove @玩家`：移除游戏黑名单

## 开发信息

### 技术栈
- **语言**：Python 3.8+
- **框架**：无头NapCatQQ
- **协议**：Onebot，http
- **数据库**：MariaDB
- **Web**：Tornado
- **AI**：集成多种AI服务
- **依赖库**：
  - tornado：Web框架
  - PyMySQL：数据库连接
  - openai：AI接口
  - filetype：文件类型检测
  - numpy：数值计算
  - psutil：系统信息
  - pillow：图像处理
  - matplotlib：图表生成
  - cairosvg：SVG处理
  - pandas：数据处理
  - requests：网络请求
  - urllib3：HTTP客户端
  - plum-dispatch：分发库
  - gitpython：Git操作

### 开发指南
1. **命令注册**：使用`@COMMAND_GROUP.register_command`装饰器注册命令
2. **服务注册**：使用`@BOT.register_service`装饰器注册服务
3. **游戏注册**：使用`@GAME_MANAGER.register_game`装饰器注册游戏
4. **触发器注册**：使用`@BOT.register_trigger`装饰器注册触发器

### 代码规范
- 遵循PEP 8代码规范
- 使用类型注解
- 提供详细的注释
- 保持代码结构清晰

## 贡献指南

1. Fork本项目
2. 创建功能分支
3. 提交代码
4. 发起Pull Request

## 许可证

本项目采用GPLv3许可证。

## 免责声明

- 本项目仅用于学习和研究目的
- 请勿使用本项目进行任何违法活动
- 请遵守相关法律法规和平台规则
- 使用本项目产生的一切后果由使用者自行承担