from typing import Any, Optional

from pymysql.cursors import Cursor

from abstract.bases.importer import functools, threading, pymysql, dispatch, time


from abstract.bases.config import CONFIG
from abstract.bases.log import LOG


class Table:
    LOCK = threading.Lock()

    def __init__(self, _con: pymysql.Connection, name: str):
        self._con = _con
        self._cursor = _con.cursor()
        self._cursor.table_name = name
        self.name = name

    def __enter__(self) -> Cursor:
        self.LOCK.acquire()
        try:
            self._con.ping(reconnect=True)
        except Exception:
            self.LOCK.release()
            raise
        return self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self._con.commit()
            else:
                self._con.rollback()
        finally:
            self.LOCK.release()

    @staticmethod
    def _with_lock(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with self:
                return func(self, *args, **kwargs)

        return wrapper

    @_with_lock
    def create(self, column, type, *args):
        self._cursor.execute(f'CREATE TABLE {self.name}({column} {type} {" ".join(args)})')
        return self

    @_with_lock
    def add_key(self, key, type: str, *args):
        self._cursor.execute(f"ALTER TABLE {self.name} ADD {key} {type} {' '.join(args)}")
        return self

    @_with_lock
    def delete_key(self, key):
        self._cursor.execute(f"ALTER TABLE {self.name} DROP COLUMN {key}")
        return self

    @_with_lock
    def have_key(self, key: str):
        return bool(self._cursor.execute(
            f"select * from information_schema.columns "
            f"where TABLE_SCHEMA = %s "
            f"and table_name = %s "
            f"and COLUMN_NAME = %s",
            (self._con.db, self.name, key)
        ))

    @_with_lock
    def get_len(self):
        return self._cursor.execute(f'SHOW COLUMNS FROM {self.name}')

    @_with_lock
    def exists(self):
        return bool(self._cursor.execute(
            f"select * from information_schema.tables "
            f"where TABLE_SCHEMA = %s "
            f"and table_name = %s",
            (self._con.db, self.name)
        ))

    @_with_lock
    def get(self, condition: str, param: tuple[Any, ...] | Any = tuple(), *attr: str) -> Optional[tuple[Any, ...]]:
        if not attr:
            attr = ('*', )
        if not isinstance(param, tuple):
            param = (param, )
        self._cursor.execute(f"SELECT {','.join(attr)} FROM {self.name} " + condition, param)
        result = self._cursor.fetchone()
        return result

    @_with_lock
    def get_all(self, condition: str, param: tuple[Any, ...] | Any = tuple(), *attr: str):
        if not attr:
            attr = ('*', )
        if not isinstance(param, tuple):
            param = (param, )
        self._cursor.execute(f"SELECT {','.join(attr)} FROM {self.name} " + condition, param)
        return self._cursor.fetchall()

    @_with_lock
    def set(self, condition: str, param: tuple[Any, ...] | Any, **attrs: Any):
        if not isinstance(param, tuple):
            param = (param, )
        assert condition.strip() and condition.isprintable(), '空condition 的 Update 语句会立刻更新所有表行'

        return self._cursor.execute(
            f'UPDATE {self.name} SET {",".join(f"{attr} = %s" for attr in attrs)} ' + condition,
            (*attrs.values(), *param)
        )

    @_with_lock
    @dispatch
    def add(self, *args: Any):
        self._cursor.execute(f"INSERT INTO {self.name} VALUES ({','.join(['%s'] * len(args))})", args)
        return self

    @_with_lock
    @dispatch
    def add(self, **kwargs: Any):
        self._cursor.execute(
            f"INSERT INTO {self.name} ({','.join(kwargs)}) VALUES ({','.join(['%s'] * len(kwargs))})",
            tuple(kwargs.values())
        )
        return self

    @_with_lock
    def delete(self, condition: str, param: tuple[Any, ...] | Any = tuple()):
        if not isinstance(param, tuple):
            param = (param, )
        assert condition.strip() and condition.isprintable(), '空condition 的 Delete 语句会清除表中的所有数据'
        self._cursor.execute(
            f"DELETE FROM {self.name} " + condition,
            param
        )
        return self

    @_with_lock
    def find_exists(self, **kwargs):
        return bool(
            self._cursor.execute(
                f"SELECT 1 FROM {self.name} "
                f"WHERE ({','.join(kwargs)}) = ({','.join(['%s'] * len(kwargs))})",
                tuple(kwargs.values())
            )
        )

LOG.INF('Connecting to MySQL database...')
while True:
    try:
        con = pymysql.connect(**CONFIG.sql_config.model_dump())
        break
    except pymysql.MySQLError as e:
        LOG.WAR(f'MySQL error: {e}')
        time.sleep(1)
LOG.INF(f'Connected to MySQL database: {con.get_server_info()} at {con.host}:{con.port}')
LOG.INF('Loading database tables...')
USER_TABLE = Table(con, 'qq_users')
GROUP_OPTION_TABLE = Table(con, 'group_options')
NOTICE_SCHEDULE_TABLE = Table(con, 'notice_schedule')
GAME_DATA_TABLE = Table(con, 'game_data')
LOG.INF(
    'Loaded database tables:\n' +
    ',\n'.join(
        table.name for table in filter(
            lambda a: isinstance(a, Table),
            locals().values()
        )
    )
)
