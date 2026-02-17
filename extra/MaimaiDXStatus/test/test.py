import unittest
import pathlib
import os
from ..MaimaiDXStatusService import *


class MyTestCase(unittest.TestCase):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    api = MAIMAIDX_STATUS_SERVICE
    def test_image_generate(self):
        node = self.api.result[1]['6']
        pathlib.Path('status.png').write_bytes(node.render())
        pathlib.Path('status_night.png').write_bytes(node.render(True))
        pathlib.Path('stat.png').write_bytes(node.stat_render())
        pathlib.Path('all.png').write_bytes(self.api.render())
        pathlib.Path('all_night.png').write_bytes(self.api.render(True))


if __name__ == '__main__':
    unittest.main()
