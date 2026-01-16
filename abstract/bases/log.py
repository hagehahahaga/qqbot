from abstract.bases.importer import pathlib, queue, time, traceback

from abstract.bases.config import CONFIG


class _LogManager:
    class _Log:
        level = ['DEB', 'INF', 'WAR', 'ERR']

        def __init__(self, path: pathlib.Path, print_level='DEB', write_level='INF'):
            self.path = path
            self.path.touch()
            self.print_level = print_level
            self.write_level = write_level

        def set_print_level(self, level='DEB'):
            assert level in self.level
            self.print_level = level
            return self

        def set_write_level(self, level='DEB'):
            assert level in self.level
            self.write_level = level
            return self

        def _log(self, level: str, text: str):
            assert level in self.level
            stack = traceback.extract_stack()[-3]
            text = ' - '.join((
                f'[{level.upper()}]',
                time.strftime("%Y-%m-%d %H:%M:%S"),
                stack.filename,
                stack.lineno.__str__(),
                stack.name,
                text
            ))
            if self.level.index(self.write_level) <= self.level.index(level):
                with self.path.open(mode='a', encoding='utf-8') as file:
                    file.write(text + '\n')
            if self.level.index(self.print_level) <= self.level.index(level):
                print(text)
                LOGS_HISTORY.append(text)
                LOGS_UPDATE_QUEUE.put(text)

        def DEB(self, text):
            self._log('DEB', text)

        def INF(self, text):
            self._log('INF', text)

        def WAR(self, text: str | Exception):
            if isinstance(text, Exception):
                text = text.__repr__()
            self._log('WAR', text)

        def ERR(self, error: Exception):
            from abstract.target import User
            from abstract.message import PrivateMessage
            error = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            (
                    self.path.parent / f'{time.strftime("%Y%m%d %H%M%S")}.err'
            ).write_text(error)
            for id in CONFIG['operators']:
                PrivateMessage(
                    error,
                    User(id)
                ).send()
            self._log('ERR', error)

    def __new__(cls, path: pathlib.Path = pathlib.Path().cwd() / 'logs', max=10, print_level='DEB', write_level='INF'):
        if not path.exists():
            path.mkdir()
        list(
            map(
                lambda a: a.unlink(),
                sorted(
                    filter(
                        lambda b: b.suffix == '.log',
                        path.iterdir()
                    ),
                    reverse=True
                )[10:]
            )
        )
        return cls._Log(path / f'{time.strftime("%Y%m%d %H%M%S")}.log', print_level=print_level, write_level=write_level)


LOG = _LogManager(write_level=CONFIG.get('log_level', 'INF'))
LOGS_HISTORY = []
LOGS_UPDATE_QUEUE = queue.Queue()
