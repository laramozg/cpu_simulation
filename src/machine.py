import sys
import enum
import logging
from exceptions import Exceptions
from isa import AddressingMode, Opcode, parser_to_name_instr
from device import Device
from isa import read_code

START_ADDR = 0  #cat 3/ hello 15 / hello user / prob1 24
MEMORY_SIZE = 2048
WORD_SIZE = 32
WORD_INIT = 0
MAX_WORD = int(2 ** (WORD_SIZE - 1) - 1)
MIN_WORD = int(-2 ** (WORD_SIZE - 1))
MAX_ADDR = MEMORY_SIZE - 1


class AluOperation(str, enum.Enum):
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    INC = "INC"
    DEC = "DEC"
    CLA = "CLA"


opcode_to_alu_operation = {
    Opcode.ADD: AluOperation.ADD,
    Opcode.SUB: AluOperation.SUB,
    Opcode.MUL: AluOperation.MUL,
    Opcode.DIV: AluOperation.DIV,
    Opcode.MOD: AluOperation.MOD,
    Opcode.CMP: AluOperation.SUB,
    Opcode.INC: AluOperation.INC,
    Opcode.DEC: AluOperation.DEC,
    Opcode.CLA: AluOperation.CLA

}


class ALU:
    def __init__(self):
        self.left = 0
        self.right = 0
        self.N = 0
        self.Z = 0
        self.C = 0

    def set_flags(self, res):
        self.N = 1 if res < 0 else 0
        self.Z = 1 if res == 0 else 0

    @staticmethod
    def check_value(val: int):
        if val > MAX_WORD or val < MIN_WORD:
            raise Exceptions('Overflow error!')
        return val

    def alu_calculate(self, left, right, operation: AluOperation, sel_left: bool = True, sel_right: bool = True):
        left_operand = int(left, 2) if sel_left else 0
        right_operand = int(right,2) if sel_right else 0
        res = None
        if operation == AluOperation.ADD:
            res = left_operand + right_operand

        elif operation == AluOperation.SUB:
            res = left_operand - right_operand

        elif operation == AluOperation.MUL:
            res = left_operand * right_operand

        elif operation == AluOperation.DIV:
            if not right_operand:
                raise Exceptions('Error! Trying to get DIV operation from 0')
            res = left_operand // right_operand

        elif operation == AluOperation.MOD:
            if not right_operand:
                raise Exceptions('Error! Trying to get MOD operation from 0')
            res = left_operand % right_operand

        elif operation == AluOperation.INC:
            res = left_operand + 1

        elif operation == AluOperation.DEC:
            res = left_operand - 1

        elif operation == AluOperation.CLA:
            res = 0

        self.set_flags(res)
        return self.check_value(res)


class DataPath:
    registers = {"AC": 0, "AR": 0, "IP": 0, "DR": 0, "CR": 0, "BR": 0}
    memory = []
    alu = ALU()

    def __init__(self, program: list):
        self.memory = program
        for _ in range(len(self.memory), MEMORY_SIZE):
            self.memory.append('00000001000000000000000000000000')

    def get_reg(self, reg):
        return self.registers[reg]

    def set_reg(self, reg, val):
        self.registers[reg] = val

    def wr(self):
        self.memory[self.registers["AR"]] = '00000000' + str(self.registers["DR"])

    def rd(self):
        self.registers["DR"] = self.memory[self.registers["AR"]]


