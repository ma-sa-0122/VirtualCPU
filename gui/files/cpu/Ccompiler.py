class CompileError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


# アセンブル結果
output = []


# ソースコード行と実行アセンブル行の対応表
dict_row = {}

def pos_to_lineno(pos: int) -> int:
    """pos（文字インデックス）から行番号を返す（1始まり）"""
    global user_input
    return user_input.count('\n', 0, pos) + 1

def emit(line: str, node):
    """
    アセンブリ出力用のラッパ関数。
    output と dict_row の両方に記録する。
    """
    global output, dict_row

    output.append(line)
    asm_line_no = len(output)  # 現在のアセンブリ行番号 (1-based)

    if node and node.src_line:
        dict_row[asm_line_no] = node.src_line


# Step22 配列の添え字
from enum import Enum
import copy

class TokenKind(Enum):
    TK_RESERVED = 1     # 記号
    TK_IDENT    = 2     # 識別子
    TK_NUM      = 3     # 整数トークン

    TK_RETURN   = 10    # returnトークン
    TK_IF       = 11    # ifトークン
    TK_ELSE     = 12    # elseトークン
    TK_WHILE    = 13    # whileトークン
    TK_FOR      = 14    # forトークン

    TK_INT      = 20    # intトークン
    
    TK_SIZEOF   = 30    # sizeofトークン

    TK_EOF      = 0     # 入力の終わりを表すトークン

class Token:
    def __init__(self):
        self.kind:  TokenKind = None # トークンの型
        self.next:  Token     = None # 次のトークン
        self.val:   int       = 0    # kindがTK_NUMの場合、その数値
        self.str:   str       = ""   # トークン文字列
        self.pos:   int       = 0    # 入力文字列インデックス。実質ポインタ

def new_token(kind: TokenKind, cur: Token, str) -> Token:
    tok = Token()
    tok.kind = kind
    tok.str = str
    cur.next = tok
    return tok

# 抽象構文木のノードの種類
class NodeKind(Enum):
    ND_ADD = 11 # +
    ND_SUB = 12 # -
    ND_MUL = 13 # *
    ND_DIV = 14 # /

    ND_EQU = 21 # ==
    ND_NEQ = 22 # !=
    ND_LSS = 23 # <
    ND_LEQ = 24 # <=
    ND_GTR = 25 # >
    ND_GEQ = 26 # >=

    ND_ASSIGN = 30  # =

    ND_RETURN = 40  # return
    ND_IF     = 41  # if
    ND_ELSE   = 42  # else
    ND_WHILE  = 43  # while
    ND_FOR    = 44  # for
    ND_BLOCK  = 45  # { block }

    ND_NUM = 0      # 整数
    ND_LVAR = 1     # ローカル変数
    ND_FUNC = 2     # 関数

    ND_ADDR = 3     # &
    ND_DEREF = 4    # *

# 抽象構文木のノードの型
class Node:
    def __init__(self):
        self.kind  : NodeKind = None # ノードの型
        self.lhs   : Node     = None # 左辺
        self.rhs   : Node     = None # 右辺
        self.val   : int      = 0    # kindがND_NUMの場合のみ使う
        self.offset: int      = 0    # kindがND_LVARの場合のみ使う
        self.type  : VarType  = None # 定数、変数、&, * など「式全体」がどういった型を持っているか

        # 制御構文用に色々追加
        # if (cond) then else els
        # while (cond) body
        # for (init; cond; loop) body
        # { block }
        # func(args) {}
        self.cond  : Node       = None
        self.then  : Node       = None
        self.els   : Node       = None
        self.init  : Node       = None
        self.loop  : Node       = None
        self.body  : Node       = None
        self.block : list[Node] = []

        self.args  : list[Node] = []
        self.argc  : int        = 0
        self.name  : str        = ""
        
        self.src_line: int = 0  # ソースコード上の行番号情報
        

def new_node(kind: NodeKind, lhs: Node, rhs: Node) -> Node:
    node = Node()
    node.kind = kind
    node.lhs = lhs
    node.rhs = rhs
    node.src_line = pos_to_lineno(token.pos) if token else 0  # ← 行番号付与
    return node

