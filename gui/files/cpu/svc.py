from random import randint


def svc_in(cpu, window, string, length, style):
    """cpu: CPU オブジェクト
    window: GUI window オブジェクト（または互換 API を持つオブジェクト）
    """
    if window is None:
        raise RuntimeError("svc_in requires a window instance for input operations")

    s = window.getInput()

    if style == 1:
        s = s[0:length]
        if len(s) > 256:    s = s[0:256]
        s = s.replace("\\t", "\t").replace("\\n", "\n")
        for i, c in enumerate(s):
            cpu.setMemory(string + i, f"{ord(c):016b}")
    elif style == 2:
        s = int(s)
        cpu.setMemory(string, f"{s:016b}")


def svc_out(cpu, window, string, length, style):
    if window is None:
        raise RuntimeError("svc_out requires a window instance for output operations")

    s = ""
    if style == 4 or style == 6:
        # string番地からlength長連続で読み出す。int(MEM, 2)で数値化して、chr()でasciiを文字に直す
        s = ''.join(chr(int(cpu.getMemory(string + i), 2)) for i in range(length))
    else:
        # 10進数で出力
        s = str(int(cpu.getMemory(string), 2))

    if style <= 5:
        s += "\n"
    window.outputWrite(s)


def svc_rand(min, max):
    return randint(min, max)
    