import pygame
import random
import sys
import math

# Initialize Pygame
pygame.init()
pygame.font.init() # Initialize font module

# Font for text
game_font = pygame.font.Font(None, 40) # Using default font
info_font = pygame.font.Font(None, 24)

# Game States
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
game_state = STATE_PLAYING

# Retro low-res screen (VGA-like, scaled up for modern displays)
WIDTH, HEIGHT = 320, 240
SCALE = 2  # Scale up for visibility
screen = pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))
pygame.display.set_caption("Retro Space Shooter")
clock = pygame.time.Clock()

# Colors (limited 16-bit palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

# Define variables that will be reset
score = 0
player_pos = [0,0]
player_angle = 0
thrust = 0
weapon_level = 1
bullets = []
enemies = []
enemy_bullets = []
asteroids = []
items = []
bg_offset_x = 0.0
bg_offset_y = 0.0
low_tier_enemy_destroyed = False

def reset_game():
    global player_pos, player_angle, thrust, weapon_level, game_state, bg_offset_x, bg_offset_y, score, low_tier_enemy_destroyed
    
    score = 0
    player_pos = [WIDTH / 2.0, HEIGHT / 2.0]
    player_angle = -90.0
    thrust = 0.0
    weapon_level = 1
    bg_offset_x = 0.0
    bg_offset_y = 0.0
    low_tier_enemy_destroyed = False
    
    bullets.clear()
    enemies.clear()
    enemy_bullets.clear()
    asteroids.clear()
    items.clear()
    
    game_state = STATE_PLAYING

# Player spaceship stats
rotation_speed = 4.5
max_thrust = 4.0
thrust_accel = 0.2
bullet_speed = 7

# Enemies stats
enemy_spawn_rate = 50
enemy_tiers = [1,2,3,4,5,6]
tier_probs = [0.4, 0.3, 0.15, 0.08, 0.05, 0.02]
low_enemy_tiers = [1, 2, 3]
low_tier_probs = [0.47, 0.35, 0.18] # Renormalized from original tier_probs
enemy_bullet_speed = 3.0
enemy_rotation_speed = 2.5 # degrees per frame

# Asteroid stats
ASTEROID_SPAWN_MARGIN = 20

# Background stars and dust (procedural)
stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.choice([WHITE, GRAY])] for _ in range(100)]
dust = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.choice([GRAY, BLUE])] for _ in range(50)]

def draw_pixel_art(surface, pos, color, size=1):
    pygame.draw.rect(surface, color, (pos[0], pos[1], size, size))

def draw_triangle_ship(surface, pos, angle, color):
    ship_points = [(10, 0), (-5, -7), (-5, 7)]
    rad = math.radians(angle)
    rotated_points = []
    for x, y in ship_points:
        new_x = x * math.cos(rad) - y * math.sin(rad)
        new_y = x * math.sin(rad) + y * math.cos(rad)
        rotated_points.append((pos[0] + new_x, pos[1] + new_y))
    pygame.draw.polygon(surface, color, rotated_points)

def draw_spaceship(surface, pos, angle):
    draw_triangle_ship(surface, pos, angle, GREEN)

def draw_enemy(surface, pos, angle, tier):
    color = [RED, YELLOW, BLUE, GREEN, WHITE, GRAY][tier-1]
    draw_triangle_ship(surface, pos, angle, color)

def draw_asteroid(surface, pos, size):
    pygame.draw.circle(surface, GRAY, (int(pos[0]), int(pos[1])), size)

def draw_item(surface, pos):
    pygame.draw.rect(surface, YELLOW, (pos[0]-2, pos[1]-2, 5, 5))

# Main game loop
running = True
reset_game() # Initial setup

