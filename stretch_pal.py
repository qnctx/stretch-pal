"""
StretchPal — 你的可爱桌面拉伸提醒伙伴
每2小时（9:00/11:00/13:00/15:00/17:00）弹出可爱横幅飘过屏幕
"""
import tkinter as tk
import random
import math
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

# ---- 颜色配置（可爱贴纸风） ----
TRANSPARENT = "#FF00FF"  # 透明色 key（用于圆角窗口）
CARD_BG = "#FFFBF5"  # 暖白卡面
CARD_BORDER = "#FFC0CB"  # 粉色描边
SHADOW_COLOR = "#E8D5E0"  # 淡紫阴影
TITLE_COLOR = "#FF6B6B"  # 珊瑚红标题
TEXT_COLOR = "#5D4E6D"  # 软紫灰正文
HINT_COLOR = "#C9A9C6"  # 薰衣草提示
ACCENT_COLOR = "#FFB6C1"  # 浅粉（备用控件）
# 装饰圆点色板
DOT_COLORS = ["#FFB6C1", "#FFD700", "#87CEEB", "#DDA0DD", "#98FB98", "#FF9A9E"]


class FloatingBanner:
    """圆角贴纸卡片 — 从右飘入，上下微浮，横穿屏幕"""

    def __init__(self, master, emoji, text):
        self.master = master
        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=TRANSPARENT)
        self.window.attributes("-transparentcolor", TRANSPARENT)

        self.width = 290
        self.height = 250
        self._wave = 0  # 浮动相位

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        self.x = screen_w + 20
        self.y = random.randint(80, max(80, screen_h - 400))

        self.window.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")

        self._build_ui(emoji, text)
        self._no_focus()
        self._bind_click()
        self._animate()

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

    def _round_rect(self, canvas, x1, y1, x2, y2, r=18, **kwargs):
        """用平滑多边形画圆角矩形"""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2 - r,
            x1, y1 + r,
        ]
        canvas.create_polygon(points, smooth=True, **kwargs)

    def _build_ui(self, emoji, text):
        canvas = tk.Canvas(
            self.window,
            width=self.width,
            height=self.height,
            highlightthickness=0,
            bg=TRANSPARENT,
        )
        canvas.pack()

        # 卡片阴影
        self._round_rect(canvas, 14, 14, self.width - 6, self.height - 6,
                         r=18, fill=SHADOW_COLOR, outline="")
        # 主卡片
        self._round_rect(canvas, 8, 8, self.width - 12, self.height - 12,
                         r=18, fill=CARD_BG, outline=CARD_BORDER, width=2)

        # 大 emoji — 视觉焦点
        canvas.create_text(
            self.width // 2, 55, text=emoji,
            font=("Segoe UI Emoji", 48),
        )

        # 标题
        canvas.create_text(
            self.width // 2, 103, text="⏰ 活动时间到！",
            font=("Microsoft YaHei", 12, "bold"),
            fill=TITLE_COLOR,
        )

        # 正文 — 支持 \n 换行
        lines = text.split("\n")
        msg_y = 132
        for line in lines:
            canvas.create_text(
                self.width // 2, msg_y, text=line,
                font=("Microsoft YaHei", 11),
                fill=TEXT_COLOR,
            )
            msg_y += 24

        # 底部提示
        canvas.create_text(
            self.width // 2, msg_y + 6, text="( 点我消失 ~ )",
            font=("Microsoft YaHei", 8),
            fill=HINT_COLOR,
        )

        # 四角 + 随机装饰小圆点
        corners = [
            (24, 24), (self.width - 34, 24),
            (24, self.height - 34), (self.width - 34, self.height - 34),
        ]
        for cx, cy in corners:
            color = random.choice(DOT_COLORS)
            canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                              fill=color, outline="", width=0)

        for _ in range(4):
            cx = random.randint(30, self.width - 30)
            cy = random.randint(30, self.height - 30)
            size = random.randint(2, 4)
            canvas.create_oval(
                cx - size, cy - size, cx + size, cy + size,
                fill=random.choice(DOT_COLORS), outline="", width=0,
            )

        # 卡片顶部的可爱小耳朵装饰
        ear_y = 10
        for ear_x in [self.width // 2 - 30, self.width // 2 + 30]:
            canvas.create_arc(
                ear_x - 8, ear_y, ear_x + 8, ear_y + 16,
                start=0, extent=180, fill=CARD_BG, outline=CARD_BORDER, width=2,
            )
        # 小耳朵上的高光
        canvas.create_oval(
            self.width // 2 - 33, ear_y + 4,
            self.width // 2 - 27, ear_y + 8,
            fill="#FFF", outline="",
        )
        canvas.create_oval(
            self.width // 2 + 27, ear_y + 4,
            self.width // 2 + 33, ear_y + 8,
            fill="#FFF", outline="",
        )

        self._canvas = canvas

    def _bind_click(self):
        self.window.bind("<Button-1>", self.close)
        self._canvas.bind("<Button-1>", self.close)

    def _animate(self):
        if self.x < -self.width - 20:
            self.window.destroy()
            return

        self._wave += 1
        y_offset = int(9 * math.sin(self._wave / 14))
        self.x -= 4

        try:
            self.window.geometry(
                f"{self.width}x{self.height}+{self.x}+{self.y + y_offset}"
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
        print("[StretchPal] 已启动！在 9-17 点每2小时提醒一次")
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
    import argparse

    parser = argparse.ArgumentParser(description="StretchPal - 桌面拉伸提醒")
    parser.add_argument(
        "--now", action="store_true", help="启动后立即弹窗演示"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="只弹窗一次然后退出（测试用）",
    )
    args = parser.parse_args()

    if args.test:
        # 纯测试：弹一个窗，飘完退出
        root = tk.Tk()
        root.withdraw()
        emoji, text = random.choice(MESSAGES)
        banner = FloatingBanner(root, emoji, text)
        print("[StretchPal] 测试横幅已弹出，12秒飘完后自动退出...")
        # 12秒后自动退出（动画约10秒，留2秒余量）
        root.after(12000, lambda: (root.quit(), root.destroy()))
        root.mainloop()
        sys.exit(0)

    app = StretchPal()
    if args.now:
        app.root.after(500, app._show_banner)
