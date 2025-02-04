# 仮想CPU

卒業研究用の仮想CPU関係を纏めたものです。  

## gui

学習システムのGUIアプリケーションが入っています。  
開発言語は Python3.9 です。  

ふぁいるつりー  

```cmd
C:.
│  main.py
│  main2.py
│
└─files
    │  superGUI.py
    │  gui.py
    │  gui2.py
    │
    ├─cpu
    │      abstractCPU.py
    │      casl2.py
    │      exceptions.py
    │      macros.py
    │      svc.py
    │
    └─util
            globalValues.py
            utils.py
```

使用modules  

- abc
- random
- re
- Tkinter
- typing

## Text

学習システムの教科書が入っています。  
markdown で記述し、markdown PDF (https://marketplace.visualstudio.com/items?itemName=yzane.markdown-pdf) でPDF化しています。  

`n_photo/` ディレクトリには、教科書内に挿入されている画像ファイルが入っています。  
PowerPointで作成しました。  
`programs/` ディレクトリには、教科書内のアセンブリ言語プログラムをまとめています。 

## VTL

Very Tiny Language 関係が入っています（未完成）。  

`compiler.py` および `interpreter.py` は python で作成したVTLコンパイラ・インタプリタです。  

`compiler.as` は、仮想CPU用のアセンブリ言語で VTLのコンパイラを記述したものです。`interpreter.as` はインタプリタです。  
`コンパイラ.vtl` は、VTLで自身のコンパイラを記述しようとしているものです。未完成。  

`テスト.txt` には、簡単なプログラム例が入っています。コンパイルが正しくできているかのテストコード的な何か。  
`文法.txt` には、VTLの文法が定義されています。  
