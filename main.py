import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame, sys, copy, math, gui, json

nodeTypes = {"AND":{'connections':[(-1,0.5,True), (-1,-0.5,True), (1,0,False)]},
             "OR":{'connections':[(-1,0.5,True), (-1,-0.5,True), (1,0,False)]},
             "NOT":{'connections':[(-1,0,True), (1,0,False)]},
             "XOR":{'connections':[(-1,0.5,True), (-1,-0.5,True), (1,0,False)]},
             "ON":{'connections':[(1,0,False)]}, "OFF":{'connections':[(1,0,False)]},
             "MSD":{'connections':[(1,0,False)]},
             "TGL":{'connections':[(1,0,False)]},
             "LMP":{'connections':[(-1,0,True)]},
             "CEL":{'connections':[(-1,0,True), (1,0,False)]}
}

class Camera:
    def __init__(self, x:int, y:int, zoom:float):
        self.x = x
        self.y = y
        self.zoom = zoom
    def move(self, dx, dy):
        self.x += dx*self.zoom
        self.y += dy*self.zoom
    def zoom_in(self, dz):
        self.zoom *= dz
    def get_pos(self, pos):
        return ((pos[0]-self.x)-screen.get_width()/2)/self.zoom+screen.get_width()/2, ((pos[1]-self.y)-screen.get_height()/2)/self.zoom+screen.get_height()/2

camera = Camera(0, 0, 1)

class Node:
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.width = 50
        self.height = 50
        self.connections = []
        self.inputConnections = []
        if type == "TGL" or type == "LMP" or type == "CEL":
            self.powered = False
        if type == "CEL":
            self.last = False
            self.lastId = None
    def draw(self):
        pos = camera.get_pos((self.x-self.width/2, self.y-self.height/2))
        color = (27, 66, 66) if HOVERNODE != self else (35, 73, 73)
        if (self.type == "TGL" or self.type == "CEL") and self.powered:
            color = (59, 98, 91)
        if self.type == "LMP":
            color = (10, 30, 30)
            for c in self.inputConnections:
                if c.powered:
                    color = (230, 255, 30)
                    break
        pygame.draw.rect(screen, color, (pos[0], pos[1], self.width/camera.zoom, self.height/camera.zoom), border_radius=int(3/camera.zoom))
        if 'connections' in nodeTypes[self.type]:
            for c in nodeTypes[self.type]['connections']:
                pos = camera.get_pos((self.x+(self.width/2)*c[0], self.y+(self.height/2)*c[1]))
                pygame.draw.circle(screen, (92, 131, 116), pos, 3/camera.zoom)
        if self.type != "LMP":
            text = font.render(self.type, True, (0, 0, 0))
            size = text.get_size()
            text = pygame.transform.scale(text, (size[0]/2/camera.zoom, size[1]/2/camera.zoom))
            size = text.get_size()
            pos = camera.get_pos((self.x-size[0]/2*camera.zoom, self.y-size[1]/2*camera.zoom))
            screen.blit(text, pos)

class Connection:
    def __init__(self, node1:Node, node1Socket:int, node2:Node, node2Socket:int):
        self.node1 = node1
        node1.connections.append(self)
        self.node1Socket = node1Socket
        self.node2 = node2
        node2.inputConnections.append(self)
        self.node2Socket = node2Socket
        self.powered = False
    
    def draw(self):
        pos1 = camera.get_pos((self.node1.x+(self.node1.width/2*nodeTypes[self.node1.type]['connections'][self.node1Socket][0]), self.node1.y+(self.node1.height/2*nodeTypes[self.node1.type]['connections'][self.node1Socket][1])))
        pos2 = camera.get_pos((self.node2.x+(self.node2.width/2*nodeTypes[self.node2.type]['connections'][self.node2Socket][0]), self.node2.y+(self.node2.height/2*nodeTypes[self.node2.type]['connections'][self.node2Socket][1])))
        color = (92, 131, 116) if self.powered else (27, 66, 66)
        pygame.draw.line(screen, color, pos1, pos2, int(3/camera.zoom))

class Widget:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.fontSize = 1
    def draw(self, surf, font:pygame.font.Font):
        pass
    def tick(self, mousePress, mousePos):
        pass

class TextWidget(Widget):
    def __init__(self, x, y, text, font:pygame.font.Font, fontSize=1):
        size = font.size(text)
        super().__init__(x, y, size[0], size[1])
        self.text = text
        self.font = font
        self.fontSize = fontSize
    def draw(self, surf):
        text = self.font.render(self.text, True, (0, 0, 0))
        size = text.get_size()
        text = pygame.transform.scale(text, (size[0]/self.fontSize/camera.zoom, size[1]/self.fontSize/camera.zoom))
        size = text.get_size()
        pos = (self.x, self.y)
        pos = camera.get_pos(pos)
        surf.blit(text, (pos[0]-size[0]/2, pos[1]-size[1]/2))
    def set_text(self, text):
        self.text = text
        size = self.font.size(text)
        self.width = size[0]
        self.height = size[1]

