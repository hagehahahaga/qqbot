import datetime
from typing import TypedDict, Optional

from abstract.bases.importer import SENTINEL


class Arcade(TypedDict):
    group: Group
    name: str
    subnames: list[str]
    num: int
    update_time: datetime.datetime
    update_user: User
    hash: bytes


class User:
    def update_arcade_num(
        self,
        group: Group,
        name: str,
        num: Optional[int],
        time: Optional[datetime.datetime] = SENTINEL
        ):
        """
        更新指定群组中指定机厅的数量（User接口）

        功能说明：
        - 委托给Group.update_arcade_num执行实际更新
        - 将self（当前用户）作为更新者传入

        :param group: 目标群组对象
        :param name: 机厅名称或别名
        :param num: 机厅数量，可为None表示清除数量
        :param time: 更新时间，默认为当前时间
        :raises AssertionError: 未找到匹配的机厅，或更新未影响任何行
        """

    def bind_arcade(self, hash: bytes):
        """
        绑定一个机厅到当前用户或群组

        功能说明：
        - 根据调用者类型（Group/User）自动设置绑定类型为'group'或'private'
        - 检查是否已绑定相同机厅
        - 检查目标机厅是否存在
        - 绑定时的names字段初始化为空JSON数组

        :param hash: 要绑定的机厅哈希标识
        :raises AssertionError: 机厅已绑定、或机厅不存在
        """

    def unbind_arcade(self, hash: bytes):
        """
        解绑当前用户或群组的一个机厅绑定

        功能说明：
        - 根据调用者类型（Group/User）自动设置绑定类型为'group'或'private'
        - 要求传入hash而非别名，防止误操作（通过检查hash不在绑定名称列表中确保）
        - 检查绑定记录是否存在

        :param hash: 要解绑的机厅哈希标识（不能是别名）
        :raises AssertionError: 传入了别名而非hash、或未绑定此机厅
        """

    def add_arcade_binding_name(self, hash: bytes, name: str):
        """
        为绑定的机厅添加一个自定义名称

        功能说明：
        - 验证name是否为合法的JSON字符串
        - 若调用者为Group类型，额外检查name不与群内已有机厅名称重复
        - 检查name不与已有绑定名称重复
        - 检查绑定记录是否存在
        - 使用JSON_ARRAY_APPEND将名称追加到names数组中

        :param hash: 目标机厅的哈希标识
        :param name: 要添加的自定义名称
        :raises AssertionError: 名称格式不符合要求、名称重复、或未绑定此机厅
        """

    def remove_arcade_binding_name(self, hash: bytes, name: str):
        """
        移除绑定机厅的一个自定义名称

        功能说明：
        - 检查名称存在于绑定名称列表中
        - 检查绑定记录是否存在
        - 使用JSON_SEARCH查找名称在数组中的位置，再通过JSON_REMOVE移除

        :param hash: 目标机厅的哈希标识
        :param name: 要移除的自定义名称
        :raises AssertionError: 绑定名称不存在，或未绑定此机厅
        """

    @property
    def arcade_binding_hashes(self) -> list[bytes]:
        """
        获取当前用户或群组所有已绑定机厅的哈希列表

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 仅返回hash字段列表

        :return: 已绑定机厅的哈希标识列表
        """

    @property
    def binding_arcades(self) -> dict[tuple[str], Arcade]:
        """
        获取当前用户或群组所有已绑定机厅的详细信息

        功能说明：
        - 通过arcade_binding_hashes获取所有绑定hash
        - 对每个hash调用_get_arcade获取完整信息（含过期数据处理）
        - 以机厅名称为键组织返回字典

        :return: 绑定机厅信息字典，键为机厅名称，值为包含以下字段的字典：
            - group: 群组对象
            - name: 机厅名称
            - subnames: 别名列表
            - num: 机厅数量，数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
            - hash: 机厅哈希标识
        """

    def get_binding_arcade(self, name: str) -> Arcade:
        """
        获取当前用户或群组中匹配指定名称的所有绑定及其机厅信息

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 通过json_contains匹配绑定表中的names字段，查找包含指定名称的绑定
        - 支持返回多个匹配结果（同一名称可能出现在多个绑定的names列表中）
        - 每个结果使用该绑定的完整names元组作为键，便于区分不同绑定

        :param name: 要查找的绑定自定义名称
        :return: 字典，键为绑定名称元组（tuple），值为机厅信息字典（同_get_arcade返回格式）：
            - group: 群组对象
            - name: 机厅名称
            - subnames: 别名列表
            - num: 机厅数量，数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
            - hash: 机厅哈希标识
        :raises AssertionError: 未找到匹配此名称的任何绑定记录
        """

    @property
    def arcade_binding_names(self) -> list[str]:
        """
        获取当前用户或群组所有已绑定机厅的自定义名称列表

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 从arcades_bind表的names字段中提取所有自定义名称
        - 将所有名称的JSON数组展开合并为一个扁平列表

        :return: 所有绑定自定义名称的完整列表
        """

    def get_arcade_binding_num(self, name: str) -> tuple[int, datetime.datetime, User]:
        """
        获取指定绑定机厅的数量、更新时间和更新用户，自动处理过期数据

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 通过json_contains匹配绑定表中的names字段，查找指定的绑定名称
        - 使用JSON_QUOTE安全处理参数
        - 委托_get_arcade_num处理过期数据逻辑
        - 注意：此函数查询的是绑定记录中匹配指定名称的单个绑定，返回单个三元组而非列表

        :param name: 绑定自定义名称（通过add_arcade_binding_name添加的名称）
        :return: (num, update_time, update_user) 三元组：
            - num: 机厅数量（int或None），数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
        :raises AssertionError: 未找到匹配此名称的绑定记录
        :example:
            - 正常返回: (10, datetime.datetime(2024, 1, 1, 12, 0, tzinfo=LOCAL_TIMEZONE), User(123456789))
            - 数据过期: (None, None, None)
        """


