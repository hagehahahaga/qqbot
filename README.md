# QQBot Extra 组件开发指南

## 概述

本文档面向 QQBot 的 extra 组件开发者，详细介绍了项目的技术架构、各模块的实现细节与注册机制，以及如何开发、集成和扩展 extra 组件。通过本文档，您将能够理解项目的整体设计，掌握 command、service、trigger、game 和 target 等核心模块的使用方法，并能够独立开发符合规范的 extra 组件。

## 技术架构概述

QQBot 是一个基于 Python 的模块化 QQ 机器人框架，采用 Onebot 协议与 NapCatQQ 框架通信。项目采用分层架构设计，核心模块位于 `abstract` 目录下，提供基础功能；扩展模块位于 `extra` 目录下，通过统一的注册机制动态集成。

### 核心模块

- **bot**: 机器人核心，负责消息路由、组件注册和生命周期管理。
- **command**: 命令系统，提供命令的注册、解析和执行。
- **service**: 后台服务系统，支持定时任务和循环执行。
- **trigger**: 触发器系统，基于条件自动响应消息。
- **game**: 游戏系统，支持多玩家回合制游戏。
- **target**: 目标系统，管理用户和群组数据，支持动态扩展。

### 扩展模块 (extra)

extra 组件是独立的功能模块，通过标准的注册接口集成到机器人中。每个组件可以注册命令、服务、触发器、游戏，并可以扩展用户和群组的功能。

### 数据存储

项目使用 MySQL 数据库，通过 `abstract.apis.table` 模块提供抽象的表操作接口。用户数据、群组设置和游戏状态等均持久化存储。

## 组件间交互逻辑

### 消息处理流程

1. 机器人接收到消息后，获取该消息发送者的 session。
2. 如果 session 处于等待输入状态（`session.getting`），将消息投递到输入管道（`pipe_put`）并返回。若已设置 `put_condition` 且消息不满足过滤条件，则投递 `SessionTransfer` 让锁信号，通知持锁的 `pipe_get` 主动释放锁以让渡给更高优先级的交互。
3. 从消息首条文本部件解析指令名与参数（无文本部件时视为空指令名）。
4. 如果是群消息且开启了 `must_at` 模式，检查消息是否 @ 了机器人，若无则忽略。
5. 如果解析结果不是有效的 `Command` 对象（即未识别为指令），按注册顺序检查触发器条件。首个匹配的触发器执行其响应函数后立即返回，不再继续匹配。
6. 如果 session 存在进行中的命令（`running_command`），由 session 处理该消息（如输入 "cancel" 取消当前命令）。
7. 若指令为 `None`（群聊且 `must_at` 时未命中任何命令前缀），提示"你好像没有输入指令?"。
8. 若指令为空字符串（消息无文本部件，如仅 @ 机器人或纯图片），提示"你好像没有输入指令?"。
9. 若指令为不存在的指令名（字符串），提示该指令不可识别。
10. 匹配到有效命令时，在 `with session:` 持锁上下文内按命令类型执行：
    - 类型 `0`：无参数；
    - 类型 `1`：字符串参数；
    - 类型 `2`：消息部件参数（按 `@bot + 文本` 或纯文本结构匹配）；
    - 字典类型：通过 `session.pipe_get_by_type` 收集指定数量的特定消息部件。
11. 后台服务独立运行，定时执行任务，不受消息流影响。
12. 游戏系统通过命令或触发器启动，管理独立的游戏会话。

### 组件注册顺序

extra 组件的注册在机器人启动时自动完成。每个 extra 组件的 `__init__.py` 文件导入其子模块（commands、services、triggers 等），这些子模块在导入时即通过全局对象（如 `COMMAND_GROUP`、`BOT`、`GAME_MANAGER`）完成注册。

### 依赖关系

- command、trigger、game 依赖于 target（User/Group）来获取上下文。
- service 可以独立运行，也可操作 target 和数据库。
- extra 组件之间应保持松耦合，通过标准接口交互。

## 核心模块详解

### 1. Command 模块

