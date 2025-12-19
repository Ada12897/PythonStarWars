# popup_result.py
import pygame
import sys
import math
import random

# ==========================================================
#  VISUAL HELPERS (HUD / FX)
# ==========================================================

def _clamp(v, a, b):
    return a if v < a else b if v > b else v

def _lerp(a, b, t):
    return a + (b - a) * t

def _draw_soft_glow_circle(surf, pos, radius, color, strength=3):
    # cheap glow: several circles with decreasing alpha
    x, y = int(pos[0]), int(pos[1])
    r = int(radius)
    for i in range(strength, 0, -1):
        rr = int(r * (1.0 + (strength - i) * 0.35))
        a = int(18 * i)
        c = (*color[:3], a)
        pygame.draw.circle(surf, c, (x, y), rr)

def _draw_scanlines(surf, alpha=22, step=3):
    w, h = surf.get_size()
    line = pygame.Surface((w, 1), pygame.SRCALPHA)
    line.fill((0, 0, 0, alpha))
    y = 0
    while y < h:
        surf.blit(line, (0, y))
        y += step

def _draw_vignette(surf, power=0.65):
    # dark edges
    w, h = surf.get_size()
    vg = pygame.Surface((w, h), pygame.SRCALPHA)
    # 4 rectangles with gradients imitation
    # top/bottom
    for i in range(110):
        a = int(_lerp(0, 140, i / 109) * power)
        pygame.draw.rect(vg, (0, 0, 0, a), (0, i, w, 1))
        pygame.draw.rect(vg, (0, 0, 0, a), (0, h - 1 - i, w, 1))
    # left/right
    for i in range(140):
        a = int(_lerp(0, 160, i / 139) * power)
        pygame.draw.rect(vg, (0, 0, 0, a), (i, 0, 1, h))
        pygame.draw.rect(vg, (0, 0, 0, a), (w - 1 - i, 0, 1, h))
    surf.blit(vg, (0, 0))

def _rounded_rect(surf, rect, color, radius=18, width=0):
    pygame.draw.rect(surf, color, rect, width=width, border_radius=radius)

def _draw_panel(surf, rect, accent, inner=(20, 24, 36), outer=(10, 12, 18)):
    # outer glow
    glow = pygame.Surface((rect.w + 40, rect.h + 40), pygame.SRCALPHA)
    _rounded_rect(glow, pygame.Rect(20, 20, rect.w, rect.h), (*accent, 80), radius=26, width=3)
    _rounded_rect(glow, pygame.Rect(18, 18, rect.w + 4, rect.h + 4), (*accent, 40), radius=28, width=3)
    surf.blit(glow, (rect.x - 20, rect.y - 20))

    # main panel
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    _rounded_rect(panel, panel.get_rect(), (*outer, 220), radius=24, width=0)
    _rounded_rect(panel, panel.get_rect().inflate(-6, -6), (*inner, 230), radius=20, width=0)

    # border
    _rounded_rect(panel, panel.get_rect(), (*accent, 220), radius=24, width=2)
    _rounded_rect(panel, panel.get_rect().inflate(-8, -8), (180, 180, 180, 80), radius=18, width=1)

    # corner screws
    for cx, cy in [(14, 14), (rect.w - 14, 14), (14, rect.h - 14), (rect.w - 14, rect.h - 14)]:
        pygame.draw.circle(panel, (220, 220, 220, 110), (cx, cy), 4)
        pygame.draw.circle(panel, (0, 0, 0, 120), (cx, cy), 2)

    surf.blit(panel, rect.topleft)
    return panel

def _draw_hud_grid(surf, t, alpha=28):
    w, h = surf.get_size()
    g = pygame.Surface((w, h), pygame.SRCALPHA)
    step = 80
    ox = int((t * 18) % step)
    oy = int((t * 12) % step)
    col = (40, 220, 255, alpha)
    for x in range(-step, w + step, step):
        pygame.draw.line(g, col, (x - ox, 0), (x - ox, h), 1)
    for y in range(-step, h + step, step):
        pygame.draw.line(g, col, (0, y - oy), (w, y - oy), 1)
    surf.blit(g, (0, 0))