class ControlUnit:

    def __init__(self, program: list, device: Device, data_path):
        self.memory = program.copy()
        self.data_path = data_path
        self.tact = 0
        self.sig_latch_reg("IP", START_ADDR)
        self.device = device
        self.instr = 0

    def sig_latch_reg(self, reg, val):
        self.data_path.set_reg(reg, val)

    def get_reg(self, reg):
        return self.data_path.get_reg(reg)

    def sig_write(self):
        self.data_path.wr()

    def sig_read(self):
        self.data_path.rd()

    def __tick(self):
        self.tact += 1

    def operand_fetch(self, arg_mode):
        if arg_mode == AddressingMode.DIRECT.value:
            self.sig_latch_reg("BR", self.get_reg("CR")[8:])
            self.__tick()
            self.sig_latch_reg("DR", self.get_reg("BR"))
            self.__tick()
        elif arg_mode == AddressingMode.ABSOLUTE.value:
            self.sig_latch_reg("AR", int(self.get_reg("DR")[8:], 2))
            self.__tick()
            self.sig_read()
            self.__tick()

        elif arg_mode == AddressingMode.RELATIVE.value:
            self.sig_latch_reg("AR", int(self.get_reg("DR")[8:], 2))
            self.__tick()
            self.sig_read()
            self.__tick()
            self.sig_latch_reg("AR", int(self.get_reg("DR")[8:], 2))
            self.__tick()
            self.sig_read()
            self.__tick()

    def instruction_fetch(self, arg: int):
        self.sig_latch_reg("AR", self.get_reg("IP"))
        self.sig_latch_reg("BR", self.get_reg("IP"))
        self.__tick()
        self.sig_latch_reg("IP", self.get_reg("BR")+1)
        self.sig_read()
        self.__tick()
        self.sig_latch_reg("CR", self.get_reg("DR"))
        self.__tick()

    def decode_and_execute_instruction(self):
        instr = self.memory[self.get_reg("IP")]
        self.instruction_fetch(instr)
        opcode = str(int(instr[:6], 2))
        arg_mode = str(int(instr[6:8], 2))

        if opcode == Opcode.HLT.value:
            raise StopIteration()

        elif opcode == Opcode.LD.value:
            self.operand_fetch(arg_mode)
            self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), AluOperation.ADD, False)
            self.sig_latch_reg("AC", self.get_reg("DR"))
            self.__tick()

        elif opcode == Opcode.ST.value:
            self.sig_latch_reg("AR", int(self.get_reg("DR")[8:], 2))
            self.__tick()
            self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), AluOperation.ADD, True, False)
            self.sig_latch_reg("DR", self.get_reg("AC"))
            self.__tick()
            self.sig_write()
            self.__tick()

        elif opcode in [Opcode.ADD.value, Opcode.SUB.value, Opcode.MUL.value, Opcode.DIV.value, Opcode.MOD.value, Opcode.CMP.value]:
            self.operand_fetch(arg_mode)
            res = self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), opcode_to_alu_operation[Opcode(opcode)])
            if opcode not in Opcode.CMP:
                self.sig_latch_reg("AC", bin(res)[2:])
            self.__tick()

        elif opcode == Opcode.INC.value:
            res = self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), AluOperation.INC, True, False)
            self.sig_latch_reg("AC", bin(res)[2:])
            self.__tick()

        elif opcode == Opcode.DEC.value:
            res = self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), AluOperation.DEC, True, False)
            self.sig_latch_reg("AC", bin(res)[2:])
            self.__tick()

        elif opcode == Opcode.CLA.value:
            self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), AluOperation.CLA, False, False)
            self.sig_latch_reg("AC", bin(0)[2:])
            self.__tick()

        elif opcode == Opcode.NEG.value:
            res = self.data_path.alu.alu_calculate(self.get_reg("AC"), self.get_reg("DR"), AluOperation.MUL)
            res1 = self.data_path.alu.alu_calculate(bin(res)[2:], self.get_reg("DR"), AluOperation.INC)
            self.sig_latch_reg("AC", bin(res1)[2:])
            self.__tick()

        elif opcode == Opcode.IN.value:
            self.device.read()
            val = self.device.io
            logging.info(f"{{info_buffer: {self.device.input} >> {val}}}")
            self.sig_latch_reg("AC", bin(val)[2:])
            self.__tick()

        elif opcode == Opcode.OUTC.value:

            val = chr(int(self.get_reg("AC"),2))
            self.device.io = val
            self.device.write()
            logging.info(f"{{output_buffer: {self.device.output} << {val}}}")
            self.__tick()

        elif opcode == Opcode.OUT.value:
            val = str(int(self.get_reg("AC"),2))
            self.device.io = val
            self.device.write()
            logging.info(f"{{output_buffer: {self.device.output} << {val}}}")
            self.__tick()

        elif opcode == Opcode.JUMP.value:
            self.sig_latch_reg("IP", int(self.get_reg("DR")[8:], 2))
            self.__tick()

        elif opcode == Opcode.LOOP.value:
            self.operand_fetch(arg_mode)
            res = self.data_path.alu.alu_calculate(self.get_reg("DR"), self.get_reg("AC"), AluOperation.DEC)
            self.sig_latch_reg("DR", bin(res)[2:])
            self.__tick()
            self.sig_write()
            self.__tick()
            if self.data_path.alu.N or self.data_path.alu.Z:
                self.sig_latch_reg("IP", self.get_reg("IP")+1)
                self.__tick()

        elif opcode == Opcode.BEQ.value:
            if self.data_path.alu.Z:
                self.sig_latch_reg("IP", int(self.get_reg("DR")[8:], 2))
                self.__tick()

        elif opcode == Opcode.BNE.value:
            if not self.data_path.alu.Z:
                self.sig_latch_reg("IP", int(self.get_reg("DR")[8:], 2))
                self.__tick()

        elif opcode == Opcode.BGE.value:
            # ~(n ^ v)
            if not self.data_path.alu.N:
                self.sig_latch_reg("IP", int(self.get_reg("DR")[8:], 2))
                self.__tick()

        elif opcode == Opcode.BLE.value:
            # z | (n ^ v)
            if self.data_path.alu.Z | self.data_path.alu.N:
                self.sig_latch_reg("IP",int(self.get_reg("DR")[8:],2))
                self.__tick()

        elif opcode == Opcode.BL.value:
            # n ^ v
            if self.data_path.alu.N:
                self.sig_latch_reg("IP", int(self.get_reg("DR")[8:], 2))
                self.__tick()

        elif opcode == Opcode.BG.value:
            # ~(z | (n ^ v))
            if not self.data_path.alu.Z | self.data_path.alu.N:
                self.sig_latch_reg("IP", int(self.get_reg("DR")[8:], 2))
                self.__tick()
        self.__print__()

    def __print__(self):
        self.instr += 1
        state_repr = (
            "INSTR: {:4} | AC {:4} | BR {:4} | IP: {:4} | AR: {:4} | DR: {:12} |  CR: {:18} |"
        ).format(
            self.instr,
            int(str(self.get_reg("AC")), 2),
            int(self.get_reg("BR")),
            self.get_reg("IP"),
            self.get_reg("AR"),
            int(self.get_reg("DR"), 2),
            parser_to_name_instr(self.get_reg("CR"))

        )
        logging.info(state_repr)




