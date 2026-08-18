import os
import tkinter as tk
import pyperclip
import threading
import keyboard
import requests
import base64
from io import BytesIO
from PIL import ImageGrab
import pyautogui
import time
import random


# ─────────────────────────────────────────
#   NodeTokyo — Stealth AI Assistant
#   Vercel API endpoint
# ─────────────────────────────────────────
API_URL = 'https://nodetokyo.vercel.app/api'

# Reusable HTTP session for faster requests
session = requests.Session()


class SnippingTool:
    def __init__(self, parent, on_select):
        self.parent = parent
        self.on_select = on_select

        # Take screenshot of the screen before we show the overlay
        self.screenshot = ImageGrab.grab()
        self.w_pixel, self.h_pixel = self.screenshot.size

        # Create full-screen transparent overlay
        self.overlay = tk.Toplevel(parent)
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.35)
        self.overlay.config(bg='black', cursor='cross')

        self.canvas = tk.Canvas(self.overlay, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        self.start_x = None
        self.start_y = None
        self.rect_id = None

        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        # Allow Escape to cancel
        self.overlay.bind('<Escape>', lambda e: self.cancel())
        
        # Focus on overlay to capture Escape key immediately
        self.overlay.focus_force()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        self.overlay.destroy()

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # Minimum selection size threshold
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            self.on_select(None)
            return

        w_tk = self.parent.winfo_screenwidth()
        h_tk = self.parent.winfo_screenheight()

        scale_x = self.w_pixel / w_tk
        scale_y = self.h_pixel / h_tk

        crop_box = (
            int(x1 * scale_x),
            int(y1 * scale_y),
            int(x2 * scale_x),
            int(y2 * scale_y)
        )

        try:
            cropped_img = self.screenshot.crop(crop_box)
            self.on_select(cropped_img)
        except Exception:
            self.on_select(None)

    def cancel(self):
        self.overlay.destroy()
        self.on_select(None)


class NodreZero:
    def __init__(self):
        # ── Main stealth window ──────────────────────────────────
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)       # Always on top
        self.root.overrideredirect(True)              # No title bar or border
        self.root.attributes('-transparentcolor', 'white')  # White = invisible
        self.root.config(bg='white')

        # Tiny faint label that follows the cursor
        self.label = tk.Label(
            self.root,
            text='.',
            font=('Consolas', 8, 'bold'),
            fg='#d3d3d3',
            bg='white',
            wraplength=350,
            justify='left'
        )
        self.label.pack()

        # ── Ghost Code Preview Window ────────────────────────────
        self.code_window = tk.Toplevel(self.root)
        self.code_window.attributes('-topmost', True)
        self.code_window.overrideredirect(True)
        self.code_window.attributes('-transparentcolor', 'white')
        self.code_window.attributes('-alpha', 0.75)  # Semi-transparent
        self.code_window.withdraw()                  # Hidden by default

        self.code_text = tk.Text(
            self.code_window,
            font=('Consolas', 8, 'bold'),
            bg='white',
            fg='#d3d3d3',
            width=55,
            height=20,
            relief='flat',
            highlightthickness=0,
            insertbackground='white'  # Hide blinking cursor
        )
        self.code_text.pack()
        self.is_code_visible = False

        # ── State variables ──────────────────────────────────────
        self.last_text = pyperclip.paste()
        self.is_hidden = False
        self.is_processing = False   # Anti-spam lock for screen scan
        self.is_auto_scanning = False
        self.auto_scan_after_id = None

        # Auto-typer state
        self.is_typing = False
        self.is_paused = False
        self.text_to_type = ''
        self.type_index = 0

        # Mash mode state
        self.mash_text = ''
        self.mash_index = 0
        self.mash_hook = None
        self.is_start_of_line = True

        # Subject mode (default: dsa)
        self.current_mode = 'dsa'

        # ── Hotkey bindings ──────────────────────────────────────
        keyboard.add_hotkey('ctrl+c', self.on_copy)
        keyboard.add_hotkey('esc',    self.stealth_hide)
        keyboard.add_hotkey('1+e',    self.stealth_hide)
        keyboard.add_hotkey('`',      self.stealth_show)
        keyboard.add_hotkey('ctrl+q', self.panic_exit)
        keyboard.add_hotkey('ctrl+v', self.clear_label)
        keyboard.add_hotkey('alt+s',  self.manual_scan_screen)
        keyboard.add_hotkey('1+s',    self.manual_scan_screen)
        keyboard.add_hotkey('alt+a',  self.toggle_auto_scan)
        keyboard.add_hotkey('1+a',    self.toggle_auto_scan)
        keyboard.add_hotkey('alt+t',  self.scan_screen_ocr)
        keyboard.add_hotkey('alt+r',  self.retry)
        keyboard.add_hotkey('alt+v',  self.auto_type_toggle)
        keyboard.add_hotkey('alt+x',  self.toggle_code_view)
        keyboard.add_hotkey('1+x',    self.toggle_code_view)
        keyboard.add_hotkey('alt+up',   self.scroll_up)
        keyboard.add_hotkey('alt+down', self.scroll_down)
        keyboard.add_hotkey('alt+m',  self.start_mash_mode)

        # Subject mode hotkeys
        keyboard.add_hotkey('alt+1', lambda: self.set_mode('aptitude'))
        keyboard.add_hotkey('alt+2', lambda: self.set_mode('dsa'))
        keyboard.add_hotkey('alt+3', lambda: self.set_mode('fullstack'))
        keyboard.add_hotkey('alt+4', lambda: self.set_mode('aws'))
        keyboard.add_hotkey('alt+5', lambda: self.set_mode('copypaste'))

        # Start UI loop and clipboard monitor
        self.update_ui()
        self.clipboard_monitor()
        self.root.mainloop()

    # ────────────────────────────────────────────────────────────
    #   SUBJECT MODE
    # ────────────────────────────────────────────────────────────

    def set_mode(self, mode):
        self.stop_auto_scan_if_running()
        self.current_mode = mode
        mode_labels = {
            'aptitude': 'ap',
            'dsa':      'dsa',
            'fullstack': 'fs',
            'aws':      'aw',
            'copypaste': 'cp',
        }
        self.label.config(fg='#d3d3d3', text=mode_labels.get(mode, mode))
        self.root.after(1000, lambda: self.label.config(text='.'))

    # ────────────────────────────────────────────────────────────
    #   CLIPBOARD MONITOR
    # ────────────────────────────────────────────────────────────

    def clipboard_monitor(self):
        self.check_clipboard()
        self.root.after(300, self.clipboard_monitor)

    def check_clipboard(self):
        try:
            current = pyperclip.paste()
            if current == self.last_text:
                return
            if len(current.strip()) < 5:
                return
            # Skip if clipboard contains our own AI output
            if 'DONE' in current or 'chars)' in current:
                return

            self.last_text = current
            if not self.is_hidden:
                if self.current_mode == 'copypaste':
                    self.label.config(text='cp')
                    self.root.after(1000, lambda: self.label.config(text='.'))
                else:
                    self.label.config(text='...')
                    threading.Thread(target=self.ask_ai, args=(current,), daemon=True).start()
        except Exception:
            pass

    def on_copy(self):
        if self.is_hidden:
            return
        self.root.after(500, self.check_clipboard)

    # ────────────────────────────────────────────────────────────
    #   AI — TEXT REQUEST
    # ────────────────────────────────────────────────────────────

    def ask_ai(self, text):
        try:
            resp = session.post(
                API_URL,
                json={'text': text, 'mode': self.current_mode},
                timeout=60
            )
            if resp.status_code == 200:
                answer = resp.json().get('answer', '')
                if answer:
                    pyperclip.copy(answer)
                    self.last_text = answer
                    if len(answer) > 15:
                        self.label.config(text='DONE')
                        self.root.after(1000, lambda: self.label.config(text='.'))
                    else:
                        self.label.config(text=answer)
                else:
                    self.label.config(text='empty')
            else:
                self.label.config(text=f'err {resp.status_code}')
        except Exception:
            self.label.config(text='timeout')

    # ────────────────────────────────────────────────────────────
    #   AI — VISION / SCREEN SCAN
    # ────────────────────────────────────────────────────────────

    def scan_screen(self):
        if self.is_processing:
            return
        try:
            self.is_processing = True
            self.label.config(text='sc')
            screenshot = ImageGrab.grab()
            buf = BytesIO()
            screenshot.save(buf, format='JPEG', quality=50)
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            if self.current_mode == 'copypaste':
                threading.Thread(target=self.ask_ai_ocr, args=(img_b64,), daemon=True).start()
            else:
                threading.Thread(target=self.ask_ai_vision, args=(img_b64,), daemon=True).start()
        except Exception:
            self.label.config(text='sc-err')
            self.is_processing = False

    def stop_auto_scan_if_running(self):
        if getattr(self, 'is_auto_scanning', False):
            self.is_auto_scanning = False
            if hasattr(self, 'auto_scan_after_id') and self.auto_scan_after_id:
                self.root.after_cancel(self.auto_scan_after_id)
                self.auto_scan_after_id = None
            self.label.config(text='auto-off')
            self.root.after(1000, lambda: self.label.config(text='.'))

    def manual_scan_screen(self):
        # Schedule on main thread with a small delay.
        # keyboard hotkeys fire on a background thread; calling ImageGrab.grab()
        # from a non-main thread on Windows returns a black frame.
        # The 300ms delay also lets the hotkey keypress clear before capture.
        self.root.after(0, self.stop_auto_scan_if_running)
        self.root.after(300, self.scan_screen)

    def toggle_auto_scan(self):
        if getattr(self, 'is_auto_scanning', False):
            self.root.after(0, self.stop_auto_scan_if_running)
        else:
            self.is_auto_scanning = True
            self.label.config(text='auto-on')
            self.root.after(1000, lambda: self.label.config(text='.'))
            self.root.after(300, self.auto_scan_loop)

    def auto_scan_loop(self):
        if not self.is_auto_scanning:
            return
        self.scan_screen()
        self.auto_scan_after_id = self.root.after(30000, self.auto_scan_loop)

    def ask_ai_vision(self, img_data):
        try:
            resp = session.post(
                API_URL,
                json={'image': img_data, 'mode': self.current_mode},
                timeout=60
            )
            if resp.status_code == 200:
                answer = resp.json().get('answer', '')
                if answer:
                    pyperclip.copy(answer)
                    self.last_text = answer
                    if len(answer) > 15:
                        self.label.config(text='P')
                        self.root.after(1000, lambda: self.label.config(text='.'))
                    else:
                        self.label.config(text=answer)
                else:
                    self.label.config(text='empty')
            else:
                self.label.config(text='sc-err')
        except Exception:
            self.label.config(text='timeout')
        finally:
            self.is_processing = False

    def scan_screen_ocr(self):
        self.stop_auto_scan_if_running()
        if self.is_processing:
            return
        self.is_processing = True
        self.label.config(text='ocr')

        def start_snipping():
            try:
                SnippingTool(self.root, self.process_ocr_image)
            except Exception:
                self.label.config(text='ocr-err')
                self.is_processing = False

        # Run SnippingTool in the main thread
        self.root.after(0, start_snipping)

    def process_ocr_image(self, img):
        if img is None:
            self.label.config(text='.')
            self.is_processing = False
            return

        try:
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=70)
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            threading.Thread(target=self.ask_ai_ocr, args=(img_b64,), daemon=True).start()
        except Exception:
            self.label.config(text='ocr-err')
            self.is_processing = False

    def ask_ai_ocr(self, img_data):
        try:
            resp = session.post(
                API_URL,
                json={'image': img_data, 'mode': 'ocr'},
                timeout=60
            )
            if resp.status_code == 200:
                answer = resp.json().get('answer', '')
                if answer:
                    pyperclip.copy(answer)
                    self.last_text = answer
                    self.label.config(text='ocr-dn')
                    self.root.after(1000, lambda: self.label.config(text='.'))
                else:
                    self.label.config(text='empty')
            else:
                self.label.config(text=f'err {resp.status_code}')
        except Exception:
            self.label.config(text='timeout')
        finally:
            self.is_processing = False

    # ────────────────────────────────────────────────────────────
    #   RETRY
    # ────────────────────────────────────────────────────────────

    def retry(self):
        self.stop_auto_scan_if_running()
        if self.is_typing or getattr(self, 'mash_hook', None):
            return
        current = pyperclip.paste()
        if len(current.strip()) > 5:
            self.label.config(text='re..')
            threading.Thread(target=self.ask_ai, args=(current,), daemon=True).start()

    # ────────────────────────────────────────────────────────────
    #   AUTO-TYPER (Alt+V)
    # ────────────────────────────────────────────────────────────

    def auto_type_toggle(self):
        self.stop_auto_scan_if_running()
        if self.is_hidden:
            return
        try:
            raw = pyperclip.paste()
            # Clean up non-breaking spaces and Windows line endings
            current = raw.replace('\xa0', ' ').replace('\r\n', '\n').replace('*', '')

            # If a different text is in clipboard, reset and start fresh
            if self.is_typing and self.text_to_type != current:
                self.is_typing = False
                time.sleep(0.1)

            if self.is_typing:
                # Already typing — toggle pause/resume
                if self.is_paused:
                    self.is_paused = False
                    self.label.config(text='t..')
                    self.root.after(1000, lambda: self.label.config(text='..'))
                else:
                    self.is_paused = True
                    self.label.config(text='psd')
                    self.root.after(1000, lambda: self.label.config(text='.'))
            else:
                # Start new auto-type session
                self.text_to_type = current
                if self.text_to_type:
                    self.type_index = 0
                    self.is_typing = True
                    self.is_paused = False
                    self.label.config(text='t..')
                    self.root.after(1000, lambda: self.label.config(text='..'))
                    threading.Thread(target=self.type_worker, daemon=True).start()
        except Exception:
            pass

    def type_worker(self):
        try:
            time.sleep(0.5)
            keyboard.release('alt')
            pyautogui.keyUp('alt')

            is_start_of_line = True
            was_paused = False

            while self.type_index < len(self.text_to_type) and self.is_typing:
                if self.is_paused:
                    was_paused = True
                    time.sleep(0.1)
                    continue

                if was_paused:
                    time.sleep(0.5)
                    was_paused = False
                    keyboard.release('alt')
                    pyautogui.keyUp('alt')

                char = self.text_to_type[self.type_index]

                # Handle newline
                if char == '\n':
                    is_start_of_line = True
                    pyautogui.press('enter')
                    self.type_index += 1
                    continue

                # Skip leading spaces/tabs on new lines (anti-staircase)
                if is_start_of_line and char in (' ', '\t'):
                    self.type_index += 1
                    continue

                is_start_of_line = False
                pyautogui.write(char)
                self.type_index += 1

            if self.is_typing:
                self.is_typing = False
                if not self.is_hidden:
                    self.label.config(text='d')
                    self.root.after(1000, lambda: self.label.config(text='.'))

        except Exception:
            self.is_typing = False
            if not self.is_hidden:
                self.label.config(text='err')

    # ────────────────────────────────────────────────────────────
    #   MASH MODE (Alt+M)
    #   Press any key → it types the next character of the answer
    # ────────────────────────────────────────────────────────────

    def start_mash_mode(self):
        self.stop_auto_scan_if_running()
        if self.is_hidden:
            return
        try:
            current = pyperclip.paste().replace('\xa0', ' ').replace('\r\n', '\n').replace('**', '')

            # If mash already active, toggle it off
            if getattr(self, 'mash_hook', None):
                keyboard.unhook(self.mash_hook)
                self.mash_hook = None
                self.label.config(text='m-off')
                self.root.after(1000, lambda: self.label.config(text='.'))
                return

            # Reset if new content
            if getattr(self, 'mash_text', '') != current:
                self.mash_text = current
                self.mash_index = 0
                self.is_start_of_line = True

            if self.mash_text:
                self.label.config(text='m-on')
                self.root.after(1000, lambda: self.label.config(text='..'))
                self.mash_hook = keyboard.on_press(self.mash_callback, suppress=True)
        except Exception:
            pass

    def mash_callback(self, event):
        if event.event_type != keyboard.KEY_DOWN:
            return True

        # Allow special keys to pass through normally
        if len(event.name) > 1 or event.name == 'space':
            return True

        if self.mash_index < len(self.mash_text):
            # Skip leading whitespace on new lines
            while (
                getattr(self, 'is_start_of_line', False)
                and self.mash_index < len(self.mash_text)
                and self.mash_text[self.mash_index] in (' ', '\t')
            ):
                self.mash_index += 1

            if self.mash_index >= len(self.mash_text):
                keyboard.unhook(self.mash_hook)
                self.mash_hook = None
                self.label.config(text='m-dn')
                self.root.after(1000, lambda: self.label.config(text='.'))
                return False

            char = self.mash_text[self.mash_index]

            if char == '\n':
                keyboard.send('enter')
                self.is_start_of_line = True
            else:
                keyboard.write(char)
                self.is_start_of_line = False

            self.mash_index += 1

            # Done
            if self.mash_index >= len(self.mash_text):
                keyboard.unhook(self.mash_hook)
                self.mash_hook = None
                self.label.config(text='m-dn')
                self.root.after(1000, lambda: self.label.config(text='.'))

            return False

        return True

    # ────────────────────────────────────────────────────────────
    #   CODE PREVIEW WINDOW (Alt+X)
    # ────────────────────────────────────────────────────────────

    def toggle_code_view(self):
        self.stop_auto_scan_if_running()
        if self.is_hidden:
            return
        if self.is_code_visible:
            self.code_window.withdraw()
            self.is_code_visible = False
        else:
            data = pyperclip.paste()
            self.code_text.delete('1.0', tk.END)
            self.code_text.insert(tk.END, data)
            x, y = self.root.winfo_pointerxy()
            self.open_x = x
            self.open_y = y
            self.code_window.geometry(f'+{x+30}+{y+30}')
            self.code_window.deiconify()
            self.is_code_visible = True

    def scroll_up(self):
        if self.is_code_visible:
            try:
                self.code_text.yview_scroll(-2, 'units')
            except Exception:
                pass

    def scroll_down(self):
        if self.is_code_visible:
            try:
                self.code_text.yview_scroll(2, 'units')
            except Exception:
                pass

    # ────────────────────────────────────────────────────────────
    #   STEALTH / HIDE / SHOW
    # ────────────────────────────────────────────────────────────

    def stealth_hide(self):
        self.stop_auto_scan_if_running()
        self.is_hidden = True
        self.is_paused = True
        self.root.withdraw()
        self.code_window.withdraw()
        self.is_code_visible = False
        if getattr(self, 'mash_hook', None):
            keyboard.unhook(self.mash_hook)
            self.mash_hook = None

    def stealth_show(self):
        self.is_hidden = False
        self.root.deiconify()

    def clear_label(self):
        self.label.config(text='.')

    def panic_exit(self):
        os._exit(0)

    # ────────────────────────────────────────────────────────────
    #   UI LOOP — follows cursor + mouse shake sensor
    # ────────────────────────────────────────────────────────────

    def update_ui(self):
        try:
            x, y = self.root.winfo_pointerxy()
            if not self.is_hidden:
                self.root.geometry(f'+{x+22}+{y+22}')

            # If mouse moves >50px from where code box was opened, hide it
            if self.is_code_visible:
                if (
                    abs(x - getattr(self, 'open_x', x)) > 50
                    or abs(y - getattr(self, 'open_y', y)) > 50
                ):
                    self.code_window.withdraw()
                    self.is_code_visible = False

            self.root.after(30, self.update_ui)
        except Exception:
            pass


if __name__ == '__main__':
    app = NodreZero()
