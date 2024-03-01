import enum
from collections import namedtuple
import struct


class Opcode(str, enum.Enum):
    DATA = 0x0

    ADD = 0x1
    SUB = 0x2
    DIV = 0x3
    MUL = 0x4
    MOD = 0x5
    CMP = 0x6
    LOOP = 0x7
    LD = 0x8
    ST = 0x9
    JUMP = 0xA
    BEQ = 0xB
    BNE = 0xC
    BGE = 0xD
    BLE = 0xE
    BL = 0xF
    BG = 0x11

    NOP = 0x12
    HLT = 0x13
    CLA = 0x14
    IN = 0x15
    OUTC = 0x16
    OUT = 0x17
    INC = 0x10
    DEC = 0x21
    NEG = 0x22


addressed_commands = [
    Opcode.ADD,
    Opcode.SUB,
    Opcode.DIV,
    Opcode.MUL,
    Opcode.MOD,
    Opcode.CMP,
    Opcode.LOOP,
    Opcode.LD,
    Opcode.ST,
    Opcode.JUMP,
    Opcode.BEQ,
    Opcode.BNE,
    Opcode.BGE,
    Opcode.BLE,
    Opcode.BL,
    Opcode.BG,
]

unaddressed_commands = [
    Opcode.NOP,
    Opcode.HLT,
    Opcode.CLA,
    Opcode.IN,
    Opcode.OUTC,
    Opcode.OUT,
    Opcode.INC,
    Opcode.DEC,
    Opcode.NEG,
]


class AddressingMode(str, enum.Enum):
    NO_ADDRESS = 0x0
    ABSOLUTE = 0x2
    DIRECT = 0x1
    RELATIVE = 0x3


class Term(namedtuple("Term", "opcode arg arg_mode")):
    """Instruction description"""


def write_code(filename, code):
    with open(f"{filename}.bin", "wb") as f:
        for item in code:
            opcode_bytes = struct.pack("B", int(item["opcode"]))
            arg = item.get("arg")
            if arg is None:
                arg_bytes = struct.pack("H", 0000000000000000)
                arg_mode_bytes = struct.pack("B", 00000000)
            else:
                if item["opcode"] == Opcode.DATA:
                    arg_mode_bytes = struct.pack("B", 00000000)
                else:
                    arg_mode = item.get("arg_mode")
                    arg_mode_bytes = struct.pack("B", int(arg_mode, 16))
                arg_bytes = struct.pack(">h", arg)

            f.write(opcode_bytes + arg_mode_bytes + arg_bytes)

    with open(f"{filename}.txt", "w", encoding="utf-8") as ft:
        ft.write(f"{'< address >'.ljust(18)}     {'hexcode'.ljust(30)}    {'< mnemonica >'.ljust(30)}\n")
        intstr = read_code(filename)
        i = 0
        for item in code:
            arg = item.get("arg")
            if arg is None:
                ft.write(
                    f"{'0x'}{'{:0>8}'.format(hex(i)[2:].upper()).ljust(16)}   "
                    f"{'0x'}{'{:0>8}'.format(hex(int(intstr[i],2))[2:].upper()).ljust(30)}   "
                    f"{Opcode(item['opcode']).name}\n"
                )
            else:
                ft.write(
                    f"{'0x'}{'{:0>8}'.format(hex(i)[2:].upper()).ljust(16)}   "
                    f"{'0x'}{'{:0>8}'.format(hex(int(intstr[i], 2))[2:].upper()).ljust(30)}   "
                    f"{Opcode(item['opcode']).name} {item.get('arg')} "
                    f"{AddressingMode(item['arg_mode']).name}\n"
                )
            i += 1


def read_code(filename):
    code = []
    index = 0
    with open(f"{filename}.bin", "rb") as f:
        byte_code = f.read()

    while index < len(byte_code):
        opcode = bin(byte_code[index])[2:].zfill(6)
        index += 1
        arg_mode = bin(byte_code[index])[2:].zfill(2)
        index += 1
        arg = bin(int.from_bytes(byte_code[index: index + 2], byteorder="big"))[2:].zfill(24)
        index += 2
        instruction_binary = "{}{}{}".format(opcode, arg_mode, arg)
        code.append(instruction_binary)

    return code


def parser_to_name_instr(instr):
    res = ""
    for opcode in Opcode:
        if Opcode(opcode).value == str(int(instr[:6], 2)):
            res += Opcode(opcode).name + " "
    res += str(int(instr[8:], 2)) + " "
    for mode in AddressingMode:
        if AddressingMode(mode).value == str(int(instr[6:8], 2)):
            res += AddressingMode(mode).name
    return res
