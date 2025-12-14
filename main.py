import pygame
import random
import sys
import math
import json
import os
import asyncio  # Added for Pygbag web support

# Initialize Pygame
pygame.init()
pygame.font.init()

# Constants
WIDTH, HEIGHT = 416, 312  # Increased internal resolution (30% larger world)
SCALE = 2  # Back to 2x scaling for crisp pixels
FPS = 30

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)

# Game States
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_HELP = "help"

# Player constants
ROTATION_SPEED = 4.5
MAX_THRUST = 4.0
THRUST_ACCEL = 0.2
BULLET_SPEED = 7
SHOOT_DELAY = 150
LOOP_DURATION = 800
LOOP_COOLDOWN = 3000  # Reduced from 5000 for more frequent use
LOOP_RADIUS = 40
BOMB_INVINCIBILITY_DURATION = 2000
BOMB_FLASH_DURATION = 300

# AI constants
EMERGENCY_DODGE_RADIUS = 50  # Increased for larger world
PERCEPTION_RADIUS = 150  # Increased for larger world

# Enemy constants
ENEMY_SPAWN_RATE = 50  # Slightly faster spawn for larger world
ENEMY_BULLET_SPEED = 3.0
ENEMY_ROTATION_SPEED = 2.5

# Boss constants
BOSS_SPAWN_SCORE = 500
BOSS_HP = 250  # Increased from 200 for more challenge
BOSS_SPEED = 1.5
BOSS_SIZE = 40

# Stage constants
STAGE_SCORE_INTERVAL = 200
STAGE_TRANSITION_DURATION = 2000

# Other constants
ASTEROID_SPAWN_MARGIN = 20
RESTART_DELAY = 3000
TIME_SCORE_INTERVAL = 10000
TIME_SCORE_AMOUNT = 1

# Particle constants
PARTICLE_LIFETIME = 30
SCREEN_SHAKE_DURATION = 200
SCREEN_SHAKE_INTENSITY = 3


class Player:
    def __init__(self, x, y):
        self.pos = [x, y]
        self.angle = -90.0
        self.thrust = 0.0
        self.weapon_level = 1
        self.hp = 3
        self.max_hp = 3
        self.shield = 0  # Start with no shield for challenge
        self.max_shield = 3
        self.bombs = 2  # Start with 2 bombs instead of 3
        self.max_bombs = 5
        self.invincible_until = 0
        self.is_looping = False
        self.loop_start_time = 0
        self.last_loop_time = -LOOP_COOLDOWN
        self.loop_start_pos = [0, 0]
        self.loop_start_angle = 0

        # Load image
        player_image_orig = pygame.image.load('craft0.png').convert_alpha()
        self.image = pygame.transform.scale(player_image_orig, (30, 30))

    def take_damage(self, amount=1):
        if pygame.time.get_ticks() < self.invincible_until:
            return False

        if self.shield > 0:
            self.shield -= amount
            return False
        else:
            self.hp -= amount
            self.invincible_until = pygame.time.get_ticks() + 1500  # 1.5 seconds invincibility
            return self.hp <= 0

    def heal(self, amount=1):
        self.hp = min(self.hp + amount, self.max_hp)

    def add_shield(self, amount=1):
        self.shield = min(self.shield + amount, self.max_shield)

    def upgrade_weapon(self):
        self.weapon_level = min(self.weapon_level + 1, 3)

    def add_bomb(self):
        self.bombs = min(self.bombs + 1, self.max_bombs)

    def use_bomb(self, current_time):
        if self.bombs > 0:
            self.bombs -= 1
            self.invincible_until = current_time + BOMB_INVINCIBILITY_DURATION
            return True
        return False

    def start_loop(self, current_time):
        if not self.is_looping and current_time - self.last_loop_time > LOOP_COOLDOWN:
            self.is_looping = True
            self.loop_start_time = current_time
            self.last_loop_time = current_time
            self.loop_start_pos = list(self.pos)
            self.loop_start_angle = self.angle
            self.invincible_until = current_time + LOOP_DURATION
            return True
        return False

    def update_loop(self, current_time):
        if not self.is_looping:
            return

        progress = (current_time - self.loop_start_time) / LOOP_DURATION
        if progress >= 1.0:
            self.is_looping = False
            self.angle = self.loop_start_angle
        else:
            self.angle = self.loop_start_angle + progress * 360
            loop_angle_rad = (progress * 2 * math.pi) - (math.pi / 2)
            center_x = self.loop_start_pos[0]
            center_y = self.loop_start_pos[1] - LOOP_RADIUS
            self.pos[0] = center_x + LOOP_RADIUS * math.cos(loop_angle_rad)
            self.pos[1] = center_y + LOOP_RADIUS * math.sin(loop_angle_rad)

    def update_movement(self, keys, ai_enabled, ai_update_func):
        if self.is_looping:
            return

        if ai_enabled:
            ai_update_func()  # Don't pass self - the function already has access to game object
        else:
            if keys[pygame.K_LEFT]:
                self.angle -= ROTATION_SPEED
            if keys[pygame.K_RIGHT]:
                self.angle += ROTATION_SPEED
            if keys[pygame.K_UP]:
                self.thrust = min(self.thrust + THRUST_ACCEL, MAX_THRUST)
            if keys[pygame.K_DOWN]:
                self.thrust = max(self.thrust - THRUST_ACCEL, 0)

        if not ai_enabled and self.thrust > 0:
            self.thrust = max(0, self.thrust - THRUST_ACCEL / 4)

        rad = math.radians(self.angle)
        move_x = self.thrust * math.cos(rad)
        move_y = self.thrust * math.sin(rad)
        self.pos[0] += move_x
        self.pos[1] += move_y

        # Wrap around screen
        if self.pos[0] > WIDTH:
            self.pos[0] = 0
        if self.pos[0] < 0:
            self.pos[0] = WIDTH
        if self.pos[1] > HEIGHT:
            self.pos[1] = 0
        if self.pos[1] < 0:
            self.pos[1] = HEIGHT

        return move_x, move_y

    def shoot(self):
        rad = math.radians(self.angle)
        vel_x = math.cos(rad) * BULLET_SPEED
        vel_y = math.sin(rad) * BULLET_SPEED
        bullets = []

        if self.weapon_level == 1:
            bullets.append(Bullet(self.pos[0], self.pos[1], vel_x, vel_y))
        elif self.weapon_level == 2:
            p_rad = math.radians(self.angle + 90)
            offset_x = math.cos(p_rad) * 5
            offset_y = math.sin(p_rad) * 5
            bullets.append(Bullet(self.pos[0] + offset_x, self.pos[1] + offset_y, vel_x, vel_y))
            bullets.append(Bullet(self.pos[0] - offset_x, self.pos[1] - offset_y, vel_x, vel_y))
        elif self.weapon_level == 3:
            bullets.append(Bullet(self.pos[0], self.pos[1], vel_x, vel_y))
            for angle_diff in [-20, 20]:
                s_rad = math.radians(self.angle + angle_diff)
                s_vel_x = math.cos(s_rad) * BULLET_SPEED
                s_vel_y = math.sin(s_rad) * BULLET_SPEED
                bullets.append(Bullet(self.pos[0], self.pos[1], s_vel_x, s_vel_y))

        return bullets

    def draw(self, surface):
        rotated_image = pygame.transform.rotate(self.image, -self.angle - 90)
        new_rect = rotated_image.get_rect(center=self.pos)

        # Draw invincibility indicator
        if pygame.time.get_ticks() < self.invincible_until:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                surface.blit(rotated_image, new_rect)
        else:
            surface.blit(rotated_image, new_rect)