def new_node_num(val: int) -> Node:
    node = Node()
    node.kind = NodeKind.ND_NUM
    node.val = val
    # 型情報の追加
    node.type = int_type()
    node.src_line = pos_to_lineno(token.pos) if token else 0  # ← 行番号付与
    return node


class TypeKind(Enum):
    INT = 1
    PTR = 2
    ARRAY = 3

# 配列で困ったので結局オブジェクト参照でptr_toを作る
class VarType:
    def __init__(self):
        self.kind = None
        self.ptr_to = None
        self.array_size = 0

class LVar:
    def __init__(self):
        # nextを用意する代わりに、localsをリストにする
        self.name:   str           = ""      # 変数の名前
        self.offset: int           = 0       # RBPからのオフセット
        self.type:  VarType        = None    # 変数の型

# 変数を名前で検索する。見つからなかった場合はNULLを返す。
def find_lvar(tok: Token) -> LVar:
    global locals
    for var in locals:
        if tok.str == var.name:     # tok.len == var.len はmemcmp用に長さ比較してるだけなので省略
            return var
    return None

# 生成関数群
def int_type():
    ty = VarType()
    ty.kind = TypeKind.INT
    return ty

def ptr_to(base):
    ty = VarType()
    ty.kind = TypeKind.PTR
    ty.ptr_to = base
    return ty

def array_of(base, size):
    ty = VarType()
    ty.kind = TypeKind.ARRAY
    ty.ptr_to = base
    ty.array_size = size
    return ty

# 型のサイズを取得
def size_of(ty: VarType):
    if ty.kind == TypeKind.INT:
        return 1
    if ty.kind == TypeKind.PTR:
        return 1
    if ty.kind == TypeKind.ARRAY:
        return ty.array_size * size_of(ty.ptr_to)

# 配列 -> ポインタ変換
def decay(node: Node):
    if node.type.kind == TypeKind.ARRAY:
        node.type = ptr_to(node.type.ptr_to)
    return node


class Func:
    def __init__(self):
        self.name   : str = ""          # 関数名
        self.argc   : int = 0           # 引数の個数。espのオフセットに使う
        self.locals : list[LVar] = []   # グローバル変数だったもの。各関数用にローカル化
        self.code   : list[Node] = []   # グローバル変数だったもの。各関数用にローカル化


# 入力プログラム
user_input: str

# 現在着目しているトークン
token: Token

# 変数の連結リスト
locals: list[LVar] = []

code: list[Func] = []

# パーサ
def program():
    global code
    while not at_eof():
        code.append(define())

def define():
    global token, locals

    expect_int()
    func = None
    if consume_ident():
        func = Func()
        func.name = token.str

        token = token.next
        expect('(')
        while not consume(')'):
            expect_int()
            func.argc += 1

            lvar = LVar()
            ty = int_type()
            # ポインタ * を解釈
            while consume('*'):
                ty = ptr_to(ty)

            # 変数名に突入
            if not consume_ident():
                error_at(token.pos, "引数宣言が正しくありません")
            
            lvar.name = token.str
            token = token.next
            if consume('['):
                # 配列
                array_size = expect_number()
                lvar.type = array_of(ty, array_size)
                expect(']')
            else:
                # 普通の変数
                lvar.type = ty
            if len(locals) < 1: lvar.offset = size_of(lvar.type)     # 最初の変数
            else:               lvar.offset = locals[-1].offset + size_of(lvar.type)
            locals.append(lvar)

            if consume(')'):
                break
            expect(',')
        
        expect('{')
        while not consume('}'):
            tree = stmt()
            if tree is not None:    # int a; 変数宣言のとき、Noneが返ってくるので確認
                func.code.append(tree)
        func.locals = copy.deepcopy(locals) # localsに追加された変数たちを関数用に保存
        locals.clear()                      # グローバルのlocalsを初期化

    else:
        error_at(token.pos, "関数の定義がありません")
    
    return func

