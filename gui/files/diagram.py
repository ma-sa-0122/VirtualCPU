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

        self.state = self.canvas.create_text(785, 590, text="State : init")

        self.canvas.create_text(140, 215, text="GR", font=("Cascadia Code", 11))
        self.gr = [Register(self.canvas, 140, 225 + i * 35, "") for i in range(8)]
        for i in range(8):
            self.canvas.create_text(50, 240 + i * 35, text=str(i), font=("Cascadia Code", 11))

        # 線（接続の可視化）
        reg1 = (270, 240)
        reg2 = (270, 275)
        regm = (270, 470)
        addr = (550, 200)
        alul = (350, 310)
        alur = (550, 310)
        acc = (460, 430)
        nodesp = (650, 310)
        gr = (15, 365)
        self.lines = {
            "pc-memory": [self.canvas.create_line(174, 60, 675, 60, fill="gray", width=2)],
            "memory-ir": [self.canvas.create_line(675, 60, 455, 100, fill="gray", width=2),
                          self.canvas.create_line(675, 90, 455, 100, fill="gray", width=2)],
            "ir-decoder": [self.canvas.create_line(340, 130, 330, 150, fill="gray", width=2),
                           self.canvas.create_line(393, 130, 395, 150, fill="gray", width=2),
                           self.canvas.create_line(430, 130, 440, 150, fill="gray", width=2),
                           self.canvas.create_line(500, 130, 540, 150, fill="gray", width=2)]}
        self.lines_execute = {
            "opr1-gr": [self.canvas.create_line(395, 200, reg1,     fill="gray", width=2)],
            "opr2-gr": [self.canvas.create_line(440, 200, reg2,     fill="gray", width=2)],
            "addr-memory_r": [self.canvas.create_line(addr,     675, 250,fill="gray", width=2)],
            "addr-memory_w": [self.canvas.create_line(addr,     nodesp,fill="gray", width=2),
                              self.canvas.create_line(nodesp,   675, 470,fill="gray", width=2)],
            "addr-pc": [self.canvas.create_line(addr,     550, 210, fill="green", width=2),
                        self.canvas.create_line(550, 210, 140, 210, fill="green", width=2),
                        self.canvas.create_line(140, 210, 140, 75, fill="green", width=2)],
            "alu-acc": [self.canvas.create_line(370, 360, 460, 380, fill="green", width=2),
                        self.canvas.create_line(550, 360, 460, 380, fill="green", width=2)],
            "memory-alu": [self.canvas.create_line(675, 250, alur,   fill="green", width=2)],
            "val-alu": [self.canvas.create_line(addr,     alur,    fill="green", width=2)],
            "val-sp": [self.canvas.create_line(addr,     nodesp, fill="green", width=2)],
            "val-gr": [self.canvas.create_line(addr,     reg2,   fill="green", width=2)],
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
            "memory-gr": [self.canvas.create_line(675, 250, reg2,   fill="green", width=2)],
            "memory_w-gr": [self.canvas.create_line(675, 470, nodesp,   fill="green", width=2)],
            "memst-memory": [self.canvas.create_line(regm,  675, 470, fill="green", width=2)],
            "gr-gr": [self.canvas.create_line(0,0,0,0,fill="", width=0)]
        } | {"opr1-gr"+str(i) : [self.canvas.create_line(reg1, 220, 240 + i*35, fill="blue", width=2)] for i in range(8)} \
          | {"opr2-gr"+str(i) : [self.canvas.create_line(reg2, 220, 240 + i*35, fill="blue", width=2)] for i in range(8)} \
          | {"acc-gr"+str(i)  : [self.canvas.create_line(gr,   40, 240 + i*35, fill="green", width=2)] for i in range(8)} \
          | {"memst-gr"+str(i)  : [self.canvas.create_line(regm,   220, 240 + i*35, fill="green", width=2)] for i in range(8)}

        self.lightupExec()
    
    def on_close(self):
        self.master.diagram_window = None   # 親ウィンドウの参照をNoneにする
        self.destroy()

    def readIR(self):
        self.updateState("IR_fetch")
        self.highlight("pc-memory", "red")
        self.highlight("memory-ir", "red")
        self.lightupExec()
        self.undoColor()

        pcAddr = self.cpu.getNowPC()
        self.memory_pc.update(pcAddr, self.cpu.getAddressValue(pcAddr), pink)
        self.memory_pc1.update(pcAddr+1, self.cpu.getAddressValue(pcAddr+1), pink)
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
        self.isRegOP = self.cpu.isRegisterOP(self.op)
        # OP 形式の命令 (# NOP, RET, SVC)。まだやることが無い
        if self.op == "00000000" or self.op == "10000001" or self.op == "11110000":
            return
        elif self.op == "01110000" or self.op == "10000000":    # OP addr [,x] 形式。PUSH, CALL
            if self.r2 == 0:    return
            self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2)])
        else:
            self.lightupExec(["opr1-gr", "opr1-gr"+str(self.r1)])
            if self.isRegOP:
                self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2)])
            elif self.op[:4] == "0101":  # シフト命令系
                return
            elif self.op == "00010010" or self.op[:4] == "0110":    # val系
                return
            else:
                if self.op == "00010001": # ST
                    self.lightupExec(["addr-memory_w"])
                    self.memory_w.update(self.cpu.getAddress(), self.cpu.getAddressValue(), color="")
                    if self.r2 == 0: return
                    self.lightupExec(["opr2-gr"+str(self.r2), "memory_w-gr"])
                else:
                    self.lightupExec(["addr-memory_r"])
                    self.memory_r.update(self.cpu.getAddress(), self.cpu.getAddressValue(), color="")
                    if self.r2 == 0: return
                    self.lightupExec(["opr2-gr"+str(self.r2), "memory-gr"])
                self.lightupExec(["opr2-gr", "opr2-gr"+str(self.r2)])

    def dataFetch(self):
        self.updateState("Data_fetch")
        # NOP or SVC or 0x6(JUMP)
        if self.op == "00000000" or self.op == "11110000" or self.op[:4] == "0110":
            return
        elif self.op[:4] == "0111" or self.op[:4] == "1000":  # PUSH, POP, CALL, RET
            if self.op[4:] == "0000":    # OP addr [,x] 形式。PUSH, CALL
                if self.r2 == 0:    return
                self.gr[self.r2].changeColor(pink)
            self.lightupExec(["val-sp", "sp-spm"])
            self.updateSP(color=pink)
        elif self.op[:4] == "0001": # LD, ST, LAD
            if self.op[5] == "1":   # LD gr, gr
                self.gr[self.r2].changeColor(pink)
            else:
                if self.op == "00010000":   # LD
                    self.memory_r.changeColor(pink)
                elif self.op == "00010001": # ST
                    self.gr[self.r1].changeColor(pink)
                if self.r2 == 0: return
                self.gr[self.r2].changeColor(pink)
        else:
            self.lightupExec()  # 線がごちゃごちゃするので、readyの線を消す
            self.alu_l.update(self.cpu.ALU_A)
            self.alu_r.update(self.cpu.ALU_B)
            self.gr[self.r1].changeColor(pink)
            self.lightupExec(["opr1-gr"+str(self.r1), "reg1-alu"])
            if self.isRegOP:
                self.gr[self.r2].changeColor(pink)
                self.lightupExec(["opr2-gr"+str(self.r2), "reg2-alu"])
            elif self.op[:4] == "0101":  # シフト命令系
                self.lightupExec(["val-alu"])
            else:
                self.memory_r.changeColor(pink)
                self.lightupExec(["memory-alu"])
                if self.r2 == 0:    return
                self.gr[self.r2].changeColor(pink)
    
    def accumulate(self):
        self.updateState("Accumulate")
        # ALU使わない系。NOP, 0x1(LD, ST, LAD), 0x6(JUMP), 0x7(PUSH, POP), 0x8(CALL, RET), SVC
        if self.op == "00000000" or self.op == "11110000" or \
            self.op[:4] == "0001" or self.op[:4] == "0110" or self.op[:4] == "0111" or self.op[:4] == "1000":
            return
        else:
            self.lightupExec(["alu-acc"])
            self.acc.update(self.cpu.Acc)
    
    def writeback(self):
        self.updateState("Write_back")
        if self.op == "00000000" or self.op == "11110000":    # NOP or SVC
            return
        elif self.op[:4] == "0110":  # JUMP系
            self.lightupExec(["memory-pc"])
            self.pc.update(self.cpu.PC)
        elif self.op[:4] == "0111":  # PUSH, POP
            self.updateSP()
        elif self.op[:4] == "1000":  # CALL, RET
            self.lightupExec(["memory-pc"])
            self.pc.update(self.cpu.PC)
            self.updateSP()
        else:
            num = self.r1
            if self.op == "00010001":   # ST
                self.lightupExec(["memst-memory", "memst-gr"+str(num)])
                self.memory_w.update(self.adr, self.cpu.getAddressValue(self.adr))
            elif self.op == "00010010":  # LAD
                self.lightupExec(["val-gr", "opr2-gr"+str(num)])
                self.gr[num].update(self.cpu.GR[num])
            else:
                self.fr.update(self.cpu.FR, digit=3)
                self.gr[num].update(self.cpu.GR[num])
                if self.op == "00010000":   # LD gr, addr
                    self.lightupExec(["memory-gr", "opr2-gr"+str(self.r1)])
                elif self.op == "00010100": # LD gr, gr
                    self.lines_execute["gr-gr"] = [self.canvas.create_line(40, 240 + self.r1*35, 15, 240 + self.r1*35, fill="green", width=4),
                                                   self.canvas.create_line(15, 240 + self.r1*35, 15, 240 + self.r2*35, fill="green", width=4),
                                                   self.canvas.create_line(15, 240 + self.r2*35, 40, 240 + self.r2*35, fill="green", width=4)]
                else:
                    self.lightupExec(["acc-fr", "acc-gr", "acc-gr"+str(self.r1)])
    
    def updateState(self, text):
        self.canvas.itemconfig(self.state, text="State : " + text)

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
            self.canvas.itemconfig(l, fill=color, width=(4 if color!="gray" else 2))
    
    def lightupExec(self, actives=None):
        if actives is None:
            for _, l in self.lines_execute.items():
                for val in l:
                    self.canvas.itemconfig(val, fill="", width=0)    # 全て非表示（initialize）
        else:
            for name in actives:
                for l in self.lines_execute[name]:
                    self.canvas.itemconfig(l, fill="green", width=4)

    def undoColor(self):
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