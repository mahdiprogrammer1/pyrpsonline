"""
سرور بازی سنگ-کاغذ-قیچی آنلاین
نحوه اجرا: python server.py
"""
import socket
import threading
import json
import os
import hashlib
import random
from datetime import datetime

HOST = '0.0.0.0'
PORT = 5555
USERS_FILE = 'users.json'

# ---------- مدیریت کاربران ----------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

users_db = load_users()

# ---------- مدیریت اتاق‌ها ----------
rooms = {}  # room_id -> {host, players, state, moves}
room_counter = 1
rooms_lock = threading.Lock()

# ---------- مدیریت کلاینت‌ها ----------
clients = {}  # socket -> {username, room}
clients_lock = threading.Lock()

def send_msg(conn, data):
    try:
        msg = json.dumps(data).encode('utf-8')
        conn.sendall(len(msg).to_bytes(4, 'big') + msg)
    except:
        pass

def recv_msg(conn):
    try:
        raw_len = conn.recv(4)
        if not raw_len or len(raw_len) < 4:
            return None
        length = int.from_bytes(raw_len, 'big')
        data = b''
        while len(data) < length:
            chunk = conn.recv(length - len(data))
            if not chunk:
                return None
            data += chunk
        return json.loads(data.decode('utf-8'))
    except:
        return None

def broadcast_to_room(room_id, data, exclude=None):
    with rooms_lock:
        if room_id not in rooms:
            return
        for p in rooms[room_id]['players']:
            if p['conn'] != exclude:
                send_msg(p['conn'], data)

def check_room_winner(room_id):
    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            return
        moves = room['moves']
        if len(moves) < len(room['players']):
            return  # هنوز همه انتخاب نکرده‌اند

        choices = list(moves.values())
        # اگر همه یک چیز انتخاب کرده باشند -> مساوی
        if len(set(choices)) == 1:
            result = {'winner': None, 'message': 'مساوی! همه یک انتخاب داشتند.'}
        else:
            # تعیین برنده (برای ۲ نفر)
            if len(room['players']) == 2:
                p1, p2 = list(moves.keys())
                c1, c2 = moves[p1], moves[p2]
                if c1 == c2:
                    result = {'winner': None, 'message': 'مساوی!'}
                elif (c1, c2) in [('rock','scissors'),('scissors','paper'),('paper','rock')]:
                    result = {'winner': p1, 'message': f'{p1} برنده شد!'}
                else:
                    result = {'winner': p2, 'message': f'{p2} برنده شد!'}
            else:
                result = {'winner': None, 'message': 'نتیجه در حالت چند نفره پیچیده است.'}

        room['moves'] = {}
        room['state'] = 'waiting'
        broadcast_to_room(room_id, {'type': 'round_result', **result, 'moves': moves})

