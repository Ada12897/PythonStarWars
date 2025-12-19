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
BASE = r"C:\Users\aknur\OneDrive\Рабочий стол\starwars"  # свой путь

# === ФОН ГЛАВНОГО МЕНЮ ===
MENU_BG_FILE = BASE + r"\menu_main.jpg"
menu_bg_original = pygame.image.load(MENU_BG_FILE)   # БЕЗ convert
BASE_WIDTH, BASE_HEIGHT = menu_bg_original.get_size()

# === ФОН МЕНЮ НАСТРОЕК ===
SETTINGS_BG_FILE = BASE + r"\settings_menu.jpg"
settings_bg_original = pygame.image.load(SETTINGS_BG_FILE)
SETTINGS_BASE_WIDTH, SETTINGS_BASE_HEIGHT = settings_bg_original.get_size()

# === ФОН БОЯ (ТАЙЛОВЫЙ, ДЛЯ БЕСКОНЕЧНОГО СКРОЛЛА) ===
BG_FILE = BASE + r"\background.jpg"
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

clock = pygame.time.Clock()

DEBUG_OUTLINE = False

# === ГРОМКОСТЬ ===
volume_level = 0.7
pygame.mixer.music.set_volume(volume_level)

# === ШРИФТЫ ===
FONT_BIG = pygame.font.SysFont("arial", 36, bold=True)
FONT_MED = pygame.font.SysFont("arial", 24, bold=True)


def draw_center_text(text, font, color, y):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH // 2, y))
    screen.blit(surf, rect)


def recalc_buttons():
    """Пересчитать размеры и позиции кнопок под текущее окно."""
    global btn_play, btn_settings, btn_exit

    btn_w = int(WIDTH * 0.50)
    btn_h = int(HEIGHT * 0.14)

    center_x   = WIDTH // 2
    play_y     = int(HEIGHT * 0.33)
    settings_y = int(HEIGHT * 0.49)
    exit_y     = int(HEIGHT * 0.65)

    btn_play     = pygame.Rect(0, 0, btn_w, btn_h); btn_play.center     = (center_x, play_y)
    btn_settings = pygame.Rect(0, 0, btn_w, btn_h); btn_settings.center = (center_x, settings_y)
    btn_exit     = pygame.Rect(0, 0, btn_w, btn_h); btn_exit.center     = (center_x, exit_y)


recalc_buttons()


