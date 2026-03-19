import pygame
import math
import random
import sys
import os
from weapons import weapons, load_weapon_textures, weapon_sounds
from level import levels
from menu import run_menu


def run_game(screen):

    WIDTH, HEIGHT = screen.get_size()

    pygame.display.set_caption("not DOOM THE KILL FYRRE")
    clock = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    player_hp = 100
    max_hp = 100
    TILE = 64
    LEVEL = 1

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

    # --- БАГ 1 ФИКС: лимит частиц ---
    MAX_PARTICLES = 200

    # --- Статистика за уровень ---
    stat_kills = 0
    stat_damage = 0
    stat_time_frames = 0

    # --- Боеприпасы ---
    ammo = {
        "9mm":    60,
        "shells": 20,
        "762":    120,
        "cells":  10,
    }
    MAX_AMMO = {
        "9mm":    120,
        "shells": 40,
        "762":    300,
        "cells":  20,
    }
    ammo_pickups = []       # пикапы на уровне
    ammo_spawn_timer = 0
    AMMO_SPAWN_DELAY = 600  # кадров между спавном пикапов

    bullets = []
    enemy_bullets = []
    enemies = []
    spawn_timer = 0
    medkits = []

    bob_timer = 0.0
    bob_offset = 0.0
    BOB_SPEED = 0.12
    BOB_AMPLITUDE = 8

    particles = []

    hit_sound = None
    hit_sound_path = "sound/hit.wav"
    if os.path.exists(hit_sound_path):
        hit_sound = pygame.mixer.Sound(hit_sound_path)
    else:
        try:
            import numpy as np
            sample_rate = 44100
            duration = 0.08
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            freq = 180
            wave = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 40) * 32767).astype(np.int16)
            stereo = np.column_stack([wave, wave])
            hit_sound = pygame.sndarray.make_sound(stereo)
        except Exception:
            hit_sound = None

    medkit_img = pygame.image.load("image/medik.png").convert_alpha()
    wall_tex = pygame.image.load("image/wall.png").convert()
    enemy_sprite = pygame.image.load("image/eNemi.png").convert_alpha()
    shooter_sprite = pygame.image.load("image/enemis.png").convert_alpha()
    shooter_sprite_shoot = pygame.image.load("image/enemis1.png").convert_alpha()
    shooter_bullet_tex = pygame.image.load("image/enemis_bullet.png").convert_alpha()
    shooter_bullet_tex2 = pygame.image.load("image/enemis_bullet1.png").convert_alpha()
    lilith_sprite = pygame.image.load("image/lilith.png").convert_alpha()
    spear_img = pygame.image.load("image/spear_of_lilith.png").convert_alpha()
    spear_frames = [
        pygame.image.load("image/peak_0.png").convert_alpha(),  # idle — держит копьё
        pygame.image.load("image/peak_1.png").convert_alpha(),  # throw — бросок
    ]
    load_weapon_textures()
    bullet_tex = pygame.image.load("image/bullet_0.png").convert_alpha()
    heal_sound = pygame.mixer.Sound("sound/medik.wav")
    TEX_SIZE = wall_tex.get_width()

    lilith = None

    current_weapon_index = 0
    current_weapon = weapons[current_weapon_index]
    gun_frame = 0
    gun_animating = False
    gun_anim_speed = 0.2
    fire_timer = 0

    # --- Перегрев пулемёта ---
    heat = 0.0           # текущий нагрев 0..100
    MAX_HEAT = 100.0
    HEAT_PER_SHOT = 4.0  # нагрев за каждый выстрел
    HEAT_COOL_RATE = 1.2 # остывание в кадр когда не стреляем
    HEAT_COOL_FAST = 0.5 # остывание во время стрельбы (медленно)
    overheated = False   # заклинило ли оружие
    OVERHEAT_COOLDOWN = 180  # кадров до разблокировки (3 сек при 60fps)
    overheat_timer = 0

    world_map = []
    MAX_ENEMIES = 5
    SPAWN_DELAY = 120

    # --- БАГ 5 ФИКС: spear_anim_timer объявлен заранее ---
    spear_unlocked = False
    spear_cooldown = 0
    spear_anim_timer = 0

    # --- Анимация броска копья ---
    SPEAR_THROW_FRAMES  = 36   # кадров на анимацию броска (медленнее)
    spear_throw_timer   = 0    # >0 пока играет анимация броска
    spear_throw_screen_x = 0
    spear_throw_screen_y = 0

    def load_level():
        nonlocal world_map, MAX_ENEMIES, SPAWN_DELAY, px, py
        nonlocal sky_color, floor_color, is_lilit, lilit_title_timer, lilith
        nonlocal spear_unlocked, spear_cooldown, spear_anim_timer
        nonlocal stat_kills, stat_damage, stat_time_frames

        enemies.clear()
        medkits.clear()
        ammo_pickups.clear()
        lilith = None
        spear_unlocked = False
        spear_cooldown = 0
        spear_anim_timer = 0
        stat_kills = 0
        stat_damage = 0
        stat_time_frames = 0

        if LEVEL in levels:
            level_data = levels[LEVEL]
        else:
            level_data = levels[1]

        world_map = level_data["map"]
        MAX_ENEMIES = level_data["max_enemies"]
        SPAWN_DELAY = level_data["spawn_delay"]
        sky_color = level_data.get("sky_color", (70, 90, 160))

        is_lilit = level_data.get("name", "") == "LILIT"
        if is_lilit:
            floor_color = (40, 0, 0)
            lilit_title_timer = 180
            for row_i, row in enumerate(world_map):
                for col_i, char in enumerate(row):
                    if char == "L":
                        lilith = {
                            "x": col_i * TILE + TILE // 2,
                            "y": row_i * TILE + TILE // 2,
                            "alive": True,
                            "gave_spear": False,
                        }
        else:
            floor_color = (50, 50, 50)
            lilit_title_timer = 0

        px = 150
        py = 150

    def is_wall(x, y):
        mx, my = int(x // TILE), int(y // TILE)
        if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
            return world_map[my][mx] == "1"
        return True

    def spawn_enemy():
        for _ in range(100):
            mx = random.randint(1, len(world_map[0]) - 2)
            my = random.randint(1, len(world_map) - 2)
            if world_map[my][mx] == "0":
                x = mx * TILE + TILE // 2
                y = my * TILE + TILE // 2
                if math.hypot(x - px, y - py) > 200:
                    etype = "shooter" if random.random() < 0.4 else "melee"
                    enemies.append({
                        "x": x, "y": y,
                        "alive": True,
                        "hp": 10,
                        "type": etype,
                        "shoot_timer": random.randint(0, 60),
                        "move_angle": random.uniform(0, math.pi * 2),
                        "shooting_anim": 0,
                    })
                    break

    def cast_walls(v_offset=0):
        ray_angle = angle - fov / 2
        depths = []
        x_pos = 0

        for ray in range(NUM_RAYS):
            sin_a = math.sin(ray_angle)
            cos_a = math.cos(ray_angle)
            depth = 1
            hit = False
            tex_x_coord = 0

            while depth < MAX_DEPTH:
                x = px + depth * cos_a
                y = py + depth * sin_a
                mx, my = int(x // TILE), int(y // TILE)
                if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
                    if world_map[my][mx] == "1":
                        hit = True
                        tex_x_coord = int(x) % TILE
                        break
                else:
                    break
                depth += 4

            if hit:
                depth *= math.cos(angle - ray_angle)
                depth = max(depth, 0.1)
                proj_h = 21000 / depth
                tex_x = int(tex_x_coord * TEX_SIZE / TILE)
                tex_x = max(0, min(tex_x, TEX_SIZE - 1))
                column = wall_tex.subsurface(tex_x, 0, 1, TEX_SIZE)
                column = pygame.transform.scale(column, (int(SCALE) + 1, int(proj_h)))
                screen.blit(column, (int(x_pos), HALF_HEIGHT - proj_h // 2 + int(v_offset)))
                depths.append(depth)
            else:
                depths.append(MAX_DEPTH)

            x_pos += SCALE
            ray_angle += DELTA_ANGLE

        return depths

    def draw_enemies(depths, v_offset=0):
        for enemy in enemies:
            if not enemy["alive"]:
                continue
            dx = enemy["x"] - px
            dy = enemy["y"] - py
            dist = math.hypot(dx, dy)
            angle_to_enemy = math.atan2(dy, dx) - angle

            while angle_to_enemy > math.pi:
                angle_to_enemy -= 2 * math.pi
            while angle_to_enemy < -math.pi:
                angle_to_enemy += 2 * math.pi

            if -fov / 2 < angle_to_enemy < fov / 2:
                # --- БАГ 3 ФИКС: ограничиваем размер спрайта ---
                size = min(int(21000 / (dist + 0.1)), HEIGHT * 2)
                x = int((angle_to_enemy + fov / 2) / fov * WIDTH) - size // 2
                y = HALF_HEIGHT - size // 2 + int(v_offset)
                ray_center = int((angle_to_enemy + fov / 2) / fov * NUM_RAYS)

                half_sprite_rays = max(1, size // int(SCALE + 1) // 2)
                ray_start = max(0, ray_center - half_sprite_rays)
                ray_end = min(len(depths) - 1, ray_center + half_sprite_rays)

                max_depth = max(depths[r] for r in range(ray_start, ray_end + 1))

                if dist < max_depth:
                    if enemy.get("type") == "shooter":
                        if enemy.get("shooting_anim", 0) > 0:
                            enemy["shooting_anim"] -= 1
                            spr = shooter_sprite_shoot
                        else:
                            spr = shooter_sprite
                    else:
                        spr = enemy_sprite
                    sprite = pygame.transform.scale(spr, (size, size))
                    screen.blit(sprite, (x, y))

    def update_enemies():
        nonlocal player_hp
        for enemy in enemies:
            if not enemy["alive"]:
                continue

            dx = px - enemy["x"]
            dy = py - enemy["y"]
            dist = math.hypot(dx, dy)

            if enemy.get("type") == "shooter":
                if dist > 300:
                    move_x = dx / dist * 1.2
                    move_y = dy / dist * 1.2
                elif dist < 150:
                    move_x = -dx / dist * 1.2
                    move_y = -dy / dist * 1.2
                else:
                    move_x = 0
                    move_y = 0

                nx = enemy["x"] + move_x
                ny = enemy["y"] + move_y
                if not is_wall(nx, enemy["y"]):
                    enemy["x"] = nx
                if not is_wall(enemy["x"], ny):
                    enemy["y"] = ny

                enemy["shoot_timer"] -= 1
                if enemy["shoot_timer"] <= 0 and dist < 500:
                    enemy["shoot_timer"] = random.randint(50, 90)
                    enemy["shooting_anim"] = 15
                    shoot_angle = math.atan2(dy, dx)
                    shoot_angle += random.uniform(-0.08, 0.08)
                    enemy_bullets.append({
                        "x": enemy["x"],
                        "y": enemy["y"],
                        "angle": shoot_angle,
                        "speed": 6,
                        "life": 100,
                        "damage": 5,
                        "variant": random.randint(0, 1),
                    })

            else:
                if dist > 1:
                    move_x = dx / dist * 1.5
                    move_y = dy / dist * 1.5
                    nx = enemy["x"] + move_x
                    ny = enemy["y"] + move_y
                    if not is_wall(nx, enemy["y"]):
                        enemy["x"] = nx
                    if not is_wall(enemy["x"], ny):
                        enemy["y"] = ny

                if dist < 40:
                    player_hp -= 0.2

    def draw_lilith(depths, v_offset=0):
        if lilith is None or not lilith["alive"]:
            return
        dx = lilith["x"] - px
        dy = lilith["y"] - py
        dist = math.hypot(dx, dy)
        angle_to = math.atan2(dy, dx) - angle
        while angle_to > math.pi:
            angle_to -= 2 * math.pi
        while angle_to < -math.pi:
            angle_to += 2 * math.pi
        if -fov / 2 < angle_to < fov / 2:
            # --- БАГ 3 ФИКС: ограничиваем размер Лилит ---
            size = max(300, min(int(80000 / (dist + 0.1)), HEIGHT * 3))
            x = int((angle_to + fov / 2) / fov * WIDTH) - size // 2
            y = HALF_HEIGHT - size // 2 + int(v_offset)
            ray_center = int((angle_to + fov / 2) / fov * NUM_RAYS)
            half_rays = max(1, size // int(SCALE + 1) // 2)
            ray_start = max(0, ray_center - half_rays)
            ray_end = min(len(depths) - 1, ray_center + half_rays)
            max_depth = max(depths[r] for r in range(ray_start, ray_end + 1))
            if dist < max_depth:
                glow_size = size + 40
                glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                pulse = int(60 + 40 * math.sin(lilit_pulse_timer * 2))
                pygame.draw.ellipse(glow, (180, 0, 0, pulse),
                                    (0, 0, glow_size, glow_size))
                screen.blit(glow, (x - 20, y - 20))
                sprite = pygame.transform.scale(lilith_sprite, (size, size))
                screen.blit(sprite, (x, y))

    def check_lilith_interact():
        # --- БАГ 5 ФИКС: добавлен nonlocal spear_anim_timer ---
        nonlocal spear_unlocked, spear_anim_timer
        if lilith is None or not lilith["alive"]:
            return
        dist = math.hypot(px - lilith["x"], py - lilith["y"])
        if dist < 180 and not spear_unlocked:
            if keys[pygame.K_e]:
                spear_unlocked = True
                spear_anim_timer = 0
                lilith["gave_spear"] = True

    def draw_lilith_prompt():
        if lilith is None or not lilith["alive"] or spear_unlocked:
            return
        dist = math.hypot(px - lilith["x"], py - lilith["y"])
        if dist < 180:
            font = pygame.font.SysFont("impact", 28)
            prompt = font.render("[E]  Взять копьё Лилит", True, (255, 200, 80))
            pad = 14
            bg = pygame.Surface((prompt.get_width() + pad * 2, prompt.get_height() + pad), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            bx = WIDTH // 2 - bg.get_width() // 2
            by = HEIGHT - 90
            screen.blit(bg, (bx, by))
            screen.blit(prompt, (bx + pad, by + pad // 2))

    def draw_spear():
        """Рисует только подсказку и таймер перезарядки копья."""
        if not spear_unlocked:
            return
        font = pygame.font.SysFont("impact", 18)
        if spear_cooldown > 0:
            cd_sec = spear_cooldown / 60.0
            label = font.render(f"[F] Перезарядка... {cd_sec:.1f}с", True, (160, 120, 60))
        else:
            label = font.render("[F] Бросить копьё", True, (200, 180, 100))
        screen.blit(label, (WIDTH - label.get_width() - 10, HEIGHT - 25))

    def throw_spear():
        nonlocal spear_cooldown, spear_throw_timer
        if not spear_unlocked or spear_cooldown > 0:
            return
        spear_cooldown = 90
        spear_throw_timer = SPEAR_THROW_FRAMES
        bullets.append({
            "x": px,
            "y": py,
            "angle": angle,
            "speed": 14,
            "life": 120,
            "damage": 80,
            "is_spear": True,
        })

    def draw_spear_bullets(depths):
        for bullet in bullets:
            if not bullet.get("is_spear"):
                continue
            dx = bullet["x"] - px
            dy = bullet["y"] - py
            dist = math.hypot(dx, dy)
            angle_to = math.atan2(dy, dx) - angle
            if -fov / 2 < angle_to < fov / 2:
                size = max(16, int(800 / (dist + 0.1)))
                x = int((angle_to + fov / 2) / fov * WIDTH) - size // 2
                y = HALF_HEIGHT - size // 2
                ray = int(x / SCALE)
                if 0 < ray < len(depths) and dist < depths[ray]:
                    sprite = pygame.transform.scale(spear_img, (size, size))
                    screen.blit(sprite, (x, y))

    def draw_medkits(depths, v_offset=0):
        for med in medkits:
            if med["picked"]:
                continue
            dx = med["x"] - px
            dy = med["y"] - py
            dist = math.hypot(dx, dy)
            angle_to_med = math.atan2(dy, dx) - angle
            if -fov / 2 < angle_to_med < fov / 2:
                size = int(21000 / (dist + 0.1))
                x = int((angle_to_med + fov / 2) / fov * WIDTH) - size // 2
                y = HALF_HEIGHT - size // 2 + int(v_offset)
                ray = int(x / SCALE)
                if 0 < ray < len(depths) and dist < depths[ray]:
                    sprite = pygame.transform.scale(medkit_img, (size, size))
                    screen.blit(sprite, (x, y))

    def update_medkits():
        nonlocal player_hp
        for med in medkits:
            if med["picked"]:
                continue
            dist = math.hypot(px - med["x"], py - med["y"])
            if dist < 40:
                med["picked"] = True
                player_hp = min(player_hp + 25, max_hp)
                heal_sound.play()

    # Цвета и метки для типов патронов
    AMMO_COLORS = {
        "9mm":    (180, 220, 80),
        "shells": (220, 140, 60),
        "762":    (80, 200, 255),
        "cells":  (200, 80, 255),
    }
    AMMO_LABELS = {
        "9mm":    "9MM",
        "shells": "ДРОБЬ",
        "762":    "7.62",
        "cells":  "ЯЧЕЙКИ",
    }
    AMMO_AMOUNTS = {
        "9mm":    20,
        "shells": 8,
        "762":    40,
        "cells":  4,
    }

    def spawn_ammo_pickup(x=None, y=None, atype=None):
        if atype is None:
            atype = random.choice(list(AMMO_AMOUNTS.keys()))
        if x is None or y is None:
            for _ in range(100):
                mx = random.randint(1, len(world_map[0]) - 2)
                my = random.randint(1, len(world_map) - 2)
                if world_map[my][mx] == "0":
                    x = mx * TILE + TILE // 2
                    y = my * TILE + TILE // 2
                    break
            else:
                return
        ammo_pickups.append({
            "x": x, "y": y,
            "type": atype,
            "amount": AMMO_AMOUNTS[atype],
            "picked": False,
            "bob": random.uniform(0, math.pi * 2),
        })

    def update_ammo_pickups():
        for p in ammo_pickups:
            if p["picked"]:
                continue
            dist = math.hypot(px - p["x"], py - p["y"])
            if dist < 40:
                p["picked"] = True
                atype = p["type"]
                ammo[atype] = min(ammo[atype] + p["amount"], MAX_AMMO[atype])

    def draw_ammo_pickups(depths, v_offset=0):
        t = pygame.time.get_ticks() / 500.0
        for p in ammo_pickups:
            if p["picked"]:
                continue
            dx = p["x"] - px
            dy = p["y"] - py
            dist = math.hypot(dx, dy)
            angle_to = math.atan2(dy, dx) - angle
            while angle_to > math.pi:
                angle_to -= 2 * math.pi
            while angle_to < -math.pi:
                angle_to += 2 * math.pi
            if -fov / 2 < angle_to < fov / 2 and dist < MAX_DEPTH:
                size = max(8, min(int(10000 / (dist + 0.1)), 80))
                sx = int((angle_to + fov / 2) / fov * WIDTH) - size // 2
                bob_y = int(math.sin(t + p["bob"]) * 4)
                sy = HALF_HEIGHT - size // 2 + int(v_offset) + bob_y
                ray = max(0, min(int((angle_to + fov / 2) / fov * NUM_RAYS), len(depths) - 1))
                if dist < depths[ray]:
                    col = AMMO_COLORS[p["type"]]
                    surf = pygame.Surface((size, size), pygame.SRCALPHA)
                    glow_a = int(140 + 60 * math.sin(t * 2 + p["bob"]))
                    surf.fill((*col, glow_a))
                    screen.blit(surf, (sx, sy))
                    pygame.draw.rect(screen, col, (sx, sy, size, size), max(1, size // 12))
                    if size >= 20:
                        lbl_font = pygame.font.SysFont("impact", max(10, size // 3))
                        lbl = lbl_font.render(AMMO_LABELS[p["type"]], True, (20, 20, 20))
                        screen.blit(lbl, (sx + size // 2 - lbl.get_width() // 2,
                                          sy + size // 2 - lbl.get_height() // 2))

    def draw_ammo_hud():
        font = pygame.font.SysFont("impact", 20)
        font_big = pygame.font.SysFont("impact", 28)
        bar_w = 160
        bar_h = 14
        pad = 6
        current_atype = current_weapon.get("ammo_type")
        items = list(ammo.items())
        total_h = len(items) * (bar_h + pad + 26)
        start_y = HEIGHT - total_h - 10
        x = WIDTH - bar_w - 80

        for i, (atype, count) in enumerate(items):
            y = start_y + i * (bar_h + pad + 26)
            is_current = (atype == current_atype)
            col = AMMO_COLORS[atype]
            max_a = MAX_AMMO[atype]
            ratio = count / max_a if max_a > 0 else 0

            if is_current:
                hl = pygame.Surface((bar_w + 60, bar_h + 26), pygame.SRCALPHA)
                hl.fill((col[0], col[1], col[2], 40))
                screen.blit(hl, (x - 4, y - 4))

            label_str = f"{AMMO_LABELS[atype]}  {count}/{max_a}"
            lc = col if is_current else (140, 140, 140)
            lf = font_big if is_current else font
            lbl = lf.render(label_str, True, lc)
            screen.blit(lbl, (x, y))

            by = y + lbl.get_height() + 2
            pygame.draw.rect(screen, (40, 40, 40), (x, by, bar_w, bar_h))
            fill_col = col if count > 0 else (80, 20, 20)
            if count == 0 and (pygame.time.get_ticks() // 300) % 2 == 0:
                fill_col = (200, 0, 0)
            pygame.draw.rect(screen, fill_col, (x, by, int(bar_w * ratio), bar_h))
            border_col = col if is_current else (80, 80, 80)
            pygame.draw.rect(screen, border_col, (x, by, bar_w, bar_h),
                             2 if is_current else 1)

    # Таймер для сообщения "нет патронов"
    no_ammo_timer = 0

    def shoot():
        nonlocal gun_animating, gun_frame, no_ammo_timer
        atype = current_weapon.get("ammo_type")
        if atype and ammo.get(atype, 0) <= 0:
            no_ammo_timer = 90  # показываем сообщение 1.5 сек
            return
        if atype:
            ammo[atype] -= 1
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

    def spawn_hit_particles(enemy):
        ex, ey = enemy["x"], enemy["y"]
        dx = ex - px
        dy = ey - py
        dist = max(1, math.hypot(dx, dy))
        angle_to = math.atan2(dy, dx) - angle

        if not (-fov / 2 < angle_to < fov / 2):
            return

        screen_x = int((angle_to + fov / 2) / fov * WIDTH)
        size_base = int(21000 / (dist + 0.1))
        screen_y = HALF_HEIGHT - size_base // 2

        for _ in range(random.randint(8, 14)):
            # --- БАГ 1 ФИКС: проверяем лимит частиц ---
            if len(particles) >= MAX_PARTICLES:
                break
            vx = random.uniform(-3, 3)
            vy = random.uniform(-4, 0.5)
            color = random.choice([
                (180, 0, 0), (220, 10, 10), (140, 0, 0), (255, 30, 30)
            ])
            r = random.randint(3, 7)
            life = random.randint(15, 30)
            particles.append({
                "x": float(screen_x + random.randint(-10, 10)),
                "y": float(screen_y + random.randint(0, size_base // 2)),
                "vx": vx,
                "vy": vy,
                "color": color,
                "r": r,
                "life": life,
                "max_life": life
            })

    def update_and_draw_particles():
        for p in particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.3
            p["life"] -= 1
            if p["life"] <= 0:
                particles.remove(p)
                continue
            alpha = int(255 * p["life"] / p["max_life"])
            r = max(1, int(p["r"] * p["life"] / p["max_life"]))
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["color"], alpha), (r, r), r)
            screen.blit(surf, (int(p["x"]) - r, int(p["y"]) - r))

    def spear_explode(x, y):
        nonlocal stat_kills, stat_damage
        EXPLOSION_RADIUS = 120
        for enemy in enemies:
            if enemy["alive"]:
                dist = math.hypot(enemy["x"] - x, enemy["y"] - y)
                if dist < EXPLOSION_RADIUS:
                    dmg = int(120 * (1 - dist / EXPLOSION_RADIUS))
                    enemy["hp"] -= dmg
                    stat_damage += dmg
                    spawn_hit_particles(enemy)
                    if enemy["hp"] <= 0:
                        enemy["alive"] = False
                        stat_kills += 1
                        if random.random() < 0.3:
                            medkits.append({"x": enemy["x"], "y": enemy["y"], "picked": False})
                        if random.random() < 0.5:
                            spawn_ammo_pickup(enemy["x"], enemy["y"])

        for _ in range(40):
            # --- БАГ 1 ФИКС: проверяем лимит частиц ---
            if len(particles) >= MAX_PARTICLES:
                break
            vx = random.uniform(-5, 5)
            vy = random.uniform(-6, 1)
            color = random.choice([
                (255, 80, 0), (255, 160, 0), (200, 0, 0),
                (255, 220, 50), (180, 0, 0)
            ])
            r = random.randint(4, 10)
            life = random.randint(20, 45)

            dx = x - px
            dy = y - py
            dist = max(1, math.hypot(dx, dy))
            angle_to = math.atan2(dy, dx) - angle
            if -fov / 2 < angle_to < fov / 2:
                screen_x = int((angle_to + fov / 2) / fov * WIDTH)
                size_base = int(21000 / (dist + 0.1))
                screen_y = HALF_HEIGHT - size_base // 2

                particles.append({
                    "x": float(screen_x + random.randint(-30, 30)),
                    "y": float(screen_y + random.randint(0, max(1, size_base // 2))),
                    "vx": vx,
                    "vy": vy,
                    "color": color,
                    "r": r,
                    "life": life,
                    "max_life": life
                })

    def update_bullets():
        nonlocal stat_kills, stat_damage
        for bullet in bullets[:]:
            bullet["x"] += bullet["speed"] * math.cos(bullet["angle"])
            bullet["y"] += bullet["speed"] * math.sin(bullet["angle"])
            bullet["life"] -= 1

            mx, my = int(bullet["x"] // TILE), int(bullet["y"] // TILE)
            hit_wall = not (0 <= my < len(world_map) and 0 <= mx < len(world_map[0])) \
                       or world_map[my][mx] == "1"

            if bullet.get("is_spear") and (hit_wall or bullet["life"] <= 0):
                spear_explode(bullet["x"], bullet["y"])
                if hit_sound:
                    hit_sound.play()
                if bullet in bullets:
                    bullets.remove(bullet)
                continue

            if hit_wall or bullet["life"] <= 0:
                if bullet in bullets:
                    bullets.remove(bullet)
                continue

            if bullet.get("is_spear"):
                for enemy in enemies:
                    if enemy["alive"]:
                        if math.hypot(enemy["x"] - bullet["x"], enemy["y"] - bullet["y"]) < 35:
                            enemy["hp"] -= bullet["damage"]
                            stat_damage += bullet["damage"]
                            spawn_hit_particles(enemy)
                            if hit_sound:
                                hit_sound.play()
                            if enemy["hp"] <= 0:
                                enemy["alive"] = False
                                stat_kills += 1
                                if random.random() < 0.3:
                                    medkits.append({"x": enemy["x"], "y": enemy["y"], "picked": False})
                                if random.random() < 0.5:
                                    spawn_ammo_pickup(enemy["x"], enemy["y"])
            else:
                for enemy in enemies:
                    if enemy["alive"]:
                        if math.hypot(enemy["x"] - bullet["x"], enemy["y"] - bullet["y"]) < 20:
                            enemy["hp"] -= bullet["damage"]
                            stat_damage += bullet["damage"]
                            spawn_hit_particles(enemy)
                            if hit_sound:
                                hit_sound.play()
                            if enemy["hp"] <= 0:
                                enemy["alive"] = False
                                stat_kills += 1
                                if random.random() < 0.3:
                                    medkits.append({"x": enemy["x"], "y": enemy["y"], "picked": False})
                            if bullet in bullets:
                                bullets.remove(bullet)
                            break

    def update_enemy_bullets():
        nonlocal player_hp
        for bullet in enemy_bullets[:]:
            bullet["x"] += bullet["speed"] * math.cos(bullet["angle"])
            bullet["y"] += bullet["speed"] * math.sin(bullet["angle"])
            bullet["life"] -= 1

            mx, my = int(bullet["x"] // TILE), int(bullet["y"] // TILE)
            hit_wall = not (0 <= my < len(world_map) and 0 <= mx < len(world_map[0])) \
                       or world_map[my][mx] == "1"

            if hit_wall or bullet["life"] <= 0:
                enemy_bullets.remove(bullet)
                continue

            if math.hypot(bullet["x"] - px, bullet["y"] - py) < 20:
                player_hp -= bullet["damage"]
                enemy_bullets.remove(bullet)

    def draw_enemy_bullets(depths):
        for bullet in enemy_bullets:
            dx = bullet["x"] - px
            dy = bullet["y"] - py
            dist = math.hypot(dx, dy)
            angle_to = math.atan2(dy, dx) - angle
            while angle_to > math.pi:
                angle_to -= 2 * math.pi
            while angle_to < -math.pi:
                angle_to += 2 * math.pi
            if -fov / 2 < angle_to < fov / 2:
                size = max(8, int(400 / (dist + 0.1)))
                x = int((angle_to + fov / 2) / fov * WIDTH) - size // 2
                y = HALF_HEIGHT - size // 2
                ray = max(0, min(int((angle_to + fov / 2) / fov * NUM_RAYS), len(depths) - 1))
                if dist < depths[ray]:
                    btex = shooter_bullet_tex if bullet.get("variant", 0) == 0 else shooter_bullet_tex2
                    sprite = pygame.transform.scale(btex, (size, size))
                    screen.blit(sprite, (x, y))

    def draw_bullets(depths):
        for bullet in bullets:
            if bullet.get("is_spear"):
                continue
            dx = bullet["x"] - px
            dy = bullet["y"] - py
            dist = math.hypot(dx, dy)
            angle_to_bullet = math.atan2(dy, dx) - angle
            while angle_to_bullet > math.pi:
                angle_to_bullet -= 2 * math.pi
            while angle_to_bullet < -math.pi:
                angle_to_bullet += 2 * math.pi
            if -fov / 2 < angle_to_bullet < fov / 2:
                size = max(6, int(400 / (dist + 0.1)))
                x = int((angle_to_bullet + fov / 2) / fov * WIDTH) - size // 2
                y = HALF_HEIGHT - size // 2
                ray = max(0, min(int((angle_to_bullet + fov / 2) / fov * NUM_RAYS), len(depths) - 1))
                if dist < depths[ray]:
                    sprite = pygame.transform.scale(bullet_tex, (size, size))
                    screen.blit(sprite, (x, y))

    def draw_hp():
        bar_width = 300
        bar_height = 25
        x = 20
        y = HEIGHT - 40
        pygame.draw.rect(screen, (80, 0, 0), (x, y, bar_width, bar_height))
        hp_ratio = player_hp / max_hp
        pygame.draw.rect(screen, (200, 0, 0), (x, y, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)

    def draw_heat_bar():
        """Полоса перегрева — показывается только когда выбран пулемёт."""
        is_minigun = current_weapon.get("minigun", False)
        if not is_minigun:
            return

        bar_width = 200
        bar_height = 16
        x = 20
        y = HEIGHT - 70  # чуть выше полосы HP

        ratio = heat / MAX_HEAT

        # Цвет: зелёный → жёлтый → красный
        if ratio < 0.5:
            r = int(ratio * 2 * 255)
            g = 200
        else:
            r = 255
            g = int((1 - (ratio - 0.5) * 2) * 200)
        color = (r, g, 0)

        # Фон
        pygame.draw.rect(screen, (40, 20, 0), (x, y, bar_width, bar_height))
        # Заполнение
        pygame.draw.rect(screen, color, (x, y, int(bar_width * ratio), bar_height))
        # Рамка
        pygame.draw.rect(screen, (255, 200, 0), (x, y, bar_width, bar_height), 2)

        # Иконка 🌡 — текст-метка
        font = pygame.font.SysFont("impact", 15)
        if overheated:
            label = font.render("ПЕРЕГРЕВ!", True, (255, 60, 0))
        else:
            label = font.render("НАГРЕВ", True, (220, 180, 80))
        screen.blit(label, (x + bar_width + 8, y))

        # Мигающая рамка при перегреве
        if overheated:
            pulse = int(abs(math.sin(overheat_timer * 0.1)) * 180 + 75)
            overheat_surf = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
            overheat_surf.fill((255, 0, 0, pulse))
            screen.blit(overheat_surf, (x, y))
            pygame.draw.rect(screen, (255, 0, 0), (x, y, bar_width, bar_height), 3)

    def draw_minimap():
        scale = 15
        surf = pygame.Surface((len(world_map[0]) * scale, len(world_map) * scale))
        surf.set_alpha(200)
        surf.fill((30, 30, 30))
        for row_i, row in enumerate(world_map):
            for col_i, char in enumerate(row):
                rect = pygame.Rect(col_i * scale, row_i * scale, scale, scale)
                if char == "1":
                    pygame.draw.rect(surf, (200, 200, 200), rect)
                elif char == "E":
                    pygame.draw.rect(surf, (0, 255, 0), rect)
        pygame.draw.circle(surf, (255, 0, 0), (int(px // TILE * scale), int(py // TILE * scale)), 4)
        for enemy in enemies:
            if enemy["alive"]:
                pygame.draw.circle(surf, (255, 255, 0),
                                   (int(enemy["x"] // TILE * scale), int(enemy["y"] // TILE * scale)), 3)
        screen.blit(surf, (20, 20))

    def draw_level_stats(completed_level):
        """Экран статистики между уровнями."""
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

        seconds = stat_time_frames // 60
        minutes = seconds // 60
        secs = seconds % 60
        time_str = f"{minutes:02d}:{secs:02d}"

        font_title = pygame.font.SysFont("impact", 72)
        font_big   = pygame.font.SysFont("impact", 42)
        font_med   = pygame.font.SysFont("impact", 32)
        font_hint  = pygame.font.SysFont("impact", 24)

        # Рейтинг по убийствам
        if stat_kills >= 20:
            rank, rank_color = "S", (255, 215, 0)
        elif stat_kills >= 12:
            rank, rank_color = "A", (100, 220, 100)
        elif stat_kills >= 6:
            rank, rank_color = "B", (100, 160, 255)
        elif stat_kills >= 2:
            rank, rank_color = "C", (200, 200, 200)
        else:
            rank, rank_color = "D", (160, 80, 80)

        anim_timer = 0
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                        waiting = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False

            anim_timer += 1

            # Фон — затемнение с красным краем
            screen.fill((10, 5, 5))
            border_pulse = int(40 + 20 * math.sin(anim_timer * 0.05))
            pygame.draw.rect(screen, (border_pulse * 2, 0, 0),
                             (0, 0, WIDTH, HEIGHT), 18)

            # Заголовок
            title = font_title.render(f"УРОВЕНЬ {completed_level} — ПРОЙДЕН", True, (220, 30, 30))
            tx = WIDTH // 2 - title.get_width() // 2
            screen.blit(title, (tx, 60))

            # Разделитель
            pygame.draw.line(screen, (180, 0, 0), (WIDTH // 2 - 300, 155), (WIDTH // 2 + 300, 155), 2)

            # --- Карточки статистики ---
            card_y = 190
            card_w = 280
            card_h = 110
            gap = 30
            total_w = card_w * 3 + gap * 2
            start_x = WIDTH // 2 - total_w // 2

            cards = [
                {
                    "icon": "☠",
                    "label": "УБИТО ВРАГОВ",
                    "value": str(stat_kills),
                    "color": (220, 60, 60),
                },
                {
                    "icon": "⏱",
                    "label": "ВРЕМЯ",
                    "value": time_str,
                    "color": (80, 180, 255),
                },
                {
                    "icon": "💥",
                    "label": "НАНЕСЕНО УРОНА",
                    "value": str(stat_damage),
                    "color": (255, 160, 30),
                },
            ]

            for i, card in enumerate(cards):
                cx = start_x + i * (card_w + gap)
                # Фон карточки с пульсацией
                alpha = 160 + int(20 * math.sin(anim_timer * 0.07 + i))
                bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                bg.fill((30, 10, 10, alpha))
                screen.blit(bg, (cx, card_y))
                pygame.draw.rect(screen, card["color"], (cx, card_y, card_w, card_h), 2)

                # Метка
                lbl = font_hint.render(card["label"], True, (180, 180, 180))
                screen.blit(lbl, (cx + card_w // 2 - lbl.get_width() // 2, card_y + 10))

                # Значение — появляется с задержкой для каждой карточки
                reveal_frame = 30 + i * 20
                if anim_timer >= reveal_frame:
                    val_surf = font_big.render(card["value"], True, card["color"])
                    screen.blit(val_surf, (cx + card_w // 2 - val_surf.get_width() // 2, card_y + 48))

            # --- Рейтинг ---
            rank_y = card_y + card_h + 40
            if anim_timer >= 80:
                rank_scale = min(1.0, (anim_timer - 80) / 20)
                rank_size = int(130 * rank_scale)
                if rank_size > 10:
                    font_rank = pygame.font.SysFont("impact", rank_size)
                    rank_surf = font_rank.render(rank, True, rank_color)
                    # Свечение
                    glow = pygame.Surface((rank_surf.get_width() + 20, rank_surf.get_height() + 20),
                                         pygame.SRCALPHA)
                    glow_a = int(60 + 30 * math.sin(anim_timer * 0.1))
                    glow.fill((*rank_color, glow_a))
                    screen.blit(glow, (WIDTH // 2 - glow.get_width() // 2, rank_y - 10))
                    screen.blit(rank_surf, (WIDTH // 2 - rank_surf.get_width() // 2, rank_y))

                    rank_label = font_hint.render("РЕЙТИНГ", True, (160, 160, 160))
                    screen.blit(rank_label, (WIDTH // 2 - rank_label.get_width() // 2, rank_y - 28))

            # Подсказка
            if anim_timer > 60:
                hint_alpha = min(255, (anim_timer - 60) * 8)
                hint = font_hint.render("[ ENTER / ЛКМ ] — следующий уровень", True, (140, 140, 140))
                hint.set_alpha(hint_alpha)
                screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 55))

            pygame.display.flip()
            clock.tick(60)

        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def check_level_exit():
        nonlocal LEVEL
        mx, my = int(px // TILE), int(py // TILE)
        if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
            if world_map[my][mx] == "E":
                completed = LEVEL
                LEVEL += 1
                if LEVEL > len(levels):
                    draw_level_stats(completed)
                    print("Ты прошёл игру!")
                    pygame.quit()
                    sys.exit()
                draw_level_stats(completed)
                load_level()

    # --- БАГ 6 ФИКС: экран смерти ---
    def draw_death_screen():
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        font_big = pygame.font.SysFont("impact", 100)
        font_small = pygame.font.SysFont("impact", 36)

        death_text = font_big.render("ТЫ УМЕР", True, (200, 0, 0))
        hint_text = font_small.render("Нажми R чтобы продолжить  |  ESC для выхода", True, (200, 200, 200))

        screen.blit(death_text, (WIDTH // 2 - death_text.get_width() // 2, HEIGHT // 2 - 80))
        screen.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, HEIGHT // 2 + 60))

        pygame.display.flip()

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        waiting = False  # перезапуск
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

    sky_color = (70, 90, 160)
    floor_color = (50, 50, 50)

    lilit_title_timer = 0
    lilit_pulse_timer = 0.0
    is_lilit = False
    lilith = None

    load_level()

    running = True
    while running:
        screen.fill((50, 50, 50))

        # --- БАГ 6 ФИКС: показываем экран смерти вместо выхода ---
        if player_hp <= 0:
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
            draw_death_screen()
            # Перезапуск игры
            player_hp = 100
            LEVEL = 1
            ammo["9mm"]    = 60
            ammo["shells"] = 20
            ammo["762"]    = 120
            ammo["cells"]  = 10
            no_ammo_timer  = 0
            load_level()
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not current_weapon.get("auto", False):
                    shoot()
            if event.type == pygame.MOUSEWHEEL:
                current_weapon_index = (current_weapon_index + event.y) % len(weapons)
                current_weapon = weapons[current_weapon_index]
                fire_timer = 0
                # Сбрасываем нагрев при смене оружия
                heat = 0.0
                overheated = False
                overheat_timer = 0
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    throw_spear()

        if current_weapon.get("auto", False):
            is_minigun = current_weapon.get("minigun", False)

            if overheated:
                # Ждём полного охлаждения
                overheat_timer += 1
                heat = max(0.0, heat - HEAT_COOL_RATE * 2)
                if heat <= 0:
                    overheated = False
                    overheat_timer = 0
                fire_timer = 0
            elif pygame.mouse.get_pressed()[0]:
                fire_timer += 1
                if fire_timer >= current_weapon["fire_rate"]:
                    shoot()
                    fire_timer = 0
                    if is_minigun:
                        heat = min(MAX_HEAT, heat + HEAT_PER_SHOT)
                        if heat >= MAX_HEAT:
                            overheated = True
                # Медленное остывание во время стрельбы
                if is_minigun and not overheated:
                    heat = max(0.0, heat - HEAT_COOL_FAST)
            else:
                fire_timer = 0
                # Быстрое остывание когда не стреляем
                if is_minigun:
                    heat = max(0.0, heat - HEAT_COOL_RATE)

        if spear_cooldown > 0:
            spear_cooldown -= 1

        if spear_throw_timer > 0:
            spear_throw_timer -= 1

        # --- Счётчик времени уровня ---
        stat_time_frames += 1

        mx_rel, _ = pygame.mouse.get_rel()
        angle += mx_rel * mouse_sens

        keys = pygame.key.get_pressed()
        is_moving = False

        if keys[pygame.K_w]:
            nx = px + speed * math.cos(angle)
            ny = py + speed * math.sin(angle)
            if not is_wall(nx, ny):
                px, py = nx, ny
                is_moving = True

        if keys[pygame.K_s]:
            nx = px - speed * math.cos(angle)
            ny = py - speed * math.sin(angle)
            if not is_wall(nx, ny):
                px, py = nx, ny
                is_moving = True

        if keys[pygame.K_a]:
            nx = px + speed * math.sin(angle)
            ny = py - speed * math.cos(angle)
            if not is_wall(nx, ny):
                px, py = nx, ny
                is_moving = True

        if keys[pygame.K_d]:
            nx = px - speed * math.sin(angle)
            ny = py + speed * math.cos(angle)
            if not is_wall(nx, ny):
                px, py = nx, ny
                is_moving = True

        if is_moving:
            bob_timer += BOB_SPEED
        else:
            bob_timer += BOB_SPEED * 0.5
        bob_offset = math.sin(bob_timer) * BOB_AMPLITUDE if is_moving else \
                     math.sin(bob_timer) * BOB_AMPLITUDE * max(0, 1 - abs(math.sin(bob_timer)))

        if is_lilit:
            lilit_pulse_timer += 0.04
            pulse = (math.sin(lilit_pulse_timer) * 0.5 + 0.5)
            r = int(sky_color[0] * (0.6 + 0.4 * pulse))
            g = int(sky_color[1])
            b = int(sky_color[2])
            current_sky = (min(255, r), g, b)
        else:
            current_sky = sky_color

        pygame.draw.rect(screen, current_sky, (0, 0, WIDTH, HALF_HEIGHT + int(bob_offset) + 1))
        pygame.draw.rect(screen, floor_color, (0, HALF_HEIGHT + int(bob_offset), WIDTH, HALF_HEIGHT + BOB_AMPLITUDE + 1))

        spawn_timer += 1
        if spawn_timer >= SPAWN_DELAY and len(enemies) < MAX_ENEMIES:
            spawn_enemy()
            spawn_timer = 0

        depths = cast_walls(bob_offset)
        draw_enemies(depths, bob_offset)
        draw_lilith(depths, bob_offset)
        draw_ammo_pickups(depths, bob_offset)
        draw_bullets(depths)
        draw_spear_bullets(depths)
        update_bullets()
        update_enemy_bullets()
        draw_enemy_bullets(depths)
        update_and_draw_particles()
        update_ammo_pickups()

        if keys[pygame.K_TAB]:
            draw_minimap()

        if gun_animating:
            gun_frame += gun_anim_speed
            if gun_frame >= len(current_weapon["frames"]):
                gun_animating = False
                gun_frame = 0

        # Основное оружие скрыто пока идёт анимация броска копья
        if spear_throw_timer <= 0:
            gun_bob_x = math.sin(bob_timer) * 6 if is_moving else 0
            gun_bob_y = abs(math.sin(bob_timer)) * 5 if is_moving else 0
            frame_image = current_weapon["frames"][int(gun_frame)] if gun_animating else current_weapon["frames"][0]
            gun = pygame.transform.scale(frame_image, (300, 200))
            x_offset = 0 if current_weapon["name"] == "Rifle" else 60
            screen.blit(gun, (WIDTH // 2 - 150 + x_offset + int(gun_bob_x),
                               HEIGHT - 200 + int(gun_bob_y)))
        else:
            # Во время броска — рисуем анимацию копья справа
            gun_bob_x = math.sin(bob_timer) * 6 if is_moving else 0
            gun_bob_y = abs(math.sin(bob_timer)) * 5 if is_moving else 0
            progress = 1.0 - spear_throw_timer / SPEAR_THROW_FRAMES

            gun_w, gun_h = 340, 220
            base_x = WIDTH - gun_w - 10 + int(gun_bob_x)
            base_y = HEIGHT - gun_h + int(gun_bob_y)

            if progress < 0.4:
                t = progress / 0.4
                off_x = int(t * 60)
                off_y = int(-t * 50)
                img = pygame.transform.scale(spear_frames[1], (gun_w, gun_h))
                img.set_alpha(255)
                screen.blit(img, (base_x + off_x, base_y + off_y))
            else:
                t = (progress - 0.4) / 0.6
                off_x = int(t * 100)
                off_y = int(t * 60)
                img = pygame.transform.scale(spear_frames[1], (gun_w, gun_h))
                img.set_alpha(max(0, int(255 * (1.0 - t))))
                screen.blit(img, (base_x + off_x, base_y + off_y))

        draw_spear()   # копьё рисуется поверх / вместо оружия

        update_enemies()
        draw_hp()
        draw_heat_bar()
        draw_ammo_hud()

        # Сообщение "нет патронов"
        if no_ammo_timer > 0:
            no_ammo_timer -= 1
            alpha = min(255, no_ammo_timer * 6)
            na_font = pygame.font.SysFont("impact", 36)
            na_surf = na_font.render("НЕТ ПАТРОНОВ!", True, (255, 60, 60))
            na_surf.set_alpha(alpha)
            screen.blit(na_surf, (WIDTH // 2 - na_surf.get_width() // 2, HEIGHT // 2 - 80))

        check_lilith_interact()
        draw_lilith_prompt()
        check_level_exit()
        draw_medkits(depths, bob_offset)
        update_medkits()

        if is_lilit:
            vign_size = 120
            pulse_a = int(80 + 60 * math.sin(lilit_pulse_timer * 0.7))
            for side, rect in [
                ("left",   (0, 0, vign_size, HEIGHT)),
                ("right",  (WIDTH - vign_size, 0, vign_size, HEIGHT)),
                ("top",    (0, 0, WIDTH, vign_size)),
                ("bottom", (0, HEIGHT - vign_size, WIDTH, vign_size)),
            ]:
                vsurf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
                vsurf.fill((120, 0, 0, pulse_a))
                screen.blit(vsurf, (rect[0], rect[1]))

            if lilit_title_timer > 0:
                lilit_title_timer -= 1
                alpha = min(255, lilit_title_timer * 4, (180 - lilit_title_timer) * 4 + 50)
                font_big = pygame.font.SysFont("impact", 120)
                title_surf = font_big.render("L I L I T", True, (255, 30, 30))
                title_surf.set_alpha(max(0, alpha))
                tx = WIDTH // 2 - title_surf.get_width() // 2
                ty = HEIGHT // 2 - title_surf.get_height() // 2
                screen.blit(title_surf, (tx, ty))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()

    WIDTH, HEIGHT = 1360, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("not DOOM THE KILL FYRRE")

    if run_menu(screen):
        run_game(screen)