def stmt() -> Node:
    global token, locals

    node = None
    if token.kind == TokenKind.TK_RETURN:
        node = Node()
        node.kind = NodeKind.ND_RETURN
        node.src_line = pos_to_lineno(token.pos)
        token = token.next
        node.lhs = expr()
        expect(';')

    elif token.kind == TokenKind.TK_IF:
        node = Node()
        node.kind = NodeKind.ND_IF
        node.src_line = pos_to_lineno(token.pos)
        token = token.next
        expect('(')
        node.cond = expr()
        expect(')')
        node.then = stmt()
        if token.kind == TokenKind.TK_ELSE:
            token = token.next
            node.els = stmt()
        
    elif token.kind == TokenKind.TK_WHILE:
        node = Node()
        node.kind = NodeKind.ND_WHILE
        node.src_line = pos_to_lineno(token.pos)
        token = token.next
        expect('(')
        node.cond = expr()
        expect(')')
        node.body = stmt()
    
    elif token.kind == TokenKind.TK_FOR:
        node = Node()
        node.kind = NodeKind.ND_FOR
        node.src_line = pos_to_lineno(token.pos)
        token = token.next
        expect('(')
        if not consume(';'):
            node.init = expr()
            expect(';')
        if not consume(';'):
            node.cond = expr()
            expect(';')
        if not consume(')'):
            node.loop = expr()
            expect(')')
        node.body = stmt()

    # ブロック
    elif consume('{'):
        node = Node()
        node.kind = NodeKind.ND_BLOCK
        node.src_line = pos_to_lineno(token.pos)
        while not consume('}'):
            node.block.append(stmt())

    # 変数宣言
    elif token.kind == TokenKind.TK_INT:
        token = token.next
        # 変数を宣言して locals に登録するだけ。構文木は作らなくていい -> Noneを返す

        lvar = LVar()
        ty = int_type()
        # ポインタ * を解釈
        while consume('*'):
            ty = ptr_to(ty)

        # 変数名
        if not consume_ident():
            error_at(token.next.pos, "変数名として許容できません")
        
        lvar.name = token.str
        token = token.next
        if consume('['):
            # 配列
            array_size = expect_number()
            lvar.type = array_of(ty, array_size)
            expect(']')
        else:
            # 普通の変数
            lvar.type = ty
        if len(locals) < 1: lvar.offset = size_of(lvar.type)     # 最初の変数
        else:               lvar.offset = locals[-1].offset + size_of(lvar.type)
        locals.append(lvar)

        expect(';')
        return None

    else:
        node = expr()
        if not consume(";"):
            error_at(token.pos, "';'ではないトークンです")

    return node

def expr() -> Node:
    return assign()

def assign() -> Node:
    node = equality()
    if (consume("=")):
        node = new_node(NodeKind.ND_ASSIGN, node, assign())
        node.type = node.rhs.type
    return node

def equality() -> Node:
    node = relational()

    while True:
        if (consume('==')):
            node = new_node(NodeKind.ND_EQU, node, relational())
            node.type = int_type()
        elif (consume('!=')):
            node = new_node(NodeKind.ND_NEQ, node, relational())
            node.type = int_type()
        else:
            return node

def relational() -> Node:
    node = add()

    while True:
        if (consume('<')):
            node = new_node(NodeKind.ND_LSS, node, add())
            node.type = int_type()
        elif (consume('<=')):
            node = new_node(NodeKind.ND_LEQ, node, add())
            node.type = int_type()
        elif (consume('>')):
            node = new_node(NodeKind.ND_GTR, node, add())
            node.type = int_type()
        elif (consume('>=')):
            node = new_node(NodeKind.ND_GEQ, node, add())
            node.type = int_type()
        else:
            return node 

def add() -> Node:
    node = mul()

    while True:
        if (consume('+')):
            node = new_node(NodeKind.ND_ADD, node, mul())
            # 型決定
            if node.lhs.type.kind == TypeKind.PTR:     # p + 1 とか
                node.type = node.lhs.type
            elif node.rhs.type.kind == TypeKind.PTR:   # 1 + p とか
                node.type = node.rhs.type
            else:
                node.type = int_type()           # 1 + 2 とか
        elif (consume('-')):
            node = new_node(NodeKind.ND_SUB, node, mul())
            if node.lhs.type.kind == TypeKind.PTR:
                node.type = node.lhs.type
            else:
                node.type = int_type()
        else:
            return node

