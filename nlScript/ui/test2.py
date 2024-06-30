from tkinter import *

root = Tk()

w = Label(root, text="Right-click to display menu", width=40, height=20)
w.place(x=0)


def function1():
    print('function1 activated')


# create a menu
f = Frame(root, width=80, height=60, background='green')
b2 = Button(f, text='function', command=function1)
b2.pack()


def open_popup(event):
    try:
        f.place(x=event.x, y=event.y)
        root.after(1)
        f.focus_set()
        w.bind_all("<Button-1>",close_popup)
    except:
        print("Can't open popup menu")


def close_popup(event):
    try:
        f.place_forget()
        root.after(1)
        w.unbind_all("<Button-1>")
    except:
        print("Can't close popup menu")


w.bind("<Button-3>", open_popup)

b = Button(root, text="Quit", command=root.destroy)
b.pack()

root.mainloop()