mode:bool = True
elements:list[gui.Button] = []
def change_mode():
    global mode, elements
    mode = not mode
    elements[0].text = "Building Mode" if mode else "Play Mode"

vel = [0, 0]
to_update = []
not_updated = []
camSpeed = 5
tick = 0
SAVING = False
LOADING = False
updateRate = 1
zoom = 0
textEditing:int = -1
textInput:str = ""
MOUSEDOWN:bool = False
HOVERNODE:Node = None
CAM_ZOOM_SPEED:float = 0.95
creatingConnection:bool = False
newConnectionInfo:dict = {'node':None, 'nodeSocket':None, 'pos':(0,0)}
#nodes:list[Node] = [Node(400, 300, "AND"), Node(480, 300, "NOT"), Node(300, 260, "ON"), Node(300, 340, "OFF")]
nodeKeys = {pygame.K_o:"ON", pygame.K_f:"OFF", pygame.K_a:"AND", pygame.K_n:"NOT", pygame.K_r:"OR", pygame.K_x:"XOR", pygame.K_m:"MSD", pygame.K_t:"TGL", pygame.K_d:"LMP", pygame.K_c:"CEL"}
#connections:list[Connection] = [Connection(nodes[0], 2, nodes[1], 0), Connection(nodes[2], 0, nodes[0], 1), Connection(nodes[3], 0, nodes[0], 0)]
connections:list[Connection] = []
nodes:list[Node] = []
decos:list[Widget] = []
elements.append(gui.Button(10, 10, 100, 50, "Building Mode", change_mode, 2))

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Logic Game")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 30)

def step():
    global connections
    newConnections = copy.deepcopy(connections)
    for node in nodes:
        if node.type == "ON":
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = True
        elif node.type == "OFF":
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = False
        elif node.type == "AND":
            n1 = False
            n2 = False
            for c in node.inputConnections:
                if c.node2Socket == 0:
                    if c.powered:
                        n1 = True
                if c.node2Socket == 1:
                    if c.powered:
                        n2 = True
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = n1 and n2
        elif node.type == "OR":
            n1 = False
            n2 = False
            for c in node.inputConnections:
                if c.node2Socket == 0:
                    if c.powered:
                        n1 = True
                if c.node2Socket == 1:
                    if c.powered:
                        n2 = True
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = n1 or n2
        elif node.type == "NOT":
            n = False
            for c in node.inputConnections:
                if c.node2Socket == 0:
                    if c.powered and not c in node.connections:
                        n = True
                        break
            for c in node.connections:
                if c in connections and not c in node.inputConnections:
                    newConnections[connections.index(c)].powered = not n
        elif node.type == "XOR":
            n1 = False
            n2 = False
            for c in node.inputConnections:
                if c.node2Socket == 0:
                    if c.powered:
                        n1 = True
                if c.node2Socket == 1:
                    if c.powered:
                        n2 = True
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = n1 != n2
        elif node.type == "MSD":
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = MOUSEDOWN
        elif node.type == "TGL":
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = node.powered
        elif node.type == "CEL":
            n = False
            ln = None
            for c in node.inputConnections:
                if c.node2Socket == 0:
                    if c.powered:
                        n = True
                        ln = c
                        break
            if (n != node.last or id(ln) != node.lastId) and n:
                node.powered = not node.powered
            for c in node.connections:
                if c in connections:
                    newConnections[connections.index(c)].powered = node.powered
            node.last = n
            node.lastId = id(ln)
    for c in newConnections:
        connections[newConnections.index(c)].powered = c.powered

def draw_nodes(nodes:list[Node]):
    for node in nodes:
        node.draw()

def draw_connections(connections:list[Connection]):
    for connection in connections:
        connection.draw()
    if creatingConnection:
        pos = get_mouse_pos()
        pos = camera.get_pos(pos)
        pos2 = newConnectionInfo['pos']
        pos2 = camera.get_pos(pos2)
        pygame.draw.line(screen, (92, 131, 116), pos, pos2, 3)
        

def distance(pos1, pos2):
    return math.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)

def closest_node(pos):
    min_dist = math.inf
    closest_node = None
    for node in nodes:
        dist = math.sqrt((node.x-pos[0])**2 + (node.y-pos[1])**2)
        if dist < min_dist:
            min_dist = dist
            closest_node = node
    return closest_node

def closest_deco(pos):
    min_dist = math.inf
    closest_deco = None
    for deco in decos:
        dist = math.sqrt((deco.x-pos[0])**2 + (deco.y-pos[1])**2)
        if dist < min_dist:
            min_dist = dist
            closest_deco = deco
    return closest_deco

