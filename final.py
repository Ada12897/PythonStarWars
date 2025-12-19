import pygame
import sys
import random
import math
import os
from glava1 import run_chapter as run_chapter_1
from glava2 import run_chapter as run_chapter_2
from glava3 import run_chapter as run_chapter_3

# === ИМПОРТ РАБОТЫ С БД ===
from popup_result import show_result_popup, show_levelup_popup

from db import (
    load_all_characters,
    load_character,
    load_player_progress,
    save_player_progress,
    load_chapter,
    load_chapters_upto,
    load_chapter_bots,
    load_boss_for_chapter,
    add_character_stats,
    load_character_stats,
    apply_chapter_reward_once,
)


pygame.init()
pygame.mixer.init()

# === ПУТЬ К ПАПКЕ ===
BASE = r"C:\Users\user\Documents\Новая папка"

# === ФОН ГЛАВНОГО МЕНЮ ===
MENU_BG_FILE = BASE + r"\menu_main.png"
menu_bg_original = pygame.image.load(MENU_BG_FILE)   # БЕЗ convert
BASE_WIDTH, BASE_HEIGHT = menu_bg_original.get_size()

# === ФОН МЕНЮ НАСТРОЕК ===
SETTINGS_BG_FILE = BASE + r"\settings_menu.png"
settings_bg_original = pygame.image.load(SETTINGS_BG_FILE)
SETTINGS_BASE_WIDTH, SETTINGS_BASE_HEIGHT = settings_bg_original.get_size()

# === ФОН ВЫБОРА ПЕРСОНАЖА ===
CHARSEL_BG_FILE = BASE + r"\settings_menu.png"
charsel_bg_original = pygame.image.load(CHARSEL_BG_FILE)

# === ФОН ВЫБОРА ГЛАВ (опционально, если есть отдельная картинка) ===
CHAPTERSEL_BG_FILE = BASE + r"\chapters_selection.png"
try:
    chaptersel_bg_original = pygame.image.load(CHAPTERSEL_BG_FILE)
except Exception:
    chaptersel_bg_original = menu_bg_original  # если нет файла — используем фон главного меню


# === НАЧАЛЬНЫЙ РЕЖИМ: ОКНО ПОД РАЗРЕШЕНИЕ ЭКРАНА ===
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
fullscreen = False

# ДЛИНА МИРА
WORLD_WIDTH = int(WIDTH * 2.5)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Star Wars")

# масштабируем фоны под текущее окно
menu_bg = pygame.transform.scale(menu_bg_original, (WIDTH, HEIGHT)).convert()
settings_bg = pygame.transform.scale(settings_bg_original, (WIDTH, HEIGHT)).convert()
charsel_bg = pygame.transform.scale(charsel_bg_original, (WIDTH, HEIGHT)).convert()
chaptersel_bg = pygame.transform.scale(chaptersel_bg_original, (WIDTH, HEIGHT)).convert()

clock = pygame.time.Clock()

DEBUG_OUTLINE = False

# === ГРОМКОСТЬ ===
volume_level = 0.7
pygame.mixer.music.set_volume(volume_level)

# === ШРИФТЫ ===
FONT_BIG = pygame.font.SysFont("arial", 100, bold=True)
FONT_MED = pygame.font.SysFont("arial", 28, bold=True)
FONT_BTN = pygame.font.SysFont("arial", 30, bold=True)

NEON_TIME = 0.0

# === 4 ГЛАВЫ (как на твоей картинке) ===
CHAPTERS_4 = [
    (1, "1. БИТВА ЗА НАБУ"),
    (2, "2. КЛОН-ВОЙНЫ: ПАДЕНИЕ\nРЕСПУБЛИКИ"),
    (3, "3. ВОССТАНИЕ НА ТАТУИНЕ"),
    (4, "4. БИТВА ЗА ЭНДОР"),
]


def draw_center_text(text, font, color, y):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH // 2, y))
    screen.blit(surf, rect)


def recalc_buttons():
    """Пересчитать размеры и позиции кнопок под текущее окно."""
    global btn_play, btn_settings, btn_exit

    btn_w = int(WIDTH * 0.50)
    btn_h = int(HEIGHT * 0.14)

    center_x = WIDTH // 2
    play_y = int(HEIGHT * 0.33)
    settings_y = int(HEIGHT * 0.49)
    exit_y = int(HEIGHT * 0.65)

    btn_play = pygame.Rect(0, 0, btn_w, btn_h)
    btn_play.center = (center_x, play_y)

    btn_settings = pygame.Rect(0, 0, btn_w, btn_h)
    btn_settings.center = (center_x, settings_y)

    btn_exit = pygame.Rect(0, 0, btn_w, btn_h)
    btn_exit.center = (center_x, exit_y)


recalc_buttons()


def toggle_fullscreen():
    """Переключить fullscreen <-> окно. ALT+ENTER или F11."""
    global fullscreen, screen, WIDTH, HEIGHT
    global menu_bg, settings_bg, charsel_bg, chaptersel_bg, WORLD_WIDTH

    fullscreen = not fullscreen

    if fullscreen:
        info_local = pygame.display.Info()
        WIDTH, HEIGHT = info_local.current_w, info_local.current_h
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

    WORLD_WIDTH = int(WIDTH * 2.5)

    menu_bg = pygame.transform.scale(menu_bg_original, (WIDTH, HEIGHT)).convert()
    settings_bg = pygame.transform.scale(settings_bg_original, (WIDTH, HEIGHT)).convert()
    charsel_bg = pygame.transform.scale(charsel_bg_original, (WIDTH, HEIGHT)).convert()
    chaptersel_bg = pygame.transform.scale(chaptersel_bg_original, (WIDTH, HEIGHT)).convert()

    recalc_buttons()


