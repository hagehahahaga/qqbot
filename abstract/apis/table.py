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

    def __enter__(self):
        self.LOCK.acquire()
        self._con.ping()
        return self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._con.commit()
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
    def get(self, *conditions: str, attr: str = '*'):
        self._cursor.execute(f"SELECT {attr} FROM {self.name} " + ' '.join(conditions))
        result = self._cursor.fetchone()
        return result

    @_with_lock
    def get_all(self, *conditions: str, attr: str = '*'):
        self._cursor.execute(f"SELECT {attr} FROM {self.name} " + ' '.join(conditions))
        return self._cursor.fetchall()

    @_with_lock
    def set(self, key, value, attr, target):
        self._cursor.execute(f"UPDATE {self.name} SET `{attr}` = %s WHERE `{key}` = %s", (target, value))
        return self

    @_with_lock
    @dispatch
    def add(self, *args):
        self._cursor.execute(f"INSERT INTO {self.name} VALUES ({','.join(['%s'] * len(args))})", args)
        return self

    @_with_lock
    @dispatch
    def add(self, args: tuple):
        self._cursor.execute(f"INSERT INTO {self.name} VALUES ({','.join(['%s'] * len(args))})", args)
        return self

    @_with_lock
    @dispatch
    def add(self, arg: str):
        self._cursor.execute(f"INSERT INTO {self.name} VALUES ({arg})")

    @_with_lock
    @dispatch
    def delete(self, key: str, value):
        self._cursor.execute(
            f"DELETE FROM {self.name} WHERE {key} = %s",
            value
        )
        return self

    @_with_lock
    @dispatch
    def delete(self, keys: tuple, values:tuple):
        self._cursor.execute(
            f"DELETE FROM {self.name} "
            f"WHERE ({','.join(keys)}) = ({','.join(['%s'] * len(values))})",
            values
        )
        return self

    @_with_lock
    @dispatch
    def find_exists(self, key: str, value):
        return bool(
            self._cursor.execute(
                f"SELECT * FROM {self.name} WHERE {key} = %s",
                (value,)
            )
        )

    @_with_lock
    @dispatch
    def find_exists(self, keys: tuple, values: tuple):
        return bool(
            self._cursor.execute(
                f"SELECT * FROM {self.name} "
                f"WHERE ({','.join(keys)}) = ({','.join(['%s'] * len(values))})",
                values
            )
        )


class Default:
    def __repr__(self):
        return 'default'


class Null:
    def __repr__(self):
        return 'null'


DEFAULT = Default()
NULL = Null()

LOG.INF('Connecting to MySQL database...')
while True:
    try:
        _con = pymysql.connect(**CONFIG.sql_config.model_dump())
        break
    except pymysql.MySQLError as e:
        LOG.WAR(f'MySQL error: {e}')
        time.sleep(1)
LOG.INF(f'Connected to MySQL database: {_con.get_server_info()} at {_con.host}:{_con.port}')
LOG.INF('Loading database tables...')
USER_TABLE = Table(_con, 'qq_users')
GROUP_OPTION_TABLE = Table(_con, 'group_options')
NOTICE_SCHEDULE_TABLE = Table(_con, 'notice_schedule')
GAME_DATA_TABLE = Table(_con, 'game_data')
LOG.INF(
    'Loaded database tables:\n' +
    ',\n'.join(
        table.name for table in filter(
            lambda a: isinstance(a, Table),
            locals().values()
        )
    )
)
