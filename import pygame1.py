import pygame
import sys
import random

# === ИМПОРТ РАБОТЫ С БД ===
from db import (
    load_all_characters,
    load_character,
    load_player_progress,
    save_player_progress,
    load_chapter,
    load_chapters_upto,
    load_chapter_bots,
    load_boss_for_chapter,
)

pygame.init()
pygame.mixer.init()

# === ПУТЬ К ПАПКЕ ===
BASE = r"C:\Users\user\Documents\Новая папка"  # свой путь

# === ФОН ГЛАВНОГО МЕНЮ ===
MENU_BG_FILE = BASE + r"\menu_main.png"
menu_bg_original = pygame.image.load(MENU_BG_FILE)   # БЕЗ convert
BASE_WIDTH, BASE_HEIGHT = menu_bg_original.get_size()

# === ФОН МЕНЮ НАСТРОЕК ===
SETTINGS_BG_FILE = BASE + r"\settings_menu.png"
settings_bg_original = pygame.image.load(SETTINGS_BG_FILE)
SETTINGS_BASE_WIDTH, SETTINGS_BASE_HEIGHT = settings_bg_original.get_size()

# === ФОН ВЫБОРА ПЕРСОНАЖА ===
CHARSEL_BG_FILE = BASE + r"\character_selection.png"
charsel_bg_original = pygame.image.load(CHARSEL_BG_FILE)

# === ФОН ВЫБОРА ГЛАВ (опционально, если есть отдельная картинка) ===
CHAPTERSEL_BG_FILE = BASE + r"\chapters_selection.png"
try:
    chaptersel_bg_original = pygame.image.load(CHAPTERSEL_BG_FILE)
except Exception:
    chaptersel_bg_original = menu_bg_original  # если нет файла — используем фон главного меню

# === ФОН БОЯ (ТАЙЛОВЫЙ, ДЛЯ БЕСКОНЕЧНОГО СКРОЛЛА) ===
BG_FILE = BASE + r"\background.png"
fight_bg_original = pygame.image.load(BG_FILE)

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
fight_bg = pygame.transform.scale(fight_bg_original, (WIDTH, HEIGHT)).convert()
charsel_bg = pygame.transform.scale(charsel_bg_original, (WIDTH, HEIGHT)).convert()
chaptersel_bg = pygame.transform.scale(chaptersel_bg_original, (WIDTH, HEIGHT)).convert()

clock = pygame.time.Clock()

DEBUG_OUTLINE = False

# === ГРОМКОСТЬ ===
volume_level = 0.7
pygame.mixer.music.set_volume(volume_level)

# === ШРИФТЫ ===
FONT_BIG = pygame.font.SysFont("arial", 48, bold=True)
FONT_MED = pygame.font.SysFont("arial", 28, bold=True)
FONT_BTN = pygame.font.SysFont("arial", 30, bold=True)

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
    global menu_bg, settings_bg, fight_bg, charsel_bg, chaptersel_bg, WORLD_WIDTH

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
    fight_bg = pygame.transform.scale(fight_bg_original, (WIDTH, HEIGHT)).convert()
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


# === СПРАЙТЫ ===
player_base_img = pygame.image.load(BASE + "\\standiright1.png").convert_alpha()
bot_base_img = pygame.image.load(BASE + "\\1.png").convert_alpha()

PLAYER_SCALE = 0.9
BOT_SIZE_MULT = 1.05
BOT_SCALE = (player_base_img.get_height() * PLAYER_SCALE * BOT_SIZE_MULT) / bot_base_img.get_height()


def img(name, scale):
    original = pygame.image.load(BASE + "\\" + name).convert_alpha()
    return pygame.transform.scale_by(original, scale)


# игрок
idle_right_img = img("standiright1.png", PLAYER_SCALE)
walk_right_imgs = [
    img("walkright1.png", PLAYER_SCALE),
    img("walkright2.png", PLAYER_SCALE),
    img("walkright3.png", PLAYER_SCALE),
    img("walkiright4.png", PLAYER_SCALE),
    img("walkright5.png", PLAYER_SCALE),
    img("walkiright4.png", PLAYER_SCALE),
]
idle_left_img = pygame.transform.flip(idle_right_img, True, False)
walk_left_imgs = [pygame.transform.flip(s, True, False) for s in walk_right_imgs]
hit_right_imgs = [
    img("hit1.png", PLAYER_SCALE),
    img("hit2.png", PLAYER_SCALE),
    img("hit3.png", PLAYER_SCALE),
    img("hit4.png", PLAYER_SCALE),
    img("hit5.png", PLAYER_SCALE),
    img("hit6.png", PLAYER_SCALE),
]
hit_left_imgs = [pygame.transform.flip(s, True, False) for s in hit_right_imgs]

