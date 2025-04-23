from abc import ABCMeta, abstractmethod
from typing import Final

from files.util import globalValues as gv
from files.util import utils

class CPU(metaclass = ABCMeta):
    OVERFLOW_FLAG :Final[int] = 0b100
    SIGN_FLAG     :Final[int] = 0b010
    ZERO_FLAG     :Final[int] = 0b001

    INIT_VAL      :Final[int] = 0xFFFF

    def __init__(self) -> None:
        self.REGBIT = gv.REGISTER_BIT
        self.REGISTER_NUM = gv.REGISTER_NUM
        self.MEMLEN = gv.MEMORY_LENGTH

        self.reset()
    
    def reset(self) -> None:
        self.GR = [0] * self.REGISTER_NUM                   # 汎用レジスタ 16bit
        self.FR = 0                                         # フラグレジスタ。OF, SF, ZFの3bit
        self.PC = 0                                         # プログラムカウンタ 16bit
        self.SP = self.MEMLEN                               # スタックポインタ 16bit
        self.IR = 0                                         # 命令レジスタ 32bit
        self.DEC = ["{0:08b}", "0000", "0000", "{0:016b}"]  # デコーダー 8+4+4+16bit
        self.MEM = [f"{self.INIT_VAL:016b}"]*self.MEMLEN    # メモリ 16bit MEMLEN-1番地まで

        self.ALU_A = 0
        self.ALU_B = 0
        self.Acc = 0

        self.msg = ""                                       # GUIに表示するメッセージ。execute()の内部処理を可視化
        self.nowPC = 0                                      # 現在実行中のアドレス。GUIのハイライトに、ジャンプ命令とかの時に困らないため
        self.labels = {}                                    # ラベルとアドレスの対応辞書

    @abstractmethod
    def assemble(self, data: str) -> str:
        pass

    def write(self, data: str) -> str:
        self.reset()
        return self.assemble(data)
    
    @abstractmethod
    def fetch(self) -> None:
        pass
    
    @abstractmethod
    def decode(self) -> int:
        pass

    @abstractmethod
    def execute(self) -> int:
        pass


    # ----------------------------------------
    # getter達
    def getRegisters(self) -> list:
        return self.GR + [self.FR, self.PC, self.SP]
    
    def getIR(self) -> int:
        return self.IR

    def getDEC(self) -> list:
        return self.DEC

    def getMsg(self) -> int:
        return self.msg
    
    def getNowPC(self) -> int:
        return self.nowPC
    
    def getLabels(self) -> str:
        '''ラベル名とアドレスを改行付き文字列にして返す'''
        return "\n".join(f"{name}\t0x{addr:04X}" for name, addr in self.labels.items())

    def getMemory(self) -> str:
        '''メモリアドレス空間を改行付き文字列にして返す'''
        return "\n".join(f"0x{index:04X} | {bit}    ({int(bit, 2):04X})" for index, bit in enumerate(self.MEM))

    @abstractmethod
    def getRow(self) -> int:
        '''現在実行中の命令が何行目に書かれているかを返す'''
        pass

    @abstractmethod
    def getLabelRow(self) -> int:
        '''現在実行中の命令の参照先ラベルが何行目に書かれているかを返す'''
        pass

    @abstractmethod
    def getExecAddr(self) -> tuple[int, int]:
        '''現在実行中のアドレスと、語数を返す'''
        pass
    
    @abstractmethod
    def getAddress(self) -> int:
        '''命令レジスタのアドレス部と修飾部を参照し、参照先アドレスを返す'''
        pass
    
    @abstractmethod
    def getAddressValue(self, addr:int) -> int:
        '''引数のメモリ番地に格納されている中身を返す'''
        '''命令レジスタのアドレス部と修飾部を参照し、参照先アドレスの中身の数値を返す。1語の場合はレジスタの値を返す'''
        pass

    def getValue(self, opr: str) -> int:
        '''オペランドが数値 or レジスタの場合に使う。中身の値を返す'''
        if utils.isnum(opr):
            return int(opr)
        else:
            return self.GR[int(opr[2:])]


    # ----------------------------------------
    # スタック関係
    def push(self, value: int) -> None:
        self.SP -= 1
        self.MEM[self.SP] = utils.binary(value)
    
    def pop(self, dest: str) -> None:
        v = int(self.MEM[self.SP], 2)
        self.MEM[self.SP] = f"{self.INIT_VAL:016b}"
        self.msg = f"0x{self.SP:04X}番地の値({v}) を {dest} にロードし、SP を 1 増やします\n"
        self.SP += 1
        return v


    # ----------------------------------------
    # 演算関係。ALU的な何か
    def add(self, a: int, b: int, isArith: bool) -> int:
        '''
        a + b を行う。
        isArith が真のとき、算術加算として扱う。
        isArith が偽のとき、論理加算として扱う。
        '''
        self.ALU_A = a
        self.ALU_B = b

        number = a + b

        # 計算結果を レジスタのビット数+1 桁にする (桁あふれしてたらそのまま、そうじゃなければ空白を追加)
        bit = utils.binary(number)
        bit = ("" if len(bit) > self.REGBIT else " ") + bit

        self.drawHissan(a, b, "+")
        self.msg += f" {bit}   ({number})\n"

        # 末尾から レジスタのビット数 だけ取り出す
        value = utils.binToValue(utils.binary(number)[-self.REGBIT:], isArith)
        self.Acc = value

        self.setFlag(value)
        if isArith:
            max = (1 << (self.REGBIT - 1)) - 1
            if not(-max-1 <= number <= max):
                self.msg += f"{number} は、符号付き{self.REGBIT}bit (-{max+1} ~ {max}) で表現できないため、OF → 1 になります\n"
                self.FR |= self.OVERFLOW_FLAG
        else:
            max = (1 << self.REGBIT) - 1
            if not(0 <= number <= max):
                self.msg += f"{number} は、符号付き{self.REGBIT}bit (0 ~ {max}) で表現できないため、OF → 1 になります\n"
                self.FR |= self.OVERFLOW_FLAG
        return value

    def mul(self, a: int, b: int) -> int:
        number = a * b
        bit = utils.binary(number)
        value = int(bit[-self.REGBIT:] ,2)
        self.setFlag(value)
        if len(bit) > self.REGBIT:  self.FR |= self.OVERFLOW_FLAG
        return value
    
    def div(self, a: int, b: int) -> tuple[int, int]:
        quotient = a // b
        remain = a % b
        return (quotient, remain)

    
    def compare(self, a: int, b: int) -> None:
        self.ALU_A = a
        self.ALU_B = b
        self.Acc = a - b

        val = a - b
        if val > 0:
            self.msg += f"{a} - {b} は正の数なので、SF → 0, ZF → 0 です\n"
            self.FR = 0x000
        elif val == 0:
            self.msg += f"{a} と {b} は (ビット列として) 等しいので、ZF → 1 です\n"
            self.FR = self.ZERO_FLAG
        else:
            self.msg += f"{a} - {b} は負の数なので、SF → 1 です\n"
            self.FR = self.SIGN_FLAG

    def lshift(self, val: int, amount: int, isArith: bool) -> tuple[list[str], int]:
        '''
        val を amount ビットだけ左シフトします。
        isArith が True で 算術左シフト、False で 論理左シフト
        '''
        self.ALU_A = utils.binary(val)
        self.ALU_B = amount

        array = list(self.ALU_A)
        fixbit = array[0]
        for _ in range(amount):
            array.append('0')
        result = array[amount:amount+self.REGBIT]     # 末尾に0を追加していき、末尾からnビット取る
        over = int(array[amount-1])
        if isArith:
            over = int(array[amount])
            result[0] = fixbit
        
        self.Acc = utils.binToValue(result, isArith)
        return (result, over)

    def rshift(self, val: int, amount: int, isArith: bool) -> tuple[list[str], int]:
        '''
        val を amount ビットだけ左シフトします。
        isArith が True で 算術左シフト、False で 論理左シフト
        '''
        self.ALU_A = utils.binary(val)
        self.ALU_B = amount

        array = list(self.ALU_A)
        fixbit = array[0]
        for _ in range(amount):
            array.insert(0, fixbit if isArith else '0')
        result = array[0:self.REGBIT]                 # 先頭に0を追加していき、先頭からnビット取る

        self.Acc = utils.binToValue(result, isArith)
        return (result, int(array[self.REGBIT]))


    def setFlag(self, val: int) -> None:
        self.msg += "\n"
        if utils.binary(val)[0] == '1':
            self.msg += f"{val} の最上位ビットが1なので、SF → 1 になります\n"
            self.FR = self.SIGN_FLAG
        elif val == 0:
            self.msg += f"結果が 0 なので、ZF → 1 になります\n"
            self.FR = self.ZERO_FLAG
        else:
            self.FR = 0x000

    def drawHissan(self, a: int, b: int, op: str) -> None:
        '''
        筆算を self.msg に書きます。opに演算子を指定します
        '''
        self.msg += ("\n"
                    f"  {utils.binary(a)}   ({a})\n"
                    f"{op} {utils.binary(b)}   ({b})\n"
                    f"-------------------\n")