def mul() -> Node:
    node = unary()

    while True:
        if (consume('*')):
            node = new_node(NodeKind.ND_MUL, node, unary())
            node.type = int_type()
        elif (consume('/')):
            node = new_node(NodeKind.ND_DIV, node, unary())
            node.type = int_type()
        else:
            return node

def unary() -> Node:
    if (consume('+')):      # +5 -> 5     と解釈
        return primary()
    if (consume('-')):      # -5 -> 0 - 5 と解釈
        node = new_node(NodeKind.ND_SUB, new_node_num(0), primary())
        node.type = int_type()
        return node
    if (consume('*')):
        node = new_node(NodeKind.ND_DEREF, unary(), None)
        # 型情報の追加。デリファレンスは一階層中へ
        node.type = node.lhs.type.ptr_to
        return node
    if (consume('&')):
        node = new_node(NodeKind.ND_ADDR, unary(), None)
        # 型情報の追加。アドレスは「このノードはポインタだよ」情報の付加
        node.type = ptr_to(node.lhs.type)
        return node
    if (consume_sizeof()):
        expr = unary()
        node = new_node_num(size_of(expr.type))
        return node
    
    return postfix()

def primary() -> Node:
    global token, locals
    # 次のトークンが"("なら、"(" expr ")"のはず
    if (consume('(')):
        node = expr()
        expect(')')
        return node
    
    # 変数
    if (consume_ident()):
        tok = token
        token = token.next

        # 関数
        if consume('('):
            node = Node()
            node.kind = NodeKind.ND_FUNC
            node.type = int_type()
            node.name = tok.str
            node.src_line = pos_to_lineno(tok.pos)
            
            while not consume(')'):
                node.args.append(primary())
                node.argc += 1
                if consume(')'):
                    break
                expect(',')

                if node.argc > 4:
                    error_at(token.pos, "引数が 4つ より多い関数は対応していません")

        # 変数
        else:
            node = Node()
            node.kind = NodeKind.ND_LVAR
            node.src_line = pos_to_lineno(tok.pos)

            lvar = find_lvar(tok)
            if (lvar):
                node.offset = lvar.offset
                # 型情報の追加
                node.type = lvar.type
            else:
                error_at(tok.pos, "未定義の変数です")

        return node

    # そうでなければ数値のはず
    return new_node_num(expect_number())

def postfix():
    node = primary()

    while consume('['):
        idx = expr()
        expect(']')

        add = new_node(NodeKind.ND_ADD, node, idx)

        # x[y] -> *(x+y)
        deref = new_node(NodeKind.ND_DEREF, add, None)

        node = deref

    return node


def consume_ident() -> bool:
    global token
    if token.kind != TokenKind.TK_IDENT:
        return False
    return True

def consume_sizeof() -> bool:
    global token
    if token.kind != TokenKind.TK_SIZEOF:
        return False
    token = token.next
    return True



# エラー箇所を報告する
def error_at(pos: int, fmt: str, *args):
    global user_input
    if args:
        msg = fmt % args
    else:
        msg = fmt

    # エラー行と、その前1行だけ抽出
    prev_line_start = 0
    error_line_start = 0
    error_line_end = 0
    # エラー箇所から後方に、改行が出現するまで探す
    i = pos
    last_char = len(user_input)
    while user_input[i] != '\n':
        if i == last_char:  break
        i += 1
    error_line_end = i
    # エラー箇所から前方に、改行が2回出現するまで探す
    i = pos
    line_cnt = 0
    while line_cnt < 2:
        if i == 0:  break
        if user_input[i-1] == '\n':
            line_cnt += 1
            if line_cnt == 1:   error_line_start = i
            else:               prev_line_start = i
        i -= 1

    code_ex = user_input[prev_line_start:error_line_end]
    pos_cor = pos - error_line_start
    raise CompileError("%s\n%s^ %s" % (code_ex, " " * pos_cor, msg))