# бот
bot_idle_right_img = img("1.png", BOT_SCALE)
bot_walk_right_imgs = [
    img("1.png", BOT_SCALE),
    img("2.png", BOT_SCALE),
    img("3.png", BOT_SCALE),
    img("4.png", BOT_SCALE),
    img("5.png", BOT_SCALE),
    img("6.png", BOT_SCALE),
    img("7.png", BOT_SCALE),
]
bot_idle_left_img = pygame.transform.flip(bot_idle_right_img, True, False)
bot_walk_left_imgs = [pygame.transform.flip(s, True, False) for s in bot_walk_right_imgs]

# === ТРИ ДОРОЖКИ ===
GROUND_Y = int(HEIGHT * 0.53)
LANE_OFFSET = 50
lanes = [GROUND_Y - LANE_OFFSET, GROUND_Y, GROUND_Y + LANE_OFFSET]

BOT_Y_OFFSET = 15


# === ПУЛИ ===
class Bullet:
    def __init__(self, x, y, vx, damage):
        self.x = x
        self.y = y
        self.vx = vx
        self.damage = damage
        self.radius = 6
        self.active = True

    def update(self, player):
        if not self.active:
            return

        self.x += self.vx

        if self.x < -50 or self.x > WORLD_WIDTH + 50:
            self.active = False
            return

        if player.alive:
            player_rect = player.current_sprite.get_rect(topleft=(player.x, player.y))
            if player_rect.collidepoint(int(self.x), int(self.y)):
                player.take_damage(self.damage)
                self.active = False

    def draw(self, surf, camera_x):
        if self.active:
            screen_x = int(self.x - camera_x)
            screen_y = int(self.y)
            if -50 < screen_x < WIDTH + 50:
                pygame.draw.circle(surf, (255, 255, 0), (screen_x, screen_y), self.radius)


class Player:
    def __init__(self, hp_max: int, attack: int, defense: int, speed: int):
        self.x = 200
        self.lane_index = 1
        self.y = lanes[self.lane_index]
        self.target_y = self.y

        self.speed_x = max(2, speed)

        self.frame_walk = 0.0
        self.frame_hit = 0.0
        self.walk_speed = 0.22
        self.hit_speed = 0.18

        self.facing_right = True
        self.attacking = False
        self.moving = False

        self.current_sprite = idle_right_img

        self.hp_max = hp_max
        self.hp = self.hp_max
        self.defense = defense
        self.alive = True

        self.hit_registered = False
        self.attack_range = 40
        self.damage = attack

    def reset_for_run(self):
        self.x = 200
        self.lane_index = 1
        self.y = lanes[self.lane_index]
        self.target_y = self.y
        self.hp = self.hp_max
        self.alive = True
        self.attacking = False
        self.moving = False
        self.frame_walk = 0
        self.frame_hit = 0
        self.hit_registered = False
        self.facing_right = True
        self.current_sprite = idle_right_img

    def start_attack(self):
        if not self.attacking and self.alive:
            self.attacking = True
            self.frame_hit = 0.0
            self.hit_registered = False

    def change_lane(self, direction):
        if direction == -1 and self.lane_index > 0:
            self.lane_index -= 1
        elif direction == 1 and self.lane_index < len(lanes) - 1:
            self.lane_index += 1
        self.target_y = lanes[self.lane_index]
        self.y = self.target_y

    def take_damage(self, amount):
        if not self.alive:
            return
        real_damage = max(0, amount - self.defense)
        self.hp -= real_damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def get_center_x(self):
        w = self.current_sprite.get_width()
        return self.x + w / 2

    def update(self, keys, can_control=True):
        if not self.alive:
            self.moving = False
        else:
            self.moving = False

            if can_control and not self.attacking:
                if keys[pygame.K_d]:
                    self.x += self.speed_x
                    self.moving = True
                    self.facing_right = True
                if keys[pygame.K_a]:
                    self.x -= self.speed_x
                    self.moving = True
                    self.facing_right = False

                if self.x < 0:
                    self.x = 0
                max_x = WORLD_WIDTH - self.current_sprite.get_width()
                if self.x > max_x:
                    self.x = max_x

        if self.attacking:
            self.frame_hit += self.hit_speed
            if self.frame_hit >= len(hit_right_imgs):
                self.frame_hit = 0.0
                self.attacking = False

            self.current_sprite = hit_right_imgs[int(self.frame_hit)] if self.facing_right else hit_left_imgs[int(self.frame_hit)]
        else:
            if self.moving:
                self.frame_walk += self.walk_speed
                if self.frame_walk >= len(walk_right_imgs):
                    self.frame_walk = 0.0
                self.current_sprite = walk_right_imgs[int(self.frame_walk)] if self.facing_right else walk_left_imgs[int(self.frame_walk)]
            else:
                self.frame_walk = 0.0
                self.current_sprite = idle_right_img if self.facing_right else idle_left_img

    def draw(self, surf, camera_x):
        surf.blit(self.current_sprite, (self.x - camera_x, self.y))