class _FloatShard:
    __slots__ = ("x", "y", "vx", "vy", "r", "vr", "size", "kind", "a")
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-22, -8)  # fly left
        self.vy = random.uniform(-10, 10)
        self.r = random.uniform(0, math.tau)
        self.vr = random.uniform(-1.2, 1.2)
        self.size = random.uniform(8, 18)
        self.kind = random.choice([0, 1, 2])
        self.a = random.randint(45, 95)

    def update(self, dt, w, h):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.r += self.vr * dt
        if self.x < -60:
            self.x = w + random.uniform(0, 120)
            self.y = random.uniform(0, h)
            self.vx = random.uniform(-24, -9)
            self.vy = random.uniform(-12, 12)
            self.size = random.uniform(8, 18)
            self.kind = random.choice([0, 1, 2])
            self.a = random.randint(45, 95)

    def draw(self, surf, accent):
        # triangle / chevron / small quad
        s = self.size
        cx, cy = self.x, self.y
        ang = self.r
        ca, sa = math.cos(ang), math.sin(ang)

        def rot(px, py):
            return (cx + px * ca - py * sa, cy + px * sa + py * ca)

        col = (*accent, self.a)
        if self.kind == 0:
            pts = [rot(-s, -s * 0.6), rot(s, 0), rot(-s, s * 0.6)]
        elif self.kind == 1:
            pts = [rot(-s, -s * 0.5), rot(s * 0.2, -s * 0.1), rot(s, 0), rot(s * 0.2, s * 0.1), rot(-s, s * 0.5)]
        else:
            pts = [rot(-s, -s), rot(s, -s * 0.2), rot(s * 0.4, s), rot(-s, s * 0.2)]
        pygame.draw.polygon(surf, col, pts, width=1)

def _ecg_value(phase):
    # simple repeating ECG-like pattern in [0..1)
    # 0.00-0.10: baseline
    # 0.10-0.18: small bump
    # 0.18-0.24: drop
    # 0.24-0.30: big spike
    # 0.30-0.36: fall below baseline
    # 0.36-0.55: recover
    # else: baseline
    p = phase
    if p < 0.10:
        return 0.0
    if p < 0.18:
        t = (p - 0.10) / 0.08
        return 0.22 * math.sin(t * math.pi)
    if p < 0.24:
        t = (p - 0.18) / 0.06
        return -0.18 * t
    if p < 0.30:
        t = (p - 0.24) / 0.06
        return 1.00 * (1.0 - abs(2 * t - 1))  # triangle spike
    if p < 0.36:
        t = (p - 0.30) / 0.06
        return -0.35 * (1.0 - abs(2 * t - 1))
    if p < 0.55:
        t = (p - 0.36) / 0.19
        return -0.12 * (1.0 - t)
    return 0.0

def _draw_ecg(surf, rect, t, color, alive=True, stop_after_s=1.2):
    """
    alive=True -> pulse keeps going
    alive=False -> pulse runs briefly then becomes flatline
    """
    x, y, w, h = rect
    mid = y + h // 2
    amp = h * 0.36

    # fade out amplitude for death
    if not alive:
        amp_mul = _clamp(1.0 - (t / max(0.001, stop_after_s)), 0.0, 1.0)
    else:
        amp_mul = 1.0

    # draw line
    line = pygame.Surface((w, h), pygame.SRCALPHA)
    points = []
    speed = 1.25  # pulses per second
    for i in range(w):
        phase = (t * speed + (i / w) * 1.2) % 1.0
        v = _ecg_value(phase) * amp * amp_mul
        yy = mid - v
        points.append((x + i, yy))
    pygame.draw.lines(surf, (*color, 170), False, points, 2)

    # glow
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.lines(glow, (*color, 55), False, [(px - x, py - y) for px, py in points], 6)
    surf.blit(glow, (x, y), special_flags=pygame.BLEND_ADD)

    # if dead and fully flat -> add subtle flat line emphasis
    if (not alive) and amp_mul <= 0.02:
        pygame.draw.line(surf, (*color, 120), (x, mid), (x + w, mid), 2)

