from os import walk
import pygame

# obtains a list of only the image files within the given directory
def import_folder(path):
    surface_list = []
    for _, _, img_files in walk(path):
        for image in img_files:
            full_path = path + '\\' + image
            image_surf = pygame.image.load(full_path).convert_alpha()
            surface_list.append(image_surf)
    return surface_list

# obtains a dictionary of key value pairs consiting of the name of the file with its image
def import_folder_dict(path):
    surface_dict = {}
    for _, _, img_files in walk(path):
        for image in img_files:
            full_path = path + '\\' + image
            image_surf = pygame.image.load(full_path).convert_alpha()
            surface_dict[image.split('.')[0]] = image_surf
    return surface_dict
