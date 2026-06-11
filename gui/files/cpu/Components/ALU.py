from enum import Enum
import operator

class ALU_OP(Enum):
    ADD = operator.add
    SUB = operator.sub
    MUL = operator.mul
    DIV = operator.floordiv
    
    AND = operator.and_
    OR  = operator.or_


class ALU:
    left = 0
    right = 0
    op = ALU_OP.ADD
    acc = 0

    def __init__(self):
        pass

    def calculate(self, left, right, op: ALU_OP):
        self.acc = op.value(left, right)
        return self.acc
    
    def getAcc(self):
        return self.acc