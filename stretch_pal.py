"""
StretchPal — 你的可爱桌面拉伸提醒伙伴
每2小时（9:00/11:00/13:00/15:00/17:00）弹出可爱横幅飘过屏幕
"""
import tkinter as tk
import random
import threading
import sys
from datetime import datetime, date

# ---- 可选依赖：系统托盘需要 pystray + Pillow ----
try:
    import pystray
    from PIL import Image, ImageDraw

    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

from messages import MESSAGES

# 提醒时间点
REMINDER_HOURS = (9, 11, 13, 15, 17)

# ---- 颜色配置（粉色可爱风） ----
BG_COLOR = "#FFF0F5"  # 薰衣草白
ACCENT_COLOR = "#FFB6C1"  # 浅粉
TEXT_COLOR = "#8B2252"  # 深玫红
TITLE_COLOR = "#FF6347"  # 番茄红
HINT_COLOR = "#CD6889"  # 中粉
BAR_START = "#FFB6C1"
BAR_END = "#FF69B4"


class FloatingBanner:
    """从屏幕右侧飘入→横穿→左侧飘出的可爱横幅"""

    def __init__(self, master, emoji, text):
        self.master = master
        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.93)
        self.window.configure(bg=BG_COLOR)

        self.width = 460
        self.height = 130

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        self.x = screen_w + 20
        self.y = random.randint(60, max(60, screen_h - 350))

        self.window.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")

        self._build_ui(emoji, text)
        self._no_focus()
        self._bind_click()
        self._animate()

    # ---- 窗口不抢焦点 ----
    def _no_focus(self):
        try:
            import ctypes

            hwnd = self.window.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        except Exception:
            pass

    # ---- UI ----
    def _build_ui(self, emoji, text):
        # 顶部渐变装饰条
        bar = tk.Canvas(
            self.window,
            width=self.width,
            height=4,
            highlightthickness=0,
            bg=BG_COLOR,
        )
        bar.place(x=0, y=0)
        for i in range(self.width):
            ratio = i / self.width
            r = 255
            g = int(182 - 30 * ratio)
            b = int(193 - 50 * ratio)
            color = f"#{r:02x}{max(0, g):02x}{max(0, b):02x}"
            bar.create_line(i, 0, i, 4, fill=color)

        # 主容器
        frame = tk.Frame(self.window, bg=BG_COLOR, bd=0)
        frame.pack(fill="both", expand=True, padx=12, pady=(10, 6))

        # Emoji
        emoji_lbl = tk.Label(
            frame,
            text=emoji,
            font=("Segoe UI Emoji", 50),
            bg=BG_COLOR,
        )
        emoji_lbl.pack(side="left", padx=(18, 15))

        # 文字区域
        text_frame = tk.Frame(frame, bg=BG_COLOR)
        text_frame.pack(side="left", fill="both", expand=True)

        title = tk.Label(
            text_frame,
            text="⏰ 活动时间到！",
            font=("Microsoft YaHei", 13, "bold"),
            fg=TITLE_COLOR,
            bg=BG_COLOR,
        )
        title.pack(anchor="w", pady=(8, 4))

        msg = tk.Label(
            text_frame,
            text=text,
            font=("Microsoft YaHei", 13),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
            justify="left",
        )
        msg.pack(anchor="w")

        hint = tk.Label(
            text_frame,
            text="( 点击我消失 ~ )",
            font=("Microsoft YaHei", 9),
            fg=HINT_COLOR,
            bg=BG_COLOR,
        )
        hint.pack(anchor="w", pady=(4, 0))

        # 角上的小花装饰
        deco = tk.Label(
            self.window,
            text="✿",
            font=("Segoe UI Emoji", 12),
            fg="#FF69B4",
            bg=BG_COLOR,
        )
        deco.place(x=self.width - 25, y=self.height - 25)

    def _bind_click(self):
        self.window.bind("<Button-1>", self.close)
        # 让子控件也响应点击关闭
        for child in self.window.winfo_children():
            child.bind("<Button-1>", self.close)
            for sub in child.winfo_children():
                sub.bind("<Button-1>", self.close)

    # ---- 动画 ----
    def _animate(self):
        if self.x < -self.width - 20:
            self.window.destroy()
            return

        self.x -= 5
        try:
            self.window.geometry(
                f"{self.width}x{self.height}+{self.x}+{self.y}"
            )
        except tk.TclError:
            return

        self._anim_id = self.window.after(22, self._animate)

    def close(self, event=None):
        if hasattr(self, "_anim_id"):
            self.window.after_cancel(self._anim_id)
        self.window.destroy()


