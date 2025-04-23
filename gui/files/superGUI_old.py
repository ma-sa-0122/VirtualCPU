from enum import IntEnum
import tkinter
import tkinter.scrolledtext as st

from files.util import utils


class ExecType(IntEnum):
    FAST = 0
    ALL = 1
    STEP = 2
    STEPIN = 3


class Step(IntEnum):
    FETCH = 0
    DECODE = 1
    EXECUTE = 2


class Window(tkinter.Tk):
    def __init__(self, cpu, windowsize):
        super().__init__()

        self.title(u"Software Title")
        self.geometry(windowsize)
        self.resizable(False, False)
        self.option_add("*font", ["Cascadia Code", 11])

        self.CPU = cpu
        self.register_num = self.CPU.REGISTER_NUM
        self.createWidgets()
        self.buttonSetting('disable')

    def createWidgets(self):
        self.button_assemble = tkinter.Button(self, text="Assemble", command=self.assemble)
        self.button_fast = tkinter.Button(self, text="F", command=lambda: self.execute(0))
        self.button_execute = tkinter.Button(self, text="▶", command=lambda: self.execute(1))
        self.button_step = tkinter.Button(self, text="→", command=lambda: self.execute(2))
        self.button_stepin = tkinter.Button(self, text="↓", command=lambda: self.execute(3))

        self.frame_code = tkinter.Frame(self, width=350, height=400)
        self.codebox = tkinter.Text(self.frame_code, height=18, width=40, undo=True, wrap=tkinter.NONE)
        self.scrollbar = tkinter.Scrollbar(self.frame_code, orient="horizontal", width=20, command=self.codebox.xview)
        self.codebox.config(xscrollcommand=self.scrollbar.set)
        self.codebox.tag_config('row', background="yellow"); self.codebox.tag_add('row', "0.0", "0.0")
        self.codebox.tag_config('label', background="#ff7f50"); self.codebox.tag_add('label', "0.0", "0.0")
        self.codebox.insert("0.0", "MAIN\tSTART\n\t\n\tRET\n\tEND")

        self.inputbox = tkinter.Entry(self, width=40)
        self.label_input = tkinter.Label(self, text="Input", font=("Cascadia Code", 10))

        self.outbox = st.ScrolledText(self, height=3, width=40, state='disable')
        self.label_output = tkinter.Label(self, text="Output", font=("Cascadia Code", 10))

        self.membox = st.ScrolledText(self, width=40)
        self.membox.tag_config('row', background="yellow"); self.membox.tag_add('row', "0.0", "0.0")
        self.membox.tag_config('label', background="#ff7f50"); self.membox.tag_add('label', "0.0", "0.0")
        self.membox.insert("0.0", "メモリ情報")
        self.membox["state"] = tkinter.DISABLED

        self.infobox = st.ScrolledText(self, width=40)
        self.infobox.insert("0.0", "実行ログ")
        self.infobox["state"] = tkinter.DISABLED
        
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

        self.codebox.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.scrollbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        self.frame_code.place(x=10, y=50)
        self.label_input.place(x=10, y=440)
        self.inputbox.place(x=10, y=470)
        self.label_output.place(x=10, y=495)
        self.outbox.place(x=10, y=520)

    def buttonSetting(self, flag: str):
        '''
        実行関係のボタンのゾンビ化を管理する。flag = True でゾンビ化
        用途 : Assemble するまで、実行関係のボタンを押せなくする
        '''
        if flag == 'disable':
            self.button_fast["state"] = tkinter.DISABLED
            self.button_execute["state"] = tkinter.DISABLED
            self.button_step["state"] = tkinter.DISABLED
            self.button_stepin["state"] = tkinter.DISABLED
        else:
            self.button_fast["state"] = tkinter.NORMAL
            self.button_execute["state"] = tkinter.NORMAL
            self.button_step["state"] = tkinter.NORMAL
            self.button_stepin["state"] = tkinter.NORMAL

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
    def infoAdd(self, s: str):
        self.infobox["state"] = tkinter.NORMAL
        self.infobox.insert(tkinter.END, s)
        self.infobox["state"] = tkinter.DISABLED
        self.infobox.yview_moveto(1)    # 最終行にスクロール

    def infoClear(self):
        
        self.infobox["state"] = tkinter.NORMAL
        self.infobox.delete("0.0", "end")
        self.infobox["state"] = tkinter.DISABLED
        self.infobox.yview_moveto(0)    # 先頭にスクロール
    
    # membox
    def memWrite(self, s: str, scroll: float):
        self.membox["state"] = tkinter.NORMAL
        self.membox.insert(tkinter.END, s)
        self.membox["state"] = tkinter.DISABLED
        self.membox.yview_moveto(scroll)    # スクロール位置を戻す

    def memClear(self):
        self.membox["state"] = tkinter.NORMAL
        self.membox.delete("0.0", "end")
        self.membox["state"] = tkinter.DISABLED
        self.membox.yview_moveto(0)    # 先頭にスクロール


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


    def assemble(self):
        data = self.codebox.get("1.0", "end-1c")    # 全て文字列で返る。endだと最後の改行文字まで受け取ってしまうので -1c
        data = data.split("\n")                     # 改行文字で配列化 -> 行単位

        try:
            memory = self.CPU.write(data)
            self.buttonSetting('able')
        except Exception as e:
            memory = "Error\n" + str(e)
            self.buttonSetting('disable')
        
        self.clearHighlight()
        self.outputClear()
        self.infoClear()
        self.memClear()
        self.memWrite(memory, 0)
        self.updateRegs()
        self.changeButton('run')
        self.step = 0


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

    step = Step.FETCH   # staticな変数が欲しかった。
    isInput = False     # 同上。IN命令かどうか
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
                self.changeButton('stop')
                self.execAll()
            #ステップ実行の場合
            else:
                self.execStep(tp)
        except Exception as e:
            self.infoAdd(f"*****異常*****\n{repr(e)}")
            self.buttonSetting('disable')
    
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
    
    def execAll(self):
        # whileにすると 終了まで画面が固まってしまうので、tkinter.after()で指定時間後に実行を繰り返す
        if not(self.isRunning):
            return
        if not(self.isInput):
            self.clearHighlight()
            self.CPU.fetch()
            self.updateFetch()
            ret = self.CPU.decode()
            self.updateDecode()
            if ret == 1:
                self.step = Step.EXECUTE
                self.promptInput()
                return
        self.isInput = False
        ret = self.CPU.execute()
        self.updateExecute(ret)
        if ret == 0:
            # 200ミリ秒後に次の命令を実行
            self.after(200, self.execAll)

    def execStep(self, tp: ExecType):
        self.button_fast["state"] = tkinter.DISABLED
        self.button_execute["state"] = tkinter.DISABLED
        if self.step == Step.FETCH:
            self.CPU.fetch()
            self.updateFetch()
            
            if tp == ExecType.STEPIN: return

        if self.step == Step.DECODE:
            ret = self.CPU.decode()
            self.updateDecode()

            if ret == 1:
                self.promptInput()
                return
            if tp == ExecType.STEPIN: return

        ret = self.CPU.execute()
        self.updateExecute(ret)
        self.isInput = False
        self.button_fast["state"] = tkinter.NORMAL
        self.button_execute["state"] = tkinter.NORMAL
        return
    
    def promptInput(self):
        self.infoAdd("\n**ユーザ入力を行って実行を継続してください**\n")
        self.isInput = True
        self.changeButton('run')

    def updateFetch(self):
        # self.infoClear()
        self.infoAdd("\n" + self.CPU.getMsg())
        self.clearHighlight()
        self.rowHighlight("row")
        self.step = Step.DECODE

    def updateDecode(self):
        self.infoAdd("\n" + self.CPU.getMsg())
        self.rowHighlight("label")
        self.step = Step.EXECUTE
    
    def updateExecute(self, ret):
        self.infoAdd("\n" + self.CPU.getMsg())
        self.updateRegs()
        self.updateMemory()
        self.step = Step.FETCH
        if ret == 0:
            return
        elif ret == 1:
            self.infoAdd("*****最後まで実行されました*****")
            self.buttonSetting('disable')
            return
        else:
            self.infoAdd("*****異常終了*****")
            self.buttonSetting('disable')
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