while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if game_state == STATE_PLAYING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                rad = math.radians(player_angle)
                vel_x = math.cos(rad) * bullet_speed
                vel_y = math.sin(rad) * bullet_speed
                if weapon_level == 1:
                    bullets.append([player_pos[0], player_pos[1], vel_x, vel_y])
                elif weapon_level == 2:
                    p_rad = math.radians(player_angle + 90)
                    offset_x, offset_y = math.cos(p_rad) * 5, math.sin(p_rad) * 5
                    bullets.append([player_pos[0] + offset_x, player_pos[1] + offset_y, vel_x, vel_y])
                    bullets.append([player_pos[0] - offset_x, player_pos[1] - offset_y, vel_x, vel_y])
                elif weapon_level == 3:
                    bullets.append([player_pos[0], player_pos[1], vel_x, vel_y])
                    for angle_diff in [-20, 20]:
                        s_rad = math.radians(player_angle + angle_diff)
                        s_vel_x, s_vel_y = math.cos(s_rad) * bullet_speed, math.sin(s_rad) * bullet_speed
                        bullets.append([player_pos[0], player_pos[1], s_vel_x, s_vel_y])
        
        elif game_state == STATE_GAME_OVER:
            if event.type == pygame.KEYDOWN:
                reset_game()

    # --- Game Logic ---
    if game_state == STATE_PLAYING:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: player_angle -= rotation_speed
        if keys[pygame.K_RIGHT]: player_angle += rotation_speed
        if keys[pygame.K_UP]: thrust = min(thrust + thrust_accel, max_thrust)
        if keys[pygame.K_DOWN]: thrust = max(thrust - thrust_accel, 0)
        if thrust > 0: thrust = max(0, thrust - thrust_accel / 4)

        rad = math.radians(player_angle)
        move_x, move_y = thrust * math.cos(rad), thrust * math.sin(rad)
        player_pos[0] += move_x
        player_pos[1] += move_y

        bg_offset_x = (bg_offset_x - move_x) % WIDTH
        bg_offset_y = (bg_offset_y - move_y) % HEIGHT

        if player_pos[0] > WIDTH: player_pos[0] = 0
        if player_pos[0] < 0: player_pos[0] = WIDTH
        if player_pos[1] > HEIGHT: player_pos[1] = 0
        if player_pos[1] < 0: player_pos[1] = HEIGHT

        if random.randint(0, enemy_spawn_rate) == 0:
            if not low_tier_enemy_destroyed:
                tier = random.choices(low_enemy_tiers, low_tier_probs)[0]
            else:
                tier = random.choices(enemy_tiers, tier_probs)[0]

            hp, speed = tier * 2, 1 + tier * 0.5
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top': pos = [random.randint(0, WIDTH), -20]
            elif side == 'bottom': pos = [random.randint(0, WIDTH), HEIGHT + 20]
            elif side == 'left': pos = [-20, random.randint(0, HEIGHT)]
            else: pos = [WIDTH + 20, random.randint(0, HEIGHT)]
            initial_angle = math.degrees(math.atan2(HEIGHT/2 - pos[1], WIDTH/2 - pos[0]))
            enemies.append([pos[0], pos[1], tier, hp, speed, initial_angle])

        if random.randint(0, 100) == 0:
            size = random.randint(5, 15)
            speed = random.uniform(0.5, 2.0)
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top': pos = [random.randint(0, WIDTH), -ASTEROID_SPAWN_MARGIN]
            elif side == 'bottom': pos = [random.randint(0, WIDTH), HEIGHT + ASTEROID_SPAWN_MARGIN]
            elif side == 'left': pos = [-ASTEROID_SPAWN_MARGIN, random.randint(0, HEIGHT)]
            else: pos = [WIDTH + ASTEROID_SPAWN_MARGIN, random.randint(0, HEIGHT)]
            target_pos = [random.randint(0, WIDTH), random.randint(0, HEIGHT)]
            dx, dy = target_pos[0] - pos[0], target_pos[1] - pos[1]
            dist = math.hypot(dx, dy)
            if dist > 0:
                vel_x, vel_y = (dx / dist) * speed, (dy / dist) * speed
                asteroids.append([pos[0], pos[1], size, vel_x, vel_y])

        for b in bullets[:]:
            b[0] += b[2]; b[1] += b[3]
            if not (0 < b[0] < WIDTH and 0 < b[1] < HEIGHT): bullets.remove(b)

        for e in enemies[:]:
            target_dx, target_dy = player_pos[0] - e[0], player_pos[1] - e[1]
            target_angle = math.degrees(math.atan2(target_dy, target_dx))
            angle_diff = (target_angle - e[5] + 180) % 360 - 180
            turn_amount = min(enemy_rotation_speed, max(-enemy_rotation_speed, angle_diff))
            e[5] += turn_amount
            rad = math.radians(e[5])
            e[0] += e[4] * math.cos(rad)
            e[1] += e[4] * math.sin(rad)
            if random.randint(0, 70 // e[2]) == 0:
                vel_x, vel_y = math.cos(rad) * enemy_bullet_speed, math.sin(rad) * enemy_bullet_speed
                enemy_bullets.append([e[0], e[1], vel_x, vel_y, e[2]])
            if math.hypot(target_dx, target_dy) < 10: game_state = STATE_GAME_OVER

        for eb in enemy_bullets[:]:
            if eb[4] >= 4: # Homing for high-tier
                dx, dy = player_pos[0] - eb[0], player_pos[1] - eb[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    homing_speed = 2.5
                    eb[0] += (dx / dist) * homing_speed
                    eb[1] += (dy / dist) * homing_speed
            else: # Straight for low-tier
                eb[0] += eb[2]; eb[1] += eb[3]
            if math.hypot(player_pos[0] - eb[0], player_pos[1] - eb[1]) < 5: game_state = STATE_GAME_OVER
            if not (0 < eb[0] < WIDTH and 0 < eb[1] < HEIGHT):
                if eb in enemy_bullets: enemy_bullets.remove(eb)

        for a in asteroids[:]:
            a[0] += a[3]; a[1] += a[4]
            if not (-ASTEROID_SPAWN_MARGIN < a[0] < WIDTH + ASTEROID_SPAWN_MARGIN and \
                    -ASTEROID_SPAWN_MARGIN < a[1] < HEIGHT + ASTEROID_SPAWN_MARGIN):
                asteroids.remove(a)

        for b in bullets[:]:
            collided = False
            for e in enemies[:]:
                if math.hypot(b[0] - e[0], b[1] - e[1]) < 10:
                    e[3] -= 1
                    if b in bullets: bullets.remove(b)
                    collided = True
                    if e[3] <= 0:
                        if e[2] < 4:
                            low_tier_enemy_destroyed = True
                        score += e[2] * 10
                        enemies.remove(e)
                        if random.random() < 0.2: items.append([e[0], e[1]])
                    break
            if collided: continue
            for a in asteroids[:]:
                if math.hypot(b[0] - a[0], b[1] - a[1]) < a[2]:
                    if a in asteroids: asteroids.remove(a)
                    if b in bullets: bullets.remove(b)
                    if random.random() < 0.1: items.append([a[0], a[1]])
                    break

        for i in items[:]:
            i[1] += 1
            if math.hypot(i[0] - player_pos[0], i[1] - player_pos[1]) < 10:
                weapon_level = min(weapon_level + 1, 3)
                items.remove(i)
            if i[1] > HEIGHT: items.remove(i)

    # --- Drawing ---
    low_res = pygame.Surface((WIDTH, HEIGHT))
    low_res.fill(BLACK)

    for s in stars:
        draw_pixel_art(low_res, [(s[0] + bg_offset_x) % WIDTH, (s[1] + bg_offset_y) % HEIGHT], s[2])
    for d in dust:
        draw_pixel_art(low_res, [(d[0] + bg_offset_x * 0.5) % WIDTH, (d[1] + bg_offset_y * 0.5) % HEIGHT], d[2], size=2)

    draw_spaceship(low_res, player_pos, player_angle)
    for b in bullets: draw_pixel_art(low_res, b, WHITE, size=3)
    for e in enemies: draw_enemy(low_res, [e[0], e[1]], e[5], e[2])
    for eb in enemy_bullets: draw_pixel_art(low_res, [eb[0], eb[1]], RED, size=2)
    for a in asteroids: draw_asteroid(low_res, [a[0], a[1]], a[2])
    for i in items: draw_item(low_res, i)

    score_text = info_font.render(f"Score: {score}", True, WHITE)
    score_rect = score_text.get_rect(topright=(WIDTH - 10, 5))
    low_res.blit(score_text, score_rect)

    if game_state == STATE_GAME_OVER:
        game_over_text = game_font.render("GAME OVER", True, RED)
        restart_text = info_font.render("Press any key to restart", True, WHITE)
        text_rect = game_over_text.get_rect(center=(WIDTH/2, HEIGHT/2 - 20))
        restart_rect = restart_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 20))
        low_res.blit(game_over_text, text_rect)
        low_res.blit(restart_text, restart_rect)

    pygame.transform.scale(low_res, (WIDTH * SCALE, HEIGHT * SCALE), screen)
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()