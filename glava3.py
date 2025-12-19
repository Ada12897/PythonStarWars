import pygame
import sys
import random
import os

from db import load_character_stats, load_chapter_bots


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
#  FIXED COUNTS / SIZES (как во 2 главе)
# ==========================================================
MAX_ELEVATOR_BOTS = 20      # ✅ всегда 20
BOT_HEIGHT_MULT   = 1.35    # ✅ как во 2 главе
BASE_SCALE_PLAYER = 0.75    # ✅ как во 2 главе

# ==========================================================
#  HELPERS
# ==========================================================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def norm_png(name: str) -> str:
    name = name.strip()
    return name if name.lower().endswith(".png") else name + ".png"

def existing_variants(name: str):
    n = name.strip()
    out = [n, norm_png(n)]
    # aligned_11 vs aligned_b11 fallback
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
    if name == "Император Палпатин":
        return (210, 160, 255)
    return (255, 255, 255)

def fade_transition(screen, clock, WIDTH, HEIGHT, draw_world_fn, mid_action_fn=None, fade_ms=420):
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
INTRO_DIALOG_3 = [
    ("Командование", "Лифт застрял между уровнями. Сепаратисты пытаются прорваться внутрь."),
    ("Джедай", "Держи позиции. Они будут падать сверху — из технического люка."),
    ("ГГ", "Понял. Перекрываю все дорожки."),
    ("Командование", "A/D — движение, W/S — дорожка, ЛКМ — удар. SPACE — далее.")
]

BOSS_DIALOG_3 = [
    ("Командование", "…Сигнал тревоги. В лифтовом отсеке фиксируется мощная энергия."),
    ("Император Палпатин", "Ты думаешь, что победил? Это была лишь разминка."),
    ("ГГ", "Тогда покажи, на что способен."),
]

# ==========================================================
#  CHAR SELECT
# ==========================================================
def resolve_character_key(character_id):
    if character_id in (1, "1", "anakin", "АНАКИН", "Энакин", "энакин"):
        return "anakin"
    if character_id in (2, "2", "rey", "REY", "Рей", "рей"):
        return "rey"
    if character_id in (3, "3", "bultar", "BULTAR", "Бултар", "булtar", "бултар"):
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

        self.x = 200  # ✅ как во 2 главе
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
                 bot_walk_right_imgs, bot_walk_left_imgs, bot_idle_left_img,
                 spawn_y=-140, fall_speed=None):
        self.x = float(x)
        self.lane_index = lane_index
        self.WORLD_WIDTH = WORLD_WIDTH
        self.lanes = lanes
        self.BOT_Y_OFFSET = BOT_Y_OFFSET

        self.ground_y = lanes[self.lane_index] + BOT_Y_OFFSET
        self.y = float(spawn_y)
        self.fall_speed = int(fall_speed) if fall_speed is not None else random.randint(10, 14)
        self.falling = True

        self.speed_x = float(speed)
        self.hp = int(hp)
        self.damage = int(damage)
        self.alive = True

        self.chase_stop_dist = 60
        self.attack_range = 360

        self.attack_cooldown = 1150
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

        if dist > self.chase_stop_dist:
            move_dir = 1 if dx > 0 else -1
            self.x += move_dir * self.speed_x
            self.facing_right = move_dir > 0

        # стрельба только если реально повернут к игроку
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

