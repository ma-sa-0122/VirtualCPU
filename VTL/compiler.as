; VTLのコンパイラ
; GR0: 入力文字のchar
; GR1: 何文字目かカウンタ
; GR4: 比較用の一時呼び出し先
; GR5: SETSTRでの文字数
; GR6: READ_V の返却値
; GR7: ISNUM, ISVAR の返却値
;
; 作成されるアセンブリ言語でのレジスタの役割
; GR1: 被演算数・演算結果
; GR2: 演算数
; GR3: 変数値の呼び出し先
; GR4: ??のカウンタ
; GR5: !の一時格納先
;
; 文法
; programs   = program*
; program    = num " " ident "=" expr
; expr       = string | formula
; formula    = primary (("+" | "-" | "*" | "/" | "=" | "<" | ">") primary)*
; primary    = num | ident | "(" formula ")"

MAIN    START

        ; MAIN STARTの出力
        OUT     ='MAIN\tSTART', =10

WHILE   CALL    INFREE          ; inputの中身を再初期化
        IN      input, ilen
        LAD     GR0, #FFFF      ; 初期化
        LAD     GR1, 0
        LAD     GR3, 0
        ; 入力確認
        CPL     GR0, input
        JZE     ENDWL
        ; 解析
        CALL    PROGRAM
        JUMP    WHILE

ENDWL   ; ENDまでの出力
        CALL    DEFINE
        RET

; program    = num " " ident "=" expr
PROGRAM LD      GR0, input, GR1
        CALL    ISNUM
        CPL     GR7, =0
        JZE     ERROR
        ; 行番号を取得
        CALL    READ_V
        ST      GR6, row
        ; スペースか
        CALL    READ_C
        CPL     GR0, =' '
        JNZ     ERROR
        ; 変数名取得 -> var に格納
        CALL    READ_C
        ST      GR0, var
        ; 変数名が ; の場合 -> 何もしないでこの行の解析終了
        CPL     GR0, =#003B
        JZE     RETURN
        ; それ以外の場合、行番号を出力。#にも格納
        OUT     row, =1, 4              ; 10進数値改行無し出力
        OUT     ='\tLAD\tGR0, ', =10, 3 ; 改行無し出力
        OUT     row, =1, 2              ; 10進数値出力
        OUT     ='\tST\tGR0, #', =10
        ; イコールを処理（1文字飛ばす）
        LAD     GR1, 1, GR1
        ; expr部分
        CALL    EXPR
        RET

; expr       = string | formula
EXPR    ; 1文字目を見る（分岐のため）
        LD      GR0, input, GR1
        ; 文字列の場合
        CPL     GR0, ='"'
        JZE     STRING
        ; 式の場合
        CALL     FORMULA
        JUMP     OUT2

; string
STRING  CALL    READ_C            ; " を読む
        ; 代入先が ?（ターミナル出力）か
        LD      GR4, var
        CPL     GR4, ='?'
        JZE     OUT1
        JNZ     ERROR

; formula    = primary (("+" | "-" | "*" | "/" | "=" | "<" | ">") primary)*
FORMULA CALL    PRIMARY
F_LOOP  CALL    READ_C
        ; そもそも文字かどうか
        CALL    ISCHAR
        CPL     GR7, =0
        JZE     RETURN
        ; それぞれの演算子
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
        CALL    POPNUMS
        OUT     ='\tADDL\t', =6, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETMINS CALL    PRIMARY
        CALL    POPNUMS
        OUT     ='\tSUBL\t', =6, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETMUL  CALL    PRIMARY
        CALL    POPNUMS
        OUT     ='\tMUL\t', =5, 3
        OUT     dest, destlen
        JUMP    PUSHVAL
SETDIV  CALL    PRIMARY
        CALL    POPNUMS
        OUT     ='\tDIV\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tST\tGR2, %', =10
        JUMP    PUSHVAL
SETEQU  CALL    PRIMARY
        CALL    POPNUMS
        OUT     ='\tCPL\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tSETE\tGR1', =9
        JUMP    PUSHVAL
SETLES  CALL    PRIMARY
        CALL    POPNUMS
        OUT     ='\tCPL\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tSETL\tGR1', =9
        JUMP    PUSHVAL
SETGEQ  CALL    PRIMARY
        CALL    POPNUMS
        OUT     ='\tCPL\t', =5, 3
        OUT     dest, destlen
        OUT     ='\tSETGE\tGR1', =10
PUSHVAL OUT     ='\tPUSH\t0, GR1', =12
        JUMP    F_LOOP

POPNUMS OUT     ='\tPOP\tGR2', =8
        OUT     ='\tPOP\tGR1', =8
        RET

