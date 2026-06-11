import tkinter

from files.cpu.casl2x86 import CASL2x86
from files.guiC import GUI_C
from files.util.environment import Environment
import tkinter


def main():
    # まず Environment を作成（cpu_impl は後で設定）
    env = Environment(register_num=9, register_bit=16, memory_length=0x10000, cpu_impl=None, window_impl=None)
    # 次に CPU を作成して env に差し替え
    cpu = CASL2x86(env)
    env.cpu_impl = cpu
    
    root = tkinter.Tk()
    win = GUI_C(root, "1200x600", env)
    # Environment に window 実装をセット
    env.window_impl = win
    try:
        cpu.window = win
    except Exception:
        pass

    root.mainloop()


main()