import random

from abstract.message import GroupMessage


class Repeater:
    def __init__(self):
        self.last_messages = {}

    def handle(self, message: GroupMessage):
        text = message.parts[0].text

        if message.target not in self.last_messages or text != self.last_messages[message.target]:
            self.last_messages[message.target] = text
            return

        if text == self.last_messages[message.target]:
            if random.choice([True, False]):
                message.send()

REPEATER = Repeater()
