import tkinter as tk
from tkinter import filedialog
import ctypes
import sys
import subprocess
import os
import json
import uuid
import re

# --- 1. Windows DPI Awareness ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- 2. Professional Embedded Icon ---
ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABmJLR0QA/wD/AP+gvaeTAAAACXBI"
    "WXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH6AMXDA0YAK97SgAAAbpJREFUWMPNl79LW0Ecxz9X06YI"
    "SmsDbe0kiYOTu8XByV26OnToX9DBv6GTo6OTo0MnJ0fBv6BDR8XNwcFJkiYIraZp6uDYp9PhvveS"
    "m8S8996DR76X7+f7vXw/388lSRL+p9YmNoGtwAnQDmSAbWAZ6Is6S8AdUAYuAncB5+8M4p/m/gBe"
    "At96vU8D80A76m0Bq/8YpIByUvAauO+N8zGvA8X4Y2+8An72nC8C7/Y+oIAn8D76XvXq3gIK6C2g"
    "HPCt7tW9BfQAByY0ZkJjInNizMTmXGjMps6JyZzInBgzsTkbGrOxM6L1mYmNmdCYyZ0RUyc0ZkJj"
    "InNizMTmXGjMps6JyZzInBgzsTkbGrOxM6L1mYmNmdCYyZ0RUye0fL14Hw3yPrAasfX7X9U76NUK"
    "YCHuLfcU8KbnvAL86X7N+8C77p1fAsvAx71jZ+C7vQ+ox/yT3p9PAsvAbW8clIDv9f48AnYAn9fT"
    "OAn8mXfSAtYAn9vHAm6B8/Vn7gK4B66B6/VnGqB18Wf8iZ93Xn8R+A68GzB/BbwC3scXv4ivf7XW"
    "uX6yD8AIsA6MApPAPDAW9S7/Vf8BqDk9383KPlIAAAAASUVORK5CYII="
)

CHROMA_KEY = "#010101"

# --- 3. Path & Config Management ---
APP_DIR = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'StickyCounter')
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(APP_DIR, 'config.json')

def load_global_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {}

global_config = load_global_config()

SAVE_DIR = global_config.get('save_dir', os.path.join(APP_DIR, 'notes'))
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR, exist_ok=True)

BG_ALPHA = global_config.get('bg_alpha', 0.90)
CONTENT_ALPHA = global_config.get('content_alpha', 1.0)
DESC_FONT_SIZE = global_config.get('desc_font_size', 12)
VAL_FONT_SIZE = global_config.get('val_font_size', 48)

# Native Windows Icon Codes (Segoe MDL2 Assets)
ICO_ADD_WIN = "\uE8A7" # Copy/New Window
ICO_PLUS = "\uE710"    # Plus
ICO_MINUS = "\uE738"   # Minus
ICO_PIN = "\uE718"     # Pin
ICO_CLOSE = "\uE8BB"   # Close (X)
ICO_TRASH = "\uE74D"   # Trash
ICO_SETTINGS = "\uE713"# Gear
ICO_DRAG = "\uE700"    # Hamburger/Drag
ICO_GHOST = "\uE890"   # Transparency toggle

# --- 4. Master Launch Logic ---
if len(sys.argv) == 1:
    existing_notes = [f for f in os.listdir(SAVE_DIR) if f.startswith('note_') and f.endswith('.json')]
    if existing_notes:
        existing_notes.sort()
        my_note_id = existing_notes[0].replace('.json', '')
        for note_file in existing_notes[1:]:
            nid = note_file.replace('.json', '')
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, nid])
            else:
                subprocess.Popen([sys.executable, os.path.abspath(__file__), nid])
    else:
        my_note_id = f"note_{uuid.uuid4().hex[:8]}"
else:
    my_note_id = sys.argv[1]

# --- 5. Save / Load Logic ---
save_job = None
counters = []

def schedule_save(*args):
    global save_job
    if save_job:
        window.after_cancel(save_job)
    save_job = window.after(500, save_data)

