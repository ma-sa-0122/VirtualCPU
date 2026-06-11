import tkinter
from tkinter import ttk

from files.util.environment import Environment


class MainWindow(tkinter.Tk):
    def __init__(self):
        super().__init__()

        self.title(u"Setting")
        self.geometry("400x300")
        self.resizable(False, False)
        self.option_add("*font", ["Cascadia Code", 11])

        self.createWidgets()

    def createWidgets(self):
        self.label_cpu = tkinter.Label(self, text="アーキテクチャ")
        self.label_reg = tkinter.Label(self, text="レジスタの数")
        self.label_bit = tkinter.Label(self, text="レジスタのビット数")
        self.label_mem = tkinter.Label(self, text="メモリのアドレス空間")

        self.combo_cpu = ttk.Combobox(self, values=["", "CASLⅡ"], state="readonly")
        self.combo_cpu.current(1)
        self.spinb_reg = tkinter.Spinbox(self, from_=1, to=16, increment=1, textvariable=tkinter.IntVar(value=8))
        self.spinb_bit = tkinter.Spinbox(self, from_=1, to=16, increment=1, textvariable=tkinter.IntVar(value=16))
        self.spinb_mem = tkinter.Spinbox(self, from_=1, to=65536, increment=1, textvariable=tkinter.IntVar(value=65536))

        self.button = tkinter.Button(self, text="決定", command=self.callWindow)

        # 配置
        self.label_cpu.grid(row=1, column=0, ipady=10)
        self.combo_cpu.grid(row=1, column=2)
        self.label_reg.grid(row=2, column=0, ipady=10)
        self.spinb_reg.grid(row=2, column=2)
        self.label_bit.grid(row=3, column=0, ipady=10)
        self.spinb_bit.grid(row=3, column=2)
        self.label_mem.grid(row=4, column=0, ipady=10)
        self.spinb_mem.grid(row=4, column=2)
        self.button.grid(row=5, column=1, pady=30)

    def callWindow(self):
        cpu = self.combo_cpu.get()

        self.destroyWidgets()
        # CPU名に対応するアーキテクチャとwindowをimport、呼び出し
        if cpu == "CASLⅡ":
            from files.cpu.casl2 import CASL2
            from files.guiCASL2 import GUI2
            # まず Environment を作成（cpu_impl は後で設定）
            env = Environment(register_num=int(self.spinb_reg.get()), register_bit=int(self.spinb_bit.get()), memory_length=int(self.spinb_mem.get()), cpu_impl=None, window_impl=None)
            # 次に CPU を作成して env に差し替え
            cpu_impl = CASL2(env)
            env.cpu_impl = cpu_impl
            # GUI に env を注入して作成
            win = GUI2(self, env)
            # Environment に window 実装をセット
            env.window_impl = win
            # CPU にウィンドウ参照を注入（SVC 互換）
            try:
                cpu_impl.window = win
            except Exception:
                pass
        else:
            return

    def destroyWidgets(self):
        for widget in self.winfo_children():
            widget.destroy()



def main():
    root = MainWindow()
    root.mainloop()

main()