#### 1.1 概述

command 模块负责管理所有用户命令。命令通过装饰器注册，支持多种参数类型和修饰器（如权限控制、成本消耗等）。

#### 1.2 核心类

- **Command**: 封装命令函数，包含名称、参数类型、帮助文本等信息。
- **CommandGroup**: 管理命令集合，提供注册和查找功能。

#### 1.3 注册机制

使用 `COMMAND_GROUP.register_command` 装饰器注册命令：

```python
from abstract.command import COMMAND_GROUP, cost, group_only, ask_for_wait

@COMMAND_GROUP.register_command(('weather', '天气'), 1, '获取天气信息')
@cost(2)
@group_only
@ask_for_wait
def weather_command(message, session, args):
    # 命令实现
    pass
```

**参数说明**：
- 第一个参数：命令名称（元组，支持多个别名）
- 第二个参数：参数类型（0: 无参数，1: 字符串参数，2: 消息部件参数，字典: 指定所需消息部件类型和数量）
- 第三个参数：帮助文本

#### 1.4 修饰器

- `@cost(points)`: 命令消耗用户点数。通过 `assert` 检查点数是否充足，不足时抛出 `AssertionError` 提示。执行成功后自动扣除点数并发送消耗通知。同时传递被装饰函数的返回值。
- `@group_only`: 仅限群聊使用。通过 `assert` 检查消息类型，同时传递被装饰函数的返回值。
- `@private_only`: 仅限私聊使用。
- `@authorize(level)`: 需要指定权限等级。
- `@ask_for_wait`: 在执行前发送"别急"等待提示，执行完毕后自动删除该提示。同时传递被装饰函数的返回值。

#### 1.5 命令函数签名

命令函数接收三个参数：
- `message`: `MESSAGE` 对象，代表接收到的消息
- `session`: `Session` 对象，管理命令会话状态
- `args`: 解析后的参数列表（根据参数类型不同而不同）

#### 1.6 异常处理

命令执行中可抛出 `CommandCancel` 异常来取消命令并返回错误信息给用户。

### 2. Service 模块

#### 2.1 概述

service 模块用于创建后台运行的任务，支持定时执行和循环逻辑。

#### 2.2 核心类

- **Service**: 服务基类，定义服务生命周期方法（实际使用中更多直接使用装饰器）。

#### 2.3 注册机制

使用 `BOT.register_service` 装饰器注册服务：

```python
from abstract.bot import BOT

@BOT.register_service('weather_predictor_hourly', 0, auto_restart=True)
def weather_predictor_hourly():
    # 服务逻辑，通常包含循环
    while True:
        # 执行任务
        time.sleep(3600)  # 每小时执行
```

**参数说明**：
- 第一个参数：服务名称
- 第二个参数：初始延迟（秒）
- `auto_restart`: 异常时是否自动重启

#### 2.4 服务设计模式

服务函数通常包含无限循环，通过 `time.sleep` 控制执行间隔。可以使用 `abstract.bases.importer.at_midnight()` 等工具函数处理定时逻辑。

### 3. Trigger 模块

#### 3.1 概述

trigger 模块提供条件触发器，当消息满足特定条件时自动执行响应函数。

#### 3.2 注册机制

使用 `BOT.register_trigger` 装饰器注册触发器：

```python
from abstract.bot import BOT

@BOT.register_trigger
def trigger_condition(message):
    # 条件函数，返回布尔值
    return 'hello' in message.text

@trigger_condition.register
def trigger_response(message, session):
    # 响应函数
    message.reply_text('Hello!')
```

触发器由条件函数和响应函数组成。条件函数接收 `MESSAGE` 对象，返回布尔值；响应函数接收 `MESSAGE` 和 `Session` 对象。

#### 3.3 执行顺序

触发器按注册顺序检查。当消息未匹配任何命令时，机器人按顺序调用每个触发器的条件函数，第一个返回 `True` 的触发器将执行其响应函数。

### 4. Game 模块

#### 4.1 概述

