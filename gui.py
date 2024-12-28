import pygame

class Button:
    def __init__(self, x, y, width, height, text, onClick, fontSize=1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.onClick = onClick
        self.fontSize = fontSize
    def draw(self, surf, font:pygame.font.Font):
        pygame.draw.rect(surf, (27, 66, 66), (self.x, self.y, self.width, self.height), border_radius=3)
        text = font.render(self.text, True, (0, 0, 0))
        size = text.get_size()
        text = pygame.transform.scale(text, (size[0]/self.fontSize, size[1]/self.fontSize))
        size = text.get_size()
        pos = (self.x+self.width/2-size[0]/2, self.y+self.height/2-size[1]/2)
        surf.blit(text, pos)
    def tick(self, mousePress, mousePos):
        if mousePress and mousePos[0] >= self.x and mousePos[0] <= self.x+self.width and mousePos[1] >= self.y and mousePos[1] <= self.y+self.height:
            self.onClick()