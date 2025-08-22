import re

from files.cpu.abstractCPU import CPU
from files.cpu import svc
from files.cpu import macros
from files.cpu import exceptions
from files.util import utils

class CASL2(CPU):
    # 言語形式：
    #   <Label>\t<OP>\t<R1> <R2>
    #   <Label>\t<OP>\t<R1> <adr> [<R2>]
    # 命令形式：
    #   1語：命令部8bit レジスタ1部4bit レジスタ2部4bit
    #   2語：命令部8bit レジスタ部4bit  修飾部4bit      アドレス16bit

    # ニーモニックと機械語の対応表
    MNEMONIC = {
        "NOP": 0x00,
        "LD": 0x10, "ST": 0x11, "LAD": 0x12,
        "ADDA": 0x20, "SUBA": 0x21, "ADDL": 0x22, "SUBL": 0x23,
        "AND": 0x30, "OR": 0x31, "XOR": 0x32,
        "CPA": 0x40, "CPL": 0x41,
        "SLA": 0x50, "SRA": 0x51, "SLL": 0x52, "SRL": 0x53,
        "JUMP": 0x60, "JPL": 0x61, "JMI": 0x62, "JNZ": 0x63, "JZE": 0x64, "JOV": 0x65,
        "PUSH": 0x70, "POP": 0x71,
        "CALL": 0x80, "RET": 0x81,
        "MUL": 0x90, "DIV": 0x91,
        "SETE": 0xA0, "SETGE": 0xA1, "SETL": 0xA2,
        "SVC": 0xF0
    }

    DICT_AddrRow = {} # {メモリアドレス : コードの行番号}


    def __init__(self) -> None:
        super().__init__()

    def isGR(self, opr: str, isXR=False) -> bool:
        if len(opr) < 3:    return False
        if isXR:
            return (opr[0:2] == "GR" and utils.isnum(opr[2:]) and 1 <= int(opr[2:]) < self.REGISTER_NUM)
        return (opr[0:2] == "GR" and utils.isnum(opr[2:]) and 0 <= int(opr[2:]) < self.REGISTER_NUM)

    def assemble(self, data: str) -> str:
        '''
        構文チェックと機械語変換を行う

        1. 初めの命令が STARTか
        2. 全走査し、ラベル名を self.labels に格納
        3. END命令が存在するか
        4. 逐次、命令を機械語に変換
        5. ラベル名とアドレスの対応付け
        '''
        # DC命令の内部処理。リテラル使ったり複数定数の場合に呼び出すので関数化
        def DC(const) -> None:
            nonlocal address, index
            # 10進数 or 16進数のとき
            if utils.isnum(const):
                if utils.isValidNum(const):
                    self.MEM[address] = utils.binary16(utils.toInt(const))
                    address += 1
                else:
                    exceptions.InvalidValue(index+1, const)
            # 文字列のとき
            elif "\'" in const:
                s = const[1:len(const)-1]                       # 文字列から両端の ' を抜く
                s = s.replace("\\t", "\t").replace("\\n", "\n") # 勝手にエスケープされて \\t とかになってるので、\t に直す
                s = s.replace("\\'", "'")
                for c in list(s):
                    self.MEM[address] = utils.binary16(ord(c))  # asciiコードに変換して代入
                    address += 1
            # ラベルのとき
            elif const in self.labels:
                tempLabel[address] = const
                address += 1
            # 複数の定数が列挙されたとき
            elif ',' in const:
                d = const.split(',')
                for i in d:
                    DC(i)
            # 該当しない
            else:
                raise exceptions.InvalidValue(index+1, const)

        # オペランドがレジスタだった時のアセンブルをする関数 
        def setRegister(opr) -> None:
            nonlocal address, index
            if self.isGR(opr):
                # レジスタ番号の4bit化
                self.MEM[address] += f"{int(opr[2:]):04b}"
            else:
                raise exceptions.InvalidRegister(index+1, opr)
        
        # オペランドがアドレスだった時のアセンブルをする関数
        def setAddress(addr, xr) -> None:
            nonlocal address, tempLabel, index
            # 数値の時 (アドレス番地直書き)
            if utils.isnum(addr):
                addr = utils.toInt(addr)
                if 0 <= addr < self.MEMLEN:
                    # 次のメモリ番地にアドレスを保存
                    self.MEM[address] = utils.binary16(addr)
                else:
                    raise exceptions.InvalidValue(index+1, addr)
            # リテラルのとき -> 一時的に、literalsにアドレスと値を保存
            elif addr[0] == "=":
                literals[address] = addr[1:]
            # ラベルの時 -> 一時的に、tempLabelにアドレスとラベル名を保存
            elif addr in self.labels:
                tempLabel[address] = addr
            else:
                raise exceptions.InvalidLabel(index+1, addr)

            # 指標レジスタの設定
            # 無い場合
            if xr == "":
                self.MEM[address-1] += "0000"
            # ある場合
            else:
                # GR0 は指標レジスタにならない
                if self.isGR(xr, True):
                    self.MEM[address-1] += f"{int(xr[2:]):04b}"
                else:
                    raise exceptions.InvalidRegister(index+1, xr)
                
        def setRegOrAddr(ra, xr) -> None:
            # まずはレジスタと予想。無理ならaddressでも検証して、address側のexceptionが返る
            nonlocal address
            try:
                if xr != "":
                    raise Exception   # GR0, GR1, GR1 みたいな時に GR0をラベル扱いしちゃうけど仕方ない
                setRegister(ra)
                mem = self.MEM[address]
                self.MEM[address] = mem[:5] + '1' + mem[6:]
            except:
                address += 1
                setAddress(ra, xr)
        
        # 機械語命令を変換する関数。SVCするときにも使うので関数化
        # 構文チェックと変換を同時に行うので煩雑……
        def toMachine(words) -> None:
            nonlocal address, tempLabel, index
            # ニーモニックの取得
            mnem = words[1]
            # ニーモニック -> 命令部8bitの変換
            if mnem not in self.MNEMONIC:
                raise exceptions.InvalidMnemonic(index+1)
            op = f"{self.MNEMONIC[mnem]:08b}"
            mainOP = int(op[0:4], 2)
            self.MEM[address] = op

            # オペランドたちの処理
            # オペランドなし -> NOP, RET
            if mnem == "NOP" or mnem == "RET":
                if len(words) != 2:
                    raise exceptions.InvalidOperand(index+1)
                # レジスタ部1, 2 に 0x00 を入れる
                self.MEM[address] += "00000000"
                return

            # r のみ -> POP, set系
            if mnem == "POP" or mnem[:3] == "SET":
                if len(words) != 3:
                    raise exceptions.InvalidOperand(index+1)
                setRegister(words[2])
                # レジスタ部2 に 0x0 を入れる
                self.MEM[address] += "0000"

            # r, val, xr -> shift系（主OP: 5）
            elif mainOP == 5:
                if not(4 <= len(words) <= 5) or self.isGR(words[3]):
                    raise exceptions.InvalidOperand(index+1)
                setRegister(words[2])
                xr = words[4] if len(words) == 5 else "" # 指標レジスタが無ければ ""
                setRegOrAddr(words[3], xr)

            # r1 r2  |  r, adr, xr  -> 主OP: 1~5, 9
            elif 1 <= mainOP <= 5 or mainOP == 9:
                if not(4 <= len(words) <= 5):
                    raise exceptions.InvalidOperand(index+1)
                setRegister(words[2])
                xr = words[4] if len(words) == 5 else "" # 指標レジスタが無ければ ""
                setRegOrAddr(words[3], xr)

            # adr, xr
            else:
                if not(3 <= len(words) <= 4):
                    raise exceptions.InvalidOperand(index+1)
                self.MEM[address] += "0000"
                address += 1
                xr = words[3] if len(words) == 4 else "" # 指標レジスタが無ければ ""
                setAddress(words[2], xr)

        # --------------------

        # コメントがあるとき -> ; 以降を消す
        # 各行を[ラベル, ニーモニック, opr1, opr2[, opr3]]に分割
        # 現時点では、空行やコメント行は 長さ0の [] になっている
        data = [utils.splitRow(utils.deleteComment(row)) for row in data]

        # 最初のニーモニックを取り出す
        first = ""
        for row in data:
            try:
                first = row[1]
                break
            except: continue

        if first != "START":
            raise exceptions.NotFoundSTART()
        
        endflag = False
        # ラベル名を登録。ついでに、コードに "END"命令があるかを確認
        for words in data:
            if len(words) > 0 and words[0] != '':
                self.labels[words[0]] = 0
            # END命令
            if len(words) > 1 and words[1] == "END":
                endflag = True
        # END命令が無いとき
        if not(endflag):
            return exceptions.NotFoundEND()

        address = 0
        start = ""      # START命令でラベルが指定されていた場合、ラベル名が入る
        tempLabel = {}  # {ラベルを使うアドレス : ラベル名}
        literals = {}   # {リテラルを使うアドレス : 値}
        # 逐次、命令をビット列に変換
        for index, words in enumerate(data):
            # メモリの上限よりコードが大きかったとき
            if address > self.MEMLEN:
                raise exceptions.BoundMemory(self.MEMLEN)

            self.DICT_AddrRow[address] = index + 1
            
            # 空行の場合
            if len(words) == 0:
                continue
            
            # 命令についたラベルとアドレスを対応付け
            if words[0] != "":
                self.labels[words[0]] = address

            # ニーモニックを取得
            try:
                mnem = words[1]
            except:
                continue
            
            # 機械語命令
            if mnem in self.MNEMONIC:
                toMachine(words)

            # アセンブラ命令
            elif mnem in ["START", "END", "DS", "DC"]:
                if mnem   == "START":
                    if len(words) == 2:
                        self.PC = address
                    else:
                        label = words[2]
                        if label in self.labels:
                            start = label
                        else:
                            raise exceptions.InvalidLabel(index+1, label)
                    continue
                elif mnem == "END":
                    # リテラルがある場合、END命令の前にまとめてDCされる
                    for addr, value in literals.items():
                        self.MEM[addr] = f"{address:016b}"
                        DC(value)
                    break   # END命令の後に書かれたものは無視するので、breakで強制終了
                elif mnem == "DS":
                    # 10進数で語数を指定するので、intで十分。無理ならinvalidで弾く
                    try:
                        address += int(words[2])
                    except:
                        raise exceptions.InvalidValue(index+1, words[2])
                    continue
                elif mnem == "DC":
                    const = words[2]
                    DC(const)
                    continue

            # マクロ命令 -> 命令群を生成する
            elif mnem in macros.MNEMONICS:
                macros.setIndex(index+1)
                orders = macros.expand(mnem, words)
                
                if orders == []:
                    raise exceptions.InvalidOperand(index+1)

                for words in orders:
                    # 行番号を登録
                    self.DICT_AddrRow[address] = index + 1
                    # 機械語命令を機械語に変換
                    toMachine(words)
                    address += 1
                continue

            # 保証されていない命令
            else:
                raise exceptions.InvalidMnemonic(index+1, mnem)
            
            address += 1

        # START命令にラベルがあった場合、対応するアドレスに返る
        if start != "":
            self.PC = self.labels[start]

        # ラベル関係を再評価
        for addr, label in tempLabel.items():
            self.MEM[addr] = f"{self.labels[label]:016b}"

        return self.getMemory()     # メモリをビット列の文字列に
        

    def fetch(self) -> None:
        self.nowPC = self.PC

        self.IR = self.MEM[self.PC]

        if self.isRegisterOP(self.IR[0:8]):   # ニーモニック r1 r2 形式の命令
            self.IR += f"{0x0000:016b}"
            self.PC += 1
        else:
            self.IR += self.MEM[self.PC+1]
            self.PC += 2
        self.msg = f"フェッチ: {self.IR}\n"
    

    def decode(self) -> int:
        isINop = (True if self.IR[0:30] == "111100000000000000000000000000" else False)
        self.DEC = [self.IR[0:8], self.IR[8:12], self.IR[12:16], self.IR[16:32]]
        self.msg = (f"デコード:\n"
                    f"  op  : {self.DEC[0]}  ({self.getMnemonic(self.DEC[0])})\n"
                    f"  r/r1: {self.DEC[1]}\n"
                    f"  x/r2: {self.DEC[2]}\n"
                    f"  adr : {self.DEC[3]}  (0x{int(self.DEC[3], 2):04X})\n")
        
        if isINop:  return 1
        else:       return 0

    def execute(self) -> int:
        self.msg = ""
        self.is_jump = False

        op = self.DEC[0]                     # オペコード
        mnem = self.getMnemonic(op)          # ニーモニック
        r1_num = int(self.DEC[1], 2)         # レジスタ1部の数値
        r1 = "GR" + str(r1_num)              # レジスタ1の名前
        r2_num = int(self.DEC[2], 2)         # レジスタ2部の数値
        r2 = "GR" + str(r2_num)              # レジスタ2の名前
        addr = self.getAddress()             # アドレス値 (指標アドレス加算済み)
        opr1 = self.getRegisterValue(r1_num) # r1の値
        opr2 = self.getNowAddressOrRegisterValue()        # r2の値 or アドレスの内容
        src = r2 if self.isRegisterOP(op) else f"0x{addr:04X}"

        # LD命令。アドレスからレジスタに代入。
        if mnem == "LD":
            self.msg = f"{src}の値({opr2}) を {r1} にロードします\n"
            self.GR[r1_num] = opr2
            self.setFlag(opr2)

        # ST命令。レジスタからアドレスに代入。
        elif mnem == "ST":
            self.msg = f"{r1}の値({opr1}) を 0x{addr:04X} にストアします\n"
            self.MEM[addr] = utils.binary16(opr1)
        
        # LAD。アドレス値をレジスタに代入
        elif mnem == "LAD":
            self.msg = f"0x{addr:04X} ({addr}) を {r1} にロードします\n"
            self.GR[r1_num] = addr

        
        # 加減算命令  r1 r2,  r1 adr [xr]
        elif mnem in ["ADDA", "ADDL", "SUBA", "SUBL"]:
            isArith = (mnem[3] == "A")
            isSUB = (mnem[0] == "S")

            v1 = utils.binToValue(utils.binary(opr1), isArith)
            v2 = utils.binToValue(utils.binary(opr2), isArith)

            self.msg = f"{r1}の値({v1}) に {src}の値({v2}) を{'算術' if isArith else '論理'}{'減算' if isSUB else '加算'}します\n"
            if isSUB: v2 = -v2
            self.GR[r1_num] = self.add(v1, v2, isArith)
        

        # 論理命令  r1 r2,  r1 adr [xr]
        elif mnem in ["AND", "OR", "XOR"]:
            self.ALU_A = utils.binary(opr1)
            self.ALU_B = utils.binary(opr2)
            v1 = list(self.ALU_A)
            v2 = list(self.ALU_B)
            if mnem == "AND":
                self.drawHissan(opr1, opr2, "&")
                bit = ['1' if v1[i] == v2[i] == '1' else '0' for i in range(self.REGBIT)]
            elif mnem == "OR":
                self.drawHissan(opr1, opr2, "|")
                bit = ['0' if v1[i] == v2[i] == '0' else '1' for i in range(self.REGBIT)]
            else:
                self.drawHissan(opr1, opr2, "^")
                bit = ['1' if v1[i] != v2[i] else '0' for i in range(self.REGBIT)]

            val = utils.binToValue(bit, (opr1 < 0 or opr2 < 0))
            self.Acc = val
            self.GR[r1_num] = val
            self.msg += f"  {utils.binary(val)}   ({val})"
            self.setFlag(val)


        # 比較命令  r1 r2,  r1 adr [xr]
        elif mnem == "CPA" or mnem == "CPL":
            isArith = (mnem == "CPA")
            opr1 = utils.binToValue(utils.binary(opr1), isArith)
            opr2 = utils.binToValue(utils.binary(opr2), isArith)

            self.msg = f"{r1}の値({opr1}) と {src}の値({opr2}) を{'算術' if isArith else '論理'}比較します\n"
            self.compare(opr1, opr2)


        # シフト命令  r1 val [xr]
        elif mnem in ["SLA", "SLL", "SRA", "SRL"]:
            isArith = (mnem[2] == "A")
            if mnem[1] == "L":
                self.msg = f"{r1}の値({opr1}) を {addr}bit {'算術' if isArith else '論理'}左シフトします\n"
                (bit, over) = self.lshift(opr1, addr, isArith)
            else:
                self.msg = f"{r1}の値({opr1}) を {addr}bit {'算術' if isArith else '論理'}右シフトします\n"
                (bit, over) = self.rshift(opr1, addr, isArith)

            self.msg += f"\n{utils.binary(opr1)} → {''.join(bit)}\n\n"
            val = utils.binToValue(bit, isArith)
            self.GR[r1_num] = val

            self.setFlag(val)
            self.FR |= over << 2    # 最後にあふれたビットover をOFフラグに格納 => 2桁シフト
            self.msg += f"最後に溢れた {over} が OF になります\n"


        # ジャンプ命令  adr [xr]
        elif mnem in ["JUMP", "JPL", "JMI", "JNZ", "JZE", "JOV"]:
            if mnem == "JUMP":
                self.msg = "JUMP"
                self.is_jump = True
            elif mnem == "JPL":
                self.msg = "SF = 0, ZF = 0"
                if not(self.FR & self.SIGN_FLAG or self.FR & self.ZERO_FLAG):  self.is_jump = True
            elif mnem == "JMI":
                self.msg = "SF = 1"
                if self.FR & self.SIGN_FLAG: self.is_jump = True
            elif mnem == "JNZ":
                self.msg = "ZF ≠ 1"
                if not(self.FR & self.ZERO_FLAG): self.is_jump = True
            elif mnem == "JZE":
                self.msg = "ZF = 1"
                if self.FR & self.ZERO_FLAG: self.is_jump = True
            else:
                self.msg = "OF = 1"
                if self.FR & self.OVERFLOW_FLAG: self.is_jump = True
            
            if self.is_jump:
                self.msg += f" なので、0x{addr:04X}にジャンプします\n"
                self.PC = addr
                return 0
            else:
                self.msg += " ではないので、ジャンプせず次の命令を実行します\n"


        # CALL命令  adr [xr]
        elif mnem == "CALL":
            self.push(self.PC)
            self.msg = f"SP を 1 減らして、0x{self.SP:04X}番地に PCの値({self.PC}) を格納します\n"
            self.PC = addr
            self.msg += f"新しく PC に {addr:04X} を設定します\n"
            return 0

        # RET命令
        elif mnem == "RET":
            try:
                self.PC = self.pop("PC")
                return 0
            except:
                self.msg = "スタックに戻り先がありません。メインルーチンのRETと見て終了します\n"
                return 1


        # PUSH命令  val [xr]
        elif mnem == "PUSH":
            self.push(addr)
            self.msg = f"SP を 1 減らして、0x{self.SP:04X}番地に {addr} を格納します\n"
        
        # POP命令  gr
        elif mnem == "POP":
            try:
                self.GR[r1_num] = self.pop(r1)
            except:
                self.msg = "Error: スタックに戻り先アドレスが存在しません\n"
                return -1


        # NOP命令
        elif mnem == "NOP":
            pass


        # SVC命令
        elif mnem == "SVC":
            length = int(self.MEM[self.GR[2]], 2)
            # 入力 IN
            if addr < 4:
                if length < 1:
                    self.msg = "Error: 文字長が 0以下 です\n"
                    return -1
                svc.svc_in(self.GR[1], length, addr)
                self.msg = "スーパーバイザーコール。OSの機能で入力を取得します\n"
            # 出力 OUT
            elif addr < 8:
                if length < 1:
                    self.msg = "Error: 文字長が 0以下 です\n"
                    return -1
                svc.svc_out(self.GR[1], length, addr)
                self.msg = "スーパーバイザーコール。OSの機能で文字列を出力します\n"
            # 乱数 RANDINT
            elif addr == 8:
                min = self.GR[2]
                max = self.GR[3]
                if min > max:
                    self.msg = f"Error: {min} > {max}  RANDINT命令のオペランドは 下限, 上限 です"
                    return -1
                self.GR[1] = svc.svc_rand(min, max)
                self.msg = "スーパーバイザーコール。OSの機能で乱数を生成します\n"
                
            else:
                self.msg = f"Error: 未定義のSVC命令番号です: {addr}\n"
                return -1

        # 追加命令
        elif mnem == "MUL":
            self.GR[r1_num] = self.mul(opr1, opr2)
        elif mnem == "DIV":
            if opr2 == 0:
                self.msg = "Error: 0で割ることはできません"
                return -1
            (self.GR[r1_num], remain) = self.div(opr1, opr2)
            if op[5] == '1':
                self.GR[r2_num] = remain
        
        elif mnem == "SETE":
            self.GR[r1_num] = 1 if self.FR & self.ZERO_FLAG else 0
        elif mnem == "SETGE":
            self.GR[r1_num] = 1 if not(self.FR & self.SIGN_FLAG) else 0
        elif mnem == "SETL":
            self.GR[r1_num] = 1 if self.FR & self.SIGN_FLAG else 0

        return 0
    

    # getterたち
    def getExecAddr(self) -> tuple[int, int]:
        return (self.getNowPC(),
                1 if self.isRegisterOP(self.getOperator()) else 2)

    def getRow(self) -> int:
        return self.DICT_AddrRow.get(self.nowPC, -1)
    
    def getAddressRow(self, address:int) -> int:
        return self.DICT_AddrRow.get(address, -1)
    
    def getLabelRow(self) -> int:
        if self.isRegisterOP(self.DEC[0]):
            return -1
        addr = int(self.DEC[3], 2)
        return self.DICT_AddrRow.get(addr, -1)

    def getAddress(self) -> int:
        if self.isRegisterOP(self.DEC[0]):
            return 0x10000
        address = int(self.DEC[3], 2)   # 命令レジスタの下位16bit
        register = int(self.DEC[2], 2)  # 命令レジスタの12~15bit目。修飾部
        offset = self.getRegisterValue(register)
        if register == 0:
            offset = 0  # GR0 は指標レジスタにならない
        return address + offset
        
    def getNowAddressOrRegisterValue(self):
        address = int(self.DEC[3], 2)   # 命令レジスタの下位16bit
        # address が 0 のとき、レジスタと思って opr2 のレジスタ値を返す
        if address == 0:
            reg = int(self.DEC[2], 2)  # 命令レジスタの12~15bit目
            return self.getRegisterValue(reg)
        else:
            return int(self.MEM[self.getAddress()], 2)

    def getOperator(self) -> str:
        '''命令部の8bitを返す。fetch時点でもdecode後でも関係なく得られる'''
        return self.IR[0:8]

    def getMnemonic(self, bit: str) -> str:
        '''
        辞書のvalueからkeyを抽出する => MNEMONIC辞書のbit列から名前を逆算
        '''
        if self.isRegisterOP(bit): bit = bit[:5] + '0' + bit[6:]
        value = int(bit, 2)

        for k, v in self.MNEMONIC.items():
            if v == value:
                return k
    

    def isRegisterOP(self, mnemonic: str) -> bool:
        '''
        この命令部bit列が、1語の命令であるか
        '''
        mainOP = mnemonic[0:4]
        subOP  = mnemonic[4:8]

        return (mainOP == '0000'                                       # 主OPが0 (0x00 NOP が引っかかる)
                or (int(mainOP, 2) <= 4 and subOP[1] == '1')           # 主OPが4以下 and 副OPが4以上 (論理演算系)
                or mnemonic == "01110001" or mnemonic == "10000001"    # 0x71 (POP) or 0x81 (RET)
                or (mainOP == '1001' and subOP[1] == '1')              # 主OPが9 and 副OPが4以上
                or mainOP == "1010")                                   # 主OPがA