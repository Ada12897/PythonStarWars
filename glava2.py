import pygame
import sys
import random
import os
from db import load_character_stats


# ==========================================================
#  BASE PATH
# ==========================================================
def get_base_dir():
    env = os.environ.get("STARWARS_BASE")
    if env and os.path.isdir(env):
        return env
    return os.path.dirname(os.path.abspath(__file__))

BASE = get_base_dir()

# ==========================================================
#  HELPERS
# ==========================================================
def norm_png(name: str) -> str:
    name = name.strip()
    return name if name.lower().endswith(".png") else name + ".png"

def existing_variants(name: str):
    n = name.strip()
    out = [n, norm_png(n)]
    if "aligned_11" in n:
        out += [n.replace("aligned_11", "aligned_b11"), norm_png(n.replace("aligned_11", "aligned_b11"))]
    if "aligned_b11" in n:
        out += [n.replace("aligned_b11", "aligned_11"), norm_png(n.replace("aligned_b11", "aligned_11"))]
    uniq = []
    for x in out:
        if x not in uniq:
            uniq.append(x)
    return uniq

def pick_file(name: str):
    for v in existing_variants(name):
        p = os.path.join(BASE, v)
        if os.path.isfile(p):
            return p
    return None

def safe_load_image(name: str, fallback_size=(96, 96), log_tag=""):
    path = pick_file(name)
    try:
        if path is None:
            raise FileNotFoundError(name)
        return pygame.image.load(path).convert_alpha()
    except Exception as e:
        print(f"[IMG MISSING] {log_tag or name} -> {e}")
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 0, 255), surf.get_rect(), 3)
        return surf

def bbox_size_after_scale(frames, scale: float):
    mw = mh = 1
    for fr in frames:
        s = pygame.transform.scale_by(fr, scale)
        r = s.get_bounding_rect(min_alpha=1)
        w = r.width if r.width > 0 else s.get_width()
        h = r.height if r.height > 0 else s.get_height()
        mw = max(mw, w)
        mh = max(mh, h)
    return mw, mh

def fit_bottom_center(original, scale: float, canvas_size):
    scaled = pygame.transform.scale_by(original, scale)
    r = scaled.get_bounding_rect(min_alpha=1)
    cropped = scaled.subsurface(r).copy() if (r.width > 0 and r.height > 0) else scaled.copy()
    cw, ch = canvas_size
    canvas = pygame.Surface((cw, ch), pygame.SRCALPHA)
    x = (cw - cropped.get_width()) // 2
    y = ch - cropped.get_height()
    canvas.blit(cropped, (x, y))
    return canvas

def sprite_bbox_h(img):
    r = img.get_bounding_rect(min_alpha=1)
    return r.height if r.height > 0 else img.get_height()

def wrap_text(font, text, max_width):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w) if cur else w
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def speaker_color(name):
    if name == "Командование":
        return (0, 255, 160)
    if name == "Джедай":
        return (0, 220, 255)
    if name == "ГГ":
        return (255, 255, 0)
    if name == "Граф Дуку":
        return (255, 160, 80)
    return (255, 255, 255)

def clamp(v, a, b):
    return max(a, min(v, b))

def fade_transition(screen, clock, WIDTH, HEIGHT, draw_world_fn, mid_action_fn=None, fade_ms=300):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill((0, 0, 0))

    # fade out
    t0 = pygame.time.get_ticks()
    while True:
        now = pygame.time.get_ticks()
        k = (now - t0) / max(1, fade_ms)
        if k >= 1.0:
            k = 1.0
        draw_world_fn()
        overlay.set_alpha(int(255 * k))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        if k >= 1.0:
            break

    if mid_action_fn:
        mid_action_fn()

    # fade in
    t0 = pygame.time.get_ticks()
    while True:
        now = pygame.time.get_ticks()
        k = (now - t0) / max(1, fade_ms)
        if k >= 1.0:
            k = 1.0
        draw_world_fn()
        overlay.set_alpha(int(255 * (1.0 - k)))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        if k >= 1.0:
            break

# ==========================================================
#  DIALOGS
# ==========================================================
INTRO_DIALOG = [
    ("Командование", "Геонозис. Заводы дроидов работают без остановки."),
    ("Джедай", "Держи линии. Руби тех, кто подходит близко."),
    ("ГГ", "Принял. Начинаю зачистку."),
    ("Командование", "A/D — движение, W/S — дорожка, ЛКМ — удар. SPACE — далее.")
]
WAVE2_DIALOG = [
    ("Командование", "Они подтянули охрану. Волна будет плотнее."),
    ("ГГ", "Пусть идут.")
]
BOSS_DIALOG = [
    ("Командование", "Внимание: на поле боя появился лидер сепаратистов."),
    ("Граф Дуку", "Твоя решимость впечатляет. Но этого недостаточно."),
    ("ГГ", "Проверим.")
]

# ==========================================================
#  CHAR SELECT
# ==========================================================
def resolve_character_key(character_id):
    if character_id in (1, "1", "anakin", "АНАКИН", "Энакин", "энакин"):
        return "anakin"
    if character_id in (2, "2", "rey", "REY", "Рей", "рей"):
        return "rey"
    if character_id in (3, "3", "bultar", "BULTAR", "Бултар", "бултар"):
        return "bultar"
    return "anakin"

