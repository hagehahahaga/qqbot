from abstract.bases.importer import json, pathlib


class Config:
    def __init__(self, file: pathlib.Path = pathlib.Path('./config.json')):
        self.file = file
        if not self.file.exists():
            self.file.write_bytes(pathlib.Path('./config_default.json').read_bytes())
        self.data = self.read()

    def __getitem__(self, item):
        self.write()
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.write()

    def __delitem__(self, key):
        del self.data[key]
        self.write()

    def get(self, *args, **kwargs):
        """ Return the value for key if key is in the dictionary, else default. """
        return self.data.get(*args, **kwargs)

    def read(self):
        self.data = json.loads(self.file.read_text(encoding='utf-8'))
        return self.data

    def write(self):
        self.file.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding='utf-8')
        return self


CONFIG = Config()
