import Tkinter
from Tkconstants import *

class F:
    '''file load / save functions'''
    def load(self):
        f=open('bitpaint.conf','r')
        x=f.read()
        f.close()
        return x

    def save(self, x):
        f=open('bitpaint.conf','w')
        f.write(x)
        f.close()

def onclick():
   pass

def editConfig():
    '''edit the config file'''
    def OkayButton():
        x=text.get(1.0, END)
        f.save(x)
        tk.destroy()
    tk = Tkinter.Tk()
    text = Tkinter.Text(tk)
    f=F()
    x=f.load().rstrip()
    text.insert(Tkinter.INSERT, x)
    text.pack()
    frame = Tkinter.Frame(tk, relief=RIDGE, borderwidth=2)
    frame.pack(fill=BOTH,expand=1)
    button_okay = Tkinter.Button(frame,text="Okay",command=OkayButton)
    button_okay.pack(side=LEFT)
    button_cancel = Tkinter.Button(frame,text="Cancel",command=tk.destroy)
    button_cancel.pack(side=LEFT)
    tk.mainloop()