def character_filenames(char_key):
    if char_key == "anakin":
        return (["aligned_a0"],
                ["aligned_a1", "aligned_a2", "aligned_a3", "aligned_a4"],
                ["hit1", "hit2", "hit3", "hit4", "hit5", "hit6", "hit7"])
    if char_key == "rey":
        return (["ray1"],
                ["ray2", "ray3", "ray4", "ray5", "ray6", "ray7", "ray8"],
                ["ray_1", "ray_2", "ray_3", "ray_4"])
    return (["bultar_attack_1"],
            ["aligned_b2", "aligned_b3", "aligned_b6", "aligned_11"],
            ["bultar_attack_2", "bultar_attack_3", "bultar_attack_4", "bultar_attack_5"])

# ==========================================================
#  FX / DROPS
# ==========================================================
class DustParticle:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-2.0, 2.0)
        self.vy = random.uniform(-4.0, -1.0)
        self.g = 0.22
        self.life = random.randint(18, 32)
        self.size = random.randint(2, 4)

    def update(self):
        self.vy += self.g
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surf, camera_x, WIDTH, HEIGHT):
        if self.life <= 0:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y)
        if -30 < sx < WIDTH + 30 and -30 < sy < HEIGHT + 30:
            pygame.draw.rect(surf, (220, 190, 90), (sx, sy, self.size, self.size))

    @property
    def alive(self):
        return self.life > 0

class HealthDrop:
    def __init__(self, x, y, heal_amount=18):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-1.2, 1.2)
        self.vy = random.uniform(-3.8, -2.0)
        self.g = 0.25
        self.radius = 9
        self.heal_amount = heal_amount
        self.active = True
        self.life_ms = 12000
        self.spawn_time = pygame.time.get_ticks()

    def update(self, lanes):
        if not self.active:
            return
        self.vy += self.g
        self.x += self.vx
        self.y += self.vy
        ground_y = lanes[1] + 8
        if self.y > ground_y:
            self.y = ground_y
            self.vy *= -0.35
            self.vx *= 0.85
        if pygame.time.get_ticks() - self.spawn_time > self.life_ms:
            self.active = False

    def try_pickup(self, player):
        if not self.active or not player.alive:
            return False
        px = player.get_center_x()
        py = player.y + player.current_sprite.get_height() * 0.55
        dx = (self.x - px)
        dy = (self.y - py)
        if (dx * dx + dy * dy) <= (48 * 48):
            player.hp = min(player.hp_max, player.hp + self.heal_amount)
            self.active = False
            return True
        return False

    def draw(self, surf, camera_x):
        if not self.active:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y)
        t = pygame.time.get_ticks() - self.spawn_time
        if self.life_ms - t < 1500:
            if (pygame.time.get_ticks() // 120) % 2 == 0:
                return
        pygame.draw.circle(surf, (0, 255, 120), (sx, sy), self.radius)
        pygame.draw.circle(surf, (0, 120, 60), (sx, sy), self.radius, 2)

def spawn_death_effects(x, y, particles, drops):
    for _ in range(18):
        particles.append(DustParticle(x, y))
    if random.random() < 0.70:
        drops.append(HealthDrop(x, y, heal_amount=18))
    if random.random() < 0.18:
        drops.append(HealthDrop(x + random.randint(-12, 12), y, heal_amount=12))

# ==========================================================
#  BULLETS
# ==========================================================
class Bullet:
    def __init__(self, x, y, vx, damage, lane_index, WORLD_WIDTH):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.damage = int(damage)
        self.radius = 6
        self.active = True
        self.lane_index = lane_index
        self.WORLD_WIDTH = WORLD_WIDTH

    def update(self, player):
        if not self.active:
            return
        self.x += self.vx
        if self.x < -80 or self.x > self.WORLD_WIDTH + 80:
            self.active = False
            return
        if player.alive and player.lane_index == self.lane_index:
            player_rect = player.current_sprite.get_rect(topleft=(player.x, player.y))
            if player_rect.collidepoint(int(self.x), int(self.y)):
                player.take_damage(self.damage)
                self.active = False

    def draw(self, surf, camera_x, WIDTH):
        if not self.active:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y)
        if -60 < sx < WIDTH + 60:
            pygame.draw.circle(surf, (255, 255, 0), (sx, sy), self.radius)