game 模块提供回合制游戏框架，支持多玩家游戏、状态管理和胜负判定。

#### 4.2 核心类

- **BaseGame**: 游戏抽象基类，定义游戏接口。
- **GameManager**: 游戏管理器，负责游戏的注册和会话管理。

#### 4.3 注册机制

使用 `GAME_MANAGER.register_game` 装饰器注册游戏：

```python
from abstract.game import GAME_MANAGER, BaseGame

@GAME_MANAGER.register_game('guess_number', '猜数字游戏')
class GuessNumberGame(BaseGame):
    def handle(self, message, session):
        # 游戏逻辑
        pass
```

**参数说明**：
- 第一个参数：游戏标识符
- 第二个参数：游戏显示名称

#### 4.4 游戏生命周期

1. 通过命令或触发器启动游戏，创建游戏实例。
2. 游戏实例管理玩家状态和游戏数据。
3. 游戏通过 `handle` 方法处理玩家输入。
4. 游戏结束后，结果保存到用户数据中。

#### 4.5 游戏数据存储

游戏数据通过 `User` 类的 `game_data` 属性持久化存储，支持胜率统计和黑名单功能。

### 5. Target 模块

#### 5.1 概述

target 模块代表消息的发送者和接收者，包括 `User`（用户）和 `Group`（群组）类。该类提供数据管理和动态方法扩展功能。

#### 5.2 核心类

- **User**: 用户类，管理用户数据（点数、签到记录、游戏统计等）。
- **Group**: 群组类，管理群组设置。

#### 5.3 数据管理

用户和群组数据通过数据库持久化存储，提供便捷的访问接口：

```python
# 获取用户点数
points = user.points

# 增加用户点数
user.points += 10

# 获取用户游戏数据
game_data = user.game_data['guess_number']
```

#### 5.4 动态扩展

extra 组件可以通过装饰器动态扩展 `User` 和 `Group` 类的方法：

```python
from abstract.target import User


@User.register_attr
def get_weather_history(self, days=7):
    """获取用户的历史天气记录（示例扩展方法）"""
    # 通过 self 访问用户数据
    pass


# 使用扩展方法
user.get_weather_history(3)
```

#### 5.5 方法重写

使用 `@User.override` 装饰器可以重写已有的方法（谨慎使用）。

## Extra 组件开发规范

### 1. 目录结构

每个 extra 组件应位于 `extra` 目录下的独立子目录中，目录名使用 PascalCase（如 `Weather`、`ArcadeRecording`）。建议的目录结构：

```
extra/ComponentName/
├── __init__.py          # 组件入口，导入子模块
├── commands.py          # 命令定义
├── services.py          # 服务定义
├── triggers.py          # 触发器定义
├── register.py          # User/Group 方法扩展
├── help_text.json       # 帮助文本（可选）
└── ...                  # 其他模块文件
```

### 2. 组件入口 (`__init__.py`)

组件入口文件应导入所有需要注册的子模块，并可注册帮助文本：

```python
import pathlib

from .commands import *
from .services import *
from .triggers import *
from .register import *

# 注册帮助文本（可选）
BOT.register_help_text(pathlib.Path(__path__[0]) / 'help_text.json')
```

### 3. 命令定义 (`commands.py`)

命令定义文件应使用 `COMMAND_GROUP.register_command` 装饰器注册命令，并合理使用修饰器：

```python
from abstract.command import COMMAND_GROUP, cost, group_only, ask_for_wait
from abstract.message import MESSAGE
from abstract.session import Session

@COMMAND_GROUP.register_command(('cmd', '命令'), 1, '命令描述')
@cost(1)
@group_only
def example_command(message: MESSAGE, session: Session, args):
    # 命令实现
    pass
```

### 4. 服务定义 (`services.py`)

服务定义文件应使用 `BOT.register_service` 装饰器注册后台服务：

```python
from abstract.bot import BOT
import time

@BOT.register_service('example_service', 0, auto_restart=True)
def example_service():
    while True:
        # 服务逻辑
        time.sleep(60)  # 每分钟执行
```

