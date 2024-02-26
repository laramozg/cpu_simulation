import sys

from isa import write_code
from lex import Lexer
from parse import Parser, CodeError


def main(args):
    assert len(args) == 2, "Wrong arguments: translate.py <input_file> <target_file>"
    source, target = args

    with open(source, "rt", encoding="utf-8") as file:
        source = file.read()

    lexer = Lexer(source)
    parser = Parser(lexer)

    try:
        code = parser.program()
        print("source LoC:", len(source.split("\n")), " code instr:", len(code))
        write_code(target, code)
    except CodeError as exception:
        print(exception.get_msg())


if __name__ == "__main__":
    main(sys.argv[1:])