def save_data():
    path = os.path.join(SAVE_DIR, f"{my_note_id}.json")
    data = {
        'items': [{'desc': c['desc_var'].get(), 'val': c['val_var'].get()} for c in counters],
        'x': window.winfo_x(),
        'y': window.winfo_y(),
        'pinned': window.attributes('-topmost')
    }
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def modify_number(var, match_index, amount):
    text = var.get()
    matches = list(re.finditer(r'-?\d+', text))
    if match_index < len(matches):
        m = matches[match_index]
        old_val = int(m.group())
        new_val = old_val + amount
        new_text = text[:m.start()] + str(new_val) + text[m.end():]
        var.set(new_text)
    elif len(matches) == 0:
        var.set(str(amount))

def create_accessible_button(parent, text, command, color="#aaaaaa"):
    btn = tk.Button(
        parent, 
        text=text, 
        bg=CHROMA_KEY, 
        fg=color, 
        bd=0, 
        activebackground="#333333", 
        activeforeground="white", 
        font=("Segoe UI", 18, "bold"),
        cursor="hand2", 
        padx=10, 
        pady=5,
        command=command
    )
    return btn

def update_buttons(c):
    if 'btn_frame' not in c:
        return
        
    # Hide incrementers if in minimal/readonly mode (BG_ALPHA near 0)
    if global_config.get('bg_alpha', 0.90) <= 0.01:
        for widget in c['btn_frame'].winfo_children():
            widget.destroy()
        c['btn_frame'].num_buttons = 0
        return

    text = c['val_var'].get()
    matches = list(re.finditer(r'-?\d+', text))
    num_matches = len(matches) if len(matches) > 0 else 1
    
    if getattr(c['btn_frame'], 'num_buttons', -1) == num_matches:
        return
        
    for widget in c['btn_frame'].winfo_children():
        widget.destroy()
        
    c['btn_frame'].num_buttons = num_matches
    
    if len(matches) == 0:
        f = tk.Frame(c['btn_frame'], bg=CHROMA_KEY)
        f.pack(side=tk.LEFT, padx=15)
        create_accessible_button(f, "−", lambda: modify_number(c['val_var'], 0, -1)).pack(side=tk.LEFT, padx=2)
        create_accessible_button(f, "＋", lambda: modify_number(c['val_var'], 0, 1)).pack(side=tk.LEFT, padx=2)
    else:
        for i in range(num_matches):
            f = tk.Frame(c['btn_frame'], bg=CHROMA_KEY)
            f.pack(side=tk.LEFT, padx=15)
            create_accessible_button(f, "−", lambda idx=i: modify_number(c['val_var'], idx, -1)).pack(side=tk.LEFT, padx=2)
            create_accessible_button(f, "＋", lambda idx=i: modify_number(c['val_var'], idx, 1)).pack(side=tk.LEFT, padx=2)

    try:
        window.update_idletasks()
        bg_window.geometry(f"{window.winfo_width()}x{window.winfo_height()}+{window.winfo_x()}+{window.winfo_y()}")
    except NameError:
        pass

def on_text_change(*args):
    schedule_save()
    for c in counters:
        c['desc_entry'].config(width=max(8, len(c['desc_var'].get())))
        c['val_entry'].config(width=max(2, len(c['val_var'].get())))
        update_buttons(c)

