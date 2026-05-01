import base64
import json
import os
import queue
import traceback
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from client.client import Client
from client.invite import create_invite, get_tailscale_host, parse_invite
from client.voice import VoiceClient, check_voice_support
from common.config import APP_NAME
from common.diagnostics import format_runtime_diagnostics
from host.host_server import HostServer
from host.voice_router import VoiceRouter


class ChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1120x680")
        self.root.configure(bg="#11161c")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.ui_queue = queue.Queue()
        self.client = None
        self.voice_client = None
        self.room_users = {}
        self.image_refs = []
        self.invite_code = ""
        self.hosting_started = False
        self.voice_enabled = False

        self.username_var = tk.StringVar(value="Guest")
        self.host_var = tk.StringVar(value=get_tailscale_host())
        self.invite_var = tk.StringVar()
        voice_ready, voice_message = check_voice_support()
        self.voice_enabled = voice_ready
        initial_status = "Ready. Tailscale should already be connected."
        if not voice_ready:
            initial_status = f"{initial_status} {voice_message} Text chat will still work."

        self.status_var = tk.StringVar(value=initial_status)

        self.participants_frame = None
        self.feed = None
        self.message_entry = None
        self.invite_text = None

        self._build_connect_view()
        self.root.after(80, self._process_ui_queue)

    def run(self):
        self.root.mainloop()

    def _build_connect_view(self):
        self.connect_frame = tk.Frame(self.root, bg="#11161c", padx=26, pady=24)
        self.connect_frame.pack(fill="both", expand=True)

        title = tk.Label(
            self.connect_frame,
            text=APP_NAME,
            fg="#f3f6f8",
            bg="#11161c",
            font=("Segoe UI", 24, "bold"),
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            self.connect_frame,
            text="Tailscale room setup for small private groups.",
            fg="#94a7b7",
            bg="#11161c",
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(6, 20))

        form = tk.Frame(self.connect_frame, bg="#11161c")
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        host_card = self._card(form, "Host Room")
        host_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        join_card = self._card(form, "Join Room")
        join_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self._labeled_entry(host_card, "Your Name", self.username_var)
        self._labeled_entry(host_card, "Tailscale Host", self.host_var)

        detect_btn = tk.Button(
            host_card,
            text="Detect Tailscale IP",
            command=self._detect_tailscale_host,
            bg="#1f6feb",
            fg="white",
            relief="flat",
            padx=12,
            pady=8,
        )
        detect_btn.pack(anchor="w", pady=(4, 12))

        diagnostics_btn = tk.Button(
            host_card,
            text="Diagnostics",
            command=self._show_diagnostics,
            bg="#2f3944",
            fg="#f3f6f8",
            relief="flat",
            padx=12,
            pady=8,
        )
        diagnostics_btn.pack(anchor="w", pady=(0, 12))

        host_btn = tk.Button(
            host_card,
            text="Start Hosted Room",
            command=self._host_room,
            bg="#13a16a",
            fg="white",
            relief="flat",
            padx=14,
            pady=10,
        )
        host_btn.pack(anchor="w")

        self.invite_text = tk.Text(
            host_card,
            height=6,
            wrap="word",
            bg="#0d1117",
            fg="#d7e0e7",
            insertbackground="#d7e0e7",
            relief="flat",
        )
        self.invite_text.pack(fill="x", pady=(16, 0))

        copy_invite_btn = tk.Button(
            host_card,
            text="Copy Invite",
            command=self._copy_invite,
            bg="#2f3944",
            fg="#f3f6f8",
            relief="flat",
            padx=12,
            pady=8,
        )
        copy_invite_btn.pack(anchor="w", pady=(10, 0))

        self._labeled_entry(join_card, "Your Name", self.username_var)
        self._labeled_entry(join_card, "Invite Code", self.invite_var)

        join_btn = tk.Button(
            join_card,
            text="Join Room",
            command=self._join_from_invite,
            bg="#f59f00",
            fg="#11161c",
            relief="flat",
            padx=14,
            pady=10,
        )
        join_btn.pack(anchor="w", pady=(6, 0))

        footer = tk.Label(
            self.connect_frame,
            textvariable=self.status_var,
            fg="#94a7b7",
            bg="#11161c",
            font=("Segoe UI", 10),
            pady=16,
        )
        footer.pack(anchor="w")

    def _build_room_view(self):
        self.connect_frame.pack_forget()

        self.room_frame = tk.Frame(self.root, bg="#11161c")
        self.room_frame.pack(fill="both", expand=True)
        self.room_frame.columnconfigure(0, weight=1, minsize=320)
        self.room_frame.columnconfigure(1, weight=2, minsize=540)
        self.room_frame.rowconfigure(1, weight=1)

        top_bar = tk.Frame(self.room_frame, bg="#151c23", padx=20, pady=14)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        top_bar.columnconfigure(0, weight=1)

        title = tk.Label(
            top_bar,
            text="Room",
            fg="#f3f6f8",
            bg="#151c23",
            font=("Segoe UI", 16, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        status = tk.Label(
            top_bar,
            textvariable=self.status_var,
            fg="#94a7b7",
            bg="#151c23",
            font=("Segoe UI", 10),
        )
        status.grid(row=1, column=0, sticky="w", pady=(4, 0))

        left = tk.Frame(self.room_frame, bg="#0f141a", padx=18, pady=18)
        left.grid(row=1, column=0, sticky="nsew")
        left.rowconfigure(2, weight=1)

        members_title = tk.Label(
            left,
            text="People Here",
            fg="#f3f6f8",
            bg="#0f141a",
            font=("Segoe UI", 14, "bold"),
        )
        members_title.grid(row=0, column=0, sticky="w")

        members_hint = tk.Label(
            left,
            text="Names light up while someone is talking.",
            fg="#8ca0b0",
            bg="#0f141a",
            font=("Segoe UI", 10),
        )
        members_hint.grid(row=1, column=0, sticky="w", pady=(4, 14))

        self.participants_frame = tk.Frame(left, bg="#0f141a")
        self.participants_frame.grid(row=2, column=0, sticky="nsew")

        right = tk.Frame(self.room_frame, bg="#141b22", padx=18, pady=18)
        right.grid(row=1, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        chat_header = tk.Label(
            right,
            text="Chat",
            fg="#f3f6f8",
            bg="#141b22",
            font=("Segoe UI", 14, "bold"),
        )
        chat_header.grid(row=0, column=0, sticky="w")

        self.feed = tk.Text(
            right,
            wrap="word",
            state="disabled",
            bg="#0d1117",
            fg="#d7e0e7",
            relief="flat",
            padx=14,
            pady=14,
        )
        self.feed.grid(row=1, column=0, sticky="nsew", pady=(12, 14))

        composer = tk.Frame(right, bg="#141b22")
        composer.grid(row=2, column=0, sticky="ew")
        composer.columnconfigure(0, weight=1)

        self.message_entry = tk.Entry(
            composer,
            bg="#eef3f6",
            fg="#11161c",
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12), ipady=10)
        self.message_entry.bind("<Return>", self._send_message)

        send_btn = tk.Button(
            composer,
            text="Send",
            command=self._send_message,
            bg="#1f6feb",
            fg="white",
            relief="flat",
            padx=16,
            pady=10,
        )
        send_btn.grid(row=0, column=1, padx=(0, 8))

        image_btn = tk.Button(
            composer,
            text="Image",
            command=self._send_image,
            bg="#2f3944",
            fg="#f3f6f8",
            relief="flat",
            padx=16,
            pady=10,
        )
        image_btn.grid(row=0, column=2)

    def _card(self, parent, title):
        frame = tk.Frame(parent, bg="#182029", padx=18, pady=18)
        heading = tk.Label(
            frame,
            text=title,
            fg="#f3f6f8",
            bg="#182029",
            font=("Segoe UI", 15, "bold"),
        )
        heading.pack(anchor="w", pady=(0, 14))
        return frame

    def _labeled_entry(self, parent, label, var):
        lbl = tk.Label(
            parent,
            text=label,
            fg="#9fb0bf",
            bg="#182029",
            font=("Segoe UI", 10),
        )
        lbl.pack(anchor="w", pady=(0, 6))
        entry = tk.Entry(
            parent,
            textvariable=var,
            bg="#f3f6f8",
            fg="#11161c",
            relief="flat",
            font=("Segoe UI", 11),
        )
        entry.pack(fill="x", ipady=10, pady=(0, 14))
        return entry

    def _detect_tailscale_host(self):
        detected = get_tailscale_host()
        if detected:
            self.host_var.set(detected)
            self.status_var.set(f"Detected Tailscale host {detected}")
        else:
            self.status_var.set("Could not auto-detect Tailscale. Enter your Tailscale IP or DNS name.")

    def _host_room(self):
        username = self.username_var.get().strip() or "Host"
        host = self.host_var.get().strip()
        if not host:
            messagebox.showerror("Missing Host", "Enter your Tailscale IP or Tailscale DNS name first.")
            return

        self.invite_code = create_invite(host)
        invite_payload = parse_invite(self.invite_code)

        self.invite_text.delete("1.0", tk.END)
        self.invite_text.insert("1.0", self.invite_code)

        with open("invite.txt", "w", encoding="utf-8") as handle:
            handle.write(self.invite_code)
        with open("invite.json", "w", encoding="utf-8") as handle:
            json.dump(invite_payload, handle, indent=2)

        if not self.hosting_started:
            try:
                host_server = HostServer(invite_payload["session_key"])
                voice_router = VoiceRouter(invite_payload["session_key"])
            except OSError as exc:
                messagebox.showerror("Startup Failed", f"Could not bind the room ports.\n\n{exc}")
                return

            self.hosting_started = True
            self._start_background_worker("Host Server", host_server.start)
            self._start_background_worker("Voice Router", voice_router.start)

        self.status_var.set("Room started. Share the invite code and stay connected to Tailscale.")
        self._join_room(invite_payload, username)

    def _join_from_invite(self):
        invite = self.invite_var.get().strip()
        username = self.username_var.get().strip() or "Guest"
        if not invite:
            messagebox.showerror("Missing Invite", "Paste the invite code from the host first.")
            return

        try:
            invite_payload = parse_invite(invite)
        except Exception:
            messagebox.showerror("Bad Invite", "That invite code could not be decoded.")
            return

        self._join_room(invite_payload, username)

    def _join_room(self, invite_payload, username):
        try:
            self.client = Client(
                invite_payload["host"],
                username,
                invite_payload["tcp_port"],
                invite_payload["session_key"],
            )
            self.client.on("connected", lambda payload: self.ui_queue.put(("connected", payload)))
            self.client.on("chat", lambda payload: self.ui_queue.put(("chat", payload)))
            self.client.on("image", lambda payload: self.ui_queue.put(("image", payload)))
            self.client.on("room_state", lambda payload: self.ui_queue.put(("room_state", payload)))
            self.client.on("talking", lambda payload: self.ui_queue.put(("talking", payload)))
            self.client.on("status", lambda payload: self.ui_queue.put(("status", payload)))
            self.client.start()
        except Exception as exc:
            messagebox.showerror("Connection Failed", str(exc))
            return

        if not hasattr(self, "room_frame"):
            self._build_room_view()

        self.status_var.set(f"Connecting to {invite_payload['host']} over Tailscale...")

        def wait_for_identity():
            while self.client and self.client.user_id is None:
                self.root.after(0, lambda: None)
                threading.Event().wait(0.1)

            if self.client and self.client.user_id is not None:
                self.root.after(0, lambda: self._start_voice(invite_payload))

        threading.Thread(target=wait_for_identity, daemon=True).start()

    def _start_background_worker(self, name, target):
        thread = threading.Thread(target=lambda: self._run_background_task(name, target), daemon=True)
        thread.start()

    def _run_background_task(self, name, target):
        try:
            target()
        except Exception as exc:
            self.ui_queue.put(("status", {"message": f"{name} stopped: {exc}"}))
            traceback.print_exc()

    def _show_diagnostics(self):
        messagebox.showinfo("Runtime Diagnostics", format_runtime_diagnostics())

    def _copy_invite(self):
        if not self.invite_code:
            self.status_var.set("Start a hosted room first so there is an invite to copy.")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(self.invite_code)
        self.status_var.set("Invite code copied to the clipboard.")

    def _start_voice(self, invite_payload):
        try:
            self.voice_client = VoiceClient(
                invite_payload["host"],
                self.client.user_id,
                invite_payload["session_key"],
                self._local_talking_changed,
                invite_payload["udp_port"],
            )
            self.voice_client.start()
            self.voice_enabled = True
            self.status_var.set("Connected. Voice is live when your microphone picks up speech.")
        except Exception as exc:
            self.voice_client = None
            self.voice_enabled = False
            self.status_var.set(f"Connected for text chat. {exc}")

    def _send_message(self, event=None):
        if not self.client:
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        self.client.send_chat(message)
        self.message_entry.delete(0, tk.END)

    def _send_image(self):
        if not self.client:
            return

        path = filedialog.askopenfilename(
            title="Choose image",
            filetypes=[
                ("Image files", "*.png *.gif"),
                ("PNG files", "*.png"),
                ("GIF files", "*.gif"),
            ],
        )
        if not path:
            return

        with open(path, "rb") as handle:
            image_data = base64.b64encode(handle.read()).decode("ascii")

        self.client.send_image(os.path.basename(path), image_data)

    def _process_ui_queue(self):
        while True:
            try:
                event_name, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            if event_name == "connected":
                if self.voice_enabled:
                    self.status_var.set("Connected. Voice is live when your microphone picks up speech.")
                else:
                    self.status_var.set("Connected for text chat. Voice is not active on this device.")
            elif event_name == "chat":
                self._append_message(payload["username"], payload["message"])
            elif event_name == "image":
                self._append_image(payload["username"], payload["filename"], payload["image_data"])
            elif event_name == "room_state":
                self._apply_room_state(payload["users"])
            elif event_name == "talking":
                self._set_talking(payload["user_id"], payload["talking"])
            elif event_name == "status":
                self.status_var.set(payload["message"])

        self.root.after(80, self._process_ui_queue)

    def _apply_room_state(self, users):
        preserved_talking = {uid: user.get("talking", False) for uid, user in self.room_users.items()}
        self.room_users = {
            user["user_id"]: {
                "username": user["username"],
                "talking": preserved_talking.get(user["user_id"], False),
            }
            for user in users
        }
        self._render_participants()

    def _set_talking(self, user_id, talking):
        if user_id not in self.room_users:
            return

        self.room_users[user_id]["talking"] = talking
        self._render_participants()

    def _local_talking_changed(self, talking):
        if self.client:
            self.client.send_talking(talking)
            if self.client.user_id in self.room_users:
                self.room_users[self.client.user_id]["talking"] = talking
                self.root.after(0, self._render_participants)

    def _render_participants(self):
        for child in self.participants_frame.winfo_children():
            child.destroy()

        if not self.room_users:
            empty = tk.Label(
                self.participants_frame,
                text="Nobody connected yet.",
                fg="#8ca0b0",
                bg="#0f141a",
                font=("Segoe UI", 11),
            )
            empty.pack(anchor="w")
            return

        for user_id, user in sorted(self.room_users.items(), key=lambda item: item[1]["username"].lower()):
            row = tk.Frame(self.participants_frame, bg="#0f141a", pady=4)
            row.pack(fill="x", anchor="w")

            indicator_text = "S" if user.get("talking") else "*"
            indicator_color = "#29d17f" if user.get("talking") else "#4b5a67"
            name_color = "#f3f6f8" if user.get("talking") else "#c3d0da"

            indicator = tk.Label(
                row,
                text=indicator_text,
                fg=indicator_color,
                bg="#0f141a",
                font=("Segoe UI", 14, "bold"),
                width=2,
            )
            indicator.pack(side="left")

            suffix = " (you)" if self.client and user_id == self.client.user_id else ""
            name = tk.Label(
                row,
                text=f"{user['username']}{suffix}",
                fg=name_color,
                bg="#0f141a",
                font=("Segoe UI", 12, "bold" if user.get("talking") else "normal"),
            )
            name.pack(side="left")

    def _append_message(self, username, message):
        self.feed.configure(state="normal")
        self.feed.insert(tk.END, f"{username}: {message}\n\n")
        self.feed.configure(state="disabled")
        self.feed.see(tk.END)

    def _append_image(self, username, filename, image_data):
        self.feed.configure(state="normal")
        self.feed.insert(tk.END, f"{username} shared {filename}\n")
        try:
            photo = tk.PhotoImage(data=image_data)
            self.image_refs.append(photo)
            self.feed.image_create(tk.END, image=photo)
            self.feed.insert(tk.END, "\n\n")
        except tk.TclError:
            self.feed.insert(tk.END, "[Image preview unavailable in this format]\n\n")
        self.feed.configure(state="disabled")
        self.feed.see(tk.END)

    def _on_close(self):
        if self.voice_client:
            self.voice_client.stop()
        if self.client:
            self.client.close()
        self.root.destroy()
