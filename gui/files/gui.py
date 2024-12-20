import tkinter

from files.superGUI import Window

class GUI1(Window):
    def __init__(self, cpu):
        super().__init__(cpu, "800x600")

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