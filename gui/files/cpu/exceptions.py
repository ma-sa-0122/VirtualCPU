class Excp(Exception):
    def __init__(self, *args):
        self.args = args

class NotFoundSTART(Excp):
    def __str__(self):
        return "初めの命令は START でなければなりません"
    
class NotFoundEND(Excp):
    def __str__(self):
        return "END命令がありません"
    
class BoundMemory(Excp):
    def __str__(self):
        return f"メモリの上限(0x{self.args[0]:04X})よりデータが大きいです"

class InvalidMnemonic(Excp):
    def __str__(self):
        return f"{self.args[0]}行目: 不明なニーモニック: '{self.args[1]}'"

class InvalidOperand(Excp):
    def __str__(self):
        return f"{self.args[0]}行目: （構文エラー）オペランドが間違っています"

class InvalidRegister(Excp):
    def __str__(self):
        return f"{self.args[0]}行目: 不正なレジスタ名: '{self.args[1]}'"
    
class InvalidLabel(Excp):
    def __str__(self):
        return f"{self.args[0]}行目: 不明なラベル名: '{self.args[1]}'"
    
class InvalidValue(Excp):
    def __str__(self):
        return f"{self.args[0]}行目: 不正な値: '{self.args[1]}'"