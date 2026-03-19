import pygame

weapons = [
    {
        "name": "Pistol",
        "damage": 2.09,
        "fire_rate": 20,
        "speed": 12,
        "minigun": False,
        "ammo_type": "9mm",
        "frames": [
            "image/pistol_0.png",
            "image/pistol_1.png",
            "image/pistol_2.png",
            "image/pistol_3.png"
        ],
        "sound": "sound/pistol.wav",
        "auto": False
    },
    {
        "name": "Shotgun",
        "damage": 3.95,
        "fire_rate": 5,
        "speed": 18,
        "minigun": False,
        "ammo_type": "shells",
        "frames": [
            "image/shotgun_0.png",
            "image/shotgun_1.png",
            "image/shotgun_2.png",
            "image/shotgun_3.png"
        ],
        "sound": "sound/shotgun.wav",
        "auto": False
    },
    {
        "name": "Rifle",
        "damage": 1.95,
        "fire_rate": 6,
        "minigun": True,
        "speed": 18,
        "ammo_type": "762",
        "frames": [
            "image/m240.png",
            "image/m240_1.png",
            "image/m240_2.png",
            "image/m240_3.png",
            "image/m240_4.png",
            "image/m240_5.png",
            "image/m240_6.png"
        ],
        "sound": "sound/m.wav",
        "auto": True
    },
    {
        "name": "Tezer",
        "damage": 35,
        "fire_rate": 40,
        "speed": 100,
        "minigun": False,
        "ammo_type": "cells",
        "frames": [
            "image/tezer_0.png",
            "image/tezer_1.png"
        ],
        "sound": "sound/tezer.wav",
        "auto": False
    }
]

weapon_sounds = {}

def load_weapon_textures():
    for weapon in weapons:
        weapon["frames"] = [
            pygame.image.load(frame).convert_alpha()
            for frame in weapon["frames"]
        ]
        weapon_sounds[weapon["name"]] = pygame.mixer.Sound(weapon["sound"])