### 5. 触发器定义 (`triggers.py`)

触发器定义文件应使用 `BOT.register_trigger` 装饰器注册触发器：

```python
from abstract.bot import BOT

@BOT.register_trigger
def example_condition(message):
    return 'keyword' in message.text

@example_condition.register
def example_response(message, session):
    message.reply_text('触发响应！')
```

### 6. 方法扩展 (`register.py`)

方法扩展文件应使用 `User.register_attr` 或 `Group.register_attr` 装饰器扩展功能：

```python
from abstract.target import User, Group


@User.register_attr
def custom_user_method(self, param):
    # 扩展方法实现
    return f"User {self.id}: {param}"


@Group.register_attr
def custom_group_method(self, param):
    # 扩展方法实现
    return f"Group {self.id}: {param}"
```

### 7. 帮助文本 (`help_text.json`)

帮助文本文件为 JSON 格式，用于生成命令帮助信息：

```json
{
  "weather": "获取天气信息\n用法: /天气 [城市] [模式]\n模式: now(实时), hourly(小时), daily(每日), today(今天), tomorrow(明天), minutely(分钟降水)"
}
```

### 8. 数据库操作

extra 组件可通过 `abstract.apis.table` 模块访问数据库表：

**基础查询方法**：

```python
from abstract.apis.table import USER_TABLE, GROUP_OPTION_TABLE

# 查询用户数据
user_data = USER_TABLE.get(f'where id = {user_id}', attr='points, sign_date')

# 更新群组选项
GROUP_OPTION_TABLE.set('id', group_id, 'weather_notice', 1)
```

**使用上下文管理器执行自定义 SQL**：

`Table` 对象支持 `with` 语句作为上下文管理器，返回持有 `table_name` 属性的 cursor 对象，适用于执行复杂 SQL：

```python
from abstract.apis.table import USER_TABLE

with USER_TABLE as cursor:
    cursor.execute(
        f'update {cursor.table_name} '
        f'set points = points + 10 '
        f'where id = %s',
        (user_id,)
    )
```

使用 `with TABLE as cursor` 时自动获取锁并提交事务。SQL 中通过 `cursor.table_name` 引用表名。

### 9. 消息发送

使用 `abstract.message` 模块中的消息类发送消息：

```python
from abstract.message import GroupMessage, PrivateMessage, TextMessage, ImageMessage

# 发送群消息
GroupMessage(TextMessage('文本内容'), Group(group_id)).send()

# 发送图片
GroupMessage(ImageMessage(image_path), Group(group_id)).send()

# 发送私聊消息
PrivateMessage(TextMessage('私聊内容'), User(user_id)).send()
```

### 10. 日志记录

使用 `abstract.bases.log.LOG` 进行日志记录：

```python
from abstract.bases.log import LOG

LOG.INF('信息日志')
LOG.WAR('警告日志')
LOG.ERR('错误日志')
```

## API 参考

### 全局对象

| 对象 | 类型 | 说明 |
|------|------|------|
| `BOT` | `Bot` | 机器人实例，用于注册服务、触发器 |
| `COMMAND_GROUP` | `CommandGroup` | 命令组，用于注册命令 |
| `GAME_MANAGER` | `GameManager` | 游戏管理器，用于注册游戏 |
| `SESSION_MANAGER` | `SessionManager` | 会话管理器 |
| `ONEBOT_SERVER` | `BaseOneBotServer` | OneBot 服务器（HTTP/WS 双模式） |
| `BOT_USER` | `User` | 机器人自身用户对象 |
| `USER_TABLE` | `Table` | 用户数据表 |
| `GROUP_OPTION_TABLE` | `Table` | 群组选项表 |

### Table 核心方法

