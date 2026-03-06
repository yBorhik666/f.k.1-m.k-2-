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

    def update(self, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        if hovered:
            self.hover_progress = min(1.0, self.hover_progress + self.ANIM_SPEED)
        else:
            self.hover_progress = max(0.0, self.hover_progress - self.ANIM_SPEED)

    def draw(self, surface):
        t = self.hover_progress

        bg     = tuple(int(BTN_NORMAL[i] + (BTN_HOVER[i]   - BTN_NORMAL[i])   * t) for i in range(3))
        border = tuple(int(BTN_BORDER[i] + (BTN_BORDER_H[i] - BTN_BORDER[i])  * t) for i in range(3))
        text_color = tuple(int(TEXT_NORMAL[i] + (TEXT_HOVER[i] - TEXT_NORMAL[i]) * t) for i in range(3))

        expand    = int(8 * t)
        draw_rect = self.rect.inflate(expand, expand // 2)

        # Полупрозрачный фон
        btn_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
        btn_surf.fill((*bg, 200))
        surface.blit(btn_surf, draw_rect.topleft)

        # Рамка
        pygame.draw.rect(surface, border, draw_rect, width=2, border_radius=4)

        # Декоративные уголки
        sz = 10
        x, y, w, h = draw_rect
        for cx, cy, dx, dy in [(x,y,1,1),(x+w,y,-1,1),(x,y+h,1,-1),(x+w,y+h,-1,-1)]:
            pygame.draw.line(surface, border, (cx, cy), (cx + dx*sz, cy), 2)
            pygame.draw.line(surface, border, (cx, cy), (cx, cy + dy*sz), 2)

        # Текст
        label      = self.font.render(self.text, True, text_color)
        label_rect = label.get_rect(center=draw_rect.center)
        surface.blit(label, label_rect)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


def run_settings(screen, bg):
    font  = pygame.font.SysFont("arial", 38, bold=True)
    small = pygame.font.SysFont("arial", 26)
    clock = pygame.time.Clock()
    WIDTH, HEIGHT = screen.get_size()

    back_btn = Button("← НАЗАД", (WIDTH // 2, HEIGHT - 110), font, width=260, height=55)

    while True:
        screen.blit(bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        title = font.render("НАСТРОЙКИ", True, (255, 160, 0))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))

        hint = small.render("(здесь будут твои настройки)", True, (160, 160, 160))
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        mouse = pygame.mouse.get_pos()
        back_btn.update(mouse)
        back_btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_btn.is_clicked(mouse):
                    return

        pygame.display.flip()
        clock.tick(60)


def run_menu(screen):
    WIDTH, HEIGHT = screen.get_size()
    clock = pygame.time.Clock()

    # Загрузка фона — файл должен лежать в image/fon.png
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
        screen.blit(bg, (0, 0))

        # Тёмный градиент снизу — чтобы кнопки читались
        grad = pygame.Surface((WIDTH, HEIGHT // 2), pygame.SRCALPHA)
        for i in range(grad.get_height()):
            alpha = int(210 * i / grad.get_height())
            pygame.draw.line(grad, (0, 0, 0, alpha), (0, i), (WIDTH, i))
        screen.blit(grad, (0, HEIGHT // 2))

        # Заголовок с тенью
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
    screen = pygame.display.set_mode((1360, 800))
    pygame.display.set_caption("NOT DOOM")
    run_menu(screen)
    pygame.quit()