# ==========================================================
#  BUTTONS
# ==========================================================

def draw_sci_button(surf, rect, text, font, accent=(0, 220, 255),
                    hover=False, pressed=False, disabled=False):
    r = pygame.Rect(rect)
    base_col = (28, 32, 46)
    inner_col = (18, 20, 30)
    edge = accent

    if disabled:
        edge = (120, 120, 120)
    elif pressed:
        base_col = (18, 22, 34)

    # shadow
    sh = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    _rounded_rect(sh, sh.get_rect(), (0, 0, 0, 130), radius=16)
    surf.blit(sh, (r.x, r.y + 4))

    # button
    btn = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    _rounded_rect(btn, btn.get_rect(), (*base_col, 240), radius=16)
    _rounded_rect(btn, btn.get_rect().inflate(-6, -6), (*inner_col, 240), radius=12)
    _rounded_rect(btn, btn.get_rect(), (*edge, 210), radius=16, width=2)

    if hover and not disabled:
        glow = pygame.Surface((r.w + 26, r.h + 26), pygame.SRCALPHA)
        _rounded_rect(glow, pygame.Rect(13, 13, r.w, r.h), (*edge, 70), radius=18, width=5)
        surf.blit(glow, (r.x - 13, r.y - 13), special_flags=pygame.BLEND_ADD)

    label = font.render(text, True, (235, 235, 235) if not disabled else (170, 170, 170))
    surf.blit(btn, r.topleft)
    surf.blit(label, label.get_rect(center=r.center))

# ==========================================================
#  RESULT POPUP (WIN / LOSE)
# ==========================================================