def poll_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
                new_bg_alpha = config.get('bg_alpha', 0.90)
                is_minimal = new_bg_alpha <= 0.01
                
                if abs(new_bg_alpha - bg_window.attributes('-alpha')) > 0.001:
                    bg_window.attributes('-alpha', new_bg_alpha)
                    global_config['bg_alpha'] = new_bg_alpha
                    # Refresh all buttons to reflect minimal mode change
                    for c in counters: update_buttons(c)
                
                # --- Header Visibility Logic ---
                if is_minimal:
                    add_win_btn.pack_forget()
                    add_row_btn.pack_forget()
                    rem_row_btn.pack_forget()
                    pin_btn.pack_forget()
                    if not drag_btn.winfo_ismapped():
                        drag_btn.pack(side=tk.RIGHT)
                else:
                    drag_btn.pack_forget()
                    add_win_btn.pack(side=tk.LEFT)
                    add_row_btn.pack(side=tk.LEFT)
                    rem_row_btn.pack(side=tk.LEFT)
                    pin_btn.pack(side=tk.LEFT)
                
                new_content_alpha = config.get('content_alpha', 1.0)
                if abs(new_content_alpha - window.attributes('-alpha')) > 0.01:
                    window.attributes('-alpha', new_content_alpha)
                    global_config['content_alpha'] = new_content_alpha
                
                new_desc_size = config.get('desc_font_size', 12)
                if new_desc_size != global_config.get('desc_font_size', 12):
                    for c in counters:
                        c['desc_entry'].config(font=("Segoe UI", new_desc_size))
                    global_config['desc_font_size'] = new_desc_size
                
                new_val_size = config.get('val_font_size', 48)
                if new_val_size != global_config.get('val_font_size', 48):
                    for c in counters:
                        c['val_entry'].config(font=("Segoe UI", new_val_size, "bold"))
                    global_config['val_font_size'] = new_val_size
    except: pass

    # Update Close vs Trash Icon
    try:
        note_files = [f for f in os.listdir(SAVE_DIR) if f.startswith('note_') and f.endswith('.json')]
        if len(note_files) > 1:
            if close_btn.cget('text') != ICO_TRASH:
                close_btn.config(text=ICO_TRASH, command=delete_note, fg="#f44336")
        else:
            if close_btn.cget('text') != ICO_CLOSE:
                close_btn.config(text=ICO_CLOSE, command=close_app, fg="#f44336")
    except: pass

    window.after(1000, poll_config)

# --- 6. Taskbar & OS Management ---
def update_taskbar_presence():
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x00000080 
        style = style | 0x00040000  
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027) 
    except: pass

def show_in_taskbar():
    update_taskbar_presence()
    window.wm_withdraw()
    window.after(10, window.wm_deiconify)

# --- 7. App Controls & Dragging ---
def on_configure(event):
    if event.widget == window:
        schedule_save()
        try:
            bg_window.geometry(f"{window.winfo_width()}x{window.winfo_height()}+{window.winfo_x()}+{window.winfo_y()}")
        except: pass

def start_move(event):
    window.lift() 
    window._x = event.x
    window._y = event.y

def do_move(event):
    x = window.winfo_x() + (event.x - window._x)
    y = window.winfo_y() + (event.y - window._y)
    window.geometry(f"+{x}+{y}")
    bg_window.geometry(f"+{x}+{y}")

def handle_bg_click(event):
    rx, ry = event.x_root, event.y_root
    def check_widgets(parent):
        for child in parent.winfo_children():
            if child.winfo_viewable():
                bx = child.winfo_rootx()
                by = child.winfo_rooty()
                bw = child.winfo_width()
                bh = child.winfo_height()
                if bx <= rx <= bx + bw and by <= ry <= by + bh:
                    if isinstance(child, tk.Button):
                        orig_bg = child.cget("bg")
                        child.config(bg="#333333")
                        child.update_idletasks()
                        def trigger(c=child, obg=orig_bg):
                            try:
                                if c.winfo_exists():
                                    c.config(bg=obg)
                                    c.invoke()
                            except: pass
                        window.after(100, trigger)
                        return True
                    elif isinstance(child, tk.Entry):
                        child.focus_set()
                        child.icursor(tk.END)
                        return True
            if check_widgets(child): return True
        return False
    if not check_widgets(window): start_move(event)