class BossPalpatine:
    def __init__(self, x, lane_index, WORLD_WIDTH, lanes, BOSS_Y_OFFSET,
                 idle_right, idle_left, walk_right, walk_left, atk_right, atk_left):
        self.x = float(x)
        self.lane_index = lane_index
        self.WORLD_WIDTH = WORLD_WIDTH
        self.lanes = lanes
        self.BOSS_Y_OFFSET = BOSS_Y_OFFSET

        self.y = -220
        self.fall_speed = 14
        self.falling = True

        self.hp_max = 260
        self.hp = self.hp_max
        self.alive = True

        self.base_speed = 2.4
        self.dash_speed = 3.2

        self.damage = 10
        self.attack_range = 82
        self.attack_cooldown = 980
        self.last_attack_time = 0

        self.combo_left = 0
        self.combo_gap_ms = 210
        self.next_combo_time = 0

        self.brain_cd = 380
        self.next_brain = 0
        self.mode = "stalk"
        self.mode_until = 0

        self.lane_change_cd = 760
        self.last_lane_change = 0

        self.facing_right = False
        self.attacking = False
        self.moving = False

        self.frame_walk = 0.0
        self.walk_speed = 0.13

        self.frame_hit = 0.0
        self.hit_speed = 0.18

        self.idle_right = idle_right
        self.idle_left = idle_left
        self.walk_right = walk_right
        self.walk_left = walk_left
        self.atk_right = atk_right
        self.atk_left = atk_left
        self.current_sprite = idle_left

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
        if dist > 360:
            self.mode = "dash" if r < 0.55 else "stalk"
            self.mode_until = now + random.randint(520, 820)
        elif dist > 200:
            self.mode = "stalk" if r < 0.75 else "dash"
            self.mode_until = now + random.randint(620, 980)
        else:
            self.mode = "stalk" if r < 0.70 else "dash"
            self.mode_until = now + random.randint(520, 780)

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

        # смена дорожки
        if (not self.attacking) and (now - self.last_lane_change >= self.lane_change_cd):
            self.last_lane_change = now
            r = random.random()
            if dist > 260 and r < 0.70:
                target_lane = player.lane_index
            else:
                target_lane = self.lane_index if r < 0.75 else random.choice([0, 1, 2])
            if target_lane != self.lane_index:
                self.lane_index = target_lane
                self.y = self._ground_y()

        self.moving = False

        # движение
        if self.mode == "stalk":
            keep = 125
            if dist > keep:
                direction = 1 if dx > 0 else -1
                self.x += direction * self.base_speed
                self.facing_right = direction > 0
                self.moving = True
        elif self.mode == "dash":
            if dist > 78:
                direction = 1 if dx > 0 else -1
                self.x += direction * self.dash_speed
                self.facing_right = direction > 0
                self.moving = True

        # атака
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
                self.combo_left = random.choice([1, 2, 2])
                self.next_combo_time = now

        # анимации
        if self.attacking:
            self.frame_hit += self.hit_speed
            hit_list = self.atk_right if self.facing_right else self.atk_left
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

def draw_boss_hp(screen, boss, FONT_SMALL, WIDTH, HEIGHT, name="ИМПЕРАТОР ПАЛПАТИН"):
    bar_w = int(WIDTH * 0.70)
    bar_h = 16
    x = (WIDTH - bar_w) // 2
    y = HEIGHT - bar_h - 18
    pygame.draw.rect(screen, (60, 0, 0), (x, y, bar_w, bar_h))
    w = int(bar_w * (boss.hp / max(1, boss.hp_max)))
    pygame.draw.rect(screen, (170, 120, 255), (x, y, w, bar_h))
    pygame.draw.rect(screen, (220, 220, 220), (x, y, bar_w, bar_h), 2)
    title = FONT_SMALL.render(name, True, (220, 200, 255))
    screen.blit(title, (x, y - 18))


