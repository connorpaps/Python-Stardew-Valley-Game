import pygame
from settings import *
from os.path import join
from pytmx.util_pygame import load_pygame
from support import *
from random import choice

class SoilTile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)
        self.z = LAYERS['soil']

class WaterTile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)
        self.z = LAYERS['soil water']

class Plant(pygame.sprite.Sprite):
    def __init__(self, plant_type, groups, soil, check_watered):
        super().__init__(groups)

        # plant setup
        self.plant_type = plant_type
        if self.plant_type == 'corn':
            self.frames = import_folder(join("graphics", "fruit", "corn"))
        if self.plant_type == 'tomato':
            self.frames = import_folder(join("graphics", "fruit", "tomato"))
    
        self.soil = soil
        self.check_watered = check_watered

        # plant growth settings
        self.age = 0
        self.max_age = len(self.frames) - 1
        self.grow_speed = GROW_SPEED[plant_type]
        self.harvestable = False

        # plant sprite setup
        self.image = self.frames[self.age]
        self.y_offset = -16 if plant_type == 'corn' else -8
        self.rect = self.image.get_rect(midbottom = soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset))
        self.z = LAYERS['ground plant']

    def grow(self):
        if self.check_watered(self.rect.center):
            self.age += self.grow_speed

            # change plant layer when it grows to allow player collision
            if int(self.age) > 0:
                self.z = LAYERS['main']
                self.hitbox = self.rect.copy().inflate(-26, -self.rect.height * 0.4)

            if self.age >= self.max_age:
                self.age = self.max_age
                self.harvestable = True

            self.image = self.frames[int(self.age)]
            self.rect = self.image.get_rect(midbottom = self.soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset))