def show_result_popup(screen, clock, background_surface, title_text, subtitle_text="", win=True):
    W, H = screen.get_size()
    start = pygame.time.get_ticks()

    # colors
    accent = (0, 220, 150) if win else (255, 80, 80)
    accent_soft = (0, 220, 150) if win else (255, 90, 90)

    # fonts
    FONT_TITLE = pygame.font.SysFont("arial", max(38, int(H * 0.065)), bold=True)
    FONT_SUB = pygame.font.SysFont("arial", max(18, int(H * 0.030)), bold=True)
    FONT_HINT = pygame.font.SysFont("consolas", max(14, int(H * 0.030)), bold=True)
    FONT_BTN = pygame.font.SysFont("arial", max(18, int(H * 0.030)), bold=True)

    # layout
    panel_w = int(W * 0.78)
    panel_h = int(H * 0.58)
    panel = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2, panel_w, panel_h)

    btn_h = int(panel_h * 0.14)
    btn_w = int(panel_w * 0.36)
    gap = int(panel_w * 0.06)
    btn_y = panel.bottom - btn_h - int(panel_h * 0.10)
    btn_left = pygame.Rect(panel.centerx - gap // 2 - btn_w, btn_y, btn_w, btn_h)
    btn_right = pygame.Rect(panel.centerx + gap // 2, btn_y, btn_w, btn_h)

    left_text = "В МЕНЮ"
    right_text = "ПРОДОЛЖИТЬ" if win else "ЗАНОВО"

    # full-screen shards
    shards = [_FloatShard(W, H) for _ in range(34)]
    # extra small dots
    dots = [(random.randint(0, W), random.randint(0, H), random.randint(25, 70)) for _ in range(70)]

    hover_l = hover_r = False
    pressed_l = pressed_r = False

    while True:
        dt = clock.tick(60) / 1000.0
        t = (pygame.time.get_ticks() - start) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "menu"
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return "continue" if win else "retry"

            if e.type == pygame.MOUSEMOTION:
                mx, my = e.pos
                hover_l = btn_left.collidepoint(mx, my)
                hover_r = btn_right.collidepoint(mx, my)

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                pressed_l = btn_left.collidepoint(mx, my)
                pressed_r = btn_right.collidepoint(mx, my)

            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                mx, my = e.pos
                if pressed_l and btn_left.collidepoint(mx, my):
                    return "menu"
                if pressed_r and btn_right.collidepoint(mx, my):
                    return "continue" if win else "retry"
                pressed_l = pressed_r = False

        # ---- draw base background snapshot
        screen.blit(background_surface, (0, 0))

        # ---- dark overlay
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 165))
        screen.blit(dim, (0, 0))

        # ---- animated HUD effects (full screen)
        _draw_hud_grid(screen, t, alpha=18 if win else 14)

        # dots drift
        for i in range(len(dots)):
            x, y, a = dots[i]
            x -= int(24 * dt)
            if x < -10:
                x = W + random.randint(0, 80)
                y = random.randint(0, H)
                a = random.randint(25, 70)
            dots[i] = (x, y, a)
            pygame.draw.circle(screen, (*accent_soft, a), (x, y), 1)

        # shards
        shard_layer = pygame.Surface((W, H), pygame.SRCALPHA)
        for s in shards:
            s.update(dt, W, H)
            s.draw(shard_layer, accent_soft)
        screen.blit(shard_layer, (0, 0), special_flags=pygame.BLEND_ADD)

        _draw_scanlines(screen, alpha=20, step=3)
        _draw_vignette(screen, power=0.62)

        # ---- panel
        _draw_panel(screen, panel, accent=accent)

        # title/subtitle
        title = FONT_TITLE.render(title_text, True, (235, 235, 235))
        screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.y + int(panel.h * 0.10))))

        if subtitle_text:
            sub = FONT_SUB.render(subtitle_text, True, (210, 210, 210))
            screen.blit(sub, sub.get_rect(midtop=(panel.centerx, panel.y + int(panel.h * 0.22))))

        # transmission + hints
        tx = panel.x + int(panel.w * 0.06)
        ty = panel.y + int(panel.h * 0.60)
        tr_text = "МИССИЯ УСПЕШНО ВЫПОЛНЕНА" if win else "МИССИЯ ПРОВАЛЕНА"
        tr = FONT_HINT.render(tr_text, True, accent)
        screen.blit(tr, (tx, ty))

        hint = FONT_HINT.render("ENTER — ок  |  ESC — в меню", True, (190, 190, 190))
        screen.blit(hint, (tx, ty + int(panel.h * 0.07)))

        # ECG strip (full width inside panel area, not in small box)
        ecg_rect = pygame.Rect(panel.x + int(panel.w * 0.06), panel.y + int(panel.h * 0.36),
                               int(panel.w * 0.88), int(panel.h * 0.11))
        # slight glass background
        glass = pygame.Surface(ecg_rect.size, pygame.SRCALPHA)
        _rounded_rect(glass, glass.get_rect(), (0, 0, 0, 90), radius=14)
        _rounded_rect(glass, glass.get_rect(), (*accent, 110), radius=14, width=1)
        screen.blit(glass, ecg_rect.topleft)

        # lose: pulse for a moment, then flatline
        if win:
            _draw_ecg(screen, ecg_rect, t=t, color=accent, alive=True)
        else:
            _draw_ecg(screen, ecg_rect, t=t, color=accent, alive=False, stop_after_s=1.35)

        # buttons
        draw_sci_button(screen, btn_left, left_text, FONT_BTN, accent=(0, 160, 220), hover=hover_l, pressed=pressed_l)
        draw_sci_button(screen, btn_right, right_text, FONT_BTN, accent=accent, hover=hover_r, pressed=pressed_r)

        pygame.display.flip()