# ==========================================================
#  ENTITIES
# ==========================================================
class Player:
    def __init__(self, WORLD_WIDTH, lanes, PLAYER_Y_OFFSET,
                 idle_right_img, idle_left_img, walk_right_imgs, walk_left_imgs,
                 hit_right_imgs, hit_left_imgs):
        self.WORLD_WIDTH = WORLD_WIDTH
        self.lanes = lanes
        self.PLAYER_Y_OFFSET = PLAYER_Y_OFFSET

        self.idle_right_img = idle_right_img
        self.idle_left_img = idle_left_img
        self.walk_right_imgs = walk_right_imgs
        self.walk_left_imgs = walk_left_imgs
        self.hit_right_imgs = hit_right_imgs
        self.hit_left_imgs = hit_left_imgs

        self.x = 200
        self.lane_index = 1
        self.y = lanes[self.lane_index] + PLAYER_Y_OFFSET

        self.speed_x = 4
        self.hp_max = 140
        self.hp = self.hp_max
        self.damage = 24
        self.defense = 2

        self.frame_walk = 0.0
        self.frame_hit = 0.0
        self.walk_speed = 0.12
        self.hit_speed = 0.22

        self.facing_right = True
        self.attacking = False
        self.moving = False
        self.current_sprite = self.idle_right_img
        self.alive = True

        self.hit_registered = False
        self.attack_range = 55

    def reset_to_start(self):
        self.x = 200
        self.lane_index = 1
        self.y = self.lanes[self.lane_index] + self.PLAYER_Y_OFFSET
        self.attacking = False
        self.moving = False
        self.frame_walk = 0.0
        self.frame_hit = 0.0
        self.hit_registered = False
        self.facing_right = True
        self.current_sprite = self.idle_right_img

    def reset_full(self):
        self.reset_to_start()
        self.hp = self.hp_max
        self.alive = True

    def start_attack(self):
        if self.alive and not self.attacking:
            self.attacking = True
            self.frame_hit = 0.0
            self.hit_registered = False

    def change_lane(self, direction):
        if direction == -1 and self.lane_index > 0:
            self.lane_index -= 1
        elif direction == 1 and self.lane_index < 2:
            self.lane_index += 1
        self.y = self.lanes[self.lane_index] + self.PLAYER_Y_OFFSET

    def get_center_x(self):
        return self.x + self.current_sprite.get_width() / 2

    def take_damage(self, amount):
        if not self.alive:
            return
        real = max(1, int(amount) - self.defense)
        self.hp -= real
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

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
                self.x = max(0, min(self.x, self.WORLD_WIDTH - self.current_sprite.get_width()))

        if self.attacking:
            self.frame_hit += self.hit_speed
            hit_list = self.hit_right_imgs if self.facing_right else self.hit_left_imgs
            idx = int(self.frame_hit)
            if idx >= len(hit_list):
                self.frame_hit = 0.0
                self.attacking = False
                idx = 0
            self.current_sprite = hit_list[idx]
        else:
            if self.moving:
                self.frame_walk += self.walk_speed
                walk_list = self.walk_right_imgs if self.facing_right else self.walk_left_imgs
                idx = int(self.frame_walk) % len(walk_list)
                self.current_sprite = walk_list[idx]
            else:
                self.frame_walk = 0.0
                self.current_sprite = self.idle_right_img if self.facing_right else self.idle_left_img

    def draw(self, surf, camera_x):
        surf.blit(self.current_sprite, (self.x - camera_x, self.y))