def simulation(input_buffer: list, instructions: list, limit: int):
    if len(instructions) > MEMORY_SIZE:
        raise Exceptions('Program is too large')

    device = Device()
    dataPath = DataPath(instructions)
    device.load(input_buffer)
    control_unit = ControlUnit(instructions, device, dataPath)

    instr_counter = 0
    try:
        while True:
            if instr_counter > limit:
                raise Exceptions('Too long execution! Increase limit')
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
    except StopIteration:
        pass

    return device.output, control_unit.tact, instr_counter


def main(args):
    assert len(args) == 2, "Wrong arguments: machinery.py <code_file> <input_file>"
    code_file, input_file = args

    code = read_code(code_file)
    input_buffer = []
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        for char in input_text:
            input_buffer.append(char)
    input_buffer.append("\0")

    try:
        output, ticks, instructions = simulation(input_buffer, code, 100000)
        print("Output:", ''.join(output))
        print("Instructions:", instructions)
        print("Ticks:", ticks)
    except Exceptions as exception:
        logging.error(exception.get_msg())


if __name__ == '__main__':
    logging.basicConfig(filename='logfile.log', level=logging.INFO, format='%(levelname)-7s %(module)s:%(funcName)-13s %(message)s')
    FORMAT = '%(levelname)-7s %(module)s:%(funcName)-13s %(message)s'
    logging.basicConfig(format=FORMAT)
    logging.getLogger().setLevel(logging.INFO)
    main(sys.argv[1:])
