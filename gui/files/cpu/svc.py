from random import randint

from files.util import globalValues as gv


def svc_in(string, length, style):
    s = gv.WINDOW.getInput()

    if style == 1:
        s = s[0:length]
        if len(s) > 256:    s = s[0:256]
        s = s.replace("\\t", "\t").replace("\\n", "\n")
        for i, c in enumerate(s):
            gv.CPU.MEM[string+i] = f"{ord(c):016b}"
    if style == 2:
        s = int(s)
        gv.CPU.MEM[string] = f"{s:016b}"

def svc_out(string, length, style):
    s = ""
    if style == 4 or style == 6:
        # string番地からlength長連続で読み出す。int(MEM, 2)で数値化して、chr()でasciiを文字に直す
        s = ''.join(chr(int(gv.CPU.MEM[string+i], 2)) for i in range(length))
    else:
        # 10進数で出力
        s = str(int(gv.CPU.MEM[string], 2))

    if style <= 5:
        s += "\n"
    gv.WINDOW.outputWrite(s)

def svc_rand(min, max):
    return randint(min, max)
    