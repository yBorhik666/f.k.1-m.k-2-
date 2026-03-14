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

    bullets = []
    enemies = []
    spawn_timer = 0
    medkits = []

    # --- Camera bob state ---
    bob_timer = 0.0
    bob_offset = 0.0          # вертикальное смещение «камеры»
    BOB_SPEED = 0.12          # скорость качания
    BOB_AMPLITUDE = 8         # амплитуда в пикселях

    # --- Hit particles ---
    particles = []            # список частичек

    # --- Hit sound (генерируем программно если нет файла, иначе грузим) ---
    hit_sound = None
    hit_sound_path = "sound/hit.wav"
    if os.path.exists(hit_sound_path):
        hit_sound = pygame.mixer.Sound(hit_sound_path)
    else:
        # Генерируем простой «шлепок» через синтез
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
    lilith_sprite = pygame.image.load("image/lilith.png").convert_alpha()
    spear_img = pygame.image.load("image/spear_of_lilith.png").convert_alpha()
    load_weapon_textures()
    bullet_tex = pygame.image.load("image/bullet_0.png").convert_alpha()
    heal_sound = pygame.mixer.Sound("sound/medik.wav")
    TEX_SIZE = wall_tex.get_width()

    # --- Lilith boss entity ---
    lilith = None   # None если не заспавнена / убита

    current_weapon_index = 0
    current_weapon = weapons[current_weapon_index]
    gun_frame = 0
    gun_animating = False
    gun_anim_speed = 0.2

    world_map = []
    MAX_ENEMIES = 5
    SPAWN_DELAY = 120

    def load_level():
        nonlocal world_map, MAX_ENEMIES, SPAWN_DELAY, px, py
        nonlocal sky_color, floor_color, is_lilit, lilit_title_timer, lilith
        nonlocal spear_unlocked, spear_cooldown

        enemies.clear()
        medkits.clear()
        lilith = None
        spear_unlocked = False
        spear_cooldown = 0

        if LEVEL in levels:
            level_data = levels[LEVEL]
        else:
            level_data = levels[1]

        world_map = level_data["map"]
        MAX_ENEMIES = level_data["max_enemies"]
        SPAWN_DELAY = level_data["spawn_delay"]
        sky_color = level_data.get("sky_color", (70, 90, 160))

        # Особые параметры для уровня Лилит
        is_lilit = level_data.get("name", "") == "LILIT"
        if is_lilit:
            floor_color = (40, 0, 0)
            lilit_title_timer = 180
            # Ищем 'L' на карте — позиция Лилит-NPC
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
                    enemies.append({"x": x, "y": y, "alive": True, "hp": 10})
                    break

    def cast_walls(v_offset=0):
        """v_offset — вертикальный сдвиг в пикселях (camera bob)."""
        ray_angle = angle - fov / 2
        depths = []
        x_pos = 0

        for ray in range(NUM_RAYS):
            sin_a = math.sin(ray_angle)
            cos_a = math.cos(ray_angle)
            depth = 1
            hit = False
            x, y = px, py

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
                depth += 4

            if hit:
                depth *= math.cos(angle - ray_angle)
                proj_h = 21000 / (depth + 0.0001)
                hit_x = int(x) % TILE
                tex_x = int(hit_x * TEX_SIZE / TILE)
                column = wall_tex.subsurface(tex_x, 0, 1, TEX_SIZE)
                column = pygame.transform.scale(column, (int(SCALE) + 1, int(proj_h)))
                # применяем вертикальный сдвиг bob
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

            # нормализуем угол в [-pi, pi]
            while angle_to_enemy > math.pi:
                angle_to_enemy -= 2 * math.pi
            while angle_to_enemy < -math.pi:
                angle_to_enemy += 2 * math.pi

            if -fov / 2 < angle_to_enemy < fov / 2:
                size = int(21000 / (dist + 0.1))
                x = int((angle_to_enemy + fov / 2) / fov * WIDTH) - size // 2
                y = HALF_HEIGHT - size // 2 + int(v_offset)
                ray_center = int((angle_to_enemy + fov / 2) / fov * NUM_RAYS)

                # проверяем диапазон лучей по ширине спрайта
                half_sprite_rays = max(1, size // int(SCALE + 1) // 2)
                ray_start = max(0, ray_center - half_sprite_rays)
                ray_end = min(len(depths) - 1, ray_center + half_sprite_rays)

                # берём максимальную глубину — враг виден если хоть один луч не перекрыт
                max_depth = max(depths[r] for r in range(ray_start, ray_end + 1))

                if dist < max_depth:
                    sprite = pygame.transform.scale(enemy_sprite, (size, size))
                    screen.blit(sprite, (x, y))

    def update_enemies():
        nonlocal player_hp
        for enemy in enemies:
            if not enemy["alive"]:
                continue
            dx = px - enemy["x"]
            dy = py - enemy["y"]
            dist = math.hypot(dx, dy)
            if dist < 40:
                player_hp -= 0.2

    def draw_lilith(depths, v_offset=0):
        """Рисует Лилит — большой босс-спрайт с кровавым свечением."""
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
            # Лилит в 2x больше обычного врага
            size = int(32000 / (dist + 0.1))
            x = int((angle_to + fov / 2) / fov * WIDTH) - size // 2
            y = HALF_HEIGHT - size // 2 + int(v_offset)
            ray_center = int((angle_to + fov / 2) / fov * NUM_RAYS)
            half_rays = max(1, size // int(SCALE + 1) // 2)
            ray_start = max(0, ray_center - half_rays)
            ray_end = min(len(depths) - 1, ray_center + half_rays)
            max_depth = max(depths[r] for r in range(ray_start, ray_end + 1))
            if dist < max_depth:
                # Красное свечение вокруг
                glow_size = size + 20
                glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                pulse = int(60 + 40 * math.sin(lilit_pulse_timer * 2))
                pygame.draw.ellipse(glow, (180, 0, 0, pulse),
                                    (0, 0, glow_size, glow_size))
                screen.blit(glow, (x - 10, y - 10))
                sprite = pygame.transform.scale(lilith_sprite, (size, size))
                screen.blit(sprite, (x, y))

    def check_lilith_interact():
        """Проверяет подход к Лилит и выдаёт копьё по E."""
        nonlocal spear_unlocked, spear_anim_timer
        if lilith is None or not lilith["alive"]:
            return
        dist = math.hypot(px - lilith["x"], py - lilith["y"])
        if dist < 100 and not spear_unlocked:
            if keys[pygame.K_e]:
                spear_unlocked = True
                spear_anim_timer = 0
                lilith["gave_spear"] = True

    def draw_lilith_prompt():
        """Подсказка [E] внизу экрана когда рядом с Лилит."""
        if lilith is None or not lilith["alive"] or spear_unlocked:
            return
        dist = math.hypot(px - lilith["x"], py - lilith["y"])
        if dist < 100:
            font = pygame.font.SysFont("impact", 28)
            prompt = font.render("[E]  Взять копьё Лилит", True, (255, 200, 80))
            # фон-плашка
            pad = 14
            bg = pygame.Surface((prompt.get_width() + pad * 2, prompt.get_height() + pad), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            bx = WIDTH // 2 - bg.get_width() // 2
            by = HEIGHT - 90
            screen.blit(bg, (bx, by))
            screen.blit(prompt, (bx + pad, by + pad // 2))

    def draw_spear():
        """Рисует копьё в правом нижнем углу если разблокировано."""
        if not spear_unlocked:
            return
        gun_w, gun_h = 280, 160
        scaled = pygame.transform.scale(spear_img, (gun_w, gun_h))
        # лёгкое покачивание как у оружия
        bob_x = int(math.sin(bob_timer) * 6) if is_moving else 0
        bob_y = int(abs(math.sin(bob_timer)) * 5) if is_moving else 0
        screen.blit(scaled, (WIDTH - gun_w - 20 + bob_x, HEIGHT - gun_h - 10 + bob_y))
        # кулдаун затемнение
        if spear_cooldown > 0:
            cd_surf = pygame.Surface((gun_w, gun_h), pygame.SRCALPHA)
            alpha = int(160 * spear_cooldown / 90)
            cd_surf.fill((0, 0, 0, alpha))
            screen.blit(cd_surf, (WIDTH - gun_w - 20 + bob_x, HEIGHT - gun_h - 10 + bob_y))
        # Подсказка F
        font = pygame.font.SysFont("impact", 18)
        label = font.render("[F] Бросить копьё", True, (200, 180, 100))
        screen.blit(label, (WIDTH - label.get_width() - 10, HEIGHT - 25))

    def throw_spear():
        """Бросок копья — мощный снаряд с большим уроном."""
        nonlocal spear_cooldown
        if not spear_unlocked or spear_cooldown > 0:
            return
        spear_cooldown = 90   # кулдаун ~1.5 сек
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
        """Рисует летящие копья спрайтом."""
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

    def shoot():
        nonlocal gun_animating, gun_frame
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
        """Создаём брызги крови в точке врага."""
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
            p["vy"] += 0.3   # гравитация
            p["life"] -= 1
            if p["life"] <= 0:
                particles.remove(p)
                continue
            alpha = int(255 * p["life"] / p["max_life"])
            r = max(1, int(p["r"] * p["life"] / p["max_life"]))
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["color"], alpha), (r, r), r)
            screen.blit(surf, (int(p["x"]) - r, int(p["y"]) - r))

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
                    hitbox = 35 if bullet.get("is_spear") else 20
                    if math.hypot(enemy["x"] - bullet["x"], enemy["y"] - bullet["y"]) < hitbox:
                        enemy["hp"] -= bullet["damage"]
                        spawn_hit_particles(enemy)
                        if hit_sound:
                            hit_sound.play()
                        if enemy["hp"] <= 0:
                            enemy["alive"] = False
                            if random.random() < 0.3:
                                medkits.append({"x": enemy["x"], "y": enemy["y"], "picked": False})
                        if bullet in bullets:
                            bullets.remove(bullet)
                        break

    def draw_bullets(depths):
        for bullet in bullets:
            dx = bullet["x"] - px
            dy = bullet["y"] - py
            dist = math.hypot(dx, dy)
            angle_to_bullet = math.atan2(dy, dx) - angle
            if -fov / 2 < angle_to_bullet < fov / 2:
                size = max(4, int(300 / (dist + 0.1)))
                x = int((angle_to_bullet + fov / 2) / fov * WIDTH) - size // 2
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
        pygame.draw.rect(screen, (80, 0, 0), (x, y, bar_width, bar_height))
        hp_ratio = player_hp / max_hp
        pygame.draw.rect(screen, (200, 0, 0), (x, y, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)

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

    def check_level_exit():
        nonlocal LEVEL
        mx, my = int(px // TILE), int(py // TILE)
        if 0 <= my < len(world_map) and 0 <= mx < len(world_map[0]):
            if world_map[my][mx] == "E":
                LEVEL += 1
                if LEVEL > len(levels):
                    print("Ты прошёл игру!")
                    pygame.quit()
                    sys.exit()
                load_level()

    sky_color = (70, 90, 160)   # цвет неба, меняется с уровнем
    floor_color = (50, 50, 50)  # цвет пола

    # --- Lilit atmosphere ---
    lilit_title_timer = 0
    lilit_pulse_timer = 0.0
    is_lilit = False
    lilith = None

    # --- Копьё Лилит ---
    spear_unlocked = False      # получено ли копьё
    spear_cooldown = 0          # кулдаун броска
    spear_anim_timer = 0        # не используется, резерв

    load_level()

    running = True
    while running:
        screen.fill((50, 50, 50))  # заливаем цветом пола — убирает чёрную полосу снизу

        if player_hp <= 0:
            print("Ты умер")
            pygame.quit()
            sys.exit()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                shoot()
            if event.type == pygame.MOUSEWHEEL:
                current_weapon_index = (current_weapon_index + event.y) % len(weapons)
                current_weapon = weapons[current_weapon_index]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    throw_spear()

        # Кулдаун копья
        if spear_cooldown > 0:
            spear_cooldown -= 1

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

        # --- Camera bob update ---
        if is_moving:
            bob_timer += BOB_SPEED
        else:
            # плавно возвращаем к нулю
            bob_timer += BOB_SPEED * 0.5
        bob_offset = math.sin(bob_timer) * BOB_AMPLITUDE if is_moving else \
                     math.sin(bob_timer) * BOB_AMPLITUDE * max(0, 1 - abs(math.sin(bob_timer)))

        # --- Lilit: пульсация неба ---
        if is_lilit:
            lilit_pulse_timer += 0.04
            pulse = (math.sin(lilit_pulse_timer) * 0.5 + 0.5)  # 0..1
            r = int(sky_color[0] * (0.6 + 0.4 * pulse))
            g = int(sky_color[1])
            b = int(sky_color[2])
            current_sky = (min(255, r), g, b)
        else:
            current_sky = sky_color

        # Небо и пол со смещением (с запасом чтобы не было чёрных полос)
        pygame.draw.rect(screen, current_sky, (0, 0, WIDTH, HALF_HEIGHT + int(bob_offset) + 1))
        pygame.draw.rect(screen, floor_color, (0, HALF_HEIGHT + int(bob_offset), WIDTH, HALF_HEIGHT + BOB_AMPLITUDE + 1))

        spawn_timer += 1
        if spawn_timer >= SPAWN_DELAY and len(enemies) < MAX_ENEMIES:
            spawn_enemy()
            spawn_timer = 0

        depths = cast_walls(bob_offset)
        draw_enemies(depths, bob_offset)
        draw_lilith(depths, bob_offset)
        draw_bullets(depths)
        draw_spear_bullets(depths)
        update_bullets()
        update_and_draw_particles()  # частички поверх всего 3D

        if keys[pygame.K_TAB]:
            draw_minimap()

        if gun_animating:
            gun_frame += gun_anim_speed
            if gun_frame >= len(current_weapon["frames"]):
                gun_animating = False
                gun_frame = 0

        # Gun bob: пушка тоже покачивается
        gun_bob_x = math.sin(bob_timer) * 6 if is_moving else 0
        gun_bob_y = abs(math.sin(bob_timer)) * 5 if is_moving else 0

        frame_image = current_weapon["frames"][int(gun_frame)] if gun_animating else current_weapon["frames"][0]
        gun = pygame.transform.scale(frame_image, (300, 200))
        x_offset = 0 if current_weapon["name"] == "Rifle" else 60
        screen.blit(gun, (WIDTH // 2 - 150 + x_offset + int(gun_bob_x),
                           HEIGHT - 200 + int(gun_bob_y)))

        update_enemies()
        draw_hp()
        check_lilith_interact()
        draw_lilith_prompt()
        draw_spear()
        check_level_exit()
        draw_medkits(depths, bob_offset)
        update_medkits()

        # --- Lilit спецэффекты поверх UI ---
        if is_lilit:
            # Красный виньет по краям экрана
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

            # Надпись LILIT при входе на уровень
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


# ✅ Точка входа
if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()

    WIDTH, HEIGHT = 1360, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("not DOOM THE KILL FYRRE")

    if run_menu(screen):
        run_game(screen)