| 方法 | 说明 |
|------|------|
| `get(conditions, attr='*')` | 查询单条记录 |
| `get_all(conditions, attr='*')` | 查询多条记录 |
| `set(key, value, attr, target)` | 更新指定字段 |
| `add(*args)` | 插入新记录（支持变长参数、元组、字符串三种重载） |
| `delete(key, value)` | 删除记录。`key` 为字符串时按单字段删除；`key` 为元组时按多字段组合条件删除 |
| `find_exists(key, value)` | 检查记录是否存在。`key` 为字符串时按单字段检查；`key` 为元组时按多字段组合条件检查。均使用参数化查询防止 SQL 注入 |
| `__enter__ / __exit__` | 上下文管理器支持，返回带 `table_name` 属性的 cursor 对象 |

### 常用装饰器

| 装饰器 | 模块 | 功能 |
|--------|------|------|
| `@COMMAND_GROUP.register_command` | `abstract.command` | 注册命令 |
| `@BOT.register_service` | `abstract.bot` | 注册服务 |
| `@BOT.register_trigger` | `abstract.bot` | 注册触发器 |
| `@GAME_MANAGER.register_game` | `abstract.game` | 注册游戏 |
| `@User.register_attr` | `abstract.target` | 扩展 User 方法 |
| `@Group.register_attr` | `abstract.target` | 扩展 Group 方法 |
| `@cost` | `abstract.command` | 设置命令消耗点数 |
| `@group_only` | `abstract.command` | 限制命令仅群聊使用 |
| `@private_only` | `abstract.command` | 限制命令仅私聊使用 |
| `@authorize` | `abstract.command` | 设置命令权限等级 |
| `@ask_for_wait` | `abstract.command` | 命令执行前发送等待提示 |

### 核心类

#### MESSAGE 类

代表接收到的消息，主要属性与方法：

- `text`: 消息文本内容
- `sender`: 发送者（User 对象）
- `target`: 接收目标（User 或 Group 对象）
- `parts`: 消息部件列表
- `reply_text(text)`: 回复文本消息
- `reply(message_part)`: 回复消息部件
- `delete()`: 删除消息

#### Session 类

管理命令会话状态与输入管道，主要属性与方法：

- `pipe`: 消息输入管道（queue.Queue）
- `getting`: 是否正在等待输入
- `running_command`: 当前运行中的命令
- `running_thread`: 当前运行命令的线程
- `pipe_put(message)`: 向管道投递消息
- `pipe_get(message, inform=True, timeout=30, condition=SENTINEL)`: 阻塞等待用户输入，支持超时（`None` 为无限期）、`condition` 过滤与 `SessionTransfer` 让锁信号
- `pipe_get_by_type(message, needed_type, num=1)`: 收集指定数量的特定类型消息部件

#### User 类

代表用户，主要属性与方法：

- `id`: 用户 ID
- `name` / `role`: 用户昵称与角色（member/admin/owner/operator）
- `points`: 用户点数（property，支持读写）
- `sign_date`: 最近签到日期（property）
- `update_sign_date()`: 更新签到日期
- `game_data`: 游戏数据字典
- `game_blacklist`: 游戏黑名单（`set[User]`，支持 `|=` / `-=`）
- `register_attr` / `override`: 动态扩展 / 重写方法

#### Group 类

代表群组，主要属性与方法：

- `id`: 群组 ID
- `settings`: 群组设置字典

## 集成步骤

### 1. 创建组件目录

在 `extra` 目录下创建新的组件目录，使用 PascalCase 命名：

```bash
cd extra
mkdir NewComponent
```

### 2. 创建组件文件

按照开发规范创建 `__init__.py`、`commands.py`、`services.py` 等文件。

### 3. 实现组件功能

根据需求实现命令、服务、触发器等功能。

### 4. 测试组件

启动机器人测试组件功能：

```bash
python main.py
```

### 5. 注册帮助文本（可选）

创建 `help_text.json` 文件，提供命令使用说明。

### 6. 提交组件

将组件目录提交到版本控制系统。

## 示例代码

### 完整组件示例：简单问候组件

#### 目录结构

```
extra/Greeting/
├── __init__.py
├── commands.py
├── triggers.py
└── help_text.json
```

#### __init__.py

```python
import pathlib

from .commands import *
from .triggers import *

BOT.register_help_text(pathlib.Path(__path__[0]) / 'help_text.json')
```

