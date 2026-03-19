import tkinter as tk
from tkinter import filedialog
import ctypes
import sys
import subprocess
import os
import json
import uuid
import re

# --- Custom Embedded Icon (A neat, minimalist dark blue icon) ---
ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz"
    "AAALEwAACxMBAJqcGAAAAHJJREFUWIXt1rENwCAQRMEHk4qMoJ+6UD4dKCA+gT0715/kSZZkCQBw"
    "1Z6qOp+L8/e89r1H++t6j+0/tv/Y/mP7j+0/tv/Y/mP7j+0/tv/Y/mP7j+0/tv/Y/mP7j+0/tv/Y"
    "/mP7j+0/tv/Y/mP77/2mAIo9F0QeW73fAAAAAElFTkSuQmCC"
)

# The magic color that Windows turns completely invisible
CHROMA_KEY = "#010101" 

# --- 1. Path & Config Management ---
# Use the standard Windows AppData directory so notes survive PyInstaller temp folders
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

# Set the default note saving folder to be inside our safe AppData folder
SAVE_DIR = global_config.get('save_dir', os.path.join(APP_DIR, 'notes'))

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR, exist_ok=True)

BG_ALPHA = global_config.get('bg_alpha', 0.90)
CONTENT_ALPHA = global_config.get('content_alpha', 1.0)
DESC_FONT_SIZE = global_config.get('desc_font_size', 12)
VAL_FONT_SIZE = global_config.get('val_font_size', 48)

# --- 2. Master Launch Logic ---
if len(sys.argv) == 1:
    existing_notes = [f for f in os.listdir(SAVE_DIR) if f.startswith('note_') and f.endswith('.json')]
    if existing_notes:
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

# --- 3. Save / Load Logic ---
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
    except Exception as e:
        pass

def modify_number(var, match_index, amount):
    text = var.get()
    matches = list(re.finditer(r'-?\d+', text))
    if match_index < len(matches):
        m = matches[match_index]
        old_val = int(m.group())
        new_val = old_val + amount
        # Reconstruct string with the new number
        new_text = text[:m.start()] + str(new_val) + text[m.end():]
        var.set(new_text)
    elif len(matches) == 0:
        var.set(str(amount))

def update_buttons(c):
    if 'btn_frame' not in c:
        return
        
    text = c['val_var'].get()
    matches = list(re.finditer(r'-?\d+', text))
    num_matches = len(matches) if len(matches) > 0 else 1
    
    # Don't recreate buttons if the count of integers hasn't changed
    if getattr(c['btn_frame'], 'num_buttons', -1) == num_matches:
        return
        
    for widget in c['btn_frame'].winfo_children():
        widget.destroy()
        
    c['btn_frame'].num_buttons = num_matches
    btn_font = ("Segoe UI", 9, "bold")
    
    if len(matches) == 0:
        f = tk.Frame(c['btn_frame'], bg=CHROMA_KEY, highlightthickness=0, bd=0)
        f.pack(side=tk.LEFT, padx=8)
        tk.Button(f, text="−", bg=CHROMA_KEY, fg="#555555", bd=0, activebackground="#333333", activeforeground="white", font=btn_font, cursor="hand2", command=lambda: modify_number(c['val_var'], 0, -1)).pack(side=tk.LEFT, padx=2)
        tk.Button(f, text="＋", bg=CHROMA_KEY, fg="#555555", bd=0, activebackground="#333333", activeforeground="white", font=btn_font, cursor="hand2", command=lambda: modify_number(c['val_var'], 0, 1)).pack(side=tk.LEFT, padx=2)
    else:
        for i in range(num_matches):
            f = tk.Frame(c['btn_frame'], bg=CHROMA_KEY, highlightthickness=0, bd=0)
            f.pack(side=tk.LEFT, padx=8)
            tk.Button(f, text="−", bg=CHROMA_KEY, fg="#555555", bd=0, activebackground="#333333", activeforeground="white", font=btn_font, cursor="hand2", command=lambda idx=i: modify_number(c['val_var'], idx, -1)).pack(side=tk.LEFT, padx=2)
            tk.Button(f, text="＋", bg=CHROMA_KEY, fg="#555555", bd=0, activebackground="#333333", activeforeground="white", font=btn_font, cursor="hand2", command=lambda idx=i: modify_number(c['val_var'], idx, 1)).pack(side=tk.LEFT, padx=2)

    # Force background window to sync geometry to fit new buttons
    try:
        window.update_idletasks()
        bg_window.geometry(f"{window.winfo_width()}x{window.winfo_height()}+{window.winfo_x()}+{window.winfo_y()}")
    except NameError:
        pass # bg_window not fully loaded yet

