import pygame
from settings import *
from support import import_folder
from os.path import join
from sprites import Generic
from random import randint, choice

class Sky:
    def __init__(self):
        # screen setup
        self.display_surface = pygame.display.get_surface()
        self.full_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # start and end color values to transition between
        self.start_color = [255, 255, 255]
        self.end_color = (38, 101, 189)

    # applies a surface over the entire game window
    def display(self, dt):
        # reduce the start color values until they reach the end color
        for index, value in enumerate(self.end_color):
            if self.start_color[index] > value:
                self.start_color[index] -= 2 * dt

        # display the color on the screen
        self.full_surf.fill(self.start_color)
        self.display_surface.blit(self.full_surf, (0,0), special_flags = pygame.BLEND_RGBA_MULT)

class Drop(Generic):
    def __init__(self, surf, pos, moving, groups, z):
        super().__init__(pos, surf, groups, z)

        # life and timer setup
        self.lifetime = randint(400, 500)
        self.start_time = pygame.time.get_ticks()

        # movement setup
        self.moving = moving
        if self.moving:
            self.pos = pygame.math.Vector2(self.rect.topleft)
            self.direction = pygame.math.Vector2(-2, 4)
            self.speed = randint(200, 250)

    def update(self, dt):
        # moving the rain drop
        if self.moving:
            self.pos += self.direction * self.speed * dt
            self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        
        # remove the rain drop sprite after its lifetime is over
        if pygame.time.get_ticks() - self.start_time >= self.lifetime:
            self.kill()

class Rain:
    def __init__(self, all_sprites):
        self.all_sprites = all_sprites
        self.rain_drops = import_folder(join("graphics", "rain", "drops"))
        self.rain_floor = import_folder(join("graphics", "rain", "floor"))
        self.floor_w, self.floor_h = pygame.image.load(join("graphics", "world","ground.png")).get_size()

    def create_floor(self):
        Drop(
            surf = choice(self.rain_floor),
            pos = (randint(0, self.floor_w), randint(0, self.floor_h)),
            moving = False, 
            groups = self.all_sprites, 
            z = LAYERS['rain floor'])

    def create_drops(self):
        Drop(surf = choice(self.rain_drops),
            pos = (randint(0, self.floor_w), randint(0, self.floor_h)),
            moving = True, 
            groups = self.all_sprites, 
            z = LAYERS['rain drops'])

    def update(self):
        self.create_floor()
        self.create_drops()