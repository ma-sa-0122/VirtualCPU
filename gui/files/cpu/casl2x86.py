import re

from files.cpu.casl2 import CASL2
from files.cpu import svc
from files.cpu import macros
from files.cpu import exceptions
from files.util import utils

class CASL2x86(CASL2):
    # レジスタの変更。
    # レジスタの個数は 9 個。ただしGR0は使わない
    # self.SP と GR6 (esp) を連動
    #   -> GETSP, SETSP を廃止して、スタック操作命令の時点でGR5を制御する

    def __init__(self, env=None) -> None:
        super().__init__(env)
        self.GR[6] = self.SP

    # abstractCPUのスタック関係操作 に esp制御を書き足す
    def push(self, value: int) -> None:
        super().push(value)
        self.GR[6] = self.SP
    
    def pop(self, dest: str) -> int:
        v = super().pop(dest)
        self.GR[6] = self.SP
        return v
    
    def execute(self) -> int:
        ret = super().execute()
        # LD esp, ebp などでespの値が変わったときに、self.SPに反映させる
        # スタック関係は push, pop の時点で esp を書き換えてるので影響しない
        self.SP = self.GR[6]

        # 実行ログ文字列中の レジスタ名 を x86仕様 に変更
        self.msg = self.msg.replace("GR1", "eax") \
                            .replace("GR2", "ecx") \
                            .replace("GR3", "edx") \
                            .replace("GR4", "ebx") \
                            .replace("GR5", "ebp") \
                            .replace("GR6", "esp") \
                            .replace("GR7", "esi") \
                            .replace("GR8", "edi") \
                            .replace("SP",  "esp")
        
        return ret