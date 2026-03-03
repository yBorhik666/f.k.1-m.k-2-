import pygame
import math
import random
import sys
import os
from weapons import weapons, load_weapon_textures, weapon_sounds
from level import levels
import mixer
pygame.init()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "save.json")

LEVEL = 1
if len(sys.argv) > 1:
    LEVEL = int(sys.argv[1])

WIDTH, HEIGHT = 1360, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(" not DOOM THE KILL FYRRE")
clock = pygame.time.Clock()
pygame.mixer.init()
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)
player_hp = 100
max_hp = 100
TILE = 64

px, py = 150, 150
angle = 0
speed = 3
mouse_sens = 0.003
fov = math.pi / 3

NUM_RAYS = 300
MAX_DEPTH = 800
DELTA_ANGLE = fov / NUM_RAYS
SCALE = WIDTH / NUM_RAYS
HALF_HEIGHT = HEIGHT // 2

bullets = []
enemies = []
spawn_timer = 0

wall_tex = pygame.image.load("image/wall.png").convert()
enemy_sprite = pygame.image.load("image/eNemi.png").convert_alpha()
gun_tex = load_weapon_textures()
bullet_tex = pygame.image.load("image/bullet_0.png").convert_alpha()

TEX_SIZE = wall_tex.get_width()

current_weapon_index = 0
current_weapon = weapons[current_weapon_index]
gun_frame = 0
gun_animating = False
gun_anim_speed = 0.2
def load_level():
    global world_map, MAX_ENEMIES, SPAWN_DELAY, enemies, px, py

    enemies.clear()

    if LEVEL in levels:
        level_data = levels[LEVEL]
        world_map = level_data["map"]
        MAX_ENEMIES = level_data["max_enemies"]
        SPAWN_DELAY = level_data["spawn_delay"]
    else:
        # Якщо рівень не знайдено, використовуємо рівень 1
        level_data = levels[1]
        world_map = level_data["map"]
        MAX_ENEMIES = level_data["max_enemies"]
        SPAWN_DELAY = level_data["spawn_delay"]

    px = 150
    py = 150

    MAX_ENEMIES = LEVEL * 5
    SPAWN_DELAY = max(60, 180 - LEVEL * 20)

    px = 150
    py = 150