def toggle_fullscreen():
    """Переключить fullscreen <-> окно. ALT+ENTER или F11."""
    global fullscreen, screen, WIDTH, HEIGHT, menu_bg, settings_bg, fight_bg, WORLD_WIDTH

    fullscreen = not fullscreen

    if fullscreen:
        info_local = pygame.display.Info()
        WIDTH, HEIGHT = info_local.current_w, info_local.current_h
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

    WORLD_WIDTH = int(WORLD_WIDTH * 0 + WIDTH * 2.5)  # перерасчёт длины мира

    menu_bg = pygame.transform.scale(menu_bg_original, (WIDTH, HEIGHT)).convert()
    settings_bg = pygame.transform.scale(settings_bg_original, (WIDTH, HEIGHT)).convert()
    fight_bg = pygame.transform.scale(fight_bg_original, (WIDTH, HEIGHT)).convert()
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
bot_base_img    = pygame.image.load(BASE + "\\1.png").convert_alpha()

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
        # позиция
        self.x = 200
        self.lane_index = 1
        self.y = lanes[self.lane_index]
        self.target_y = self.y

        # скорость по X берём из speed
        self.speed_x = max(2, speed)

        # анимация
        self.frame_walk = 0.0
        self.frame_hit = 0.0
        self.walk_speed = 0.22
        self.hit_speed = 0.18

        self.facing_right = True
        self.attacking = False
        self.moving = False

        self.current_sprite = idle_right_img

        # характеристики
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
        """Мгновенная смена дорожки."""
        if direction == -1 and self.lane_index > 0:
            self.lane_index -= 1
        elif direction == 1 and self.lane_index < len(lanes) - 1:
            self.lane_index += 1
        self.target_y = lanes[self.lane_index]
        self.y = self.target_y

    def take_damage(self, amount):
        if not self.alive:
            return
        # можно учесть defense, если хочется
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

        # выбор анимации
        if self.attacking:
            self.frame_hit += self.hit_speed
            if self.frame_hit >= len(hit_right_imgs):
                self.frame_hit = 0.0
                self.attacking = False

            if self.facing_right:
                self.current_sprite = hit_right_imgs[int(self.frame_hit)]
            else:
                self.current_sprite = hit_left_imgs[int(self.frame_hit)]
        else:
            if self.moving:
                self.frame_walk += self.walk_speed
                if self.frame_walk >= len(walk_right_imgs):
                    self.frame_walk = 0.0
                if self.facing_right:
                    self.current_sprite = walk_right_imgs[int(self.frame_walk)]
                else:
                    self.current_sprite = walk_left_imgs[int(self.frame_walk)]
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

        # скорость бота по X – из БД
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

        # скорость пули можно привязать к speed
        self.bullet_speed = 3 + speed * 0.2

        self.is_boss = is_boss
        if self.is_boss:
            # небольшой баф, чтобы босс был пожирнее
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

        # падение сверху
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
            # движение
            if dist > 5:
                self.moving = True
                direction = 1 if dx > 0 else -1
                self.x += direction * self.speed_x
                self.facing_right = direction > 0
            else:
                self.moving = False

            # выстрел
            if dist < self.attack_range and now - self.last_attack_time > self.attack_cooldown:
                self.attacking = True
                self.frame_hit = 0.0
                self.last_attack_time = now

                direction = 1 if dx > 0 else -1
                vx = direction * self.bullet_speed
                muzzle_x = self.get_center_x() + direction * 10
                muzzle_y = self.y + self.current_sprite.get_height() * 0.45
                bullets.append(Bullet(muzzle_x, muzzle_y, vx, self.damage))

        # спрайты
        if self.attacking:
            frame_idx = int(self.frame_hit)
            if frame_idx >= len(bot_walk_right_imgs):
                frame_idx = len(bot_walk_right_imgs) - 1
            if self.facing_right:
                self.current_sprite = bot_walk_right_imgs[frame_idx]
            else:
                self.current_sprite = bot_walk_left_imgs[frame_idx]
        else:
            if self.moving:
                self.frame_walk += self.walk_speed
                if self.frame_walk >= len(bot_walk_right_imgs):
                    self.frame_walk = 0.0
                if self.facing_right:
                    self.current_sprite = bot_walk_right_imgs[int(self.frame_walk)]
                else:
                    self.current_sprite = bot_walk_left_imgs[int(self.frame_walk)]
            else:
                self.current_sprite = bot_idle_right_img if self.facing_right else bot_idle_left_img

    def draw(self, surf, camera_x):
        if self.alive:
            surf.blit(self.current_sprite, (self.x - camera_x, self.y))


# ========= ЛОГИКА БОЯ С ГЛАВАМИ И БД =========