# ==========================================================
#  LEVEL UP POPUP (UPGRADE REPORT)
# ==========================================================

def _draw_stat_card(surf, rect, title, delta_text, accent, fill_ratio, sublabel="SYNCHRONIZED"):
    r = pygame.Rect(rect)
    card = pygame.Surface(r.size, pygame.SRCALPHA)
    _rounded_rect(card, card.get_rect(), (0, 0, 0, 110), radius=16)
    _rounded_rect(card, card.get_rect(), (*accent, 120), radius=16, width=2)

    # header
    font_t = pygame.font.SysFont("arial", max(16, int(r.h * 0.22)), bold=True)
    font_s = pygame.font.SysFont("consolas", max(12, int(r.h * 0.17)), bold=True)
    font_d = pygame.font.SysFont("arial", max(16, int(r.h * 0.22)), bold=True)

    t = font_t.render(title, True, (235, 235, 235))
    card.blit(t, (16, 10))

    # sublabel
    sub = font_s.render(sublabel, True, (*accent, 220))
    card.blit(sub, (16, 10 + t.get_height() + 2))

    # delta
    d = font_d.render(delta_text, True, (235, 235, 235))
    card.blit(d, d.get_rect(topright=(r.w - 16, 12)))

    # progress bar
    bar = pygame.Rect(16, r.h - 22, r.w - 32, 10)
    _rounded_rect(card, bar, (30, 34, 46, 220), radius=8)
    w = int(bar.w * _clamp(fill_ratio, 0.0, 1.0))
    if w > 0:
        _rounded_rect(card, pygame.Rect(bar.x, bar.y, w, bar.h), (*accent, 220), radius=8)

    # little ticks
    for i in range(1, 5):
        xx = bar.x + int(bar.w * (i / 5))
        pygame.draw.line(card, (180, 180, 180, 55), (xx, bar.y), (xx, bar.bottom), 1)

    surf.blit(card, r.topleft)

