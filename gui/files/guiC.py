import tkinter
import tkinter.scrolledtext as st
from tkinter import ttk

from files.superGUI import Window, ExecuteController, ExecType
from files.util import utils
from files.cpu import Ccompiler

x86 = ["eax", "ecx", "edx", "ebx", "ebp", "esp", "esi", "edi"]


class ExecController(ExecuteController):
    def setCallback(self, after, promptInput, updateFetch, updateDecode, updateExecute):
        self.on_after = after
        self.on_prompt_input = promptInput
        self.on_update_fetch = updateFetch
        self.on_update_decode = updateDecode
        self.on_update_execute = updateExecute

    def set_dict_mem_to_src(self, mem_to_src):
        self.mem_to_src = mem_to_src

    def _exec_1op(self):
        if not self.is_input:
            self.cpu.fetch()
            self.on_update_fetch()

            self.ret = self.cpu.decode()
            self.on_update_decode()
            if self.ret == 1:
                self.is_input = True
                self.on_prompt_input()
                return

        self.is_input = False
        self.ret = self.cpu.execute()
        self.on_update_execute(self.ret)

    def exec_step(self, tp: ExecType):
        if tp == ExecType.STEPIN:
            self._exec_1op()
        else:
            pc = self.cpu.getPC()
            src_row = self.mem_to_src[pc]
            while self.mem_to_src[pc] == src_row:
                self._exec_1op()
                pc = self.cpu.getPC()