#### commands.py

```python
from abstract.command import COMMAND_GROUP
from abstract.message import MESSAGE
from abstract.session import Session

@COMMAND_GROUP.register_command(('hello', '你好'), 0, '打招呼')
def hello_command(message: MESSAGE, session: Session, args):
    message.reply_text(f'你好，{message.sender.id}！')
```

#### triggers.py

```python
from abstract.bot import BOT

@BOT.register_trigger
def morning_trigger(message):
    return '早上好' in message.text

@morning_trigger.register
def morning_response(message, session):
    message.reply_text('早上好！今天也是充满希望的一天！')
```

#### help_text.json

```json
{
  "hello": "打招呼\n用法: /hello 或 /你好"
}
```

### 数据库操作示例

```python
from abstract.apis.table import USER_TABLE
from abstract.target import User


def update_user_points(user_id, delta):
    """更新用户点数"""
    user = User(user_id)
    user.points += delta

    # 使用上下文管理器执行自定义 SQL
    with USER_TABLE as cursor:
        cursor.execute(
            f'update {cursor.table_name} '
            f'set points = points + %s '
            f'where id = %s', (delta, user_id)
        )
```

### 服务示例：定时提醒

```python
from abstract.bot import BOT
import time
import datetime


@BOT.register_service('daily_reminder', 0, auto_restart=True)
def daily_reminder():
    """每天8点发送提醒"""
    while True:
        now = datetime.datetime.now()

        # 计算到第二天8点的等待时间
        target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if target_time <= now:
            target_time += datetime.timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        time.sleep(wait_seconds)

        # 发送提醒
        from abstract.message import GroupMessage, TextMessage
        from abstract.target import Group

        # 这里需要实现具体的提醒逻辑  # GroupMessage(TextMessage('每日提醒！'), Group(group_id)).send()
```

## 常见问题与解决方案

### 1. 命令未注册

**问题**: 命令定义后无法使用。

**解决方案**:
- 确保 `commands.py` 被 `__init__.py` 导入。
- 检查命令装饰器参数是否正确。
- 重启机器人使更改生效。

### 2. 服务未启动

**问题**: 服务注册后未执行。

**解决方案**:
- 检查服务函数是否包含循环逻辑。
- 确认 `auto_restart=True` 设置正确。
- 查看日志中是否有服务异常。

### 3. 数据库操作失败

**问题**: 数据库查询或更新出错。

**解决方案**:
- 确认表名和字段名正确。
- 检查 SQL 条件表达式格式。
- 确保数据库连接正常。

### 4. 权限不足

**问题**: 用户无法执行某些命令。

**解决方案**:
- 检查 `@authorize` 装饰器设置的权限等级。
- 确认用户具有足够权限。
- 使用 `User` 类的 `role` 属性检查用户权限（member/admin/owner/operator）。

### 5. 消息发送失败

**问题**: 消息无法发送到群组或用户。

**解决方案**:
- 确认机器人已加入目标群组。
- 检查目标用户是否在好友列表中。
- 查看是否有频率限制或风控限制。

## 最佳实践

1. **模块化设计**: 每个组件应功能独立，避免过度耦合。
2. **错误处理**: 妥善处理异常，避免组件崩溃影响机器人运行。
3. **资源管理**: 及时释放数据库连接、文件句柄等资源。
4. **日志记录**: 关键操作记录日志，便于调试和监控。
5. **性能优化**: 避免在循环中进行昂贵的数据库操作。
6. **代码复用**: 提取公共逻辑到工具函数或基类中。
7. **文档完善**: 为组件提供清晰的帮助文本和使用说明。

## 结语

本文档详细介绍了 QQBot extra 组件的开发流程和技术细节。通过遵循本文档的规范，您可以开发出功能强大、稳定可靠的 extra 组件，扩展机器人的能力。如有问题或建议，请参考现有组件代码或联系项目维护者。

---

*文档版本: 1.2*
*最后更新: 2026-09-03*