def handle_bg_motion(event):
    rx, ry = event.x_root, event.y_root
    def check_widgets(parent):
        for child in parent.winfo_children():
            if child.winfo_viewable():
                bx = child.winfo_rootx()
                by = child.winfo_rooty()
                bw = child.winfo_width()
                bh = child.winfo_height()
                if bx <= rx <= bx + bw and by <= ry <= by + bh:
                    if isinstance(child, tk.Button): return "hand2"
                    elif isinstance(child, tk.Entry): return "xterm"
            res = check_widgets(child)
            if res: return res
        return ""
    cursor = check_widgets(window)
    bg_window.config(cursor=cursor)

def toggle_pin():
    is_pinned = window.attributes('-topmost')
    window.attributes('-topmost', not is_pinned)
    bg_window.attributes('-topmost', not is_pinned)
    if not is_pinned: 
        bg_window.lift()
        window.lift()
    pin_btn.config(fg="#4CAF50" if not is_pinned else "#555555")
    schedule_save()
    window.after(10, update_taskbar_presence)

def toggle_opacity_mode():
    """Toggles between 0 (Minimal) and 0.25 opacity"""
    current = global_config.get('bg_alpha', 0.90)
    new_alpha = 0.25 if current <= 0.01 else 0.0
    global_config['bg_alpha'] = new_alpha
    bg_window.attributes('-alpha', new_alpha)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(global_config, f)
    # Trigger refresh
    for c in counters: update_buttons(c)
    poll_config()

def duplicate_app():
    new_id = f"note_{uuid.uuid4().hex[:8]}"
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, new_id])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), new_id])

def handle_map_and_focus(event):
    if event.widget == window:
        window.overrideredirect(True)
        bg_window.deiconify()
        bg_window.lift()
        window.lift()
        window.after(10, update_taskbar_presence)

def close_app():
    save_data()
    window.destroy()

def delete_note():
    path = os.path.join(SAVE_DIR, f"{my_note_id}.json")
    try:
        if os.path.exists(path):
            os.remove(path)
    except: pass
    window.destroy()

# --- 8. Row Management ---
def add_row(desc_val="Tracker...", val_val="0"):
    row_frame = tk.Frame(app_frame, bg=CHROMA_KEY, highlightthickness=0, bd=0)
    row_frame.pack(fill=tk.BOTH, expand=True, pady=0)
    
    row_frame.bind("<ButtonPress-1>", start_move)
    row_frame.bind("<B1-Motion>", do_move)
    
    desc_var = tk.StringVar(value=desc_val)
    desc_var.trace_add("write", on_text_change)
    
    desc_entry = tk.Entry(row_frame, textvariable=desc_var, font=("Segoe UI", global_config.get('desc_font_size', 12)), bg=CHROMA_KEY, fg="#aaaaaa", bd=0, highlightthickness=0, justify="center", insertbackground="white")
    desc_entry.pack(pady=0, fill=tk.X, padx=10)
    
    val_var = tk.StringVar(value=val_val)
    val_var.trace_add("write", on_text_change)
    
    val_entry = tk.Entry(row_frame, textvariable=val_var, font=("Segoe UI", global_config.get('val_font_size', 48), "bold"), bg=CHROMA_KEY, fg="#ffffff", bd=0, highlightthickness=0, justify="center", insertbackground="white")
    val_entry.pack(expand=True, fill=tk.BOTH, pady=0)
    
    btn_frame = tk.Frame(row_frame, bg=CHROMA_KEY, highlightthickness=0, bd=0)
    btn_frame.pack(pady=0)
    
    counters.append({
        'desc_var': desc_var,
        'val_var': val_var,
        'frame': row_frame,
        'desc_entry': desc_entry,
        'val_entry': val_entry,
        'btn_frame': btn_frame
    })
    
    on_text_change()
    window.update_idletasks()
    try:
        bg_window.geometry(f"{window.winfo_width()}x{window.winfo_height()}+{window.winfo_x()}+{window.winfo_y()}")
    except: pass

