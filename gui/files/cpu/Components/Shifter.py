from enum import Enum

from files.util import utils

class Shifter_OP(Enum):
    LSHIFT = 1
    RSHIFT = 2


class Shifter:
    """シフタコンポーネント。
    値を指定ビットだけシフトし、結果ビット配列（'0'/'1' のリスト）と溢れビットを返す。
    注意: ビット列の幅は呼び出し側が指定する（通常は CPU.REGBIT）。
    """
    over_bit = 0

    def __init__(self):
        self.over_bit = 0

    def shift(self, value: int, amount: int, op: 'Shifter_OP', width: int, isArith: bool = False):
        """シフトを行い、(result_bits: list[str], over: int) を返す。
        - value: シフト対象の整数
        - amount: シフト量（>=0）
        - op: Shifter_OP.LSHIFT または Shifter_OP.RSHIFT
        - width: ビット幅
        - isArith: 算術シフトフラグ（符号保持）
        """
        # value を width ビットの2進表現（2の補数）に変換
        binstr = utils.binary(value, width)
        array = list(binstr)
        fixbit = array[0]

        if op == Shifter_OP.LSHIFT:
            for _ in range(amount):
                array.append('0')
            result = array[amount:amount+width]
            # 溢れビットはシフトで捨てられた最後のビット
            over = int(array[amount-1]) if amount > 0 else 0
            if isArith:
                # 算術左シフト時の既存の実装に合わせる（やや特殊）
                over = int(array[amount]) if amount < len(array) else 0
                # 最上位ビットを保持
                result[0] = fixbit
        elif op == Shifter_OP.RSHIFT:
            for _ in range(amount):
                array.insert(0, fixbit if isArith else '0')
            result = array[0:width]
            # 溢れビットは右シフトで捨てられる最下位側の次のビット
            over = int(array[width]) if width < len(array) else 0
        else:
            raise ValueError("Unknown Shifter operation")

        # 保存
        self.over_bit = over
        return (result, over)

    def getOverBit(self):
        return self.over_bit
