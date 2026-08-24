class SendFailure(Exception):
    """
    The frame_server available but the message send failed
    """
    def __init__(self, text: str, message_data):
        """
        :type text: str
        :type message_data: MESSAGE
        """
        self.text = text
        self.message_data = message_data

    def __str__(self):
        return f'发送失败: {self.text}'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.text}> at {hex(id(self))}\nmessage: {self.message_data}'


class GroupNotJoined(SendFailure):
    """
    Exception raised when the specified group is not joined.
    """
    def __init__(self, group):
        """
        :type group: abstract.target.Group
        """
        self.group = group

    def __str__(self):
        return f'发送失败: 不在群聊{self.group}中.'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.group}> at {hex(id(self))}'


class PrivateChatFailed(SendFailure):
    """
    Exception raised when the private chat failed due to user's qq option.
    """
    def __init__(self, user):
        """
        :type user: abstract.target.User
        """
        self.user = user

    def __str__(self):
        return f'发送失败: 无法私聊{self.user}, 可能因对方隐私设置或群聊设置.'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.user}> at {hex(id(self))}'


class CommandCancel(BaseException):
    """
    The command is canceled
    """
    def __init__(self, text=''):
        """
        :type text: str
        """
        self.text = text

    def __str__(self):
        return f'命令取消: {self.text}'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.text}> at {hex(id(self))}'


class SessionTransfer(BaseException):
    ...