# エラーを報告するための関数
# printfと同じ引数を取る
def error(fmt, *args):
    if args:
        msg = fmt % args
    else:
        msg = fmt
    raise CompileError(msg)


def consume(op) -> bool:
    global token
    if token.kind != TokenKind.TK_RESERVED or token.str != op:
        return False
    token = token.next
    return True

def expect(op):
    global token
    if token.kind != TokenKind.TK_RESERVED or token.str != op:
        error_at(token.pos, "'%c'ではありません", op)
    token = token.next

def expect_number():
    global token
    if token.kind != TokenKind.TK_NUM:
        error_at(token.pos, "数ではありません")
    val = token.val
    token = token.next
    return val

def expect_int():
    global token
    if token.kind != TokenKind.TK_INT:
        error_at(token.pos, "'int' ではないトークンです")
    token = token.next

def at_eof() -> bool:
    global token
    return token.kind == TokenKind.TK_EOF

# トークンを構成する文字（英数字とアンダースコア）か
def is_alnum(c: str) -> int:
  return c.isalnum() or (c == '_')


def tokenize(p: str) -> Token:
    global user_input
    user_input = p   # error_at のために保存しておく

    head = Token()
    cur = head
    i = 0  # 文字位置を追跡

    while i < len(p):
        # 空白をスキップ
        if p[i].isspace():
            i += 1
            continue

        # 制御構文
        if p[i:i+6] == "return" and not is_alnum(p[i+6]):
            tok = new_token(TokenKind.TK_RETURN, cur, p[i:i+6])
            tok.pos = i
            cur = tok
            i += 6
            continue

        if p[i:i+2] == "if" and not is_alnum(p[i+2]):
            tok = new_token(TokenKind.TK_IF, cur, p[i:i+2])
            tok.pos = i
            cur = tok
            i += 2
            continue

        if p[i:i+4] == "else" and not is_alnum(p[i+4]):
            tok = new_token(TokenKind.TK_ELSE, cur, p[i:i+4])
            tok.pos = i
            cur = tok
            i += 4
            continue

        if p[i:i+5] == "while" and not is_alnum(p[i+5]):
            tok = new_token(TokenKind.TK_WHILE, cur, p[i:i+5])
            tok.pos = i
            cur = tok
            i += 5
            continue

        if p[i:i+3] == "for" and not is_alnum(p[i+3]):
            tok = new_token(TokenKind.TK_FOR, cur, p[i:i+3])
            tok.pos = i
            cur = tok
            i += 3
            continue

        # キーワード
        if p[i:i+3] == "int" and not is_alnum(p[i+3]):
            tok = new_token(TokenKind.TK_INT, cur, p[i:i+3])
            tok.pos = i
            cur = tok
            i += 3
            continue

        if p[i:i+6] == "sizeof" and not is_alnum(p[i+6]):
            tok = new_token(TokenKind.TK_SIZEOF, cur, p[i:i+6])
            tok.pos = i
            cur = tok
            i += 6
            continue

        # < より <= を先に判定する
        # そうしないと、<= を < と　= として解釈されてしまう
        if p[i:i+2] in ['==', '!=', '>=', '<=']:
            length = 2
            tok = new_token(TokenKind.TK_RESERVED, cur, p[i:i+length])
            tok.pos = i
            cur = tok
            i += length
            continue 

        if p[i] in ['+', '-', '*', '/', '(', ')', '>', '<', '=', ';', '{', '}', ',', '&', '[', ']']:
            tok = new_token(TokenKind.TK_RESERVED, cur, p[i])
            tok.pos = i
            cur = tok
            i += 1
            continue

        if p[i].isdigit():
            start = i
            val, rest = strtol(p[i:], 10)
            length = len(p[i:]) - len(rest)
            tok = new_token(TokenKind.TK_NUM, cur, p[start:start+length])
            tok.val = val
            tok.pos = start
            cur = tok
            i += length
            continue

        # アルファベットかアンダースコアならば、変数として TK_IDENT型のトークンを作る
        if p[i].isalpha() or p[i] == '_':
            start = i
            # アルファベット、数字、アンダースコアの限りは変数名の続き
            while p[i].isalnum() or p[i] == '_':
                i += 1
            cur = new_token(TokenKind.TK_IDENT, cur, p[start:i])
            cur.pos = start
            continue

        error_at(i, "トークナイズできません")

    tok = new_token(TokenKind.TK_EOF, cur, "")
    tok.pos = i
    return head.next