def get_mouse_pos():
    pos = pygame.mouse.get_pos()
    return ((pos[0]-screen.get_width()/2)*camera.zoom+screen.get_width()/2)+camera.x, ((pos[1]-screen.get_height()/2)*camera.zoom+screen.get_height()/2)+camera.y

def draw_gui():
    for element in elements:
        element.draw(screen, font)

def update_gui():
    for element in elements:
        element.tick(MOUSEPRESS, pygame.mouse.get_pos())

def get_hover_node():
    mp = get_mouse_pos()
    node = closest_node(mp)
    if not node is None:
        if mp[0] >= node.x-node.width/2 and mp[0] <= node.x+node.width/2 and mp[1] >= node.y-node.height/2 and mp[1] <= node.y+node.height/2:
            return node
    return None

def get_hover_deco():
    mp = get_mouse_pos()
    deco = closest_deco(mp)
    if not deco is None:
        if mp[0] >= deco.x-deco.width/2 and mp[0] <= deco.x+deco.width/2 and mp[1] >= deco.y-deco.height/2 and mp[1] <= deco.y+deco.height/2:
            return deco
    return None

def save(slot):
    saveFile = json.load(open("save.json"))
    data = {}
    data['nodes'] = []
    for node in nodes:
        d = {'x':node.x, 'y':node.y, 'type':node.type}
        if node.type == "TGL":
            d['powered'] = node.powered
        elif node.type == "LMP":
            d['powered'] = node.powered
        data['nodes'].append(d)
    data['connections'] = []
    for connection in connections:
        data['connections'].append({'node1':nodes.index(connection.node1), 'node1Socket':connection.node1Socket, 'node2':nodes.index(connection.node2), 'node2Socket':connection.node2Socket, 'powered':connection.powered})
    data['decos'] = []
    for deco in decos:
        data['decos'].append({'x':deco.x, 'y':deco.y, 'text':deco.text})
    saveFile[str(slot)] = data
    json.dump(saveFile, open("save.json", "w"))

def load(slot):
    global nodes, connections, decos
    connections = []
    nodes = []
    decos = []
    saveFile = json.load(open("save.json"))
    if str(slot) in saveFile:
        data = saveFile[str(slot)]
        for node in data['nodes']:
            nodes.append(Node(node['x'], node['y'], node['type']))
            if 'powered' in node:
                nodes[-1].powered = node['powered']
        for connection in data['connections']:
            connections.append(Connection(nodes[connection['node1']], connection['node1Socket'], nodes[connection['node2']], connection['node2Socket']))
            connections[-1].powered = connection['powered']
        if 'decos' in data:
            for deco in data['decos']:
                decos.append(TextWidget(deco['x'], deco['y'], deco['text'], font, 2))

def draw_decos():
    for deco in decos:
        if decos[textEditing] == deco:
            lText = deco.text
            deco.set_text(textInput)
        deco.draw(screen)
        if decos[textEditing] == deco:
            deco.set_text(lText)

