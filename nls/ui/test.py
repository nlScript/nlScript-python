from __future__ import print_function

import tkinter
from tkinter import *
from tkinter import ttk


class Editor(Tk):
    def __init__(self):
        super().__init__()

        self.title("Feet to Meters")

        self.mainframe = ttk.Frame(self, padding="3 3 12 12")
        self.mainframe.grid(column=0, row=0, sticky='nwes')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.script = Text(self.mainframe, width=40, height=10, wrap="none")
        ys = ttk.Scrollbar(self, orient='vertical', command=self.script.yview)
        xs = ttk.Scrollbar(self, orient='horizontal', command=self.script.xview)
        self.script['yscrollcommand'] = ys.set
        self.script['xscrollcommand'] = xs.set
        self.script.grid(column=0, row=0, sticky='nwes')
        xs.grid(column=0, row=1, sticky='we')
        ys.grid(column=1, row=0, sticky='ns')
        self.script.grid_columnconfigure(0, weight=1)
        self.script.grid_rowconfigure(0, weight=1)

        # self.script.bind('<<Modified>>', callback)
        self.script.bind('<KeyRelease>', self.display_autocomplete_menu)

        self.script.insert("end", "Lorem ipsum ...\n...\n...")

    def after_menu_post(self):
        print("bla")
        self.after(50)
        self.script.focus_force()
        print(self.focus_get())

    def display_autocomplete_menu(self, *arg):
        (x, y) = self.get_menu_coordinates()
        print("callback")
        self.complete_menu = Menu(self, tearoff=0, takefocus="", postcommand=self.after_menu_post)
        self.complete_menu.add_command(label="menu item 1")
        self.complete_menu.add_command(label="menu item 2")
        self.complete_menu.post(x, y)

    def get_menu_coordinates(self):
        bbox = self.script.bbox(tkinter.INSERT)
        menu_x = bbox[0] + self.script.winfo_rootx()
        menu_y = bbox[1] + self.script.winfo_rooty() + bbox[3]
        print(str(bbox))
        return menu_x, menu_y


if __name__ == "__main__":
    editor = Editor()
    editor.mainloop()