# 左辺値の検証を行う
def gen_lval(node: Node):
    if node.kind == NodeKind.ND_DEREF:
        # 中身の構文木を右辺値としてコンパイル
        gen(node.lhs)

    elif node.kind == NodeKind.ND_LVAR:
        emit("\tLD\teax, ebp", node)
        emit("\tSUBL\teax, =%d" % node.offset, node)
        emit("\tPUSH\t0, eax", node)

    else:
        error("代入の左辺値がデリファレンス* でも 変数 でもありません")

# 制御構文用の LbeginXXX, LelseXXX, LendXXX の連番
XXXnumber: int = 0

def gen(node: Node):
    global XXXnumber

    if node.kind == NodeKind.ND_NUM:
        emit("\tPUSH\t%d" % node.val, node)
        return
    if node.kind == NodeKind.ND_LVAR:
        if node.type.kind == TypeKind.ARRAY:
            # 配列型の値は、その値のアドレスをスタックにプッシュする
            gen_lval(node)
            return
        # 普通の変数は、アドレスをスタックに -> アドレス参照で中身を得る -> スタックに変数値をプッシュする
        gen_lval(node)
        emit("\tPOP\teax", node)
        emit("\tLD\teax, 0, eax", node)  # eaxの中身をアドレス参照。 mov eax, [eax]
        emit("\tPUSH\t0, eax", node)
        return
    if node.kind == NodeKind.ND_ASSIGN:
        gen_lval(node.lhs)
        gen(node.rhs)

        emit("\tPOP\tedx", node)
        emit("\tPOP\teax", node)
        emit("\tST\tedx, 0, eax", node)  # edxの中身を eaxのアドレス にストア
        emit("\tPUSH\t0, edx", node)
        return
    if node.kind == NodeKind.ND_RETURN:
        gen(node.lhs)
        emit("\tPOP\teax", node)
        emit("\tLD\tesp, ebp", node)
        emit("\tPOP\tebp", node)
        emit("\tRET", node)
        return
    if node.kind == NodeKind.ND_IF:
        # then, elsは結果をスタックから消さないと積まれたままで汚染される
        gen(node.cond)
        emit("\tPOP\teax", node)
        emit("\tCPL\teax, =0", node)
        xxx = XXXnumber
        XXXnumber += 1
        if node.els:
            emit("\tJZE\tLelse%03d" % xxx, node)
            gen(node.then)
            pop_expr(node.then)
            emit("\tJUMP\tLend%03d" % xxx, node)
            emit("Lelse%03d" % xxx, node)
            gen(node.els)
            pop_expr(node.els)
            emit("Lend%03d" % xxx, node)
        else:
            emit("\tJZE\tLend%03d" % xxx, node)
            gen(node.then)
            pop_expr(node.then)
            emit("Lend%03d" % xxx, node)
        return
    if node.kind == NodeKind.ND_WHILE:
        # body は結果をスタックから消さないと積まれたままで汚染される
        xxx = XXXnumber
        XXXnumber += 1
        emit("Lbegin%03d" % xxx, node)
        gen(node.cond)
        emit("\tPOP\teax", node)
        emit("\tCPL\teax, =0", node)
        emit("\tJZE\tLend%03d" % xxx, node)
        gen(node.body)
        pop_expr(node.body)
        emit("\tJUMP\tLbegin%03d" % xxx, node)
        emit("Lend%03d" % xxx, node)
        return
    if node.kind == NodeKind.ND_FOR:
        # init, body, loopは結果をスタックから消さないと積まれたままで汚染される
        xxx = XXXnumber
        XXXnumber += 1
        if node.init:
            gen(node.init)
            pop_expr(node.init)
        emit("Lbegin%03d" % xxx, node)
        if node.cond:
            gen(node.cond)
            emit("\tPOP\teax", node)
            emit("\tCPL\teax, =0", node)
            emit("\tJZE\tLend%03d" % xxx, node)
        gen(node.body)
        pop_expr(node.body)
        if node.loop:
            gen(node.loop)
            pop_expr(node.loop)
        emit("\tJUMP\tLbegin%03d" % xxx, node)
        emit("Lend%03d" % xxx, node)
        return
    if node.kind == NodeKind.ND_BLOCK:
        # 1つ1つのステートメントは1つの値をスタックに残すので、
        # それを毎回ポップするのを忘れないようにしましょう。
        for n in node.block:
            gen(n)
            pop_expr(n)
        return
    if node.kind == NodeKind.ND_FUNC:
        for arg in node.args:
            gen(arg)
        emit("\tPUSH\t%d" % node.argc, node)
        emit("\tPOP\teax", node)  # 引数の数 
        if node.argc >= 4: emit("\tPOP\tecx", node)  # 第4引数
        if node.argc >= 3: emit("\tPOP\tedx", node)  # 第3引数
        if node.argc >= 2: emit("\tPOP\tesi", node)  # 第2引数
        if node.argc >= 1: emit("\tPOP\tedi", node)  # 第1引数
        emit("\tCALL\t%s" % node.name, node)
        
        # 返却値が eax に入っているのでスタックに渡す
        emit("\tPUSH\t0, eax", node)
        return
    
    if node.kind == NodeKind.ND_ADDR:
        gen_lval(node.lhs)
        return
    if node.kind == NodeKind.ND_DEREF:
        gen(node.lhs)
        emit("\tPOP\teax", node)
        emit("\tLD\teax, 0, eax", node)
        emit("\tPUSH\t0, eax", node)
        return
    

    gen(node.lhs)
    gen(node.rhs)

    emit("\tPOP\tedx", node)
    emit("\tPOP\teax", node)

    if node.kind == NodeKind.ND_ADD:
        # ポインタへの足し算に対応（int* p = int + 1 は +4として見る、= ptr + 1 は +8として見る）
        if node.type == TypeKind.PTR:
            if node.lhs.type.kind == TypeKind.PTR: # ptr + int
                emit("\tMUL\tedx, =%d" % size_of(node.lhs.type.ptr_to), node)
            else:   # int + ptr
                emit("\tMUL\teax, =%d" % size_of(node.rhs.type.ptr_to), node)

        emit("\tADDA\teax, edx", node)
    elif node.kind == NodeKind.ND_SUB:
        # ポインタへの引き算に対応（ptr - intは型合わせ、ptr - ptr は最終的にintになる(/8)。int-ptrは構文エラー）
        if node.type == TypeKind.PTR:
            if node.rhs.type.kind == TypeKind.INT: # ptr - int
                emit("\tMUL\tedx, =%d" % size_of(node.lhs.type.ptr_to), node)
                emit("\tSUBA\teax, edx", node)
            else:  # ptr - ptr
                emit("\tSUBA\teax, edx", node)
                emit("\tDIV\teax, =%d" % size_of(node.lhs.type.ptr_to), node)
        else:
            emit("\tSUBA\teax, edx", node)
    elif node.kind == NodeKind.ND_MUL:
        emit("\tMUL\teax, edx", node)
    elif node.kind == NodeKind.ND_DIV:
        emit("\tDIV\teax, edx", node)
    
    elif node.kind == NodeKind.ND_EQU:
        emit("\tCPA\teax, edx", node)
        emit("\tSETE\teax", node)
    elif node.kind == NodeKind.ND_NEQ:
        emit("\tCPA\teax, edx", node)
        emit("\tSETNE\teax", node)
    elif node.kind == NodeKind.ND_LSS:
        emit("\tCPA\teax, edx", node)
        emit("\tSETL\teax", node)
    elif node.kind == NodeKind.ND_LEQ:
        emit("\tCPA\teax, edx", node)
        emit("\tSETLE\teax", node)
    elif node.kind == NodeKind.ND_GTR:
        emit("\tCPA\teax, edx", node)
        emit("\tSETG\teax", node)
    elif node.kind == NodeKind.ND_GEQ:
        emit("\tCPA\teax, edx", node)
        emit("\tSETGE\teax", node)

    emit("\tPUSH\t0, eax", node)

