from enum import Enum
from typing import Optional

class TokenKind(Enum):
    TK_RESERVED = 1     # 記号
    TK_IDENT    = 2     # 識別子（変数名など）
    TK_NUM      = 3     # 数値
    TK_END      = 5     # トークンの末尾

class Token():
    def __init__(self):
        self.kind   : TokenKind = None  # トークンの型
        self.next   : Token     = None  # 次のトークン
        self.val    : int       = 0     # 数値だった場合の値
        self.string : str       = ""    # トークン文字列
    
    def new(kind :TokenKind, cur, str :str):
        tok = Token()
        tok.kind = kind
        tok.string = str
        cur.next = tok
        return tok

class NodeKind(Enum):
    ND_ADD    = 11     # +
    ND_SUB    = 12     # -
    ND_MUL    = 13     # *
    ND_DIV    = 14     # /
    ND_EQU    = 15     # = (等価演算子)
    ND_GEQ    = 16     # >
    ND_LES    = 17     # <
    ND_ASSIGN = 1     # = (代入演算子)
    ND_NUM = 21     # 整数
    ND_VAR = 22     # 変数
    ND_STR = 23     # 文字列リテラル

class Node():
    def __init__(self):
        self.kind : NodeKind = None  # ノードの型
        self.lhs  : Node     = None  # 左辺
        self.rhs  : Node     = None  # 右辺
        self.val  : int      = 0     # kindがND_NUMの場合のみ使う
        self.var  : str      = ""    # kindがND_VARの場合のみ使う
    
    def new(kind: NodeKind, lhs, rhs):
        node = Node()
        node.kind = kind
        node.lhs = lhs
        node.rhs = rhs
        return node
    
    def new_num(val: int):
        node = Node()
        node.kind = NodeKind.ND_NUM
        node.val = val
        return node
    
    def new_ident(var: str):
        node = Node()
        node.kind = NodeKind.ND_VAR
        node.var = var
        return node
    
    def new_string(var: str):
        node = Node()
        node.kind = NodeKind.ND_STR
        node.var = var
        return node

# 現在のトークン
token :Token


# エラーを報告するための関数
def error(s: str):
    print(s)
    input()
    exit(1)

# 次のトークンが期待している記号のときには、トークンを1つ読み進めて
# 真を返す。それ以外の場合には偽を返す。
def consume(op : str) -> bool:
    global token
    if (token.kind != TokenKind.TK_RESERVED or token.string != op):
        return False
    token = token.next
    return True

# 次のトークンが変数の場合は、トークンを1つ読み進めて変数名を返す。
# それ以外の場合にはNoneを返す
def consume_ident() -> Optional[str]:
    global token
    if (token.kind != TokenKind.TK_IDENT):
        return None
    var = token.string
    token = token.next
    return var

# 次のトークンが期待している記号のときには、トークンを1つ読み進める。
# それ以外の場合にはエラーを報告する。
def expect(op : str) -> bool:
    global token
    if (token.kind != TokenKind.TK_RESERVED or token.string != op):
        error(f"'{op}'ではありません")
    token = token.next

# 次のトークンが数値の場合、トークンを1つ読み進めてその数値を返す。
# それ以外の場合にはエラーを報告する。
def expect_number() -> int:
    global token
    if (token.kind != TokenKind.TK_NUM):
        error("数ではありません")
    val = token.val
    token = token.next
    return val

# 次のトークンが文字列の場合、トークンを1つ読み進めてその文字列を返す。
# それ以外の場合にはエラーを報告する。
def expect_string() -> str:
    global token
    if (token.kind != TokenKind.TK_IDENT):
        error("文字列ではありません")
    var = token.string
    token = token.next
    return var

# 構文木の関係
def program() -> Node:
    # program = stmt
    code = stmt()
    return code

def stmt() -> Node:
    # stmt = ident "=" expr
    var = consume_ident()
    if var is None:
        error("代入先の変数がありません")
    node  = Node.new_ident(var)
    if not(consume('=')):
        error("代入演算子 '=' がありません")
    node = Node.new(NodeKind.ND_ASSIGN, node, expr())
    return node

