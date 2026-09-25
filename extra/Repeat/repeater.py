import random

from abstract.message import GroupMessage
from abstract.target import Group


class Repeater:
    def __init__(self):
        self.last_messages: dict[Group, list[str | bool]] = {}

    def handle(self, message: GroupMessage):
        text = message.parts[0].text

        if message.target not in self.last_messages or text != self.last_messages[message.target][0]:
            self.last_messages[message.target] = [text, False]
            return

        if self.last_messages[message.target][1]:
            return

        if random.choice([True, False]):
            self.last_messages[message.target][1] = True
            message.send()


REPEATER = Repeater()
