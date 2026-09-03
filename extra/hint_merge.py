"""
extra/hint_merge.py
===================

检查 extra 组件类型存根与注册代码的一致性, 并将所有 extra 的 target.pyi
与 abstract/target_core.pyi 合并, 生成 abstract/target.pyi.

功能:
1. 对等性检查: 每个 extra 组件的 target.pyi 中注解的成员(方法/属性),
   必须与 register.py 中实际注册到 User/Group 的成员一致.
   (注意: 同一个函数可同时注册到多个类, 如 @Group.register_attr 叠加 @User.register_attr)
2. 冲突检查: 所有 extra 的 target.pyi 中, 同一类(User/Group)的同一成员名
   不得被多个组件注册.
3. 合并: 通过检查后, 将各 extra 的 target.pyi 与 abstract/target_core.pyi
   合并输出为 abstract/target.pyi. (因已检查冲突, 无需处理 override)

用法:
    python extra/hint_merge.py
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRA_DIR = ROOT / 'extra'
CORE_PYI = ROOT / 'abstract' / 'target_core.pyi'
OUTPUT_PYI = ROOT / 'abstract' / 'target.pyi'

TARGET_CLASSES = ('User', 'Group')
REGISTER_DECORATOR = 'register_attr'  # abstract.target 上实际使用的注册装饰器名
PACKAGE = 'target'  # register.py 中导入 User/Group 的来源模块名(末尾段)

if sys.version_info < (3, 12):
    sys.exit('此脚本依赖 PEP 695 泛型语法解析, 需要 Python 3.12+.')


def _init_members() -> dict[str, set[str]]:
    return {cls: set() for cls in TARGET_CLASSES}


# ---------- 解析 ----------

def parse_pyi_members(pyi_path: Path) -> dict[str, set[str]]:
    """解析 .pyi 存根, 返回每个类下声明的成员名集合(属性/方法)."""
    tree = ast.parse(pyi_path.read_text(encoding='utf-8'))
    members = _init_members()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in TARGET_CLASSES:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # property 的 getter/setter 同名, set 天然去重
                    members[node.name].add(item.name)
    return members


def _resolve_class(value: ast.AST, aliases: dict[str, str]) -> str | None:
    """将装饰器值(User / Group / 别名 / 完整路径)解析为类名."""
    if isinstance(value, ast.Name):
        return aliases.get(value.id)
    if isinstance(value, ast.Attribute) and value.attr in TARGET_CLASSES:
        return value.attr
    return None


def parse_register_members(reg_path: Path) -> dict[str, set[str]]:
    """解析 register.py, 返回注册到每个类的成员名集合.

    register.py 中形如 @User.register_attr / @Group.register_attr 的装饰器
    决定注册目标, 同一函数可同时携带多个该类装饰器(注册到多个类).
    属性的 setter/getter 通过同名 def 携带注册装饰器, 亦由此捕获.
    """
    tree = ast.parse(reg_path.read_text(encoding='utf-8'))

    # 解析类名别名: from abstract.target import User as U 等
    aliases = {cls: cls for cls in TARGET_CLASSES}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split('.')[-1] == PACKAGE:
                for alias in node.names:
                    if alias.name in TARGET_CLASSES:
                        aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[-1] == PACKAGE and alias.asname:
                    # import abstract.target as T 形式, 极少见, 仅覆盖最简场景
                    aliases[alias.asname] = 'User' if 'User' in alias.name else 'Group'

    registered = _init_members()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute) and decorator.attr == REGISTER_DECORATOR:
                    cls = _resolve_class(decorator.value, aliases)
                    if cls in TARGET_CLASSES:
                        registered[cls].add(node.name)
    return registered


# ---------- 检查 ----------

def check_equivalence(name: str, pyi: dict[str, set[str]], reg: dict[str, set[str]]) -> list[str]:
    """对等性检查: pyi 声明与 register 注册双向一致."""
    problems = []
    for cls in TARGET_CLASSES:
        declared, registered = pyi[cls], reg[cls]
        if declared - registered:
            problems.append(f'{name}: {cls} 在 target.pyi 中声明但 register.py 未注册 -> {sorted(declared - registered)}')
        if registered - declared:
            problems.append(f'{name}: {cls} 在 register.py 中注册但 target.pyi 未声明 -> {sorted(registered - declared)}')
    return problems


def check_conflicts(components: list[tuple[str, dict[str, set[str]]]]) -> list[str]:
    """跨 extra 冲突检查: 同一类(User/Group)的同一成员名不得被多个组件注册."""
    holder: dict[tuple[str, str], list[str]] = {}
    for name, members in components:
        for cls in TARGET_CLASSES:
            for member in members[cls]:
                holder.setdefault((cls, member), []).append(name)
    return [
        f'冲突: {cls}.{member} 被多个 extra 注册 -> {names}'
        for (cls, member), names in holder.items()
        if len(names) > 1
    ]


# ---------- 合并 ----------

def _node_lines(lines: list[str], node: ast.AST) -> list[str]:
    """取 AST 节点(含装饰器)对应的原始文本行."""
    start = min((d.lineno for d in getattr(node, 'decorator_list', [])), default=node.lineno)
    return lines[start - 1: node.end_lineno]


def _join(block: list[str]) -> str:
    text = ''.join(block)
    return text if text.endswith('\n') else text + '\n'


def extract_blocks(path: Path) -> dict:
    """将 .pyi 拆分为 imports / 其他顶层块 / 各类的声明行与 body."""
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    top = tree.body

    imports, others, classes = [], [], {}
    for node in top:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(_join(_node_lines(lines, node)))
        elif isinstance(node, ast.ClassDef) and node.name in TARGET_CLASSES:
            classes[node.name] = node
        else:
            others.append(_join(_node_lines(lines, node)))

    sorted_top = sorted(top, key=lambda n: n.lineno)
    class_header, class_body = {}, {}
    for cls in TARGET_CLASSES:
        node = classes.get(cls)
        if node is None:
            class_header[cls] = None
            class_body[cls] = []
            continue
        end = len(lines)
        for other in sorted_top:
            if other.lineno > node.lineno:
                end = other.lineno - 1
                break
        segment = lines[node.lineno - 1: end]
        class_header[cls] = _join(segment[:1])
        class_body[cls] = segment[1:]
    return {
        'imports': imports,
        'others': others,
        'class_header': class_header,
        'class_body': class_body,
    }


def merge(core: dict, extras: list[dict], output: Path) -> None:
    """合并 core 与各 extra 的块, 写出 abstract/target.pyi."""
    chunks: list[str] = ['# 此文件由 extra/hint_merge.py 自动生成, 请勿手动编辑.\n']

    # imports: 全部收集并按文本去重, core 在前
    seen_imports: set[str] = set()
    for source in [core, *extras]:
        for imp in source['imports']:
            key = imp.strip()
            if key not in seen_imports:
                seen_imports.add(key)
                chunks.append(imp)
    chunks.append('\n')

    # 其他顶层块: core 在前, 各 extra 依次在后(TypedDict 等类型定义)
    chunks.extend(core['others'])
    for extra in extras:
        chunks.extend(extra['others'])
    chunks.append('\n')

    # 类体: core 成员在前, 各 extra 成员依次追加
    for cls in TARGET_CLASSES:
        header = core['class_header'][cls]
        if header is None:
            continue
        chunks.append(header)
        chunks.extend(core['class_body'][cls])
        for extra in extras:
            chunks.extend(extra['class_body'].get(cls, []))
        chunks.append('\n')

    output.write_text(''.join(chunks), encoding='utf-8')
    ast.parse(output.read_text(encoding='utf-8'))  # 生成结果语法校验


# ---------- 入口 ----------

def main() -> int:
    if not CORE_PYI.exists():
        print(f'缺少核心存根: {CORE_PYI}')
        return 1

    components: list[tuple[str, dict[str, set[str]]]] = []
    problems: list[str] = []

    for directory in sorted(EXTRA_DIR.iterdir()):
        if not directory.is_dir() or directory.name.startswith('_'):
            continue
        if not (directory / '__init__.py').is_file():
            # 与 extra/__init__.py 过滤逻辑一致: 仅处理含 __init__.py 的常规包
            continue
        pyi_path = directory / 'target.pyi'
        reg_path = directory / 'register.py'
        if not pyi_path.exists():
            if reg_path.exists():
                print(f'提示: {directory.name} 存在 register.py 但缺少 target.pyi, 已跳过.')
            continue
        if not reg_path.exists():
            problems.append(f'{directory.name}: 存在 target.pyi 但缺少 register.py.')
            continue

        pyi_members = parse_pyi_members(pyi_path)
        reg_members = parse_register_members(reg_path)
        components.append((directory.name, pyi_members))
        problems.extend(check_equivalence(directory.name, pyi_members, reg_members))

    if not components:
        print('未找到任何含 target.pyi 的 extra 组件.')
        return 1

    problems.extend(check_conflicts(components))

    if problems:
        print('检查未通过, 不会生成 abstract/target.pyi:')
        for problem in problems:
            print(f'  - {problem}')
        return 1

    core = extract_blocks(CORE_PYI)
    extras = [extract_blocks(EXTRA_DIR / name / 'target.pyi') for name, _ in components]
    try:
        merge(core, extras, OUTPUT_PYI)
    except SyntaxError as error:
        print(f'合并结果语法错误, 未写入: {error}')
        return 1

    print(f'检查通过, 已生成 {OUTPUT_PYI.relative_to(ROOT)}:')
    for name, members in components:
        total = sum(len(members[cls]) for cls in TARGET_CLASSES)
        detail = ', '.join(f'{cls}: {len(members[cls])}' for cls in TARGET_CLASSES if members[cls])
        print(f'  - {name}: 共 {total} 个成员 ({detail})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