def expr() -> Node:
    # expr = string | formula
    # 次のトークンが " なら "string" のはず
    if consume('"'):
        node = Node.new_string(expect_string())
        expect('"')
        return node
    # そうでなければ formula のはず
    return formula()

def formula() -> Node:
    # formula = ("+" | "-")? primary (記号系 primary)*
    if consume('+'):
        node = primary()
    elif consume('-'):
        node = Node.new(NodeKind.ND_SUB, Node.new_num(0), primary())    # -a は 0-a として解釈
    else:
        node = primary()

    while True:
        if consume('+'):
            node = Node.new(NodeKind.ND_ADD, node, primary())
        elif consume('-'):
            node = Node.new(NodeKind.ND_SUB, node, primary())
        elif consume('*'):
            node = Node.new(NodeKind.ND_MUL, node, primary())
        elif consume('/'):
            node = Node.new(NodeKind.ND_DIV, node, primary())
        elif consume('='):
            node = Node.new(NodeKind.ND_EQU, node, primary())
        elif consume('>'):
            node = Node.new(NodeKind.ND_GEQ, node, primary())
        elif consume('<'):
            node = Node.new(NodeKind.ND_LES, node, primary())
        else:
            return node

def primary() -> Node:
    # primary = num | ident | "(" formula ")"
    # 次のトークンが"("なら、"(" formula ")"のはず
    if consume('('):
        node = formula()
        expect(')')
        return node

    var = consume_ident()
    if var is None:
        # 変数でなければ数値のはず
        return Node.new_num(expect_number())
    return Node.new_ident(var)

# 構文木から機械語を生成
def gen(node : Node) -> None:
    if node is None:
        return
    # 代入演算子のとき
    if node.kind == NodeKind.ND_ASSIGN:
        # コメント行の場合何もしない
        if node.lhs.var == ';':
            return
        # 左辺は変数なので一旦無視。右辺を生成
        gen(node.rhs)
        return

    if node.kind == NodeKind.ND_NUM:
        print(f"\tPUSH\t{node.val}")
        return
    if node.kind == NodeKind.ND_VAR:
        if (node.var == '?'):
            print("\tIN\t?, v256")
            print("\tLD\tGR1, ?")
            print("\tPUSH\t0, GR1")
            return
        if (node.var == '$'):
            print("\tIN\t$, v1, 2")
            print("\tLD\tGR1, $")
            print("\tPUSH\t0, GR1")
            return
        if node.var == "'":
            print("\tPUSH\t0, GR1")
            print("\tRANDINT\t0, 65535")
            print("\tST\tGR1, '")
            print("\tPOP\tGR1")
        print(f"\tLD\tGR3, {node.var}")
        print(f"\tPUSH\t0, GR3")
        return
    if node.kind == NodeKind.ND_STR:
        return

    gen(node.lhs)
    gen(node.rhs)

    print("\tPOP\tGR2")
    print("\tPOP\tGR1")

    if (node.kind == NodeKind.ND_ADD):
        print("\tADDA\tGR1, GR2")
    elif (node.kind == NodeKind.ND_SUB):
        print("\tSUBA\tGR1, GR2")
    elif (node.kind == NodeKind.ND_MUL):
        print("\tMUL\tGR1, GR2")
    elif (node.kind == NodeKind.ND_DIV):
        print("\tDIV\tGR1, GR2")
        print("\tST\tGR2, %")
    elif (node.kind == NodeKind.ND_EQU):
        print("\tCPL\tGR1, GR2")
        print("\tSETE\tGR1")
    elif (node.kind == NodeKind.ND_GEQ):
        print("\tCPL\tGR1, GR2")
        print("\tSETGE\tGR1")
    elif (node.kind == NodeKind.ND_LES):
        print("\tCPL\tGR1, GR2")
        print("\tSETL\tGR1")

    print("\tPUSH\t0, GR1")