def _draw_received_row(surf, rect, text_left, text_right, accent):
    r = pygame.Rect(rect)
    row = pygame.Surface(r.size, pygame.SRCALPHA)
    _rounded_rect(row, row.get_rect(), (0, 0, 0, 95), radius=14)
    _rounded_rect(row, row.get_rect(), (*accent, 90), radius=14, width=2)

    # icon
    pygame.draw.circle(row, (*accent, 220), (18, r.h // 2), 6)
    pygame.draw.circle(row, (0, 0, 0, 140), (18, r.h // 2), 3)

    font = pygame.font.SysFont("arial", max(16, int(r.h * 0.42)), bold=True)
    a = font.render(text_left, True, (235, 235, 235))
    b = font.render(text_right, True, (235, 235, 235))
    row.blit(a, (36, (r.h - a.get_height()) // 2))
    row.blit(b, b.get_rect(midright=(r.w - 18, r.h // 2)))

    surf.blit(row, r.topleft)

def show_levelup_popup(
    screen,
    clock,
    background_surface,
    title_text="ПРОКАЧКА!",
    subtitle_text="ПОЛУЧЕНЫ УЛУЧШЕНИЯ",
    lines=None,
    extra_text="",
    win=True,   # ✅ добавили, чтобы final.py не падал
):

    """
    Обновлённый экран прокачки:
    - Убрано полностью: "БЫЛО", левая колонка, UPGRADE REPORT, BASE-сравнения.
    - Оставлено: заголовок, подзаголовок, ровный список улучшений, кнопка OK.
    - Окна победы/поражения (show_result_popup) НЕ ЗАТРАГИВАЕТ.
    """
    import pygame
    import math

    if lines is None:
        lines = []

    # ---------- helpers ----------
    def _safe_font(size, bold=False):
        try:
            f = pygame.font.Font(None, size)
            if hasattr(f, "set_bold"):
                f.set_bold(bold)
            return f
        except Exception:
            return pygame.font.SysFont("arial", size, bold=bold)

    def _parse_upgrade_line(s: str):
        """
        Пытаемся красиво разложить строку:
        "+10 HP" -> ("HP", "+10")
        "+2 УРОН" -> ("УРОН", "+2")
        "СИЛА +2 УРОН" -> ("СИЛА", "+2 УРОН")
        Если не получилось — вернём (s, "")
        """
        t = (s or "").strip()
        if not t:
            return ("", "")

        parts = t.split()
        # вариант: "+10 HP"
        if len(parts) == 2 and (parts[0].startswith("+") or parts[0].startswith("-")):
            return (parts[1], parts[0])

        # вариант: "ЗДОРОВЬЕ +10 HP" или "СИЛА +2 УРОН"
        # ищем первое слово с +/-
        for i, p in enumerate(parts):
            if p.startswith("+") or p.startswith("-"):
                left = " ".join(parts[:i]).strip()
                right = " ".join(parts[i:]).strip()
                if left and right:
                    return (left, right)

        return (t, "")

    # ---------- colors ----------
    overlay_alpha = 170
    bg_dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    bg_dim.fill((0, 0, 0, overlay_alpha))

    # UI colors (под твой sci-fi стиль)
    C_PANEL = (8, 10, 18)
    C_PANEL2 = (12, 14, 26)
    C_LINE = (230, 190, 90)        # золотая рамка
    C_TEXT = (235, 240, 250)
    C_SUB = (180, 190, 210)
    C_CYAN = (60, 220, 255)
    C_BAR_BG = (28, 32, 46)

    # ---------- fonts ----------
    f_title = _safe_font(64, bold=True)
    f_sub = _safe_font(28, bold=False)
    f_label = _safe_font(24, bold=True)
    f_small = _safe_font(45, bold=False)
    f_value = _safe_font(26, bold=True)

    W, H = screen.get_size()

    # ---------- panel geometry ----------
    panel_w = int(W * 0.82)
    panel_h = int(H * 0.62)
    panel_x = (W - panel_w) // 2
    panel_y = (H - panel_h) // 2

    # Content paddings
    pad = 32
    inner_x = panel_x + pad
    inner_y = panel_y + pad
    inner_w = panel_w - pad * 2

    # Button
    btn_w = int(panel_w * 0.42)
    btn_h = 70
    btn_x = panel_x + (panel_w - btn_w) // 2
    btn_y = panel_y + panel_h - btn_h - 28

    # Rows area
    title_h = 110
    rows_top = inner_y + title_h
    rows_bottom = btn_y - 26
    rows_h = max(120, rows_bottom - rows_top)

    # Prepare rows
    parsed = [_parse_upgrade_line(s) for s in lines if (s or "").strip()]
    if not parsed:
        parsed = [("УЛУЧШЕНИЕ", "+1")]

    # Limit rows to 4 visually (чтобы не ломало макет)
    parsed = parsed[:4]

    # Animation timer
    t0 = pygame.time.get_ticks()

    running = True
    result = "ok"

    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                result = "ok"
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
                    result = "ok"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if pygame.Rect(btn_x, btn_y, btn_w, btn_h).collidepoint(mx, my):
                    running = False
                    result = "ok"

        # ---------- draw ----------
        # background
        if background_surface is not None:
            screen.blit(background_surface, (0, 0))
        screen.blit(bg_dim, (0, 0))

        # panel (двухслойный для глубины)
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(screen, C_PANEL, panel_rect, border_radius=18)
        inner_rect = panel_rect.inflate(-8, -8)
        pygame.draw.rect(screen, C_PANEL2, inner_rect, border_radius=16)

        # border
        pygame.draw.rect(screen, C_LINE, panel_rect, width=2, border_radius=18)

        # subtle scanline / noise (если у тебя уже есть _draw_scanlines — можно заменить на неё)
        # тут лёгкий эффект через альфу, чтобы не мешал читабельности
        scan = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        for y in range(0, panel_h, 6):
            scan.fill((0, 0, 0, 22), rect=pygame.Rect(0, y, panel_w, 2))
        screen.blit(scan, (panel_x, panel_y))

        # title
        title_surf = f_title.render(str(title_text), True, C_TEXT)
        title_rect = title_surf.get_rect(center=(W // 2, panel_y + 72))
        screen.blit(title_surf, title_rect)

        sub_surf = f_sub.render(str(subtitle_text), True, C_SUB)
        sub_rect = sub_surf.get_rect(center=(W // 2, panel_y + 118))
        screen.blit(sub_surf, sub_rect)

        # rows (одна сетка — всё ровно)
        row_gap = 18
        row_h = 74
        max_rows_fit = max(1, (rows_h + row_gap) // (row_h + row_gap))
        rows = parsed[:max_rows_fit]

        start_y = rows_top
        now = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin((now - t0) / 350.0)

        for i, (lbl, val) in enumerate(rows):
            ry = start_y + i * (row_h + row_gap)
            rrect = pygame.Rect(inner_x, ry, inner_w, row_h)

            # row panel
            pygame.draw.rect(screen, (6, 7, 12), rrect, border_radius=14)
            pygame.draw.rect(screen, (20, 24, 40), rrect, width=2, border_radius=14)

            # label left
            lbl_txt = f_label.render(lbl.upper(), True, C_TEXT)
            screen.blit(lbl_txt, (rrect.x + 18, rrect.y + 14))

            # value right
            if val:
                val_txt = f_value.render(val.upper(), True, C_CYAN)
                val_rect = val_txt.get_rect()
                val_rect.midright = (rrect.right - 18, rrect.y + 26)
                screen.blit(val_txt, val_rect)

            # bar
            bar_x = rrect.x + 18
            bar_y = rrect.y + 44
            bar_w = rrect.w - 36
            bar_h = 14

            pygame.draw.rect(screen, C_BAR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=10)

            # fill (анимированная “синхронизация”, но без сравнения "было")
            # чтобы не зависеть от чисел — просто визуальный прогресс
            base_fill = 0.55 + 0.25 * pulse
            fill_w = int(bar_w * max(0.15, min(0.95, base_fill)))
            pygame.draw.rect(screen, C_CYAN, (bar_x, bar_y, fill_w, bar_h), border_radius=10)


        # получено (коротко, без повторов)
        # если lines много — покажем одной строкой
        got_str = " · ".join([(" ".join([v, l]).strip() if v and l else (l or v)).strip() for (l, v) in rows])
        got_str = got_str.strip() if got_str else ""
        if got_str:
            got = f_small.render(f"ПОЛУЧЕНО: {got_str}", True, (210, 220, 235))
            screen.blit(got, (inner_x, btn_y - 63))

        # button OK (используй твою draw_sci_button если она есть)
        mouse = pygame.mouse.get_pos()
        hovering = pygame.Rect(btn_x, btn_y, btn_w, btn_h).collidepoint(*mouse)

        # кнопка в твоём стиле (простая версия)
        pygame.draw.rect(screen, (10, 12, 20), (btn_x, btn_y, btn_w, btn_h), border_radius=18)
        pygame.draw.rect(screen, C_LINE, (btn_x, btn_y, btn_w, btn_h), width=2, border_radius=18)
        if hovering:
            glow = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            glow.fill((255, 220, 120, 35))
            screen.blit(glow, (btn_x, btn_y))

        ok_txt = _safe_font(34, bold=True).render("OK", True, C_TEXT)
        ok_rect = ok_txt.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2))
        screen.blit(ok_txt, ok_rect)

        pygame.display.flip()

    return result
