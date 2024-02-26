import re
from exceptions import Exceptions
from isa import Opcode, AddressingMode, addressed_commands
from lex import Lexer, TokenType


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.integers = {}
        self.strings = {}
        self.loop_ind = 0
        self.if_ind = 0
        self.exp_ind = 0
        self.instructions = []
        self.last_comparison_instr = None
        self.labels_indx = {}
        self.var_indx = {}
        self.variables = []
        self.cur_token = None
        self.peek_token = None
        self.__next_token()
        self.__next_token()

    def __next_token(self):
        self.cur_token = self.peek_token
        self.peek_token = self.lexer.get_token()

    def __check_token(self, kind: TokenType):
        return kind == self.cur_token.kind

    def __match(self, kind: TokenType):
        if not self.__check_token(kind):
            raise Exceptions("Need to use " + kind.name + ", instead of " + self.cur_token.kind.name)
        self.__next_token()

    def program(self):
        while self.__check_token(TokenType.NEWLINE):
            self.__next_token()

        while not self.__check_token(TokenType.EOF):
            self.statement()

        self.instructions.append({"opcode": Opcode.HLT})
        return self.__generate_machine_code_arr()

    @staticmethod
    def loop_begin(number: int):
        return "loop" + str(number)

    @staticmethod
    def loop_end(number: int):
        return "end_loop" + str(number)

    @staticmethod
    def index(label: str):
        return label + "index"

    @staticmethod
    def loop_arg_count(count: str):
        return count + "count"

    @staticmethod
    def loop_cointer(counter: str):
        return counter + "counter"

    def __add_variables(self):
        for var, value in self.integers.items():
            self.var_indx[var] = len(self.variables)
            self.variables.append({"opcode": Opcode.DATA, "arg": value, "arg_mode": AddressingMode.DIRECT})

        for var, value in self.strings.items():
            self.var_indx[self.index(var)] = len(self.variables)

            self.variables.append(
                {"opcode": Opcode.DATA, "arg": len(self.variables) + 2, "arg_mode": AddressingMode.ABSOLUTE}
            )
            self.var_indx[self.loop_arg_count(var)] = len(self.variables)

            self.var_indx[var] = len(self.variables)
            self.variables.append({"opcode": Opcode.DATA, "arg": len(value), "arg_mode": AddressingMode.DIRECT})
            for i in range(0, len(value)):
                letter = value[i]
                self.variables.append({"opcode": Opcode.DATA, "arg": ord(letter), "arg_mode": AddressingMode.DIRECT})
            self.var_indx[self.loop_cointer(var)] = len(self.variables)
            self.variables.append({"opcode": Opcode.DATA, "arg": 0, "arg_mode": AddressingMode.DIRECT})

    # Create extra variable for data store for the calculation process; put it in Term format to the 'variables' array
    def __create_exp_op(self):
        self.exp_ind += 1
        exp = "exp_op" + str(self.exp_ind)
        self.var_indx[exp] = len(self.variables)
        self.variables.append({"opcode": Opcode.DATA, "arg": 0, "arg_mode": AddressingMode.DIRECT})
        return exp

    def __create_and_save_to_exp_op(self):
        exp = self.__create_exp_op()
        self.instructions.append({"opcode": Opcode.ST, "arg": exp, "arg_mode": AddressingMode.ABSOLUTE})
        return exp

    # Add calculation instruction to the program for the calculation process
    def __create_exp_evaluation(self, opcode, exp1, exp2, exp_res):
        self.instructions.append({"opcode": Opcode.LD, "arg": exp1, "arg_mode": AddressingMode.ABSOLUTE})
        self.instructions.append({"opcode": opcode, "arg": exp2, "arg_mode": AddressingMode.ABSOLUTE})
        if exp_res is not None:
            self.instructions.append({"opcode": Opcode.ST, "arg": exp_res, "arg_mode": AddressingMode.ABSOLUTE})

    # Generate final code in Term format - add variables to the head, change variables and labels to their addresses
    def __generate_machine_code_arr(self):
        self.__add_variables()
        code = []
        code += self.variables

        for instr in self.instructions:
            if instr["opcode"] in addressed_commands:
                arg = instr["arg"]
                if re.search("[a-zA-Z]", str(arg)):
                    if arg in self.labels_indx:
                        arg = self.labels_indx[arg] + len(self.variables)
                    elif arg in self.var_indx:
                        arg = self.var_indx[arg]

                instr["arg"] = int(arg)
            code.append(instr)
        return code

    def statement(self):
        if self.__check_token(TokenType.PRINT):
            self.__next_token()
            self.__match(TokenType.OPEN_PAREN_ROUND)

            ident = self.cur_token.text
            self.__match(TokenType.IDENT)
            self.__match(TokenType.COMMA)
            print_type = self.cur_token.kind
            self.__next_token()
            self.__match(TokenType.CLOSE_PAREN_ROUND)

            if ident in self.integers:
                self.instructions.append({"opcode": Opcode.LD, "arg": ident, "arg_mode": AddressingMode.ABSOLUTE})
                if print_type == TokenType.STRING:
                    self.instructions.append({"opcode": Opcode.OUTC})
                elif print_type == TokenType.INT:
                    self.instructions.append({"opcode": Opcode.OUT})
                else:
                    raise Exceptions("Incorrect type in print")

            elif ident in self.strings:
                self.loop_ind += 1
                l_begin = self.loop_begin(self.loop_ind)
                l_end = self.loop_end(self.loop_ind)
                ptr = self.index(ident)
                l_count_symbol = self.loop_arg_count(ident)
                l_counter = self.loop_cointer(ident)
                self.instructions.append(
                    {"opcode": Opcode.LD, "arg": l_count_symbol, "arg_mode": AddressingMode.ABSOLUTE}
                )
                self.instructions.append({"opcode": Opcode.ST, "arg": l_counter, "arg_mode": AddressingMode.ABSOLUTE})
                self.labels_indx[l_begin] = len(self.instructions)

                self.instructions.append({"opcode": Opcode.LD, "arg": l_counter, "arg_mode": AddressingMode.ABSOLUTE})
                self.instructions.append({"opcode": Opcode.BEQ, "arg": l_end, "arg_mode": AddressingMode.DIRECT})
                self.instructions.append({"opcode": Opcode.DEC})
                self.instructions.append({"opcode": Opcode.ST, "arg": l_counter, "arg_mode": AddressingMode.ABSOLUTE})
                self.instructions.append({"opcode": Opcode.LD, "arg": ptr, "arg_mode": AddressingMode.RELATIVE})
                if print_type == TokenType.STRING:
                    self.instructions.append({"opcode": Opcode.OUTC})
                elif print_type == TokenType.INT:
                    self.instructions.append({"opcode": Opcode.OUT})
                else:
                    raise Exceptions("Incorrect type in print()")
                self.instructions.append({"opcode": Opcode.LD, "arg": ptr, "arg_mode": AddressingMode.ABSOLUTE})
                self.instructions.append({"opcode": Opcode.INC})
                self.instructions.append({"opcode": Opcode.ST, "arg": ptr, "arg_mode": AddressingMode.ABSOLUTE})
                self.instructions.append({"opcode": Opcode.JUMP, "arg": l_begin, "arg_mode": AddressingMode.DIRECT})
                self.labels_indx[l_end] = len(self.instructions)
            else:
                raise Exceptions("Invalid operation - try to print not defined variable - " + ident)

        elif self.__check_token(TokenType.IF):
            self.__next_token()

            self.__match(TokenType.OPEN_PAREN_ROUND)
            self.if_ind += 1

            if_end = "if_done" + str(self.if_ind)
            self.comparison()
            self.__match(TokenType.CLOSE_PAREN_ROUND)

            self.new_line()
            opcode = self.last_comparison_instr
            self.instructions.append({"opcode": opcode, "arg": if_end, "arg_mode": AddressingMode.DIRECT})

            while not self.__check_token(TokenType.ENDIF):
                self.statement()

            self.__match(TokenType.ENDIF)
            self.labels_indx[if_end] = len(self.instructions)

        elif self.__check_token(TokenType.WHILE):
            self.__next_token()
            self.__match(TokenType.OPEN_PAREN_ROUND)

            self.loop_ind += 1
            l_begin = self.loop_begin(self.loop_ind)
            l_end = self.loop_end(self.loop_ind)

            self.labels_indx[l_begin] = len(self.instructions)
            self.comparison()
            self.__match(TokenType.CLOSE_PAREN_ROUND)
            self.new_line()
            opcode = self.last_comparison_instr
            self.instructions.append({"opcode": opcode, "arg": l_end, "arg_mode": AddressingMode.DIRECT})

            while not self.__check_token(TokenType.ENDWHILE):
                self.statement()

            self.__match(TokenType.ENDWHILE)
            self.instructions.append({"opcode": Opcode.JUMP, "arg": l_begin, "arg_mode": AddressingMode.DIRECT})
            self.labels_indx[l_end] = len(self.instructions)

        elif self.__check_token(TokenType.INT):
            self.__next_token()
            ident = self.cur_token.text
            self.__match(TokenType.IDENT)
            self.__match(TokenType.EQ)
            self.integers[ident] = self.evaluate_expression()

        elif self.__check_token(TokenType.STRING):
            self.__next_token()
            ident = self.cur_token.text
            self.__match(TokenType.IDENT)
            self.__match(TokenType.EQ)

            word = self.cur_token.text
            self.strings[ident] = word
            self.__next_token()

        elif self.__check_token(TokenType.IDENT):
            ident = self.cur_token.text
            self.__next_token()
            operator = self.cur_token.kind
            if (
                self.__check_token(TokenType.EQ)
                or self.__check_token(TokenType.ASTERISKEQ)
                or self.__check_token(TokenType.MODEQ)
                or self.__check_token(TokenType.SLASHEQ)
                or self.__check_token(TokenType.MINUSEQ)
                or self.__check_token(TokenType.PLUSEQ)
            ):
                self.__next_token()
                self.expression()
                if operator == TokenType.EQ:
                    self.instructions.append({"opcode": Opcode.ST, "arg": ident, "arg_mode": AddressingMode.ABSOLUTE})
                else:
                    exp = self.__create_and_save_to_exp_op()
                    if operator == TokenType.PLUSEQ:
                        self.__create_exp_evaluation(opcode=Opcode.ADD, exp1=ident, exp2=exp, exp_res=ident)
                    elif operator == TokenType.MINUSEQ:
                        self.__create_exp_evaluation(opcode=Opcode.SUB, exp1=ident, exp2=exp, exp_res=ident)
                    elif operator == TokenType.SLASHEQ:
                        self.__create_exp_evaluation(opcode=Opcode.DIV, exp1=ident, exp2=exp, exp_res=ident)
                    elif operator == TokenType.ASTERISKEQ:
                        self.__create_exp_evaluation(opcode=Opcode.MUL, exp1=ident, exp2=exp, exp_res=ident)
                    elif operator == TokenType.MODEQ:
                        self.__create_exp_evaluation(opcode=Opcode.MOD, exp1=ident, exp2=exp, exp_res=ident)
                    else:
                        raise Exceptions("Invalid operator in assignment - " + ident)
            else:
                raise Exceptions("Invalid operation " + self.cur_token.text)

        elif self.__check_token(TokenType.INPUT):
            self.__next_token()
            self.__match(TokenType.OPEN_PAREN_ROUND)

            ident = self.cur_token.text

            if ident not in self.integers and ident not in self.strings:
                raise Exceptions("Invalid operation - try to read in not defined variable - " + ident)

            self.__match(TokenType.IDENT)
            self.instructions.append({"opcode": Opcode.IN})
            self.instructions.append({"opcode": Opcode.ST, "arg": ident, "arg_mode": AddressingMode.ABSOLUTE})
            self.__match(TokenType.CLOSE_PAREN_ROUND)

        else:
            raise Exceptions("Invalid statement at " + self.cur_token.text + " (" + self.cur_token.kind.name + ")")

        self.new_line()

    def new_line(self):
        self.__match(TokenType.NEWLINE)
        while self.__check_token(TokenType.NEWLINE):
            self.__next_token()

    def comparison(self):
        self.expression()
        if (
            self.__check_token(TokenType.GT)
            or self.__check_token(TokenType.GTEQ)
            or self.__check_token(TokenType.LT)
            or self.__check_token(TokenType.LTEQ)
            or self.__check_token(TokenType.EQEQ)
            or self.__check_token(TokenType.NOTEQ)
        ):
            exp_id1 = self.__create_and_save_to_exp_op()
            operator = self.cur_token.text
            self.__next_token()
            self.expression()
            exp_id2 = self.__create_and_save_to_exp_op()
            self.__create_exp_evaluation(opcode=Opcode.CMP, exp1=exp_id1, exp2=exp_id2, exp_res=None)
            if operator == "==":
                self.last_comparison_instr = Opcode.BNE
            elif operator == "!=":
                self.last_comparison_instr = Opcode.BEQ
            elif operator == ">=":
                self.last_comparison_instr = Opcode.BL
            elif operator == "<=":
                self.last_comparison_instr = Opcode.BG
            elif operator == "<":
                self.last_comparison_instr = Opcode.BGE
            elif operator == ">":
                self.last_comparison_instr = Opcode.BLE
        else:
            raise Exceptions("Expected comparison operator at: " + self.cur_token.text)

    def expression(self):
        self.term()
        if self.__check_token(TokenType.PLUS) or self.__check_token(TokenType.MINUS):
            exp1 = self.__create_exp_op()
            while self.__check_token(TokenType.PLUS) or self.__check_token(TokenType.MINUS):
                self.instructions.append({"opcode": Opcode.ST, "arg": exp1, "arg_mode": AddressingMode.ABSOLUTE})
                operator = self.cur_token.text
                self.__next_token()
                self.term()
                exp2 = self.__create_and_save_to_exp_op()
                if operator == "+":
                    self.__create_exp_evaluation(opcode=Opcode.ADD, exp1=exp1, exp2=exp2, exp_res=None)
                elif operator == "-":
                    self.__create_exp_evaluation(opcode=Opcode.SUB, exp1=exp1, exp2=exp2, exp_res=None)

    def term(self):
        self.unary()
        if (
            self.__check_token(TokenType.ASTERISK)
            or self.__check_token(TokenType.SLASH)
            or self.__check_token(TokenType.MOD)
        ):
            exp1 = self.__create_exp_op()
            while (
                self.__check_token(TokenType.ASTERISK)
                or self.__check_token(TokenType.SLASH)
                or self.__check_token(TokenType.MOD)
            ):
                self.instructions.append({"opcode": Opcode.ST, "arg": exp1, "arg_mode": AddressingMode.ABSOLUTE})
                operator = self.cur_token.text
                self.__next_token()
                self.unary()
                exp2 = self.__create_and_save_to_exp_op()
                if operator == "/":
                    self.__create_exp_evaluation(opcode=Opcode.DIV, exp1=exp1, exp2=exp2, exp_res=None)
                elif operator == "*":
                    self.__create_exp_evaluation(opcode=Opcode.MUL, exp1=exp1, exp2=exp2, exp_res=None)
                elif operator == "%":
                    self.__create_exp_evaluation(opcode=Opcode.MOD, exp1=exp1, exp2=exp2, exp_res=None)

    def unary(self):
        token = None
        if self.__check_token(TokenType.PLUS) or self.__check_token(TokenType.MINUS):
            if self.__check_token(TokenType.MINUS):
                token = "-"
            self.__next_token()
        self.primary()
        if token == "-":
            self.instructions.append({"opcode": Opcode.NEG})

    def primary(self):
        if self.__check_token(TokenType.NUMBER):
            self.instructions.append(
                {"opcode": Opcode.LD, "arg": self.cur_token.text, "arg_mode": AddressingMode.DIRECT}
            )
            self.__next_token()
        elif self.__check_token(TokenType.IDENT):
            if self.cur_token.text not in self.integers:
                raise Exceptions("Referencing variable before assignment: " + self.cur_token.text)

            self.instructions.append(
                {"opcode": Opcode.LD, "arg": self.cur_token.text, "arg_mode": AddressingMode.ABSOLUTE}
            )
            self.__next_token()
        else:
            raise Exceptions("Unexpected token at " + self.cur_token.text)

    def evaluate_expression(self):
        res = self.evaluate_term()

        while self.__check_token(TokenType.PLUS) or self.__check_token(TokenType.MINUS):
            operator = self.cur_token.text
            self.__next_token()
            term = self.evaluate_term()
            if operator == "+":
                res = res + term
            elif operator == "-":
                res = res - term
        return res

    def evaluate_term(self):
        res = self.evaluate_unary()

        while (
            self.__check_token(TokenType.ASTERISK)
            or self.__check_token(TokenType.SLASH)
            or self.__check_token(TokenType.MOD)
        ):
            operator = self.cur_token.text
            self.__next_token()
            unary = self.evaluate_unary()
            if operator == "/":
                res = res // unary
            elif operator == "*":
                res = res * unary
            elif operator == "%":
                res = res % unary
        return res

    def evaluate_unary(self):
        sign = 1
        if self.__check_token(TokenType.PLUS) or self.__check_token(TokenType.MINUS):
            if self.__check_token(TokenType.MINUS):
                sign = -1
            self.__next_token()

        return self.evaluate_primary() * sign

    def evaluate_primary(self):
        if self.__check_token(TokenType.NUMBER):
            res = int(self.cur_token.text)
            self.__next_token()
        elif self.__check_token(TokenType.IDENT):
            if self.cur_token.text not in self.integers:
                raise Exceptions("Referencing variable before assignment: " + self.cur_token.text)

            res = int(self.integers[self.cur_token.text])
            self.__next_token()
        else:
            raise Exceptions("Unexpected token at " + self.cur_token.text)
        return res
