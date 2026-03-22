import pygame
import sys

# ── Цвета ──────────────────────────────────────────────
WHITE        = (255, 255, 255)
BTN_NORMAL   = (20,  20,  20)
BTN_HOVER    = (180, 30,  30)
BTN_BORDER   = (220, 80,  0)
BTN_BORDER_H = (255, 200, 0)
TEXT_NORMAL  = (220, 180, 100)
TEXT_HOVER   = (255, 255, 255)

# ── Доступные разрешения ────────────────────────────────
RESOLUTIONS = [
    (1024, 600),
    (1280, 720),
    (1360, 800),
    (1600, 900),
    (1920, 1080),
]

# Глобальные настройки (читаются из game.py если нужно)
menu_settings = {
    "volume":     0.8,
    "resolution": (1360, 800),
}


class Button:
    def __init__(self, text, center, font, width=320, height=58):
        self.text   = text
        self.font   = font
        self.width  = width
        self.height = height
        self.rect   = pygame.Rect(0, 0, width, height)
        self.rect.center = center
        self.hover_progress = 0.0
        self.ANIM_SPEED     = 0.10

    def set_text(self, text):
        self.text = text

    def update(self, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        if hovered:
            self.hover_progress = min(1.0, self.hover_progress + self.ANIM_SPEED)
        else:
            self.hover_progress = max(0.0, self.hover_progress - self.ANIM_SPEED)

    def draw(self, surface):
        t = self.hover_progress

        bg         = tuple(int(BTN_NORMAL[i] + (BTN_HOVER[i]    - BTN_NORMAL[i])   * t) for i in range(3))
        border     = tuple(int(BTN_BORDER[i] + (BTN_BORDER_H[i] - BTN_BORDER[i])   * t) for i in range(3))
        text_color = tuple(int(TEXT_NORMAL[i] + (TEXT_HOVER[i]  - TEXT_NORMAL[i])  * t) for i in range(3))

        expand    = int(8 * t)
        draw_rect = self.rect.inflate(expand, expand // 2)

        btn_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
        btn_surf.fill((*bg, 200))
        surface.blit(btn_surf, draw_rect.topleft)

        pygame.draw.rect(surface, border, draw_rect, width=2, border_radius=4)

        sz = 10
        x, y, w, h = draw_rect
        for cx, cy, dx, dy in [(x,y,1,1),(x+w,y,-1,1),(x,y+h,1,-1),(x+w,y+h,-1,-1)]:
            pygame.draw.line(surface, border, (cx, cy), (cx + dx*sz, cy), 2)
            pygame.draw.line(surface, border, (cx, cy), (cx, cy + dy*sz), 2)

        label      = self.font.render(self.text, True, text_color)
        label_rect = label.get_rect(center=draw_rect.center)
        surface.blit(label, label_rect)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


def draw_slider(surface, font, label, val, min_v, max_v, sx, sy, sw, mouse_pos, pressed, drag_key, dragging_ref):
    """
    Рисует слайдер. Возвращает (новое_значение, новый_drag_key).
    dragging_ref — строка-ключ текущего перетаскиваемого слайдера или None.
    """
    import math

    sh = 10
    ratio  = (val - min_v) / (max_v - min_v)
    handle = int(sx + ratio * sw)
    cy     = sy + sh // 2

    # Трек
    pygame.draw.rect(surface, (50, 30, 10), (sx, cy - sh // 2, sw, sh), border_radius=5)
    pygame.draw.rect(surface, (220, 100, 0), (sx, cy - sh // 2, int(ratio * sw), sh), border_radius=5)

    # Ручка
    hov = math.hypot(mouse_pos[0] - handle, mouse_pos[1] - cy) < 14
    r   = 13 if (hov or dragging_ref == drag_key) else 10
    pygame.draw.circle(surface, (255, 220, 100) if hov else (220, 130, 0), (handle, cy), r)
    pygame.draw.circle(surface, (255, 160, 0), (handle, cy), r, 2)

    # Начало перетаскивания
    if pressed and hov and dragging_ref is None:
        dragging_ref = drag_key

    # Обновление значения при перетаскивании
    if dragging_ref == drag_key:
        new_ratio = max(0.0, min(1.0, (mouse_pos[0] - sx) / sw))
        val = min_v + new_ratio * (max_v - min_v)

    # Подпись слева и значение справа
    lbl_s  = font.render(label, True, (220, 180, 100))
    if drag_key == "vol":
        val_str = f"{int(val * 100)}%"
    else:
        val_str = str(int(val))
    val_s  = font.render(val_str, True, (255, 255, 255))
    surface.blit(lbl_s, (sx, sy - 30))
    surface.blit(val_s, (sx + sw - val_s.get_width(), sy - 30))

    return val, dragging_ref


def run_settings(screen, bg):
    import math

    clock = pygame.time.Clock()
    WIDTH, HEIGHT = screen.get_size()

    font_title = pygame.font.SysFont("impact", 54)
    font       = pygame.font.SysFont("arial", 34, bold=True)
    font_small = pygame.font.SysFont("arial", 24)
    font_hint  = pygame.font.SysFont("arial", 20)

    # Рабочие копии
    tmp_vol = menu_settings["volume"]
    cur_res_idx = RESOLUTIONS.index(menu_settings["resolution"]) \
                  if menu_settings["resolution"] in RESOLUTIONS else 2

    dragging = None  # "vol" | None

    # Кнопки разрешения: стрелки влево/вправо
    arrow_y   = HEIGHT // 2 + 30
    arrow_sz  = 44
    res_lx    = WIDTH // 2 - 180   # левая стрелка центр x
    res_rx    = WIDTH // 2 + 180   # правая стрелка центр x
    left_rect  = pygame.Rect(res_lx  - arrow_sz // 2, arrow_y - arrow_sz // 2, arrow_sz, arrow_sz)
    right_rect = pygame.Rect(res_rx  - arrow_sz // 2, arrow_y - arrow_sz // 2, arrow_sz, arrow_sz)

    # Кнопки Применить / Назад
    apply_btn = Button("✔  ПРИМЕНИТЬ", (WIDTH // 2, HEIGHT - 170), font, width=300, height=55)
    back_btn  = Button("← НАЗАД",      (WIDTH // 2, HEIGHT - 100), font, width=260, height=55)

    # Зона слайдера громкости
    sl_x = WIDTH // 2 - 220
    sl_w = 440
    sl_y = HEIGHT // 2 - 100

    need_restart_hint = False

    while True:
        mouse     = pygame.mouse.get_pos()
        pressed   = pygame.mouse.get_pressed()[0]

        if not pressed:
            dragging = None

        # ── Рисуем фон ──
        screen.blit(bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))

        # Панель
        panel_w, panel_h = 560, 420
        panel_x = WIDTH  // 2 - panel_w // 2
        panel_y = HEIGHT // 2 - panel_h // 2 - 20
        panel   = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((18, 8, 0, 220))
        screen.blit(panel, (panel_x, panel_y))
        pygame.draw.rect(screen, (200, 80, 0), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=10)

        # Заголовок
        title = font_title.render("НАСТРОЙКИ", True, (255, 140, 0))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, panel_y + 44)))
        pygame.draw.line(screen, (180, 60, 0),
                         (panel_x + 30, panel_y + 80),
                         (panel_x + panel_w - 30, panel_y + 80), 1)

        # ── Слайдер громкости ──
        tmp_vol, dragging = draw_slider(
            screen, font_small, "Громкость", tmp_vol, 0.0, 1.0,
            sl_x, sl_y, sl_w, mouse, pressed, "vol", dragging
        )
        pygame.mixer.music.set_volume(tmp_vol)   # превью в реальном времени

        # ── Выбор разрешения ──
        res_label = font_small.render("Разрешение экрана", True, (220, 180, 100))
        screen.blit(res_label, res_label.get_rect(center=(WIDTH // 2, arrow_y - 36)))

        cur_res = RESOLUTIONS[cur_res_idx]
        res_str = f"{cur_res[0]}  ×  {cur_res[1]}"
        res_surf = font.render(res_str, True, (255, 255, 200))
        screen.blit(res_surf, res_surf.get_rect(center=(WIDTH // 2, arrow_y + arrow_sz // 2 - 2)))

        # Стрелки
        for rect, sym, active in [
            (left_rect,  "◀", cur_res_idx > 0),
            (right_rect, "▶", cur_res_idx < len(RESOLUTIONS) - 1),
        ]:
            hov = rect.collidepoint(mouse) and active
            col = (255, 180, 0) if hov else ((160, 100, 0) if active else (60, 40, 0))
            bg_col = (80, 30, 0, 180) if hov else (30, 15, 0, 150)
            s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            s.fill(bg_col)
            screen.blit(s, rect.topleft)
            pygame.draw.rect(screen, col, rect, 2, border_radius=6)
            sym_s = font.render(sym, True, col)
            screen.blit(sym_s, sym_s.get_rect(center=rect.center))

        # Подсказка о перезапуске
        if need_restart_hint:
            hint = font_hint.render("⚠  Разрешение применится после перезапуска игры", True, (255, 200, 60))
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, arrow_y + 58)))

        # Кнопки
        apply_btn.update(mouse)
        apply_btn.draw(screen)
        back_btn.update(mouse)
        back_btn.draw(screen)

        # ── События ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Стрелки разрешения
                if left_rect.collidepoint(mouse) and cur_res_idx > 0:
                    cur_res_idx -= 1
                if right_rect.collidepoint(mouse) and cur_res_idx < len(RESOLUTIONS) - 1:
                    cur_res_idx += 1

                if apply_btn.is_clicked(mouse):
                    menu_settings["volume"]     = tmp_vol
                    menu_settings["resolution"] = RESOLUTIONS[cur_res_idx]
                    pygame.mixer.music.set_volume(tmp_vol)
                    # Меняем разрешение окна
                    new_res = RESOLUTIONS[cur_res_idx]
                    if new_res != screen.get_size():
                        screen = pygame.display.set_mode(new_res)
                        WIDTH, HEIGHT = screen.get_size()
                        # Пересчитываем позиции под новый размер
                        sl_x = WIDTH // 2 - 220
                        sl_y = HEIGHT // 2 - 100
                        arrow_y  = HEIGHT // 2 + 30
                        res_lx   = WIDTH // 2 - 180
                        res_rx   = WIDTH // 2 + 180
                        left_rect  = pygame.Rect(res_lx - arrow_sz // 2, arrow_y - arrow_sz // 2, arrow_sz, arrow_sz)
                        right_rect = pygame.Rect(res_rx - arrow_sz // 2, arrow_y - arrow_sz // 2, arrow_sz, arrow_sz)
                        panel_x  = WIDTH  // 2 - panel_w // 2
                        panel_y  = HEIGHT // 2 - panel_h // 2 - 20
                        apply_btn = Button("✔  ПРИМЕНИТЬ", (WIDTH // 2, HEIGHT - 170), font, width=300, height=55)
                        back_btn  = Button("← НАЗАД",      (WIDTH // 2, HEIGHT - 100), font, width=260, height=55)
                        try:
                            bg_raw = pygame.image.load("image/fon.png").convert()
                            bg     = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
                        except Exception:
                            bg = pygame.Surface((WIDTH, HEIGHT))
                            bg.fill((20, 20, 20))

                if back_btn.is_clicked(mouse):
                    return

        pygame.display.flip()
        clock.tick(60)


def run_menu(screen):
    WIDTH, HEIGHT = screen.get_size()
    clock = pygame.time.Clock()

    try:
        bg_raw = pygame.image.load("image/fon.png").convert()
        bg     = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
    except Exception:
        bg = pygame.Surface((WIDTH, HEIGHT))
        bg.fill((20, 20, 20))

    font_btn   = pygame.font.SysFont("arial",  38, bold=True)
    font_title = pygame.font.SysFont("impact", 90, bold=True)
    font_sub   = pygame.font.SysFont("arial",  22)

    buttons = {
        "start":    Button("▶  СТАРТ",     (WIDTH // 2, HEIGHT - 280), font_btn),
        "settings": Button("⚙  НАСТРОЙКИ", (WIDTH // 2, HEIGHT - 210), font_btn),
        "exit":     Button("✕  ВЫХОД",     (WIDTH // 2, HEIGHT - 140), font_btn),
    }

    while True:
        # Если разрешение поменялось в настройках — обновляем
        cur_size = screen.get_size()
        if cur_size != (WIDTH, HEIGHT):
            WIDTH, HEIGHT = cur_size
            try:
                bg_raw = pygame.image.load("image/fon.png").convert()
                bg     = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
            except Exception:
                bg = pygame.Surface((WIDTH, HEIGHT))
                bg.fill((20, 20, 20))
            buttons = {
                "start":    Button("▶  СТАРТ",     (WIDTH // 2, HEIGHT - 280), font_btn),
                "settings": Button("⚙  НАСТРОЙКИ", (WIDTH // 2, HEIGHT - 210), font_btn),
                "exit":     Button("✕  ВЫХОД",     (WIDTH // 2, HEIGHT - 140), font_btn),
            }

        screen.blit(bg, (0, 0))

        grad = pygame.Surface((WIDTH, HEIGHT // 2), pygame.SRCALPHA)
        for i in range(grad.get_height()):
            alpha = int(210 * i / grad.get_height())
            pygame.draw.line(grad, (0, 0, 0, alpha), (0, i), (WIDTH, i))
        screen.blit(grad, (0, HEIGHT // 2))

        shadow = font_title.render("NOT DOOM", True, (80, 0, 0))
        title  = font_title.render("NOT DOOM", True, (255, 80, 0))
        screen.blit(shadow, shadow.get_rect(center=(WIDTH // 2 + 4, HEIGHT - 416)))
        screen.blit(title,  title.get_rect(center=(WIDTH // 2,     HEIGHT - 420)))

        sub = font_sub.render("THE KILL FYRRE", True, (200, 160, 80))
        screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT - 360)))

        mouse = pygame.mouse.get_pos()
        for btn in buttons.values():
            btn.update(mouse)
            btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if buttons["start"].is_clicked(mouse):
                    return True
                if buttons["settings"].is_clicked(mouse):
                    run_settings(screen, bg)
                if buttons["exit"].is_clicked(mouse):
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((1360, 800))
    pygame.display.set_caption("NOT DOOM")
    run_menu(screen)
    pygame.quit()