class Bullet:
    def __init__(self, x, y, vel_x, vel_y):
        self.pos = [x, y]
        self.vel = [vel_x, vel_y]

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        return 0 < self.pos[0] < WIDTH and 0 < self.pos[1] < HEIGHT

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, (self.pos[0], self.pos[1], 3, 3))


class Enemy:
    TIER_COLORS = [RED, YELLOW, BLUE, GREEN, WHITE, GRAY]
    TIER_SPAWN_PROBS = [0.4, 0.3, 0.15, 0.08, 0.05, 0.02]
    LOW_TIER_PROBS = [0.47, 0.35, 0.18]

    def __init__(self, tier, low_tier_only=True):
        self.tier = tier
        self.hp = tier * 2
        self.speed = 1 + tier * 0.5

        # Spawn position
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            self.pos = [random.randint(0, WIDTH), -20]
        elif side == 'bottom':
            self.pos = [random.randint(0, WIDTH), HEIGHT + 20]
        elif side == 'left':
            self.pos = [-20, random.randint(0, HEIGHT)]
        else:
            self.pos = [WIDTH + 20, random.randint(0, HEIGHT)]

        self.angle = math.degrees(math.atan2(HEIGHT/2 - self.pos[1], WIDTH/2 - self.pos[0]))

    def update(self, target_pos):
        # Rotate towards target
        target_dx = target_pos[0] - self.pos[0]
        target_dy = target_pos[1] - self.pos[1]
        target_angle = math.degrees(math.atan2(target_dy, target_dx))
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        turn_amount = min(ENEMY_ROTATION_SPEED, max(-ENEMY_ROTATION_SPEED, angle_diff))
        self.angle += turn_amount

        # Move
        rad = math.radians(self.angle)
        self.pos[0] += self.speed * math.cos(rad)
        self.pos[1] += self.speed * math.sin(rad)

        return math.hypot(target_dx, target_dy)

    def should_shoot(self):
        return random.randint(0, 70 // self.tier) == 0

    def shoot(self):
        rad = math.radians(self.angle)
        vel_x = math.cos(rad) * ENEMY_BULLET_SPEED
        vel_y = math.sin(rad) * ENEMY_BULLET_SPEED
        return EnemyBullet(self.pos[0], self.pos[1], vel_x, vel_y, self.tier)

    def take_damage(self, amount=1):
        self.hp -= amount
        return self.hp <= 0

    def draw(self, surface):
        color = self.TIER_COLORS[self.tier - 1]
        ship_points = [(10, 0), (-5, -7), (-5, 7)]
        rad = math.radians(self.angle)
        rotated_points = []
        for x, y in ship_points:
            new_x = x * math.cos(rad) - y * math.sin(rad)
            new_y = x * math.sin(rad) + y * math.cos(rad)
            rotated_points.append((self.pos[0] + new_x, self.pos[1] + new_y))
        pygame.draw.polygon(surface, color, rotated_points)


class EnemyBullet:
    def __init__(self, x, y, vel_x, vel_y, tier):
        self.pos = [x, y]
        self.vel = [vel_x, vel_y]
        self.tier = tier
        self.creation_time = pygame.time.get_ticks()

    def update(self, target_pos=None):
        # Check if homing bullet has expired (15 seconds lifetime)
        if self.tier >= 4:
            current_time = pygame.time.get_ticks()
            if current_time - self.creation_time > 15000:  # 15 seconds
                return False

        if self.tier >= 4 and target_pos:
            # Homing bullet
            dx = target_pos[0] - self.pos[0]
            dy = target_pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist > 0:
                homing_speed = 2.5
                self.pos[0] += (dx / dist) * homing_speed
                self.pos[1] += (dy / dist) * homing_speed
        else:
            self.pos[0] += self.vel[0]
            self.pos[1] += self.vel[1]

        return 0 < self.pos[0] < WIDTH and 0 < self.pos[1] < HEIGHT

    def draw(self, surface):
        pygame.draw.rect(surface, RED, (self.pos[0], self.pos[1], 2, 2))


class Boss:
    def __init__(self):
        self.pos = [WIDTH / 2, 50]
        self.hp = BOSS_HP
        self.max_hp = BOSS_HP
        self.speed = BOSS_SPEED
        self.size = BOSS_SIZE
        self.direction = 1
        self.attack_timer = 0
        self.attack_pattern = 0
        self.phase = 1

    def update(self, target_pos):
        # Move horizontally
        self.pos[0] += self.speed * self.direction
        if self.pos[0] > WIDTH - self.size or self.pos[0] < self.size:
            self.direction *= -1

        # Update phase based on HP
        hp_ratio = self.hp / self.max_hp
        if hp_ratio > 0.66:
            self.phase = 1
        elif hp_ratio > 0.33:
            self.phase = 2
        else:
            self.phase = 3

        # Attack timer
        self.attack_timer += 1

    def should_shoot(self):
        # Phase 3 shoots faster
        shoot_interval = 60 if self.phase < 3 else 30
        if self.attack_timer >= shoot_interval:
            self.attack_timer = 0
            return True
        return False

    def shoot(self, target_pos):
        bullets = []

        if self.phase == 1:
            # Pattern 1: Aimed shot
            dx = target_pos[0] - self.pos[0]
            dy = target_pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist > 0:
                vel_x = (dx / dist) * ENEMY_BULLET_SPEED
                vel_y = (dy / dist) * ENEMY_BULLET_SPEED
                bullets.append(EnemyBullet(self.pos[0], self.pos[1], vel_x, vel_y, 5))

        elif self.phase == 2:
            # Pattern 2: Triple shot
            for angle_offset in [-15, 0, 15]:
                dx = target_pos[0] - self.pos[0]
                dy = target_pos[1] - self.pos[1]
                base_angle = math.atan2(dy, dx)
                angle = base_angle + math.radians(angle_offset)
                vel_x = math.cos(angle) * ENEMY_BULLET_SPEED
                vel_y = math.sin(angle) * ENEMY_BULLET_SPEED
                bullets.append(EnemyBullet(self.pos[0], self.pos[1], vel_x, vel_y, 5))

        else:  # Phase 3
            # Pattern 3: Circular pattern
            num_bullets = 8
            for i in range(num_bullets):
                angle = (2 * math.pi / num_bullets) * i + (self.attack_timer * 0.1)
                vel_x = math.cos(angle) * ENEMY_BULLET_SPEED
                vel_y = math.sin(angle) * ENEMY_BULLET_SPEED
                bullets.append(EnemyBullet(self.pos[0], self.pos[1], vel_x, vel_y, 6))

        return bullets

    def take_damage(self, amount=1):
        self.hp -= amount
        return self.hp <= 0

    def draw(self, surface):
        # Draw boss body (large diamond shape)
        points = [
            (self.pos[0], self.pos[1] - self.size),  # Top
            (self.pos[0] + self.size, self.pos[1]),  # Right
            (self.pos[0], self.pos[1] + self.size),  # Bottom
            (self.pos[0] - self.size, self.pos[1])   # Left
        ]

        # Color changes based on phase
        if self.phase == 1:
            color = PURPLE
        elif self.phase == 2:
            color = ORANGE
        else:
            color = RED

        pygame.draw.polygon(surface, color, points)

        # Draw core
        core_size = self.size // 3
        pygame.draw.circle(surface, WHITE, (int(self.pos[0]), int(self.pos[1])), core_size)

    def draw_health_bar(self, surface):
        # Boss health bar at top
        bar_width = WIDTH - 40
        bar_height = 8
        bar_x = 20
        bar_y = 10

        # Background
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, bar_height))

        # Health
        hp_ratio = max(0, self.hp / self.max_hp)
        health_width = int(bar_width * hp_ratio)

        if self.phase == 1:
            hp_color = GREEN
        elif self.phase == 2:
            hp_color = YELLOW
        else:
            hp_color = RED

        pygame.draw.rect(surface, hp_color, (bar_x, bar_y, health_width, bar_height))

        # Border
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)


