class Register:
    value = 0
    def __init__(self, value=0):
        self.value = value
    
    def getValue(self) -> int:
        return self.value

    def setValue(self, value: int):
        self.value = value


class RegisterFile:
    """Register オブジェクト群を内包し、外部からは list[int] のように振る舞うラッパークラス。
    これにより既存コードの self.GR[i] 参照や反復を壊さずに Register オブジェクトを使える。"""
    def __init__(self, size:int, init_val:int=0):
        self._regs = [Register(init_val) for _ in range(size)]

    def __len__(self):
        return len(self._regs)

    def __getitem__(self, idx):
        return self._regs[idx].getValue()

    def __setitem__(self, idx, value):
        self._regs[idx].setValue(int(value))

    def __iter__(self):
        for r in self._regs:
            yield r.getValue()

    def __repr__(self):
        return repr(list(self))

    def get_register_objects(self):
        """Register オブジェクトのリストを取得する（必要に応じて）。"""
        return list(self._regs)

    def __add__(self, other):
        return list(self) + list(other)

    def __radd__(self, other):
        return list(other) + list(self)