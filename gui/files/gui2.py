import tkinter
import tkinter.scrolledtext as st
from tkinter import ttk

from files.superGUI import Window, FONT_MAIN

class GUI2(Window):
    def __init__(self, cpu):
        super().__init__(cpu, "1200x600")

    def createWidgets(self):
        super().createWidgets()
        # 宣言つづき
        style = ttk.Style()
        style.configure("Treeview",font=FONT_MAIN)
        style.configure("Treeview.Heading",font=FONT_MAIN)

        self.labelbox = ttk.Treeview(self, columns=('label', 'address'))
        self.labelbox.column('#0', width=0, stretch='no')
        self.labelbox.column('label', width=220, anchor='w')
        self.labelbox.column('address', width=150, anchor='w')
        self.labelbox.heading('#0', text='', anchor='w')
        self.labelbox.heading('label', text='label Name', anchor='center')
        self.labelbox.heading('address', text='address', anchor='center')
        self.labelbox.bind("<Button-1>", self.labSelect)    # 左クリック
        
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

    # テキストボックスの内容を弄る関係
    # labelbox
    def labWrite(self, d: dict):
        for i, (k, v) in enumerate(d.items()):
            self.labelbox.insert(parent='', index='end', iid=i ,values=(k, f"0x{v:04X}"))

    def labClear(self):
        self.labelbox.delete(*self.labelbox.get_children())
    
    def labSelect(self, event):
        index = self.labelbox.focus()
        if not index:
            return
        address = self.labelbox.item(index, 'values')[1]
        super().memScroll(int(address, 16) / 0xFFFF)

    def assemble(self) -> int:
        ret = super().assemble()
        if ret < 0:
            return

        self.labClear()
        lab = self.CPU.getLabels()
        self.labWrite(lab)
    