def on_text_change(*args):
    schedule_save()
    for c in counters:
        c['desc_entry'].config(width=max(8, len(c['desc_var'].get())))
        c['val_entry'].config(width=max(2, len(c['val_var'].get())))
        update_buttons(c)

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

def poll_config():
    """Polls the global config every second to sync global properties across all open notes"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
                new_bg_alpha = config.get('bg_alpha', 0.90)
                if round(new_bg_alpha, 2) != round(bg_window.attributes('-alpha'), 2):
                    bg_window.attributes('-alpha', new_bg_alpha)
                    global_config['bg_alpha'] = new_bg_alpha
                
                new_content_alpha = config.get('content_alpha', 1.0)
                if round(new_content_alpha, 2) != round(window.attributes('-alpha'), 2):
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
    window.after(1000, poll_config)

# --- 4. Taskbar & OS Management ---
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

# --- 5. App Controls & Dragging ---
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

def duplicate_app():
    new_id = f"note_{uuid.uuid4().hex[:8]}"
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, new_id])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), new_id])

def minimize_app():
    window.overrideredirect(False)
    bg_window.withdraw()
    window.iconify()

def handle_map_and_focus(event):
    if event.widget == window:
        window.overrideredirect(True)
        bg_window.deiconify()
        bg_window.lift()
        window.lift()
        window.after(10, update_taskbar_presence)

def close_app():
    path = os.path.join(SAVE_DIR, f"{my_note_id}.json")
    try:
        if os.path.exists(path):
            os.remove(path)
    except: pass
    window.destroy()

# Singleton tracker for settings window
settings_win = None

def open_settings():
    global settings_win, global_config, SAVE_DIR
    
    if settings_win is not None and settings_win.winfo_exists():
        settings_win.lift()
        settings_win.focus_set()
        return

    settings_win = tk.Toplevel(window)
    settings_win.title("Settings")
    settings_win.geometry("380x430") 
    settings_win.config(bg="#2b2b2b")
    settings_win.attributes('-topmost', True)

    tk.Label(settings_win, text="Save Data Path:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(10, 0))
    path_var = tk.StringVar(value=SAVE_DIR)
    tk.Entry(settings_win, textvariable=path_var, font=("Segoe UI", 9), width=45, state='readonly').pack(pady=2)

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

    tk.Button(settings_win, text="Browse & Move Files", command=browse_dir, bg="#2196F3", fg="white", relief="flat").pack(pady=5)

    tk.Label(settings_win, text="Background Transparency:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(10, 0))
    bg_alpha_var = tk.DoubleVar(value=global_config.get('bg_alpha', 0.90))
    
    def update_local_bg_alpha(val):
        bg_window.attributes('-alpha', float(val))
        
    def save_bg_alpha_to_config(event):
        global_config['bg_alpha'] = bg_alpha_var.get()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(global_config, f)
        except: pass

    bg_slider = tk.Scale(settings_win, from_=0.15, to_=1.0, resolution=0.05, orient=tk.HORIZONTAL, 
                            variable=bg_alpha_var, command=update_local_bg_alpha, bg="#2b2b2b", fg="white", 
                            highlightthickness=0, bd=0, length=200)
    bg_slider.bind("<ButtonRelease-1>", save_bg_alpha_to_config)
    bg_slider.pack()

    tk.Label(settings_win, text="Content Transparency:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(10, 0))
    content_alpha_var = tk.DoubleVar(value=global_config.get('content_alpha', 1.0))
    
    def update_local_content_alpha(val):
        window.attributes('-alpha', float(val))
        
    def save_content_alpha_to_config(event):
        global_config['content_alpha'] = content_alpha_var.get()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(global_config, f)
        except: pass

    content_slider = tk.Scale(settings_win, from_=0.15, to_=1.0, resolution=0.05, orient=tk.HORIZONTAL, 
                            variable=content_alpha_var, command=update_local_content_alpha, bg="#2b2b2b", fg="white", 
                            highlightthickness=0, bd=0, length=200)
    content_slider.bind("<ButtonRelease-1>", save_content_alpha_to_config)
    content_slider.pack()

    tk.Label(settings_win, text="Title Font Size:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(10, 0))
    desc_size_var = tk.IntVar(value=global_config.get('desc_font_size', 12))
    
    def update_local_desc_size(val):
        for c in counters:
            c['desc_entry'].config(font=("Segoe UI", int(val)))
        
    def save_desc_size_to_config(event):
        global_config['desc_font_size'] = desc_size_var.get()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(global_config, f)
        except: pass

    desc_slider = tk.Scale(settings_win, from_=8, to_=36, orient=tk.HORIZONTAL, 
                           variable=desc_size_var, command=update_local_desc_size, bg="#2b2b2b", fg="white", 
                           highlightthickness=0, bd=0, length=200)
    desc_slider.bind("<ButtonRelease-1>", save_desc_size_to_config)
    desc_slider.pack()

    tk.Label(settings_win, text="Counter Font Size:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(pady=(10, 0))
    val_size_var = tk.IntVar(value=global_config.get('val_font_size', 48))
    
    def update_local_val_size(val):
        for c in counters:
            c['val_entry'].config(font=("Segoe UI", int(val), "bold"))
        
    def save_val_size_to_config(event):
        global_config['val_font_size'] = val_size_var.get()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(global_config, f)
        except: pass

    val_slider = tk.Scale(settings_win, from_=16, to_=96, orient=tk.HORIZONTAL, 
                          variable=val_size_var, command=update_local_val_size, bg="#2b2b2b", fg="white", 
                          highlightthickness=0, bd=0, length=200)
    val_slider.bind("<ButtonRelease-1>", save_val_size_to_config)
    val_slider.pack()


# --- 6. Main Window Setup ---

window = tk.Tk()

# Set Custom Icon Globally
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

bg_window.bind("<ButtonPress-1>", start_move)
bg_window.bind("<B1-Motion>", do_move)

# --- 7. Seamless User Interface ---
bg_color = CHROMA_KEY

app_frame = tk.Frame(window, bg=bg_color, highlightthickness=0, bd=0)
app_frame.pack(fill=tk.BOTH, expand=True)

app_frame.bind("<ButtonPress-1>", start_move)
app_frame.bind("<B1-Motion>", do_move)

header = tk.Frame(app_frame, bg=bg_color, relief="flat", bd=0)
header.pack(fill=tk.X, pady=(2, 0), padx=2)
header.bind("<ButtonPress-1>", start_move)
header.bind("<B1-Motion>", do_move)

add_win_btn = tk.Button(header, text="⧉", bg=bg_color, fg="#2196F3", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 11), cursor="hand2", command=duplicate_app)
add_win_btn.pack(side=tk.LEFT, padx=5)

# --- Stacking logic ---
def add_row(desc_val="Tracker...", val_val="0"):
    row_frame = tk.Frame(app_frame, bg=CHROMA_KEY, highlightthickness=0, bd=0)
    row_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 2))
    
    row_frame.bind("<ButtonPress-1>", start_move)
    row_frame.bind("<B1-Motion>", do_move)
    
    desc_var = tk.StringVar(value=desc_val)
    desc_var.trace_add("write", on_text_change)
    
    desc_entry = tk.Entry(row_frame, textvariable=desc_var, font=("Segoe UI", global_config.get('desc_font_size', 12)), bg=CHROMA_KEY, fg="#aaaaaa", bd=0, highlightthickness=0, justify="center", insertbackground="white")
    desc_entry.pack(pady=(5, 0), fill=tk.X, padx=10)
    
    val_var = tk.StringVar(value=val_val)
    val_var.trace_add("write", on_text_change)
    
    val_entry = tk.Entry(row_frame, textvariable=val_var, font=("Segoe UI", global_config.get('val_font_size', 48), "bold"), bg=CHROMA_KEY, fg="#ffffff", bd=0, highlightthickness=0, justify="center", insertbackground="white")
    val_entry.pack(expand=True, fill=tk.BOTH, pady=0)
    
    # Tiny dynamic + / - Buttons container
    btn_frame = tk.Frame(row_frame, bg=CHROMA_KEY, highlightthickness=0, bd=0)
    btn_frame.pack(pady=(0, 5))
    
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

add_row_btn = tk.Button(header, text="＋", bg=bg_color, fg="#aaaaaa", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 11, "bold"), cursor="hand2", command=add_row)
add_row_btn.pack(side=tk.LEFT, padx=2)

rem_row_btn = tk.Button(header, text="−", bg=bg_color, fg="#aaaaaa", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 11, "bold"), cursor="hand2", command=remove_row)
rem_row_btn.pack(side=tk.LEFT, padx=2)

pin_btn = tk.Button(header, text="📌", bg=bg_color, fg="#4CAF50", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 9), cursor="hand2", command=toggle_pin)
pin_btn.pack(side=tk.LEFT, padx=5)

close_btn = tk.Button(header, text="✕", bg=bg_color, fg="#f44336", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 10, "bold"), cursor="hand2", command=close_app)
close_btn.pack(side=tk.RIGHT, padx=5)

min_btn = tk.Button(header, text="—", bg=bg_color, fg="#aaaaaa", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 10, "bold"), cursor="hand2", command=minimize_app)
min_btn.pack(side=tk.RIGHT, padx=2)

settings_btn = tk.Button(header, text="⚙", bg=bg_color, fg="#aaaaaa", bd=0, activebackground="#333333", activeforeground="white", font=("Segoe UI", 10), cursor="hand2", command=open_settings)
settings_btn.pack(side=tk.RIGHT, padx=2)

load_data()
window.mainloop()
