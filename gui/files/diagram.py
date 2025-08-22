import tkinter as tk

def binaryN(num: int, digit: int) -> str:
    if num < 0:
        num = (~(-num) & ((1 << digit) -1)) + 1  # ビット反転に桁数制限(& 0xF...) +1 で二の補数表現
    return f"{num:0{digit}b}"

bg = "#beffbe"
pink = "#ffbebe"

class Register:
    def __init__(self, canvas, x, y, name, digit=16):
        self.canvas = canvas
        self.name = name
        self.value = 0
        self.label = self.canvas.create_text(x, y - 10, text=name, font=("Cascadia Code", 11))
        self.text = self.canvas.create_text(x, y + 15, text=binaryN(self.value, digit), font=("Cascadia Code", 11))
        x0, y0, x1, y1 = self.canvas.bbox(self.text)
        self.box = self.canvas.create_rectangle(x0 - 5, y0 - 5, x1 + 5, y1 + 5, fill="white")
        self.canvas.tag_lower(self.box)  # 生成の順番的に、textより長方形が前に出ちゃう → textが見えないので背面に移動

    def update(self, value, digit=16, color=bg):
        self.changeColor(color)
        self.value = value
        if type(value) is str:
            self.canvas.itemconfig(self.text, text=value)
        else:
            self.canvas.itemconfig(self.text, text=binaryN(self.value, digit))
    
    def changeColor(self, color):
        self.canvas.itemconfig(self.box, fill=color)

class Pointer:
    def __init__(self, canvas, x, y, name):
        self.canvas = canvas
        self.name = name
        self.value = 0
        self.label = self.canvas.create_text(x, y - 10, text=name, font=("Cascadia Code", 11))
        self.text = self.canvas.create_text(x, y + 15, text=f"0x{self.value:04X}", font=("Cascadia Code", 11))
        x0, y0, x1, y1 = self.canvas.bbox(self.text)
        self.box = self.canvas.create_rectangle(x0 - 5, y0 - 5, x1 + 5, y1 + 5, fill="white")
        self.canvas.tag_lower(self.box)  # 生成の順番的に、textより長方形が前に出ちゃう → textが見えないので背面に移動

    def update(self, value, color=bg):
        self.changeColor(color)
        self.value = value
        self.canvas.itemconfig(self.text, text=f"0x{value:04X}")

    def changeColor(self, color):
        self.canvas.itemconfig(self.box, fill=color)

class Decoder:
    def __init__(self, canvas, x, y):
        self.opcode = Register(canvas, x, y, "opcode", digit=8)
        self.opr1 = Register(canvas, x+65, y, "opr1", digit=4)
        self.opr2 = Register(canvas, x+113, y, "opr2", digit=4)
        self.addr = Register(canvas, x+215, y, "addr/val")
    
    def update(self, opcode, opr1, opr2, addr, color=bg):
        self.changeColor(color)
        self.opcode.update(opcode)
        self.opr1.update(opr1)
        self.opr2.update(opr2)
        self.addr.update(addr)
    
    def changeColor(self, color):
        self.opcode.changeColor(color)
        self.opr1.changeColor(color)
        self.opr2.changeColor(color)
        self.addr.changeColor(color)

class Memory:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.text = self.canvas.create_text(x, y, text="0000000000000000", font=("Cascadia Code", 11))
        x0, y0, x1, y1 = self.canvas.bbox(self.text)
        self.box = self.canvas.create_rectangle(x0 - 5, y0 - 5, x1 + 5, y1 + 5, fill="white")
        self.label = self.canvas.create_text(x0 - 40, y, text=f"0x0000", font=("Cascadia Code", 11))
        self.canvas.tag_lower(self.box)

    def update(self, addr, value, color=bg):
        self.changeColor(color)
        self.canvas.itemconfig(self.label, text=f"0x{addr:004X}")
        if type(value) is str:
            self.canvas.itemconfig(self.text, text=value)
        else:
            self.canvas.itemconfig(self.text, text=binaryN(value, 16))
    
    def changeColor(self, color):
        self.canvas.itemconfig(self.box, fill=color)

