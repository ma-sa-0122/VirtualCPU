from typing import Optional

class Excp(Exception):
    def __init__(self, message: str, line: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line = line if (line is not None) else -1 # None なら -1 を返す

    def __str__(self):
        if self.line > 0:
            return f"{self.line}行目: {self.message}"
        return self.message


class NotFoundSTART(Excp):
    def __init__(self, line: Optional[int] = None):
        super().__init__("初めの命令は START でなければなりません", line)


class NotFoundEND(Excp):
    def __init__(self, line: Optional[int] = None):
        super().__init__("END命令がありません", line)


class BoundMemory(Excp):
    def __init__(self, limit: int, line: Optional[int] = None):
        super().__init__(f"メモリの上限(0x{limit:04X})よりデータが大きいです", line)


class InvalidMnemonic(Excp):
    def __init__(self, line: int, mnemonic: str):
        super().__init__(f"不明なニーモニック: '{mnemonic}'", line)


class InvalidOperand(Excp):
    def __init__(self, line: int):
        super().__init__("（構文エラー）オペランドが間違っています", line)


class InvalidRegister(Excp):
    def __init__(self, line: int, reg: str):
        super().__init__(f"不正なレジスタ名: '{reg}'", line)


class InvalidLabel(Excp):
    def __init__(self, line: int, label: str):
        super().__init__(f"不明なラベル名: '{label}'", line)


class InvalidValue(Excp):
    def __init__(self, line: int, value: str):
        super().__init__(f"不正な値: '{value}'", line)
