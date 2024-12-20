from files.cpu.casl2 import CASL2
from files.gui import GUI1
from files.util import globalValues as gv

def main():
    gv.REGISTER_NUM = 8
    gv.REGISTER_BIT = 16
    gv.MEMORY_LENGTH = 0x10000
    gv.CPU = CASL2()
    root = GUI1(gv.CPU)
    gv.WINDOW = root
    root.mainloop()



main()