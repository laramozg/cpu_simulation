import enum
from codeerror import CodeError


class TokenType(enum.Enum):
    EOF = -1
    NEWLINE = 0
    NUMBER = 1
    IDENT = 2
    WORD = 3
    OPEN_PAREN_ROUND = 4
    CLOSE_PAREN_ROUND = 5
    COMMA = 6

    PRINT = 100
    INPUT = 101
    IF = 102
    ENDIF = 103
    WHILE = 104
    ENDWHILE = 105
    INT = 106
    STRING = 107

    EQ = 200
    PLUS = 201
    MINUS = 202
    ASTERISK = 203
    SLASH = 204
    EQEQ = 205
    NOTEQ = 206
    LT = 207
    LTEQ = 208
    GT = 209
    GTEQ = 210
    MOD = 211
    PLUSEQ = 212
    MINUSEQ = 213
    ASTERISKEQ = 214
    SLASHEQ = 215
    MODEQ = 216


class Token:
    def __init__(self, token_text: str, token_kind: TokenType):
        self.text = token_text
        self.kind = token_kind


class Lexer:
    def __init__(self, inp: str):
        self.source = inp + "\n"
        self.cur_char = ""
        self.cur_pos = -1
        self.__next_char()

    def __next_char(self):
        self.cur_pos += 1
        if self.cur_pos >= len(self.source):
            self.cur_char = "\0"
        else:
            self.cur_char = self.source[self.cur_pos]

    def __skip_whitespace(self):
        while self.cur_char in (" ", "\t", "\r"):
            self.__next_char()

    def __skip_comment(self):
        if self.cur_char == "/" and self.__peek() == "/":
            while self.cur_char != "\n":
                self.__next_char()

    def __peek(self):
        if self.cur_pos + 1 >= len(self.source):
            return "\0"
        return self.source[self.cur_pos + 1]

    def get_token(self):
        self.__skip_whitespace()
        self.__skip_comment()

        if self.cur_char == "+":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.PLUSEQ)
            else:
                token = Token(self.cur_char, TokenType.PLUS)

        elif self.cur_char == "-":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.MINUSEQ)
            else:
                token = Token(self.cur_char, TokenType.MINUS)

        elif self.cur_char == "*":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.ASTERISKEQ)
            else:
                token = Token(self.cur_char, TokenType.ASTERISK)

        elif self.cur_char == "/":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.SLASHEQ)
            else:
                token = Token(self.cur_char, TokenType.SLASH)

        elif self.cur_char == "%":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.MODEQ)
            else:
                token = Token(self.cur_char, TokenType.MOD)

        elif self.cur_char == "=":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.EQEQ)
            else:
                token = Token(self.cur_char, TokenType.EQ)

        elif self.cur_char == ">":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.GTEQ)
            else:
                token = Token(self.cur_char, TokenType.GT)

        elif self.cur_char == "<":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.LTEQ)
            else:
                token = Token(self.cur_char, TokenType.LT)

        elif self.cur_char == "!":
            if self.__peek() == "=":
                last_char = self.cur_char
                self.__next_char()
                token = Token(last_char + self.cur_char, TokenType.NOTEQ)
            else:
                raise CodeError("Need to use !=" + self.__peek())

        elif self.cur_char == "(":
            token = Token(self.cur_char, TokenType.OPEN_PAREN_ROUND)

        elif self.cur_char == ")":
            token = Token(self.cur_char, TokenType.CLOSE_PAREN_ROUND)

        elif self.cur_char == ",":
            token = Token(self.cur_char, TokenType.COMMA)

        elif self.cur_char == '"':
            self.__next_char()
            start_pos = self.cur_pos

            while self.cur_char != '"':
                if self.cur_char in ("\r", "\n", "\t", "\\", "%"):
                    raise CodeError("Illegal character in string")
                self.__next_char()

            tok_text = self.source[start_pos : self.cur_pos]
            token = Token(tok_text, TokenType.WORD)

        elif self.cur_char.isdigit():
            start_pos = self.cur_pos
            while self.__peek().isdigit():
                self.__next_char()
            if self.__peek() == ".":
                raise CodeError("Use only integers")
            tok_text = self.source[start_pos : self.cur_pos + 1]
            token = Token(tok_text, TokenType.NUMBER)

        elif self.cur_char.isalpha():
            start_pos = self.cur_pos
            while self.__peek().isalnum():
                self.__next_char()

            tok_text = self.source[start_pos : self.cur_pos + 1]
            keyword = None
            for kind in TokenType:
                if kind.name == tok_text.upper() and 100 <= kind.value < 200:
                    keyword = kind
                    break
            if keyword is None:
                token = Token(tok_text, TokenType.IDENT)
            else:
                token = Token(tok_text, keyword)

        elif self.cur_char == "\n":
            token = Token(self.cur_char, TokenType.NEWLINE)

        elif self.cur_char == "\0":
            token = Token("", TokenType.EOF)
        else:
            raise CodeError("Unknown token: " + self.cur_char)

        self.__next_char()
        return token
