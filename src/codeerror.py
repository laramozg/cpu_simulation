class CodeError(Exception):
    def __init__(self, msg: str):
        self.msg = msg

    def get_msg(self):
        return self.msg