class GUI_C(Window):
    def __init__(self, master, windowsize, env):
        # Window requires env; pass through
        super().__init__(master, windowsize, env)

        # インスタンス変数
        self.code_info = None   # 関数の情報 name,argc,locals,code が入ってる
        self.func_indexs = []   # 現状の関数呼び出し階層
        self.adr_to_label = {}  # メモリアドレス -> ラベルの表

        # CPUexecutionをc仕様に
        # ExecuteController に CPU を注入
        self.CPUexecution = ExecController(self, cpu=self.CPU)
        self.CPUexecution.setCallback(
            after=self.after,
            promptInput=self.promptInput,
            updateFetch=self.updateFetch,
            updateDecode=self.updateDecode,
            updateExecute=self.updateExecute,
        )

        # 初期テキストを消す
        self.codebox.delete("0.0", "end")

        # diagram関係のボタンを非表示にする
        self.buttons["diagram"].place_forget()
        self.check_button.place_forget()
        index = self.runmenu.index("CPUメモリステップ（■）")
        self.runmenu.delete(index)

    def createWidgets(self):
        super().createWidgets()
        super().createLabelbox()
        self.createReferenceBox()
        self.createStackInfobox()

        self.infobox['height'] = 8
        self.infobox.place(x=400, y=50)
        self.membox['height'] = 8
        self.membox.place(x=400, y=235)
        self.labelbox['height'] = 7
        self.labelbox.place(x=400, y=420)        

        self.frame_info.place(x=800, y=0)
        self.referencebox['height'] = 5
        self.referencebox.place(x=800, y=295)
        self.stackbox['height'] = 7
        self.stackbox.place(x=800, y=420)
        for i in self.label_GR: i.pack(anchor=tkinter.W)
        self.label_FR.pack(anchor=tkinter.W)
        self.label_PC.pack(anchor=tkinter.W)

    def createRegisterFrame(self):
        self.frame_info = tkinter.LabelFrame(self, text="Register", width=350)
        self.label_GR = [
            tkinter.Label(self.frame_info, text=f"{x86[i-1]}: {0:<8d}  ({utils.binary(0, order=self.CPU.REGBIT)} | 0x0000)", anchor=tkinter.W)
            for i in range(1, self.register_num)
        ]
        self.label_FR = tkinter.Label(self.frame_info, text="FR: 000  (Overflow: 0, Sign: 0, Zero: 0)", anchor=tkinter.W)
        self.label_PC = tkinter.Label(self.frame_info, text="PC: 0x0000", anchor=tkinter.W)

    def createReferenceBox(self):
        self.referencebox = st.ScrolledText(self, width=40)
        self.referencebox.insert("0.0", "参照情報")
        self.referencebox["state"] = tkinter.DISABLED
        self.textbox_manager.setInstance("ref", self.referencebox)
    
    def createStackInfobox(self):
        self.stackbox = ttk.Treeview(self, columns=('name', 'address', 'value'))
        self.stackbox.column('#0', width=0, stretch='no')
        self.stackbox.column('name', width=160, anchor='w')
        self.stackbox.column('address', width=90, anchor='w')
        self.stackbox.column('value', width=130, anchor='w')
        self.stackbox.heading('#0', text='', anchor='w')
        self.stackbox.heading('name', text='stack', anchor='center')
        self.stackbox.heading('address', text='address', anchor='center')
        self.stackbox.heading('value', text='value', anchor='center')

    # テキストボックスの内容を弄る関係
    # stackbox
    def stackWrite(self, d: dict, index='end'):
        for k, v in d.items():
            self.stackbox.insert(parent='', index=index, iid=k ,values=(k, f"0x{v:04X}", "0"))

    def stackUpdates(self):
        item_ids = self.stackbox.get_children()
        for id in item_ids:
            values = self.stackbox.item(id, 'values')
            name = values[0]
            addr = values[1]
            val = int(self.CPU.getMemory(int(addr, 16)), 2)
            val_str = "{:<5d} (#{:04X})".format(val, val)
            self.stackbox.item(id, values=(name, addr, val_str))
    
    def stackPop(self):
        id = self.stackbox.get_children()[0]
        self.stackbox.delete(id)

    def stackClear(self):
        self.stackbox.delete(*self.stackbox.get_children())


    # ==================================================
    # membox の 実行中命令、参照先アドレス をハイライトする関係
    def clearHighlight(self):
        '''
        membox のハイライトを消す
        '''
        self.membox.tag_remove("row", "0.0", "end")
        self.membox.tag_remove("label", "0.0", "end")

    def rowHighlight(self, label: str):
        '''
        membox のハイライトを付ける。codebox はc言語コードなので難あり。\n
        label : "row" で 実行中命令(黄色), "label" で 参照先(橙色)
        '''
        mem = 0
        if label == "row":
            (mem, length) = self.CPU.getExecAddr()
            mem += 1
        elif label == "label":
            mem = self.CPU.getAddress() + 1
            length = 1
        self.membox.tag_remove(label, "0.0", "end")
        self.membox.tag_add(label, f"{mem}.0", f"{mem+ length-1}.end")


    def assemble(self) -> int:
        data = self.textbox_manager.getText("code")

        try:
            assembly, self.code_info, asm_to_src = Ccompiler.compile(data)
        except Ccompiler.CompileError as e:
            self.memClear()
            self.memWrite(e, 0)
            return -1

        for i in range(8):
            assembly = [row.replace(x86[i], "GR"+str(i+1)) for row in assembly]

        memory = ""
        isError = False
        try:
            memory = self.CPU.write(assembly)
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

        self.labClear()
        lab = self.CPU.getLabels()
        self.labWrite(lab)

        # メモリアドレス -> ラベル名。updateStacksの関数名取得に使う
        self.adr_to_label = {v:k for k,v in lab.items()}

        # メモリアドレス -> ソースコード行。ステップ実行に使う
        adr_to_asm = self.CPU.getDICT_AddrRow()
        adr_to_src = {}
        for adr, asm in adr_to_asm.items():
            if asm in asm_to_src:
                adr_to_src[adr] = asm_to_src[asm]
        
        self.CPUexecution.set_dict_mem_to_src(adr_to_src)
        return 0


    def updateExecute(self, ret):
        super().updateExecute(ret)
        self.updateStacks()
    

    def updateRegs(self):
        reg = self.CPU.getRegisters()
        for i in range(1, self.register_num):
            bits = utils.binary(reg[i], order=self.CPU.REGBIT)
            self.label_GR[i-1]["text"] = f"{x86[i-1]}: {reg[i]:<8d}  ({bits} | 0x{int(bits, 2):04X})"
        bits = reg[self.register_num]
        of = 1 if (bits & 0x4) else 0
        sf = 1 if (bits & 0x2) else 0
        zf = 1 if (bits & 0x1) else 0
        self.label_FR["text"] = f"FR: {bits:03b}  (Overflow: {of}, Sign: {sf}, Zero: {zf})"
        self.label_PC["text"] = f"PC: 0x{reg[self.register_num+1]:04X}"



    def append_func(self, func_name):
        for i, func in enumerate(self.code_info):
            if func_name == func.name:
                self.func_indexs.append(i)

    def updateStacks(self):
        DEC = self.CPU.getDEC()

        # CALL 関数呼び出し を取得 -> 関数名取得して code_info のインデックス探す
        if DEC[0] == "10000000":
            func_name = self.adr_to_label[int(DEC[3], 2)]
            self.append_func(func_name)

        # PUSH 0, ebp (GR5) 関数ベースポインタの設定 を取得
        elif DEC == ["01110000", "0000", "0101", "0000000000000000"]:
            func_name = ""
            if self.func_indexs == []:
                func_name = "main"
                self.append_func(func_name)
            else:
                func_name = self.code_info[self.func_indexs[-1]].name
            self.stackWrite({func_name + " ベースポインタ": self.CPU.getSP()}, 0)
        
        # SUBL esp (GR6), =n ローカル変数領域の設定 を取得
        elif DEC[:2] == ["00100011", "0110"]:
            func = self.code_info[self.func_indexs[-1]]
            base = self.CPU.GR[5]   # ebp
            for i, local in enumerate(func.locals):
                self.stackWrite({func.name + "." + local.name: base - (i+1)}, 0)

        # POP ebp (GR5) 関数からのリターンを取得
        elif DEC == ["01110001", "0101", "0000", "0000000000000000"]:
            func = self.code_info[self.func_indexs[-1]]
            length = len(func.locals)
            for _ in range(length + 1): # ベースポインタも解放するので +1
                self.stackPop()
            self.func_indexs.pop()

        self.stackUpdates()