class Group:
    @property
    def arcades(self) -> dict[str, Arcade]:
        """
        获取群组的所有机厅信息，自动处理过期数据

        功能说明：
        - 获取群内所有机厅的详细信息
        - 自动重置今日7点前的过期数据（num、update_time、update_user_id设为NULL）
        - 将update_time转换为本地时区
        - 将update_user_id转换为User对象

        :return: 机厅信息字典，键为机厅名称，值为包含以下字段的字典：
            - group: 群组对象（Group类型）
            - name: 机厅名称
            - subnames: 别名列表，从数据库subnames字段JSON解析
            - num: 机厅数量，数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
            - hash: 机厅哈希标识（bytes类型）
        """

    def add_arcade(self, name: str):
        """
        向群组添加一个新的机厅

        功能说明：
        - 验证name是否为合法的JSON字符串
        - 检查name是否与本群已有机厅名称或绑定名称重复
        - 在arcades表中插入新记录，自动生成hash

        :param name: 机厅名称
        :raises AssertionError: name格式不符合要求，或名称重复
        """

    def remove_arcade(self, name: str):
        """
        从群组中移除一个机厅

        功能说明：
        - 不允许使用别名（subname）作为参数移除，只能使用主名称
        - 要求机厅没有别名（subnames为空），需要先移除所有别名
        - 先删除该机厅在arcades_bind表中的关联记录，再删除arcades表中的记录

        :param name: 机厅主名称（不能使用别名）
        :raises AssertionError: 使用了别名、机厅不存在、或机厅还有未移除的别名
        """

    def get_arcade_hash(self, name: str) -> bytes:
        """
        获取机厅的哈希标识

        功能说明：
        - 通过json_contains匹配names字段（包含主名称和所有别名），支持使用别名查询
        - 使用JSON_QUOTE安全处理参数，防止SQL注入

        :param name: 机厅名称或别名
        :return: 机厅的唯一哈希标识（binary(32)）
        :raises AssertionError: 未找到匹配的机厅
        """

    def add_arcade_subname(self, name: str, subname: str):
        """
        为机厅添加一个别名

        功能说明：
        - 验证subname是否为合法的JSON字符串
        - 检查subname是否与群内已有名称（机厅名称、别名、绑定名称）重复
        - 使用JSON_ARRAY_APPEND将别名追加到subnames数组中

        :param name: 机厅主名称
        :param subname: 要添加的别名
        :raises AssertionError: 别名格式不符合要求、名称重复、或机厅不存在
        """

    def remove_arcade_subname(self, name: str, subname: str):
        """
        移除机厅的一个别名

        功能说明：
        - 先验证机厅主名称是否存在
        - 使用JSON_SEARCH查找别名在数组中的位置，再通过JSON_REMOVE移除
        - 如果更新未影响任何行（别名不存在），则断言失败

        :param name: 机厅主名称
        :param subname: 要移除的别名
        :raises AssertionError: 机厅不存在，或机厅没有该别名
        """

    @property
    def arcade_names(self) -> list[str]:
        """
        获取群组所有机厅的名称和别名列表

        功能说明：
        - 从arcades表中查询所有记录的names字段（虚拟生成列，包含主名称+所有别名）
        - 将每个names的JSON数组展开合并为一个扁平列表

        :return: 群组内所有机厅名称和别名的完整列表
        """

    def update_arcade_num(
        self, name: str, num: Optional[int], user: User, time: Optional[datetime.datetime] = SENTINEL
    ):
        """
        更新指定机厅的数量、更新时间和更新用户

        功能说明：
        - 通过json_contains匹配names字段，支持使用主名称或别名更新
        - 使用JSON_QUOTE安全处理参数，防止SQL注入
        - 未指定time时自动设置为当前时间
        - 记录更新操作对应的用户ID

        :param name: 机厅名称或别名
        :param num: 机厅数量，可为None表示清除数量
        :param user: 执行更新操作的用户对象
        :param time: 更新时间，默认为当前时间
        :raises AssertionError: 未找到匹配的机厅，或更新未影响任何行
        """

    def get_arcade_num(self, name: str) -> tuple[int, datetime.datetime, User]:
        """
        获取指定机厅的数量、更新时间和更新用户，自动处理过期数据

        功能说明：
        - 通过json_contains匹配names字段，支持使用主名称或别名查询
        - 使用JSON_QUOTE安全处理参数，防止SQL注入
        - 自动处理过期数据：若更新时间存在且在今日7点之前，自动重置为NULL
        - 将update_user_id转换为User对象
        - 将update_time转换为本地时区

        :param name: 机厅名称或别名

        :return: (num, update_time, update_user) 三元组：
            - num: 机厅数量（int或None），数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None

        :raises AssertionError: 群组中未找到匹配的机厅或别名

        :example:
            - 正常返回: (10, datetime.datetime(2024, 1, 1, 12, 0, tzinfo=LOCAL_TIMEZONE), User(123456789))
            - 数据过期: (None, None, None)
        """

    def bind_arcade(self, hash: bytes):
        """
        绑定一个机厅到当前用户或群组

        功能说明：
        - 根据调用者类型（Group/User）自动设置绑定类型为'group'或'private'
        - 检查是否已绑定相同机厅
        - 检查目标机厅是否存在
        - 绑定时的names字段初始化为空JSON数组

        :param hash: 要绑定的机厅哈希标识
        :raises AssertionError: 机厅已绑定、或机厅不存在
        """

    def unbind_arcade(self, hash: bytes):
        """
        解绑当前用户或群组的一个机厅绑定

        功能说明：
        - 根据调用者类型（Group/User）自动设置绑定类型为'group'或'private'
        - 要求传入hash而非别名，防止误操作（通过检查hash不在绑定名称列表中确保）
        - 检查绑定记录是否存在

        :param hash: 要解绑的机厅哈希标识（不能是别名）
        :raises AssertionError: 传入了别名而非hash、或未绑定此机厅
        """

    def add_arcade_binding_name(self, hash: bytes, name: str):
        """
        为绑定的机厅添加一个自定义名称

        功能说明：
        - 验证name是否为合法的JSON字符串
        - 若调用者为Group类型，额外检查name不与群内已有机厅名称重复
        - 检查name不与已有绑定名称重复
        - 检查绑定记录是否存在
        - 使用JSON_ARRAY_APPEND将名称追加到names数组中

        :param hash: 目标机厅的哈希标识
        :param name: 要添加的自定义名称
        :raises AssertionError: 名称格式不符合要求、名称重复、或未绑定此机厅
        """

    def remove_arcade_binding_name(self, hash: bytes, name: str):
        """
        移除绑定机厅的一个自定义名称

        功能说明：
        - 检查名称存在于绑定名称列表中
        - 检查绑定记录是否存在
        - 使用JSON_SEARCH查找名称在数组中的位置，再通过JSON_REMOVE移除

        :param hash: 目标机厅的哈希标识
        :param name: 要移除的自定义名称
        :raises AssertionError: 绑定名称不存在，或未绑定此机厅
        """

    @property
    def arcade_binding_hashes(self) -> list[bytes]:
        """
        获取当前用户或群组所有已绑定机厅的哈希列表

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 仅返回hash字段列表

        :return: 已绑定机厅的哈希标识列表
        """

    @property
    def binding_arcades(self) -> dict[tuple[str], Arcade]:
        """
        获取当前用户或群组所有已绑定机厅的详细信息

        功能说明：
        - 通过arcade_binding_hashes获取所有绑定hash
        - 对每个hash调用_get_arcade获取完整信息（含过期数据处理）
        - 以机厅名称为键组织返回字典

        :return: 绑定机厅信息字典，键为机厅名称，值为包含以下字段的字典：
            - group: 群组对象
            - name: 机厅名称
            - subnames: 别名列表
            - num: 机厅数量，数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
            - hash: 机厅哈希标识
        """

    def get_binding_arcade(self, name: str) -> Arcade:
        """
        获取当前用户或群组中匹配指定名称的所有绑定及其机厅信息

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 通过json_contains匹配绑定表中的names字段，查找包含指定名称的绑定
        - 支持返回多个匹配结果（同一名称可能出现在多个绑定的names列表中）
        - 每个结果使用该绑定的完整names元组作为键，便于区分不同绑定

        :param name: 要查找的绑定自定义名称
        :return: 字典，键为绑定名称元组（tuple），值为机厅信息字典（同_get_arcade返回格式）：
            - group: 群组对象
            - name: 机厅名称
            - subnames: 别名列表
            - num: 机厅数量，数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
            - hash: 机厅哈希标识
        :raises AssertionError: 未找到匹配此名称的任何绑定记录
        """

    @property
    def arcade_binding_names(self) -> list[str]:
        """
        获取当前用户或群组所有已绑定机厅的自定义名称列表

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 从arcades_bind表的names字段中提取所有自定义名称
        - 将所有名称的JSON数组展开合并为一个扁平列表

        :return: 所有绑定自定义名称的完整列表
        """

    def get_arcade_binding_num(self, name: str) -> tuple[int, datetime.datetime, User]:
        """
        获取指定绑定机厅的数量、更新时间和更新用户，自动处理过期数据

        功能说明：
        - 根据调用者类型（Group/User）查询对应类型的绑定记录
        - 通过json_contains匹配绑定表中的names字段，查找指定的绑定名称
        - 使用JSON_QUOTE安全处理参数
        - 委托_get_arcade_num处理过期数据逻辑
        - 注意：此函数查询的是绑定记录中匹配指定名称的单个绑定，返回单个三元组而非列表

        :param name: 绑定自定义名称（通过add_arcade_binding_name添加的名称）
        :return: (num, update_time, update_user) 三元组：
            - num: 机厅数量（int或None），数据过期或未记录时为None
            - update_time: 更新时间（已转为本地时区），数据过期或未记录时为None
            - update_user: 更新用户（User类型），数据过期或未记录时为None
        :raises AssertionError: 未找到匹配此名称的绑定记录
        :example:
            - 正常返回: (10, datetime.datetime(2024, 1, 1, 12, 0, tzinfo=LOCAL_TIMEZONE), User(123456789))
            - 数据过期: (None, None, None)
        """
