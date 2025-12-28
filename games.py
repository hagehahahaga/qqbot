from typing import Optional

from abstract.bases.importer import itertools, PIL, io

from abstract.game import BaseGame, GameManager, GAME_MANAGER
from abstract.message import GroupMessage, TextMessage, ImageMessage, AtMessage
from abstract.target import User


@GAME_MANAGER.register_game
class TicTacToe(BaseGame):
    NAME = '井字棋'
    NEEDED_MEMBER_NUM = 2
    STARTING_TEXT = (
        '\n欢迎来到井字棋游戏.',
        '\n游戏发起者先手, 输入位置编号 (1-9) 进行落子.',
    )

    def __init__(self, game_manager: GameManager, owner: User):
        super().__init__(game_manager, owner)
        # 初始化井字棋游戏状态
        self.round_loop = itertools.cycle(self.members)
        self.board = list(map(str, range(1,10)))  # 3x3 棋盘
        self.chess_symbols: Optional[dict[int, str]] = None
        self.current_player = None

    def _render_board(self) -> bytes:
        image = PIL.Image.new('RGB', (300, 300), color='white')
        draw = PIL.ImageDraw.Draw(image)
        # 画网格线
        for i in range(1, 3):
            draw.line((0, i * 100, 300, i * 100), fill='black', width=2)
            draw.line((i * 100, 0, i * 100, 300), fill='black', width=2)
        # 画棋子 - 使用调整大小后的默认字体
        default_font = PIL.ImageFont.load_default()
        # 创建更大的字体变体
        font = default_font.font_variant(size=40)
        for i, cell in enumerate(self.board):
            # 计算文字居中位置
            bbox = draw.textbbox((0, 0), cell, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (i % 3) * 100 + 50 - text_width // 2
            y = (i // 3) * 100 + 50 - text_height // 2
            draw.text((x, y), cell, fill='black', font=font)
        # 保存图片到字节流
        byte_io = io.BytesIO()
        try:
            image.save(byte_io, format='PNG')
            byte_io.seek(0)
            return byte_io.read()
        finally:
            byte_io.close()

    def _check_winner(self) -> Optional[int]:
        winning_combinations = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # 横向
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # 纵向
            (0, 4, 8), (2, 4, 6)              # 对角线
        ]
        for combo in winning_combinations:
            s = set(self.board[i] for i in combo)
            if len(s) != 1:
                continue
            symbol = s.pop()
            for user, sym in self.chess_symbols.items():
                if sym == symbol:
                    return user
        return None
    
    def _is_draw(self) -> bool:
        # 检查是否所有位置都已被占用
        return all(cell in ['X', 'O'] for cell in self.board)

    def start(self, message: GroupMessage):
        self.chess_symbols = {self.members[0].id: 'X', self.members[1].id: 'O'}
        self.current_player = next(self.round_loop)
        message.reply(ImageMessage(self._render_board()))
        super().start(message)

    def handle(self, message: GroupMessage):
        text = message.get_parts_by_type(TextMessage)
        if not text:
            return
        args = text[0].to_args()
        if not args:
            return
        position = args[0]
        if not position.isdigit():
            return
        position = int(position)
        if not position in range(1, 10):
            return
        if message.sender != self.current_player:
            message.reply_text('现在不是你的回合.')
            return
        if self.board[position - 1] != str(position):
            message.reply_text('该位置已被占用, 请重新选择.')
            return
        self.board[position - 1] = self.chess_symbols[message.sender.id]
        message.reply(ImageMessage(self._render_board()))
        # 检查是否有玩家获胜
        winner_id = self._check_winner()
        if winner_id:
            self.winner = User(winner_id)
            message.reply(
                TextMessage('游戏结束: 获胜者 '),
                AtMessage(self.winner)
            )
            self.end()
        # 检查是否平局
        if self._is_draw():
            message.reply_text('游戏结束: 平局.')
            self.end()
        # 切换到下一位玩家
        self.current_player = next(self.round_loop)
        message.reply(
            TextMessage('下一位玩家: '),
            AtMessage(self.current_player)
        )


@GAME_MANAGER.register_game
class Gomoku(BaseGame):
    NAME = '五子棋'
    NEEDED_MEMBER_NUM = 2
    STARTING_TEXT = (
        '\n欢迎来到五子棋游戏.',
        '\n游戏发起者先手(黑棋), 输入坐标 (例如: 5 5) 进行落子.',
        '\n棋盘大小为 15x15, 坐标范围为 1-15.',
    )

    def __init__(self, game_manager: GameManager, owner: User):
        super().__init__(game_manager, owner)
        # 初始化五子棋游戏状态
        self.round_loop = itertools.cycle(self.members)
        self.board_size = 15
        self.board: list[list[Optional[str]]] = [[None for _ in range(self.board_size)] for _ in range(self.board_size)]  # 15x15 棋盘
        self.chess_symbols: Optional[dict[int, str]] = None
        self.current_player = None

    def _render_board(self) -> bytes:
        # 渲染 15x15 棋盘，每个格子 40px，留出 40px 用于坐标轴和数字
        cell_size = 40
        axis_size = 40
        board_size_px = self.board_size * cell_size
        total_size_px = board_size_px + axis_size
        
        # 创建画布，包含坐标轴区域
        image = PIL.Image.new('RGB', (total_size_px, total_size_px), color='#F5DEB3')  # 米黄色背景
        draw = PIL.ImageDraw.Draw(image)
        
        # 设置字体 - 使用调整大小后的默认字体
        default_font = PIL.ImageFont.load_default()
        # 创建更大的字体变体
        font = default_font.font_variant(size=24)
        
        # 绘制数字标记（左侧和顶部）
        for i in range(self.board_size):
            # 左侧数字（行号）
            text = str(i + 1)
            # 使用 textbbox 替代 textsize 获取文本尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (axis_size - text_width) // 2
            y = i * cell_size + axis_size + (cell_size - text_height) // 2
            draw.text((x, y), text, fill='black', font=font)
            
            # 顶部数字（列号）
            text = str(i + 1)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = i * cell_size + axis_size + (cell_size - text_width) // 2
            y = (axis_size - text_height) // 2
            draw.text((x, y), text, fill='black', font=font)
        
        # 画网格线（从坐标轴区域后开始）
        for i in range(self.board_size):
            # 横线
            y = i * cell_size + axis_size
            draw.line((axis_size, y, total_size_px, y), fill='black', width=2)
            # 竖线
            x = i * cell_size + axis_size
            draw.line((x, axis_size, x, total_size_px), fill='black', width=2)
        
        # 画棋子（调整坐标以适应坐标轴区域）
        for row in range(self.board_size):
            for col in range(self.board_size):
                cell = self.board[row][col]
                if not cell:
                    continue
                x = col * cell_size + axis_size + cell_size // 2
                y = row * cell_size + axis_size + cell_size // 2
                radius = cell_size // 2 - 5
                color = 'black' if cell == 'X' else 'white'
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline='black', width=2)
        
        # 保存图片到字节流
        byte_io = io.BytesIO()
        try:
            image.save(byte_io, format='PNG')
            byte_io.seek(0)
            return byte_io.read()
        finally:
            byte_io.close()

    def _check_direction(self, row: int, col: int, dx: int, dy: int) -> int:
        """检查指定方向上的连续棋子数量"""
        symbol = self.board[row][col]
        count = 1
        # 检查正方向
        for i in range(1, 5):
            new_row = row + dx * i
            new_col = col + dy * i
            if (0 <= new_row < self.board_size and 0 <= new_col < self.board_size and
                self.board[new_row][new_col] == symbol):
                count += 1
            else:
                break
        # 检查反方向
        for i in range(1, 5):
            new_row = row - dx * i
            new_col = col - dy * i
            if (0 <= new_row < self.board_size and 0 <= new_col < self.board_size and
                self.board[new_row][new_col] == symbol):
                count += 1
            else:
                break
        return count

    def _check_winner(self) -> Optional[int]:
        """检查是否有玩家获胜"""
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # 横向、纵向、主对角线、副对角线
        for row in range(self.board_size):
            for col in range(self.board_size):
                cell = self.board[row][col]
                if not cell:
                    continue
                # 检查四个方向
                for dx, dy in directions:
                    if self._check_direction(row, col, dx, dy) >= 5:
                        # 找到获胜者
                        for user_id, symbol in self.chess_symbols.items():
                            if symbol == cell:
                                return user_id
        return None
    
    def _is_draw(self) -> bool:
        """检查是否平局"""
        # 检查是否所有位置都已被占用
        return all(itertools.chain(*self.board))

    def start(self, message: GroupMessage):
        # 黑棋先行（X），白棋后行（O）
        self.chess_symbols = {self.members[0].id: 'X', self.members[1].id: 'O'}
        self.current_player = next(self.round_loop)
        message.reply(ImageMessage(self._render_board()))
        super().start(message)

    def handle(self, message: GroupMessage):
        text = message.get_parts_by_type(TextMessage)
        if not text:
            return

        args = text[0].to_args()
        if not args:
            return
        if not all(arg.isdigit() for arg in args):
            return

        if message.sender != self.current_player:
            message.reply_text('现在不是你的回合.')
            return

        if len(args) != 2:
            message.reply_text('请输入正确的坐标格式，例如: 5 5')
            return

        # 获取坐标
        col = int(args[0]) - 1
        row = int(args[1]) - 1

        # 检查坐标是否合法
        if not (row in range(self.board_size) and col in range(self.board_size)):
            message.reply_text(f'坐标超出范围，请输入 1-{self.board_size} 之间的数字')
            return

        if self.board[row][col]:
            message.reply_text('该位置已被占用, 请重新选择.')
            return

        # 落子
        self.board[row][col] = self.chess_symbols[message.sender.id]
        message.reply(ImageMessage(self._render_board()))

        # 检查是否有玩家获胜
        winner_id = self._check_winner()
        if winner_id:
            self.winner = User(winner_id)
            message.reply(
                TextMessage('游戏结束: 获胜者 '),
                AtMessage(self.winner)
            )
            self.end()
            return

        # 检查是否平局
        if self._is_draw():
            message.reply_text('游戏结束: 平局.')
            self.end()
            return

        # 切换到下一位玩家
        self.current_player = next(self.round_loop)
        message.reply(
            TextMessage('下一位玩家: '),
            AtMessage(self.current_player)
        )
