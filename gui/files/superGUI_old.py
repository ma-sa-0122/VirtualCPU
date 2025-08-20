from enum import IntEnum
import tkinter
import tkinter.font
import tkinter.scrolledtext as st
import tkinter.filedialog
import os

from files.diagram import CPUDiagram
from files.util import utils

FONT_MAIN = ("Cascadia Code", 11)
COLOR_HIGHLIGHT = "yelllow"
COLOR_LABEL = "#ff7f50"


class ExecType(IntEnum):
    FAST = 0
    ALL = 1
    STEP = 2
    STEPIN = 3
    DIAGRAM = 4

class Step(IntEnum):
    IR_FETCH = 0
    FETCH = 1
    DECODE = 2
    DATA_READY = 3
    DATA_FETCH = 4
    ACCUMLATE = 5
    EXECUTE = 6

class Window(tkinter.Tk):
    def __init__(self, cpu, windowsize):
        super().__init__()

        self.title(u"Software Title")
        self.geometry(windowsize)
        self.resizable(False, False)
        self.option_add("*font", FONT_MAIN)

        self.step = Step.IR_FETCH
        self.showDiagram = tkinter.BooleanVar()

        self.CPU = cpu
        self.diagram_window = None
        self.register_num = self.CPU.REGISTER_NUM
        self.createWidgets()
        self.createMenubar()
        self.buttonSetting(tkinter.DISABLED)

    def createWidgets(self):
        # ボタン関係
        self.button_assemble = tkinter.Button(self, text="Assemble", command=self.assemble)
        self.button_fast = tkinter.Button(self, text="F", command=lambda: self.execute(ExecType.FAST))
        self.button_execute = tkinter.Button(self, text="▶", command=lambda: self.execute(ExecType.ALL))
        self.button_step = tkinter.Button(self, text="→", command=lambda: self.execute(ExecType.STEP))
        self.button_stepin = tkinter.Button(self, text="↓", command=lambda: self.execute(ExecType.STEPIN))
        self.button_diagram = tkinter.Button(self, text="■", command=lambda: self.execute(ExecType.DIAGRAM))
        self.check_button = tkinter.Checkbutton(self, text="CPUモデル\nを表示", variable=self.showDiagram)

        # コードボックス
        self.frame_code = tkinter.Frame(self, width=350, height=400)
        self.codebox = tkinter.Text(self.frame_code, height=18, width=40, undo=True, wrap=tkinter.NONE)
        self.scrollbar = tkinter.Scrollbar(self.frame_code, orient="horizontal", width=20, command=self.codebox.xview)
        self.codebox.config(xscrollcommand=self.scrollbar.set)
        self.codebox.tag_config('row', background=COLOR_HIGHLIGHT); self.codebox.tag_add('row', "0.0", "0.0")
        self.codebox.tag_config('label', background=COLOR_LABEL); self.codebox.tag_add('label', "0.0", "0.0")
        self.codebox.insert("0.0", "MAIN\tSTART\n\t\n\tRET\n\tEND")

        # inputボックス
        self.inputbox = tkinter.Entry(self, width=40)
        self.label_input = tkinter.Label(self, text="Input", font=("Cascadia Code", 10))

        # outputボックス
        self.font_outbox = tkinter.font.Font(family="Cascadia Code", size=11)
        self.outbox = st.ScrolledText(self, state='disable', font=self.font_outbox)
        self.label_output = tkinter.Label(self, text="Output", font=("Cascadia Code", 10))

        # メモリ情報ボックス
        self.membox = st.ScrolledText(self, width=40)
        self.membox.tag_config('row', background=COLOR_HIGHLIGHT); self.membox.tag_add('row', "0.0", "0.0")
        self.membox.tag_config('label', background=COLOR_LABEL); self.membox.tag_add('label', "0.0", "0.0")
        self.membox.insert("0.0", "メモリ情報")
        self.membox["state"] = tkinter.DISABLED

        # ログ出力ボックス
        self.infobox = st.ScrolledText(self, width=40)
        self.infobox.insert("0.0", "実行ログ")
        self.infobox["state"] = tkinter.DISABLED
        
        # registerフレーム
        self.frame_info = tkinter.LabelFrame(self, text="Register", width=350)
        self.label_GR = [tkinter.Label(self.frame_info, text=f"R{i}: {0:<8d}  ({utils.binary(0)} | 0x0000)", anchor=tkinter.W) for i in range(self.register_num)]
        self.label_FR = tkinter.Label(self.frame_info, text="FR: 000", anchor=tkinter.W)    # text="OF: 0    SF: 0    ZF: 0")
        self.label_PCSP = tkinter.Label(self.frame_info, text=f"PC: 0x0000        SP: 0x0000", anchor=tkinter.W)

        # 配置
        self.button_assemble.place(x=150, y=5, width=100, height=40)
        self.button_fast.place(x=400, y=5, width=40, height=40)
        self.button_execute.place(x=450, y=5, width=40, height=40)
        self.button_step.place(x=500, y=5, width=40, height=40)
        self.button_stepin.place(x=550, y=5, width=40, height=40)
        self.button_diagram.place(x=650, y=5, width=40, height=40)
        self.check_button.place(x=700, y=0)
        
        self.codebox.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.scrollbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        self.frame_code.place(x=10, y=50)
        self.label_input.place(x=10, y=440)
        self.inputbox.place(x=10, y=470)
        self.label_output.place(x=10, y=495)
        self.outbox.place(x=10, y=520, width=370, height=65)  # pixel単位で指定。宣言時のwidthはテキストベースなのでfontsizeを変えるとボックスごと変わってしまう

        # ショートカットキー関係
        self.bind('<Control-semicolon>', self.increaseFontSize)
        self.bind('<Control-minus>', self.decreaseFontSize)

    def createMenubar(self):
        self.menubar = tkinter.Menu(self)
        self.config(menu=self.menubar)

        self.filemenu = tkinter.Menu(self.menubar, tearoff=False)
        self.filemenu.add_command(label='ソースコードを開く', command=self.loadFile)
        self.filemenu.add_command(label='ソースコードを保存', command=self.saveFile)
        self.filemenu.add_separator()
        self.filemenu.add_command(label='メモリダンプ(binary)を保存', state=tkinter.DISABLED, command=self.saveBinary)

        self.runmenu = tkinter.Menu(self.menubar, tearoff=False)
        self.runmenu.add_command(label="高速実行（F）", command=lambda: self.execute(ExecType.FAST))
        self.runmenu.add_command(label="通常実行（▶）", command=lambda: self.execute(ExecType.ALL))
        self.runmenu.add_command(label="ステップ実行（→）", command=lambda: self.execStep(ExecType.STEP))
        self.runmenu.add_command(label="ステップイン（↓）", command=lambda: self.execute(ExecType.STEPIN))
        self.runmenu.add_command(label="CPUメモリステップ（■）", command=lambda: self.execute(ExecType.DIAGRAM))

        self.menubar.add_cascade(label='ファイル', menu=self.filemenu)
        self.menubar.add_cascade(label='実行', menu=self.runmenu)
    
    def loadFile(self):
        fTyp = [("", "*")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        filename = tkinter.filedialog.askopenfilename(filetypes=fTyp, initialdir=iDir)
        code = ""
        if filename != "":
            try:
                with open(filename, 'r', encoding="utf-8") as f:
                    code = f.read()
            except UnicodeDecodeError:
                with open(filename, 'r', encoding="shift_jis") as f:
                    code = f.read()
        self.codebox.delete("0.0", "end")
        self.codebox.insert("1.0", code)
    
    def saveFile(self):
        code = self.codebox.get("1.0", "end")

        fTyp = [("CASL2コード", ".casl2")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        filename = tkinter.filedialog.asksaveasfilename(filetypes=fTyp, initialdir=iDir, defaultextension="casl2")
        if filename != "":
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
    
    def saveBinary(self):
        data = ''.join(self.CPU.MEM)
        # 8ビットずつintにしてbytesに変換
        bdata = bytes(int(data[i:i+8], 2) for i in range(0, len(data), 8))

        fTyp = [("バイナリファイル", ".bin")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        filename = tkinter.filedialog.asksaveasfilename(filetypes=fTyp, initialdir=iDir, defaultextension="bin")
        if filename != "":
            with open(filename, "wb") as f:
                f.write(bdata)

    def buttonSetting(self, flag: str):
        '''
        実行関係のボタンのゾンビ化を管理する。
        用途 : Assemble するまで、実行関係のボタンを押せなくする
        '''
        self.menubar.entryconfig("実行", state=flag)
        self.button_fast["state"] = flag
        self.button_execute["state"] = flag
        self.button_step["state"] = flag
        self.button_stepin["state"] = flag
        self.button_diagram["state"] = flag


    # codebox, membox の、実行中命令、参照先アドレスをハイライトする関係
    def clearHighlight(self):
        '''
        codebox, membox のハイライトを消す
        '''
        self.codebox.tag_remove("row", "0.0", "end")
        self.codebox.tag_remove("label", "0.0", "end")
        self.membox.tag_remove("row", "0.0", "end")
        self.membox.tag_remove("label", "0.0", "end")

    def rowHighlight(self, label: str):
        '''
        codebox, membox のハイライトを付ける
        label : "row" で 実行中命令(黄色), "label" で 参照先(橙色)
        '''
        code = 0; mem = 0
        if label == "row":
            code = self.CPU.getRow()
            (mem, length) = self.CPU.getExecAddr()
            mem += 1
            # ハイライトの場所にスクロール位置をずらす
            self.codebox.yview_moveto(0)
            self.codebox.yview_scroll(code-3, 'units')
        elif label == "label":
            code = self.CPU.getLabelRow()
            mem = self.CPU.getAddress() + 1
            length = 1
        self.codebox.tag_remove(label, "0.0", "end")
        self.codebox.tag_add(label, f"{code}.0", f"{code}.end")
        self.membox.tag_remove(label, "0.0", "end")
        self.membox.tag_add(label, f"{mem}.0", f"{mem+ length-1}.end")
    

    # テキストボックスの内容を弄る関係
    # infobox
    def scroll_infobox(self, scroll: float):
        self.infobox.yview_moveto(scroll)

    def infoAdd(self, s: str):
        self.infobox["state"] = tkinter.NORMAL
        self.infobox.insert(tkinter.END, s)
        self.infobox["state"] = tkinter.DISABLED
        self.scroll_infobox(1)    # 最終行にスクロール

    def infoClear(self):
        self.infobox["state"] = tkinter.NORMAL
        self.infobox.delete("0.0", "end")
        self.infobox["state"] = tkinter.DISABLED
        self.scroll_infobox(0)    # 先頭にスクロール
    
    # membox
    def scroll_membox(self, scroll: float):
        self.membox.yview_moveto(scroll)

    def memWrite(self, s: str, scroll: float):
        self.membox["state"] = tkinter.NORMAL
        self.membox.insert(tkinter.END, s)
        self.membox["state"] = tkinter.DISABLED
        self.scroll_membox(scroll)    # スクロール位置を戻す

    def memClear(self):
        self.membox["state"] = tkinter.NORMAL
        self.membox.delete("0.0", "end")
        self.membox["state"] = tkinter.DISABLED
        self.scroll_membox(0)    # 先頭にスクロール


    # input, output 関係
    def getInput(self):
        str = self.inputbox.get()
        self.inputbox.delete(0, tkinter.END)
        return str

    def outputWrite(self, s: str):
        self.outbox["state"] = tkinter.NORMAL
        self.outbox.insert("end", s)
        self.outbox["state"] = tkinter.DISABLED
        self.outbox.yview_moveto(1)    # 最終行にスクロール

    def outputClear(self):
        self.outbox["state"] = tkinter.NORMAL
        self.outbox.delete("0.0", "end")
        self.outbox["state"] = tkinter.DISABLED
        self.outbox.yview_moveto(0)    # 先頭にスクロール

    # 追加機能：Outputのフォントサイズ変更
    def increaseFontSize(self, event):
        current_size = self.font_outbox['size']
        self.font_outbox.configure(size=current_size + 1)
    def decreaseFontSize(self, event):
        current_size = self.font_outbox['size']
        self.font_outbox.configure(size=current_size - 1)


    # 実行関係
    def assemble(self) -> int:
        data = self.codebox.get("1.0", "end-1c")    # 全て文字列で返る。endだと最後の改行文字まで受け取ってしまうので -1c
        data = data.split("\n")                     # 改行文字で配列化 -> 行単位

        memory = ""
        isError = False
        try:
            memory = self.CPU.write(data)
            self.buttonSetting(tkinter.NORMAL)
            self.filemenu.entryconfig("メモリダンプ(binary)を保存", state=tkinter.NORMAL)
        except Exception as e:
            isError = True
            memory = "Error\n" + str(e)
            self.buttonSetting(tkinter.DISABLED)
            self.filemenu.entryconfig("メモリダンプ(binary)を保存", state=tkinter.DISABLED)
        
        self.clearHighlight()
        self.outputClear()
        self.infoClear()
        self.memClear()
        self.memWrite(memory, 0)

        if isError: return -1

        self.updateRegs()
        self.changeButton('run')
        self.step = 0
        self.makeDiagram()
        return 0

    # CPUモデル図を子ウィンドウで作成
    def makeDiagram(self):
        if not(self.showDiagram.get()):
            self.button_diagram["state"] = tkinter.DISABLED
            return
        try:
            if self.diagram_window.winfo_exists():
                self.diagram_window.destroy()
        except AttributeError:
            pass  # diagram_window がまだ存在しないとき
        self.diagram_window = CPUDiagram(self, self.CPU)
        self.diagram_window.deiconify()

    def changeButton(self, state: str):
        if state == 'stop':
            self.button_execute['text'] = '||'
            self.button_execute['command'] = self.pause
        elif state == 'run':
            self.button_execute['text'] = '▶'
            self.button_execute['command'] = lambda: self.execute(1)
    
    def pause(self):
        self.isRunning = False
        self.changeButton('run')

    isInput = False     # staticな変数。IN命令かどうか
    isRunning = False   # 同上。executeしているかどうか
    def execute(self, tp: ExecType):
        # 実行。try-except でCPU内での実行時エラーを受け取る
        try:
            # 最速で実行する場合
            if tp == ExecType.FAST:
                self.execFast()
            # 最後まで実行する場合
            elif tp == ExecType.ALL:
                self.isRunning = True
                self.isInput = False
                self.changeButton('stop')
                self.execAll()
            #ステップ実行の場合
            else:
                self.execStep(tp)
        except Exception as e:
            self.infoAdd(f"*****異常*****\n{repr(e)}")
            self.buttonSetting(tkinter.DISABLED)
    
    def execFast(self):
        # 終わるまでとにかくwhileで実行し続ける
        eRet = 0
        while True:
            if not(self.isInput):
                self.CPU.fetch()
                ret = self.CPU.decode()
                if ret == 1:
                    self.promptInput()
                    break
            self.isInput = False
            eRet = self.CPU.execute()
            if eRet != 0:
                break
        self.updateExecute(eRet)
    
    ret = 0
    def execAll(self):
        # whileにすると 終了まで画面が固まってしまうので、tkinter.after()で指定時間後に実行を繰り返す
        if not(self.isRunning):
            return
        if not(self.isInput):
            self.execStep(ExecType.ALL)
        if self.ret == 0:
            # 200ミリ秒後に次の命令を実行
            self.after(200, self.execAll)
        else:
            return

    def execStep(self, tp: ExecType):
        if tp != ExecType.ALL:
            self.button_fast["state"] = tkinter.DISABLED
            self.button_execute["state"] = tkinter.DISABLED

        if self.step == Step.IR_FETCH:
            self.CPU.fetch()
            self.updateFetch()
            if self.diagram_window is not None and self.diagram_window.winfo_exists():
                self.diagram_window.readIR()
            self.step += 1
            if tp == ExecType.DIAGRAM: return

        if self.step == Step.FETCH:
            if self.diagram_window is not None and self.diagram_window.winfo_exists():
                self.diagram_window.increPC()
            self.step += 1
            if tp == ExecType.DIAGRAM or tp == ExecType.STEPIN: return

        if self.step == Step.DECODE:
            self.ret = self.CPU.decode()
            self.updateDecode()
            if self.diagram_window is not None and self.diagram_window.winfo_exists():
                self.diagram_window.decode()
            self.step += 1
            if self.ret == 1:
                self.promptInput()
                return
            if tp == ExecType.DIAGRAM or tp == ExecType.STEPIN: return

        if self.step == Step.DATA_READY:
            self.ret = self.CPU.execute()
            self.isInput = False
            if self.diagram_window is not None and self.diagram_window.winfo_exists():
                self.diagram_window.readReady()
            self.step += 1
            if tp == ExecType.DIAGRAM: return

        if self.step == Step.DATA_FETCH:
            if self.diagram_window is not None and self.diagram_window.winfo_exists():
                self.diagram_window.dataFetch()
            self.step += 1
            if tp == ExecType.DIAGRAM: return

        if self.step == Step.ACCUMLATE:
            if self.diagram_window is not None and self.diagram_window.winfo_exists():
                self.diagram_window.accumulate()
            self.step += 1
            if tp == ExecType.DIAGRAM: return

        if self.diagram_window is not None and self.diagram_window.winfo_exists():
            self.diagram_window.writeback()
        self.button_fast["state"] = tkinter.NORMAL
        self.button_execute["state"] = tkinter.NORMAL
        self.updateExecute(self.ret)
    
    def promptInput(self):
        self.infoAdd("\n**ユーザ入力を行って実行を継続してください**\n")
        self.isInput = True
        self.changeButton('run')

    def updateFetch(self):
        # self.infoClear()
        self.infoAdd("\n" + self.CPU.getMsg())
        self.clearHighlight()
        self.rowHighlight("row")

    def updateDecode(self):
        self.infoAdd("\n" + self.CPU.getMsg())
        self.rowHighlight("label")
    
    def updateExecute(self, ret):
        self.infoAdd("\n" + self.CPU.getMsg())
        self.updateRegs()
        self.updateMemory()
        self.step = Step.IR_FETCH
        if ret == 0:
            return
        elif ret == 1:
            self.infoAdd("*****最後まで実行されました*****")
            self.buttonSetting(tkinter.DISABLED)
            return
        else:
            self.infoAdd("*****異常終了*****")
            self.buttonSetting(tkinter.DISABLED)
            return
    
    def updateRegs(self):
        reg = self.CPU.getRegisters()
        for i in range(self.register_num):
            bits = utils.binary(reg[i])
            self.label_GR[i]["text"] = f"R{i}: {reg[i]:<8d}  ({bits} | 0x{int(bits, 2):04X})"
        self.label_FR["text"] = f"FR: {reg[self.register_num]:03b}"
        sp = f"{reg[self.register_num+2]:04X}"
        self.label_PCSP["text"] = f"PC: 0x{reg[self.register_num+1]:04X}        SP: 0x{sp[-4:]}"
    
    def updateMemory(self):
        memory = self.CPU.getMemory()
        scroll = self.membox.yview()[0] # スクロール位置を保持
        self.memClear()
        self.memWrite(memory, scroll)
        self.rowHighlight("row")
        self.rowHighlight("label")