class Bot:
    def __init__(self, x, lane_index, hp, damage, speed,
                 WORLD_WIDTH, lanes, BOT_Y_OFFSET,
                 bot_walk_right_imgs, bot_walk_left_imgs, bot_idle_left_img):
        self.x = float(x)
        self.lane_index = lane_index
        self.WORLD_WIDTH = WORLD_WIDTH
        self.lanes = lanes
        self.BOT_Y_OFFSET = BOT_Y_OFFSET

        self.ground_y = lanes[self.lane_index] + BOT_Y_OFFSET
        self.y = -140
        self.fall_speed = random.randint(10, 14)
        self.falling = True

        self.speed_x = float(speed)
        self.hp = int(hp)
        self.damage = int(damage)
        self.alive = True

        # идут НА игрока
        self.chase_stop_dist = 60
        self.attack_range = 360

        self.attack_cooldown = 1050
        self.last_attack_time = 0
        self.bullet_speed = 5.2

        self.frame_walk = 0.0
        self.walk_speed = 0.18
        self.facing_right = False

        self.bot_walk_right_imgs = bot_walk_right_imgs
        self.bot_walk_left_imgs = bot_walk_left_imgs
        self.current_sprite = bot_idle_left_img

        self.death_fx_done = False
        self.flash_until = 0

    def get_center_x(self):
        return self.x + self.current_sprite.get_width() / 2

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp -= int(amount)
        self.flash_until = pygame.time.get_ticks() + 180
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def update_ai(self, player: Player, bullets):
        if not self.alive:
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

        # движение НА игрока
        if dist > self.chase_stop_dist:
            move_dir = 1 if dx > 0 else -1
            self.x += move_dir * self.speed_x
            self.facing_right = move_dir > 0

        # стрельба только если смотрит на игрока
        if (player.lane_index == self.lane_index) and (dist < self.attack_range):
            want_dir = 1 if dx > 0 else -1
            want_face = want_dir > 0
            if self.facing_right == want_face:
                if now - self.last_attack_time > self.attack_cooldown:
                    self.last_attack_time = now
                    vx = want_dir * self.bullet_speed
                    muzzle_x = self.get_center_x() + want_dir * 10
                    muzzle_y = self.y + self.current_sprite.get_height() * 0.45
                    bullets.append(Bullet(muzzle_x, muzzle_y, vx, self.damage, self.lane_index, self.WORLD_WIDTH))

        self.frame_walk += self.walk_speed
        idx = int(self.frame_walk) % len(self.bot_walk_right_imgs)
        self.current_sprite = self.bot_walk_right_imgs[idx] if self.facing_right else self.bot_walk_left_imgs[idx]
        self.x = max(0, min(self.x, self.WORLD_WIDTH - self.current_sprite.get_width()))

    def draw(self, surf, camera_x):
        if not self.alive:
            return
        now = pygame.time.get_ticks()
        if now < self.flash_until:
            if (now // 70) % 2 == 0:
                return
        surf.blit(self.current_sprite, (self.x - camera_x, self.y))

class BossDooku:
    def __init__(self, x, lane_index, WORLD_WIDTH, lanes, BOSS_Y_OFFSET,
                 idle_right, idle_left, walk_right, walk_left, hit_right, hit_left):
        self.x = float(x)
        self.lane_index = lane_index
        self.WORLD_WIDTH = WORLD_WIDTH
        self.lanes = lanes
        self.BOSS_Y_OFFSET = BOSS_Y_OFFSET

        # НЕ показывать сверху на диалоге
        self.y = -220
        self.fall_speed = 14
        self.falling = True

        # баланс
        self.hp_max = 240
        self.hp = self.hp_max
        self.alive = True

        self.base_speed = 2.0
        self.dash_speed = 2.8

        self.damage = 9
        self.attack_range = 78
        self.attack_cooldown = 1050
        self.last_attack_time = 0

        self.combo_left = 0
        self.combo_gap_ms = 220
        self.next_combo_time = 0

        self.brain_cd = 420
        self.next_brain = 0
        self.mode = "stalk"
        self.mode_until = 0

        self.lane_change_cd = 820
        self.last_lane_change = 0

        self.facing_right = False
        self.attacking = False
        self.moving = False

        self.frame_walk = 0.0
        self.walk_speed = 0.12

        self.frame_hit = 0.0
        self.hit_speed = 0.16

        self.idle_right = idle_right
        self.idle_left = idle_left
        self.walk_right = walk_right
        self.walk_left = walk_left
        self.hit_right = hit_right
        self.hit_left = hit_left
        self.current_sprite = idle_left

        # можно скрывать на диалоге
        self.visible = True

    def _ground_y(self):
        return self.lanes[self.lane_index] + self.BOSS_Y_OFFSET

    def place_on_ground_now(self):
        self.falling = False
        self.y = self._ground_y()

    def get_center_x(self):
        return self.x + self.current_sprite.get_width() / 2

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp -= int(amount)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def _pick_mode(self, now, player):
        dx = player.get_center_x() - self.get_center_x()
        dist = abs(dx)
        r = random.random()
        if dist > 340:
            self.mode = "dash" if r < 0.25 else "stalk"
            self.mode_until = now + random.randint(600, 900)
        elif dist > 200:
            self.mode = "stalk"
            self.mode_until = now + random.randint(650, 980)
        else:
            self.mode = "stalk" if r < 0.85 else "dash"
            self.mode_until = now + random.randint(520, 800)

    def update_ai(self, player: Player):
        if not self.alive:
            return

        now = pygame.time.get_ticks()

        if self.falling:
            self.y += self.fall_speed
            if self.y >= self._ground_y():
                self.y = self._ground_y()
                self.falling = False
            return

        if now >= self.next_brain:
            self.next_brain = now + self.brain_cd
            if now >= self.mode_until:
                self._pick_mode(now, player)

        dx = player.get_center_x() - self.get_center_x()
        dist = abs(dx)

        if (not self.attacking) and (now - self.last_lane_change >= self.lane_change_cd):
            self.last_lane_change = now
            r = random.random()
            if dist > 240 and r < 0.55:
                target_lane = player.lane_index
            else:
                target_lane = self.lane_index
            if target_lane != self.lane_index:
                self.lane_index = target_lane
                self.y = self._ground_y()

        self.moving = False
        if self.mode == "stalk":
            keep = 135
            if dist > keep:
                direction = 1 if dx > 0 else -1
                self.x += direction * self.base_speed
                self.facing_right = direction > 0
                self.moving = True
        elif self.mode == "dash":
            if dist > 80:
                direction = 1 if dx > 0 else -1
                self.x += direction * self.dash_speed
                self.facing_right = direction > 0
                self.moving = True

        can_hit_lane = (player.lane_index == self.lane_index)
        if can_hit_lane and dist <= self.attack_range:
            if self.combo_left > 0 and now >= self.next_combo_time:
                player.take_damage(self.damage)
                self.combo_left -= 1
                self.next_combo_time = now + self.combo_gap_ms
                self.attacking = True
                self.frame_hit = 0.0
                self.last_attack_time = now
            elif (now - self.last_attack_time >= self.attack_cooldown) and (self.combo_left == 0):
                self.last_attack_time = now
                self.combo_left = random.choice([1, 2])
                self.next_combo_time = now

        if self.attacking:
            self.frame_hit += self.hit_speed
            hit_list = self.hit_right if self.facing_right else self.hit_left
            idx = int(self.frame_hit)
            if idx >= len(hit_list):
                self.frame_hit = 0.0
                self.attacking = (self.combo_left > 0)
                idx = 0
            self.current_sprite = hit_list[idx]
        else:
            if self.moving:
                self.frame_walk += self.walk_speed
                walk_list = self.walk_right if self.facing_right else self.walk_left
                idx = int(self.frame_walk) % len(walk_list)
                self.current_sprite = walk_list[idx]
            else:
                self.frame_walk = 0.0
                self.current_sprite = self.idle_right if self.facing_right else self.idle_left

        LEFT_SAFE = 140
        RIGHT_SAFE = self.WORLD_WIDTH - 260
        self.x = max(LEFT_SAFE, min(self.x, RIGHT_SAFE))
        self.y = self._ground_y()

    def draw(self, surf, camera_x):
        if (not self.alive) or (not self.visible):
            return
        surf.blit(self.current_sprite, (self.x - camera_x, self.y))

# ==========================================================
#  UI
# ==========================================================
def draw_dialog_panel(surf, speaker, full_text, visible_chars, anim, WIDTH, HEIGHT,
                      FONT_DIALOG, FONT_DIALOG_HINT, FONT_DIALOG_NAME):
    if not full_text:
        return
    bar_h = int(HEIGHT * 0.24)
    target_y = int(HEIGHT * 0.08)
    start_y = -bar_h
    anim = max(0.0, min(1.0, anim))
    bar_y = start_y + (target_y - start_y) * anim

    rect = pygame.Rect(18, bar_y, WIDTH - 36, bar_h)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((0, 0, 0, 190))
    surf.blit(panel, rect.topleft)

    pygame.draw.rect(surf, (0, 200, 255), rect, 2)
    inner = rect.inflate(-6, -6)
    pygame.draw.rect(surf, (40, 40, 80), inner, 2)

    x = rect.x + 16
    y = rect.y + 12
    if speaker:
        name = FONT_DIALOG_NAME.render(speaker + ":", True, speaker_color(speaker))
        surf.blit(name, (x, y))
        y += name.get_height() + 8

    visible_text = full_text[:max(0, min(int(visible_chars), len(full_text)))]
    for line in wrap_text(FONT_DIALOG, visible_text, rect.width - 32)[:5]:
        surf.blit(FONT_DIALOG.render(line, True, (255, 255, 255)), (x, y))
        y += FONT_DIALOG.get_height() + 4

    hint = FONT_DIALOG_HINT.render("SPACE — далее", True, (200, 200, 200))
    surf.blit(hint, (rect.right - hint.get_width() - 14, rect.bottom - hint.get_height() - 10))

def draw_player_hp(screen, player, FONT_SMALL):
    pygame.draw.rect(screen, (80, 0, 0), (20, 20, 240, 14))
    w = int(240 * (player.hp / max(1, player.hp_max)))
    pygame.draw.rect(screen, (0, 220, 0), (20, 20, w, 14))
    t = FONT_SMALL.render(f"HP: {player.hp}/{player.hp_max}", True, (230, 230, 230))
    screen.blit(t, (20, 40))

def draw_boss_hp(screen, boss, FONT_SMALL, WIDTH, HEIGHT, name="ГРАФ ДУКУ"):
    bar_w = int(WIDTH * 0.70)
    bar_h = 16
    x = (WIDTH - bar_w) // 2
    y = HEIGHT - bar_h - 18
    pygame.draw.rect(screen, (60, 0, 0), (x, y, bar_w, bar_h))
    w = int(bar_w * (boss.hp / max(1, boss.hp_max)))
    pygame.draw.rect(screen, (255, 160, 80), (x, y, w, bar_h))
    pygame.draw.rect(screen, (220, 220, 220), (x, y, bar_w, bar_h), 2)
    title = FONT_SMALL.render(name, True, (255, 200, 130))
    screen.blit(title, (x, y - 18))

# ==========================================================
#  CHAPTER 2
# ==========================================================
def run_chapter(character_id=None):
    pygame.init()
    pygame.mixer.init()

    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Star Wars — Chapter 2 (Geonosis)")
    clock = pygame.time.Clock()

    bg = safe_load_image("background2", fallback_size=(WIDTH, HEIGHT), log_tag="background2.png")
    fight_bg = pygame.transform.scale(bg, (WIDTH, HEIGHT)).convert()

    # звук меча
    try:
        sfx_path = os.path.join(BASE, "metal-sound-fighting-game-87507.mp3")
        SWORD_SFX = pygame.mixer.Sound(sfx_path)
    except:
        SWORD_SFX = None
    SWORD_CHANNEL = pygame.mixer.Channel(1)

    # шрифты
    FONT_BIG = pygame.font.SysFont("arial", 56, bold=True)
    FONT_MED = pygame.font.SysFont("arial", 28, bold=True)
    FONT_SMALL = pygame.font.SysFont("arial", 20, bold=True)
    try:
        fnt = os.path.join(BASE, "PressStart2P-Regular.ttf")
        FONT_DIALOG = pygame.font.Font(fnt, 20)
        FONT_DIALOG_HINT = pygame.font.Font(fnt, 14)
        FONT_DIALOG_NAME = pygame.font.Font(fnt, 16)
    except:
        FONT_DIALOG = pygame.font.SysFont("consolas", 20, bold=True)
        FONT_DIALOG_HINT = pygame.font.SysFont("consolas", 14, bold=True)
        FONT_DIALOG_NAME = pygame.font.SysFont("consolas", 16, bold=True)

    # ----------------------------------------------------------
    # ДОРОЖКИ (подняты на 1 уровень)
    # ----------------------------------------------------------
    GROUND_Y = int(HEIGHT * 0.83)
    LANE_OFFSET = 55
    SHIFT_UP = LANE_OFFSET
    lanes = [
        (GROUND_Y - LANE_OFFSET) - SHIFT_UP,
        (GROUND_Y) - SHIFT_UP,
        (GROUND_Y + LANE_OFFSET) - SHIFT_UP
    ]
    FOOT_PAD = 4

    # ========= PLAYER LOAD
    char_key = resolve_character_key(character_id)
    idle_names, walk_names, hit_names = character_filenames(char_key)

    idle_raw = safe_load_image(idle_names[0], log_tag=f"{char_key}_idle")
    walk_raw = [safe_load_image(n, log_tag=f"{char_key}_walk") for n in walk_names]
    hit_raw  = [safe_load_image(n, log_tag=f"{char_key}_hit") for n in hit_names]

    BASE_SCALE = 0.75
    an_idle_names, _, _ = character_filenames("anakin")
    anakin_idle_raw = safe_load_image(an_idle_names[0], log_tag="anakin_idle_ref")
    target_h = max(1, int(sprite_bbox_h(anakin_idle_raw) * BASE_SCALE))

    if char_key == "bultar":
        b_h = max(1, sprite_bbox_h(idle_raw))
        PLAYER_SCALE = (target_h / b_h) * 1.05
    else:
        PLAYER_SCALE = BASE_SCALE

    PLAYER_CANVAS = bbox_size_after_scale([idle_raw] + walk_raw + hit_raw, PLAYER_SCALE)
    idle_right_img = fit_bottom_center(idle_raw, PLAYER_SCALE, PLAYER_CANVAS)
    idle_left_img  = pygame.transform.flip(idle_right_img, True, False)
    walk_right_imgs = [fit_bottom_center(fr, PLAYER_SCALE, PLAYER_CANVAS) for fr in walk_raw]
    walk_left_imgs  = [pygame.transform.flip(fr, True, False) for fr in walk_right_imgs]
    hit_right_imgs = [fit_bottom_center(fr, PLAYER_SCALE, PLAYER_CANVAS) for fr in hit_raw]
    hit_left_imgs  = [pygame.transform.flip(fr, True, False) for fr in hit_right_imgs]
    PLAYER_Y_OFFSET = -idle_right_img.get_height() + FOOT_PAD

    # ========= BOTS (wave1=синие, wave2=фиолетовые)
    def build_bot_pack(names, target_bbox_h):
        raw = [safe_load_image(n, log_tag=f"bot_{n}") for n in names]
        src_h = max(1, sprite_bbox_h(raw[0]))
        scale = (float(target_bbox_h) / float(src_h))
        scale = max(0.2, min(scale, 6.0))
        canvas = bbox_size_after_scale(raw, scale)
        right = [fit_bottom_center(fr, scale, canvas) for fr in raw]
        left = [pygame.transform.flip(fr, True, False) for fr in right]
        y_off = -right[0].get_height() + FOOT_PAD
        return right, left, left[0], y_off

    # эталонная высота бота: игрок (bbox) * 1.35 (как у тебя было)
    player_bbox_h_scaled = max(1, int(sprite_bbox_h(idle_raw) * PLAYER_SCALE))
    ref_target_bbox_h = int(player_bbox_h_scaled * 1.35)

    blue_names   = [f"blue{i}" for i in range(0, 8)]     # нужны blue0.png..blue7.png
    purple_names = [f"purple{i}" for i in range(0, 8)]   # нужны purple0.png..purple7.png

    bot_pack_wave1 = build_bot_pack(blue_names, ref_target_bbox_h)
    bot_pack_wave2 = build_bot_pack(purple_names, ref_target_bbox_h)

    # ========= BOSS DOOKU (размер по bbox относительно эталона)
    dooku_idle_raw = safe_load_image("duku1", log_tag="duku1")
    dooku_walk_raw = [safe_load_image(n, log_tag=n) for n in ["duku_2", "duku_3", "duku_4"]]
    dooku_hit_raw  = [safe_load_image(n, log_tag=n) for n in ["duku2", "duku3", "duku4", "duku5", "duku6"]]

    dooku_bbox_h = max(1, sprite_bbox_h(dooku_idle_raw))
    BOSS_SCALE = clamp((target_h / dooku_bbox_h) * 1.08, 0.35, 1.10)

    DOOKU_CANVAS = bbox_size_after_scale([dooku_idle_raw] + dooku_walk_raw + dooku_hit_raw, BOSS_SCALE)
    dooku_idle_right = fit_bottom_center(dooku_idle_raw, BOSS_SCALE, DOOKU_CANVAS)
    dooku_idle_left  = pygame.transform.flip(dooku_idle_right, True, False)

    walk_frames_right_base = [fit_bottom_center(fr, BOSS_SCALE, DOOKU_CANVAS) for fr in dooku_walk_raw]
    walk_frames_left_base  = [pygame.transform.flip(fr, True, False) for fr in walk_frames_right_base]
    walk_order = [0, 2, 0, 1, 0]
    dooku_walk_right = [walk_frames_right_base[i] for i in walk_order]
    dooku_walk_left  = [walk_frames_left_base[i] for i in walk_order]

    dooku_hit_right = [fit_bottom_center(fr, BOSS_SCALE, DOOKU_CANVAS) for fr in dooku_hit_raw]
    dooku_hit_left  = [pygame.transform.flip(fr, True, False) for fr in dooku_hit_right]
    BOSS_Y_OFFSET = -dooku_idle_right.get_height() + FOOT_PAD

    # ========= WORLD / ENTITIES
    WORLD_WIDTH = int(WIDTH * 12.0)
    player = Player(WORLD_WIDTH, lanes, PLAYER_Y_OFFSET,
                    idle_right_img, idle_left_img,
                    walk_right_imgs, walk_left_imgs,
                    hit_right_imgs, hit_left_imgs)

    # применяем прокачку из БД
    if character_id is not None:
        st = load_character_stats(int(character_id))
        player.hp_max = 140 + int(st.get("hp", 0))
        player.damage = 24 + int(st.get("attack", 0))
    player.reset_full()

    bullets = []
    bots = []
    particles = []
    drops = []

    boss = None
    boss_spawned = False
    boss_visible = False
    camera_x = 0.0

    def extend_world(mult):
        nonlocal WORLD_WIDTH
        WORLD_WIDTH = int(WIDTH * mult)
        player.WORLD_WIDTH = WORLD_WIDTH

    def teleport_to_start(clear_enemies=True):
        player.reset_to_start()
        bullets.clear()
        if clear_enemies:
            bots.clear()

    # волны
    waves = [
        {"kills_required": 10, "spawn_min": 2, "spawn_max": 3, "bot_hp": 70, "bot_dmg": 7, "bot_spd": 2.20},
        {"kills_required": 14, "spawn_min": 2, "spawn_max": 3, "bot_hp": 82, "bot_dmg": 8, "bot_spd": 2.35},
    ]
    wave_idx = 0
    killed_in_wave = 0
    total_kills_needed = waves[wave_idx]["kills_required"]
    spawn_cooldown = 1100
    last_spawn = 0

    def safe_spawn_x():
        cfg_min = player.x + WIDTH * 0.55
        cfg_max = player.x + WIDTH * 1.25
        min_x = min(cfg_min, WORLD_WIDTH - 320)
        max_x = min(cfg_max, WORLD_WIDTH - 260)
        if min_x > max_x:
            min_x = max(220, player.x + WIDTH * 0.4)
            max_x = min(WORLD_WIDTH - 260, player.x + WIDTH * 0.9)
        min_x = max(min_x, 220)
        max_x = min(max_x, WORLD_WIDTH - 260)
        if min_x > max_x:
            min_x = max(220, WORLD_WIDTH - 520)
            max_x = WORLD_WIDTH - 320
        return int(min_x), int(max_x)

    # ✅ строго: wave1=синие, wave2=фиолетовые
    def spawn_pack():
        cfg = waves[wave_idx]

        if wave_idx == 0:
            cur_right, cur_left, cur_idle, cur_yoff = bot_pack_wave1  # СИНИЕ
        else:
            cur_right, cur_left, cur_idle, cur_yoff = bot_pack_wave2  # ФИОЛЕТОВЫЕ

        n = random.randint(cfg["spawn_min"], cfg["spawn_max"])
        min_x, max_x = safe_spawn_x()

        lanes_pool = [0, 1, 2]
        random.shuffle(lanes_pool)
        last_lane = None

        for i in range(n):
            if i < len(lanes_pool):
                lane = lanes_pool[i]
            else:
                choices = [0, 1, 2]
                if last_lane in choices and len(choices) > 1:
                    choices.remove(last_lane)
                lane = random.choice(choices)
            last_lane = lane

            x = random.randint(min_x, max_x)

            bots.append(
                Bot(x, lane, hp=cfg["bot_hp"], damage=cfg["bot_dmg"], speed=cfg["bot_spd"],
                    WORLD_WIDTH=WORLD_WIDTH, lanes=lanes, BOT_Y_OFFSET=cur_yoff,
                    bot_walk_right_imgs=cur_right, bot_walk_left_imgs=cur_left,
                    bot_idle_left_img=cur_idle)
            )

    # ========= DIALOG STATE
    dialog_entries = INTRO_DIALOG[:]
    dialog_index = 0
    dialog_active = True
    dialog_visible = 0.0
    dialog_speed = 60.0
    dialog_anim = 0.0

    def draw_world_only():
        nonlocal camera_x
        camera_x = player.x - WIDTH * 0.35
        camera_x = max(0, min(camera_x, max(0, WORLD_WIDTH - WIDTH)))

        bg_w = fight_bg.get_width()
        offset = int(camera_x) % bg_w
        screen.blit(fight_bg, (-offset, 0))
        if -offset + bg_w < WIDTH:
            screen.blit(fight_bg, (-offset + bg_w, 0))

        for p in particles:
            p.draw(screen, camera_x, WIDTH, HEIGHT)
        for d in drops:
            d.draw(screen, camera_x)

        for b in bots:
            b.draw(screen, camera_x)

        if boss_spawned and boss is not None:
            boss.draw(screen, camera_x)

        player.draw(screen, camera_x)

        for bullet in bullets:
            bullet.draw(screen, camera_x, WIDTH)

        draw_player_hp(screen, player, FONT_SMALL)
        if boss_spawned and boss is not None and boss.alive and boss_visible:
            draw_boss_hp(screen, boss, FONT_SMALL, WIDTH, HEIGHT, name="ГРАФ ДУКУ")

    running = True
    won = False

    while running:
        dt = clock.tick(60)
        dt_sec = dt / 1000.0

        if dialog_active and 0 <= dialog_index < len(dialog_entries):
            cur_speaker, cur_text = dialog_entries[dialog_index]
        else:
            cur_speaker, cur_text = "", ""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    won = False

                if dialog_active and event.key == pygame.K_SPACE:
                    if dialog_visible < len(cur_text):
                        dialog_visible = float(len(cur_text))
                    else:
                        dialog_index += 1
                        if dialog_index >= len(dialog_entries):
                            dialog_active = False
                            if boss_spawned and boss is not None:
                                boss_visible = True
                                boss.visible = True
                        else:
                            dialog_visible = 0.0
                    continue

                if not dialog_active:
                    if event.key == pygame.K_w:
                        player.change_lane(-1)
                    if event.key == pygame.K_s:
                        player.change_lane(1)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not dialog_active:
                    player.start_attack()

        keys = pygame.key.get_pressed()
        player.update(keys, can_control=(not dialog_active))

        if dialog_active and cur_text:
            dialog_visible += dialog_speed * dt_sec
            dialog_visible = min(dialog_visible, float(len(cur_text)))
            if dialog_anim < 1.0:
                dialog_anim += dt_sec * 4.0
                dialog_anim = min(1.0, dialog_anim)

        now = pygame.time.get_ticks()

        # spawn bots
        if (not dialog_active) and (not boss_spawned):
            alive_bots = [b for b in bots if b.alive]
            if killed_in_wave < total_kills_needed:
                if len(alive_bots) == 0:
                    spawn_pack()
                    last_spawn = now
                elif now - last_spawn > spawn_cooldown and len(alive_bots) <= 1:
                    spawn_pack()
                    last_spawn = now

        # AI / combat
        if not dialog_active:
            for b in bots:
                b.update_ai(player, bullets)

            if boss_spawned and boss is not None and boss.alive and boss_visible:
                boss.update_ai(player)

            # sword hit
            if player.attacking and not player.hit_registered:
                targets = [b for b in bots if b.alive]
                if boss_spawned and boss is not None and boss.alive and boss_visible:
                    targets.append(boss)

                for t in targets:
                    if t.lane_index != player.lane_index:
                        continue
                    dx = (t.get_center_x() - player.get_center_x())
                    if abs(dx) <= player.attack_range:
                        if (dx > 0 and player.facing_right) or (dx < 0 and not player.facing_right):
                            t.take_damage(player.damage)
                            player.hit_registered = True
                            if SWORD_SFX is not None:
                                SWORD_CHANNEL.play(SWORD_SFX)

                            if isinstance(t, Bot) and (not t.alive) and (not t.death_fx_done):
                                t.death_fx_done = True
                                spawn_death_effects(
                                    t.get_center_x(),
                                    t.y + t.current_sprite.get_height() * 0.65,
                                    particles,
                                    drops
                                )
                                killed_in_wave += 1
                            break

            for bullet in bullets:
                bullet.update(player)
            bullets[:] = [b for b in bullets if b.active]

        # FX/drops
        for p in particles:
            p.update()
        particles[:] = [p for p in particles if p.alive]

        for d in drops:
            d.update(lanes)
            d.try_pickup(player)
        drops[:] = [d for d in drops if d.active]

        # death / win
        if not player.alive:
            running = False
            won = False

        if boss_spawned and boss is not None and (not boss.alive):
            running = False
            won = True

        # ==== TELEPORT TRANSITIONS ====
        if (not dialog_active) and (not boss_spawned):
            if wave_idx == 0 and killed_in_wave >= waves[0]["kills_required"]:
                def mid():
                    extend_world(14.0)
                    teleport_to_start(clear_enemies=True)

                fade_transition(screen, clock, WIDTH, HEIGHT, draw_world_only, mid_action_fn=mid, fade_ms=280)

                wave_idx = 1
                killed_in_wave = 0
                total_kills_needed = waves[wave_idx]["kills_required"]
                spawn_cooldown = 1050

                dialog_entries = WAVE2_DIALOG[:]
                dialog_index = 0
                dialog_active = True
                dialog_visible = 0.0
                dialog_anim = 0.0

            elif wave_idx == 1 and killed_in_wave >= waves[1]["kills_required"]:
                def mid():
                    extend_world(16.0)
                    teleport_to_start(clear_enemies=True)

                fade_transition(screen, clock, WIDTH, HEIGHT, draw_world_only, mid_action_fn=mid, fade_ms=280)

                boss_spawned = True
                boss_visible = False

                boss = BossDooku(
                    520, 1, WORLD_WIDTH, lanes, BOSS_Y_OFFSET,
                    dooku_idle_right, dooku_idle_left,
                    dooku_walk_right, dooku_walk_left,
                    dooku_hit_right, dooku_hit_left
                )

                boss.place_on_ground_now()
                boss.visible = False

                dialog_entries = BOSS_DIALOG[:]
                dialog_index = 0
                dialog_active = True
                dialog_visible = 0.0
                dialog_anim = 0.0

        # camera
        camera_x = player.x - WIDTH * 0.35
        camera_x = max(0, min(camera_x, max(0, WORLD_WIDTH - WIDTH)))

        # draw bg infinite
        bg_w = fight_bg.get_width()
        offset = int(camera_x) % bg_w
        screen.blit(fight_bg, (-offset, 0))
        if -offset + bg_w < WIDTH:
            screen.blit(fight_bg, (-offset + bg_w, 0))

        for p in particles:
            p.draw(screen, camera_x, WIDTH, HEIGHT)
        for d in drops:
            d.draw(screen, camera_x)

        for b in bots:
            b.draw(screen, camera_x)

        if boss_spawned and boss is not None:
            boss.draw(screen, camera_x)

        player.draw(screen, camera_x)

        for bullet in bullets:
            bullet.draw(screen, camera_x, WIDTH)

        draw_player_hp(screen, player, FONT_SMALL)

        if boss_spawned and boss is not None and boss.alive and boss_visible:
            draw_boss_hp(screen, boss, FONT_SMALL, WIDTH, HEIGHT, name="ГРАФ ДУКУ")
        else:
            t = FONT_SMALL.render(
                f"ВОЛНА {wave_idx+1}/2  |  УБИТО: {killed_in_wave}/{total_kills_needed}",
                True, (220, 220, 220)
            )
            screen.blit(t, (20, 64))

        if dialog_active and cur_text:
            draw_dialog_panel(screen, cur_speaker, cur_text, dialog_visible, dialog_anim,
                              WIDTH, HEIGHT, FONT_DIALOG, FONT_DIALOG_HINT, FONT_DIALOG_NAME)

        pygame.display.flip()

    # ✅ отрисуем последний кадр ещё раз, чтобы фон для попапов был правильный
    draw_world_only()
    pygame.display.flip()
    bg_frame = screen.copy()

    # ✅ final.py сможет показать попапы (level up / win / lose)
    return won, bg_frame
