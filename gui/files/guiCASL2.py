import tkinter

from files.superGUI import Window
from files.util import utils

class GUI_CASL2(Window):
    def __init__(self, master, windowsize, env):
        # Window now requires env to be provided
        super().__init__(master, windowsize, env)

    def updateRegs(self):
        reg = self.CPU.getRegisters()
        for i in range(self.register_num):
            bits = utils.binary(reg[i], order=self.CPU.REGBIT)
            self.label_GR[i]["text"] = f"R{i}: {reg[i]:<8d}  ({bits} | 0x{int(bits, 2):04X})"
        bits = reg[self.register_num]
        # ビット列と個別フラグを表示
        of = 1 if (bits & 0x4) else 0
        sf = 1 if (bits & 0x2) else 0
        zf = 1 if (bits & 0x1) else 0
        self.label_FR["text"] = f"FR: {bits:03b}  (Overflow: {of}, Sign: {sf}, Zero: {zf})"
        sp = f"{reg[self.register_num+2]:04X}"
        self.label_PCSP["text"] = f"PC: 語 {reg[self.register_num+1]:04X}        SP: 語 {sp[-4:]}"


class GUI1(GUI_CASL2):
    def __init__(self, master, env):
        super().__init__(master, "800x600", env)

    def createWidgets(self):
        super().createWidgets()
        # 配置つづき（GUI2 との差異がある部分）
        self.membox['height'] = 5
        self.membox.place(x=400, y=50)
        self.infobox['height'] = 6
        self.infobox.place(x=400, y=175)
        self.frame_info.place(x=400, y=300)
        for i in self.label_GR: i.pack(anchor=tkinter.W)
        self.label_FR.pack(anchor=tkinter.W)
        self.label_PCSP.pack(anchor=tkinter.W)


class GUI2(GUI_CASL2):
    def __init__(self, master, env):
        super().__init__(master, "1200x620", env)

    def createWidgets(self):
        super().createWidgets()
        super().createLabelbox()
        
        # 配置つづき
        self.infobox['height'] = 8
        self.infobox.place(x=400, y=50)
        self.membox['height'] = 8
        self.membox.place(x=400, y=235)
        self.labelbox['height'] = 7
        self.labelbox.place(x=400, y=420)

        self.frame_info.place(x=800, y=50)
        for i in self.label_GR: i.pack(anchor=tkinter.W)
        self.label_FR.pack(anchor=tkinter.W)
        self.label_PCSP.pack(anchor=tkinter.W)

        # レジスタの個数が9以上だと描画に対応していないので、CPUモデル図を無効に
        if self.register_num >= 9:
            self.check_button["state"] = tkinter.DISABLED

    def assemble(self) -> int:
        ret = super().assemble()
        if ret < 0:
            return

        self.labClear()
        lab = self.CPU.getLabels()
        self.labWrite(lab)