def fight_game(chapter_id: int, character_id: int):
    # === 1. Загрузка персонажа из БД ===
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

    # === 2. Загрузка прогресса ===
    progress = load_player_progress(character_id)
    current_chapter = progress["current_chapter"]
    unlocked_chapters = progress["unlocked_chapters"]

    # === 3. Загрузка главы и конфигурации ботов/босса ===
    chapter = load_chapter(chapter_id)
    if chapter is None:
        chapter_title = f"Chapter {chapter_id}"
        difficulty = 1
    else:
        chapter_title = chapter["title"]
        difficulty = chapter["difficulty"]

    chapter_bots = load_chapter_bots(chapter_id)
    boss_cfg = load_boss_for_chapter(chapter_id)

    # План спавна ботов из БД
    spawn_plan = []
    for cfg in chapter_bots:
        for _ in range(cfg["spawn_count"]):
            spawn_plan.append(cfg)

    TOTAL_BOTS = len(spawn_plan)
    next_spawn_index = 0

    # Немного подстраиваем интервал спавна под сложность
    base_spawn_cd = 2200
    spawn_cooldown = max(900, base_spawn_cd - difficulty * 200)

    # === 4. Создаём игрока ===
    player = Player(hp_max=hp, attack=attack, defense=defense, speed=speed)
    player.reset_for_run()

    bullets = []
    bots = []

    camera_x = 0.0

    total_spawned = 0
    last_spawn_time = 0

    boss_spawned = False

    def spawn_bot_ahead(cfg_bot, is_boss=False):
        """Создаём бота впереди игрока, с параметрами из БД."""
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
        alive_bots = [b for b in bots if b.alive]
        alive_regular = [b for b in bots if b.alive and not b.is_boss]
        alive_bosses = [b for b in bots if b.alive and b.is_boss]

        # === СПАВН ОБЫЧНЫХ БОТОВ: строго по плану, по одному ===
        if (next_spawn_index < TOTAL_BOTS and
                len(alive_regular) == 0 and
                now - last_spawn_time > spawn_cooldown and
                player.x < WORLD_WIDTH - WIDTH):
            cfg_bot = spawn_plan[next_spawn_index]
            spawn_bot_ahead(cfg_bot, is_boss=False)
            next_spawn_index += 1
            total_spawned += 1
            last_spawn_time = now

        # === СПАВН БОССА, если он есть ===
        if (boss_cfg is not None
                and next_spawn_index >= TOTAL_BOTS
                and not boss_spawned
                and len(alive_regular) == 0):
            # создаём босса в конце уровня
            boss_spawned = True
            boss_data = {
                "hp": boss_cfg["hp"],
                "attack": boss_cfg["attack"],
                "speed": 2,  # можешь добавить поле speed в таблицу bosses, пока фикс
            }
            # Ставим босса ближе к концу карты
            lane = random.randint(0, 2)
            x = WORLD_WIDTH - WIDTH * 0.6
            bots.append(Bot(x, lane, boss_data["hp"], boss_data["attack"], boss_data["speed"], is_boss=True))

        # обновление ботов
        for b in bots:
            b.update_ai(player, bullets)

        # атака игрока мечом
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

        # пули
        for bullet in bullets:
            bullet.update(player)
        bullets = [bullet for bullet in bullets if bullet.active]

        # === ПРОВЕРКА ПРОИГРЫША / ПОБЕДЫ ===
        if not player.alive:
            # проигрыш – просто выходим из боя (прогресс не меняем)
            running = False

        level_completed = False
        if boss_cfg is not None:
            # если есть босс – победа, когда все боты (включая босса) мертвы
            if boss_spawned and all(not b.alive for b in bots):
                level_completed = True
        else:
            # если босса нет – победа по достижению конца мира
            if player.x >= WORLD_WIDTH - 200:
                level_completed = True

        if level_completed:
            # обновляем прогресс: если это самая дальняя глава – открываем следующую
            if chapter_id >= current_chapter:
                current_chapter = chapter_id + 1
                unlocked_chapters = max(unlocked_chapters, current_chapter)

            save_player_progress(
                character_id,
                current_chapter=current_chapter,
                unlocked_chapters=unlocked_chapters,
            )
            running = False

        # камера
        camera_x = player.x - WIDTH * 0.3
        if camera_x < 0:
            camera_x = 0
        max_cam = max(0, WORLD_WIDTH - WIDTH)
        if camera_x > max_cam:
            camera_x = max_cam

        # фон (тайл)
        bg_w = fight_bg.get_width()
        offset = int(camera_x) % bg_w
        screen.blit(fight_bg, (-offset, 0))
        if -offset + bg_w < WIDTH:
            screen.blit(fight_bg, (-offset + bg_w, 0))

        # UI
        # полоска ХП
        pygame.draw.rect(screen, (80, 0, 0), (20, 20, 200, 12))
        pygame.draw.rect(screen, (0, 200, 0),
                         (20, 20, 200 * (player.hp / player.hp_max), 12))

        # инфа о главе/персе
        text = FONT_MED.render(f"{char_name} | {chapter_title}", True, (220, 220, 220))
        screen.blit(text, (20, 40))

        # дистанция до конца
        dist_left = max(0, int(WORLD_WIDTH - player.x))
        text2 = FONT_MED.render(f"DIST: {dist_left}", True, (200, 200, 200))
        screen.blit(text2, (WIDTH - 200, 20))

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
        active_rect = pygame.Rect(volume_bar_rect.x,
                                  volume_bar_rect.y,
                                  active_w,
                                  volume_bar_rect.h)

        pygame.draw.rect(screen, (0, 200, 255), active_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), volume_bar_rect, 3, border_radius=8)

        if DEBUG_OUTLINE:
            pygame.draw.rect(screen, (255, 0, 0), back_rect, 2)

        pygame.display.flip()
        clock.tick(60)


