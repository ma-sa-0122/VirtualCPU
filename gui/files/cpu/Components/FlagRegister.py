class FlagRegister:
    SF = False
    ZF = False
    OF = False

    def __init__(self, bit_length = 16):
        self.bit_length = bit_length

    def setFlags(self, value: int):
        """整数 value に基づいてフラグを設定する（従来の挙動を継承）。"""
        self.SF = (value < 0)
        self.ZF = (value == 0)
        self.OF = (len(bin(value)) - 2 > self.bit_length)
    
    def set_from_bits(self, bits:int):
        """ビットマスクからフラグを設定する。bits のフォーマット: OF(0x4), SF(0x2), ZF(0x1)"""
        self.OF = bool(bits & 0x4)
        self.SF = bool(bits & 0x2)
        self.ZF = bool(bits & 0x1)

    def to_bits(self) -> int:
        """現在のフラグ状態をビットマスクで返す（OF=4, SF=2, ZF=1）。"""
        return (0x4 if self.OF else 0) | (0x2 if self.SF else 0) | (0x1 if self.ZF else 0)

    def getSF(self):
        return self.SF
    
    def getZF(self):
        return self.ZF

    def getOF(self):
        return self.OF