; primary    = num | ident | "(" formula ")"
PRIMARY ; 1文字見る
        LD      GR0, input, GR1
        ; 数値の場合
        CALL    ISNUM
        CPL     GR7, =1
        JZE     SETNUM
        ; 変数の場合
        CALL    ISVAR
        CPL     GR7, =1
        JZE     SETVAR
        ; ( の場合
        CPL     GR0, ='('
        JNZ     ERROR
        CALL    FORMULA
        CPL     GR0, =')'
        JNZ     ERROR
        RET

SETNUM  CALL    READ_V
        ST      GR6, val
        OUT     ='\tPUSH\t', =6, 3
        OUT     val, =1, 2
        RET

SETVAR  CALL    READ_C
        ST      GR0, tempvar
        CPL     GR0, ='?'
        JZE     VAR_?
        CPL     GR0, ='$'
        JZE     VAR_$
        CPL     GR0, ='\''
        JZE     VAR_'
        JNZ     VARPUSH
VAR_?   LD      GR0, input, GR1
        CPL     GR0, ='?'
        JZE     VAR_??
        CALL    ISNUM
        CPL     GR7, =1
        JZE     VAR_?n
        OUT     ='\tIN\t?, v256', =11
        JUMP    VARPUSH
VAR_??  LAD     GR1, 1, GR1
        OUT     ='\tLAD\tGR4, 1, GR4', =16
        OUT     ='\tLD\tGR3, ?, GR4', =15
        JUMP    PUSHGR3
VAR_?n  CALL    READ_V
        ST      GR6, val
        OUT     ='\tLAD\tGR3, ', =10, 3         ; 改行無し出力
        OUT     val, =1, 2                      ; 10進数出力
        OUT     ='\tLD\tGR3, ?, GR3', =15
        JUMP    PUSHGR3
VAR_$   OUT     ='\tIN\t$, v1, 2', =12
        JUMP    VARPUSH
VAR_'   OUT     ='\tPUSH\t0, GR1', =12
        OUT     ='\tRANDINT\t0, 65535', =17
        OUT     ='\tST\tGR1, \'', =10
        OUT     ='\tPOP\tGR1', =8
VARPUSH OUT     ='\tLD\tGR3, ', =9, 3           ; 改行無し出力
        OUT     tempvar, =1
PUSHGR3 OUT     ='\tPUSH\t0, GR3', =12
        RET

; 標準出力（文字列）。'OUT    ='str', =len' を出力
OUT1    CALL    GETSTR
        OUT     ='\tOUT\t=\'', =7, 3            ; 改行無し出力
        OUT     sstr, slen, 3
        OUT     ='\', =', =4, 3
        OUT     slen, =1, 2                     ; 10進数出力
        RET

; formula結果（値）の処理
OUT2    OUT     ='\tPOP\tGR1', =8
        LD      GR0, var
        ; 代入先（左辺）によって分岐
        ; # (実行行番号を変える) の場合
        CPL     GR0, ='#'
        JZE     JMP#
        ; それ以外は、一度変数にSTする
        OUT     ='\tST\tGR1, ', =9, 3
        ; ? (数値そのまま) の場合
        CPL     GR0, ='?'
        JZE     OUTV
        ; $ (数値をasciiコードと見る) の場合
        CPL     GR0, ='$'
        JZE     OUTC
        ; 変数のとき
        CALL    ISVAR
        CPL     GR7, =0
        JZE     ERROR
        OUT     var, =1
        RET

; #で指定先に飛ぶ
JMP#    LD      GR2, row
        LAD     GR2, 1, GR2
        ST      GR2, row
        OUT     ='\tLAD\tGR4, ', =10, 3
        OUT     row, =1, 2
        OUT     ='\tST\tGR4, !', =10
        OUT     ='\tJUMP\t0, GR1', =12
        RET

; 標準出力（値）。'OUT    ?, v1, 2' を出力 
OUTV    OUT     ='?', =1
        OUT     ='\tOUT\t?, v1, 2', =13
        RET

; 10進数値出力。'OUT    $, v1' を出力
OUTC    OUT     ='$', =1
        OUT     ='\tOUT\t$, v1', =10
        RET

; エラー出力
ERROR   OUT     estr, elen
POP_LP  POP     GR0             ; スタックを全部吐き出してエラー終了
        JUMP    POP_LP

; RETと変数たちとENDの出力
DEFINE  OUT     ='\tRET', =4
        OUT     ='v1\tDC\t1', =7
        OUT     ='v256\tDC\t256', =11
        OUT     ='A\tDC\t0', =6
        OUT     ='B\tDC\t0', =6
        OUT     ='C\tDC\t0', =6
        OUT     ='D\tDC\t0', =6
        OUT     ='E\tDC\t0', =6
        OUT     ='F\tDC\t0', =6
        OUT     ='G\tDC\t0', =6
        OUT     ='H\tDC\t0', =6
        OUT     ='I\tDC\t0', =6
        OUT     ='J\tDC\t0', =6
        OUT     ='K\tDC\t0', =6
        OUT     ='L\tDC\t0', =6
        OUT     ='M\tDC\t0', =6
        OUT     ='N\tDC\t0', =6
        OUT     ='O\tDC\t0', =6
        OUT     ='P\tDC\t0', =6
        OUT     ='Q\tDC\t0', =6
        OUT     ='R\tDC\t0', =6
        OUT     ='S\tDC\t0', =6
        OUT     ='T\tDC\t0', =6
        OUT     ='U\tDC\t0', =6
        OUT     ='V\tDC\t0', =6
        OUT     ='W\tDC\t0', =6
        OUT     ='X\tDC\t0', =6
        OUT     ='Y\tDC\t0', =6
        OUT     ='Z\tDC\t0', =6
        OUT     ='~\tDC\t#FFFF', =10
        OUT     ='%\tDC\t0', =6
        OUT     ='\'\tDC\t0', =6
        OUT     ='#\tDC\t0', =6
        OUT     ='$\tDS\t1', =6
        OUT     ='?\tDS\t256', =8
        OUT     ='\tEND', =4
        RET

; 関数 ------------------------------------------

;inputの中身メモリを再初期化
INFREE  LAD     GR6, 0
        LAD     GR7, 65535
FREE_LP ST      GR7, input, GR6
        LAD     GR6, 1, GR6
        CPL     GR6, ilen
        JMI     FREE_LP
        RET

; 1文字読む -> GR0
READ_C  LD      GR0, input, GR1
        LAD     GR1, 1, GR1
        RET

; 数値を読む -> GR6
READ_V  LAD     GR6, 0          ; 初期化
RV_LOOP LD      GR0, input, GR1 ; 1文字見る
        CALL    ISNUM
        CPL     GR7, =0
        JZE     RETURN
        LAD     GR1, 1, GR1     ; 見るだけじゃなく読む
        SUBA    GR0, ='0'
        MUL     GR6, =10
        ADDA    GR6, GR0
        JUMP    RV_LOOP

; 文字かどうか -> GR7
ISCHAR  LAD     GR7, 0
        CPL     GR0, =#007F
        JPL     RETURN
        LAD     GR7, 1
        RET

; 数値かどうか -> GR7
ISNUM   LAD     GR7, 0
        CPL     GR0, ='0'
        JMI     RETURN
        CPL     GR0, ='9'
        JPL     RETURN
        LAD     GR7, 1
        RET

; 変数かどうか -> GR7
ISVAR   LAD     GR7, 0
        CPL     GR0, ='\''
        JZE     CHANGE
        CPL     GR0, ='?'
        JZE     CHANGE
        CPL     GR0, ='~'
        JZE     CHANGE
        CPL     GR0, ='!'
        JZE     CHANGE
        CPL     GR0, =#0023     ; #, $, %
        JMI     RETURN
        CPL     GR0, =#0026
        JMI     CHANGE
        CPL     GR0, ='A'
        JMI     RETURN
        CPL     GR0, ='Z'
        JPL     RETURN
CHANGE  LAD     GR7, 1
        RET


; 文字列とその長さを取得 -> sstr, slen
GETSTR  LAD     GR5, 0          ; 初期化
GS_LOOP CALL    READ_C
        CPL     GR0, ='"'
        JZE     GS_END
        ST      GR0, sstr, GR5  ; sstrに一文字格納
        LAD     GR5, 1, GR5     ; 文字数を1増やす
        JUMP    GS_LOOP
GS_END  ST      GR5, slen       ; 文字数を slen に格納
        RET

; リターン
RETURN  RET

; 変数 ------------------------------------------

dest    DC      'GR1, GR2'
destlen DC      8
row     DS      1                   ; 行番号の格納先
var     DS      1                   ; 変数名
val     DS      1                   ; 数値を"PUSH"するための一時的な格納先
tempvar DS      1                   ; formula内の変数名を"PUSH"するための一時的な格納先
estr    DC      'Syntax Error!'
elen    DC      13
slen    DC      0                   ; 文字列stringの文字数
sstr    DS      256                 ; 文字列stringを格納
input   DS      256
ilen    DC      256

        END