def main():
    global creatingConnection, newConnectionInfo, MOUSEDOWN, MOUSEPRESS, tick, SAVING, LOADING, zoom, HOVERNODE, textEditing, textInput
    while True:
        HOVERNODE = get_hover_node()
        HOVERDECO = get_hover_deco()
        MOUSEPRESS = False
        tick += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_UP:
                    vel[1] -= 1
                elif event.key == pygame.K_DOWN:
                    vel[1] += 1
                elif event.key == pygame.K_LEFT:
                    vel[0] -= 1
                elif event.key == pygame.K_RIGHT:
                    vel[0] += 1
                elif event.key == pygame.K_RETURN:
                    step()
                elif event.key == pygame.K_s:
                    if textEditing == -1:
                        SAVING = True
                elif event.key == pygame.K_l:
                    if textEditing == -1:
                        LOADING = True
                elif event.key == pygame.K_EQUALS:
                    zoom += 1
                elif event.key == pygame.K_MINUS:
                    zoom -= 1
                elif event.key == pygame.K_BACKSPACE:
                    if textEditing == -1:
                        if not HOVERNODE is None:
                            for c in HOVERNODE.connections:
                                if c in connections:
                                    connections.remove(c)
                                if c in c.node1.inputConnections:
                                    c.node1.inputConnections.remove(c)
                                if c in c.node2.inputConnections:
                                    c.node2.inputConnections.remove(c)
                            for c in HOVERNODE.inputConnections:
                                if c in connections:
                                    connections.remove(c)
                                if c in c.node1.connections:
                                    c.node1.connections.remove(c)
                                if c in c.node2.connections:
                                    c.node2.connections.remove(c)
                            nodes.remove(HOVERNODE)
                            HOVERNODE = None
                        if not HOVERDECO is None:
                            decos.remove(HOVERDECO)
                            HOVERDECO = None
                if textEditing == -1:
                    for key,nodeType in nodeKeys.items():
                        if event.key == key:
                            pos = get_mouse_pos()
                            nodes.append(Node(pos[0], pos[1], nodeType))
                if textEditing == -1:
                    for i in range(10):
                        if event.key == pygame.K_1 + i - 1:
                            if SAVING:
                                save(i)
                            elif LOADING:
                                load(i)
                if textEditing != -1:
                    if event.key == pygame.K_RETURN:
                        decos[textEditing].set_text(textInput)
                        textEditing = -1
                    elif event.key == pygame.K_ESCAPE:
                        textEditing = -1
                    elif event.key == pygame.K_BACKSPACE:
                        textInput = textInput[:-1]
                    else:
                        textInput += event.unicode
                elif event.key == pygame.K_p:
                    if textEditing == -1:
                        textEditing = len(decos)
                        mp = get_mouse_pos()
                        decos.append(TextWidget(mp[0], mp[1], "", font, 2))
                        textInput = ""
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    vel[1] += 1
                elif event.key == pygame.K_DOWN:
                    vel[1] -= 1
                elif event.key == pygame.K_LEFT:
                    vel[0] += 1
                elif event.key == pygame.K_RIGHT:
                    vel[0] -= 1
                elif event.key == pygame.K_s:
                    SAVING = False
                elif event.key == pygame.K_l:
                    LOADING = False
                elif event.key == pygame.K_EQUALS:
                    zoom -= 1
                elif event.key == pygame.K_MINUS:
                    zoom += 1
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    MOUSEDOWN = True
                    MOUSEPRESS = True
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    MOUSEDOWN = False
                    
        if not mode:
            if tick % updateRate == 0:
                step()
            if MOUSEPRESS:
                node = HOVERNODE
                if not node is None:
                    if node.type == "TGL":
                        node.powered = not node.powered
        
        if MOUSEPRESS and mode:
            if not creatingConnection:
                mousePos = get_mouse_pos()
                node = closest_node(mousePos)
                if not node is None:
                    for c in nodeTypes[node.type]['connections']:
                        if distance(mousePos, (node.x+(node.width/2*c[0]), node.y+(node.height/2*c[1]))) < 10:
                            creatingConnection = True
                            newConnectionInfo['node'] = node
                            newConnectionInfo['nodeSocket'] = nodeTypes[node.type]['connections'].index(c)
                            newConnectionInfo['pos'] = (node.x+(node.width/2*c[0]), node.y+(node.height/2*c[1]))
                            break
            else:
                mousePos = get_mouse_pos()
                node = closest_node(mousePos)
                if not node is None:
                    if node == newConnectionInfo['node']:
                        creatingConnection = False
                    else:
                        for c in nodeTypes[node.type]['connections']:
                            if distance(mousePos, (node.x+(node.width/2*c[0]), node.y+(node.height/2*c[1]))) < 10:
                                if nodeTypes[newConnectionInfo['node'].type]['connections'][newConnectionInfo['nodeSocket']][2]:
                                    connections.append(Connection(node, nodeTypes[node.type]['connections'].index(c), newConnectionInfo['node'], newConnectionInfo['nodeSocket']))
                                else:
                                    connections.append(Connection(newConnectionInfo['node'], newConnectionInfo['nodeSocket'], node, nodeTypes[node.type]['connections'].index(c)))
                                creatingConnection = False
                                break
        update_gui()
        camera.move(vel[0]*camSpeed, vel[1]*camSpeed)
        if zoom == 1:
            camera.zoom_in(CAM_ZOOM_SPEED)
        elif zoom == -1:
            camera.zoom_in(1/CAM_ZOOM_SPEED)
        if textEditing != -1:
            screenSize = screen.get_size()
            camera.x = decos[textEditing].x-screenSize[0]/2
            camera.y = decos[textEditing].y-screenSize[1]/2
        screen.fill((24, 28, 20))
        draw_nodes(nodes)
        draw_connections(connections)
        draw_gui()
        draw_decos()
        if LOADING:
            text = font.render(f"Loading...", True, (0, 0, 0))
            size = text.get_size()
            screen.blit(text, (screen.get_width()/2-size[0]/2, screen.get_height()/2-size[1]/2))
        elif SAVING:
            text = font.render(f"Saving...", True, (0, 0, 0))
            size = text.get_size()
            screen.blit(text, (screen.get_width()/2-size[0]/2, screen.get_height()/2-size[1]/2))
        fps = round(clock.get_fps())
        fpsText = font.render(f"FPS: {fps}", True, (0, 0, 0))
        size = fpsText.get_size()
        screen.blit(fpsText, (screen.get_width()-size[0], screen.get_height()-size[1]))
        pygame.display.flip()
        clock.tick(60)

main()