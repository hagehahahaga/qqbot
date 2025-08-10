from abstract.bases.importer import functools, threading, pymysql, dispatch

from config import CONFIG
from abstract.bases.log import LOG


class Table:
    LOCK = threading.Lock()

    def __init__(self, db: pymysql.Connection, name: str):
        self.db = db
        self.cursor = db.cursor()
        self.name = name

    def __enter__(self):
        self.LOCK.acquire()
        self.db.ping()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.commit()
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
        self.cursor.execute(f'CREATE TABLE {self.name}({column} {type} {" ".join(args)})')
        return self

    @_with_lock
    def add_key(self, key, type: str, *args):
        self.cursor.execute(f"ALTER TABLE {self.name} ADD {key} {type} {' '.join(args)}")
        return self

    @_with_lock
    def delete_key(self, key):
        self.cursor.execute(f"ALTER TABLE {self.name} DROP COLUMN {key}")
        return self

    @_with_lock
    def get_len(self):
        assert self.cursor.execute(
            f'select column_name from information_schema.columns where table_name = "{self.name}"'
        ), 'No data. Can not get len.'
        return len(self.cursor.fetchall())

    @_with_lock
    def exists(self):
        return bool(self.cursor.execute(f"select * from information_schema.tables where table_name = '{self.name}'"))

    @_with_lock
    def  get(self, *args, attr: str = '*'):
        self.cursor.execute(f"SELECT {attr} FROM {self.name} " + ' '.join(args))
        result = self.cursor.fetchone()
        return result

    @_with_lock
    def get_all(self, *args, attr: str = '*'):
        self.cursor.execute(f"SELECT {attr} FROM {self.name} " + ' '.join(args))
        return self.cursor.fetchall()

    @_with_lock
    def set(self, key, value, attr, target):
        self.cursor.execute(f"UPDATE {self.name} SET {attr} = %s WHERE {key} = %s", (target, value))
        return self

    @dispatch
    @_with_lock
    def add(self, *args):
        self.cursor.execute(f"INSERT INTO {self.name} VALUES {args}")
        return self

    @dispatch
    @_with_lock
    def add(self, args: tuple):
        self.cursor.execute(f"INSERT INTO {self.name} VALUES {args}")
        return self

    @dispatch
    @_with_lock
    def add(self, arg: str):
        self.cursor.execute(f"INSERT INTO {self.name} VALUES ({arg})")

    @_with_lock
    def delete(self, key, value):
        self.cursor.execute(f"DELETE FROM {self.name} WHERE {key} = {value}")
        return self

    @_with_lock
    def find_exists(self, key, value):
        return bool(self.cursor.execute(f"SELECT * FROM {self.name} WHERE {key} = {value}"))


class Default:
    def __repr__(self):
        return 'default'


class Null:
    def __repr__(self):
        return 'null'


DEFAULT = Default()
NULL = Null()

LOG.INF('Connecting to MySQL database...')
sqldb = pymysql.connect(**CONFIG['sql_config'])
LOG.INF(f'Connected to MySQL database: {sqldb.get_server_info()} at {sqldb.host}:{sqldb.port}')
LOG.INF('Loading database tables...')
USER_TABLE = Table(sqldb, 'qq_users')
STOCK_TABLE = Table(sqldb, 'stocks')
GROUP_OPTION_TABLE = Table(sqldb, 'group_options')
NOTICE_SCHEDULE_TABLE = Table(sqldb, 'notice_schedule')
AI_MESSAGES_TABLE = Table(sqldb, 'ai_messages')
LOG.INF(
    'Loaded database tables:\n' +
    ',\n'.join(
        table.name for table in (
            USER_TABLE,
            STOCK_TABLE,
            GROUP_OPTION_TABLE,
            NOTICE_SCHEDULE_TABLE,
            AI_MESSAGES_TABLE
        )
    )
)