class Bot:
    def __init__(self, x, lane_index, hp, attack, speed, is_boss=False):
        self.x = x
        self.lane_index = lane_index

        self.ground_y = lanes[self.lane_index] - BOT_Y_OFFSET
        self.y = -100
        self.fall_speed = 8
        self.falling = True

        self.speed_x = max(1.0, float(speed))

        self.frame_walk = 0.0
        self.frame_hit = 0.0
        self.walk_speed = 0.18
        self.hit_speed = 0.20

        self.facing_right = False
        self.attacking = False
        self.moving = False

        self.current_sprite = bot_idle_left_img

        self.hp_max = hp
        self.hp = self.hp_max
        self.alive = True

        self.attack_range = 220
        self.damage = attack
        self.attack_cooldown = 1100
        self.last_attack_time = 0

        self.bullet_speed = 3 + speed * 0.2

        self.is_boss = is_boss
        if self.is_boss:
            self.hp_max = int(self.hp_max * 1.5)
            self.hp = self.hp_max
            self.damage = int(self.damage * 1.3)

    def get_center_x(self):
        w = self.current_sprite.get_width()
        return self.x + w / 2

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def update_ai(self, player: Player, bullets):
        if not self.alive:
            self.attacking = False
            self.moving = False
            return

        if self.falling:
            self.y += self.fall_speed
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.falling = False
            return

        dx = player.get_center_x() - self.get_center_x()
        dist = abs(dx)
        now = pygame.time.get_ticks()

        if self.attacking:
            self.moving = False
            self.frame_hit += self.hit_speed
            if self.frame_hit >= len(bot_walk_right_imgs):
                self.frame_hit = 0.0
                self.attacking = False
        else:
            if dist > 5:
                self.moving = True
                direction = 1 if dx > 0 else -1
                self.x += direction * self.speed_x
                self.facing_right = direction > 0
            else:
                self.moving = False

            if dist < self.attack_range and now - self.last_attack_time > self.attack_cooldown:
                self.attacking = True
                self.frame_hit = 0.0
                self.last_attack_time = now

                direction = 1 if dx > 0 else -1
                vx = direction * self.bullet_speed
                muzzle_x = self.get_center_x() + direction * 10
                muzzle_y = self.y + self.current_sprite.get_height() * 0.45
                bullets.append(Bullet(muzzle_x, muzzle_y, vx, self.damage))

        if self.attacking:
            frame_idx = int(self.frame_hit)
            frame_idx = min(frame_idx, len(bot_walk_right_imgs) - 1)
            self.current_sprite = bot_walk_right_imgs[frame_idx] if self.facing_right else bot_walk_left_imgs[frame_idx]
        else:
            if self.moving:
                self.frame_walk += self.walk_speed
                if self.frame_walk >= len(bot_walk_right_imgs):
                    self.frame_walk = 0.0
                self.current_sprite = bot_walk_right_imgs[int(self.frame_walk)] if self.facing_right else bot_walk_left_imgs[int(self.frame_walk)]
            else:
                self.current_sprite = bot_idle_right_img if self.facing_right else bot_idle_left_img

    def draw(self, surf, camera_x):
        if self.alive:
            surf.blit(self.current_sprite, (self.x - camera_x, self.y))


