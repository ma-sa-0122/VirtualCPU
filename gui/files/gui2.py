import tkinter
import tkinter.scrolledtext as st
from typing_extensions import override

from files.superGUI import Window

class GUI2(Window):
    def __init__(self, cpu):
        super().__init__(cpu, "1200x600")

    def createWidgets(self):
        super().createWidgets()
        # 宣言つづき
        self.labelbox = st.ScrolledText(self, height=8, width=40)
        self.labelbox.insert("0.0", "ラベル一覧")
        self.labelbox["state"] = tkinter.DISABLED

        # 配置つづき
        self.infobox['height'] = 8
        self.infobox.place(x=400, y=50)
        self.membox['height'] = 8
        self.membox.place(x=400, y=235)
        self.labelbox.place(x=400, y=420)

        self.frame_info.place(x=800, y=50)
        for i in self.label_GR: i.pack(anchor=tkinter.W)
        self.label_FR.pack(anchor=tkinter.W)
        self.label_PCSP.pack(anchor=tkinter.W)

    # テキストボックスの内容を弄る関係
    # labelbox
    def labWrite(self, str):
        self.labelbox["state"] = tkinter.NORMAL
        self.labelbox.insert(tkinter.END, str)
        self.labelbox["state"] = tkinter.DISABLED
        self.labelbox.yview_moveto(0)

    def labClear(self):
        self.labelbox["state"] = tkinter.NORMAL
        self.labelbox.delete("0.0", "end")
        self.labelbox["state"] = tkinter.DISABLED
        self.labelbox.yview_moveto(0)    # 先頭にスクロール


    @override
    def assemble(self):
        data = self.codebox.get("1.0", "end-1c")    # 全て文字列で返る。endだと最後の改行文字まで受け取ってしまうので -1c
        data = data.split("\n")                     # 改行文字で配列化 -> 行単位

        memory = ""
        lab = ""
        isError = False
        try:
            memory = self.CPU.write(data)
            lab = self.CPU.getLabels()
            self.buttonSetting('able')
        except Exception as e:
            isError = True
            memory = "Error\n" + str(e)
            self.buttonSetting('disable')
        
        self.clearHighlight()
        self.outputClear()
        self.infoClear()
        self.memClear()
        self.memWrite(memory, 0)
        self.labClear()
        self.labWrite(lab)
        self.updateRegs()
        self.changeButton('run')
        self.step = 0

        if isError: return

        self.makeDiagram()