def genAssign(node: Node) -> None:
    left = node.lhs.var
    if node.rhs.kind == NodeKind.ND_STR:
        if left == '?':
            s = node.rhs.var
            l = strlen(s)
            print(f"\tOUT\t='{s}', ={l}")
            return
        else:
            error("変数に文字列リテラルは代入できません")
    if left == '?':
        # 変数や式は、結果をPUSHしてるのでPOPで取り出す
        print("\tPOP\tGR0")
        print("\tST\tGR0, ?")
        print("\tOUT\t?, v1, 2")
        return
    elif left == '$':
        print("\tPOP\tGR0")
        print("\tST\tGR0, $")
        print("\tOUT\t$, v1")
        return
    elif left == ';':
        return
    # 他の変数
    print("\tPOP\tGR0")
    print(f"\tST\tGR0, {left}")
    return
    

# def gen(node : Node) -> None:
#     print(f"[{node.kind=}, {node.val=}, {node.var=}]")

#     if node.kind == NodeKind.ND_NUM:
#         return
#     if node.kind == NodeKind.ND_VAR:
#         return
#     if node.kind == NodeKind.ND_STR:
#         return

#     gen(node.lhs)
#     print("-", end="")
#     gen(node.rhs)



# 入力文字列pをトークナイズしてそれを返す
def tokenize(p :str) -> list[Token]:
    head = Token()

    cur: Token = head
    i = 0
    while True:
        try:
            c = p[i]
        except:
            break        

        # 空白文字をスキップ
        if c.isspace():
            i += 1
            continue

        # 記号の場合
        if (c == '+' or c == '-' or c == '*' or c == '/' or
            c == '=' or c == '<' or c == '>' or
            c == '(' or c == ')'):
            cur = Token.new(TokenKind.TK_RESERVED, cur, c)
            i += 1
            continue

        # 数値の場合
        if (c.isdigit()):
            cur = Token.new(TokenKind.TK_NUM, cur, c)
            (cur.val, length) = strtol(p[i:], 10)
            i += length
            continue

        # 文字列の場合
        if (c == '"'):
            cur = Token.new(TokenKind.TK_RESERVED, cur, c)
            (s, length) = getString(p[i+1:])
            cur = Token.new(TokenKind.TK_IDENT, cur, s)
            cur = Token.new(TokenKind.TK_RESERVED, cur, c)
            i += length + 2 # 文字列の長さと " 2個分
            continue

        # 変数の場合  (変数名は A ~ Z, ~, &, %, ;, ?, $, #, !, ')
        if isVariable(c):
            cur = Token.new(TokenKind.TK_IDENT, cur, c)
            length = strlen(p[i:])
            i += length
            continue

        error("トークナイズできません")
    
    Token.new(TokenKind.TK_END, cur, '0')
    return head.next

def main():
    global token

    code = input("> ")

    # トークナイズしてパースする
    token = tokenize(code)
    node = program()

    # 抽象構文木を下りながらコード生成
    gen(node)
    genAssign(node)
    input()

# ------------------------
# c言語っぽいutil関数
def strtol(p:str, base) -> tuple[int, int]:
    num_str = ''

    l = 0
    # 数字が続く限り、num_strに追加
    for c in p:
        if c.isdigit():
            num_str += c
            l += 1
        else:
            break

    if num_str == '':  # 数字が見つからない場合はエラー
        raise ValueError(f"Invalid number: {p}")

    value = int(num_str, base)  # 数字部分を整数に変換
    return (value, l)

def strlen(p:str) -> int:
    l = 0
    for c in p:
        if isVariable(c):
            l += 1
        else:
            break
    return l

def getString(p:str) -> tuple[str, int]:
    string = ""
    l = 0
    while p[l] != '"':
        string += p[l]
        l += 1
    return (string, l)

# util
def isVariable(c: str) -> bool:
    return c.isupper() or c in ["~", "&", "%", ";", "?", "$", "#", "!", "'"]


main()