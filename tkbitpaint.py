import Tkinter
import bitpaint
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
button_genaddress = Tkinter.Button(frame,text="NewAddress",command=NewAddressButton)
button_genaddress.pack(side=BOTTOM)
button_holdings = Tkinter.Button(frame,text="MyHoldings",command=MyHoldingsButton)
button_holdings.pack(side=BOTTOM)
tk.mainloop()


