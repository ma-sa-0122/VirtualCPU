class Memory:
    word_size = 16
    length = 1 << 16

    def __init__(self, word_size:int = 16, length:int = 10000):
        self.word_size = word_size
        self.length = length
        self.memory = [0]*length
    
    def read(self, address:int):
        # 以前の list 実装と互換性を保つため、負のインデックスは末尾からのオフセットとして扱う
        # （Python の list の挙動に合わせる）
        if address < 0:
            address = self.length + address
        if not 0 <= address < self.length:
            raise MemoryAccessError(address)
        return self.memory[address]

    def write(self, address:int, value:int):
        # 負のインデックスをサポートして、list と同じように末尾を参照できるようにする
        if address < 0:
            address = self.length + address
        if not 0 <= address < self.length:
            raise MemoryAccessError(address)
        # 書き込み値は int を期待する
        if not isinstance(value, int):
            try:
                value = int(value)
            except Exception:
                raise MemoryWriteError(value)
        if len(bin(value)) - 2 > self.word_size:    # bin() は 0b 付きなので 0b 分を引く
            raise MemoryWriteError(value)
        self.memory[address] = value


class MemoryAccessError(Exception):
    def __init__(self, address):
        super().__init__()
        self.address = address
    
    def __str__(self):
        return f"Address 0x{self.address:x} can not access"


class MemoryWriteError(Exception):
    def __init__(self, value):
        super().__init__()
        self.value = value
    
    def __str__(self):
        return f"value {self.value} has too long bits"