class Asteroid:
    def __init__(self):
        self.size = random.randint(5, 15)
        speed = random.uniform(0.5, 2.0)

        # Spawn position
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            self.pos = [random.randint(0, WIDTH), -ASTEROID_SPAWN_MARGIN]
        elif side == 'bottom':
            self.pos = [random.randint(0, WIDTH), HEIGHT + ASTEROID_SPAWN_MARGIN]
        elif side == 'left':
            self.pos = [-ASTEROID_SPAWN_MARGIN, random.randint(0, HEIGHT)]
        else:
            self.pos = [WIDTH + ASTEROID_SPAWN_MARGIN, random.randint(0, HEIGHT)]

        target_pos = [random.randint(0, WIDTH), random.randint(0, HEIGHT)]
        dx = target_pos[0] - self.pos[0]
        dy = target_pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.vel = [(dx / dist) * speed, (dy / dist) * speed]
        else:
            self.vel = [0, 0]

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        return (-ASTEROID_SPAWN_MARGIN < self.pos[0] < WIDTH + ASTEROID_SPAWN_MARGIN and
                -ASTEROID_SPAWN_MARGIN < self.pos[1] < HEIGHT + ASTEROID_SPAWN_MARGIN)

    def draw(self, surface):
        pygame.draw.circle(surface, GRAY, (int(self.pos[0]), int(self.pos[1])), self.size)


class PowerUp:
    TYPE_WEAPON = "weapon"
    TYPE_HEALTH = "health"
    TYPE_SHIELD = "shield"
    TYPE_BOMB = "bomb"

    def __init__(self, x, y, power_type=None):
        self.pos = [x, y]
        # Random velocity for item movement
        self.vel = [random.uniform(-0.5, 0.5), random.uniform(0.5, 1.5)]
        if power_type is None:
            self.type = random.choice([self.TYPE_WEAPON, self.TYPE_HEALTH, self.TYPE_SHIELD, self.TYPE_BOMB])
        else:
            self.type = power_type

    def update(self):
        # Move with velocity
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

        # Wrap around screen like player ship
        if self.pos[0] > WIDTH:
            self.pos[0] = 0
        if self.pos[0] < 0:
            self.pos[0] = WIDTH
        if self.pos[1] > HEIGHT:
            self.pos[1] = 0
        if self.pos[1] < 0:
            self.pos[1] = HEIGHT

        return True  # Always stay alive (wrap around instead of disappearing)

    def draw(self, surface):
        if self.type == self.TYPE_WEAPON:
            color = YELLOW
        elif self.type == self.TYPE_HEALTH:
            color = GREEN
        elif self.type == self.TYPE_SHIELD:
            color = CYAN
        else:  # BOMB
            color = ORANGE
        pygame.draw.rect(surface, color, (self.pos[0]-2, self.pos[1]-2, 5, 5))


class Particle:
    def __init__(self, x, y, vel_x, vel_y, color, size=2, lifetime=PARTICLE_LIFETIME):
        self.pos = [x, y]
        self.vel = [vel_x, vel_y]
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        self.vel[0] *= 0.95
        self.vel[1] *= 0.95
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, surface):
        alpha_ratio = self.lifetime / self.max_lifetime
        current_size = max(1, int(self.size * alpha_ratio))
        pygame.draw.rect(surface, self.color, (int(self.pos[0]), int(self.pos[1]), current_size, current_size))