def remove_row():
    if len(counters) > 1:
        c = counters.pop()
        c['frame'].destroy()
        schedule_save()
        window.update_idletasks()
        try:
            bg_window.geometry(f"{window.winfo_width()}x{window.winfo_height()}+{window.winfo_x()}+{window.winfo_y()}")
        except: pass

def load_data():
    path = os.path.join(SAVE_DIR, f"{my_note_id}.json")
    loaded_items = []
    
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                if 'items' in data:
                    loaded_items = data['items']
                else:
                    loaded_items = [{'desc': data.get('desc', 'Tracker...'), 'val': data.get('val', '0')}]
                
                x = data.get('x', 100)
                y = data.get('y', 100)
                window.geometry(f"+{x}+{y}")
                bg_window.geometry(f"+{x}+{y}")
                
                is_pinned = data.get('pinned', True)
                window.attributes('-topmost', is_pinned)
                bg_window.attributes('-topmost', is_pinned)
                pin_btn.config(fg="#4CAF50" if is_pinned else "#555555")
        except: pass
        
    if not loaded_items:
        loaded_items = [{'desc': 'Tracker...', 'val': '0'}]
        
    for item in loaded_items:
        add_row(item.get('desc', 'Tracker...'), item.get('val', '0'))
    save_data()

settings_win = None