# ========= БОЙ С ГЛАВАМИ И БД =========

def fight_game(chapter_id: int, character_id: int):
    char = load_character(character_id)
    if char is None:
        hp = 100
        attack = 20
        defense = 0
        speed = 4
        char_name = "Unknown"
    else:
        hp = char["hp"]
        attack = char["attack"]
        defense = char["defense"]
        speed = char["speed"]
        char_name = char["name"]

    progress = load_player_progress(character_id)
    current_chapter = progress["current_chapter"]
    unlocked_chapters = progress["unlocked_chapters"]

    chapter = load_chapter(chapter_id)
    if chapter is None:
        chapter_title = f"Chapter {chapter_id}"
        difficulty = 1
    else:
        chapter_title = chapter["title"]
        difficulty = chapter["difficulty"]

    chapter_bots = load_chapter_bots(chapter_id)
    boss_cfg = load_boss_for_chapter(chapter_id)

    spawn_plan = []
    for cfg in chapter_bots:
        for _ in range(cfg["spawn_count"]):
            spawn_plan.append(cfg)

    TOTAL_BOTS = len(spawn_plan)
    next_spawn_index = 0

    base_spawn_cd = 2200
    spawn_cooldown = max(900, base_spawn_cd - difficulty * 200)

    player = Player(hp_max=hp, attack=attack, defense=defense, speed=speed)
    player.reset_for_run()

    bullets = []
    bots = []
    camera_x = 0.0

    last_spawn_time = 0
    boss_spawned = False

    def spawn_bot_ahead(cfg_bot, is_boss=False):
        lane = random.randint(0, 2)
        min_x = player.x + WIDTH * 0.6
        max_x = min(player.x + WIDTH * 1.5, WORLD_WIDTH - 100)
        if min_x >= WORLD_WIDTH - 100:
            return
        x = random.randint(int(min_x), int(max_x))

        hp_b = cfg_bot["hp"]
        atk_b = cfg_bot["attack"]
        spd_b = cfg_bot["speed"]
        bots.append(Bot(x, lane, hp_b, atk_b, spd_b, is_boss=is_boss))

    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                player.start_attack()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w:
                    player.change_lane(-1)
                if event.key == pygame.K_s:
                    player.change_lane(1)

        keys = pygame.key.get_pressed()
        player.update(keys, can_control=True)

        now = pygame.time.get_ticks()
        alive_regular = [b for b in bots if b.alive and not b.is_boss]

        # спавн по одному (как у тебя было)
        if (
            next_spawn_index < TOTAL_BOTS
            and len(alive_regular) == 0
            and now - last_spawn_time > spawn_cooldown
            and player.x < WORLD_WIDTH - WIDTH
        ):
            cfg_bot = spawn_plan[next_spawn_index]
            spawn_bot_ahead(cfg_bot, is_boss=False)
            next_spawn_index += 1
            last_spawn_time = now

        # босс
        if (
            boss_cfg is not None
            and next_spawn_index >= TOTAL_BOTS
            and not boss_spawned
            and len(alive_regular) == 0
        ):
            boss_spawned = True
            boss_data = {
                "hp": boss_cfg["hp"],
                "attack": boss_cfg["attack"],
                "speed": 2,
            }
            lane = random.randint(0, 2)
            x = WORLD_WIDTH - WIDTH * 0.6
            bots.append(Bot(x, lane, boss_data["hp"], boss_data["attack"], boss_data["speed"], is_boss=True))

        for b in bots:
            b.update_ai(player, bullets)

        if player.attacking and not player.hit_registered:
            for b in bots:
                if not b.alive:
                    continue
                if player.lane_index != b.lane_index:
                    continue
                dx = b.get_center_x() - player.get_center_x()
                if abs(dx) < player.attack_range:
                    if (dx > 0 and player.facing_right) or (dx < 0 and not player.facing_right):
                        b.take_damage(player.damage)
                        player.hit_registered = True
                        break

        for bullet in bullets:
            bullet.update(player)
        bullets = [bullet for bullet in bullets if bullet.active]

        if not player.alive:
            running = False

        level_completed = False
        if boss_cfg is not None:
            if boss_spawned and all(not b.alive for b in bots):
                level_completed = True
        else:
            if player.x >= WORLD_WIDTH - 200:
                level_completed = True

        if level_completed:
            if chapter_id >= current_chapter:
                current_chapter = chapter_id + 1
                unlocked_chapters = max(unlocked_chapters, current_chapter)

            save_player_progress(
                character_id,
                current_chapter=current_chapter,
                unlocked_chapters=unlocked_chapters,
            )
            running = False

        camera_x = player.x - WIDTH * 0.3
        camera_x = max(0, min(camera_x, max(0, WORLD_WIDTH - WIDTH)))

        bg_w = fight_bg.get_width()
        offset = int(camera_x) % bg_w
        screen.blit(fight_bg, (-offset, 0))
        if -offset + bg_w < WIDTH:
            screen.blit(fight_bg, (-offset + bg_w, 0))

        pygame.draw.rect(screen, (80, 0, 0), (20, 20, 200, 12))
        pygame.draw.rect(screen, (0, 200, 0), (20, 20, 200 * (player.hp / player.hp_max), 12))

        text = FONT_MED.render(f"{char_name} | {chapter_title}", True, (220, 220, 220))
        screen.blit(text, (20, 40))

        for b in bots:
            b.draw(screen, camera_x)
        player.draw(screen, camera_x)
        for bullet in bullets:
            bullet.draw(screen, camera_x)

        pygame.display.flip()


