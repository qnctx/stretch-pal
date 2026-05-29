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
# 尾焰亮晶晶色板
SPARKLE_COLORS = ["#FFD700", "#FFB6C1", "#FF69B4", "#FFA500", "#FFFACD",
                  "#87CEEB", "#DDA0DD", "#FF1493", "#FFDAB9", "#E0FFFF"]

# ---- 锁屏归来文案（元气打鸡血风） ----
WELCOME_BACK = [
    ("⚡", "充电完毕！\n战斗力恢复到 100%，开冲！"),
    ("🚀", "系统检测到一位大佬已归位\n请开始你的表演～"),
    ("💪", "满血复活！\n键盘已经等不及了，开整！"),
    ("🔥", "能量槽已满！\n释放你的小宇宙吧～"),
    ("🏆", "中场休息结束\n下半场开始，加油加油！"),
    ("🌟", "大佬归来！\n全场起立…然后坐下继续肝"),
    ("🎯", "目标锁定：\n今天也要做全公司最靓的仔！"),
    ("🦁", "王者归来！\n站起来吼一嗓子，然后干活！"),
    ("🍜", "摸鱼结束，该干正事了！\n（开玩笑的，辛苦了哈哈）"),
    ("⚔️", "休息好了就是最强状态\n拔剑吧，打工人！"),
    ("🎪", "欢迎回到快乐工位！\n新一轮战斗开始了～"),
    ("💎", "刚刚偷偷给你加了 buff\n接下来两小时效率翻倍！"),
]


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
        self._sparkles = []  # 活跃的尾焰粒子窗口

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
            self._clear_sparkles()
            self.window.destroy()
            return

        self._wave += 1
        y_offset = int(9 * math.sin(self._wave / 14))
        self.x -= 4

        # 每 3 帧生成一颗亮晶晶尾焰
        if self._wave % 3 == 0:
            self._spawn_sparkle()

        try:
            self.window.geometry(
                f"{self.width}x{self.height}+{self.x}+{self.y + y_offset}"
            )
        except tk.TclError:
            self._clear_sparkles()
            return

        self._anim_id = self.window.after(22, self._animate)

    # ---- 亮晶晶尾焰粒子 ----
    def _spawn_sparkle(self):
        """在横幅尾部生成一颗飘落的亮晶晶粒子"""
        sparkle_size = random.randint(6, 12)
        sx = self.x + self.width + random.randint(-10, 10)
        sy = self.y + random.randint(15, self.height - 10)
        color = random.choice(SPARKLE_COLORS)

        win = tk.Toplevel(self.master)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=TRANSPARENT)
        win.attributes("-transparentcolor", TRANSPARENT)
        win.geometry(f"{sparkle_size}x{sparkle_size}+{sx}+{sy}")

        c = tk.Canvas(win, width=sparkle_size, height=sparkle_size,
                      highlightthickness=0, bg=TRANSPARENT)
        c.pack()
        # 亮晶晶圆点 + 十字光芒
        c.create_oval(0, 0, sparkle_size, sparkle_size,
                      fill=color, outline="", width=0)
        mid = sparkle_size // 2
        c.create_line(mid, 0, mid, sparkle_size, fill="#FFFFFF", width=1)
        c.create_line(0, mid, sparkle_size, mid, fill="#FFFFFF", width=1)

        # 无焦点
        try:
            import ctypes
            hwnd = win.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        except Exception:
            pass

        # 动画：向下飘落 + 渐隐
        steps = random.randint(6, 10)
        drift_x = random.choice([-2, -1, 1, 2])
        drift_y = random.randint(2, 5)

        def drift(remaining=steps):
            nonlocal sx, sy
            if remaining <= 0:
                try:
                    win.destroy()
                except tk.TclError:
                    pass
                return
            sx += drift_x
            sy += drift_y
            try:
                win.attributes("-alpha", remaining / steps)
                win.geometry(f"+{sx}+{sy}")
            except tk.TclError:
                return
            win.after(80, drift, remaining - 1)

        win.after(30, drift)
        self._sparkles.append(win)

    def _clear_sparkles(self):
        for w in getattr(self, "_sparkles", []):
            try:
                w.destroy()
            except tk.TclError:
                pass
        self._sparkles.clear()

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
        self._was_locked = False  # 锁屏状态追踪

        if HAS_TRAY:
            self._setup_tray()
        else:
            self._setup_fallback()

        self._schedule_check()
        self._check_lock()  # 每3秒检测锁屏状态
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

    def _show_banner(self, emoji=None, text=None):
        if emoji is None or text is None:
            emoji, text = random.choice(MESSAGES)
        FloatingBanner(self.root, emoji, text)

    # ========== 锁屏检测 ==========

    def _is_locked(self):
        """用 OpenInputDesktop 检测当前输入桌面是否为锁屏桌面"""
        try:
            import ctypes
            # 打开当前接收用户输入的桌面（锁屏时是 Winlogon 桌面）
            h = ctypes.windll.user32.OpenInputDesktop(
                0, False, 0x00010000  # GENERIC_READ
            )
            if not h:
                return True  # 打不开 → 大概率在锁屏
            # 取桌面名称判断
            name = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetUserObjectInformationW(
                h, 2, name, ctypes.sizeof(name), None  # UOI_NAME = 2
            )
            ctypes.windll.user32.CloseDesktop(h)
            # 锁屏时活动桌面名称为 "Winlogon"
            return name.value == "Winlogon"
        except Exception:
            return False

    def _check_lock(self):
        locked = self._is_locked()
        if not locked and self._was_locked:
            # 锁屏 → 解锁：弹出暖心横幅
            emoji, text = random.choice(WELCOME_BACK)
            self._show_banner(emoji=emoji, text=text)
        self._was_locked = locked
        self.root.after(2000, self._check_lock)  # 每2秒检查一次

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