class CPUDiagram(tk.Toplevel):
    def __init__(self, master, cpu):
        super().__init__(master)
        self.title("CPU model diagram")
        self.geometry("900x600")
        self.cpu = cpu
        self.protocol("WM_DELETE_WINDOW", self.on_close)  # 閉じる処理

        self.op = ""
        self.r1 = 0
        self.r2 = 0
        self.adr = 0
        self.isRegOP = False
        self.isValue = False
        self.isALU = False

        self.canvas = tk.Canvas(self, width=900, height=600, bg='white')
        self.canvas.pack()

        # コンポーネントの描画
        self.pc = Pointer(self.canvas, 140, 45, "PC")
        self.ir = Register(self.canvas, 450, 100, "IR", digit=32)
        self.decoder = Decoder(self.canvas, 330, 170)
        self.alu_l = Register(self.canvas, 370, 330, "ALU")
        self.alu_r = Register(self.canvas, 550, 330, "ALU")
        self.acc = Register(self.canvas, 460, 400, "Acc (result)")
        self.fr = Register(self.canvas, 140, 525, "FR", digit=3)
        self.sp = Pointer(self.canvas, 600, 527, "SP")

        self.canvas.create_line(670, 0, 670, 600, fill="black", width=2)
        self.canvas.create_text(785, 20, text="Memory (partial)", font=("Cascadia Code", 11))
        self.memory_pc  = Memory(self.canvas, 820, 60)
        self.memory_pc1 = Memory(self.canvas, 820, 90)
        self.memory_r = Memory(self.canvas, 820, 250)
        self.memory_w = Memory(self.canvas, 820, 470)
        self.memory_sp = Memory(self.canvas, 820, 540)

        self.enzanshi = self.canvas.create_text(461, 344, text="", font=("Cascadia Code", 15), fill='green')
        self.AriORLog = self.canvas.create_text(461, 360, text="", font=("Cascadia Code", 11), fill='green')

        self.state = self.canvas.create_text(785, 590, text="State : init")

        self.canvas.create_text(140, 215, text="GR", font=("Cascadia Code", 11))
        self.gr = [Register(self.canvas, 140, 225 + i * 35, "") for i in range(8)]
        for i in range(8):
            self.canvas.create_text(50, 240 + i * 35, text=str(i), font=("Cascadia Code", 11))

        # 線（接続の可視化）
        reg1 = (270, 240)
        reg2 = (270, 275)
        regmr = (270, 300)
        regmw = (270, 470)
        addr = (550, 200)
        alul = (350, 310)
        alur = (550, 310)
        acc = (460, 430)
        nodesp = (650, 310)
        gr = (15, 365)
        self.lines = {
            "pc-memory": [self.canvas.create_line(174, 60, 675, 60, fill="", width=0, arrow=tk.LAST, arrowshape=(16, 20, 6))],
            "memory-ir0": [self.canvas.create_line(670, 60, 460, 90, fill="", width=0, arrow=tk.LAST, arrowshape=(16, 20, 6))],
            "memory-ir1": [self.canvas.create_line(675, 90, 460, 90, fill="", width=0, arrow=tk.LAST, arrowshape=(16, 20, 6))],
            "ir-decoder": [self.canvas.create_line(340, 130, 330, 150, fill="gray", width=0, arrow=tk.LAST, arrowshape=(8, 10, 6)),
                           self.canvas.create_line(393, 130, 395, 150, fill="gray", width=0, arrow=tk.LAST, arrowshape=(8, 10, 6)),
                           self.canvas.create_line(430, 130, 440, 150, fill="gray", width=0, arrow=tk.LAST, arrowshape=(8, 10, 6)),
                           self.canvas.create_line(500, 130, 540, 150, fill="gray", width=0, arrow=tk.LAST, arrowshape=(8, 10, 6))]}
        self.lines_execute = {
            "opr1-gr": [self.canvas.create_line(395, 200, reg1,     fill="green", width=2)],
            "opr2-gr": [self.canvas.create_line(440, 200, reg2,     fill="green", width=2)],
            "addr-memory_r": [self.canvas.create_line(addr,     675, 250,fill="green", width=2)],
            "addr-memory_w": [self.canvas.create_line(addr,     nodesp,fill="green", width=2),
                              self.canvas.create_line(nodesp,   675, 470,fill="green", width=2)],
            "addr-pc": [self.canvas.create_line(addr,     550, 210, fill="green", width=2),
                        self.canvas.create_line(550, 210, 140, 210, fill="green", width=2),
                        self.canvas.create_line(140, 210, 140, 75, fill="green", width=2)],
            "alu-acc": [self.canvas.create_line(370, 360, 460, 380, fill="green", width=2),
                        self.canvas.create_line(550, 360, 460, 380, fill="green", width=2)],
            "memory-alu": [self.canvas.create_line(675, 250, alur,   fill="green", width=2)],
            "val-alu": [self.canvas.create_line(addr,     alur,    fill="green", width=2)],
            "val-sp": [self.canvas.create_line(addr,     nodesp, fill="green", width=2)],
            "val-gr": [self.canvas.create_line(addr,     regmr,   fill="green", width=2)],
            "reg1-alu": [self.canvas.create_line(270, 240, alul,     fill="green", width=2)],
            "reg2-alu": [self.canvas.create_line(270, 275, alur,     fill="green", width=2)],
            "reg1-sp": [self.canvas.create_line(270, 240, nodesp,   fill="green", width=2)],
            "sp-spm": [self.canvas.create_line(nodesp, 600, 510, fill="green", width=2),
                       self.canvas.create_line(nodesp, 675, 540, fill="green", width=2)],
            "acc-fr": [self.canvas.create_line(acc,      160, 540, fill="green", width=2)],
            "acc-gr": [self.canvas.create_line(acc,      460, 580, fill="green", width=2),
                       self.canvas.create_line(460, 580, 15, 580,  fill="green", width=2),
                       self.canvas.create_line(15, 580, gr,        fill="green", width=2)],
            "memory-pc": [self.canvas.create_line(820, 555, 820, 580, fill="green", width=2),
                          self.canvas.create_line(820, 580, 15, 580, fill="green", width=2),
                          self.canvas.create_line(15, 580, 15, 60, fill="green", width=2),
                          self.canvas.create_line(15, 60, 108, 60, fill="green", width=2)],
            "memory_r-opr2": [self.canvas.create_line(675, 250, reg2,   fill="green", width=2)],
            "memory_r-gr": [self.canvas.create_line(675, 250, regmr,   fill="green", width=2)],
            "memory_w-gr": [self.canvas.create_line(675, 470, nodesp,   fill="green", width=2)],
            "memst-memory": [self.canvas.create_line(regmw,  675, 470, fill="green", width=2)],
            "gr-gr": [self.canvas.create_line(0,0,0,0,fill="", width=0)]
        } | {"opr1-gr"+str(i) : [self.canvas.create_line(reg1, 220, 240 + i*35, fill="green", width=2)] for i in range(8)} \
          | {"opr2-gr"+str(i) : [self.canvas.create_line(reg2, 220, 240 + i*35, fill="green", width=2)] for i in range(8)} \
          | {"memr-gr"+str(i) : [self.canvas.create_line(regmr, 220, 240 + i*35, fill="green", width=2)] for i in range(8)} \
          | {"acc-gr"+str(i)  : [self.canvas.create_line(gr,   40, 240 + i*35, fill="green", width=2)] for i in range(8)} \
          | {"memst-gr"+str(i)  : [self.canvas.create_line(regmw,   220, 240 + i*35, fill="green", width=2)] for i in range(8)}

        self.undoColor()
    
    def on_close(self):
        self.master.diagram_window = None   # 親ウィンドウの参照をNoneにする
        self.destroy()

    def readIR(self):
        self.updateState("IR_fetch")
        self.undoColor()
        self.highlight("pc-memory", "red")
        self.highlight("memory-ir0", "red")

        pcAddr = self.cpu.getNowPC()
        self.isRegOP = self.cpu.isRegisterOP(self.cpu.IR[0:8])
        self.memory_pc.update(pcAddr, self.cpu.getAddressValue(pcAddr), pink)
        if not self.isRegOP:
            self.memory_pc1.update(pcAddr+1, self.cpu.getAddressValue(pcAddr+1), pink)
            self.highlight("memory-ir1", "red")
        self.ir.update(self.cpu.IR, digit=32)
        self.pc.changeColor(pink)
    
    def increPC(self):
        self.updateState("Fetch")
        self.pc.update(self.cpu.PC)
    
    def decode(self):
        self.updateState("Decode")
        self.highlight("ir-decoder", "blue")
        self.op, self.r1, self.r2, self.adr = self.cpu.DEC
        self.decoder.update(self.op, self.r1, self.r2, self.adr)
        self.r1 = int(self.r1, 2)
        self.r2 = int(self.r2, 2)
        self.adr = int(self.adr, 2)
    
    def readReady(self):
        self.updateState("Data_ready")
        # OP 形式の命令 (NOP, RET, SVC)。まだやることが無い
        if self.op == "00000000" or self.op == "10000001" or self.op == "11110000":
            return
        # OP addr [,x] 形式。JUMP系0x6_, CALL
        # OP val  [,x] 形式のPUSH も今は共通
        if self.op[:4] == "0110" or self.op == "01110000" or self.op == "10000000":    
            if self.r2 == 0:    return
            self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2)], color='blue')
            self.setArrowHead("opr2-gr"+str(self.r2), tk.LAST)
            return
        # OP r, まで確定
        self.lightupExec(["opr1-gr", "opr1-gr"+str(self.r1)], color='blue')
        self.setArrowHead("opr1-gr"+str(self.r1), tk.LAST)
        # OP r, r 形式
        if self.isRegOP:
            self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2)], color='blue')
            self.setArrowHead("opr2-gr"+str(self.r2), tk.LAST)
            return
        # OP r, val [,x] 形式。LAD と シフト命令(0x5)
        if self.op == "00010010" or self.op[:4] == "0101":
            if self.r2 == 0:    return
            self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2)], color='blue')
            self.setArrowHead("opr2-gr"+str(self.r2), tk.LAST)
            return
        # OP r, addr [,x] 形式。ST はmemory_wに伸ばすので特別
        if self.op == "00010001": # ST
            self.lightupExec(["addr-memory_w"], color='blue')
            self.setArrowHead("addr-memory_w", 1, tk.LAST)
            memaddr = self.cpu.getAddress()
            self.memory_w.update(memaddr, self.cpu.getAddressValue(memaddr), color="")
            if self.r2 == 0: return
            self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2), "memory_w-gr"], color='blue')
            self.setArrowHead("memory_w-gr", tk.FIRST)
        else: # LD
            self.lightupExec(["addr-memory_r"], color='blue')
            self.setArrowHead("addr-memory_r", tk.LAST)
            memaddr = self.cpu.getAddress()
            self.memory_r.update(memaddr, self.cpu.getAddressValue(memaddr), color="")
            if self.r2 == 0: return
            self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2), "memory_r-opr2"], color='blue')
            self.setArrowHead("memory_r-opr2", tk.FIRST)

    def dataFetch(self):
        self.updateState("Data_fetch")
        # NOP or SVC or 0x6(JUMP)
        if self.op == "00000000" or self.op == "11110000" or self.op[:4] == "0110":
            return
        # スタック使う系。PUSH, POP, CALL, RET (0x7, 0x8)
        elif self.op[:4] == "0111" or self.op[:4] == "1000":
            self.lightupExec(["val-sp", "sp-spm"])
            self.setArrowHead("sp-spm", 0, tk.LAST)
            self.setArrowHead("sp-spm", 1, tk.LAST)
            self.updateSP(color=pink)
            # OP addr [,x] 形式。PUSH, CALL (0x7)
            if self.op[4:] == "0000":
                if self.r2 == 0:    return
                self.gr[self.r2].changeColor(pink)
        # LD, ST, LAD
        elif self.op[:4] == "0001":
            if self.r2 != 0:
                self.gr[self.r2].changeColor(pink)
            # LD r, addr
            if self.op == "00010000":
                self.memory_r.changeColor(pink)
            # ST
            elif self.op == "00010001":
                self.gr[self.r1].changeColor(pink)
        else: # ALUを使うやつ
            self.lightupExec()  # 線がごちゃごちゃするので、readyの線を消す
            self.setArrowHead("opr1-gr"+str(self.r1), tk.NONE)
            self.setArrowHead("opr2-gr"+str(self.r2), tk.NONE)

            self.alu_l.update(self.cpu.ALU_A)
            self.alu_r.update(self.cpu.ALU_B)
            self.gr[self.r1].changeColor(pink)
            self.lightupExec(["opr1-gr"+str(self.r1), "reg1-alu"])
            self.setArrowHead("reg1-alu", tk.LAST)
            if self.isRegOP:
                self.gr[self.r2].changeColor(pink)
                self.lightupExec(["opr2-gr"+str(self.r2), "reg2-alu"])
                self.setArrowHead("reg2-alu", tk.LAST)
            elif self.op[:4] == "0101":  # val, [,x]。シフト命令
                self.lightupExec(["val-alu"])
                self.setArrowHead("val-alu", tk.LAST)
            else:
                self.memory_r.changeColor(pink)
                self.lightupExec(["memory-alu"])
                self.setArrowHead("memory-alu", tk.LAST)
                if self.r2 == 0:    return
                self.gr[self.r2].changeColor(pink)
    
    def accumulate(self):
        self.updateState("Accumulate")
        # ALU使わない系。NOP, 0x1(LD, ST, LAD), 0x6(JUMP), 0x7(PUSH, POP), 0x8(CALL, RET), SVC
        if self.op == "00000000" or self.op == "11110000" or \
                self.op[:4] == "0001" or self.op[:4] == "0110" or self.op[:4] == "0111" or self.op[:4] == "1000":
            self.updateALUop("", "")
            return
        else:
            self.lightupExec(["alu-acc"])
            self.acc.update(self.cpu.Acc)
            if   self.op in ["00100000", "00100100"]: self.updateALUop("+", "A")
            elif self.op in ["00100001", "00100101"]: self.updateALUop("-", "A")
            elif self.op in ["00100010", "00100110"]: self.updateALUop("+", "L")
            elif self.op in ["00100011", "00100111"]: self.updateALUop("-", "L")
            elif self.op in ["00110000", "00110100"]: self.updateALUop("&", "")
            elif self.op in ["00110001", "00110101"]: self.updateALUop("|", "")
            elif self.op in ["00110010", "00110110"]: self.updateALUop("^", "")
            elif self.op in ["01000000", "01000100"]: self.updateALUop("?-", "A")
            elif self.op in ["01000001", "01000101"]: self.updateALUop("?-", "L")
            elif self.op == "01010000": self.updateALUop("<<", "A")
            elif self.op == "01010001": self.updateALUop(">>", "A")
            elif self.op == "01010010": self.updateALUop("<<", "L")
            elif self.op == "01010011": self.updateALUop(">>", "L")
            
    
    def writeback(self):
        self.updateState("Write_back")
        if self.op == "00000000" or self.op == "11110000":    # NOP or SVC
            return
        elif self.op[:4] == "0110":  # JUMP系
            if not self.cpu.is_jump:
                return
            self.lightupExec(["addr-pc"])
            self.setArrowHead("addr-pc", 2, tk.LAST)
            self.pc.update(self.cpu.PC)
        elif self.op[:4] == "0111":  # PUSH, POP
            self.updateSP()
        elif self.op[:4] == "1000":  # CALL, RET
            self.lightupExec(["memory-pc"])
            self.setArrowHead("memory-pc", 3, tk.LAST)
            self.pc.update(self.cpu.PC)
            self.updateSP()
        else:
            num = self.r1
            if self.op == "00010001":   # ST
                self.lightupExec(["memst-memory", "memst-gr"+str(num)])
                self.setArrowHead("memst-gr"+str(num), tk.LAST)
                self.memory_w.update(self.adr, self.cpu.getAddressValue(self.adr))
            elif self.op == "00010010":  # LAD
                self.lightupExec(["val-gr", "memr-gr"+str(num)])
                self.setArrowHead("memr-gr"+str(num), tk.LAST)
                self.gr[num].update(self.cpu.GR[num])
                if self.r2 != 0:
                    self.createGRtoGR()
            elif self.op[:4] == "0100":  # 比較系 -> GRが変わらない
                self.lightupExec(["acc-fr"])
                self.setArrowHead("acc-fr", tk.LAST)
            else:
                self.fr.update(self.cpu.FR, digit=3)
                self.gr[num].update(self.cpu.GR[num])
                if self.op == "00010000":   # LD gr, addr
                    self.lightupExec(["memory_r-gr", "memr-gr"+str(self.r1)])
                    self.setArrowHead("memr-gr"+str(self.r1), tk.LAST)
                elif self.op == "00010100": # LD gr, gr
                    self.createGRtoGR()
                else: # ALU系
                    self.lightupExec(["acc-fr", "acc-gr", "acc-gr"+str(self.r1)])
                    self.setArrowHead("acc-fr", tk.LAST)
                    self.setArrowHead("acc-gr"+str(self.r1), tk.LAST)
    
    def createGRtoGR(self):
        if self.r1 == self.r2:
            self.lines_execute["gr-gr"] = [self.canvas.create_line(40, 245 + self.r2*35, 15, 245 + self.r2*35, fill="green", width=4),
                                           self.canvas.create_line(15, 245 + self.r2*35, 15, 235 + self.r1*35, fill="green", width=4),
                                           self.canvas.create_line(15, 235 + self.r1*35, 40, 235 + self.r1*35, fill="green", width=4)]
        else:
            self.lines_execute["gr-gr"] = [self.canvas.create_line(40, 240 + self.r2*35, 15, 240 + self.r2*35, fill="green", width=4),
                                           self.canvas.create_line(15, 240 + self.r2*35, 15, 240 + self.r1*35, fill="green", width=4),
                                           self.canvas.create_line(15, 240 + self.r1*35, 40, 240 + self.r1*35, fill="green", width=4)]
        self.setArrowHead("gr-gr", 2, tk.LAST)


    def updateState(self, text):
        self.canvas.itemconfig(self.state, text="State : " + text)

    def updateALUop(self, text, AL):
        self.canvas.itemconfig(self.enzanshi, text=text)
        self.canvas.itemconfig(self.AriORLog, text=AL)

    def updateSP(self, color=bg):
        spval = self.cpu.SP
        if spval < 0x10000:
            self.sp.update(spval)
            self.memory_sp.update(spval, self.cpu.getAddressValue(spval), color=color)
        else:
            self.sp.update(0)
            self.memory_sp.update(0, 0, color=color)

    def highlight(self, linename, color):
        for l in self.lines[linename]:
            self.canvas.itemconfig(l, fill=color, width=4)
    
    def lightupExec(self, actives=None, color="green"):
        if actives is None:
            for _, l in self.lines_execute.items():
                for val in l:
                    self.canvas.itemconfig(val, fill="", width=0)    # 全て非表示（initialize）
        else:
            for name in actives:
                for l in self.lines_execute[name]:
                    self.canvas.itemconfig(l, fill=color, width=4)
    
    def setArrowHead(self, linename, *args):
        if len(args) == 1:
            direction = args[0]
            lineID = self.lines_execute[linename][0]
        elif len(args) == 2:
            index, direction = args
            lineID = self.lines_execute[linename][index]
        else:
            raise TypeError("setArrowHead() takes 2 or 3 arguments")
        self.canvas.itemconfig(lineID, arrow=direction)
        self.canvas.itemconfig(lineID, arrowshape=(16, 20, 6))


    def undoColor(self):
        self.highlight("pc-memory", "")
        self.highlight("memory-ir0", "")
        self.highlight("memory-ir1", "")
        self.highlight("ir-decoder", "")
        self.lightupExec()
        for gr in self.gr:
            gr.changeColor("")
        self.pc.changeColor("")
        self.ir.changeColor("")
        self.fr.changeColor("")
        self.sp.changeColor("")
        self.decoder.changeColor("")
        self.alu_l.changeColor("")
        self.alu_r.changeColor("")
        self.acc.changeColor("")
        self.memory_pc.changeColor("")
        self.memory_pc1.changeColor("")
        self.memory_r.changeColor("")
        self.memory_w.changeColor("")
        self.memory_sp.changeColor("")