def is_wall(x, y):
    mx, my = int(x // TILE), int(y // TILE)
    if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
        return world_map[my][mx] == "1"
    return True


def spawn_enemy():
    while True:
        mx = random.randint(1, len(world_map[0]) - 2)
        my = random.randint(1, len(world_map) - 2)

        if world_map[my][mx] == "0":
            x = mx * TILE + TILE // 2
            y = my * TILE + TILE // 2

            if math.hypot(x - px, y - py) > 200:
                enemies.append({"x": x, "y": y, "alive": True, "hp": 10})
                break


def cast_walls():
    ray_angle = angle - fov / 2
    depths = []
    x_pos = 0

    for ray in range(NUM_RAYS):

        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        depth = 1
        hit = False

        while depth < MAX_DEPTH:
            x = px + depth * cos_a
            y = py + depth * sin_a

            mx, my = int(x // TILE), int(y // TILE)

            if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
                if world_map[my][mx] == "1":
                    hit = True
                    break
            else:
                break

            depth += 4   # 🚀 шаг луча (оптимизация)

        if hit:
            depth *= math.cos(angle - ray_angle)
            proj_h = 21000 / (depth + 0.0001)

            hit_x = int(x) % TILE
            tex_x = int(hit_x * TEX_SIZE / TILE)

            column = wall_tex.subsurface(tex_x, 0, 1, TEX_SIZE)
            column = pygame.transform.scale(
                column,
                (int(SCALE) + 1, int(proj_h))
            )

            screen.blit(column, (int(x_pos), HALF_HEIGHT - proj_h // 2))
            depths.append(depth)
        else:
            depths.append(MAX_DEPTH)

        x_pos += SCALE
        ray_angle += DELTA_ANGLE

    return depths


def draw_enemies(depths):
    for enemy in enemies:
        if not enemy["alive"]:
            continue

        dx = enemy["x"] - px
        dy = enemy["y"] - py
        dist = math.hypot(dx, dy)

        angle_to_enemy = math.atan2(dy, dx) - angle

        if -fov/2 < angle_to_enemy < fov/2:
            size = int(21000 / (dist + 0.1))
            x = int((angle_to_enemy + fov/2) / fov * WIDTH) - size // 2
            y = HALF_HEIGHT - size // 2

            ray = int(x / SCALE)
            if 0 < ray < len(depths) and dist < depths[ray]:
                sprite = pygame.transform.scale(enemy_sprite, (size, size))
                screen.blit(sprite, (x, y))

def update_enemies():
    global player_hp

    for enemy in enemies:
        if not enemy["alive"]:
            continue

        dx = px - enemy["x"]
        dy = py - enemy["y"]
        dist = math.hypot(dx, dy)

        # Если враг рядом — наносит урон
        if dist < 40:
            player_hp -= 0.2   # скорость урона

def shoot():
    global gun_animating, gun_frame
    weapon_sounds[current_weapon["name"]].play()
    bullets.append({
        "x": px,
        "y": py,
        "angle": angle,
        "speed": current_weapon["speed"],
        "life": 60,
        "damage": current_weapon["damage"]
    })
    gun_animating = True
    gun_frame = 0




def update_bullets():
    for bullet in bullets[:]:
        bullet["x"] += bullet["speed"] * math.cos(bullet["angle"])
        bullet["y"] += bullet["speed"] * math.sin(bullet["angle"])
        bullet["life"] -= 1

        mx, my = int(bullet["x"] // TILE), int(bullet["y"] // TILE)

        if not (0 <= my < len(world_map) and 0 <= mx < len(world_map[0])) \
                or world_map[my][mx] == "1" \
                or bullet["life"] <= 0:
            bullets.remove(bullet)
            continue

        for enemy in enemies:
            if enemy["alive"]:
                if math.hypot(enemy["x"] - bullet["x"], enemy["y"] - bullet["y"]) < 20:
                    enemy["hp"] = enemy.get("hp", 3) - bullet["damage"]
                    if enemy["hp"] <= 0:
                        enemy["alive"] = False
                    if bullet in bullets:
                        bullets.remove(bullet)


def draw_bullets(depths):
    for bullet in bullets:
        dx = bullet["x"] - px
        dy = bullet["y"] - py
        dist = math.hypot(dx, dy)

        angle_to_bullet = math.atan2(dy, dx) - angle

        if -fov/2 < angle_to_bullet < fov/2:
            size = max(4, int(300 / (dist + 0.1)))
            x = int((angle_to_bullet + fov/2) / fov * WIDTH) - size // 2
            y = HALF_HEIGHT - size // 2

            ray = int(x / SCALE)
            if 0 < ray < len(depths) and dist < depths[ray]:
                sprite = pygame.transform.scale(bullet_tex, (size, size))
                screen.blit(sprite, (x, y))

def draw_hp():
    bar_width = 300
    bar_height = 25
    x = 20
    y = HEIGHT - 40

    # фон
    pygame.draw.rect(screen, (80, 0, 0), (x, y, bar_width, bar_height))

    # текущее HP
    hp_ratio = player_hp / max_hp
    pygame.draw.rect(screen, (200, 0, 0),
                     (x, y, bar_width * hp_ratio, bar_height))

    # рамка
    pygame.draw.rect(screen, (255,255,255),
                     (x, y, bar_width, bar_height), 2)

def draw_minimap():
    scale = 15
    surf = pygame.Surface((len(world_map[0])*scale, len(world_map)*scale))
    surf.set_alpha(200)
    surf.fill((30,30,30))

    for y,row in enumerate(world_map):
        for x,char in enumerate(row):
            rect = pygame.Rect(x*scale,y*scale,scale,scale)
            if char == "1":
                pygame.draw.rect(surf,(200,200,200),rect)
            elif char == "E":
                pygame.draw.rect(surf,(0,255,0),rect)

    pygame.draw.circle(surf,(255,0,0),
                       (int(px//TILE*scale),int(py//TILE*scale)),4)

    for enemy in enemies:
        if enemy["alive"]:
            pygame.draw.circle(surf,(255,255,0),
                (int(enemy["x"]//TILE*scale),
                 int(enemy["y"]//TILE*scale)),3)

    screen.blit(surf,(20,20))


def check_level_exit():
    global LEVEL
    mx,my = int(px//TILE),int(py//TILE)

    if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
        if world_map[my][mx] == "E":
            LEVEL += 1
            if LEVEL > 5:
                print("Ты прошёл игру!")
                pygame.quit()
                exit()
            load_level()


load_level()

running = True
while running:
    screen.fill((0,0,0))
    pygame.draw.rect(screen, (70, 90, 160), (0, 0, WIDTH, HALF_HEIGHT))
    pygame.draw.rect(screen, (50, 50, 50), (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
    if player_hp <= 0:
        print("Ты умер")
        pygame.quit()
        exit()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running=False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            shoot()
        if event.type == pygame.MOUSEWHEEL:
            current_weapon_index += event.y
            current_weapon_index %= len(weapons)
            current_weapon = weapons[current_weapon_index]

    mx,_ = pygame.mouse.get_rel()
    angle += mx*mouse_sens

    keys = pygame.key.get_pressed()

    if keys[pygame.K_w]:
        nx = px + speed*math.cos(angle)
        ny = py + speed*math.sin(angle)
        if not is_wall(nx,ny):
            px,py = nx,ny

    if keys[pygame.K_s]:
        nx = px - speed*math.cos(angle)
        ny = py - speed*math.sin(angle)
        if not is_wall(nx,ny):
            px,py = nx,ny

    if keys[pygame.K_a]:
        nx = px + speed*math.sin(angle)
        ny = py - speed*math.cos(angle)
        if not is_wall(nx,ny):
            px,py = nx,ny

    if keys[pygame.K_d]:
        nx = px - speed*math.sin(angle)
        ny = py + speed*math.cos(angle)
        if not is_wall(nx,ny):
            px,py = nx,ny



    spawn_timer += 1
    if spawn_timer >= SPAWN_DELAY and len(enemies) < MAX_ENEMIES:
        spawn_enemy()
        spawn_timer = 0

    depths = cast_walls()
    draw_enemies(depths)
    draw_bullets(depths)
    update_bullets()

    if keys[pygame.K_TAB]:
        draw_minimap()
    # 🔥 обновление отдачи
    if gun_animating:
        gun_frame += gun_anim_speed
        if gun_frame >= len(current_weapon["frames"]):
            gun_animating = False
            gun_frame = 0




    if gun_animating:
        frame_image = current_weapon["frames"][int(gun_frame)]
    else:
        frame_image = current_weapon["frames"][0]

    gun = pygame.transform.scale(frame_image, (300, 200))
    if current_weapon["name"] == "Rifle":
        x_offset = 0
    else:
        x_offset = 60
    screen.blit(gun, (WIDTH // 2 - 150 + x_offset , HEIGHT - 200))
    update_enemies()
    draw_hp()
    check_level_exit()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
