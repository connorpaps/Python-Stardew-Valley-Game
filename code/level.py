import pygame 
from settings import *
from player import Player
from overlay import Overlay
from sprites import Generic, Water, WildFlower, Tree, Interaction, Particle
from os.path import join
from pytmx.util_pygame import load_pygame
from support import *
from transition import Transition
from soil import SoilLayer
from sky import Rain, Sky
from random import randint
from menu import Menu

class Level:
	def __init__(self):
		# get the display surface
		self.display_surface = pygame.display.get_surface()

		# add sprites into the custom groups made below
		self.all_sprites = CameraGroup()
		self.collision_sprites = pygame.sprite.Group()
		self.tree_sprites = pygame.sprite.Group()
		self.interaction_sprites = pygame.sprite.Group()

		# soil setup
		self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites)

		self.setup()
		self.overlay = Overlay(self.player)

		# day/night setup
		self.transition = Transition(self.reset, self.player)

		# sky/rain setup
		self.rain = Rain(self.all_sprites)
		self.raining = randint(0, 10) > 7
		self.soil_layer.raining = self.raining
		self.sky = Sky()

		# trading setup
		self.shop_active = False
		self.menu = Menu(self.player, self.toggle_shop)

		# game sounds
		self.success = pygame.mixer.Sound(join("audio", "success.wav"))
		self.success.set_volume(0.2)

		self.music = pygame.mixer.Sound(join("audio", "music.mp3"))
		self.music.set_volume(0.05)
		self.music.play(loops = -1)
		
	def setup(self):
		# loading pytmx level map and building the map objects based on layer
		tmx_data = load_pygame(join("data", "map.tmx"))
		
		# building house floor
		for layer in ['HouseFloor', 'HouseFurnitureBottom']:
			for x, y, surf in tmx_data.get_layer_by_name(layer).tiles():
				Generic((x * TILE_SIZE,y * TILE_SIZE), surf, self.all_sprites, LAYERS['house bottom'])

		# building house walls
		for layer in ['HouseWalls', 'HouseFurnitureTop']:
			for x, y, surf in tmx_data.get_layer_by_name(layer).tiles():
				Generic((x * TILE_SIZE,y * TILE_SIZE), surf, self.all_sprites)

		# building fence
		for x, y, surf in tmx_data.get_layer_by_name('Fence').tiles():
			Generic((x * TILE_SIZE,y * TILE_SIZE), surf, [self.all_sprites, self.collision_sprites])
		
		# building water
		water_frames = import_folder(join("graphics", "water"))
		for x, y, surf in tmx_data.get_layer_by_name('Water').tiles():
			Water((x * TILE_SIZE,y * TILE_SIZE), water_frames, self.all_sprites)

		# building trees
		for obj in tmx_data.get_layer_by_name('Trees'):
			Tree(
				pos = (obj.x, obj.y), 
				surf = obj.image, 
				groups = [self.all_sprites, self.collision_sprites, self.tree_sprites], name = obj.name,
				player_add = self.player_add)

		# building flowers
		for obj in tmx_data.get_layer_by_name('Decoration'):
			WildFlower((obj.x, obj.y), obj.image, [self.all_sprites, self.collision_sprites])

		# collision tiles for walls/water
		for x, y, surf in tmx_data.get_layer_by_name('Collision').tiles():
			# only place in collision_sprites so it is not drawn but still exists
			Generic((x * TILE_SIZE,y * TILE_SIZE), pygame.Surface((TILE_SIZE, TILE_SIZE)), self.collision_sprites)

		# creating the player layer
		for obj in tmx_data.get_layer_by_name('Player'):
			if obj.name == 'Start':
				self.player = Player(
					pos = (obj.x, obj.y), 
					group = self.all_sprites, 
					collision_sprites = self.collision_sprites,
					tree_sprites = self.tree_sprites,
					interaction = self.interaction_sprites,
					soil_layer = self.soil_layer,
					toggle_shop = self.toggle_shop)

			# check if the player is on the Bed tile to allow sleeping
			if obj.name == 'Bed':
				Interaction(
					pos = (obj.x, obj.y),
					size = (obj.width, obj.height),
					groups = self.interaction_sprites,
					name = obj.name
				)
			
			# check if the player is near the trader to allow trading
			if obj.name == 'Trader':
				Interaction(
					pos = (obj.x, obj.y),
					size = (obj.width, obj.height),
					groups = self.interaction_sprites,
					name = obj.name
				)

		# creating the floor
		Generic(
			pos = (0,0), 
			surf = pygame.image.load(join("graphics", "world") + "\ground.png").convert_alpha(),
			groups = self.all_sprites,
			z = LAYERS['ground']
		)

	def player_add(self, item):
		self.player.item_inventory[item] += 1
		self.success.play()

	def toggle_shop(self):
		self.shop_active = not self.shop_active

	def reset(self):
		# grow plants
		self.soil_layer.update_plants()

		# reset water on the soil patches
		self.soil_layer.remove_water()

		# rest the rain state
		self.raining = randint(0, 10) > 7
		self.soil_layer.raining = self.raining
		if self.raining:
			self.soil_layer.water_all()

		# reset apples on trees
		for tree in self.tree_sprites.sprites():
			# remove all existing apples for every tree then create new
			for apple in tree.apple_sprites.sprites():
				apple.kill()
			tree.create_fruit()

		# reset sky transition when sleeping
		self.sky.start_color = [255, 255, 255]

	def plant_collision(self):
		if self.soil_layer.plant_sprites:
			for plant in self.soil_layer.plant_sprites.sprites():
				if plant.harvestable and plant.rect.colliderect(self.player.hitbox):
					# update player inventory and remove plant
					self.player_add(plant.plant_type)
					plant.kill()

					# create a particle animation for removing the plant
					Particle(plant.rect.topleft, plant.image, self.all_sprites, z = LAYERS['main'])

					# remove the 'P' from the soil dict grid
					self.soil_layer.grid[plant.rect.centery // TILE_SIZE][plant.rect.centerx // TILE_SIZE].remove('P')

	def run(self, dt):
		
		# drawing objects
		self.display_surface.fill('black')
		self.all_sprites.custom_draw(self.player)

		# update logic
		# if the player is shopping no need to update sprites/collision
		if self.shop_active:
			self.menu.update()
		else:			
			self.all_sprites.update(dt)
			self.plant_collision()

		# weather/rain updates
		self.overlay.display()
		if self.raining and not self.shop_active:
			self.rain.update()

		# daytime transition
		self.sky.display(dt)

		# day/night system transition when sleeping
		if self.player.sleep:
			self.transition.play()

# creating a special group to put all the sprites in
class CameraGroup(pygame.sprite.Group):
	def __init__(self):
		super().__init__()

		# get display surface to allow camera group to draw on the screen
		self.display_surface = pygame.display.get_surface()
		# the offset adjusts the position of the world based on player movement
		self.offset = pygame.math.Vector2()

	def custom_draw(self, player):
		# offset is how much every sprite will be shifted relative to player
		self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2
		self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2

		for layer in LAYERS.values():
			# sort the sprites based on Y position to always draw sprites behind the player before the player sprite to simulate 3d overlapping sprites
			for sprite in sorted(self.sprites(), key = lambda sprite: sprite.rect.centery):
				# only draw the sprites in the correct layer order
				if sprite.z == layer:
					offset_rect = sprite.rect.copy()
					offset_rect.center -= self.offset
					self.display_surface.blit(sprite.image, offset_rect)
					# # anaytics
					# if sprite == player:
					# 	pygame.draw.rect(self.display_surface,'red',offset_rect,5)
					# 	hitbox_rect = player.hitbox.copy()
					# 	hitbox_rect.center = offset_rect.center
					# 	pygame.draw.rect(self.display_surface,'green',hitbox_rect,5)
					# 	target_pos = offset_rect.center + PLAYER_TOOL_OFFSET[player.status.split('_')[0]]
					# 	pygame.draw.circle(self.display_surface,'blue',target_pos,5)
