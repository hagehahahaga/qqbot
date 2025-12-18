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
        # 画棋子
        for i, cell in enumerate(self.board):
            x = (i % 3) * 100 + 50
            y = (i // 3) * 100 + 50
            draw.text((x, y), cell, fill='black', font=PIL.ImageFont.truetype("arial.ttf", 40))
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
        super().start(message)
        self.chess_symbols = {self.members[0].id: 'X', self.members[1].id: 'O'}
        self.current_player = next(self.round_loop)
        message.reply(ImageMessage(self._render_board()))

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