class SoilLayer:
    def __init__(self, all_sprites, collision_sprites):
        # sprite group setup
        self.all_sprites = all_sprites
        self.collision_sprites = collision_sprites
        self.soil_sprites = pygame.sprite.Group()
        self.water_sprites = pygame.sprite.Group()
        self.plant_sprites = pygame.sprite.Group()

        # soil graphics setup
        self.soil_surfs = import_folder_dict(join("graphics", "soil"))
        self.water_surfs = import_folder(join("graphics", "soil_water"))

        # calling methods
        self.create_soil_grid()
        self.create_hit_rects()

        # game sounds
        self.hoe_sound = pygame.mixer.Sound(join("audio", "hoe.wav"))
        self.hoe_sound.set_volume(0.1)

        self.plant_sound = pygame.mixer.Sound(join("audio", "plant.wav"))
        self.plant_sound.set_volume(0.1)

    def create_soil_grid(self):
        ground = pygame.image.load(join("graphics", "world", "ground.png"))
        h_tiles, v_tiles = ground.get_width() // TILE_SIZE, ground.get_height() // TILE_SIZE

        # a list of lists that each contain information about every tile on the map
        self.grid = [[[] for col in range(h_tiles)] for row in range(v_tiles)]
        
        for x, y, _ in load_pygame(join("data", "map.tmx")).get_layer_by_name('Farmable').tiles():
            self.grid[y][x].append('F')
    
    # creating a rect for every tile on the map that the player can hit
    def create_hit_rects(self):
        self.hit_rects = []
        for index_row, row in enumerate(self.grid):
            for index_col, cell in enumerate(row):
                # if the tile is farmable, create a rect for that tiles position
                if 'F' in cell:
                    x = index_col * TILE_SIZE
                    y = index_row * TILE_SIZE
                    rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                    self.hit_rects.append(rect)

    def get_hit(self, point):
        for rect in self.hit_rects:
            if rect.collidepoint(point):
                self.hoe_sound.play()

                x = rect.x // TILE_SIZE
                y = rect.y // TILE_SIZE
                # if the tile the player hoe's is farmable, add an X to represent a soil patch added
                if 'F' in self.grid[y][x]:
                    self.grid[y][x].append('X')
                    self.create_soil_tiles()
                    if self.raining:
                        self.water_all()

    # check if the target position for watering is hitting a soil sprite tile
    def water(self, target_pos):
        for soil_sprite in self.soil_sprites.sprites():
            if soil_sprite.rect.collidepoint(target_pos):
                # if true, add 'W' to soil dict in the correct spot to indicate watered
                x = soil_sprite.rect.x // TILE_SIZE
                y = soil_sprite.rect.y // TILE_SIZE
                self.grid[y][x].append('W')

                # create a water sprite
                pos = soil_sprite.rect.topleft
                surf = choice(self.water_surfs)
                WaterTile(pos, surf, [self.all_sprites, self.water_sprites])

    def water_all(self):
        for index_row, row in enumerate(self.grid):
            for index_col, cell in enumerate(row):
                # checking if a cell/tile is soiled and not yet watered
                if 'X' in cell and 'W' not in cell:
                    cell.append('W')
                    # switching the grid cell positions to actual pixel positions for the game
                    x = index_col * TILE_SIZE
                    y = index_row * TILE_SIZE
                    WaterTile((x, y), choice(self.water_surfs), [self.all_sprites, self.water_sprites])

    def remove_water(self):
        # remove all water sprite tiles from the map
        for sprite in self.water_sprites.sprites():
            sprite.kill()
        # remove the 'W' indicators from the soil dictionary grid
        for row in self.grid:
            for cell in row:
                if 'W' in cell:
                    cell.remove('W')

    def check_watered(self, pos):
        x = pos[0] // TILE_SIZE
        y = pos[1] // TILE_SIZE
        cell = self.grid[y][x]
        is_watered = 'W' in cell
        return is_watered

    def plant_seed(self, target_pos, seed):
        # checking if the target is hitting a soil sprite tile to allow planting
        for soil_sprite in self.soil_sprites.sprites():
            if soil_sprite.rect.collidepoint(target_pos):
                self.plant_sound.play()

                # convert pixel position to grid position to access soil dictionary
                x = soil_sprite.rect.x // TILE_SIZE
                y = soil_sprite.rect.y // TILE_SIZE
                
                if 'P' not in self.grid[y][x]:
                    # add P for plant added to the soil tile and create a Plant
                    self.grid[y][x].append('P')
                    Plant(seed, [self.all_sprites, self.plant_sprites, self.collision_sprites], soil_sprite, self.check_watered)

    def update_plants(self):
        for plant in self.plant_sprites.sprites():
            plant.grow()

    def create_soil_tiles(self):
        self.soil_sprites.empty()
        for index_row, row in enumerate(self.grid):
            for index_col, cell in enumerate(row):
                if 'X' in cell:

                    # determine what is around the current soil tile cell being placed
                    # get cells above, to the left, to the right, and below
                    t = 'X' in self.grid[index_row - 1][index_col]
                    b = 'X' in self.grid[index_row + 1][index_col]
                    r = 'X' in row[index_col + 1]
                    l = 'X' in row[index_col - 1]

                    # get the appropriate tile type to apply to the current cell
                    tile_type = 'o'

                    #horizontal tiles
                    # placing center tile
                    if all((t, r, b, l)): tile_type = 'x'
                    # tile only to the left
                    if l and not any((t, r, b)): tile_type = 'r'
                    # tile only to the right
                    if r and not any((t, l, b)): tile_type = 'l'
                    # tile left and right of placing tile
                    if r and l and not any((t, b)): tile_type = 'lr'

                    # vertical tiles
                    # placing bottom tile
                    if t and not any((r, l, b)): tile_type = 'b'
                    # placing top tile
                    if b and not any((r, l, t)): tile_type = 't'
                    # placing tile between top and bottom tiles only
                    if b and t and not any((r, l)): tile_type = 'tb'

                    # checking for corners
                    # top right tile if only left/bottom tiles exist
                    if l and b and not any((t, r)): tile_type = 'tr'
                    # top left tile if only right/bottom tiles exist
                    if r and b and not any((t, l)): tile_type = 'tl'
                    # bottom right tile if onlyleft/top tiles exist 
                    if l and t and not any((b, r)): tile_type = 'br'
                    # bottom left tile if only bottom/left tiles exist
                    if r and t and not any((b, l)): tile_type = 'bl'

                    # adjusting/checking T shaped tile placement
                    if all((t, b, r)) and not l: tile_type = 'tbr'
                    if all((t, b, l)) and not r: tile_type = 'tbl'
                    if all((l, r, t)) and not b: tile_type = 'lrb'
                    if all((l, r, b)) and not t: tile_type = 'lrt'                   

                    SoilTile(
                        pos = (index_col * TILE_SIZE, index_row * TILE_SIZE), 
                        surf = self.soil_surfs[tile_type], 
                        groups = [self.all_sprites, self.soil_sprites])
