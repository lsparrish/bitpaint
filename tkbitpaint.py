import Tkinter
import bitpaint, tkeditconfig
from Tkconstants import *
'''
Tkinter based gui for bitpaint
'''
def NewAddressButton():
    print bitpaint.generate_holding_address()

def MyHoldingsButton():
    print bitpaint.show_my_holdings()

tk = Tkinter.Tk()
frame = Tkinter.Frame(tk, relief=RIDGE, borderwidth=2)
frame.pack(fill=BOTH,expand=1)
label = Tkinter.Label(frame, text="BitPaint")
label.pack(fill=X, expand=1)
button_exit = Tkinter.Button(frame,text="Exit",command=tk.destroy)
button_exit.pack(side=BOTTOM)
button_genaddress = Tkinter.Button(frame,text="New Address",command=NewAddressButton)
button_genaddress.pack(side=BOTTOM)
button_holdings = Tkinter.Button(frame,text="My Holdings",command=MyHoldingsButton)
button_holdings.pack(side=BOTTOM)
button_editconfig = Tkinter.Button(frame,text="Edit Config",command=tkeditconfig.editConfig)
button_editconfig.pack(side=BOTTOM)
tk.mainloop()


