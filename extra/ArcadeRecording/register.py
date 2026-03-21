import operator, itertools, datetime
from typing import Optional
from abstract.bases.importer import today_7am, SENTINEL

from abstract.target import *

from .tables import ARCADES_TABLE


@User.register_func
def update_arcade_num(self, group: Group, name: str, num: Optional[int], time: Optional[datetime.datetime] = SENTINEL):
    """
    更新指定群组中指定机厅的数量

    :param group: 群组对象
    :param name: 机厅名称或别名
    :param num: 机厅数量，可为None表示未记录
    :param time: 更新时间，默认为当前时间
    """
    group.update_arcade_num(name, num, self, time)


@Group.register_func
def get_arcades(self) -> dict[str, dict[str, list | Optional[int] | Optional[datetime.datetime] | Optional[User]]]:
    """
    获取群组的所有机厅信息，自动处理过期数据

    功能说明：
    - 获取群内所有机厅的详细信息
    - 自动重置今日7点前的数据（num、update_time和update_user设为None）
    - 将update_time转换为本地时区

    :return: 机厅信息字典，键为机厅名称，值为包含以下字段的字典：
        - sub_names: 机厅别名列表，从数据库subnames字段JSON解析
        - num: 机厅数量，可能为None（未记录或已过期）
        - update_time: 更新时间，可能为None，已转换为本地时区
        - update_user: 更新用户，可能为None（未记录或已过期）
    """
    result = ARCADES_TABLE.get_all(f'where group_id = {self.id}', attr='name, subnames, num, update_time, update_user_id')
    response = {}
    for name, sub_names, num, update_time, update_user_id in result:
        if update_time and (update_time := update_time.replace(tzinfo=datetime.UTC)) < today_7am():
            self.reset_arcade_num(name)
            num = None
            update_time = None
            update_user = None
        else:
            update_user = User(int(update_user_id)) if update_user_id else None
        response[name] = {
            'sub_names': json.loads(sub_names),
            'num': num,
            'update_time': update_time.astimezone() if update_time else update_time,
            'update_user': update_user,
        }
    return response

@Group.register_func
def add_arcade(self, name: str):
    assert json.dumps(name, ensure_ascii=False) == f'"{name}"', '机厅名不符合要求.'
    assert name not in self.get_arcade_names(), '有重复命名'
    with ARCADES_TABLE:
        ARCADES_TABLE.cursor.execute(
            f'insert into {ARCADES_TABLE.name} (group_id, name)'
            f'values (%s, %s)',
            (self.id, name)
        )

@Group.register_func
def remove_arcade(self, name: str):
    arcades = self.get_arcades()
    assert name not in itertools.chain(*map(operator.itemgetter('sub_names'), arcades.values())), '安全起见移除不能使用机厅别名.'
    assert name in arcades, f'{name} 未在此群设置.'
    assert not arcades[name]['sub_names'], '安全起见移除机厅需要先移除机厅所有别名.'
    ARCADES_TABLE.delete('(group_id, name)', (self.id, name))

@Group.register_func
def add_arcade_subname(self, name: str, subname: str):
    assert json.dumps(subname, ensure_ascii=False) == f'"{subname}"', '别名不符合要求.'
    assert subname not in self.get_arcade_names(), '有重复命名'
    with ARCADES_TABLE:
        ARCADES_TABLE.cursor.execute(
            f'update {ARCADES_TABLE.name} '
            f'set subnames = json_array_append(subnames, "$", %s) '
            f'where group_id = %s and name = %s',
            (subname, self.id, name)
        )

@Group.register_func
def remove_arcade_subname(self, name: str, subname: str):
    with ARCADES_TABLE:
        ARCADES_TABLE.cursor.execute(
            f'update {ARCADES_TABLE.name} '
            f'set subnames = json_remove(subnames, json_unquote(json_search(subnames, "one", %s))) '
            f'where group_id = %s and name = %s',
            (subname, self.id, name)
        )

@Group.register_func
def get_arcade_names(self):
    return list(
        itertools.chain(
            *map(
                json.loads,
                itertools.chain(
                    *ARCADES_TABLE.get_all(f'where group_id = {self.id}', attr='names')
                )
            )
        )
    )

@Group.register_func
def update_arcade_num(self, name: str, num: Optional[int], user: User, time: Optional[datetime.datetime] = SENTINEL):
    """
    更新指定机厅的数量、更新时间和更新用户ID

    功能说明：
    - 使用参数化查询和JSON_QUOTE处理机厅名称，支持使用机厅别名更新
    - 自动设置更新时间为当前时间（如果未指定）
    - 记录更新操作的用户ID

    :param name: 机厅名称或别名
    :param num: 机厅数量，可为None表示未记录
    :param user: 更新操作的用户对象
    :param time: 更新时间，默认为当前时间
    """
    if time is SENTINEL:
        time = datetime.datetime.now()
    with ARCADES_TABLE:
        ARCADES_TABLE.cursor.execute(
            f'update {ARCADES_TABLE.name} '
            f'set num = %s, update_time = %s, update_user_id = %s '
            f'where group_id = %s and json_contains(names, json_quote(%s))',
            (num, time.astimezone(datetime.UTC), user.id, self.id, name)
        )

@Group.register_func
def reset_arcade_num(self, name: str):
    with ARCADES_TABLE:
        ARCADES_TABLE.cursor.execute(
            f'update {ARCADES_TABLE.name} '
            f'set num = NULL, update_time = NULL, update_user_id = NULL '
            f'where group_id = %s and json_contains(names, json_quote(%s))',
            (self.id, name)
        )

@Group.register_func
def get_arcade_num(self, name: str) -> Optional[tuple[Optional[int], Optional[datetime.datetime], Optional[User]]]:
    """
    获取指定机厅的数量、更新时间和更新用户，自动处理过期数据

    功能说明：
    - 使用参数化查询和JSON_QUOTE处理机厅名称，支持使用机厅别名查询
    - 自动处理过期数据：
      - 未找到记录时返回None
      - 更新时间为None时返回(None, None, None)
      - 更新时间在今日7点之前时：
        - 调用reset_arcade_num重置数据库中的num和update_time为NULL
        - 返回(None, None, None)
      - 否则返回(机厅数量, 本地时区的更新时间, 更新用户)

    :param name: 机厅名称或别名

    :return: 包含机厅数量、更新时间和更新用户的元组，可能为：
        - None: 未找到指定机厅
        - (None, None, None): 数据已过期或未记录
        - (num, update_time, update_user): 机厅数量、更新时间和更新用户，update_time已转换为本地时区，update_user为User类型

    :example:
        - 正常返回: (10, datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=LOCAL_TIMEZONE), User(123456789))
        - 数据过期: (None, None, None)
        - 未找到: None
    """

    with ARCADES_TABLE:
        ARCADES_TABLE.cursor.execute(
            f'select num, update_time, update_user_id '
            f'from {ARCADES_TABLE.name} '
            f'where group_id = %s and json_contains(names, JSON_QUOTE(%s))',
            (self.id, name)
        )
        result = ARCADES_TABLE.cursor.fetchone()

    if not result:
        return None

    if not result[1] or (update_time := result[1].replace(tzinfo=datetime.UTC)) < today_7am():
        self.reset_arcade_num(name)
        return None, None, None

    update_user = User(int(result[2])) if result[2] else None
    return result[0], update_time.astimezone(), update_user
