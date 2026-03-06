import pygame
import sys

def run_menu(screen):

    font = pygame.font.SysFont("arial", 50)
    clock = pygame.time.Clock()

    WIDTH, HEIGHT = screen.get_size()

    while True:

        screen.fill((20,20,20))

        title = font.render("NOT DOOM", True, (255,255,255))
        start = font.render("START", True, (255,255,255))
        exit_btn = font.render("EXIT", True, (255,255,255))

        title_rect = title.get_rect(center=(WIDTH//2,150))
        start_rect = start.get_rect(center=(WIDTH//2,300))
        exit_rect = exit_btn.get_rect(center=(WIDTH//2,400))

        screen.blit(title,title_rect)
        screen.blit(start,start_rect)
        screen.blit(exit_btn,exit_rect)

        mouse = pygame.mouse.get_pos()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:

                if start_rect.collidepoint(mouse):
                    return True   # запускаем игру

                if exit_rect.collidepoint(mouse):
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()
        clock.tick(60)