import tkinter
from tkinter import ttk

from files.gui2 import GUI2
from files.util import globalValues as gv

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
        gv.REGISTER_NUM = int(self.spinb_reg.get())
        gv.REGISTER_BIT = int(self.spinb_bit.get())

        # CPU名に対応するアーキテクチャをimport、呼び出し
        if cpu == "CASLⅡ":
            from files.cpu.casl2 import CASL2
            gv.CPU = CASL2()
        
        else:
            return

        self.destroy()
        window = GUI2(gv.CPU)
        gv.WINDOW = window
        window.mainloop()


def main():
    root = MainWindow()
    root.mainloop()



main()