def open_settings():
    global settings_win, global_config, SAVE_DIR
    if settings_win is not None and settings_win.winfo_exists():
        settings_win.lift()
        settings_win.focus_set()
        return

    settings_win = tk.Toplevel(window)
    settings_win.title("Settings")
    settings_win.geometry("460x650") 
    settings_win.config(bg="#2b2b2b")
    settings_win.attributes('-topmost', True)

    tk.Label(settings_win, text="Save Data Path:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(20, 0))
    path_var = tk.StringVar(value=SAVE_DIR)
    tk.Entry(settings_win, textvariable=path_var, font=("Segoe UI", 9), width=45, state='readonly').pack(pady=5)

    def browse_dir():
        global SAVE_DIR
        new_dir = filedialog.askdirectory(parent=settings_win, initialdir=SAVE_DIR)
        if new_dir:
            path_var.set(new_dir)
            global_config['save_dir'] = new_dir
            with open(CONFIG_FILE, 'w') as f:
                json.dump(global_config, f)
            for file in os.listdir(SAVE_DIR):
                if file.startswith('note_') and file.endswith('.json'):
                    os.rename(os.path.join(SAVE_DIR, file), os.path.join(new_dir, file))
            SAVE_DIR = new_dir

    tk.Button(settings_win, text="Browse & Move Files", command=browse_dir, bg="#2196F3", fg="white", relief="flat", padx=15, pady=8).pack(pady=10)

    # --- Sliders for Visuals ---
    def add_setting_slider(label, from_, to_, init_val, cmd, save_cmd, resolution=1):
        tk.Label(settings_win, text=label, bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(15, 0))
        var = tk.DoubleVar(value=init_val)
        slider = tk.Scale(settings_win, from_=from_, to_=to_, resolution=resolution, orient=tk.HORIZONTAL, 
                          variable=var, command=cmd, bg="#2b2b2b", fg="white", 
                          highlightthickness=0, bd=0, length=350)
        slider.bind("<ButtonRelease-1>", save_cmd)
        slider.pack(pady=5)
        return var

    add_setting_slider("Background Transparency (0 = Hidden):", 0.0, 1.0, global_config.get('bg_alpha', 0.90), 
                       lambda v: bg_window.attributes('-alpha', float(v)), 
                       lambda e: global_config.update({'bg_alpha': float(e.widget.get())}) or json.dump(global_config, open(CONFIG_FILE, 'w')), 0.01)

    add_setting_slider("Content Transparency:", 0.1, 1.0, global_config.get('content_alpha', 1.0), 
                       lambda v: window.attributes('-alpha', float(v)), 
                       lambda e: global_config.update({'content_alpha': float(e.widget.get())}) or json.dump(global_config, open(CONFIG_FILE, 'w')), 0.01)

    add_setting_slider("Title Font Size:", 8, 48, global_config.get('desc_font_size', 12), 
                       lambda v: [c['desc_entry'].config(font=("Segoe UI", int(v))) for c in counters], 
                       lambda e: global_config.update({'desc_font_size': int(e.widget.get())}) or json.dump(global_config, open(CONFIG_FILE, 'w')))

    add_setting_slider("Counter Font Size:", 16, 120, global_config.get('val_font_size', 48), 
                       lambda v: [c['val_entry'].config(font=("Segoe UI", int(v), "bold")) for c in counters], 
                       lambda e: global_config.update({'val_font_size': int(e.widget.get())}) or json.dump(global_config, open(CONFIG_FILE, 'w')))


# --- 9. Main Window Setup ---
window = tk.Tk()

try:
    app_icon = tk.PhotoImage(data=ICON_BASE64)
    window.iconphoto(True, app_icon)
except: pass

window.geometry("+100+100") 
window.overrideredirect(True) 
window.attributes('-topmost', True)
window.attributes('-alpha', CONTENT_ALPHA) 
window.attributes('-transparentcolor', CHROMA_KEY) 
window.config(bg=CHROMA_KEY)

bg_window = tk.Toplevel(window)
bg_window.geometry("+100+100")
bg_window.overrideredirect(True)
bg_window.attributes('-topmost', True)
bg_window.attributes('-alpha', BG_ALPHA)
bg_window.config(bg="#1e1e1e")

window.after(10, show_in_taskbar)
window.after(1000, poll_config)

window.bind('<Configure>', on_configure)
window.bind('<Map>', handle_map_and_focus)     
window.bind('<FocusIn>', handle_map_and_focus) 

bg_window.bind("<ButtonPress-1>", handle_bg_click)
bg_window.bind("<Motion>", handle_bg_motion)
bg_window.bind("<B1-Motion>", do_move)

# --- 10. UI Layout Construction ---
app_frame = tk.Frame(window, bg=CHROMA_KEY, highlightthickness=0, bd=0)
app_frame.pack(fill=tk.BOTH, expand=True)

app_frame.bind("<ButtonPress-1>", start_move)
app_frame.bind("<B1-Motion>", do_move)

header = tk.Frame(app_frame, bg=CHROMA_KEY, relief="flat", bd=0)
header.pack(fill=tk.X, pady=1, padx=10)
header.bind("<ButtonPress-1>", start_move)
header.bind("<B1-Motion>", do_move)

def create_header_btn(parent, text, command, color="#aaaaaa", font_size=10):
    return tk.Button(
        parent, text=text, bg=CHROMA_KEY, fg=color, bd=0, 
        activebackground="#333333", activeforeground="white", 
        font=("Segoe MDL2 Assets", font_size),
        cursor="hand2", 
        padx=8, pady=4,
        command=command
    )

# Header Buttons Initialization
drag_btn = create_header_btn(header, ICO_DRAG, None) # Logic handled by binding
drag_btn.bind("<ButtonPress-1>", start_move)
drag_btn.bind("<B1-Motion>", do_move)

add_win_btn = create_header_btn(header, ICO_ADD_WIN, duplicate_app, "#2196F3")
add_row_btn = create_header_btn(header, ICO_PLUS, add_row)
rem_row_btn = create_header_btn(header, ICO_MINUS, remove_row)
pin_btn = create_header_btn(header, ICO_PIN, toggle_pin, "#4CAF50", 9)

# Permanent Buttons (Visible on the Right)
close_btn = create_header_btn(header, ICO_CLOSE, close_app, "#f44336")
close_btn.pack(side=tk.RIGHT)

settings_btn = create_header_btn(header, ICO_SETTINGS, open_settings)
settings_btn.pack(side=tk.RIGHT)

toggle_btn = create_header_btn(header, ICO_GHOST, toggle_opacity_mode, "#9c27b0")
toggle_btn.pack(side=tk.RIGHT)

load_data()
window.mainloop()