def compile(data: str) -> list[str]:
    global token, code, output, dict_row

    init_globals()

    # トークナイズしてパースする
    # 結果は code に保存される
    user_input = data
    token = tokenize(user_input)
    program()

    # アセンブリの前半部分を出力
    node = Node()
    # mainがあるか
    has_main = False
    for func in code:
        if func.name == "main":
            has_main = True
            node.src_line = func.code[0].src_line - 1   # 関数の一行目の前 -> 関数宣言のはず
            emit("____\tSTART\tmain", node)
    if not has_main:
        raise CompileError("main関数がありません")

    for func in code:
        node.src_line = func.code[0].src_line - 1

        emit(func.name, node)

        # プロローグ
        emit("\tPUSH\t0, ebp", node)
        emit("\tLD\tebp, esp", node)

        # レジスタ渡しされた実引数をスタックに入れる
        # -> ローカル変数と区別なく扱える
        if func.argc >= 1:  emit("\tPUSH\t0, edi", node) # 第1実引数
        if func.argc >= 2:  emit("\tPUSH\t0, esi", node) # 第2実引数
        if func.argc >= 3:  emit("\tPUSH\t0, edx", node) # 第3実引数
        if func.argc >= 4:  emit("\tPUSH\t0, ecx", node) # 第4実引数

        # 変数の個数分の領域を確保する
        stack_size = 0
        for var in func.locals:
            stack_size = max(stack_size, var.offset)

        emit("\tSUBL\tesp, =%d" % stack_size, node)


        # 先頭の式から順にコード生成
        for c in func.code:
            gen(c)

            # 式の評価結果としてスタックに一つの値が残っている
            # はずなので、スタックが溢れないようにポップしておく
            pop_expr(c)

        # エピローグ
        node.src_line = func.code[-1].src_line + 1  # 関数の最終行の次 -> 閉じ括弧のはず
        emit("\tLD\tesp, ebp", node)
        emit("\tPOP\tebp", node)
        emit("\tRET", node)

    emit("\tEND", node)
    return output, code, dict_row