# ========= МЕНЮ НАСТРОЕК =========

def settings_menu():
    global volume_level

    BAR_X_REL = 0.150
    BAR_Y_REL = 0.410
    BAR_W_REL = 0.26
    BAR_H_REL = 0.025

    bar_w = int(WIDTH * BAR_W_REL)
    bar_h = int(HEIGHT * BAR_H_REL)
    bar_x = int(WIDTH * BAR_X_REL)
    bar_y = int(HEIGHT * BAR_Y_REL)
    volume_bar_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)

    back_w = int(WIDTH * 0.26)
    back_h = int(HEIGHT * 0.11)
    back_x = (WIDTH - back_w) // 2
    back_y = int(HEIGHT * 0.77)
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)

    dragging = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if volume_bar_rect.collidepoint(event.pos):
                    dragging = True
                    rel_x = (event.pos[0] - volume_bar_rect.x) / volume_bar_rect.w
                    volume_level = max(0.0, min(1.0, rel_x))
                    pygame.mixer.music.set_volume(volume_level)
                elif back_rect.collidepoint(event.pos):
                    return

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False

            if event.type == pygame.MOUSEMOTION and dragging:
                rel_x = (event.pos[0] - volume_bar_rect.x) / volume_bar_rect.w
                volume_level = max(0.0, min(1.0, rel_x))
                pygame.mixer.music.set_volume(volume_level)

        screen.blit(settings_bg, (0, 0))

        active_w = int(volume_bar_rect.w * volume_level)
        active_rect = pygame.Rect(volume_bar_rect.x, volume_bar_rect.y, active_w, volume_bar_rect.h)

        pygame.draw.rect(screen, (0, 200, 255), active_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), volume_bar_rect, 3, border_radius=8)

        pygame.display.flip()
        clock.tick(60)


# ========= ВСПОМОГАТЕЛЬНОЕ: КРАСИВАЯ КНОПКА =========