class StretchPal:
    """主程序：托盘 + 定时器 + 弹窗管理"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("StretchPal")

        self._shown_hours = set()
        self._last_date = date.today()

        if HAS_TRAY:
            self._setup_tray()
        else:
            self._setup_fallback()

        self._schedule_check()
        print("🌸 StretchPal 已启动！在 9-17 点每2小时提醒一次")
        if HAS_TRAY:
            print("   右键系统托盘图标 → 测试弹窗 / 退出")
        else:
            print("   右键桌面右下角小花 → 测试弹窗 / 退出")
        self.root.mainloop()

    # ========== 系统托盘 ==========

    def _setup_tray(self):
        icon_img = self._make_icon()
        menu = pystray.Menu(
            pystray.MenuItem("💪 现在提醒我", self._on_show_now),
            pystray.MenuItem(
                "📋 已触发: 无", self._on_dummy, enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔔 提示时间: 9/11/13/15/17 点", self._on_dummy, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 退出", self._on_quit),
        )
        self._tray_menu = menu
        self._tray = pystray.Icon(
            "stretch_pal",
            icon_img,
            "🌸 StretchPal - 拉伸提醒",
            menu=menu,
        )
        self._tray_thread = threading.Thread(
            target=self._tray.run, daemon=True
        )
        self._tray_thread.start()

    def _make_icon(self):
        """生成一颗粉色爱心作为托盘图标"""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 爱心
        draw.ellipse([6, 2, 30, 26], fill=(255, 105, 180))
        draw.ellipse([30, 2, 54, 26], fill=(255, 105, 180))
        draw.polygon([6, 16, 54, 16, 30, 56], fill=(255, 105, 180))
        return img

    # ========== 无托盘时的备用控件 ==========

    def _setup_fallback(self):
        """没有 pystray 时，右下角放一朵小花作为控制入口"""
        self._ctrl = tk.Toplevel(self.root)
        self._ctrl.overrideredirect(True)
        self._ctrl.attributes("-topmost", True)
        self._ctrl.configure(bg=ACCENT_COLOR)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self._ctrl.geometry(f"38x38+{sw - 50}+{sh - 90}")

        lbl = tk.Label(
            self._ctrl,
            text="🌸",
            font=("Segoe UI Emoji", 16),
            bg=ACCENT_COLOR,
            cursor="hand2",
        )
        lbl.pack(expand=True)

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="💪 现在提醒我", command=self._on_show_now)
        menu.add_separator()
        menu.add_command(label="❌ 退出", command=self._on_quit)

        def popup(event):
            menu.post(event.x_root, event.y_root)

        lbl.bind("<Button-3>", popup)
        lbl.bind("<Button-1>", lambda e: self._on_show_now())

        # 右下角小花也设置不抢焦点
        try:
            import ctypes

            hwnd = self._ctrl.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        except Exception:
            pass

    # ========== 定时逻辑 ==========

    def _schedule_check(self):
        now = datetime.now()
        today = now.date()
        hour, minute = now.hour, now.minute

        # 跨天重置
        if today != self._last_date:
            self._shown_hours.clear()
            self._last_date = today

        # 到点弹出
        if (
            hour in REMINDER_HOURS
            and minute < 5
            and hour not in self._shown_hours
        ):
            self._shown_hours.add(hour)
            self._show_banner()
            self._update_tray_status()

        self.root.after(30000, self._schedule_check)

    # ========== 弹窗 ==========

    def _on_show_now(self, *_):
        """供托盘/小花回调，调度到主线程"""
        self.root.after(0, self._show_banner)

    def _show_banner(self):
        emoji, text = random.choice(MESSAGES)
        FloatingBanner(self.root, emoji, text)

    # ========== 托盘状态 ==========

    def _update_tray_status(self):
        if not HAS_TRAY:
            return
        hours_str = ",".join(
            str(h) for h in sorted(self._shown_hours)
        ) or "无"
        # 更新菜单第二项的文字（重建菜单有点重，这里做个简单版）
        try:
            self._tray.title = f"🌸 StretchPal - 已触发: {hours_str}"
        except Exception:
            pass

    def _on_dummy(self, *_):
        pass

    # ========== 退出 ==========

    def _on_quit(self, *_):
        if HAS_TRAY:
            self._tray.stop()
        # 必须调度到主线程退出 tk
        self.root.after(0, self._quit_tk)

    def _quit_tk(self):
        self.root.quit()
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    StretchPal()
