from abc import ABCMeta, abstractmethod
from typing import Final, Union

from files.util import utils
from files.cpu.Components import *
# 明示的に Memory, RegisterFile をインポート（ワイルドカード import に依存せず確実に利用できるように）
from files.cpu.Components.Memory import Memory
from files.cpu.Components.Registor import RegisterFile
from files.cpu.Components.FlagRegister import FlagRegister
from files.cpu.Components.ALU import ALU, ALU_OP
from files.cpu.Components.Shifter import Shifter, Shifter_OP

class CPU(metaclass = ABCMeta):
    OVERFLOW_FLAG = 0b100
    SIGN_FLAG = 0b010
    ZERO_FLAG = 0b001

    INIT_VAL      :Final[int] = 0xFFFF

    def __init__(self, env) -> None:
        """env: Environment を必須で受け取る（gv 参照は廃止）。
        env から register_bit / register_num / memory_length を取得して初期化する。
        """
        if env is None:
            raise ValueError("Environment is required for CPU initialization")
        self.env = env

        # Environment から各種パラメータを取得
        self.REGBIT = env.register_bit
        self.REGISTER_NUM = env.register_num
        self.MEMLEN = env.memory_length

        # self.FLAGS = FlagRegister(self.REGBIT)
        
        self.reset()
    
    def reset(self) -> None:
        # 汎用レジスタ: Register オブジェクト群を内包するラッパーを使用して互換性を保つ
        self.GR = RegisterFile(self.REGISTER_NUM)
        # フラグレジスタ。OF, SF, ZFの3bit（互換のため self.FR はビットマスク整数として残す）
        self.FR = 0
        # FlagRegister コンポーネントを使ってフラグ状態を管理
        self.FLAGS = FlagRegister(self.REGBIT)
        self.PC = 0                                         # プログラムカウンタ
        self.SP = self.MEMLEN                               # スタックポインタ
        self.IR = 0                                         # 命令レジスタ
        self.DEC = None                                     # デコーダー
        # 実行時は Components の Memory を使用する（従来の bytearray の代替）
        self.MEM = Memory(word_size=self.REGBIT, length=self.MEMLEN)

        self.ALU_A = 0
        self.ALU_B = 0
        self.Acc = 0
        self.is_jump = False
        # ALU / Shifter コンポーネント
        self.alu = ALU()
        self.shifter = Shifter()

        self.msg = ""                                       # GUIに表示するメッセージ。execute()の内部処理を可視化
        self.nowPC = 0                                      # 現在実行中のアドレス。GUIのハイライトに、ジャンプ命令とかの時に困らないため
        self.labels = {}                                    # ラベルとアドレスの対応辞書

    @abstractmethod
    def assemble(self, data: str) -> str:
        pass

    def write(self, data: str) -> str:
        """Reset → assemble を呼び出し、
        アッセンブル段階でサブクラスが self.MEM を list（ビット列文字列）で保持した場合は
        Components.Memory インスタンスへ変換してランタイムで利用する。
        """
        self.reset()
        res = self.assemble(data)
        # サブクラスが組み立て時に list を使っている場合は Memory に変換する
        if isinstance(self.MEM, list):
            newmem = Memory(word_size=self.REGBIT, length=self.MEMLEN)
            for i, v in enumerate(self.MEM):
                if isinstance(v, str):
                    try:
                        val = int(v, 2)
                    except Exception:
                        val = 0
                else:
                    val = int(v)
                newmem.write(i, val)
            self.MEM = newmem
        return res
    
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
    
    def getSP(self) -> int:
        return self.SP
    
    def getPC(self) -> int:
        return self.PC
    
    def getIR(self) -> int:
        return self.IR

    def getDEC(self) -> list:
        return self.DEC

    def getMsg(self) -> int:
        return self.msg
    
    def getNowPC(self) -> int:
        return self.nowPC
    
    def getLabels(self) -> dict:
        '''ラベル名とアドレスを辞書で返す'''
        return self.labels

    @abstractmethod
    def getMemoryStrings(self) -> str:
        '''メモリアドレス空間を改行付き文字列にして返す'''
        pass

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

    def getMemory(self, addr:int) -> str:
        '''引数のメモリ番地に格納されている中身（16bit のビット列）を返す'''
        if addr >= self.MEMLEN:
            raise Exception("Segmentation Fault!! 参照先が無効です")
        # Components.Memory を使っている場合は int を読み出して 16bit 文字列に変換して返す
        if isinstance(self.MEM, Memory):
            return utils.binary16(self.MEM.read(addr))
        # 旧来の list/bytearray をそのまま返す
        return self.MEM[addr]
    
    def setMemory(self, addr:int, value:Union[int, str]):
        # 互換：int または ビット文字列を受け付ける
        if addr >= self.MEMLEN:
            raise Exception("Segmentation Fault!! 参照先が無効です")
        if isinstance(self.MEM, Memory):
            # Memory コンポーネントには整数で書き込む
            if isinstance(value, int):
                v = value
            else:
                v = int(value, 2)
            self.MEM.write(addr, v)
            return
        # 旧来の実装と互換にするため、文字列へ変換して格納する
        if isinstance(value, int):
            value = utils.binary16(value)
        self.MEM[addr] = value

    @abstractmethod
    def getNowAddressOrRegisterValue(self):
        '''命令レジスタのアドレス部と修飾部を参照し、参照先アドレスの中身の数値を返す。1語の場合はレジスタの値を返す'''
        pass

    def getRegisterValue(self, num: int) -> int:
        if 0 <= num < self.REGISTER_NUM:
            return self.GR[num]
        else:
            raise Exception(f"無効なレジスタ番号: {num}")


    # ----------------------------------------
    # スタック関係
    def push(self, value: int) -> None:
        # check for stack overflow (SP is word index; valid addresses are 0..MEMLEN-1)
        if self.SP - 1 < 0:
            raise Exception(f"Stack overflow: SP would become negative (SP={self.SP})")
        self.SP -= 1
        try:
            self.setMemory(self.SP, value)
        except Exception as e:
            # augment error with stack context
            raise Exception(f"Push failed when writing to memory address 0x{self.SP:04X}: {e}") from e
    
    def pop(self, dest: str) -> int:
        # check for stack underflow (nothing to pop if SP >= MEMLEN)
        if self.SP >= self.MEMLEN:
            raise Exception(f"Stack underflow: SP ({self.SP}) is beyond memory bounds (MEMLEN={self.MEMLEN})")
        v = int(self.getMemory(self.SP), 2)
        try:
            self.setMemory(self.SP, f"{self.INIT_VAL:016b}")
        except Exception as e:
            raise Exception(f"Pop failed when clearing memory address 0x{self.SP:04X}: {e}") from e
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

        # 演算は ALU コンポーネントへ委譲
        number = self.alu.calculate(a, b, ALU_OP.ADD)
        # 計算結果を レジスタのビット数+1 桁にする (桁あふれしてたらそのまま、そうじゃなければ空白を追加)
        bit = utils.binary(number, order=self.REGBIT)
        bit = ("" if len(bit) > self.REGBIT else " ") + bit

        self.drawHissan(a, b, "+")
        self.msg += f" {bit}   ({number})\n"

        # 末尾から レジスタのビット数 だけ取り出す
        value = utils.binToValue(utils.binary(number, order=self.REGBIT)[-self.REGBIT:], isArith, order=self.REGBIT)
        self.Acc = value

        self.setFlag(value)
        if isArith:
            max = (1 << (self.REGBIT - 1)) - 1
            if not(-max-1 <= number <= max):
                self.msg += f"{number} は、符号付き{self.REGBIT}bit (-{max+1} ~ {max}) で表現できないため、OF → 1 になります\n"
                # FlagRegister に OF をセットして FR を再構築
                self.FLAGS.OF = True
                self.FR = self.FLAGS.to_bits()
        else:
            max = (1 << self.REGBIT) - 1
            if not(0 <= number <= max):
                self.msg += f"{number} は、符号付き{self.REGBIT}bit (0 ~ {max}) で表現できないため、OF → 1 になります\n"
                # FlagRegister に OF をセットして FR を再構築
                self.FLAGS.OF = True
                self.FR = self.FLAGS.to_bits()
        return value

    def mul(self, a: int, b: int) -> int:
        # 演算は ALU コンポーネントへ委譲
        number = self.alu.calculate(a, b, ALU_OP.MUL)
        bit = utils.binary(number, order=self.REGBIT)
        value = int(bit[-self.REGBIT:] ,2)
        self.setFlag(value)
        if len(bit) > self.REGBIT:
            # 乗算でオーバーフローが発生したら OF をセット
            self.FLAGS.OF = True
            self.FR = self.FLAGS.to_bits()
        return value
    
    def div(self, a: int, b: int) -> tuple[int, int]:
        # 割り算は ALU へ委譲し、剰余は手計算で返す
        quotient = self.alu.calculate(a, b, ALU_OP.DIV)
        remain = a % b
        return (quotient, remain)

    
    def compare(self, a: int, b: int) -> None:
        self.ALU_A = a
        self.ALU_B = b
        self.Acc = a - b

        val = a - b
        if val > 0:
            self.msg += f"{a} - {b} は正の数なので、SF → 0, ZF → 0 です\n"
            # Flags をクリア
            self.FLAGS.SF = False
            self.FLAGS.ZF = False
        elif val == 0:
            self.msg += f"{a} と {b} は (ビット列として) 等しいので、ZF → 1 です\n"
            self.FLAGS.SF = False
            self.FLAGS.ZF = True
        else:
            self.msg += f"{a} - {b} は負の数なので、SF → 1 です\n"
            self.FLAGS.SF = True
            self.FLAGS.ZF = False
        # FR のビットマスクを更新
        self.FR = self.FLAGS.to_bits()

    def lshift(self, val: int, amount: int, isArith: bool) -> tuple[list[str], int]:
        '''
        val を amount ビットだけ左シフトします。
        isArith が True で 算術左シフト、False で 論理左シフト
        Shifter コンポーネントを使用するが、結果のビット配列と溢れビットは従来のロジックに合わせて生成する。
        '''
        self.ALU_A = utils.binary(val, order=self.REGBIT)
        self.ALU_B = amount

        # Shifter コンポーネントに委譲して結果のビット列と over を受け取る
        (result, over) = self.shifter.shift(val, amount, Shifter_OP.LSHIFT, self.REGBIT, isArith)

        # 結果を反映
        self.Acc = utils.binToValue(result, isArith, order=self.REGBIT)
        return (result, over)

    def rshift(self, val: int, amount: int, isArith: bool) -> tuple[list[str], int]:
        '''
        val を amount ビットだけ右シフトします。
        isArith が True で 算術右シフト、False で 論理右シフト
        Shifter コンポーネントを使用するが、結果のビット配列と溢れビットは従来のロジックに合わせて生成する。
        '''
        self.ALU_A = utils.binary(val, order=self.REGBIT)
        self.ALU_B = amount

        # Shifter コンポーネントに委譲して結果のビット列と over を受け取る
        (result, over) = self.shifter.shift(val, amount, Shifter_OP.RSHIFT, self.REGBIT, isArith)

        # 結果を反映
        self.Acc = utils.binToValue(result, isArith, order=self.REGBIT)
        return (result, over)

    def setFlag(self, val: int) -> None:
        """計算結果 val に基づいて SF/ZF を設定し、FR のビットマスクを更新する。
        OF はオーバーフロー判定の処理で個別に設定する。
        """
        self.msg += "\n"
        # SF の設定（最上位ビット）
        if utils.binary(val, order=self.REGBIT)[0] == '1':
            self.msg += f"{val} の最上位ビットが1なので、SF → 1 になります\n"
            self.FLAGS.SF = True
        else:
            self.FLAGS.SF = False
        # ZF の設定
        if val == 0:
            self.msg += f"結果が 0 なので、ZF → 1 になります\n"
            self.FLAGS.ZF = True
        else:
            self.FLAGS.ZF = False
        # FR のビットマスクを FLAGS から再構築
        self.FR = self.FLAGS.to_bits()

    def drawHissan(self, a: int, b: int, op: str) -> None:
        '''
        筆算を self.msg に書きます。opに演算子を指定します
        '''
        self.msg += ("\n"
                    f"  {utils.binary(a, order=self.REGBIT)}   ({a})\n"
                    f"{op} {utils.binary(b, order=self.REGBIT)}   ({b})\n"
                    f"-------------------\n")