class Explosion:
    def __init__(self, x, y, color, particle_count=20, size=1):
        self.particles = []
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 4) * size
            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed
            particle_size = random.randint(2, 4) * size
            self.particles.append(Particle(x, y, vel_x, vel_y, color, particle_size))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        return len(self.particles) > 0

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))
        pygame.display.set_caption("Retro Space Shooter")
        self.clock = pygame.time.Clock()
        self.game_font = pygame.font.Font(None, 40)
        self.info_font = pygame.font.Font(None, 24)

        # Background - scaled for larger world
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT),
                      random.choice([WHITE, GRAY])] for _ in range(150)]
        self.dust = [[random.randint(0, WIDTH), random.randint(0, HEIGHT),
                     random.choice([GRAY, BLUE])] for _ in range(75)]
        self.bg_offset = [0.0, 0.0]

        # Game state
        self.state = STATE_MENU
        self.player = None
        self.bullets = []
        self.enemies = []
        self.enemy_bullets = []
        self.asteroids = []
        self.powerups = []
        self.explosions = []
        self.engine_particles = []
        self.boss = None
        self.boss_defeated_count = 0

        self.score = 0
        self.stage = 1
        self.stage_transition_time = None
        self.bomb_flash_until = 0
        self.screen_shake_until = 0
        self.shake_offset = [0, 0]
        self.high_score = self.load_high_score()
        self.low_tier_enemy_destroyed = False
        self.last_shot_time = 0
        self.last_time_score_tick = 0
        self.game_over_time = None
        self.ai_enabled = False

    def load_high_score(self):
        try:
            if os.path.exists('highscore.json'):
                with open('highscore.json', 'r') as f:
                    data = json.load(f)
                    return data.get('high_score', 0)
        except:
            pass
        return 0

    def save_high_score(self):
        try:
            with open('highscore.json', 'w') as f:
                json.dump({'high_score': self.high_score}, f)
        except:
            pass

    def add_screen_shake(self, duration=SCREEN_SHAKE_DURATION):
        self.screen_shake_until = pygame.time.get_ticks() + duration

    def update_screen_shake(self):
        current_time = pygame.time.get_ticks()
        if current_time < self.screen_shake_until:
            self.shake_offset[0] = random.randint(-SCREEN_SHAKE_INTENSITY, SCREEN_SHAKE_INTENSITY)
            self.shake_offset[1] = random.randint(-SCREEN_SHAKE_INTENSITY, SCREEN_SHAKE_INTENSITY)
        else:
            self.shake_offset = [0, 0]

    def create_explosion(self, x, y, color, size=1):
        self.explosions.append(Explosion(x, y, color, particle_count=int(20 * size), size=size))
        self.add_screen_shake()

    def reset_game(self):
        self.player = Player(WIDTH / 2, HEIGHT / 2)
        self.bullets = []
        self.enemies = []
        self.enemy_bullets = []
        self.asteroids = []
        self.powerups = []
        self.explosions = []
        self.engine_particles = []
        self.boss = None
        self.score = 0
        self.stage = 1
        self.stage_transition_time = None
        self.bomb_flash_until = 0
        self.screen_shake_until = 0
        self.shake_offset = [0, 0]
        self.low_tier_enemy_destroyed = False
        self.last_shot_time = 0
        self.last_time_score_tick = pygame.time.get_ticks()
        self.game_over_time = None
        self.bg_offset = [0.0, 0.0]
        self.ai_enabled = False
        self.state = STATE_PLAYING

    def update_ai(self):
        current_time = pygame.time.get_ticks()

        # Analyze situation
        all_threats = []
        nearby_bullets = 0
        nearby_enemies = 0

        for e in self.enemies:
            dist = math.hypot(self.player.pos[0] - e.pos[0], self.player.pos[1] - e.pos[1])
            all_threats.append({'pos': e.pos, 'threat': 6.0 * e.tier, 'dist': dist})
            if dist < 100:  # Increased for larger world
                nearby_enemies += 1

        for a in self.asteroids:
            dist = math.hypot(self.player.pos[0] - a.pos[0], self.player.pos[1] - a.pos[1])
            all_threats.append({'pos': a.pos, 'threat': 3.0, 'dist': dist})

        for eb in self.enemy_bullets:
            dist = math.hypot(self.player.pos[0] - eb.pos[0], self.player.pos[1] - eb.pos[1])
            all_threats.append({'pos': eb.pos, 'threat': 25.0, 'dist': dist})
            if dist < 80:  # Increased for larger world
                nearby_bullets += 1

        if self.boss:
            dist = math.hypot(self.player.pos[0] - self.boss.pos[0], self.player.pos[1] - self.boss.pos[1])
            all_threats.append({'pos': self.boss.pos, 'threat': 50.0, 'dist': dist})

        # Decision making: Use bomb if overwhelmed
        hp_ratio = self.player.hp / self.player.max_hp
        danger_level = nearby_bullets * 2 + nearby_enemies

        if self.player.bombs > 0 and not self.player.is_looping:
            # Use bomb if: low HP + many threats OR too many bullets
            should_bomb = (hp_ratio <= 0.33 and danger_level >= 4) or nearby_bullets >= 6
            if should_bomb:
                if self.player.use_bomb(current_time):
                    self.bomb_flash_until = current_time + BOMB_FLASH_DURATION
                    self.add_screen_shake(400)
                    for e in self.enemies[:]:
                        self.create_explosion(e.pos[0], e.pos[1], Enemy.TIER_COLORS[e.tier - 1], size=2)
                        self.score += e.tier * 5
                    self.enemies.clear()
                    for eb in self.enemy_bullets[:]:
                        for _ in range(2):
                            vel_x = random.uniform(-2, 2)
                            vel_y = random.uniform(-2, 2)
                            self.engine_particles.append(Particle(eb.pos[0], eb.pos[1], vel_x, vel_y, RED, size=2, lifetime=10))
                    self.enemy_bullets.clear()
                    if self.boss:
                        for _ in range(10):
                            vel_x = random.uniform(-3, 3)
                            vel_y = random.uniform(-3, 3)
                            self.engine_particles.append(Particle(self.boss.pos[0], self.boss.pos[1], vel_x, vel_y, PURPLE, size=4, lifetime=20))
                        self.boss.take_damage(50)
                    return

        # Decision making: Use loop for emergency escape
        loop_ready = current_time - self.player.last_loop_time > LOOP_COOLDOWN
        if loop_ready and not self.player.is_looping:
            # Use loop if surrounded or many bullets nearby
            should_loop = danger_level >= 5 or nearby_bullets >= 4
            if should_loop:
                self.player.start_loop(current_time)
                return

        # Emergency dodge - use loop if available, otherwise dodge
        for t in all_threats:
            if t['dist'] < EMERGENCY_DODGE_RADIUS:
                if loop_ready and not self.player.is_looping and t['threat'] >= 20:
                    self.player.start_loop(current_time)
                    return

                repulsion_vec_x = self.player.pos[0] - t['pos'][0]
                repulsion_vec_y = self.player.pos[1] - t['pos'][1]
                target_angle = math.degrees(math.atan2(repulsion_vec_y, repulsion_vec_x))
                angle_diff = (target_angle - self.player.angle + 180) % 360 - 180
                turn_amount = min(ROTATION_SPEED, max(-ROTATION_SPEED, angle_diff))
                self.player.angle += turn_amount
                self.player.thrust = MAX_THRUST
                return

        # General avoidance and targeting
        steer_vec = [0.0, 0.0]
        for t in all_threats:
            if t['dist'] < PERCEPTION_RADIUS:
                repulsion_vec_x = self.player.pos[0] - t['pos'][0]
                repulsion_vec_y = self.player.pos[1] - t['pos'][1]
                weight = t['threat'] / (t['dist']**2 + 1)
                steer_vec[0] += repulsion_vec_x / (t['dist'] + 0.1) * weight
                steer_vec[1] += repulsion_vec_y / (t['dist'] + 0.1) * weight

        # Smart targeting: prioritize powerups based on need
        target_pos = None
        is_enemy_target = False

        # If low HP, prioritize health powerups
        if hp_ratio <= 0.5 and self.powerups:
            health_powerups = [p for p in self.powerups if p.type == PowerUp.TYPE_HEALTH]
            if health_powerups:
                health_powerups.sort(key=lambda p: math.hypot(self.player.pos[0] - p.pos[0],
                                                               self.player.pos[1] - p.pos[1]))
                target_pos = health_powerups[0].pos

        # If no shield, prioritize shield powerups
        elif self.player.shield == 0 and self.powerups:
            shield_powerups = [p for p in self.powerups if p.type == PowerUp.TYPE_SHIELD]
            if shield_powerups:
                shield_powerups.sort(key=lambda p: math.hypot(self.player.pos[0] - p.pos[0],
                                                               self.player.pos[1] - p.pos[1]))
                target_pos = shield_powerups[0].pos

        # Default: target enemies or nearest powerup
        if not target_pos:
            if self.enemies or self.boss:
                # Target weakest nearby enemy first
                if self.enemies:
                    nearby_enemies_list = [e for e in self.enemies if
                                          math.hypot(self.player.pos[0] - e.pos[0],
                                                    self.player.pos[1] - e.pos[1]) < 200]  # Increased for larger world
                    if nearby_enemies_list:
                        nearby_enemies_list.sort(key=lambda e: (e.tier, math.hypot(self.player.pos[0] - e.pos[0],
                                                                                    self.player.pos[1] - e.pos[1])))
                        target_pos = nearby_enemies_list[0].pos
                        is_enemy_target = True
                    else:
                        self.enemies.sort(key=lambda e: math.hypot(self.player.pos[0] - e.pos[0],
                                                                   self.player.pos[1] - e.pos[1]))
                        target_pos = self.enemies[0].pos
                        is_enemy_target = True
                elif self.boss:
                    target_pos = self.boss.pos
                    is_enemy_target = True
            elif self.powerups:
                self.powerups.sort(key=lambda p: math.hypot(self.player.pos[0] - p.pos[0],
                                                             self.player.pos[1] - p.pos[1]))
                target_pos = self.powerups[0].pos

        final_vec = list(steer_vec)
        steer_magnitude = math.hypot(steer_vec[0], steer_vec[1])

        if target_pos:
            # Adjust attraction based on health
            attraction_weight = 0.3 if hp_ratio > 0.5 else 0.15
            if steer_magnitude > 1.0:
                attraction_weight /= (steer_magnitude * 2)
            dx = target_pos[0] - self.player.pos[0]
            dy = target_pos[1] - self.player.pos[1]
            dist = math.hypot(dx, dy)
            if dist > 0:
                final_vec[0] += (dx / dist) * attraction_weight
                final_vec[1] += (dy / dist) * attraction_weight

        if abs(final_vec[0]) > 0.01 or abs(final_vec[1]) > 0.01:
            target_angle = math.degrees(math.atan2(final_vec[1], final_vec[0]))
            angle_diff = (target_angle - self.player.angle + 180) % 360 - 180
            turn_amount = min(ROTATION_SPEED, max(-ROTATION_SPEED, angle_diff))
            self.player.angle += turn_amount

        # Adaptive movement
        if steer_magnitude > 0.5:
            self.player.thrust = min(MAX_THRUST, self.player.thrust + THRUST_ACCEL * 2)
        elif target_pos and is_enemy_target:
            dist_to_target = math.hypot(self.player.pos[0] - target_pos[0],
                                       self.player.pos[1] - target_pos[1])
            # Better distance management for boss
            optimal_dist = 150 if self.boss else 110  # Increased for larger world
            if dist_to_target > optimal_dist:
                self.player.thrust = min(MAX_THRUST, self.player.thrust + THRUST_ACCEL)
            elif dist_to_target < optimal_dist - 30:
                self.player.thrust = max(0, self.player.thrust - THRUST_ACCEL * 2)
            else:
                # Maintain distance - strafe
                self.player.thrust = min(MAX_THRUST * 0.6, self.player.thrust + THRUST_ACCEL * 0.5)
        elif target_pos:
            self.player.thrust = min(MAX_THRUST, self.player.thrust + THRUST_ACCEL)
        else:
            self.player.thrust = max(0, self.player.thrust - THRUST_ACCEL)

    def handle_events(self):
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                # Help toggle (works in any state except playing)
                if event.key == pygame.K_h:
                    if self.state == STATE_MENU:
                        self.state = STATE_HELP
                    elif self.state == STATE_HELP:
                        self.state = STATE_MENU
                    elif self.state == STATE_PAUSED:
                        self.state = STATE_HELP

                if event.key == pygame.K_ESCAPE:
                    if self.state == STATE_PLAYING:
                        self.state = STATE_PAUSED
                    elif self.state == STATE_PAUSED:
                        self.state = STATE_PLAYING
                    elif self.state == STATE_HELP:
                        self.state = STATE_MENU
                    elif self.state == STATE_MENU:
                        return False

                if self.state == STATE_MENU:
                    if event.key == pygame.K_RETURN:
                        self.reset_game()
                    elif event.key == pygame.K_q:
                        return False

                if self.state == STATE_PLAYING:
                    if event.key == pygame.K_a:
                        self.ai_enabled = not self.ai_enabled
                    if event.key == pygame.K_u:
                        self.player.start_loop(current_time)
                    if event.key == pygame.K_b:
                        if self.player.use_bomb(current_time):
                            # Bomb activated
                            self.bomb_flash_until = current_time + BOMB_FLASH_DURATION
                            self.add_screen_shake(400)
                            # Clear all enemies and bullets
                            for e in self.enemies[:]:
                                self.create_explosion(e.pos[0], e.pos[1], Enemy.TIER_COLORS[e.tier - 1], size=2)
                                self.score += e.tier * 5
                            self.enemies.clear()
                            for eb in self.enemy_bullets[:]:
                                for _ in range(2):
                                    vel_x = random.uniform(-2, 2)
                                    vel_y = random.uniform(-2, 2)
                                    self.engine_particles.append(Particle(eb.pos[0], eb.pos[1], vel_x, vel_y, RED, size=2, lifetime=10))
                            self.enemy_bullets.clear()
                            # Damage boss
                            if self.boss:
                                for _ in range(10):
                                    vel_x = random.uniform(-3, 3)
                                    vel_y = random.uniform(-3, 3)
                                    self.engine_particles.append(Particle(self.boss.pos[0], self.boss.pos[1], vel_x, vel_y, PURPLE, size=4, lifetime=20))
                                self.boss.take_damage(50)  # Heavy damage to boss

        return True

    def update(self):
        if self.state != STATE_PLAYING:
            return

        current_time = pygame.time.get_ticks()

        # Update screen shake
        self.update_screen_shake()

        # Time-based score
        if current_time - self.last_time_score_tick > TIME_SCORE_INTERVAL:
            self.score += TIME_SCORE_AMOUNT
            self.last_time_score_tick += TIME_SCORE_INTERVAL

        # Stage progression
        new_stage = (self.score // STAGE_SCORE_INTERVAL) + 1
        if new_stage > self.stage:
            self.stage = new_stage
            self.stage_transition_time = current_time

        # Update player
        self.player.update_loop(current_time)
        keys = pygame.key.get_pressed()
        move = self.player.update_movement(keys, self.ai_enabled, self.update_ai)

        if move:
            self.bg_offset[0] = (self.bg_offset[0] - move[0]) % WIDTH
            self.bg_offset[1] = (self.bg_offset[1] - move[1]) % HEIGHT

        # Create engine particles
        if self.player.thrust > 0.5 and random.random() < 0.5:
            rad = math.radians(self.player.angle + 180)
            offset_dist = 10
            particle_x = self.player.pos[0] + math.cos(rad) * offset_dist
            particle_y = self.player.pos[1] + math.sin(rad) * offset_dist
            vel_x = math.cos(rad) * self.player.thrust * 0.5 + random.uniform(-0.5, 0.5)
            vel_y = math.sin(rad) * self.player.thrust * 0.5 + random.uniform(-0.5, 0.5)
            color = random.choice([ORANGE, YELLOW, RED])
            self.engine_particles.append(Particle(particle_x, particle_y, vel_x, vel_y, color, size=2, lifetime=15))

        # Auto-fire
        if not self.player.is_looping and current_time - self.last_shot_time > SHOOT_DELAY:
            self.last_shot_time = current_time
            self.bullets.extend(self.player.shoot())

        # Boss spawning
        boss_threshold = BOSS_SPAWN_SCORE * (self.boss_defeated_count + 1)
        if self.boss is None and self.score >= boss_threshold:
            self.boss = Boss()
            # Clear all enemies and bullets when boss spawns
            self.enemies.clear()
            self.enemy_bullets.clear()

        # Spawn enemies (only if no boss) - difficulty scales with stage
        enemy_spawn_rate = max(20, ENEMY_SPAWN_RATE - self.stage * 2)  # Gets faster each stage
        if self.boss is None and random.randint(0, enemy_spawn_rate) == 0:
            if not self.low_tier_enemy_destroyed:
                tier = random.choices([1, 2, 3], Enemy.LOW_TIER_PROBS)[0]
            else:
                # Higher stages increase chance of high-tier enemies
                adjusted_probs = list(Enemy.TIER_SPAWN_PROBS)
                for i in range(min(self.stage - 1, 3)):
                    # Shift probability towards higher tiers
                    for j in range(len(adjusted_probs) - 1):
                        transfer = adjusted_probs[j] * 0.1
                        adjusted_probs[j] -= transfer
                        adjusted_probs[j + 1] += transfer
                # Normalize
                total = sum(adjusted_probs)
                adjusted_probs = [p / total for p in adjusted_probs]
                tier = random.choices([1, 2, 3, 4, 5, 6], adjusted_probs)[0]
            self.enemies.append(Enemy(tier))

        # Spawn asteroids (only if no boss) - more asteroids in higher stages
        asteroid_spawn_rate = max(30, 100 - self.stage * 5)
        if self.boss is None and random.randint(0, asteroid_spawn_rate) == 0:
            self.asteroids.append(Asteroid())

        # Update bullets
        self.bullets = [b for b in self.bullets if b.update()]

        # Update enemies
        for e in self.enemies[:]:
            dist = e.update(self.player.pos)
            if dist < 10:
                is_dead = self.player.take_damage()
                if is_dead:
                    # Player explosion
                    self.create_explosion(self.player.pos[0], self.player.pos[1], WHITE, size=2)
                    self.state = STATE_GAME_OVER
                    self.game_over_time = current_time
                    if self.score > self.high_score:
                        self.high_score = self.score
                        self.save_high_score()
                else:
                    # Hit effect
                    self.add_screen_shake(100)
                    for _ in range(8):
                        vel_x = random.uniform(-3, 3)
                        vel_y = random.uniform(-3, 3)
                        self.engine_particles.append(Particle(self.player.pos[0], self.player.pos[1], vel_x, vel_y, RED, size=2, lifetime=15))

            if e.should_shoot():
                self.enemy_bullets.append(e.shoot())

        # Update enemy bullets
        for eb in self.enemy_bullets[:]:
            if not eb.update(self.player.pos):
                self.enemy_bullets.remove(eb)
            elif math.hypot(self.player.pos[0] - eb.pos[0], self.player.pos[1] - eb.pos[1]) < 5:
                is_dead = self.player.take_damage()
                if is_dead:
                    # Player explosion
                    self.create_explosion(self.player.pos[0], self.player.pos[1], WHITE, size=2)
                    self.state = STATE_GAME_OVER
                    self.game_over_time = current_time
                    if self.score > self.high_score:
                        self.high_score = self.score
                        self.save_high_score()
                else:
                    # Hit effect
                    self.add_screen_shake(100)
                    for _ in range(8):
                        vel_x = random.uniform(-3, 3)
                        vel_y = random.uniform(-3, 3)
                        self.engine_particles.append(Particle(self.player.pos[0], self.player.pos[1], vel_x, vel_y, RED, size=2, lifetime=15))

        # Update boss
        if self.boss:
            self.boss.update(self.player.pos)

            # Boss collision with player
            dist_to_player = math.hypot(self.boss.pos[0] - self.player.pos[0],
                                       self.boss.pos[1] - self.player.pos[1])
            if dist_to_player < self.boss.size:
                is_dead = self.player.take_damage()
                if is_dead:
                    self.create_explosion(self.player.pos[0], self.player.pos[1], WHITE, size=2)
                    self.state = STATE_GAME_OVER
                    self.game_over_time = current_time
                    if self.score > self.high_score:
                        self.high_score = self.score
                        self.save_high_score()
                else:
                    self.add_screen_shake(100)
                    for _ in range(8):
                        vel_x = random.uniform(-3, 3)
                        vel_y = random.uniform(-3, 3)
                        self.engine_particles.append(Particle(self.player.pos[0], self.player.pos[1], vel_x, vel_y, RED, size=2, lifetime=15))

            # Boss shooting
            if self.boss.should_shoot():
                boss_bullets = self.boss.shoot(self.player.pos)
                self.enemy_bullets.extend(boss_bullets)

        # Update asteroids
        self.asteroids = [a for a in self.asteroids if a.update()]

        # Update powerups
        self.powerups = [p for p in self.powerups if p.update()]

        # Update particles and explosions
        self.engine_particles = [p for p in self.engine_particles if p.update()]
        self.explosions = [e for e in self.explosions if e.update()]

        # Handle collisions
        self.handle_collisions()

    def handle_collisions(self):
        # Bullet vs Enemy Bullet
        for b in self.bullets[:]:
            for eb in self.enemy_bullets[:]:
                if b in self.bullets and eb in self.enemy_bullets:
                    if math.hypot(b.pos[0] - eb.pos[0], b.pos[1] - eb.pos[1]) < 4:
                        self.bullets.remove(b)
                        self.enemy_bullets.remove(eb)
                        # Small spark effect
                        for _ in range(3):
                            vel_x = random.uniform(-2, 2)
                            vel_y = random.uniform(-2, 2)
                            self.engine_particles.append(Particle(b.pos[0], b.pos[1], vel_x, vel_y, WHITE, size=1, lifetime=10))
                        break
            if b not in self.bullets:
                continue

            # Bullet vs Boss
            if self.boss:
                if math.hypot(b.pos[0] - self.boss.pos[0], b.pos[1] - self.boss.pos[1]) < self.boss.size:
                    if b in self.bullets:
                        self.bullets.remove(b)
                    # Hit spark
                    for _ in range(8):
                        vel_x = random.uniform(-2, 2)
                        vel_y = random.uniform(-2, 2)
                        self.engine_particles.append(Particle(self.boss.pos[0], self.boss.pos[1], vel_x, vel_y, ORANGE, size=3, lifetime=15))

                    if self.boss.take_damage():
                        # Boss defeated
                        self.score += 500
                        self.boss_defeated_count += 1
                        # Massive explosion
                        for i in range(5):
                            offset_x = random.uniform(-20, 20)
                            offset_y = random.uniform(-20, 20)
                            self.create_explosion(self.boss.pos[0] + offset_x, self.boss.pos[1] + offset_y,
                                                random.choice([PURPLE, ORANGE, RED]), size=3)
                        # Drop multiple powerups
                        for _ in range(5):
                            offset_x = random.uniform(-30, 30)
                            offset_y = random.uniform(-30, 30)
                            self.powerups.append(PowerUp(self.boss.pos[0] + offset_x, self.boss.pos[1] + offset_y))
                        self.boss = None
                    continue

            # Bullet vs Enemy
            for e in self.enemies[:]:
                if math.hypot(b.pos[0] - e.pos[0], b.pos[1] - e.pos[1]) < 10:
                    if b in self.bullets:
                        self.bullets.remove(b)
                    # Hit spark
                    for _ in range(5):
                        vel_x = random.uniform(-1, 1)
                        vel_y = random.uniform(-1, 1)
                        self.engine_particles.append(Particle(e.pos[0], e.pos[1], vel_x, vel_y, YELLOW, size=2, lifetime=12))

                    if e.take_damage():
                        if e.tier < 4:
                            self.low_tier_enemy_destroyed = True
                        self.score += e.tier * 10
                        # Create explosion based on enemy tier
                        explosion_color = Enemy.TIER_COLORS[e.tier - 1]
                        self.create_explosion(e.pos[0], e.pos[1], explosion_color, size=e.tier * 0.5)
                        self.enemies.remove(e)
                        # Higher tier enemies drop powerups more frequently
                        drop_chance = 0.15 + (e.tier * 0.05)  # 20% for tier 1, 45% for tier 6
                        if random.random() < drop_chance:
                            self.powerups.append(PowerUp(e.pos[0], e.pos[1]))
                    break

            if b not in self.bullets:
                continue

            # Bullet vs Asteroid
            for a in self.asteroids[:]:
                if math.hypot(b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]) < a.size:
                    if a in self.asteroids:
                        # Asteroid fragments
                        for _ in range(a.size):
                            vel_x = random.uniform(-2, 2)
                            vel_y = random.uniform(-2, 2)
                            self.engine_particles.append(Particle(a.pos[0], a.pos[1], vel_x, vel_y, GRAY, size=3, lifetime=20))
                        self.asteroids.remove(a)
                    if b in self.bullets:
                        self.bullets.remove(b)
                    if random.random() < 0.12:  # Slightly reduced from 0.15
                        self.powerups.append(PowerUp(a.pos[0], a.pos[1]))
                    break

        # Player vs PowerUp
        for p in self.powerups[:]:
            if math.hypot(p.pos[0] - self.player.pos[0], p.pos[1] - self.player.pos[1]) < 10:
                if p.type == PowerUp.TYPE_WEAPON:
                    self.player.upgrade_weapon()
                elif p.type == PowerUp.TYPE_HEALTH:
                    self.player.heal()
                elif p.type == PowerUp.TYPE_SHIELD:
                    self.player.add_shield()
                elif p.type == PowerUp.TYPE_BOMB:
                    self.player.add_bomb()
                self.powerups.remove(p)

    def draw(self):
        low_res = pygame.Surface((WIDTH, HEIGHT))

        # Bomb flash effect
        current_time = pygame.time.get_ticks()
        if current_time < self.bomb_flash_until:
            low_res.fill(WHITE)
        else:
            low_res.fill(BLACK)

        # Draw background
        for s in self.stars:
            x = (s[0] + self.bg_offset[0] + self.shake_offset[0]) % WIDTH
            y = (s[1] + self.bg_offset[1] + self.shake_offset[1]) % HEIGHT
            pygame.draw.rect(low_res, s[2], (x, y, 1, 1))

        for d in self.dust:
            x = (d[0] + self.bg_offset[0] * 0.5 + self.shake_offset[0]) % WIDTH
            y = (d[1] + self.bg_offset[1] * 0.5 + self.shake_offset[1]) % HEIGHT
            pygame.draw.rect(low_res, d[2], (x, y, 2, 2))

        if self.state == STATE_MENU:
            self.draw_menu(low_res)
        elif self.state == STATE_HELP:
            self.draw_help(low_res)
        elif self.state == STATE_PLAYING or self.state == STATE_PAUSED:
            # Draw particles (behind everything)
            for p in self.engine_particles:
                p.draw(low_res)

            # Draw game objects
            self.player.draw(low_res)
            for b in self.bullets:
                b.draw(low_res)
            for e in self.enemies:
                e.draw(low_res)
            for eb in self.enemy_bullets:
                eb.draw(low_res)
            for a in self.asteroids:
                a.draw(low_res)
            for p in self.powerups:
                p.draw(low_res)

            # Draw boss
            if self.boss:
                self.boss.draw(low_res)

            # Draw explosions (in front of everything)
            for exp in self.explosions:
                exp.draw(low_res)

            # Draw HUD
            self.draw_hud(low_res)

            # Draw boss health bar
            if self.boss:
                self.boss.draw_health_bar(low_res)

            # Draw stage transition notification
            if self.stage_transition_time:
                elapsed = current_time - self.stage_transition_time
                if elapsed < STAGE_TRANSITION_DURATION:
                    # Fade effect
                    alpha_ratio = 1.0 - (elapsed / STAGE_TRANSITION_DURATION)
                    if alpha_ratio > 0.5:
                        alpha_ratio = 1.0
                    else:
                        alpha_ratio = alpha_ratio * 2

                    stage_notify = self.game_font.render(f"STAGE {self.stage}", True, CYAN)
                    notify_rect = stage_notify.get_rect(center=(WIDTH/2, HEIGHT/2))
                    low_res.blit(stage_notify, notify_rect)
                else:
                    self.stage_transition_time = None

            if self.state == STATE_PAUSED:
                pause_text = self.game_font.render("PAUSED", True, YELLOW)
                text_rect = pause_text.get_rect(center=(WIDTH/2, HEIGHT/2))
                low_res.blit(pause_text, text_rect)

        elif self.state == STATE_GAME_OVER:
            self.draw_game_over(low_res)

            # Auto-restart
            current_time = pygame.time.get_ticks()
            if self.game_over_time and current_time - self.game_over_time > RESTART_DELAY:
                self.state = STATE_MENU

        pygame.transform.scale(low_res, (WIDTH * SCALE, HEIGHT * SCALE), self.screen)
        pygame.display.flip()

    def draw_menu(self, surface):
        title = self.game_font.render("SPACE SHOOTER", True, CYAN)
        title_rect = title.get_rect(center=(WIDTH/2, HEIGHT/3))
        surface.blit(title, title_rect)

        start_text = self.info_font.render("Press ENTER to Start", True, WHITE)
        start_rect = start_text.get_rect(center=(WIDTH/2, HEIGHT/2))
        surface.blit(start_text, start_rect)

        high_score_text = self.info_font.render(f"High Score: {self.high_score}", True, YELLOW)
        hs_rect = high_score_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 30))
        surface.blit(high_score_text, hs_rect)

        help_text = self.info_font.render("Press H for Help", True, GREEN)
        help_rect = help_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 50))
        surface.blit(help_text, help_rect)

        quit_text = self.info_font.render("Press Q to Quit", True, GRAY)
        quit_rect = quit_text.get_rect(center=(WIDTH/2, HEIGHT - 30))
        surface.blit(quit_text, quit_rect)

    def draw_help(self, surface):
        title = self.game_font.render("CONTROLS", True, CYAN)
        title_rect = title.get_rect(center=(WIDTH/2, 15))
        surface.blit(title, title_rect)

        y_offset = 35
        line_height = 14

        # Controls
        controls = [
            ("Arrow Keys: Move & Rotate", WHITE),
            ("A: Smart AI Auto-Pilot", GREEN),
            ("  -Uses Loop & Bomb", GREEN),
            ("  -Prioritizes survival", GREEN),
            ("U: Loop (Special Move)", PURPLE),
            ("B: Bomb (Clear Screen)", ORANGE),
            ("ESC: Pause Game", GRAY),
            ("", BLACK),
            ("POWERUPS:", CYAN),
            ("Yellow: Weapon Upgrade", YELLOW),
            ("Green: Health +1", GREEN),
            ("Cyan: Shield +1", CYAN),
            ("Orange: Bomb +1", ORANGE),
            ("", BLACK),
            ("GOAL:", YELLOW),
            ("Destroy enemies & bosses!", WHITE),
            ("Boss every 500 points", WHITE),
            ("Stage up every 200 pts", WHITE),
        ]

        for text, color in controls:
            if text:
                line = self.info_font.render(text, True, color)
                surface.blit(line, (10, y_offset))
            y_offset += line_height

        back_text = self.info_font.render("Press H or ESC to go back", True, GRAY)
        back_rect = back_text.get_rect(center=(WIDTH/2, HEIGHT - 10))
        surface.blit(back_text, back_rect)

    def draw_hud(self, surface):
        # Score and Stage
        score_text = self.info_font.render(f"Score: {self.score}", True, WHITE)
        surface.blit(score_text, (WIDTH - 95, 5))

        stage_text = self.info_font.render(f"Stage {self.stage}", True, CYAN)
        surface.blit(stage_text, (WIDTH - 85, 25))

        # Health bar
        hp_text = self.info_font.render("HP:", True, WHITE)
        surface.blit(hp_text, (5, 5))
        for i in range(self.player.max_hp):
            color = GREEN if i < self.player.hp else GRAY
            pygame.draw.rect(surface, color, (35 + i * 12, 8, 10, 10))

        # Shield bar
        if self.player.max_shield > 0:
            shield_text = self.info_font.render("SH:", True, WHITE)
            surface.blit(shield_text, (5, 20))
            for i in range(self.player.max_shield):
                color = CYAN if i < self.player.shield else GRAY
                pygame.draw.rect(surface, color, (35 + i * 12, 23, 10, 10))

        # Weapon level
        weapon_text = self.info_font.render(f"Weapon: Lv.{self.player.weapon_level}", True, YELLOW)
        surface.blit(weapon_text, (5, 38))

        # Bombs
        bomb_text = self.info_font.render(f"Bombs[B]: {self.player.bombs}", True, ORANGE)
        surface.blit(bomb_text, (5, 53))

        # Loop cooldown
        current_time = pygame.time.get_ticks()
        loop_ready = current_time - self.player.last_loop_time > LOOP_COOLDOWN
        loop_color = GREEN if loop_ready else GRAY
        loop_text = self.info_font.render("Loop[U]", True, loop_color)
        surface.blit(loop_text, (5, 68))

        # AI indicator
        if self.ai_enabled:
            ai_text = self.info_font.render("AI ON", True, GREEN)
            surface.blit(ai_text, (WIDTH - 50, 45))

    def draw_game_over(self, surface):
        game_over_text = self.game_font.render("GAME OVER", True, RED)
        text_rect = game_over_text.get_rect(center=(WIDTH/2, HEIGHT/2 - 20))
        surface.blit(game_over_text, text_rect)

        score_text = self.info_font.render(f"Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 10))
        surface.blit(score_text, score_rect)

        if self.score >= self.high_score:
            new_high_text = self.info_font.render("NEW HIGH SCORE!", True, YELLOW)
            nh_rect = new_high_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 30))
            surface.blit(new_high_text, nh_rect)

    async def run(self):
        """Main game loop - async for Pygbag web support"""
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
            await asyncio.sleep(0)  # Critical for Pygbag - yields to browser

        pygame.quit()
        sys.exit()


async def main():
    """Entry point for async execution"""
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
