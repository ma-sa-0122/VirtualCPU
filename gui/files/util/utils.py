import re

def deleteComment(row: str) -> str:
    return re.sub(r"[\s]*;.*", "", row)

def splitRow(row: str) -> list:
    # [ラベル, ニーモニック, オペランドたち] に分割
    words = re.split(r'[\s]+', row, maxsplit=2)     # [\s]+ 1個以上の空白文字
    # オペランドたちを、カンマと空白で区切る
    if len(words) > 2 and words[2] != "":
        opr = words[2]
        # \' と 文字列中の , を置き換えてエスケープ
        opr = opr.replace("\\'", "###QUART###")
        # group(0) で正規表現にマッチした全体を取得。これをreplace
        opr = re.sub(r"'([^']*)'", lambda m: m.group(0).replace(',', '###COMMA###'), opr)
        # カンマ+0文字以上の空白 で分割
        opr = re.split(r",[\s]*", opr)
        # 置換を元に戻す
        opr = [w.replace('###QUART###', "\\'").replace('###COMMA###', ',') for w in opr]
        words = words[0:2] + opr


    # コメントを消すとき、「A ;~~」とかだと最後に '' が残るので消しとく
    if words[len(words)-1] == '':
        words = words[0:len(words) - 1]
    
    return words


def isnum(s: str) -> bool:
    try:
        if s[0] == "#":   int(s[1:], 16)
        else:             int(s)
    except:
        return False
    return True

def isValidNum(s: str, order: int) -> bool:
    """数値が指定されたビット幅で表現できるか検証する。
    order は必須（グローバル状態に依存しないため）
    """
    num = toInt(s)
    return (0 - (1 << (order-1)) <= num < (1 << order))

def toInt(s: str) -> int:
    if s[0] == "#":   return int(s[1:], 16)
    else:             return int(s)

def binary(num: int, order: int) -> str:
    '''
    num の2進数表現を返す。負数は2の補数表現を返す
    order は必須（グローバル状態に依存しないため）
    '''
    if num < 0:
        num = (~(-num) & ((1 << order) -1)) + 1  # ビット反転に桁数制限(& 0xF...) +1 で二の補数表現
    return f"{num:0{order}b}"[-order:]  # 下 order 桁を取り出す

def binary16(num: int) -> str:
    '''
    num の16bit2進数表現を返す。負数は2の補数表現を返す
    '''
    return binary(num, 16)


def binToValue(bin, isArith: bool, order: int) -> int:
    '''
    str, list[str], list[int] のビット列を数値に直す
    order は必須（グローバル状態に依存しないため）
    '''
    value = 0
    for i in range(order):
        value += (1 << ((order-1) - i)) * int(bin[i])
    if isArith and value >= (1 << (order - 1)):
        value = value - (1 << order)   #value - 2^nで2の補数が負になるよう調整
    return value