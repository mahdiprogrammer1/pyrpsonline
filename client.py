"""
کلاینت بازی سنگ-کاغذ-قیچی آنلاین (رابط گرافیکی)
نحوه اجرا: python client.py
پیش‌نیاز: pip install pillow (اختیاری - اگر نبود، بدون تصویر اجرا می‌شود)
"""
import socket
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

HOST = '127.0.0.1'  # پیش‌فرض؛ در GUI قابل تغییر است
PORT = 5555

class RPSClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎮 سنگ-کاغذ-قیچی آنلاین")
        self.root.geometry("600x500")
        self.root.configure(bg="#2c3e50")
        self.conn = None
        self.username = None
        self.current_room = None
        self.is_host = False

        self.show_connect_screen()
        self.root.mainloop()

    # ---------- صفحه اتصال ----------
    def show_connect_screen(self):
        self.clear()
        frame = tk.Frame(self.root, bg="#2c3e50")
        frame.pack(expand=True)

        tk.Label(frame, text="🎮 سنگ-کاغذ-قیچی آنلاین",
                 font=("Tahoma", 20, "bold"), bg="#2c3e50", fg="#ecf0f1").pack(pady=20)

        tk.Label(frame, text="آی‌پی سرور:", bg="#2c3e50", fg="#ecf0f1",
                 font=("Tahoma", 11)).pack()
        self.ip_entry = tk.Entry(frame, font=("Tahoma", 12), width=25)
        self.ip_entry.insert(0, HOST)
        self.ip_entry.pack(pady=5)

        tk.Label(frame, text="پورت:", bg="#2c3e50", fg="#ecf0f1",
                 font=("Tahoma", 11)).pack()
        self.port_entry = tk.Entry(frame, font=("Tahoma", 12), width=25)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.pack(pady=5)

        tk.Button(frame, text="اتصال به سرور", font=("Tahoma", 12, "bold"),
                  bg="#27ae60", fg="white", width=20,
                  command=self.connect_to_server).pack(pady=20)

    def connect_to_server(self):
        host = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except:
            messagebox.showerror("خطا", "پورت نامعتبر است.")
            return
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((host, port))
            threading.Thread(target=self.listen_loop, daemon=True).start()
            self.show_auth_screen()
        except Exception as e:
            messagebox.showerror("خطای اتصال", f"امکان اتصال به سرور:\n{e}")

    # ---------- صفحه ورود/ثبت‌نام ----------
    def show_auth_screen(self):
        self.clear()
        frame = tk.Frame(self.root, bg="#2c3e50")
        frame.pack(expand=True)

        tk.Label(frame, text="ورود / ثبت‌نام", font=("Tahoma", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=15)

        tk.Label(frame, text="نام کاربری:", bg="#2c3e50", fg="#ecf0f1",
                 font=("Tahoma", 11)).pack()
        self.user_entry = tk.Entry(frame, font=("Tahoma", 12), width=25)
        self.user_entry.pack(pady=5)

        tk.Label(frame, text="رمز عبور:", bg="#2c3e50", fg="#ecf0f1",
                 font=("Tahoma", 11)).pack()
        self.pass_entry = tk.Entry(frame, font=("Tahoma", 12), width=25, show="*")
        self.pass_entry.pack(pady=5)

        self.auth_status = tk.Label(frame, text="", bg="#2c3e50", fg="#f1c40f",
                                    font=("Tahoma", 10))
        self.auth_status.pack(pady=5)

        btn_frame = tk.Frame(frame, bg="#2c3e50")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="ورود", font=("Tahoma", 11, "bold"),
                  bg="#3498db", fg="white", width=12,
                  command=lambda: self.send_auth('login')).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="ثبت‌نام", font=("Tahoma", 11, "bold"),
                  bg="#9b59b6", fg="white", width=12,
                  command=lambda: self.send_auth('register')).grid(row=0, column=1, padx=5)

    def send_auth(self, action):
        u = self.user_entry.get().strip()
        p = self.pass_entry.get().strip()
        if not u or not p:
            self.auth_status.config(text="نام کاربری و رمز الزامی است.", fg="#e74c3c")
            return
        self.send({'action': action, 'username': u, 'password': p})

    # ---------- لابی ----------
    def show_lobby(self):
        self.clear()
        top = tk.Frame(self.root, bg="#2c3e50")
        top.pack(fill='x', pady=5)
        tk.Label(top, text=f"👤 {self.username}", font=("Tahoma", 12, "bold"),
                 bg="#2c3e50", fg="#2ecc71").pack(side='left', padx=10)
        tk.Button(top, text="خروج", bg="#e74c3c", fg="white",
                  command=self.disconnect).pack(side='right', padx=10)

        tk.Label(self.root, text="🏠 لابی", font=("Tahoma", 16, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=10)

        # ساخت اتاق
        create_frame = tk.Frame(self.root, bg="#2c3e50")
        create_frame.pack(pady=5)
        tk.Button(create_frame, text="➕ ساخت اتاق جدید",
                  font=("Tahoma", 11, "bold"), bg="#27ae60", fg="white",
                  command=lambda: self.send({'action':'create_room'})).pack()

        # پیوستن به اتاق
        join_frame = tk.Frame(self.root, bg="#2c3e50")
        join_frame.pack(pady=5)
        tk.Label(join_frame, text="شماره اتاق:", bg="#2c3e50", fg="#ecf0f1",
                 font=("Tahoma", 10)).pack(side='left')
        self.room_id_entry = tk.Entry(join_frame, font=("Tahoma", 11), width=8)
        self.room_id_entry.pack(side='left', padx=5)
        tk.Button(join_frame, text="پیوستن", bg="#3498db", fg="white",
                  command=self.join_room).pack(side='left')

        # لیست اتاق‌ها
        tk.Button(self.root, text="🔄 بروزرسانی لیست اتاق‌ها",
                  bg="#f39c12", fg="white",
                  command=lambda: self.send({'action':'list_rooms'})).pack(pady=5)

        self.rooms_listbox = tk.Listbox(self.root, font=("Tahoma", 11),
                                        height=10, width=60, bg="#34495e", fg="#ecf0f1")
        self.rooms_listbox.pack(pady=5)

        self.lobby_status = tk.Label(self.root, text="", bg="#2c3e50", fg="#f1c40f",
                                     font=("Tahoma", 10))
        self.lobby_status.pack(pady=5)

        # دریافت اولیه لیست
        self.send({'action':'list_rooms'})

    def join_room(self):
        try:
            rid = int(self.room_id_entry.get().strip())
            self.send({'action':'join_room','room_id':rid})
        except:
            self.lobby_status.config(text="شماره اتاق نامعتبر.", fg="#e74c3c")

    # ---------- اتاق ----------
    def show_room(self, room_id, host):
        self.current_room = room_id
        self.is_host = (host == self.username)
        self.clear()

        top = tk.Frame(self.root, bg="#2c3e50")
        top.pack(fill='x', pady=5)
        tk.Label(top, text=f"👤 {self.username}", font=("Tahoma", 12, "bold"),
                 bg="#2c3e50", fg="#2ecc71").pack(side='left', padx=10)

        info = f"🏠 اتاق #{room_id}"
        if self.is_host:
            info += " (میزبان)"
        tk.Label(top, text=info, font=("Tahoma", 12, "bold"),
                 bg="#2c3e50", fg="#f1c40f").pack(side='left', padx=10)

        tk.Button(top, text="🚪 ترک اتاق", bg="#e74c3c", fg="white",
                  command=self.leave_room).pack(side='right', padx=10)

        # نمایش آی‌پی برای اشتراک‌گذاری
        ip_frame = tk.Frame(self.root, bg="#2c3e50")
        ip_frame.pack(pady=5)
        tk.Label(ip_frame, text="📡 آدرس برای اشتراک‌گذاری با دوستان:",
                 bg="#2c3e50", fg="#ecf0f1", font=("Tahoma", 10)).pack()
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            share_text = f"IP: {local_ip} | Port: {PORT} | Room: #{room_id}"
        except:
            share_text = f"Port: {PORT} | Room: #{room_id}"
        tk.Label(ip_frame, text=share_text, bg="#1abc9c", fg="white",
                 font=("Consolas", 11, "bold"), padx=10, pady=5).pack(pady=3)

        # لیست بازیکنان
        tk.Label(self.root, text="👥 بازیکنان:", bg="#2c3e50", fg="#ecf0f1",
                 font=("Tahoma", 11, "bold")).pack(pady=5)
        self.players_listbox = tk.Listbox(self.root, font=("Tahoma", 11),
                                          height=4, width=40, bg="#34495e", fg="#ecf0f1")
        self.players_listbox.pack()

        # دکمه شروع (فقط میزبان)
        if self.is_host:
            tk.Button(self.root, text="▶️ شروع بازی",
                      font=("Tahoma", 12, "bold"), bg="#27ae60", fg="white",
                      command=lambda: self.send({'action':'start_game'})).pack(pady=10)

        # ناحیه بازی
        self.game_frame = tk.Frame(self.root, bg="#2c3e50")
        self.game_frame.pack(pady=10)
        self.game_status = tk.Label(self.game_frame, text="در انتظار شروع بازی...",
                                    bg="#2c3e50", fg="#f1c40f", font=("Tahoma", 11))
        self.game_status.pack()

        # چت
        chat_frame = tk.Frame(self.root, bg="#2c3e50")
        chat_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.chat_box = tk.Text(chat_frame, height=6, bg="#34495e", fg="#ecf0f1",
                                font=("Tahoma", 10), state='disabled')
        self.chat_box.pack(fill='both', expand=True)
        chat_input = tk.Frame(chat_frame, bg="#2c3e50")
        chat_input.pack(fill='x')
        self.chat_entry = tk.Entry(chat_input, font=("Tahoma", 11))
        self.chat_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        tk.Button(chat_input, text="ارسال", bg="#3498db", fg="white",
                  command=self.send_chat).pack(side='right')

    def show_game_choices(self):
        for w in self.game_frame.winfo_children():
            w.destroy()
        tk.Label(self.game_frame, text="انتخاب کن:",
                 bg="#2c3e50", fg="#ecf0f1", font=("Tahoma", 12, "bold")).pack()
        btn_frame = tk.Frame(self.game_frame, bg="#2c3e50")
        btn_frame.pack(pady=10)
        choices = [('🪨 سنگ','rock'), ('📄 کاغذ','paper'), ('✂️ قیچی','scissors')]
        for text, val in choices:
            tk.Button(btn_frame, text=text, font=("Tahoma", 14, "bold"),
                      bg="#e67e22", fg="white", width=10, height=2,
                      command=lambda v=val: self.send({'action':'play','choice':v})
                      ).pack(side='left', padx=5)
        self.game_status.config(text="نوبت شماست!", fg="#2ecc71")

    def leave_room(self):
        self.send({'action':'leave_room'})
        self.current_room = None
        self.show_lobby()

    def send_chat(self):
        msg = self.chat_entry.get().strip()
        if msg:
            self.send({'action':'chat','msg':msg})
            self.chat_entry.delete(0, 'end')

    def append_chat(self, text):
        self.chat_box.config(state='normal')
        self.chat_box.insert('end', text + '\n')
        self.chat_box.see('end')
        self.chat_box.config(state='disabled')

    # ---------- ابزارها ----------
    def send(self, data):
        try:
            msg = json.dumps(data).encode('utf-8')
            self.conn.sendall(len(msg).to_bytes(4, 'big') + msg)
        except Exception as e:
            messagebox.showerror("خطا", f"ارسال ناموفق: {e}")

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def disconnect(self):
        try:
            if self.current_room:
                self.send({'action':'leave_room'})
            self.conn.close()
        except: pass
        self.root.destroy()

    # ---------- حلقه دریافت پیام ----------
    def listen_loop(self):
        while True:
            try:
                raw_len = self.conn.recv(4)
                if not raw_len or len(raw_len) < 4:
                    break
                length = int.from_bytes(raw_len, 'big')
                data = b''
                while len(data) < length:
                    chunk = self.conn.recv(length - len(data))
                    if not chunk:
                        break
                    data += chunk
                msg = json.loads(data.decode('utf-8'))
                self.root.after(0, self.handle_msg, msg)
            except:
                break
        self.root.after(0, self.on_disconnect)

    def handle_msg(self, msg):
        t = msg.get('type')

        if t == 'auth_result':
            if hasattr(self, 'auth_status'):
                self.auth_status.config(text=msg.get('msg',''))
                self.auth_status.config(fg="#2ecc71" if msg.get('ok') else "#e74c3c")
            if msg.get('ok') and msg.get('username'):
                self.username = msg['username']
                self.show_lobby()

        elif t == 'rooms_list':
            if hasattr(self, 'rooms_listbox'):
                self.rooms_listbox.delete(0, 'end')
                rooms = msg.get('rooms', [])
                if not rooms:
                    self.rooms_listbox.insert('end', "هیچ اتاقی موجود نیست.")
                for r in rooms:
                    self.rooms_listbox.insert('end',
                        f"#{r['id']} | میزبان: {r['host']} | بازیکنان: {r['players']} | وضعیت: {r['state']}")

        elif t == 'room_created':
            rid = msg.get('room_id')
            self.lobby_status.config(text=f"✅ اتاق #{rid} ساخته شد!", fg="#2ecc71")
            self.show_room(rid, msg.get('host'))

        elif t == 'room_joined':
            self.show_room(msg.get('room_id'), msg.get('host'))

        elif t == 'room_update':
            if hasattr(self, 'players_listbox'):
                self.players_listbox.delete(0, 'end')
                for p in msg.get('players', []):
                    self.players_listbox.insert('end', p)

        elif t == 'game_started':
            self.show_game_choices()

        elif t == 'choice_ok':
            self.game_status.config(text="✅ انتخاب ثبت شد. در انتظار حریف...", fg="#f1c40f")
            for w in self.game_frame.winfo_children():
                if isinstance(w, tk.Frame):
                    for b in w.winfo_children():
                        if isinstance(b, tk.Button):
                            b.config(state='disabled')

        elif t == 'round_result':
            winner = msg.get('winner')
            moves = msg.get('moves', {})
            result_text = f"\n🎯 نتیجه: {msg.get('message')}\n"
            for p, c in moves.items():
                emoji = {'rock':'🪨','paper':'📄','scissors':'✂️'}.get(c,c)
                result_text += f"  {p}: {emoji}\n"
            self.append_chat(result_text)
            self.show_game_choices()

        elif t == 'player_ready':
            self.append_chat(f"⏳ {msg.get('username')} انتخاب کرد.")

        elif t == 'player_left':
            self.append_chat(f"🚪 {msg.get('username')} اتاق را ترک کرد.")
            if hasattr(self, 'players_listbox'):
                self.players_listbox.delete(0, 'end')
                for p in msg.get('players', []):
                    self.players_listbox.insert('end', p)

        elif t == 'chat':
            if hasattr(self, 'chat_box'):
                self.append_chat(f"[{msg.get('from')}]: {msg.get('msg')}")

        elif t == 'left_room':
            pass

        elif t == 'error':
            if hasattr(self, 'lobby_status'):
                self.lobby_status.config(text=msg.get('msg',''), fg="#e74c3c")
            elif hasattr(self, 'game_status'):
                self.game_status.config(text=msg.get('msg',''), fg="#e74c3c")

    def on_disconnect(self):
        messagebox.showinfo("اتصال قطع شد", "ارتباط با سرور قطع شد.")
        self.root.destroy()

if __name__ == '__main__':
    RPSClient()