def handle_global_keys(event):
    """Обработчик ALT+ENTER / F11 для всех экранов."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT):
            toggle_fullscreen()
            return True
        if event.key == pygame.K_F11:
            toggle_fullscreen()
            return True
    return False


def img(name, scale):
    original = pygame.image.load(BASE + "\\" + name).convert_alpha()
    return pygame.transform.scale_by(original, scale)

def _load_scaled_list(files, scale):
    return [img(fn, scale) for fn in files]


# ==============================
# ✅ NEW: ЕДИНАЯ ОБРАБОТКА ГЛАВЫ
# ==============================
def run_and_handle_chapter(chapter_id: int, character_id: int):
    """
    Возвращает: "menu" | "continue" | "retry"
    Запуск главы -> попап поражения или победы.
    При первой победе в главе: награда 1 раз (apply_chapter_reward_once) + levelup popup.
    После победы: сохраняем прогресс (разблокируем следующую главу).
    """

    rewards = {
        1: (10, 2),
        2: (12, 3),
        3: (20, 4),
        4: (18, 5),
    }

    while True:
        def _call_chapter(fn, cid):
            ret = fn(cid)

            # вариант 1: глава вернула (won, bg)
            if isinstance(ret, tuple) and len(ret) == 2:
                won, bg = ret
                if bg is None:
                    bg = screen.copy()
                return bool(won), bg

            # вариант 2: глава вернула только bool
            return bool(ret), screen.copy()

        if chapter_id == 1:
            won, bg = _call_chapter(run_chapter_1, character_id)
        elif chapter_id == 2:
            won, bg = _call_chapter(run_chapter_2, character_id)
        elif chapter_id == 3:
            won, bg = _call_chapter(run_chapter_3, character_id)
        else:
            won, bg = False, screen.copy()

        # если глава вдруг вернула только bool (на всякий)
        if isinstance(won, tuple) and len(won) == 2:
            won, bg = won

        if bg is None:
            bg = screen.copy()

        # 2) поражение
        if not won:
            action = show_result_popup(
                screen, clock, bg,
                title_text="ТЫ ПОГИБ...",
                subtitle_text="",
                win=False
            )
            if action == "retry":
                continue
            return "menu"

        # 3) победа: награда 1 раз + прокачка (если применилось)
        hp_add, dmg_add = rewards.get(int(chapter_id), (0, 0))

        applied = False
        try:
            applied = apply_chapter_reward_once(
                cid=int(character_id),
                chapter_id=int(chapter_id),
                hp_add=int(hp_add),
                dmg_add=int(dmg_add)
            )
        except Exception as e:
            print("apply_chapter_reward_once error:", e)

        if applied and (hp_add or dmg_add):
            show_levelup_popup(
                screen, clock, bg,
                title_text="ПРОКАЧКА!",
                subtitle_text="ПОЛУЧЕНЫ УЛУЧШЕНИЯ",
                lines=[f"+{hp_add} HP", f"+{dmg_add} УРОН"],
                win=True
            )
            bg = screen.copy()

        # 4) окно победы
        action = show_result_popup(
            screen, clock, bg,
            title_text="ПОБЕДА!",
            subtitle_text="",
            win=True
        )

        # 5) сохраняем прогресс (разблок следующей главы)
        try:
            progress = load_player_progress(int(character_id))
            unlocked_before = int(progress.get("unlocked_chapters", 1))

            unlocked_after = unlocked_before
            if int(chapter_id) >= unlocked_before:
                unlocked_after = int(chapter_id) + 1

            save_player_progress(int(character_id), int(chapter_id), int(unlocked_after))
        except Exception as e:
            print("save_player_progress error:", e)

        if action == "continue":
            return "continue"
        return "menu"

# ========= МЕНЮ НАСТРОЕК =========

def settings_menu():
    global volume_level

    # ---------- ГЕОМЕТРИЯ ----------
    panel_w = int(WIDTH * 0.38)
    panel_h = int(HEIGHT * 0.42)
    gap = int(WIDTH * 0.05)

    left_panel = pygame.Rect(0, 0, panel_w, panel_h)
    right_panel = pygame.Rect(0, 0, panel_w, panel_h)

    left_panel.center = (WIDTH // 2 - (panel_w // 2 + gap // 2), int(HEIGHT * 0.52))
    right_panel.center = (WIDTH // 2 + (panel_w // 2 + gap // 2), int(HEIGHT * 0.52))

    btn_back = pygame.Rect(0, 0, int(WIDTH * 0.30), int(HEIGHT * 0.12))
    btn_back.center = (WIDTH // 2, int(HEIGHT * 0.85))

    # ---------- ПОЛЗУНОК ----------
    slider_area = pygame.Rect(0, 0, int(panel_w * 0.90), int(panel_h * 0.18))
    slider_area.center = (left_panel.centerx, left_panel.centery - int(panel_h * 0.20))

    slider_line = pygame.Rect(0, 0, int(slider_area.w * 0.78), 9)
    slider_line.midleft = (slider_area.x + 20, slider_area.centery)

    dragging = False

    # ---------- АНИМАЦИИ / ТАЙМИНГ ----------
    t0 = pygame.time.get_ticks()
    intro_dur = 360  # мс

    # helper: мягкое рассеянное свечение (без блюра)
    def draw_soft_glow_rect(surf, rect, color_rgb, strength=1.0, radius=22, pad=14):
        """
        Рисует рассеянный glow несколькими слоями.
        pad — общий "раздув" (меньше pad = меньше glow, чтобы не касалось бортиков).
        """
        r = rect.copy()

        # слои: (inflate, alpha, border_radius_add)
        k = pad / 14.0
        layers = [
            (int(26 * k), 16, 10),
            (int(18 * k), 22, 8),
            (int(12 * k), 28, 6),
            (int(6  * k), 36, 4),
        ]

        for infl, a, br_add in layers:
            if infl <= 0:
                continue
            rr = r.inflate(infl * 2, infl * 2)
            layer = pygame.Surface((rr.w, rr.h), pygame.SRCALPHA)
            aa = int(a * strength)
            pygame.draw.rect(layer, (*color_rgb, aa), layer.get_rect(), border_radius=radius + br_add)
            surf.blit(layer, (rr.x, rr.y))

    while True:
        now = pygame.time.get_ticks()
        dt = clock.tick(60)
        elapsed = now - t0

        mx, my = pygame.mouse.get_pos()

        # ---------- INTRO (slide + fade) ----------
        p = min(1.0, elapsed / float(intro_dur))
        p_e = 1.0 - (1.0 - p) * (1.0 - p)  # easeOutQuad

        slide = int((1.0 - p_e) * (WIDTH * 0.035))

        left_draw = left_panel.copy()
        right_draw = right_panel.copy()
        left_draw.x += slide
        right_draw.x -= slide

        content_alpha = int(255 * p_e)

        # ВАЖНО: ползунок тоже должен "ехать" вместе с панелью
        slider_area_draw = slider_area.move(slide, 0)
        slider_line_draw = slider_line.move(slide, 0)

        hover_slider = (
            slider_area_draw.collidepoint(mx, my)
            or slider_line_draw.collidepoint(mx, my)
        )

        # ---------- INPUT ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if slider_line_draw.collidepoint(event.pos):
                    dragging = True
                if btn_back.collidepoint(event.pos):
                    return

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False

        keys = pygame.key.get_pressed()

        # ---------- DRAG ----------
        if dragging:
            rel = (mx - slider_line_draw.x) / slider_line_draw.w
            volume_level = max(0.0, min(1.0, rel))
            pygame.mixer.music.set_volume(volume_level)

        # ---------- BACKGROUND ----------
        screen.blit(settings_bg, (0, 0))

        title = FONT_BIG.render("НАСТРОЙКИ", True, (235, 240, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.18))))

        # ---------- PANELS ----------
        panel_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_sci_panel(panel_layer, left_draw, "ГРОМКОСТЬ")
        draw_sci_panel(panel_layer, right_draw, "УПРАВЛЕНИЕ")
        panel_layer.set_alpha(content_alpha)
        screen.blit(panel_layer, (0, 0))

        # ---------- SLIDER ----------
        slider_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        if hover_slider:
            # glow МЕНЬШЕ, чтобы не касалось бортиков
            k = 0.85 + 0.15 * (0.5 + 0.5 * math.sin(now * 0.012))
            slider_glow_pad = 8
            draw_soft_glow_rect(
                slider_layer,
                slider_area_draw,
                (35, 170, 255),
                strength=1.05 * k,
                radius=22,
                pad=slider_glow_pad
            )

        pygame.draw.rect(slider_layer, (16, 18, 26), slider_area_draw, border_radius=18)

        edge = pygame.Surface(slider_area_draw.size, pygame.SRCALPHA)
        pygame.draw.rect(edge, (35, 170, 255, 160 if hover_slider else 120),
                         edge.get_rect(), 2, border_radius=18)
        slider_layer.blit(edge, slider_area_draw.topleft)

        pygame.draw.rect(slider_layer, (30, 34, 48), slider_line_draw, border_radius=6)

        fill_w = int(slider_line_draw.w * volume_level)
        fill_rect = pygame.Rect(slider_line_draw.x, slider_line_draw.y, fill_w, slider_line_draw.h)
        pygame.draw.rect(slider_layer, (35, 170, 255), fill_rect, border_radius=6)

        pct = FONT_MED.render(f"{int(volume_level * 100)}%", True, (235, 240, 255))
        slider_layer.blit(
            pct,
            (slider_area_draw.right - pct.get_width() - 18,
             slider_area_draw.centery - pct.get_height() // 2)
        )

        slider_layer.set_alpha(content_alpha)
        screen.blit(slider_layer, (0, 0))

        # =========================================================
        # ЛЕВАЯ ПАНЕЛЬ — ИНФО
        # =========================================================
        info_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        info_x = left_draw.x + int(panel_w * 0.08)
        info_y = slider_area_draw.bottom + int(panel_h * 0.06)

        pulse = (1.0 + math.sin(now * 0.008)) * 0.5
        active_alpha = int(140 + 115 * pulse)

        head = FONT_MED.render("СИСТЕМА СИМУЛЯЦИИ", True, (120, 190, 255))
        info_layer.blit(head, (info_x, info_y))

        y2 = info_y + FONT_MED.get_height() + 10

        stat_label = FONT_MED.render("Статус:", True, (200, 220, 240))
        info_layer.blit(stat_label, (info_x, y2))

        act = FONT_MED.render(" АКТИВНА", True, (220, 245, 255))
        act_s = act.copy()
        act_s.set_alpha(active_alpha)
        info_layer.blit(act_s, (info_x + stat_label.get_width(), y2))

        y2 += FONT_MED.get_height() + 8

        sync = FONT_MED.render("Синхронизация: OK", True, (120, 220, 180))
        info_layer.blit(sync, (info_x, y2))

        y2 += FONT_MED.get_height() + 6

        ver = FONT_MED.render("Версия: 1.0.3", True, (180, 200, 220))
        info_layer.blit(ver, (info_x, y2))

        info_layer.set_alpha(content_alpha)
        screen.blit(info_layer, (0, 0))

        # =========================================================
        # ПРАВАЯ ПАНЕЛЬ — W/A/S/D + ТОЧКА/ЛУЧИ + ЛКМ
        # =========================================================
        ui_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        cx = right_draw.centerx
        cy = right_draw.centery - int(panel_h * 0.05)

        neon = (35, 170, 255)
        line_col = (160, 190, 210)

        KEY_COLORS = {
            "W": (80, 180, 255),
            "A": (120, 255, 140),
            "S": (190, 120, 255),
            "D": (255, 220, 120),
        }

        UI_SCALE = 1.28

        key_off = int(70 * UI_SCALE)
        ray_len1 = int(40 * UI_SCALE)
        ray_len2 = int(18 * UI_SCALE)
        atk_off = int(110 * UI_SCALE)

        active = keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d]
        boost = 4 if active else 0
        pulse_r = int((18 + boost + (2.2 * (1.0 + math.sin(now * 0.010)))) * UI_SCALE)

        shake = int(math.sin(now * 0.018) * 1.3)
        cx2, cy2 = cx + shake, cy - shake

        pygame.draw.circle(ui_layer, neon, (cx2, cy2), pulse_r, 2)

        pygame.draw.line(ui_layer, line_col, (cx2, cy2 - ray_len1), (cx2, cy2 - ray_len2), 2)
        pygame.draw.line(ui_layer, line_col, (cx2 - ray_len1, cy2), (cx2 - ray_len2, cy2), 2)
        pygame.draw.line(ui_layer, line_col, (cx2 + ray_len2, cy2), (cx2 + ray_len1, cy2), 2)
        pygame.draw.line(ui_layer, line_col, (cx2, cy2 + ray_len2), (cx2, cy2 + ray_len1), 2)

        def draw_key_letter(txt, x, y, pressed=False):
            col = KEY_COLORS.get(txt, (235, 240, 255))

            if pressed:
                k = 0.70 + 0.30 * (0.5 + 0.5 * math.sin(now * 0.020))
                r1 = int((34 + 10 * k) * UI_SCALE)
                r2 = int((22 + 8 * k) * UI_SCALE)
                r3 = int((16 + 5 * k) * UI_SCALE)

                pygame.draw.circle(ui_layer, (*col, int(14 + 20 * k)), (x, y), r1)
                pygame.draw.circle(ui_layer, (*col, int(30 + 40 * k)), (x, y), r2)
                pygame.draw.circle(ui_layer, (*col, int(85 + 55 * k)), (x, y), r3, 2)

                pygame.draw.line(ui_layer, (*col, int(40 + 60 * k)), (x, y), (cx2, cy2), 2)

                text_col = (255, 255, 255)
                shadow_a = 180
            else:
                pygame.draw.circle(ui_layer, (200, 210, 225, 10), (x, y), int(16 * UI_SCALE))
                text_col = (200, 210, 225)
                shadow_a = 115

            key_font = pygame.font.SysFont("arial", int(28 * UI_SCALE), bold=True)

            sh = key_font.render(txt, True, (0, 0, 0))
            sh.set_alpha(shadow_a)
            ui_layer.blit(sh, sh.get_rect(center=(x + 2, y + 2)))

            t = key_font.render(txt, True, text_col)
            ui_layer.blit(t, t.get_rect(center=(x, y)))

        draw_key_letter("W", cx, cy - key_off, pressed=keys[pygame.K_w])
        draw_key_letter("A", cx - key_off, cy, pressed=keys[pygame.K_a])
        draw_key_letter("D", cx + key_off, cy, pressed=keys[pygame.K_d])
        draw_key_letter("S", cx, cy + key_off, pressed=keys[pygame.K_s])

        atk_font = pygame.font.SysFont("arial", int(30 * UI_SCALE), bold=True)
        atk = atk_font.render("ЛКМ — УДАР", True, (235, 240, 255))
        ui_layer.blit(atk, atk.get_rect(center=(cx, cy + atk_off)))

        if pygame.mouse.get_pressed()[0]:
            ring_size = int(120 * UI_SCALE)
            ring = pygame.Surface((ring_size, ring_size), pygame.SRCALPHA)
            pygame.draw.circle(
                ring, (255, 90, 90, 80),
                (ring_size // 2, ring_size // 2),
                int(52 * UI_SCALE), 3
            )
            ui_layer.blit(ring, (cx - ring_size // 2, cy - ring_size // 2))

        ui_layer.set_alpha(content_alpha)
        screen.blit(ui_layer, (0, 0))

        # ---------- BACK BUTTON ----------
        btn_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_main_menu_button(
            btn_layer,
            btn_back,
            "НАЗАД",
            neon=(35, 170, 255),
            hovered=btn_back.collidepoint(mx, my)
        )
        btn_layer.set_alpha(content_alpha)
        screen.blit(btn_layer, (0, 0))

        pygame.display.flip()


# ========= ВЫБОР ПЕРСОНАЖА =========

def draw_character_card(
    surf,
    rect,
    name,
    sprite_surf=None,
    selected=False,
    hovered=False,
    dim_alpha=0
):
    """
    Карточка персонажа — ВИЗУАЛ 1 В 1 как в старой версии.
    Движение ТОЛЬКО при selected.
    """

    import math
    t = pygame.time.get_ticks() / 1000.0

    # ====== ЦВЕТА (НЕ ТРОГАТЬ) ======
    METAL_DARK  = (18, 22, 30)
    METAL_INNER = (30, 36, 48)
    PANEL       = (55, 64, 82)
    CORE        = (24, 28, 40)
    TEXT_COL    = (240, 245, 255)

    OPEN_NEON   = (35, 170, 255)   # синий
    SELECT_NEON = (35, 255, 170)   # зелёный

    neon = SELECT_NEON if selected else OPEN_NEON
    radius = 18

    # ====== ГЕОМЕТРИЯ ======
    outer = rect
    mid   = rect.inflate(-10, -10)
    inner = rect.inflate(-20, -20)
    core  = rect.inflate(-32, -38)

    # ====== СВЕЧЕНИЕ (КАК РАНЬШЕ) ======
    if hovered or selected:
        glow = pygame.Surface((outer.w + 24, outer.h + 24), pygame.SRCALPHA)
        alpha = 70 if selected else 40
        pygame.draw.rect(
            glow,
            (*neon, alpha),
            glow.get_rect(),
            border_radius=radius + 14
        )
        surf.blit(glow, (outer.x - 12, outer.y - 12))

    # ====== МЕТАЛЛ ======
    pygame.draw.rect(surf, (70, 80, 98), outer, border_radius=radius)
    pygame.draw.rect(surf, METAL_DARK, mid, border_radius=radius - 2)
    pygame.draw.rect(surf, PANEL, inner, border_radius=radius - 6)
    pygame.draw.rect(surf, METAL_INNER, core, border_radius=radius - 10)

    # ====== НЕОНОВАЯ ОБВОДКА (ВАЖНО!) ======
    edge = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
    edge_alpha = 220 if selected else 150 if hovered else 120
    pygame.draw.rect(
        edge,
        (*neon, edge_alpha),
        edge.get_rect(),
        2,
        border_radius=radius
    )
    surf.blit(edge, outer.topleft)

    # ====== ОБЛАСТЬ СПРАЙТА ======
    label_h = int(rect.h * 0.20)
    sprite_area = pygame.Rect(rect.x, rect.y, rect.w, rect.h - label_h)
    sprite_area = sprite_area.inflate(-36, -28)

    # внутренняя рамка (как раньше!)
    slot = sprite_area.inflate(-20, -20)
    pygame.draw.rect(surf, (12, 14, 20), slot, border_radius=14)
    pygame.draw.rect(surf, (*neon, 140), slot, 2, border_radius=14)

    # ====== ПУЛЬСАЦИЯ (ТОЛЬКО ПРИ SELECTED) ======
    offset_y = 0
    if selected:
        offset_y = int(math.sin(t * 3.0) * 6)  # плавно, не дергается

    # ====== СПРАЙТ ======
    if sprite_surf is not None:
        sw, sh = sprite_surf.get_size()
        scale = min(sprite_area.w / sw, sprite_area.h / sh)
        draw_s = pygame.transform.smoothscale(
            sprite_surf,
            (int(sw * scale), int(sh * scale))
        )
        # --- ПУЛЬСАЦИЯ ТОЛЬКО ЕСЛИ ВЫБРАН ---
        offset_y = 0.0
        if selected:
            t = pygame.time.get_ticks() / 1000.0
            offset_y = (
                    math.sin(t * 3.0) * 4.0 +
                    math.sin(t * 6.0) * 1.2
            )

        shadow = draw_s.copy()
        shadow.fill((0, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        shadow.set_alpha(120)

        surf.blit(
            shadow,
            shadow.get_rect(
                center=(sprite_area.centerx + 4, sprite_area.centery + 6 + offset_y)
            )
        )
        surf.blit(
            draw_s,
            draw_s.get_rect(
                center=(sprite_area.centerx, sprite_area.centery + offset_y)
            )
        )

    # ====== ИМЯ ======
    name_bar = pygame.Rect(
        rect.x + 26,
        rect.bottom - label_h - 6,
        rect.w - 50,
        label_h - 26
    )
    pygame.draw.rect(surf, (25, 60, 120), name_bar, border_radius=14)
    pygame.draw.rect(surf, (*neon, 170), name_bar, 2, border_radius=14)

    font = pygame.font.SysFont("arial", 30, bold=True)
    sh = font.render(name.upper(), True, (0, 0, 0))
    surf.blit(sh, sh.get_rect(center=(name_bar.centerx + 2, name_bar.centery + 2)))

    tx = font.render(name.upper(), True, TEXT_COL)
    surf.blit(tx, tx.get_rect(center=name_bar.center))

    # ====== ЗАТЕМНЕНИЕ (ДЛЯ НЕВЫБРАННЫХ) ======
    if dim_alpha > 0:
        dim = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, dim_alpha))
        surf.blit(dim, rect.topleft)




def choose_character_menu():
    chars = load_all_characters()
    if not chars:
        return None

    import os

    count = len(chars)

    # ✅ при входе никто не выбран
    selected_index = None      # индекс выбранного (или None)
    focused_index = 0          # для стрелок/клавиатуры

    # --- геометрия (чуть ниже от заголовка) ---
    card_w = int(WIDTH * 0.24)
    card_h = int(HEIGHT * 0.50)
    spacing = int(WIDTH * 0.035)

    total_w = card_w * count + spacing * (count - 1)
    start_x = (WIDTH - total_w) // 2
    card_y = int(HEIGHT * 0.245)  # было ближе к заголовку — опустили

    card_rects = []
    for i in range(count):
        x = start_x + i * (card_w + spacing)
        card_rects.append(pygame.Rect(x, card_y, card_w, card_h))

    # кнопки
    btn_w = int(WIDTH * 0.24)
    btn_h = int(HEIGHT * 0.10)

    btn_back = pygame.Rect(0, 0, btn_w, btn_h)
    btn_choose = pygame.Rect(0, 0, btn_w, btn_h)

    btn_back.center = (int(WIDTH * 0.30), int(HEIGHT * 0.86))     # чуть ниже
    btn_choose.center = (int(WIDTH * 0.70), int(HEIGHT * 0.86))   # чуть ниже

    # --- СПРАЙТЫ ДЛЯ КАРТОЧЕК (по имени из БД) ---
    def load_card_sprite(char_name: str):
        name = (char_name or "").strip().lower()

        CARD_SPRITES = {
            "энакин": "Anakin.png",
            "рэй": "rey.png",
            "бултар": "bultar.png",
        }

        file_name = None
        for k, v in CARD_SPRITES.items():
            if k in name:
                file_name = v
                break

        if not file_name:
            return None

        path = os.path.join(BASE, file_name)
        if not os.path.exists(path):
            return None

        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            return None

    # ✅ ПРЕДЗАГРУЗКА спрайтов (ОДИН РАЗ)
    card_sprites = {}
    for ch in chars:
        nm = ch.get("name", "")
        card_sprites[nm] = load_card_sprite(nm)

    # --- АНИМАЦИЯ ВХОДА (медленнее) ---
    t0 = pygame.time.get_ticks()
    intro_dur = 520  # было 360 — сделали медленнее

    # вспомогалка: рисуем disabled кнопку поверх обычной
    def draw_disabled_overlay(ui_surf, rect, radius=18, alpha=120):
        over = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(over, (0, 0, 0, alpha), over.get_rect(), border_radius=radius)
        ui_surf.blit(over, rect.topleft)

    while True:
        now = pygame.time.get_ticks()
        p = min(1.0, (now - t0) / float(intro_dur))
        p_e = 1.0 - (1.0 - p) * (1.0 - p)  # easeOutQuad

        content_alpha = int(255 * p_e)

        # подъезд вниз->вверх (небольшой)
        slide_y = int((1.0 - p_e) * (HEIGHT * 0.06))

        mx, my = pygame.mouse.get_pos()
        mx_ui, my_ui = mx, my - slide_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None

                if event.key == pygame.K_LEFT:
                    focused_index = (focused_index - 1) % count
                if event.key == pygame.K_RIGHT:
                    focused_index = (focused_index + 1) % count

                # Enter — как "клик по карточке": выбрать/снять
                if event.key == pygame.K_RETURN:
                    if selected_index == focused_index:
                        selected_index = None
                    else:
                        selected_index = focused_index

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ex, ey = event.pos
                ex_ui, ey_ui = ex, ey - slide_y

                clicked_card = None
                for i, r in enumerate(card_rects):
                    if r.collidepoint(ex_ui, ey_ui):
                        clicked_card = i
                        break

                if clicked_card is not None:
                    focused_index = clicked_card
                    # ✅ toggle: клик по выбранному снимает выбор
                    if selected_index == clicked_card:
                        selected_index = None
                    else:
                        selected_index = clicked_card

                can_choose = (selected_index is not None)

                if btn_back.collidepoint(ex_ui, ey_ui):
                    return None

                if btn_choose.collidepoint(ex_ui, ey_ui) and can_choose:
                    return chars[selected_index]["character_id"]

        # фон
        screen.blit(charsel_bg, (0, 0))

        # всё рисуем на ui-слое (для alpha)
        ui = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        # --- заголовок (тоже анимируем) ---
        title = FONT_BIG.render("ВЫБОР ПЕРСОНАЖА", True, (235, 240, 255))
        title_rect = title.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.14) - int(slide_y * 0.25)))
        ui.blit(title, title_rect)

        # --- карточки ---
        someone_selected = (selected_index is not None)

        for i, r in enumerate(card_rects):
            ch = chars[i]
            name = ch.get("name", f"Герой {i+1}")
            hovered = r.collidepoint(mx_ui, my_ui)

            # подсветка:
            # - selected: зелёная
            # - hovered: синяя
            is_selected = (selected_index == i)
            is_hovered = hovered

            # тусклость остальных — только если кто-то выбран
            dim_alpha = 0
            if someone_selected and (not is_selected):
                dim_alpha = 120  # можешь 100..150

            spr = card_sprites.get(name)

            draw_character_card(
                ui,
                r.move(0, slide_y),
                name,
                sprite_surf=spr,
                selected=is_selected,
                hovered=is_hovered,
                dim_alpha=dim_alpha
            )

        # --- кнопки ---
        can_choose = (selected_index is not None)

        # НАЗАД (всегда активна)
        draw_main_menu_button(
            ui,
            btn_back.move(0, slide_y),
            "НАЗАД",
            neon=(35, 170, 255),
            hovered=btn_back.collidepoint(mx_ui, my_ui)
        )

        # ВЫБРАТЬ (только если выбран персонаж)
        draw_main_menu_button(
            ui,
            btn_choose.move(0, slide_y),
            "ВЫБРАТЬ",
            neon=(35, 255, 170) if can_choose else (120, 140, 160),
            hovered=(btn_choose.collidepoint(mx_ui, my_ui) and can_choose)
        )
        if not can_choose:
            draw_disabled_overlay(ui, btn_choose.move(0, slide_y), radius=18, alpha=120)

        # применяем общую альфу анимации
        ui.set_alpha(content_alpha)
        screen.blit(ui, (0, 0))

        pygame.display.flip()
        clock.tick(60)

# ========= ВЫБОР ГЛАВ (С НОВЫМИ КНОПКАМИ НАЗАД/ПРОДОЛЖИТЬ) =========

def choose_chapter_menu(max_unlocked: int, current_chapter: int):
    chapters = CHAPTERS_4[:]
    if not chapters:
        return None

    max_unlocked = max(1, int(max_unlocked))

    # ✅ при входе НИКТО НЕ ВЫБРАН
    selected_index = None

    # --- ГЕОМЕТРИЯ ---
    btn_w = int(WIDTH * 0.49)
    btn_h = int(HEIGHT * 0.10)
    gap = int(HEIGHT * 0.03)

    start_y = int(HEIGHT * 0.34)
    center_x = WIDTH // 2

    chapter_rects = []
    for i in range(4):
        r = pygame.Rect(0, 0, btn_w, btn_h)
        r.center = (center_x, start_y + i * (btn_h + gap))
        chapter_rects.append(r)

    # нижние кнопки
    bottom_w = int(WIDTH * 0.26)
    bottom_h = int(HEIGHT * 0.10)

    btn_back = pygame.Rect(0, 0, bottom_w, bottom_h)
    btn_continue = pygame.Rect(0, 0, bottom_w, bottom_h)

    btn_back.center = (int(WIDTH * 0.195), int(HEIGHT * 0.865))
    btn_continue.center = (int(WIDTH * 0.785), int(HEIGHT * 0.865))

    # --- ПАЛИТРА (красный НЕ трогаем) ---
    OPEN_NEON = (35, 170, 255)      # синий
    SELECT_NEON = (255, 70, 70)     # ✅ красный
    LOCK_NEON = (150, 150, 150)     # серый

    NAV_NEON_BACK = (35, 255, 170)  # зелёно-бирюзовый
    NAV_NEON_GO = (255, 210, 70)    # жёлтый

    METAL_DARK = (18, 22, 30)
    METAL_INNER = (30, 36, 48)
    TEXT_COL = (240, 245, 255)

    def _clamp(x): return max(0, min(255, x))
    def _add(c, v): return (_clamp(c[0] + v), _clamp(c[1] + v), _clamp(c[2] + v))

    # ---------- easing для "гармошки" ----------
    def ease_out_back(t, s=1.6):
        # 0..1 -> 0..1 c overshoot
        t = max(0.0, min(1.0, t))
        t -= 1.0
        return 1.0 + (t * t * ((s + 1.0) * t + s))

    def ease_out_quad(t):
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) * (1.0 - t)

    def draw_sci_button(surf, rect, neon, text, enabled=True, hovered=False, pressed=False, dim=False):
        radius = 16

        # если нужно "тускло" — рисуем на слой и понижаем альфу
        if dim:
            layer = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            local = pygame.Rect(0, 0, rect.w, rect.h)
            draw_sci_button(layer, local, neon, text, enabled=enabled, hovered=False, pressed=False, dim=False)
            layer.set_alpha(115)
            surf.blit(layer, rect.topleft)
            return

        outer = rect
        mid = rect.inflate(-8, -8)
        inner = rect.inflate(-16, -16)

        base_outer = (70, 80, 95) if enabled else (60, 60, 60)
        pygame.draw.rect(surf, base_outer, outer, border_radius=radius)
        pygame.draw.rect(surf, METAL_DARK, mid, border_radius=radius - 2)

        panel = (55, 64, 82) if enabled else (45, 45, 45)
        pygame.draw.rect(surf, panel, inner, border_radius=radius - 6)
        core = inner.inflate(-10, -10)
        pygame.draw.rect(surf, METAL_INNER, core, border_radius=radius - 10)

        neon_use = neon if enabled else LOCK_NEON
        edge = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
        bump = 50 if (hovered or pressed) and enabled else 15
        edge_col = _add(neon_use, bump)
        pygame.draw.rect(edge, (*edge_col, 200 if enabled else 120), edge.get_rect(), 2, border_radius=radius)
        surf.blit(edge, outer.topleft)

        if (hovered or pressed) and enabled:
            glow = pygame.Surface((outer.w + 14, outer.h + 14), pygame.SRCALPHA)
            ga = 55 if pressed else 35
            pygame.draw.rect(glow, (*neon_use, ga), glow.get_rect(), border_radius=radius + 10)
            surf.blit(glow, (outer.x - 7, outer.y - 7))

        bolt = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
        bolt_col = (210, 220, 235, 120 if enabled else 70)
        b = 5
        pygame.draw.circle(bolt, bolt_col, (b + 6, b + 6), 3)
        pygame.draw.circle(bolt, bolt_col, (outer.w - b - 6, b + 6), 3)
        pygame.draw.circle(bolt, bolt_col, (b + 6, outer.h - b - 6), 3)
        pygame.draw.circle(bolt, bolt_col, (outer.w - b - 6, outer.h - b - 6), 3)
        surf.blit(bolt, outer.topleft)

        lines = text.split("\n")
        line_h = FONT_BTN.get_height()
        total_h = len(lines) * (line_h + 4) - 4
        y0 = outer.centery - total_h // 2

        txt = TEXT_COL if enabled else (200, 200, 200)

        for i, line in enumerate(lines):
            sh = FONT_BTN.render(line, True, (0, 0, 0))
            shr = sh.get_rect(center=(outer.centerx + 2, y0 + i * (line_h + 4) + line_h // 2 + 2))
            surf.blit(sh, shr)

            t = FONT_BTN.render(line, True, txt)
            tr = t.get_rect(center=(outer.centerx, y0 + i * (line_h + 4) + line_h // 2))
            surf.blit(t, tr)

    # ✅ анимация "гармошка": по очереди + пружинка + смещение
    t0 = pygame.time.get_ticks()
    STAGGER_DELAY = 110    # задержка между кнопками
    ANIM_DUR = 420         # длительность одной кнопки (больше = плавнее)
    START_OFFSET_Y = int(HEIGHT * 0.06)  # откуда "влетает" (снизу вверх)
    START_OFFSET_X = int(WIDTH * 0.02)   # легкая боковая гармошка (влево/вправо)

    while True:
        mx, my = pygame.mouse.get_pos()
        now = pygame.time.get_ticks()

        hover_back = btn_back.collidepoint(mx, my)
        hover_cont = btn_continue.collidepoint(mx, my)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None

                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    step = -1 if event.key == pygame.K_UP else 1

                    if selected_index is None:
                        for i, (cid, _) in enumerate(chapters):
                            if cid <= max_unlocked:
                                selected_index = i
                                break
                    else:
                        tries = 0
                        idx = selected_index
                        while tries < 10:
                            idx = (idx + step) % len(chapters)
                            cid, _ = chapters[idx]
                            if cid <= max_unlocked:
                                selected_index = idx
                                break
                            tries += 1

                if event.key == pygame.K_RETURN:
                    if selected_index is not None:
                        cid, _ = chapters[selected_index]
                        if cid <= max_unlocked:
                            return cid

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(chapter_rects):
                    if r.collidepoint(event.pos):
                        cid, _ = chapters[i]
                        if cid <= max_unlocked:
                            selected_index = None if selected_index == i else i
                        break

                if btn_back.collidepoint(event.pos):
                    return None

                if btn_continue.collidepoint(event.pos):
                    if selected_index is not None:
                        cid, _ = chapters[selected_index]
                        if cid <= max_unlocked:
                            return cid

        screen.blit(chaptersel_bg, (0, 0))

        title = FONT_BIG.render("ВЫБОР ГЛАВ", True, (230, 230, 230))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.20))))

        has_selection = (selected_index is not None)

        # кнопки глав — гармошка по очереди
        for i, (cid, text) in enumerate(chapters):
            locked = cid > max_unlocked
            selected = (selected_index == i) and (not locked)
            hovered = chapter_rects[i].collidepoint(mx, my)
            dim = has_selection and (not locked) and (not selected)

            if locked:
                neon = LOCK_NEON
            elif selected:
                neon = SELECT_NEON
            else:
                neon = OPEN_NEON

            start_i = t0 + i * STAGGER_DELAY
            if now <= start_i:
                a = 0
                t = 0.0
            else:
                t = (now - start_i) / float(ANIM_DUR)
                t = max(0.0, min(1.0, t))
                a = int(255 * ease_out_quad(t))

            # --- пружинка (overshoot) ---
            s = ease_out_back(t, s=1.7)

            # размер: чуть меньше -> больше -> норм (гармошка)
            scale = 0.86 + 0.14 * s

            # движение: из смещения в ноль, с небольшим перелетом
            # (используем (1 - s) чтобы было чуть "перелёта")
            off_y = int((1.0 - s) * START_OFFSET_Y)

            # чередуем влево/вправо для эффекта гармошки
            side = -1 if (i % 2 == 0) else 1
            off_x = int((1.0 - s) * START_OFFSET_X * side)

            base = chapter_rects[i]
            rr = base.copy()
            rr.center = (base.centerx + off_x, base.centery + off_y)
            rr.w = int(base.w * scale)
            rr.h = int(base.h * scale)
            rr.center = (base.centerx + off_x, base.centery + off_y)

            layer = pygame.Surface((rr.w + 22, rr.h + 22), pygame.SRCALPHA)
            local_rect = pygame.Rect(11, 11, rr.w, rr.h)

            draw_sci_button(
                layer,
                local_rect,
                neon,
                text,
                enabled=(not locked),
                hovered=(hovered and not locked),
                pressed=selected,
                dim=dim
            )

            if locked:
                lock = FONT_BTN.render("🔒", True, (230, 230, 230))
                layer.blit(lock, (local_rect.right - lock.get_width() - 14,
                                  local_rect.centery - lock.get_height() // 2))

            layer.set_alpha(a)
            screen.blit(layer, (rr.x - 11, rr.y - 11))

        # continue активна только если выбрана доступная глава
        if selected_index is not None:
            selected_cid, _ = chapters[selected_index]
            can_continue = (selected_cid <= max_unlocked)
        else:
            can_continue = False

        draw_sci_button(
            screen,
            btn_back,
            NAV_NEON_BACK,
            "НАЗАД",
            enabled=True,
            hovered=hover_back,
            pressed=False
        )

        draw_sci_button(
            screen,
            btn_continue,
            NAV_NEON_GO,
            "ПРОДОЛЖИТЬ",
            enabled=can_continue,
            hovered=hover_cont and can_continue,
            pressed=False
        )

        pygame.display.flip()
        clock.tick(60)

def select_character_and_chapter():
    character_id = choose_character_menu()
    if character_id is None:
        return None, None

    progress = load_player_progress(character_id)
    max_unlocked = progress["unlocked_chapters"]
    current_chapter = progress["current_chapter"]

    chapter_id = choose_chapter_menu(max_unlocked, current_chapter)
    if chapter_id is None:
        return None, None

    return character_id, chapter_id

#настройки
def draw_sci_panel(surf, rect, title, neon=(35, 170, 255)):
    """Большая панель как на твоей картинке: металл + неон + заголовок."""
    radius = 18
    outer = rect
    mid = rect.inflate(-10, -10)
    inner = rect.inflate(-22, -22)

    METAL_DARK = (18, 22, 30)
    METAL_INNER = (30, 36, 48)

    # внешний металл
    pygame.draw.rect(surf, (70, 80, 95), outer, border_radius=radius)
    pygame.draw.rect(surf, METAL_DARK, mid, border_radius=radius - 2)

    # внутренняя панель
    pygame.draw.rect(surf, (55, 64, 82), inner, border_radius=radius - 6)
    core = inner.inflate(-14, -14)
    pygame.draw.rect(surf, METAL_INNER, core, border_radius=radius - 10)

    # неоновая тонкая окантовка
    edge = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
    pygame.draw.rect(edge, (*neon, 210), edge.get_rect(), 2, border_radius=radius)
    surf.blit(edge, outer.topleft)

    # заголовок панели
    t = FONT_MED.render(title, True, (240, 245, 255))
    surf.blit(t, (inner.x + 22, inner.y + 18))

    return core  # возвращаем “полезную” область внутри


def draw_keyboard_icon(surf, rect, neon=(35, 170, 255)):
    """Схематичная клавиатура (как на твоём примере), без картинок."""
    r = rect
    radius = 14

    # корпус
    pygame.draw.rect(surf, (12, 14, 20), r, border_radius=radius)
    pygame.draw.rect(surf, neon, r, 2, border_radius=radius)

    # клавиши
    pad = int(r.w * 0.06)
    key_w = int((r.w - pad * 2) / 10)
    key_h = int((r.h - pad * 2) / 4)
    gap = max(2, int(key_w * 0.15))

    for row in range(4):
        for col in range(10):
            x = r.x + pad + col * key_w + gap // 2
            y = r.y + pad + row * key_h + gap // 2
            kw = key_w - gap
            kh = key_h - gap
            key = pygame.Rect(x, y, kw, kh)
            pygame.draw.rect(surf, (26, 30, 42), key, border_radius=6)

    # “неоновая линия” снизу
    line = pygame.Rect(r.x + pad, r.bottom - pad - 6, r.w - pad * 2, 4)
    pygame.draw.rect(surf, neon, line, border_radius=6)


def draw_mouse_icon(surf, rect, neon=(35, 170, 255)):
    """Круглая sci-fi мышь как на твоей картинке: круг + колесо + линия."""
    cx, cy = rect.center
    r = min(rect.w, rect.h) // 2

    # внешний круг
    pygame.draw.circle(surf, (12, 14, 20), (cx, cy), r)
    pygame.draw.circle(surf, neon, (cx, cy), r, 2)

    # вертикальная линия (ось)
    pygame.draw.line(surf, (70, 90, 120), (cx, cy - r + 10), (cx, cy + r - 10), 2)

    # колесо/кнопка сверху
    wheel_h = max(18, r // 2)
    wheel_w = max(8, r // 5)
    wheel = pygame.Rect(0, 0, wheel_w, wheel_h)
    wheel.center = (cx, cy - int(r * 0.35))
    pygame.draw.rect(surf, neon, wheel, border_radius=6)

    # маленькая точка-подсветка
    pygame.draw.circle(surf, (240, 245, 255), (cx, cy - int(r * 0.62)), 3)

def draw_main_menu_button(surf, rect, text, neon=(35, 170, 255), hovered=False, pressed=False):
    """
    Красивые sci-fi кнопки: металл + неон по краю + блик + микро-свечение при наведении.
    Без полосок внутри. Без огромных ореолов.
    """
    radius = 18

    def clamp(x): return max(0, min(255, x))
    def add(c, v): return (clamp(c[0] + v), clamp(c[1] + v), clamp(c[2] + v))
    def mul(c, k): return (clamp(int(c[0] * k)), clamp(int(c[1] * k)), clamp(int(c[2] * k)))
    def mix(a, b, t):
        return (int(a[0]*(1-t)+b[0]*t), int(a[1]*(1-t)+b[1]*t), int(a[2]*(1-t)+b[2]*t))

    # размеры “слоёв”
    outer = rect
    mid = rect.inflate(-8, -8)
    inner = rect.inflate(-16, -16)
    core = rect.inflate(-26, -26)

    # маленькое свечение (аккуратное)
    if hovered or pressed:
        glow = pygame.Surface((outer.w + 18, outer.h + 18), pygame.SRCALPHA)
        a = 55 if pressed else 35
        pygame.draw.rect(glow, (*neon, a), glow.get_rect(), border_radius=radius + 12)
        surf.blit(glow, (outer.x - 9, outer.y - 9))

    # металл: внешний слой
    pygame.draw.rect(surf, (70, 80, 98), outer, border_radius=radius)
    pygame.draw.rect(surf, (18, 22, 30), mid, border_radius=radius - 2)

    # внутренняя панель
    pygame.draw.rect(surf, (52, 60, 78), inner, border_radius=radius - 6)
    pygame.draw.rect(surf, (28, 34, 48), core, border_radius=radius - 10)

    # градиент по “core” сверху-вниз (делает кнопку живой)
    grad = pygame.Surface((core.w, core.h), pygame.SRCALPHA)
    top = add((28, 34, 48), 28)
    midc = add((28, 34, 48), 10)
    bot = mul((28, 34, 48), 0.70)
    for y in range(core.h):
        t = y / max(1, core.h - 1)
        col = mix(top, midc, min(1.0, t / 0.45)) if t < 0.45 else mix(midc, bot, (t - 0.45) / 0.55)
        grad.set_at((0, y), (*col, 255))
    grad = pygame.transform.scale(grad, (core.w, core.h))
    surf.blit(grad, core.topleft)

    # блик (эллипс сверху) — выглядит дорого
    hl = pygame.Surface((core.w, core.h), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (255, 255, 255, 26 if (hovered or pressed) else 18),
                        (-core.w * 0.15, -core.h * 0.75, core.w * 1.3, core.h * 1.2))
    surf.blit(hl, core.topleft)

    # неоновая окантовка (тонкая)
    edge = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
    edge_col = add(neon, 55 if (hovered or pressed) else 20)
    pygame.draw.rect(edge, (*edge_col, 210 if (hovered or pressed) else 150),
                     edge.get_rect(), 2, border_radius=radius)
    surf.blit(edge, outer.topleft)

    # “болты” по углам (очень в стиле)
    bolt = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
    bolt_col = (210, 220, 235, 115 if (hovered or pressed) else 80)
    bx, by = 12, 12
    pygame.draw.circle(bolt, bolt_col, (bx, by), 3)
    pygame.draw.circle(bolt, bolt_col, (outer.w - bx, by), 3)
    pygame.draw.circle(bolt, bolt_col, (bx, outer.h - by), 3)
    pygame.draw.circle(bolt, bolt_col, (outer.w - bx, outer.h - by), 3)
    surf.blit(bolt, outer.topleft)

    # текст + тень
    txt_col = (245, 248, 255)
    shadow = FONT_BTN.render(text, True, (0, 0, 0))
    surf.blit(shadow, shadow.get_rect(center=(outer.centerx + 2, outer.centery + 2)))

    label = FONT_BTN.render(text, True, txt_col)
    surf.blit(label, label.get_rect(center=outer.center))

# ========= ГЛАВНОЕ МЕНЮ =========

def main_menu():
    btn_w = int(WIDTH * 0.42)
    btn_h = int(HEIGHT * 0.12)
    gap = int(HEIGHT * 0.05)

    center_x = WIDTH // 2
    start_y = int(HEIGHT * 0.36)

    btn_play = pygame.Rect(0, 0, btn_w, btn_h)
    btn_settings = pygame.Rect(0, 0, btn_w, btn_h)
    btn_exit = pygame.Rect(0, 0, btn_w, btn_h)

    btn_play.center = (center_x, start_y)
    btn_settings.center = (center_x, start_y + btn_h + gap)
    btn_exit.center = (center_x, start_y + (btn_h + gap) * 2)

    while True:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.collidepoint(mx, my):
                    return "play"
                if btn_settings.collidepoint(mx, my):
                    return "settings"
                if btn_exit.collidepoint(mx, my):
                    pygame.quit()
                    sys.exit()

        screen.blit(menu_bg, (0, 0))
        # === ЗАГОЛОВОК ИГРЫ ===
        title_text = "ЗВЕЗДНЫЕ ВОЙНЫ"
        title_surf = FONT_BIG.render(title_text, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.20)))
        screen.blit(title_surf, title_rect)

        # тень (очень лёгкая)
        shadow = FONT_BIG.render(title_text, True, (0, 0, 0))
        shadow.set_alpha(120)
        shadow_rect = shadow.get_rect(center=(title_rect.centerx + 3, title_rect.centery + 3))
        screen.blit(shadow, shadow_rect)

        draw_main_menu_button(screen, btn_play, "ИГРАТЬ", neon=(35, 170, 255), hovered=btn_play.collidepoint(mx, my))
        draw_main_menu_button(screen, btn_settings, "НАСТРОЙКИ", neon=(255, 210, 70),
                              hovered=btn_settings.collidepoint(mx, my))
        draw_main_menu_button(screen, btn_exit, "ВЫХОД", neon=(255, 80, 80), hovered=btn_exit.collidepoint(mx, my))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":

    while True:
        choice = main_menu()

        if choice == "settings":
            settings_menu()
            continue

        if choice != "play":
            continue

        char_id, chap_id = select_character_and_chapter()
        if char_id is None or chap_id is None:
            continue

        # цикл глав: retry/continue/menu уже внутри run_and_handle_chapter
        while True:
            result = run_and_handle_chapter(int(chap_id), int(char_id))

            if result == "continue":
                chap_id = int(chap_id) + 1

                # если главы нет — в меню
                if chap_id > len(CHAPTERS_4):
                    break

                # если глава ещё не открыта — в меню
                try:
                    pr = load_player_progress(int(char_id))
                    if chap_id > int(pr.get("unlocked_chapters", 1)):
                        break
                except Exception as e:
                    print("load_player_progress error:", e)
                    break

                continue

            # menu (или что угодно) -> выходим в главное меню
            break
