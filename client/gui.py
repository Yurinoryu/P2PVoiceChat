import tkinter as tk

class ChatGUI:
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.root.title("VoiceChat")
        self.text = tk.Text(self.root)
        self.text.pack()
        self.entry = tk.Entry(self.root)
        self.entry.pack()
        self.entry.bind("<Return>", self.send)

    def send(self, event):
        msg = self.entry.get()
        self.client.send_chat(msg)
        self.entry.delete(0, tk.END)

    def run(self):
        self.root.mainloop()
