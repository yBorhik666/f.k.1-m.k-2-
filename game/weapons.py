import pygame

weapons = [
    {
        "name": "Pistol",
        "damage": 1,
        "fire_rate": 20,
        "speed": 12,
        "texture": "image/pistol.png"
    },
    {
        "name": "Shotgun",
        "damage": 2,
        "fire_rate": 40,
        "speed": 10,
        "texture": "image/pistol.png"
    },
    {
        "name": "Rifle",
        "damage": 1,
        "fire_rate": 5,
        "speed": 18,
        "texture": "image/pistol.png"
    }
]


def load_weapon_textures():
    for weapon in weapons:
        weapon["image"] = pygame.image.load(weapon["texture"]).convert_alpha()
