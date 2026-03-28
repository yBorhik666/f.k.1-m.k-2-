import pygame
import sys
import json
import os

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

menu_settings = {
    "volume":     0.8,
    "resolution": (1360, 800),
}

SAVE_FILE = "savegame.json"


# ═══════════════════════ СОХРАНЕНИЕ / ЗАГРУЗКА ═══════════════════════════════

def save_game(state: dict):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        print(f"[SAVE] Сохранено в {SAVE_FILE}")
        return True
    except Exception as e:
        print(f"[SAVE] Ошибка сохранения: {e}")
        return False


def load_game() -> dict | None:
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        print(f"[LOAD] Загружено из {SAVE_FILE}")
        return state
    except Exception as e:
        print(f"[LOAD] Ошибка загрузки: {e}")
        return None


def has_save() -> bool:
    return os.path.exists(SAVE_FILE)


# ═══════════════════════════ КНОПКА ══════════════════════════════════════════

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
        bg         = tuple(int(BTN_NORMAL[i] + (BTN_HOVER[i]    - BTN_NORMAL[i])  * t) for i in range(3))
        border     = tuple(int(BTN_BORDER[i] + (BTN_BORDER_H[i] - BTN_BORDER[i])  * t) for i in range(3))
        text_color = tuple(int(TEXT_NORMAL[i] + (TEXT_HOVER[i]  - TEXT_NORMAL[i]) * t) for i in range(3))
        expand    = int(8 * t)
        draw_rect = self.rect.inflate(expand, expand // 2)
        btn_surf  = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
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


# ═══════════════════════ СЛАЙДЕР ═════════════════════════════════════════════

def draw_slider(surface, font, label, val, min_v, max_v, sx, sy, sw, mouse_pos, pressed, drag_key, dragging_ref):
    import math
    sh = 10
    ratio  = (val - min_v) / (max_v - min_v)
    handle = int(sx + ratio * sw)
    cy     = sy + sh // 2
    pygame.draw.rect(surface, (50, 30, 10),  (sx, cy - sh//2, sw, sh), border_radius=5)
    pygame.draw.rect(surface, (220, 100, 0), (sx, cy - sh//2, int(ratio * sw), sh), border_radius=5)
    hov = math.hypot(mouse_pos[0] - handle, mouse_pos[1] - cy) < 14
    r   = 13 if (hov or dragging_ref == drag_key) else 10
    pygame.draw.circle(surface, (255, 220, 100) if hov else (220, 130, 0), (handle, cy), r)
    pygame.draw.circle(surface, (255, 160, 0), (handle, cy), r, 2)
    if pressed and hov and dragging_ref is None:
        dragging_ref = drag_key
    if dragging_ref == drag_key:
        new_ratio = max(0.0, min(1.0, (mouse_pos[0] - sx) / sw))
        val = min_v + new_ratio * (max_v - min_v)
    lbl_s  = font.render(label, True, (220, 180, 100))
    val_str = f"{int(val * 100)}%" if drag_key == "vol" else str(int(val))
    val_s  = font.render(val_str, True, (255, 255, 255))
    surface.blit(lbl_s, (sx, sy - 30))
    surface.blit(val_s, (sx + sw - val_s.get_width(), sy - 30))
    return val, dragging_ref


# ═══════════════════════ НАСТРОЙКИ ═══════════════════════════════════════════

def run_settings(screen, bg):
    clock = pygame.time.Clock()
    WIDTH, HEIGHT = screen.get_size()
    font_title = pygame.font.SysFont("impact", 54)
    font       = pygame.font.SysFont("arial", 34, bold=True)
    font_small = pygame.font.SysFont("arial", 24)
    font_hint  = pygame.font.SysFont("arial", 20)
    tmp_vol = menu_settings["volume"]
    cur_res_idx = RESOLUTIONS.index(menu_settings["resolution"]) \
                  if menu_settings["resolution"] in RESOLUTIONS else 2
    dragging = None
    arrow_y   = HEIGHT // 2 + 30
    arrow_sz  = 44
    res_lx    = WIDTH // 2 - 180
    res_rx    = WIDTH // 2 + 180
    left_rect  = pygame.Rect(res_lx - arrow_sz//2, arrow_y - arrow_sz//2, arrow_sz, arrow_sz)
    right_rect = pygame.Rect(res_rx - arrow_sz//2, arrow_y - arrow_sz//2, arrow_sz, arrow_sz)
    apply_btn = Button("✔  ПРИМЕНИТЬ", (WIDTH//2, HEIGHT - 170), font, width=300, height=55)
    back_btn  = Button("← НАЗАД",      (WIDTH//2, HEIGHT - 100), font, width=260, height=55)
    sl_x = WIDTH//2 - 220; sl_w = 440; sl_y = HEIGHT//2 - 100
    panel_w, panel_h = 560, 420

    while True:
        mouse   = pygame.mouse.get_pos()
        pressed = pygame.mouse.get_pressed()[0]
        if not pressed:
            dragging = None
        screen.blit(bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        panel_x = WIDTH//2 - panel_w//2
        panel_y = HEIGHT//2 - panel_h//2 - 20
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((18, 8, 0, 220))
        screen.blit(panel, (panel_x, panel_y))
        pygame.draw.rect(screen, (200, 80, 0), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=10)
        title = font_title.render("НАСТРОЙКИ", True, (255, 140, 0))
        screen.blit(title, title.get_rect(center=(WIDTH//2, panel_y + 44)))
        pygame.draw.line(screen, (180,60,0),(panel_x+30,panel_y+80),(panel_x+panel_w-30,panel_y+80),1)
        tmp_vol, dragging = draw_slider(
            screen, font_small, "Громкость", tmp_vol, 0.0, 1.0,
            sl_x, sl_y, sl_w, mouse, pressed, "vol", dragging)
        pygame.mixer.music.set_volume(tmp_vol)
        res_label = font_small.render("Разрешение экрана", True, (220,180,100))
        screen.blit(res_label, res_label.get_rect(center=(WIDTH//2, arrow_y - 36)))
        cur_res = RESOLUTIONS[cur_res_idx]
        res_surf = font.render(f"{cur_res[0]}  ×  {cur_res[1]}", True, (255,255,200))
        screen.blit(res_surf, res_surf.get_rect(center=(WIDTH//2, arrow_y + arrow_sz//2 - 2)))
        for rect, sym, active in [(left_rect,"◀",cur_res_idx>0),(right_rect,"▶",cur_res_idx<len(RESOLUTIONS)-1)]:
            hov = rect.collidepoint(mouse) and active
            col    = (255,180,0) if hov else ((160,100,0) if active else (60,40,0))
            bg_col = (80,30,0,180) if hov else (30,15,0,150)
            s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA); s.fill(bg_col)
            screen.blit(s, rect.topleft)
            pygame.draw.rect(screen, col, rect, 2, border_radius=6)
            screen.blit(font.render(sym, True, col), font.render(sym,True,col).get_rect(center=rect.center))
        apply_btn.update(mouse); apply_btn.draw(screen)
        back_btn.update(mouse);  back_btn.draw(screen)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if left_rect.collidepoint(mouse)  and cur_res_idx > 0: cur_res_idx -= 1
                if right_rect.collidepoint(mouse) and cur_res_idx < len(RESOLUTIONS)-1: cur_res_idx += 1
                if apply_btn.is_clicked(mouse):
                    menu_settings["volume"]     = tmp_vol
                    menu_settings["resolution"] = RESOLUTIONS[cur_res_idx]
                    pygame.mixer.music.set_volume(tmp_vol)
                    new_res = RESOLUTIONS[cur_res_idx]
                    if new_res != screen.get_size():
                        screen = pygame.display.set_mode(new_res)
                        WIDTH, HEIGHT = screen.get_size()
                        sl_x = WIDTH//2 - 220; sl_y = HEIGHT//2 - 100
                        arrow_y = HEIGHT//2 + 30
                        res_lx  = WIDTH//2 - 180; res_rx = WIDTH//2 + 180
                        left_rect  = pygame.Rect(res_lx-arrow_sz//2, arrow_y-arrow_sz//2, arrow_sz, arrow_sz)
                        right_rect = pygame.Rect(res_rx-arrow_sz//2, arrow_y-arrow_sz//2, arrow_sz, arrow_sz)
                        apply_btn  = Button("✔  ПРИМЕНИТЬ", (WIDTH//2, HEIGHT-170), font, width=300, height=55)
                        back_btn   = Button("← НАЗАД",      (WIDTH//2, HEIGHT-100), font, width=260, height=55)
                        try:
                            bg_raw = pygame.image.load("image/fon.png").convert()
                            bg = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
                        except Exception:
                            bg = pygame.Surface((WIDTH, HEIGHT)); bg.fill((20,20,20))
                if back_btn.is_clicked(mouse): return
        pygame.display.flip()
        clock.tick(60)


# ═══════════════════ ПОДМЕНЮ ВЫБОРА: НОВАЯ ИГРА / ЗАГРУЗИТЬ ══════════════════

def run_start_submenu(screen, bg):
    clock = pygame.time.Clock()
    WIDTH, HEIGHT = screen.get_size()
    font_title = pygame.font.SysFont("impact", 60)
    font_btn   = pygame.font.SysFont("arial",  36, bold=True)
    font_hint  = pygame.font.SysFont("arial",  20)

    cy = HEIGHT // 2
    new_btn  = Button("🗡  НОВАЯ ИГРА",  (WIDTH//2, cy - 60),  font_btn, width=340, height=58)
    load_btn = Button("📂  ЗАГРУЗИТЬ",   (WIDTH//2, cy + 20),  font_btn, width=340, height=58)
    back_btn = Button("← НАЗАД",        (WIDTH//2, cy + 110), font_btn, width=260, height=52)

    save_exists = has_save()
    save_info   = ""
    if save_exists:
        state = load_game()
        if state:
            lvl = state.get("level", "?")
            hp  = state.get("player_hp", "?")
            save_info = f"Сохранение: уровень {lvl}, HP {int(hp)}"

    while True:
        mouse = pygame.mouse.get_pos()
        screen.blit(bg, (0, 0))
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        screen.blit(ov, (0, 0))
        pw, ph = 420, 320
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((15, 5, 0, 230))
        px_p = WIDTH//2 - pw//2
        py_p = HEIGHT//2 - ph//2 - 10
        screen.blit(panel, (px_p, py_p))
        pygame.draw.rect(screen, (200, 80, 0), (px_p, py_p, pw, ph), 2, border_radius=10)
        title = font_title.render("НАЧАТЬ ИГРУ", True, (255, 120, 0))
        screen.blit(title, title.get_rect(center=(WIDTH//2, py_p + 44)))
        pygame.draw.line(screen, (180, 60, 0), (px_p+30, py_p+80), (px_p+pw-30, py_p+80), 1)
        if not save_exists:
            grey_surf = pygame.Surface((340, 58), pygame.SRCALPHA)
            grey_surf.fill((40, 40, 40, 180))
            screen.blit(grey_surf, (WIDTH//2 - 170, cy + 20 - 29))
            pygame.draw.rect(screen, (80, 80, 80), (WIDTH//2-170, cy+20-29, 340, 58), 2, border_radius=4)
            lbl = font_btn.render("📂  НЕТ СОХРАНЕНИЯ", True, (100, 100, 100))
            screen.blit(lbl, lbl.get_rect(center=(WIDTH//2, cy + 20)))
        else:
            load_btn.update(mouse)
            load_btn.draw(screen)
            if save_info:
                info_s = font_hint.render(save_info, True, (160, 200, 160))
                screen.blit(info_s, info_s.get_rect(center=(WIDTH//2, cy + 58)))
        new_btn.update(mouse);  new_btn.draw(screen)
        back_btn.update(mouse); back_btn.draw(screen)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if new_btn.is_clicked(mouse):  return "new"
                if save_exists and load_btn.is_clicked(mouse): return "load"
                if back_btn.is_clicked(mouse): return None
        pygame.display.flip()
        clock.tick(60)


# ═══════════════════════ МЕНЮ ПАУЗЫ ══════════════════════════════════════════

def run_pause_menu(screen, game_state_getter=None):
    """
    Меню паузы внутри игры.
    Возвращает: "resume" | "menu" | "quit"
    """
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    clock   = pygame.time.Clock()
    WIDTH, HEIGHT = screen.get_size()
    font_title = pygame.font.SysFont("impact", 72)
    font_btn   = pygame.font.SysFont("arial",  34, bold=True)
    font_hint  = pygame.font.SysFont("arial",  20)

    bg_snap = screen.copy()

    cy = HEIGHT // 2
    # ── Кнопки паузы (добавлена ⚙ НАСТРОЙКИ) ──
    resume_btn   = Button("▶  ПРОДОЛЖИТЬ",  (WIDTH//2, cy - 100), font_btn, width=340, height=55)
    save_btn     = Button("💾  СОХРАНИТЬ",  (WIDTH//2, cy -  30), font_btn, width=340, height=55)
    settings_btn = Button("⚙  НАСТРОЙКИ",  (WIDTH//2, cy +  40), font_btn, width=340, height=55)
    menu_btn     = Button("⌂  ГЛАВНОЕ МЕНЮ",(WIDTH//2, cy + 110), font_btn, width=340, height=55)
    quit_btn     = Button("✕  ВЫХОД",       (WIDTH//2, cy + 180), font_btn, width=340, height=55)

    save_msg       = ""
    save_msg_timer = 0

    # Панель растянута под пять кнопок
    pw, ph = 420, 440

    while True:
        mouse = pygame.mouse.get_pos()

        screen.blit(bg_snap, (0, 0))
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (0, 0))

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((15, 5, 0, 220))
        px_p = WIDTH//2 - pw//2
        py_p = HEIGHT//2 - ph//2 - 20
        screen.blit(panel, (px_p, py_p))
        pygame.draw.rect(screen, (200, 80, 0), (px_p, py_p, pw, ph), 2, border_radius=10)

        title = font_title.render("ПАУЗА", True, (255, 120, 0))
        screen.blit(title, title.get_rect(center=(WIDTH//2, py_p + 48)))
        pygame.draw.line(screen, (180,60,0),(px_p+30,py_p+86),(px_p+pw-30,py_p+86),1)

        for btn in (resume_btn, save_btn, settings_btn, menu_btn, quit_btn):
            btn.update(mouse); btn.draw(screen)

        if save_msg_timer > 0:
            save_msg_timer -= 1
            alpha = min(255, save_msg_timer * 8)
            msg_s = font_hint.render(save_msg, True, (100, 255, 100))
            msg_s.set_alpha(alpha)
            screen.blit(msg_s, msg_s.get_rect(center=(WIDTH//2, cy + 230)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    return "resume"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if resume_btn.is_clicked(mouse):
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    return "resume"
                if save_btn.is_clicked(mouse):
                    if game_state_getter:
                        state = game_state_getter()
                        ok = save_game(state)
                        save_msg       = "✔ Сохранено!" if ok else "✗ Ошибка сохранения"
                        save_msg_timer = 180
                    else:
                        save_msg       = "✗ Нет данных для сохранения"
                        save_msg_timer = 180
                if settings_btn.is_clicked(mouse):
                    # Открываем настройки прямо поверх паузы
                    run_settings(screen, bg_snap)
                if menu_btn.is_clicked(mouse):
                    return "menu"
                if quit_btn.is_clicked(mouse):
                    pygame.quit(); sys.exit()

        pygame.display.flip()
        clock.tick(60)


# ═══════════════════════ ГЛАВНОЕ МЕНЮ ════════════════════════════════════════

def run_menu(screen):
    """
    Возвращает:
      ("new",  None)   — начать новую игру
      ("load", state)  — загрузить сохранение
      False            — выход
    """
    WIDTH, HEIGHT = screen.get_size()
    clock = pygame.time.Clock()

    try:
        bg_raw = pygame.image.load("image/fon.png").convert()
        bg     = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
    except Exception:
        bg = pygame.Surface((WIDTH, HEIGHT)); bg.fill((20, 20, 20))

    font_btn   = pygame.font.SysFont("arial",  38, bold=True)
    font_title = pygame.font.SysFont("impact", 90, bold=True)
    font_sub   = pygame.font.SysFont("arial",  22)

    buttons = {
        "start":    Button("▶  ИГРАТЬ",    (WIDTH//2, HEIGHT - 280), font_btn),
        "settings": Button("⚙  НАСТРОЙКИ", (WIDTH//2, HEIGHT - 210), font_btn),
        "exit":     Button("✕  ВЫХОД",     (WIDTH//2, HEIGHT - 140), font_btn),
    }

    while True:
        cur_size = screen.get_size()
        if cur_size != (WIDTH, HEIGHT):
            WIDTH, HEIGHT = cur_size
            try:
                bg_raw = pygame.image.load("image/fon.png").convert()
                bg     = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
            except Exception:
                bg = pygame.Surface((WIDTH, HEIGHT)); bg.fill((20, 20, 20))
            buttons = {
                "start":    Button("▶  ИГРАТЬ",    (WIDTH//2, HEIGHT-280), font_btn),
                "settings": Button("⚙  НАСТРОЙКИ", (WIDTH//2, HEIGHT-210), font_btn),
                "exit":     Button("✕  ВЫХОД",     (WIDTH//2, HEIGHT-140), font_btn),
            }

        screen.blit(bg, (0, 0))

        grad = pygame.Surface((WIDTH, HEIGHT//2), pygame.SRCALPHA)
        for i in range(grad.get_height()):
            alpha = int(210 * i / grad.get_height())
            pygame.draw.line(grad, (0, 0, 0, alpha), (0, i), (WIDTH, i))
        screen.blit(grad, (0, HEIGHT//2))

        shadow = font_title.render("NOT DOOM", True, (80, 0, 0))
        title  = font_title.render("NOT DOOM", True, (255, 80, 0))
        screen.blit(shadow, shadow.get_rect(center=(WIDTH//2 + 4, HEIGHT - 416)))
        screen.blit(title,  title.get_rect(center=(WIDTH//2,      HEIGHT - 420)))
        sub = font_sub.render("THE KILL FYRRE", True, (200, 160, 80))
        screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT - 360)))

        mouse = pygame.mouse.get_pos()
        for btn in buttons.values():
            btn.update(mouse); btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if buttons["start"].is_clicked(mouse):
                    result = run_start_submenu(screen, bg)
                    if result == "new":
                        return ("new", None)
                    elif result == "load":
                        state = load_game()
                        if state:
                            return ("load", state)
                if buttons["settings"].is_clicked(mouse):
                    run_settings(screen, bg)
                if buttons["exit"].is_clicked(mouse):
                    pygame.quit(); sys.exit()

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((1360, 800))
    pygame.display.set_caption("NOT DOOM")
    result = run_menu(screen)
    print("Результат меню:", result)
    pygame.quit()