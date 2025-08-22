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

class TextBoxManager:
    def __init__(self):
        self.boxes = {}
    
    def setInstance(self, name, inst):
        self.boxes[name] = inst
    
    def scroll(self, name, scroll: float):
        self.boxes[name].yview_moveto(scroll)

    def clear(self, name):
        box = self.boxes[name]
        box["state"] = tkinter.NORMAL
        box.delete("0.0", "end")
        box["state"] = tkinter.DISABLED
        box.yview_moveto(0)

    def write(self, name, text, scroll=1):
        box = self.boxes[name]
        box["state"] = tkinter.NORMAL
        box.insert("end", text)
        box["state"] = tkinter.DISABLED
        box.yview_moveto(scroll)
    
    def getText(self, name):
        return self.boxes[name].get("0.0", "end")

class ExecuteController:
    def __init__(self, window, cpu):
        self.window = window
        self.cpu = cpu
        self.reset()

    def setCallback(self, after, promptInput, updateFetch, updateDecode, updateExecute, execDiagram):
        self.on_after = after
        self.on_prompt_input = promptInput
        self.on_update_fetch = updateFetch
        self.on_update_decode = updateDecode
        self.on_update_execute = updateExecute
        self.on_exec_step_diagram = execDiagram

    def reset(self):
        self.step = Step.IR_FETCH
        self.is_running = False
        self.is_input = False
        self.ret = 0

    def execute(self, tp):
        # 実行。try-except でCPU内での実行時エラーを受け取る
        try:
            # 最速で実行する場合
            if tp == ExecType.FAST:
                self.exec_fast()
            # 最後まで実行する場合
            elif tp == ExecType.ALL:
                self.is_running = True
                self.is_input = False
                self.exec_all()
            #ステップ実行の場合
            else:
                self.exec_step(tp)
        except Exception as e:
            raise e

    def exec_fast(self):
        # 終わるまでとにかくwhileで実行し続ける
        while True:
            if not self.is_input:
                self.cpu.fetch()
                ret = self.cpu.decode()
                if ret == 1:
                    self.is_input = True
                    self.on_prompt_input()
                    break
            self.is_input = False
            self.ret = self.cpu.execute()
            if self.ret != 0:
                break
        self.on_update_execute(self.ret)

    def exec_all(self):
        if not self.is_running:
            return
        if not self.is_input:
            self.exec_step(ExecType.ALL)
        if self.ret == 0:
            self.on_after(200, self.exec_all)

    def exec_step(self, tp: ExecType):
        if self.step == Step.IR_FETCH:
            self.cpu.fetch()
            self.on_update_fetch()
            self.callStepDiagram()
            self.step += 1
            if tp == ExecType.DIAGRAM:
                return

        if self.step == Step.FETCH:
            self.callStepDiagram()
            self.step += 1
            if tp == ExecType.STEPIN or tp == ExecType.DIAGRAM:
                return

        if self.step == Step.DECODE:
            self.ret = self.cpu.decode()
            self.on_update_decode()
            self.callStepDiagram()
            self.step += 1
            if self.ret == 1:
                self.is_input = True
                self.on_prompt_input()
                return
            if tp == ExecType.STEPIN or tp == ExecType.DIAGRAM:
                return

        if self.step == Step.DATA_READY:
            self.ret = self.cpu.execute()
            self.is_input = False
            self.callStepDiagram()
            self.step += 1
            if tp == ExecType.DIAGRAM:
                return

        if self.step == Step.DATA_FETCH:
            self.callStepDiagram()
            self.step += 1
            if tp == ExecType.DIAGRAM:
                return

        if self.step == Step.ACCUMLATE:
            self.callStepDiagram()
            self.step += 1
            if tp == ExecType.DIAGRAM:
                return

        # EXECUTE完了
        self.on_update_execute(self.ret)
        self.callStepDiagram()
        self.step = Step.IR_FETCH

    def callStepDiagram(self):
        if self.on_exec_step_diagram:
            self.on_exec_step_diagram(self.step)


