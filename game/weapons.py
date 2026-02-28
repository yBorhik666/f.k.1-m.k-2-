import pygame

weapons = [
    {
        "name": "Pistol",
        "damage": 1,
        "fire_rate": 20,
        "speed": 12,
        "frames": [
            "image/pistol_0.png",
            "image/pistol_1.png",
            "image/pistol_2.png",
            "image/pistol_3.png"
        ]
    },
    {
        "name": "Tezer",
        "damage": 15,
        "fire_rate": 40,
        "speed": 100,
        "frames": [
            "image/tezer_0.png",
            "image/tezer_1.png",
            "image/tezer_2.png"
        ]
    },
    {
        "name": "Rifle",
        "damage": 1.95,
        "fire_rate": 5,
        "speed": 18,
        "frames": [
            "image/mini_gun_0.png",
            "image/mini_gun_1.png",
            "image/mini_gun_2.png"
        ]
    },
    {
        "name": "Shutgun",
        "damage": 1.95,
        "fire_rate": 5,
        "speed": 18,
        "frames": [
            "image/shotgun_0.png",
            "image/shotgun_1.png",
            "image/shotgun_2.png"
        ]
    }
]


def load_weapon_textures():
    for weapon in weapons:
        weapon["frames"] = [
            pygame.image.load(frame).convert_alpha()
            for frame in weapon["frames"]
        ]