def handle_client(conn, addr):
    username = None
    try:
        # حلقه احراز هویت
        while True:
            msg = recv_msg(conn)
            if not msg:
                return
            action = msg.get('action')

            if action == 'register':
                u, p = msg.get('username','').strip(), msg.get('password','')
                if not u or not p:
                    send_msg(conn, {'type':'auth_result','ok':False,'msg':'نام کاربری و رمز الزامی است.'})
                    continue
                if u in users_db:
                    send_msg(conn, {'type':'auth_result','ok':False,'msg':'این نام کاربری قبلاً ثبت شده.'})
                    continue
                users_db[u] = hash_password(p)
                save_users(users_db)
                send_msg(conn, {'type':'auth_result','ok':True,'msg':'ثبت‌نام موفق! اکنون وارد شوید.'})

            elif action == 'login':
                u, p = msg.get('username','').strip(), msg.get('password','')
                if u in users_db and users_db[u] == hash_password(p):
                    username = u
                    with clients_lock:
                        clients[conn] = {'username': u, 'room': None}
                    send_msg(conn, {'type':'auth_result','ok':True,'msg':f'خوش آمدید {u}!', 'username': u})
                    break
                else:
                    send_msg(conn, {'type':'auth_result','ok':False,'msg':'نام کاربری یا رمز اشتباه است.'})

        # حلقه لابی
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            action = msg.get('action')

            if action == 'list_rooms':
                with rooms_lock:
                    room_list = []
                    for rid, r in rooms.items():
                        room_list.append({
                            'id': rid,
                            'host': r['host'],
                            'players': len(r['players']),
                            'state': r['state']
                        })
                send_msg(conn, {'type':'rooms_list','rooms':room_list})

            elif action == 'create_room':
                global room_counter
                with rooms_lock:
                    rid = room_counter
                    room_counter += 1
                    rooms[rid] = {
                        'host': username,
                        'players': [{'conn': conn, 'username': username}],
                        'state': 'waiting',
                        'moves': {}
                    }
                    with clients_lock:
                        clients[conn]['room'] = rid
                send_msg(conn, {'type':'room_created','room_id': rid, 'host': username})
                broadcast_to_room(rid, {'type':'room_update','players':[p['username'] for p in rooms[rid]['players']]})

            elif action == 'join_room':
                rid = msg.get('room_id')
                with rooms_lock:
                    if rid not in rooms:
                        send_msg(conn, {'type':'error','msg':'اتاق یافت نشد.'})
                    elif rooms[rid]['state'] == 'playing':
                        send_msg(conn, {'type':'error','msg':'بازی در حال انجام است.'})
                    elif len(rooms[rid]['players']) >= 2:
                        send_msg(conn, {'type':'error','msg':'اتاق پر است (حداکثر ۲ نفر).'})
                    else:
                        rooms[rid]['players'].append({'conn': conn, 'username': username})
                        with clients_lock:
                            clients[conn]['room'] = rid
                        send_msg(conn, {'type':'room_joined','room_id': rid, 'host': rooms[rid]['host']})
                        broadcast_to_room(rid, {'type':'room_update','players':[p['username'] for p in rooms[rid]['players']]})

            elif action == 'start_game':
                with rooms_lock:
                    if rooms.get(conn_room := clients.get(conn,{}).get('room')):
                        r = rooms[conn_room]
                        if r['host'] != username:
                            send_msg(conn, {'type':'error','msg':'فقط میزبان می‌تواند بازی را شروع کند.'})
                        elif len(r['players']) < 2:
                            send_msg(conn, {'type':'error','msg':'حداقل ۲ نفر لازم است.'})
                        else:
                            r['state'] = 'playing'
                            r['moves'] = {}
                            broadcast_to_room(conn_room, {'type':'game_started'})

            elif action == 'play':
                choice = msg.get('choice')
                if choice not in ('rock','paper','scissors'):
                    send_msg(conn, {'type':'error','msg':'انتخاب نامعتبر.'})
                    continue
                with clients_lock:
                    rid = clients[conn].get('room')
                with rooms_lock:
                    if rid and rid in rooms:
                        rooms[rid]['moves'][username] = choice
                        send_msg(conn, {'type':'choice_ok','msg':'انتخاب شما ثبت شد. در انتظار حریف...'})
                        broadcast_to_room(rid, {'type':'player_ready','username': username}, exclude=conn)
                        check_room_winner(rid)

            elif action == 'leave_room':
                with clients_lock:
                    rid = clients[conn].get('room')
                if rid:
                    with rooms_lock:
                        if rid in rooms:
                            rooms[rid]['players'] = [p for p in rooms[rid]['players'] if p['conn'] != conn]
                            if not rooms[rid]['players']:
                                del rooms[rid]
                            else:
                                if rooms[rid]['host'] == username:
                                    rooms[rid]['host'] = rooms[rid]['players'][0]['username']
                                broadcast_to_room(rid, {'type':'player_left','username': username,
                                                         'players':[p['username'] for p in rooms[rid]['players']]})
                    with clients_lock:
                        clients[conn]['room'] = None
                    send_msg(conn, {'type':'left_room'})

            elif action == 'chat':
                with clients_lock:
                    rid = clients[conn].get('room')
                if rid:
                    broadcast_to_room(rid, {'type':'chat','from':username,'msg':msg.get('msg','')})

    except Exception as e:
        print(f"خطا: {e}")
    finally:
        # پاکسازی
        with clients_lock:
            rid = clients.get(conn, {}).get('room')
            if rid:
                with rooms_lock:
                    if rid in rooms:
                        rooms[rid]['players'] = [p for p in rooms[rid]['players'] if p['conn'] != conn]
                        if not rooms[rid]['players']:
                            del rooms[rid]
                        else:
                            broadcast_to_room(rid, {'type':'player_left','username':username,
                                                     'players':[p['username'] for p in rooms[rid]['players']]})
            clients.pop(conn, None)
        try: conn.close()
        except: pass
        print(f"[-] اتصال قطع شد: {addr} | کاربر: {username}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print("="*50)
    print("🎮 سرور بازی سنگ-کاغذ-قیچی آنلاین")
    print("="*50)
    print(f"✅ سرور در حال اجرا روی {HOST}:{PORT}")
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        print(f"📡 آی‌پی محلی برای اشتراک‌گذاری: {local_ip}:{PORT}")
    except:
        pass
    print("در انتظار اتصال کلاینت‌ها...")
    print("="*50)
    while True:
        conn, addr = server.accept()
        print(f"[+] اتصال جدید: {addr}")
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    start_server()