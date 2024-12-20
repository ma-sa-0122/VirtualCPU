from files.util import globalValues as gv

# 追加する場合は、MNEMONICSに命令名、expandに展開結果を追加

MNEMONICS = ["IN", "OUT", "RPUSH", "RPOP", "RANDINT"]

index = 0  # 行数を保存しておく。これを使って、一意なラベル名に
def setIndex(i):
    global index
    index = i


def expand(mnemonic, words) -> list:
    # INマクロ命令 入力領域, 入力文字長領域
    if mnemonic == "IN":
        if len(words) < 4:  return []
        opt = "1" if len(words) == 4 else words[4]
        return [
            ["", "PUSH", "0", "GR1"],
            ["", "PUSH", "0", "GR2"],
            ["", "LAD", "GR1", f"{words[2]}"],
            ["", "LAD", "GR2", f"{words[3]}"],
            ["", "SVC", f"{opt}"],
            ["", "POP", "GR2"],
            ["", "POP", "GR1"]
        ]

    # OUTマクロ命令 出力領域, 出力文字長領域
    elif mnemonic == "OUT":
        if len(words) < 4:  return []
        opt = 1 if len(words) == 4 else int(words[4])
        return [
            ["", "PUSH", "0", "GR1"],
            ["", "PUSH", "0", "GR2"],
            ["", "LAD", "GR1", f"{words[2]}"],
            ["", "LAD", "GR2", f"{words[3]}"],
            ["", "SVC", f"{opt+3}"],
            ["", "POP", "GR2"],
            ["", "POP", "GR1"]
        ]
    
    # RPUSHマクロ命令
    elif mnemonic == "RPUSH":
        return [["", "PUSH", "0", f"GR{i+1}"] for i in range(gv.REGISTER_NUM)]
    
    # RPOPマクロ命令
    elif mnemonic == "RPOP":
        return [["", "POP", f"GR{i+1}"] for i in range(gv.REGISTER_NUM)]
    
    # RANDINTマクロ命令 val, val
    elif mnemonic == "RANDINT":
        if len(words) < 4:  return []
        return [
            ["", "PUSH", "0", "GR2"],
            ["", "PUSH", "0", "GR3"],
            ["", "LAD", "GR2", f"{words[2]}"],
            ["", "LAD", "GR3", f"{words[3]}"],
            ["", "SVC", "8"],
            ["", "POP", "GR3"],
            ["", "POP", "GR2"]
        ]

    # 追加する場合はここに記述
    # elif mnemonic == "":
    #     return [
    #         []
    #     ]