# ==========================================================
#  CHAPTER 3 (ELEVATOR -> BOSS) — DB BOTS + 4 TYPES
# ==========================================================
def run_chapter(character_id=None):
    pygame.init()
    pygame.mixer.init()

    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Star Wars — Chapter 3 (Elevator + Boss)")
    clock = pygame.time.Clock()

    # ======================================================
    #  AUDIO
    # ======================================================
    try:
        sfx_path = os.path.join(BASE, "metal-sound-fighting-game-87507.mp3")
        SWORD_SFX = pygame.mixer.Sound(sfx_path)
    except:
        SWORD_SFX = None
    SWORD_CHANNEL = pygame.mixer.Channel(1)

    # ======================================================
    #  FONTS
    # ======================================================
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

    # ======================================================
    #  LANES - elevator / fight
    # ======================================================
    # лифт
    GROUND_Y_E = int(HEIGHT * 0.87)
    LANE_OFFSET_E = int(HEIGHT * 0.050)
    lanes_elevator = [GROUND_Y_E - LANE_OFFSET_E, GROUND_Y_E, GROUND_Y_E + LANE_OFFSET_E]

    # бой
    GROUND_Y_F = int(HEIGHT * 0.83)
    LANE_OFFSET_F = 55
    lanes_fight = [GROUND_Y_F - LANE_OFFSET_F, GROUND_Y_F, GROUND_Y_F + LANE_OFFSET_F]

    FOOT_PAD = 4

    # ======================================================
    #  PLAYER SPRITES (РАЗМЕР = как во 2 главе)
    # ======================================================
    char_key = resolve_character_key(character_id)
    idle_names, walk_names, hit_names = character_filenames(char_key)

    idle_raw = safe_load_image(idle_names[0], log_tag=f"{char_key}_idle")
    walk_raw = [safe_load_image(n, log_tag=f"{char_key}_walk") for n in walk_names]
    hit_raw  = [safe_load_image(n, log_tag=f"{char_key}_hit") for n in hit_names]

    an_idle_names, _, _ = character_filenames("anakin")
    anakin_idle_raw = safe_load_image(an_idle_names[0], log_tag="anakin_idle_ref")
    target_h = max(1, int(sprite_bbox_h(anakin_idle_raw) * BASE_SCALE_PLAYER))

    if char_key == "bultar":
        b_h = max(1, sprite_bbox_h(idle_raw))
        PLAYER_SCALE = (target_h / b_h) * 1.05
    else:
        PLAYER_SCALE = BASE_SCALE_PLAYER

    PLAYER_CANVAS = bbox_size_after_scale([idle_raw] + walk_raw + hit_raw, PLAYER_SCALE)
    idle_right_img = fit_bottom_center(idle_raw, PLAYER_SCALE, PLAYER_CANVAS)
    idle_left_img  = pygame.transform.flip(idle_right_img, True, False)
    walk_right_imgs = [fit_bottom_center(fr, PLAYER_SCALE, PLAYER_CANVAS) for fr in walk_raw]
    walk_left_imgs  = [pygame.transform.flip(fr, True, False) for fr in walk_right_imgs]
    hit_right_imgs  = [fit_bottom_center(fr, PLAYER_SCALE, PLAYER_CANVAS) for fr in hit_raw]
    hit_left_imgs   = [pygame.transform.flip(fr, True, False) for fr in hit_right_imgs]

    PLAYER_Y_OFFSET = -idle_right_img.get_height() + FOOT_PAD

    # ======================================================
    #  BOT SPRITES: 4 TYPES (red / yellow / blue / purple)
    #  РАЗМЕР = как во 2 главе (player_bbox * 1.35)
    # ======================================================
    def build_bot_set(prefix: str, player_bbox_h_px: float, height_mult: float):
        bot_raw = [safe_load_image(f"{prefix}{i}", log_tag=f"{prefix}{i}") for i in range(0, 8)]

        bot_h0 = max(1, sprite_bbox_h(bot_raw[0]))
        target_bot_h = max(1, int(player_bbox_h_px * float(height_mult)))
        BOT_SCALE = target_bot_h / bot_h0
        BOT_SCALE = clamp(BOT_SCALE, 0.20, 6.00)

        BOT_CANVAS = bbox_size_after_scale(bot_raw, BOT_SCALE)
        bot_walk_right_imgs = [fit_bottom_center(fr, BOT_SCALE, BOT_CANVAS) for fr in bot_raw]
        bot_walk_left_imgs = [pygame.transform.flip(fr, True, False) for fr in bot_walk_right_imgs]
        bot_idle_left_img = bot_walk_left_imgs[0]

        BOT_Y_OFFSET = -bot_walk_right_imgs[0].get_height() + FOOT_PAD
        return bot_walk_right_imgs, bot_walk_left_imgs, bot_idle_left_img, BOT_Y_OFFSET

    player_bbox_px = float(sprite_bbox_h(idle_raw)) * float(PLAYER_SCALE)

    bot_sets = {
        "red":    build_bot_set("red",    player_bbox_px, BOT_HEIGHT_MULT),
        "yellow": build_bot_set("yellow", player_bbox_px, BOT_HEIGHT_MULT),
        "blue":   build_bot_set("blue",   player_bbox_px, BOT_HEIGHT_MULT),
        "purple": build_bot_set("purple", player_bbox_px, BOT_HEIGHT_MULT),
    }

    def get_bot_set_safe(color_key: str):
        return bot_sets.get(color_key, bot_sets["red"])

    # ======================================================
    #  DB -> spawn plan (какие боты и сколько) + FIX TO 20
    # ======================================================
    def parse_db_bots(chapter_id: int):
        try:
            rows = load_chapter_bots(int(chapter_id))
        except Exception as e:
            print("[DB] load_chapter_bots error:", e)
            rows = []

        parsed = []
        for r in rows:
            if isinstance(r, dict):
                name = str(r.get("name", "BOT"))
                hp = int(r.get("hp", r.get("bot_hp", 80)))
                dmg = int(r.get("attack", r.get("damage", r.get("bot_dmg", 7))))
                spd = float(r.get("speed", r.get("bot_spd", 2.25)))
                cnt = int(r.get("spawn_count", r.get("count", 1)))
            else:
                t = list(r)
                name = str(t[1]) if len(t) > 1 else "BOT"
                hp = int(t[2]) if len(t) > 2 else 80
                dmg = int(t[3]) if len(t) > 3 else 7
                spd = float(t[4]) if len(t) > 4 else 2.25
                cnt = int(t[5]) if len(t) > 5 else 1
            parsed.append({"name": name, "hp": hp, "dmg": dmg, "spd": spd, "count": max(0, cnt)})
        return parsed

    def name_to_color(name: str):
        n = (name or "").lower()

        if "b2" in n:
            return "red"
        if "b1" in n:
            return "yellow"
        if "ig-100" in n:
            return "blue"
        if "ig-250" in n:
            return "purple"

        if "super" in n and "droid" in n:
            return "red"
        if "magna" in n and ("100" in n or "ig100" in n):
            return "blue"
        if "magna" in n and ("250" in n or "ig250" in n):
            return "purple"

        return "yellow"

    db_bots = parse_db_bots(3)

    if not db_bots:
        db_bots = [
            {"name": "B2 супербоевой дроид", "hp": 90,  "dmg": 8,  "spd": 2.25, "count": 1},
            {"name": "B1 боевой дроид",      "hp": 70,  "dmg": 7,  "spd": 2.15, "count": 1},
            {"name": "IG-100 MagnaGuard",    "hp": 95,  "dmg": 9,  "spd": 2.35, "count": 1},
            {"name": "IG-250 MagnaGuard",    "hp": 110, "dmg": 10, "spd": 2.30, "count": 1},
        ]

    spawn_queue = []
    for b in db_bots:
        for _ in range(int(b.get("count", 1))):
            spawn_queue.append({
                "name": b["name"],
                "hp": int(b["hp"]),
                "dmg": int(b["dmg"]),
                "spd": float(b["spd"]),
            })

    # ✅ FIX: всегда делаем ровно 20
    if not spawn_queue:
        # на всякий случай
        spawn_queue = [{"name": "B1 боевой дроид", "hp": 70, "dmg": 7, "spd": 2.15}]

    random.shuffle(spawn_queue)

    if len(spawn_queue) > MAX_ELEVATOR_BOTS:
        spawn_queue = spawn_queue[:MAX_ELEVATOR_BOTS]
    elif len(spawn_queue) < MAX_ELEVATOR_BOTS:
        base = spawn_queue[:]
        while len(spawn_queue) < MAX_ELEVATOR_BOTS:
            spawn_queue.append(random.choice(base))

    TOTAL_BOTS = len(spawn_queue)  # == 20

    # ======================================================
    #  ELEVATOR BACKGROUND (phase 1)
    # ======================================================
    BG_FILE = "elevator_bg.png"
    TILE_FILE = "center_tile.png"

    bg_src = safe_load_image(BG_FILE, fallback_size=(1536, 1024), log_tag=BG_FILE).convert()
    tile_src = safe_load_image(TILE_FILE, fallback_size=(925, 1536), log_tag=TILE_FILE).convert()

    BG_W0, BG_H0 = bg_src.get_width(), bg_src.get_height()

    def scale_to_screen(img):
        return pygame.transform.smoothscale(img, (WIDTH, HEIGHT))

    def scaled_rect_from_src(r: pygame.Rect):
        sx = WIDTH / BG_W0
        sy = HEIGHT / BG_H0
        return pygame.Rect(int(r.x * sx), int(r.y * sy), int(r.w * sx), int(r.h * sy))

    bg_elevator = scale_to_screen(bg_src)

    WALL_RECT_SRC = pygame.Rect(316, 105, 905, 700)
    INSET_SRC = 8

    wall_dst = scaled_rect_from_src(WALL_RECT_SRC)
    sx = WIDTH / BG_W0
    sy = HEIGHT / BG_H0
    inset_x = int(INSET_SRC * sx)
    inset_y = int(INSET_SRC * sy)
    wall_inner = wall_dst.inflate(-2 * inset_x, -2 * inset_y)

    tile_scaled_w = wall_inner.width
    tile_scaled_h = int(tile_src.get_height() * (tile_scaled_w / tile_src.get_width()))
    tile = pygame.transform.smoothscale(tile_src, (tile_scaled_w, tile_scaled_h))

    scroll_y = 0.0
    SCROLL_SPEED_START = 500.0
    scroll_speed = SCROLL_SPEED_START

    def draw_elevator(scroll_offset_px: float):
        screen.blit(bg_elevator, (0, 0))
        h = tile.get_height()
        if h > 1:
            off = int(scroll_offset_px) % h
            y1 = wall_inner.y - off
            screen.blit(tile, (wall_inner.x, y1))
            screen.blit(tile, (wall_inner.x, y1 + h))

        top_h = wall_inner.y
        if top_h > 0:
            screen.blit(bg_elevator, (0, 0), area=pygame.Rect(0, 0, WIDTH, top_h))

        bottom_y = wall_inner.bottom
        if bottom_y < HEIGHT:
            screen.blit(bg_elevator, (0, bottom_y), area=pygame.Rect(0, bottom_y, WIDTH, HEIGHT - bottom_y))

        left_w = wall_inner.x
        if left_w > 0:
            screen.blit(bg_elevator, (0, wall_inner.y), area=pygame.Rect(0, wall_inner.y, left_w, wall_inner.height))

        right_x = wall_inner.right
        if right_x < WIDTH:
            screen.blit(bg_elevator, (right_x, wall_inner.y),
                        area=pygame.Rect(right_x, wall_inner.y, WIDTH - right_x, wall_inner.height))

    # ======================================================
    #  BOSS BACKGROUND (phase 2)
    # ======================================================
    bg3_raw = safe_load_image("background3", fallback_size=(WIDTH, HEIGHT), log_tag="background3.png")
    fight_bg3 = pygame.transform.scale(bg3_raw, (WIDTH, HEIGHT)).convert()

    # ======================================================
    #  WORLD / ENTITIES
    # ======================================================
    phase = "elevator"  # elevator -> boss
    WORLD_WIDTH = WIDTH
    camera_x = 0.0

    player = Player(WORLD_WIDTH, lanes_elevator, PLAYER_Y_OFFSET,
                    idle_right_img, idle_left_img,
                    walk_right_imgs, walk_left_imgs,
                    hit_right_imgs, hit_left_imgs)

    # ===== применяем прокачку из БД =====
    if character_id is not None:
        st = load_character_stats(int(character_id))
        player.hp_max = 140 + int(st.get("hp", 0))
        player.damage = 24 + int(st.get("attack", 0))
    player.reset_full()

    bullets = []
    bots = []
    particles = []
    drops = []

    # ======================================================
    #  HOLE (spawn сверху, по центру)
    # ======================================================
    HOLE_DST = pygame.Rect(
        wall_inner.centerx - int(wall_inner.width * 0.20),
        max(8, int(HEIGHT * 0.06)),
        int(wall_inner.width * 0.40),
        int(HEIGHT * 0.07),
    )

    def spawn_from_hole_x():
        return random.randint(HOLE_DST.left + 10, HOLE_DST.right - 10)

    def spawn_from_hole_y():
        return HOLE_DST.bottom - 10

    # ======================================================
    #  SPAWN: по одному (строго 20)
    # ======================================================
    spawn_index = 0
    killed_count = 0

    spawn_cooldown_ms = 900
    last_spawn_time = 0

    def spawn_one_bot_from_queue():
        nonlocal spawn_index
        if spawn_index >= TOTAL_BOTS:
            return

        b = spawn_queue[spawn_index]
        spawn_index += 1

        color = name_to_color(b["name"])
        bot_walk_right_imgs, bot_walk_left_imgs, bot_idle_left_img, BOT_Y_OFFSET = get_bot_set_safe(color)

        lane = random.choice([0, 1, 2])
        x = spawn_from_hole_x()
        spawn_y = spawn_from_hole_y() - random.randint(140, 240)

        bots.append(
            Bot(
                x, lane,
                hp=int(b["hp"]),
                damage=int(b["dmg"]),
                speed=float(b["spd"]),
                WORLD_WIDTH=WORLD_WIDTH,
                lanes=player.lanes,
                BOT_Y_OFFSET=BOT_Y_OFFSET,
                bot_walk_right_imgs=bot_walk_right_imgs,
                bot_walk_left_imgs=bot_walk_left_imgs,
                bot_idle_left_img=bot_idle_left_img,
                spawn_y=spawn_y,
                fall_speed=random.randint(11, 16)
            )
        )

    # ======================================================
    #  BOSS SPRITES (Palpatine)
    # ======================================================
    pal_idle_raw = safe_load_image("b3_1", log_tag="b3_1")
    pal_walk_raw = [safe_load_image(n, log_tag=n) for n in ["b3_2", "b3_3"]]
    pal_atk_raw  = [safe_load_image(n, log_tag=n) for n in ["b3_4", "b3_5"]]

    pal_bbox_h = max(1, sprite_bbox_h(pal_idle_raw))
    BOSS_SCALE = clamp((target_h / pal_bbox_h) * 1.08, 0.35, 1.25)  # ✅ ближе к масштабу во 2 главе

    PAL_CANVAS = bbox_size_after_scale([pal_idle_raw] + pal_walk_raw + pal_atk_raw, BOSS_SCALE)
    pal_idle_right = fit_bottom_center(pal_idle_raw, BOSS_SCALE, PAL_CANVAS)
    pal_idle_left  = pygame.transform.flip(pal_idle_right, True, False)

    walk_base_right = [fit_bottom_center(fr, BOSS_SCALE, PAL_CANVAS) for fr in pal_walk_raw]
    walk_base_left  = [pygame.transform.flip(fr, True, False) for fr in walk_base_right]

    pal_walk_right = [pal_idle_right, walk_base_right[1], walk_base_right[1], walk_base_right[0]]
    pal_walk_left  = [pal_idle_left,  walk_base_left[1],  walk_base_left[1],  walk_base_left[0]]

    pal_atk_right = [fit_bottom_center(fr, BOSS_SCALE, PAL_CANVAS) for fr in pal_atk_raw]
    pal_atk_right = [pal_atk_right[0], pal_atk_right[1], pal_atk_right[1]]
    pal_atk_left  = [pygame.transform.flip(fr, True, False) for fr in pal_atk_right]

    BOSS_Y_OFFSET = -pal_idle_right.get_height() + FOOT_PAD

    boss = None
    boss_spawned = False
    boss_visible = False

    # ======================================================
    #  DIALOG STATE
    # ======================================================
    dialog_entries = INTRO_DIALOG_3[:]
    dialog_index = 0
    dialog_active = True
    dialog_visible = 0.0
    dialog_speed = 60.0
    dialog_anim = 0.0

    # ======================================================
    #  DRAW WORLD for fade (uses current phase)
    # ======================================================
    def draw_world_only():
        nonlocal camera_x

        if phase == "elevator":
            camera_x = 0.0
            draw_elevator(scroll_y)
        else:
            camera_x = player.x - WIDTH * 0.35
            camera_x = max(0, min(camera_x, max(0, player.WORLD_WIDTH - WIDTH)))
            bg_w = fight_bg3.get_width()
            offset = int(camera_x) % bg_w
            screen.blit(fight_bg3, (-offset, 0))
            if -offset + bg_w < WIDTH:
                screen.blit(fight_bg3, (-offset + bg_w, 0))

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

        if phase == "elevator":
            t = FONT_SMALL.render(f"БОТЫ: {killed_count}/{TOTAL_BOTS}", True, (220, 220, 220))
            screen.blit(t, (20, 64))
        else:
            if boss_spawned and boss is not None and boss.alive and boss_visible:
                draw_boss_hp(screen, boss, FONT_SMALL, WIDTH, HEIGHT, name="ИМПЕРАТОР ПАЛПАТИН")

        if dialog_active and 0 <= dialog_index < len(dialog_entries):
            sp, tx = dialog_entries[dialog_index]
            draw_dialog_panel(screen, sp, tx, dialog_visible, dialog_anim,
                              WIDTH, HEIGHT, FONT_DIALOG, FONT_DIALOG_HINT, FONT_DIALOG_NAME)

    # ======================================================
    #  SWITCH TO BOSS PHASE
    # ======================================================
    def enter_boss_phase():
        nonlocal phase, WORLD_WIDTH, boss, boss_spawned, boss_visible
        nonlocal dialog_entries, dialog_index, dialog_active, dialog_visible, dialog_anim

        phase = "boss"

        WORLD_WIDTH = int(WIDTH * 12.0)
        player.WORLD_WIDTH = WORLD_WIDTH
        player.lanes = lanes_fight
        player.reset_to_start()

        bullets.clear()
        bots.clear()
        particles.clear()
        drops.clear()

        boss_spawned = True
        boss_visible = False
        boss = BossPalpatine(
            520, 1, WORLD_WIDTH, player.lanes, BOSS_Y_OFFSET,
            pal_idle_right, pal_idle_left,
            pal_walk_right, pal_walk_left,
            pal_atk_right, pal_atk_left
        )
        boss.place_on_ground_now()
        boss.visible = False

        dialog_entries = BOSS_DIALOG_3[:]
        dialog_index = 0
        dialog_active = True
        dialog_visible = 0.0
        dialog_anim = 0.0

    # ======================================================
    #  MAIN LOOP
    # ======================================================
    won = False
    running = True

    while running:
        dt = clock.tick(60)
        dt_sec = dt / 1000.0
        now = pygame.time.get_ticks()

        if phase == "elevator":
            scroll_y += scroll_speed * dt_sec

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

        # spawn (elevator only, 1 bot at a time)
        if phase == "elevator" and (not dialog_active):
            alive_bots = [b for b in bots if b.alive]
            if spawn_index < TOTAL_BOTS:
                if len(alive_bots) == 0 and (now - last_spawn_time >= spawn_cooldown_ms):
                    spawn_one_bot_from_queue()
                    last_spawn_time = now

        # AI / combat
        if not dialog_active:
            for b in bots:
                b.update_ai(player, bullets)

            if boss_spawned and boss is not None and boss.alive and boss_visible:
                boss.update_ai(player)

            # sword hit
            if player.attacking and not player.hit_registered:
                targets = [t for t in bots if t.alive]
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
                                killed_count += 1
                            break

            for bullet in bullets:
                bullet.update(player)
            bullets[:] = [b for b in bullets if b.active]

        for p in particles:
            p.update()
        particles[:] = [p for p in particles if p.alive]

        for d in drops:
            d.update(player.lanes)
            d.try_pickup(player)
        drops[:] = [d for d in drops if d.active]

        # lose
        if not player.alive:
            running = False
            won = False

        # переход к боссу
        if running and phase == "elevator" and (killed_count >= TOTAL_BOTS):
            def mid():
                enter_boss_phase()
            fade_transition(screen, clock, WIDTH, HEIGHT, draw_world_only, mid_action_fn=mid, fade_ms=520)

        # win
        if boss_spawned and boss is not None and (not boss.alive):
            running = False
            won = True

        # DRAW
        if phase == "elevator":
            camera_x = 0.0
            draw_elevator(scroll_y)
        else:
            camera_x = player.x - WIDTH * 0.35
            camera_x = max(0, min(camera_x, max(0, player.WORLD_WIDTH - WIDTH)))
            bg_w = fight_bg3.get_width()
            offset = int(camera_x) % bg_w
            screen.blit(fight_bg3, (-offset, 0))
            if -offset + bg_w < WIDTH:
                screen.blit(fight_bg3, (-offset + bg_w, 0))

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

        if phase == "elevator":
            t = FONT_SMALL.render(f"БОТЫ: {killed_count}/{TOTAL_BOTS}", True, (220, 220, 220))
            screen.blit(t, (20, 64))
        else:
            if boss_spawned and boss is not None and boss.alive and boss_visible:
                draw_boss_hp(screen, boss, FONT_SMALL, WIDTH, HEIGHT, name="ИМПЕРАТОР ПАЛПАТИН")

        if dialog_active and cur_text:
            draw_dialog_panel(
                screen, cur_speaker, cur_text, dialog_visible, dialog_anim,
                WIDTH, HEIGHT, FONT_DIALOG, FONT_DIALOG_HINT, FONT_DIALOG_NAME
            )

        pygame.display.flip()

    # последний кадр для попапов в final.py
    draw_world_only()
    pygame.display.flip()
    bg_frame = screen.copy()
    return won, bg_frame
