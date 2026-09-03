# extra/__init__.py
# 自动导入目录下的所有包
from abstract.bases.importer import os, importlib

from abstract.bases.log import LOG

# 获取 extra 目录下的所有子目录
# 仅导入非下划线前缀(私有/测试库)且含 __init__.py 的常规包
current_dir = os.path.dirname(__file__)
subdirs = [d for d in os.listdir(current_dir)
           if os.path.isdir(os.path.join(current_dir, d))
           and not d.startswith('_')
           and os.path.isfile(os.path.join(current_dir, d, '__init__.py'))]

# 导入每个子目录作为模块
for subdir in subdirs:
    # 构建模块路径
    module_name = f"extra.{subdir}"
    # 导入模块
    importlib.import_module(module_name)
    LOG.INF(f'Module {module_name} loaded.')