def is_stmt(node: Node):
    return node.kind in [NodeKind.ND_RETURN, NodeKind.ND_IF, NodeKind.ND_WHILE, NodeKind.ND_FOR, NodeKind.ND_BLOCK]

def pop_expr(node: Node):
    if not is_stmt(node):
        emit("\tPOP\teax", node)


def init_globals():
    global output, dict_row, user_input, token, locals, code, XXXnumber
    output = []
    dict_row = {}
    user_input = ""
    token = None
    locals = []
    code = []
    XXXnumber = 0


# ~~~~~~~~~~
import re

def strtol(s: str, base: int = 10):
    """
    C言語の strtol と同じような挙動をする関数
    - 先頭の空白を無視
    - + / - を解釈
    - base に従って数値を解釈
    - 数値部分を返し、残りの文字列も返す
    """
    # 先頭の空白を無視
    s = s.lstrip()
    if not s:
        raise ValueError("invalid literal for strtol(): empty string")

    # 正規表現パターン生成
    if base == 10:
        pattern = r"[+-]?\d+"
    elif base == 16:
        # 0x / 0X の接頭辞も許容
        pattern = r"[+-]?(?:0[xX])?[0-9a-fA-F]+"
    elif base == 8:
        # 0o / 0O 接頭辞も許容（Python流）
        pattern = r"[+-]?(?:0[oO])?[0-7]+"
    elif base == 2:
        # 0b / 0B 接頭辞も許容
        pattern = r"[+-]?(?:0[bB])?[01]+"
    else:
        raise ValueError(f"base {base} not supported in this implementation")

    m = re.match(pattern, s)
    if not m:
        raise ValueError(f"invalid literal for strtol(): {s!r} with base {base}")

    num_str = m.group()
    rest = s[m.end():]
    return int(num_str, base), rest