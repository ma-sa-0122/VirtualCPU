; VTLのコンパイラ
; GR0: 入力文字のchar
; GR1: 何文字目かカウンタ
;
; 文法
; program    = ident "=" expr
; expr       = string | formula
; formula    = ("+" | "-")? primary (("+" | "-" | "*" | "/" | "=" | "<" | ">") primary)*
; primary    = num | ident | "(" formula ")"

MAIN    START
        IN      input, ilen
        LAD     GR1, 0          ; initialize

        CALL    PROGRAM
        CALL    OUT2

; program    = ident "=" expr
PROGRAM CALL    READ_C
        ; 変数名取得 -> var に格納
        ST      GR0, var
        ; イコール1文字ぶん進む
        LAD     GR1, 1, GR1

        CALL    EXPR
        RET

; expr       = string | formula
EXPR    LD      GR0, input, GR1
        ; 1文字目取得（分岐のため）
        ; 文字列の場合
        CPL     GR0, ='"'
        JZE     STRING
        ; 式の場合
        JNZ     FORMULA

; formula    = primary (("+" | "-" | "*" | "/" | "=" | "<" | ">") primary)*
FORMULA CALL    PRIMARY
        CALL    READ_C
        CPL     GR0, ='+'
        JZE     SETPLUS
        CPL     GR0, ='-'
        JZE     SETMINS
        CPL     GR0, ='*'
        JZE     SETMUL
        CPL     GR0, ='/'
        JZE     SETDIV
        CPL     GR0, ='='
        JZE     SETEQU
        CPL     GR0, ='<'
        JZE     SETLES
        CPL     GR0, ='>'
        JZE     SETGEQ
        JNZ     ERROR

SETPLUS CALL    PRIMARY
        OUT     ='\tADDA\t', =6, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETMINS CALL    PRIMARY
        OUT     ='\tSUBA\t', =6, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETMUL  CALL    PRIMARY
        OUT     ='\tMUL\t', =5, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETDIV  CALL    PRIMARY
        OUT     ='\tDIV\t', =5, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETEQU  CALL    PRIMARY
        OUT     ='\tCPL\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tSETE\tGR1', =9
        JUMP    PUSHVAL
SETLES  CALL    PRIMARY
        OUT     ='\tCPL\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tSETL\tGR1', =9
        JUMP    PUSHVAL
SETGEQ  CALL    PRIMARY
        OUT     ='\tCPL\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tSETGE\tGR1', =10
PUSHVAL OUT     ='\tPUSH\t0, GR1', =12
        RET

; primary    = num | ident | "(" formula ")"
PRIMARY LD      GR0, input, GR1
        CALL    ISNUM
        CPL     GR7, =1
        JZE     SETNUM
;        CALL    ISVAR
;        CPL     GR7, =1
;        JZE     SETVAR
        CPL     GR0, ='('
        JNZ     ERROR
        CALL    FORMULA
        CPL     GR0, =')'
        JNZ     ERROR
        RET

SETNUM  CALL    READ_V
        ST      GR7, val
        OUT     ='\tPUSH\t', =6, 3
        OUT     val, =1, 2
        RET

STRING  CALL    READ_C            ; " を読む
        CALL    READ_C            ; 文字列1文字目を読む
        CPL     var, ='?'
        JZE     OUT1
        JNZ     ERROR

; 標準出力（文字列）。'OUT    ='str', =len' を出力
OUT1    CALL    STRLEN
        ST      GR5, slen
        OUT     ='\tOUT\t=\'', =7, 3     ; 改行無し出力
        OUT     sstr, slen, 3
        OUT     ='\', =', =4, 3
        OUT     slen, =1, 2             ; 10進数出力
        JUMP    FIN

; 出力（値）
OUT2    OUT     ='\tPOP\tGR0', =8
        OUT     ='\tST\tGR0, ', =9, 3
        CPL     var, ='?'
        JZE     OUTS
        CPL     var, ='$'
        JZE     OUTV
        JNZ     ERROR

; 標準出力（値）。'OUT    ?, v1, 2' を出力 
OUTS    OUT     ='?', =1
        OUT     ='\tOUT\t?, v1, 2',  =13
        JUMP    FIN

; 10進数値出力。'OUT    $, v1' を出力
OUTV    OUT     ='$', =1
        OUT     ='\tOUT\t$, v1', =10
        JUMP    FIN

; エラー出力
ERROR   OUT     estr, elen
        JUMP    FIN


; 1文字読む
READ_C  LD      GR0, input, GR1
        LAD     GR1, 1, GR1
        RET

; 数値を読む
READ_V  CALL    READ_C
        CALL    ISNUM
        CPL     GR7, =0
        JZE     RETURN
        SUBA    GR0, ='0'
        MUL     GR6, 10
        ADDA    GR6, GR0
        JUMP    READ_V

; 数値かどうか。数値: GR7 -> 1
ISNUM   LAD     GR7, 0
        CPL     GR0, ='0'
        JMI     RETURN
        CPL     GR0, ='9'
        JPL     RETURN
        LAD     GR7, 1
        RET

; 文字列の長さを取得 -> GR5
STRLEN  CPL     GR0, ='"'
        JZE     FIN
        LAD     GR5, 1, GR5
        CALL    READ_C
        JUMP    STRLEN

; リターン
RETURN  RET

; 終了処理。CALLが積まれまくってたとき用に無限ループしとく
FIN     RET
        JUMP    FIN

dest    DC      'GR0, GR1'
destlen DC      8
var     DS      1                   ; 変数名
val     DS      1                   ; 数値の一時的な格納先
estr    DC      'Syntax Error!'
elen    DC      13
slen    DC      0                   ; 文字列の文字数
sstr    DS      256                 ; 文字列を格納
input   DS      256
ilen    DC      256

        END