def draw_bevel_button(surf, rect, fill, text, enabled=True, selected=False):
    # рамка как “металл”
    border = (180, 200, 210)
    inner_border = (80, 90, 110)

    pygame.draw.rect(surf, border, rect, border_radius=14)
    inner = rect.inflate(-8, -8)
    pygame.draw.rect(surf, inner_border, inner, border_radius=12)
    core = inner.inflate(-6, -6)

    # цвет состояния
    pygame.draw.rect(surf, fill, core, border_radius=10)

    # блики
    hl = (255, 255, 255, 70)
    sh = (0, 0, 0, 70)
    pygame.draw.line(surf, (220, 220, 220), (core.left + 6, core.top + 6), (core.right - 6, core.top + 6), 2)
    pygame.draw.line(surf, (30, 30, 30), (core.left + 6, core.bottom - 6), (core.right - 6, core.bottom - 6), 2)

    # текст (2 строки поддержка)
    lines = text.split("\n")
    total_h = len(lines) * (FONT_BTN.get_height() + 4) - 4
    y0 = core.centery - total_h // 2

    txt_col = (255, 255, 255) if enabled else (170, 170, 170)
    for i, line in enumerate(lines):
        t = FONT_BTN.render(line, True, txt_col)
        tr = t.get_rect(center=(core.centerx, y0 + i * (FONT_BTN.get_height() + 4) + FONT_BTN.get_height() // 2))
        surf.blit(t, tr)

    if DEBUG_OUTLINE:
        pygame.draw.rect(surf, (0, 255, 0), rect, 2)


# ========= ВЫБОР ПЕРСОНАЖА =========

def choose_character_menu():
    chars = load_all_characters()
    if not chars:
        return None

    count = len(chars)
    selected_index = 0

    card_w = int(WIDTH * 0.24)
    card_h = int(HEIGHT * 0.45)
    spacing = int(WIDTH * 0.035)

    total_w = card_w * count + spacing * (count - 1)
    start_x = (WIDTH - total_w) // 2
    card_y = int(HEIGHT * 0.25)

    card_rects = []
    for i in range(count):
        x = start_x + i * (card_w + spacing)
        card_rects.append(pygame.Rect(x, card_y, card_w, card_h))

    btn_w = int(WIDTH * 0.24)
    btn_h = int(HEIGHT * 0.1)

    btn_back = pygame.Rect(0, 0, btn_w, btn_h)
    btn_choose = pygame.Rect(0, 0, btn_w, btn_h)

    btn_back.center = (int(WIDTH * 0.30), int(HEIGHT * 0.81))
    btn_choose.center = (int(WIDTH * 0.70), int(HEIGHT * 0.81))

    while True:
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
                    selected_index = (selected_index - 1) % count
                if event.key == pygame.K_RIGHT:
                    selected_index = (selected_index + 1) % count
                if event.key == pygame.K_RETURN:
                    return chars[selected_index]["character_id"]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                for i, r in enumerate(card_rects):
                    if r.collidepoint(mx, my):
                        selected_index = i
                        break

                if btn_choose.collidepoint(mx, my):
                    return chars[selected_index]["character_id"]
                if btn_back.collidepoint(mx, my):
                    return None

        screen.blit(charsel_bg, (0, 0))

        # (стрелка подсказка оставлена как была)
        sel_rect = card_rects[selected_index]
        thickness = int(sel_rect.height * 0.025)
        arrow_length = int(sel_rect.width * 0.47)

        y_center = sel_rect.centery
        offset = -int(WIDTH * 0.06)

        x_tip = sel_rect.left - offset
        tip_len = int(sel_rect.height * 0.10)
        x_line_end = x_tip - tip_len
        x_line_start = x_line_end - (arrow_length - tip_len)

        pygame.draw.line(screen, (0, 255, 0), (x_line_start, y_center), (x_line_end, y_center), thickness)
        pygame.draw.polygon(
            screen, (0, 255, 0),
            [(x_tip, y_center), (x_tip - tip_len, y_center - tip_len // 2), (x_tip - tip_len, y_center + tip_len // 2)]
        )

        pygame.display.flip()
        clock.tick(60)


# ========= ВЫБОР ГЛАВ (ТО ЧТО ТЫ ПРОСИЛА) =========

def choose_chapter_menu(max_unlocked: int, current_chapter: int):
    """
    Серый = заблокировано
    Синий = разблокировано
    Красный = выбранная (только одна)
    Выбор кликом по кнопке, запуск через "ПРОДОЛЖИТЬ"
    """
    # показываем ровно 4 главы
    chapters = CHAPTERS_4[:]
    if not chapters:
        return None

    # если прогресс больше 4 — всё равно считаем, что все 4 открыты
    max_unlocked = max(1, max_unlocked)
    max_unlocked = min(max_unlocked, 999)

    # стартовая выбранная: current_chapter если он открыт, иначе первая открытая
    selected_index = 0
    for i, (cid, _) in enumerate(chapters):
        if cid == current_chapter and cid <= max_unlocked:
            selected_index = i
            break
    else:
        # первая открытая
        for i, (cid, _) in enumerate(chapters):
            if cid <= max_unlocked:
                selected_index = i
                break

    # геометрия как на картинке
    btn_w = int(WIDTH * 0.62)
    btn_h = int(HEIGHT * 0.11)
    gap = int(HEIGHT * 0.03)

    start_y = int(HEIGHT * 0.22)
    center_x = WIDTH // 2

    chapter_rects = []
    for i in range(4):
        r = pygame.Rect(0, 0, btn_w, btn_h)
        r.center = (center_x, start_y + i * (btn_h + gap))
        chapter_rects.append(r)

    bottom_w = int(WIDTH * 0.26)
    bottom_h = int(HEIGHT * 0.10)

    btn_back = pygame.Rect(0, 0, bottom_w, bottom_h)
    btn_continue = pygame.Rect(0, 0, bottom_w, bottom_h)

    btn_back.center = (int(WIDTH * 0.22), int(HEIGHT * 0.85))
    btn_continue.center = (int(WIDTH * 0.78), int(HEIGHT * 0.85))

    # цвета
    BLUE = (10, 90, 200)
    BLUE_DARK = (8, 60, 140)
    RED = (180, 20, 20)
    RED_DARK = (120, 12, 12)
    GRAY = (120, 120, 120)
    GRAY_DARK = (80, 80, 80)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None

                # стрелками можно менять выбранную только по открытым
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    step = -1 if event.key == pygame.K_UP else 1
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
                    # enter = продолжить
                    cid, _ = chapters[selected_index]
                    if cid <= max_unlocked:
                        return cid

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # выбор главы кликом (только если открыта)
                for i, r in enumerate(chapter_rects):
                    if r.collidepoint(mx, my):
                        cid, _ = chapters[i]
                        if cid <= max_unlocked:
                            selected_index = i
                        break

                if btn_back.collidepoint(mx, my):
                    return None

                if btn_continue.collidepoint(mx, my):
                    cid, _ = chapters[selected_index]
                    if cid <= max_unlocked:
                        return cid

        # рисуем фон
        screen.blit(chaptersel_bg, (0, 0))

        # заголовок
        title = "ВЫБОР ГЛАВ"
        t = FONT_BIG.render(title, True, (230, 230, 230))
        tr = t.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.12)))
        screen.blit(t, tr)

        # кнопки глав
        for i, (cid, text) in enumerate(chapters):
            locked = cid > max_unlocked
            selected = (i == selected_index) and not locked

            if locked:
                fill = GRAY
            elif selected:
                fill = RED
            else:
                fill = BLUE

            draw_bevel_button(screen, chapter_rects[i], fill, text, enabled=(not locked), selected=selected)

        # нижние кнопки
        draw_bevel_button(screen, btn_back, BLUE_DARK, "НАЗАД", enabled=True)
        # продолжить активна только если выбранная глава открыта
        sel_cid, _ = chapters[selected_index]
        cont_enabled = sel_cid <= max_unlocked
        draw_bevel_button(screen, btn_continue, BLUE_DARK, "ПРОДОЛЖИТЬ", enabled=cont_enabled)

        pygame.display.flip()
        clock.tick(60)


def select_character_and_chapter():
    character_id = choose_character_menu()
    if character_id is None:
        return None, None

    progress = load_player_progress(character_id)
    max_unlocked = progress["unlocked_chapters"]
    current_chapter = progress["current_chapter"]

    # меню глав с цветами (серый/синий/красный)
    chapter_id = choose_chapter_menu(max_unlocked, current_chapter)
    if chapter_id is None:
        return None, None

    return character_id, chapter_id


# ========= ГЛАВНОЕ МЕНЮ =========

def main_menu():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if handle_global_keys(event):
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.collidepoint(event.pos):
                    return "play"
                if btn_settings.collidepoint(event.pos):
                    return "settings"
                if btn_exit.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

        screen.blit(menu_bg, (0, 0))
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    while True:
        choice = main_menu()

        if choice == "play":
            char_id, chap_id = select_character_and_chapter()
            if char_id is not None and chap_id is not None:
                fight_game(chap_id, char_id)
        elif choice == "settings":
            settings_menu()
