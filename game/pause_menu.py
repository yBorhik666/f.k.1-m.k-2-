import pygame
import sys
import json
import os
import math

SAVE_FILE = "savegame.json"


def save_game(state: dict):
    """Сохраняет состояние игры в JSON-файл."""
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[SAVE] Ошибка сохранения: {e}")
        return False


def load_game() -> dict | None:
    """Загружает состояние игры из JSON-файла. Возвращает None если файла нет."""
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[LOAD] Ошибка загрузки: {e}")
        return None


def run_pause_menu(screen, settings: dict) -> str:
    """
    Показывает меню паузы поверх текущего кадра.

    settings — словарь с текущими настройками:
        {
            "volume":     0.0..1.0,
            "mouse_sens": float,
        }

    Возвращает одну из строк:
        "resume"    — продолжить игру
        "load"      — загрузить сохранение (данные в settings["loaded_state"])
        "main_menu" — выйти в главное меню
        "quit"      — выйти из игры
    """
    clock = pygame.time.Clock()
    WIDTH, HEIGHT = screen.get_size()

    # Снимок экрана для фона (блюр-эффект через масштабирование)
    bg_snapshot = screen.copy()
    small = pygame.transform.smoothscale(bg_snapshot, (WIDTH // 8, HEIGHT // 8))
    blurred_bg = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))

    # --- Цвета ---
    C_BG        = (10, 5, 5, 210)
    C_PANEL     = (20, 10, 10)
    C_BORDER    = (160, 20, 20)
    C_TITLE     = (220, 30, 30)
    C_BTN_IDLE  = (40, 18, 18)
    C_BTN_HOV   = (90, 25, 25)
    C_BTN_TEXT  = (230, 210, 210)
    C_BTN_HOV_T = (255, 255, 255)
    C_ACCENT    = (200, 50, 50)
    C_GREY      = (120, 120, 120)

    font_title  = pygame.font.SysFont("impact", 54)
    font_btn    = pygame.font.SysFont("impact", 32)
    font_small  = pygame.font.SysFont("impact", 22)
    font_hint   = pygame.font.SysFont("impact", 18)

    PANEL_W = 420
    BTN_W   = 360
    BTN_H   = 52
    BTN_GAP = 14

    # Состояние подменю: "main" | "settings"
    submenu = "main"

    # Рабочая копия настроек (изменяем только при выходе из settings)
    vol      = settings.get("volume", 0.8)
    sens     = settings.get("mouse_sens", 0.003)
    tmp_vol  = vol
    tmp_sens = sens

    # Перетаскиваемый слайдер
    dragging = None   # "vol" | "sens" | None

    anim_timer = 0

    # Кнопки главного меню
    MAIN_BUTTONS = [
        ("resume",    "▶  Продолжить"),
        ("settings",  "⚙  Настройки"),
        ("load",      "💾  Загрузить сохранение"),
        ("main_menu", "🏠  Выйти в меню"),
        ("quit",      "✕  Выйти из игры"),
    ]

    def draw_button(surf, rect, label, hovered, danger=False):
        bg_col  = C_BTN_HOV if hovered else C_BTN_IDLE
        txt_col = C_BTN_HOV_T if hovered else C_BTN_TEXT
        if danger and hovered:
            bg_col  = (120, 20, 20)
            txt_col = (255, 100, 100)
        pygame.draw.rect(surf, bg_col, rect, border_radius=8)
        border_col = C_ACCENT if hovered else (60, 30, 30)
        pygame.draw.rect(surf, border_col, rect, 2, border_radius=8)
        lbl = font_btn.render(label, True, txt_col)
        surf.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                        rect.y + rect.h // 2 - lbl.get_height() // 2))

    def draw_slider(surf, label, val, min_v, max_v, sx, sy, sw, key, mouse_pos, pressed):
        nonlocal dragging, tmp_vol, tmp_sens
        ratio  = (val - min_v) / (max_v - min_v)
        handle = int(sx + ratio * sw)
        sh     = 8
        cy     = sy + sh // 2

        # Трек
        pygame.draw.rect(surf, (50, 30, 30), (sx, cy - sh // 2, sw, sh), border_radius=4)
        pygame.draw.rect(surf, C_ACCENT,     (sx, cy - sh // 2, int(ratio * sw), sh), border_radius=4)

        # Ручка
        hov_handle = math.hypot(mouse_pos[0] - handle, mouse_pos[1] - cy) < 14
        r = 13 if hov_handle or dragging == key else 10
        pygame.draw.circle(surf, C_BTN_HOV_T if hov_handle else C_ACCENT, (handle, cy), r)
        pygame.draw.circle(surf, C_BORDER, (handle, cy), r, 2)

        # Перетаскивание
        if pressed and hov_handle and dragging is None:
            dragging = key
        if dragging == key:
            new_ratio = max(0.0, min(1.0, (mouse_pos[0] - sx) / sw))
            new_val   = min_v + new_ratio * (max_v - min_v)
            if key == "vol":
                tmp_vol  = round(new_val, 2)
            else:
                tmp_sens = round(new_val, 4)

        # Метка + значение
        val_disp = f"{int(val * 100)}%" if key == "vol" else f"{val:.4f}"
        lbl_surf = font_small.render(label, True, (200, 180, 180))
        val_surf = font_small.render(val_disp, True, C_BTN_HOV_T)
        surf.blit(lbl_surf, (sx, sy - 26))
        surf.blit(val_surf, (sx + sw - val_surf.get_width(), sy - 26))

    running = True
    result  = "resume"

    while running:
        anim_timer += 1
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        # --- Сброс dragging при отпускании мыши ---
        if not mouse_pressed:
            dragging = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if submenu == "settings":
                        submenu = "main"
                    else:
                        result  = "resume"
                        running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # --- Главное меню ---
                if submenu == "main":
                    panel_x = WIDTH // 2 - PANEL_W // 2
                    btn_x   = WIDTH // 2 - BTN_W  // 2
                    start_y = HEIGHT // 2 - (len(MAIN_BUTTONS) * (BTN_H + BTN_GAP)) // 2 + 30

                    for i, (action, label) in enumerate(MAIN_BUTTONS):
                        by = start_y + i * (BTN_H + BTN_GAP)
                        rect = pygame.Rect(btn_x, by, BTN_W, BTN_H)
                        if rect.collidepoint(mouse_pos):
                            if action == "settings":
                                submenu  = "settings"
                                tmp_vol  = vol
                                tmp_sens = sens
                            elif action == "load":
                                loaded = load_game()
                                if loaded:
                                    settings["loaded_state"] = loaded
                                    result = "load"
                                    running = False
                                # иначе — кнопка недоступна, ничего не делаем
                            elif action == "resume":
                                result  = "resume"
                                running = False
                            elif action == "main_menu":
                                result  = "main_menu"
                                running = False
                            elif action == "quit":
                                pygame.quit()
                                sys.exit()

                # --- Настройки ---
                elif submenu == "settings":
                    panel_x = WIDTH // 2 - PANEL_W // 2
                    # Кнопка "Применить"
                    apply_rect = pygame.Rect(WIDTH // 2 - BTN_W // 2, HEIGHT // 2 + 110, BTN_W, BTN_H)
                    back_rect  = pygame.Rect(WIDTH // 2 - BTN_W // 2, HEIGHT // 2 + 174, BTN_W, BTN_H)
                    if apply_rect.collidepoint(mouse_pos):
                        vol  = tmp_vol
                        sens = tmp_sens
                        settings["volume"]     = vol
                        settings["mouse_sens"] = sens
                        pygame.mixer.music.set_volume(vol)
                        submenu = "main"
                    if back_rect.collidepoint(mouse_pos):
                        submenu = "main"   # отмена

        # ===================== ОТРИСОВКА =====================

        # Размытый фон
        screen.blit(blurred_bg, (0, 0))

        # Тёмный оверлей
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        # Пульсирующий бордер экрана
        pulse_a = int(30 + 20 * math.sin(anim_timer * 0.05))
        for i in range(3):
            pygame.draw.rect(screen, (*C_BORDER, pulse_a),
                             (i, i, WIDTH - i * 2, HEIGHT - i * 2), 1)

        # ---------- ГЛАВНОЕ МЕНЮ ----------
        if submenu == "main":
            panel_x = WIDTH // 2 - PANEL_W // 2
            btn_x   = WIDTH // 2 - BTN_W  // 2
            start_y = HEIGHT // 2 - (len(MAIN_BUTTONS) * (BTN_H + BTN_GAP)) // 2 + 30

            # Панель
            total_h = len(MAIN_BUTTONS) * (BTN_H + BTN_GAP) + 100
            panel_rect = pygame.Rect(panel_x, HEIGHT // 2 - total_h // 2, PANEL_W, total_h)
            panel_surf = pygame.Surface((PANEL_W, total_h), pygame.SRCALPHA)
            panel_surf.fill((*C_PANEL, 230))
            screen.blit(panel_surf, panel_rect.topleft)
            pygame.draw.rect(screen, C_BORDER, panel_rect, 2, border_radius=12)

            # Заголовок
            title = font_title.render("ПАУЗА", True, C_TITLE)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2,
                                panel_rect.y + 18))
            pygame.draw.line(screen, C_BORDER,
                             (panel_x + 20, panel_rect.y + 76),
                             (panel_x + PANEL_W - 20, panel_rect.y + 76), 1)

            save_exists = os.path.exists(SAVE_FILE)

            for i, (action, label) in enumerate(MAIN_BUTTONS):
                by   = start_y + i * (BTN_H + BTN_GAP)
                rect = pygame.Rect(btn_x, by, BTN_W, BTN_H)
                hov  = rect.collidepoint(mouse_pos)
                danger = action in ("quit", "main_menu")

                # Серая/недоступная кнопка загрузки если нет сейва
                if action == "load" and not save_exists:
                    pygame.draw.rect(screen, (28, 18, 18), rect, border_radius=8)
                    pygame.draw.rect(screen, (50, 35, 35), rect, 2, border_radius=8)
                    lbl = font_btn.render(label + "  [нет]", True, C_GREY)
                    screen.blit(lbl, (rect.x + rect.w // 2 - lbl.get_width() // 2,
                                     rect.y + rect.h // 2 - lbl.get_height() // 2))
                else:
                    draw_button(screen, rect, label, hov, danger=danger)

            # Подсказка
            hint = font_hint.render("ESC — продолжить", True, (90, 90, 90))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, panel_rect.bottom - 22))

        # ---------- НАСТРОЙКИ ----------
        elif submenu == "settings":
            panel_x = WIDTH // 2 - PANEL_W // 2
            panel_h = 400
            panel_rect = pygame.Rect(panel_x, HEIGHT // 2 - panel_h // 2, PANEL_W, panel_h)
            panel_surf = pygame.Surface((PANEL_W, panel_h), pygame.SRCALPHA)
            panel_surf.fill((*C_PANEL, 230))
            screen.blit(panel_surf, panel_rect.topleft)
            pygame.draw.rect(screen, C_BORDER, panel_rect, 2, border_radius=12)

            title = font_title.render("НАСТРОЙКИ", True, C_TITLE)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2,
                                panel_rect.y + 18))
            pygame.draw.line(screen, C_BORDER,
                             (panel_x + 20, panel_rect.y + 76),
                             (panel_x + PANEL_W - 20, panel_rect.y + 76), 1)

            sl_x  = panel_x + 30
            sl_w  = PANEL_W - 60

            # Слайдер громкости
            draw_slider(screen, "Громкость", tmp_vol, 0.0, 1.0,
                        sl_x, HEIGHT // 2 - 80, sl_w, "vol",
                        mouse_pos, mouse_pressed)

            # Слайдер чувствительности мыши
            draw_slider(screen, "Чувствительность мыши", tmp_sens, 0.0005, 0.008,
                        sl_x, HEIGHT // 2, sl_w, "sens",
                        mouse_pos, mouse_pressed)

            # Кнопки Применить / Назад
            apply_rect = pygame.Rect(WIDTH // 2 - BTN_W // 2, HEIGHT // 2 + 110, BTN_W, BTN_H)
            back_rect  = pygame.Rect(WIDTH // 2 - BTN_W // 2, HEIGHT // 2 + 174, BTN_W, BTN_H)
            draw_button(screen, apply_rect, "✔  Применить", apply_rect.collidepoint(mouse_pos))
            draw_button(screen, back_rect,  "←  Назад",     back_rect.collidepoint(mouse_pos))

            hint = font_hint.render("ESC — назад", True, (90, 90, 90))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, panel_rect.bottom - 22))

        pygame.display.flip()
        clock.tick(60)

    return result