# ========= ВЫБОР ПЕРСОНАЖА / ГЛАВЫ =========

def choose_character_menu():
    """Меню выбора персонажа из таблицы characters."""
    chars = load_all_characters()
    if not chars:
        # если в БД никого нет – просто возвращаем None
        return None

    selected_index = 0

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
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(chars)
                if event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(chars)
                if event.key == pygame.K_RETURN:
                    return chars[selected_index]["character_id"]

        screen.blit(menu_bg, (0, 0))
        draw_center_text("Выбор персонажа", FONT_BIG, (255, 255, 255), int(HEIGHT * 0.18))

        start_y = int(HEIGHT * 0.30)
        step_y = int(HEIGHT * 0.07)

        for i, ch in enumerate(chars):
            name = ch["name"]
            hp = ch["hp"]
            atk = ch["attack"]
            defense = ch["defense"]
            speed = ch["speed"]

            text = f"{name} | HP:{hp} ATK:{atk} DEF:{defense} SPD:{speed}"
            color = (255, 255, 0) if i == selected_index else (230, 230, 230)
            surf = FONT_MED.render(text, True, color)
            rect = surf.get_rect(center=(WIDTH // 2, start_y + i * step_y))
            screen.blit(surf, rect)

        pygame.display.flip()
        clock.tick(60)


def choose_chapter_menu(max_unlocked: int, current_chapter: int):
    """Меню выбора главы до max_unlocked."""
    chapters = load_chapters_upto(max_unlocked)
    if not chapters:
        return None

    # по умолчанию – текущая глава
    selected_index = 0
    for i, ch in enumerate(chapters):
        if ch["chapter_id"] == current_chapter:
            selected_index = i
            break

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
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(chapters)
                if event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(chapters)
                if event.key == pygame.K_RETURN:
                    return chapters[selected_index]["chapter_id"]

        screen.blit(menu_bg, (0, 0))
        draw_center_text("Выбор главы", FONT_BIG, (255, 255, 255), int(HEIGHT * 0.18))

        start_y = int(HEIGHT * 0.30)
        step_y = int(HEIGHT * 0.07)

        for i, ch in enumerate(chapters):
            title = ch["title"]
            diff = ch["difficulty"]
            cid = ch["chapter_id"]

            text = f"{cid}. {title} (сложность {diff})"
            color = (255, 255, 0) if i == selected_index else (230, 230, 230)
            surf = FONT_MED.render(text, True, color)
            rect = surf.get_rect(center=(WIDTH // 2, start_y + i * step_y))
            screen.blit(surf, rect)

        pygame.display.flip()
        clock.tick(60)


def select_character_and_chapter():
    """Общий флоу: выбор персонажа -> прогресс -> выбор главы."""
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


# ========= ГЛАВНОЕ МЕНЮ =========

def main_menu():
    """Главное меню. Возвращает 'play' или 'settings'."""
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

        if DEBUG_OUTLINE:
            pygame.draw.rect(screen, (0, 255, 0), btn_play, 2)
            pygame.draw.rect(screen, (255, 255, 0), btn_settings, 2)
            pygame.draw.rect(screen, (255, 0, 0), btn_exit, 2)

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