class Window(tkinter.Tk):
    def __init__(self, cpu, windowsize):
        super().__init__()

        self.title(u"Software Title")
        self.geometry(windowsize)
        self.resizable(False, False)
        self.option_add("*font", FONT_MAIN)

        self.step = Step.IR_FETCH
        self.showDiagram = tkinter.BooleanVar()
        self.diagram_window = None

        self.CPU = cpu
        self.register_num = self.CPU.REGISTER_NUM
        self.CPUexecution = ExecuteController(self, cpu)
        self.CPUexecution.setCallback(
            after=self.after,
            promptInput=self.promptInput,
            updateFetch=self.updateFetch,
            updateDecode=self.updateDecode,
            updateExecute=self.updateExecute,
            execDiagram=self.exec_step_diagram
        )

        self.textbox_manager = TextBoxManager()
        self.createWidgets()
        self.createMenubar()
        self.buttonSetting(tkinter.DISABLED)

    def createWidgets(self):
        self.createButtons()
        self.createCodebox()
        self.createInOutbox()
        self.createMemoryLogbox()
        self.createRegisterFrame()

        self.placeWigdgets()

        # ショートカットキー関係
        self.bind('<Control-semicolon>', self.increaseFontSize)
        self.bind('<Control-minus>', self.decreaseFontSize)

    def createButtons(self):
        self.buttons = {
            "assemble": tkinter.Button(self, text="Assemble", command=self.assemble),
            "fast": tkinter.Button(self, text="F", command=lambda: self.execute(ExecType.FAST)),
            "execute": tkinter.Button(self, text="▶", command=lambda: self.execute(ExecType.ALL)),
            "step": tkinter.Button(self, text="→", command=lambda: self.execute(ExecType.STEP)),
            "stepin": tkinter.Button(self, text="↓", command=lambda: self.execute(ExecType.STEPIN)),
            "diagram": tkinter.Button(self, text="■", command=lambda: self.execute(ExecType.DIAGRAM)),
        }
        self.check_button = tkinter.Checkbutton(self, text="CPUモデル\nを表示", variable=self.showDiagram)

    def placeButtons(self):
        x_positions = {
            "assemble": (150, 5, 100),
            "fast": (400, 5, 40),
            "execute": (450, 5, 40),
            "step": (500, 5, 40),
            "stepin": (550, 5, 40),
            "diagram": (650, 5, 40),
        }

        for name, (x, y, w) in x_positions.items():
            self.buttons[name].place(x=x, y=y, width=w, height=40)

        self.check_button.place(x=700, y=0)

    def createCodebox(self):
        self.frame_code = tkinter.Frame(self, width=350, height=400)
        self.codebox = tkinter.Text(self.frame_code, height=18, width=40, undo=True, wrap=tkinter.NONE)
        self.scrollbar = tkinter.Scrollbar(self.frame_code, orient="horizontal", width=20, command=self.codebox.xview)
        self.codebox.config(xscrollcommand=self.scrollbar.set)

        self.codebox.tag_config('row', background="yellow")
        self.codebox.tag_config('label', background="#ff7f50")
        self.codebox.insert("0.0", "MAIN\tSTART\n\t\n\tRET\n\tEND")
        self.textbox_manager.setInstance("code", self.codebox)

    def createInOutbox(self):
        self.label_input = tkinter.Label(self, text="Input", font=("Cascadia Code", 10))
        self.inputbox = tkinter.Entry(self, width=40)
        self.textbox_manager.setInstance("in", self.inputbox)

        self.label_output = tkinter.Label(self, text="Output", font=("Cascadia Code", 10))
        self.font_outbox = tkinter.font.Font(family="Cascadia Code", size=11)
        self.outbox = st.ScrolledText(self, state='disabled', font=self.font_outbox)
        self.textbox_manager.setInstance("out", self.outbox)

    def createMemoryLogbox(self):
        self.membox = st.ScrolledText(self, width=40)
        self.membox.tag_config('row', background="yellow")
        self.membox.tag_config('label', background="#ff7f50")
        self.membox.insert("0.0", "メモリ情報")
        self.membox["state"] = tkinter.DISABLED
        self.textbox_manager.setInstance("mem", self.membox)

        self.infobox = st.ScrolledText(self, width=40)
        self.infobox.insert("0.0", "実行ログ")
        self.infobox["state"] = tkinter.DISABLED
        self.textbox_manager.setInstance("info", self.infobox)
    
    def createRegisterFrame(self):
        self.frame_info = tkinter.LabelFrame(self, text="Register", width=350)
        self.label_GR = [
            tkinter.Label(self.frame_info, text=f"R{i}: {0:<8d}  ({utils.binary(0)} | 0x0000)", anchor=tkinter.W)
            for i in range(self.register_num)
        ]
        self.label_FR = tkinter.Label(self.frame_info, text="FR: 000", anchor=tkinter.W)
        self.label_PCSP = tkinter.Label(self.frame_info, text="PC: 0x0000        SP: 0x0000", anchor=tkinter.W)

    def placeWigdgets(self):
        self.placeButtons()

        self.codebox.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.scrollbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        self.frame_code.place(x=10, y=50)
        self.label_input.place(x=10, y=440)
        self.inputbox.place(x=10, y=470)
        self.label_output.place(x=10, y=495)
        self.outbox.place(x=10, y=520, width=370, height=65)  # pixel単位で指定。宣言時のwidthはテキストベースなのでfontsizeを変えるとボックスごと変わってしまう


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
        self.runmenu.add_command(label="ステップ実行（→）", command=lambda: self.execute(ExecType.STEP))
        self.runmenu.add_command(label="ステップイン（↓）", command=lambda: self.execute(ExecType.STEPIN))
        self.runmenu.add_command(label="CPUメモリステップ（■）", command=lambda: self.execute(ExecType.DIAGRAM))

        self.menubar.add_cascade(label='ファイル', menu=self.filemenu)
        self.menubar.add_cascade(label='実行', menu=self.runmenu)


    # ==================================================
    def buttonSetting(self, flag: str):
        '''
        実行関係のボタンのゾンビ化を管理する。
        用途 : Assemble するまで、実行関係のボタンを押せなくする
        '''
        self.menubar.entryconfig("実行", state=flag)
        for name in ["fast", "execute", "step", "stepin", "diagram"]:
            self.buttons[name]["state"] = flag


    # ==================================================
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
        codebox, membox のハイライトを付ける\n
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

    def codeHighlight(self, row: int):
        '''
        コードボックスの指定行目を黄色でハイライトする
        '''
        self.codebox.tag_remove('row', "0.0", "end")
        self.codebox.tag_add('row', f"{row}.0", f"{row}.end")
        # ハイライトの場所にスクロール位置をずらす
        self.codebox.yview_moveto(0)
        self.codebox.yview_scroll(row-3, 'units')
    

    # ==================================================
    # テキストボックスの内容を弄る関係
    def infoAdd(self, s: str):
        self.textbox_manager.write("info", s)

    def infoClear(self):
        self.textbox_manager.clear("info")
    
    def memScroll(self, scroll: float):
        self.textbox_manager.scroll("mem", scroll)

    def memWrite(self, s: str, scroll: float):
        self.textbox_manager.write("mem", s, scroll)

    def memClear(self):
        self.textbox_manager.clear("mem")

    def getInput(self):
        return self.inputbox.get()

    def outputWrite(self, s: str):
        self.textbox_manager.write("out", s)

    def outputClear(self):
        self.textbox_manager.clear("out")

    # 追加機能：Outputのフォントサイズ変更
    def increaseFontSize(self, event):
        current_size = self.font_outbox['size']
        self.font_outbox.configure(size=current_size + 1)
    def decreaseFontSize(self, event):
        current_size = self.font_outbox['size']
        self.font_outbox.configure(size=current_size - 1)


    # ==================================================
    # 実行関係
    def assemble(self) -> int:
        data = self.textbox_manager.getText("code")
        data = data.split("\n")              # 改行文字で配列化 -> 行単位
        data = data[:-1]                     # 最後の改行文字（空行）まで受け取ってしまうので、-1

        memory = ""
        isError = False
        try:
            memory = self.CPU.write(data)
            self.buttonSetting(tkinter.NORMAL)
            self.filemenu.entryconfig("メモリダンプ(binary)を保存", state=tkinter.NORMAL)
        except Exception as e:
            isError = True
            memory = "Error\n" + str(e)
            errline = e.line
            self.buttonSetting(tkinter.DISABLED)
            self.filemenu.entryconfig("メモリダンプ(binary)を保存", state=tkinter.DISABLED)
        
        self.clearHighlight()
        self.outputClear()
        self.infoClear()
        self.memClear()
        self.memWrite(memory, 0)

        if isError:
            self.codeHighlight(errline)
            return -1

        self.CPUexecution.reset()
        self.updateRegs()
        self.changeButton('run')
        self.makeDiagram()
        return 0

    # CPUモデル図を子ウィンドウで作成
    def makeDiagram(self):
        if not(self.showDiagram.get()):
            self.buttons["diagram"]["state"] = tkinter.DISABLED
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
            self.buttons["execute"]['text'] = '||'
            self.buttons["execute"]['command'] = self.pause
        elif state == 'run':
            self.buttons["execute"]['text'] = '▶'
            self.buttons["execute"]['command'] = lambda: self.execute(ExecType.ALL)
    
    def pause(self):
        self.CPUexecution.is_running = False
        self.changeButton('run')

    def execute(self, tp: ExecType):
        # 実行。try-except でCPU内での実行時エラーを受け取る
        try:
            if tp == ExecType.FAST or tp == ExecType.ALL:
                self.changeButton('stop')
            self.CPUexecution.execute(tp)
        except Exception as e:
            self.infoAdd(f"*****異常*****\n{repr(e)}")
            self.buttonSetting(tkinter.DISABLED)

    def exec_step_diagram(self, step: Step):
        if self.diagram_window is None or not self.diagram_window.winfo_exists():
            return

        if step == Step.IR_FETCH:
            self.diagram_window.readIR()
        elif step == Step.FETCH:
            self.diagram_window.increPC()
        elif step == Step.DECODE:
            self.diagram_window.decode()
        elif step == Step.DATA_READY:
            self.diagram_window.readReady()
        elif step == Step.DATA_FETCH:
            self.diagram_window.dataFetch()
        elif step == Step.ACCUMLATE:
            self.diagram_window.accumulate()
        elif step == Step.EXECUTE:
            self.diagram_window.writeback()
    
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


    # ==================================================
    # タブバーのファイル操作系
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