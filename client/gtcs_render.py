import threading
import panda3d
from panda3d.core import *
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from math import *

from http.server import HTTPServer, BaseHTTPRequestHandler

loadPrcFileData("", "catch-signals 0")

# This will start a small server at port 6160 to communicate
# with GTCS main program.
PORT=6160
TERMINATE="####"
ZOOM=3
NIGHT=True

# Manage only S-signal for debugging
signal_info = []
DEBUG = False
FREE = False
graphpos = 0
accufix = 0

default_scene = "models/environment"
default_texture = None
signal_scenes = []

class GTCSMainApplication(ShowBase):
    def __init__(self):
        super().__init__()

        if DEBUG:
            base.useDrive()
            base.useTrackball()
            self.env1 = self.loader.loadModel("models/environment")
            self.env1.reparentTo(self.render)

        self.free_location = False
        self.sunlight = panda3d.core.AmbientLight('ambientLight')
        if NIGHT:
            self.setBackgroundColor(r=0,g=0,b=0,a=0)
            self.sunlight.setColor((0.5, 0.5, 0.5, 1))
        else:
            self.setBackgroundColor(r=0.5294,g=0.8078,b=0.9216,a=0)
            
        self.light = render.attachNewNode(self.sunlight)
        self.light.setPos(10, 30, 3)
        self.render.setLight(self.light)

        self.light_models = []
        self.lightings = []
        #self.camera.look_at(0, 0, 0)
        self.red_light = self.loader.loadTexture("gtcs_red_texture.png")
        self.yellow_light = self.loader.loadTexture("gtcs_yellow_texture.png")
        self.green_light = self.loader.loadTexture("gtcs_green_texture.png")
        self.metal = self.loader.loadTexture("gtcs_metal.png")
        # self.block1 = self.loader.loadModel("test2.gltf")
        # self.block1.reparentTo(self.render)

        # self.block1.setPos(0, 20, 3)
        print("Camera configured")
        self.camera.setScale(1, 1, 1)
        self.camera.setPos(-1, 0, 45)
        self.camera.lookAt(100, 0, 45)

        for i in range(0,10000,500):
            newrail = self.loader.loadModel("gtcs_rail.stl")
            newrail.reparentTo(self.render)
            newrail.setTexture(self.metal)
            newrail.setPos(-i, -30, 0)

        self.task_mgr.add(self.UpdateSceneTask, "SceneUpdater")
        self.task_mgr.add(self.MovingTask, "CameraMover")
    def AddIllumination(self, color_desc, offset=0):
        imain = panda3d.core.PointLight('dlight{}'.format(str(len(self.lightings))))
        imain.setColor(color_desc)
        ipar = self.render.attachNewNode(imain)
        self.lightings.append(ipar)
    def AddLights(self, texture=None, altexture=None, ltspec="gtcs_tbase.stl", sgspec="gtcs_red.stl"):
        ltmain = self.loader.loadModel(ltspec)
        sgmain = self.loader.loadModel(sgspec)
        if not (altexture is None):
            ltmain.setTexture(altexture)
        if not (texture is None):
            sgmain.setTexture(texture)
        ltmain.reparentTo(self.render)
        sgmain.reparentTo(self.render)
        self.light_models.append([ltmain, sgmain])
    def ModifyIllumination(self, id, x, y, z, color_desc, offset=0, turnon=True):
        while len(self.lightings) <= id:
            self.AddIllumination(color_desc, offset)
        #ipar = self.lightings[id]
        iparz = self.render.find("**/dlight{}".format(str(id)))
        ipar = iparz.node()
        flag = False
        #print("Current configuration of color",id,":",ipar.getColor())
        self.render.clearLight(iparz)
        ipar.setColor(color_desc)
        iparz.setPos(x-accufix+12, y, z-offset)
        iparz.lookAt(-graphpos, 0, 45)
        if turnon:
            self.render.setLight(iparz)
    def ModifyLights(self, id, x, y, z, texture=None, offset=0, altexture=None, ltspec="gtcs_tbase.stl", sgspec="gtcs_red.stl"):
        while len(self.light_models) <= id:
            self.AddLights(texture, altexture, ltspec, sgspec)
        ltmain = self.light_models[id][0]
        sgmain = self.light_models[id][1]
        if not (altexture is None):
            ltmain.setTexture(altexture)
        if not (texture is None):
            sgmain.setTexture(texture)
        if ltspec != "gtcs_tbase.stl":
            self.light_models[id][0] = self.loader.loadModel(ltspec)
        if sgspec != "gtcs_red.stl":
            self.light_models[id][1] = self.loader.loadModel(sgspec)
        
        ltmain.setPos(x-accufix, y, z)
        sgmain.setPos(x-accufix, y, z-offset)
    def ModifyScenes(self, id, x, y, z, model, texture=None):
        self.ModifyLights(id, x, y, z, None, 1000000, texture, model)
    def GetSignalTexture(self, signal):
        if (signal in [".","|"]):
            return self.green_light
        elif (signal.isdigit() and signal != "0") or (signal in ["<",">","/"]):
            return self.yellow_light
        else:
            return self.red_light
    def GetSignalColor(self, signal):
        if (signal in [".","|"]):
            return (0,0.3,0,0)
        elif (signal.isdigit() and signal != "0") or (signal in ["<",">","/"]):
            return (0.3,0.3,0,0)
        else:
            return (0.3,0,0,0)
    def GetSignalOffset(self, signal):
        if (signal in [".","|"]):
            return 40
        elif (signal.isdigit() and signal != "0") or (signal in ["<",">","/"]):
            return 20
        else:
            return 0
    def UpdateSignalScene(self, id, sname, x, y, z):
        global signal_scenes, default_scene, default_texture
        scname = default_scene
        txname = default_texture
        if sname in signal_scenes:
            scname = signal_scenes[sname][0]
            txname = signal_scenes[sname][1]
        #print("Loading scene",scname,"with texture",txname,"at",x,y,z)
        if not (scname is None):
            self.ModifyScenes(id, x, y, z, scname, txname)
    def UpdateSceneTask(self, task):
        global signal_info
        lts = 0
        ils = 0
        self.render.setLightOff()
        self.render.setLight(self.light)
        for i in signal_info:
            try:
                #print("Processing:",i)
                csp = i.split(" ")
                if len(csp) < 2:
                    continue
                dis = int(csp[0])
                if csp[1] == "S":
                    self.ModifyLights(lts, (-dis)*ZOOM, 0, 0, self.GetSignalTexture(csp[3]), self.GetSignalOffset(csp[3]))
                    lts += 1
                    self.ModifyIllumination(ils, (-dis)*ZOOM, 0, 0, self.GetSignalColor(csp[3]), self.GetSignalOffset(csp[3]))
                    ils += 1
                    if len(csp) >= 4:
                        self.UpdateSignalScene(lts, csp[3], (-dis)*ZOOM, 0, 0)
                        lts += 1
                    #print("Loading signal:",csp)
            except Exception as e:
                print("Data error:",str(e))
        for i in range(lts, len(self.light_models)):
            self.ModifyLights(i, 1000000, 1000000, 1000000)
        for i in range(ils, len(self.lightings)):
            self.ModifyIllumination(i, 1000000, 1000000, 1000000, (1,1,1,0), turnon=False)
        return Task.cont
    def MovingTask(self, task):
        global graphpos, FREE
        if (not self.free_location) or (not FREE):
            self.camera.setPos(-graphpos, 0, 45)
            self.camera.lookAt(-graphpos-2, 0, 45)
            self.free_location = True
        return Task.cont
# Should be provided with signal data fetched by server (distance information provided)
def report_info(signal_data):
    global signal_info
    signal_info = signal_data

def report_location(ginfo, ainfo):
    global graphpos, accufix, ZOOM
    graphpos = ginfo*ZOOM
    accufix = ainfo*ZOOM

def render_thread():
    global gtcs_app
    gtcs_app = GTCSMainApplication()
    gtcs_app.run()

class Request(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(400)
        self.send_header('Content-Type','text/plain')
        self.send_header('Connection','close')
        self.end_headers()
        self.wfile.write("Bad Request, please use POST instead".encode('utf-8'))
    
    def do_POST(self):
        # Write in following format:
        # (ginfo: int) (ainfo: int)
        # signal data ...
        try:
            data = self.rfile.read(int(self.headers['content-length'])).decode().split("\n")
            headline = data[0].split(" ")
            #print("Read data:",data)
            report_location(int(headline[0]), int(headline[1]))
            #report_info(data[1:])
            stream = []
            for i in data[1:]:
                if i.strip()[:len(TERMINATE)] == TERMINATE:
                    break
                stream.append(i)
            report_info(stream)
            self.send_response(200)
            self.send_header('Content-Type','text/plain')
            self.send_header('Connection','close')
            self.end_headers()
            self.wfile.write("OK".encode('utf-8'))
        except Exception as e:
            print("Server error:",str(e))
            self.send_response(500)
            self.send_header('Content-Type','text/plain')
            self.send_header('Connection','close')
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

def server_thread():
    global PORT
    host = ('', PORT)
    if PORT == 5033:
        print("Port is conflict with GTCS main program. Setting to default.")
        PORT = 6160
    server = HTTPServer(host, Request)
    print("Server will be run at {}:{}".format(host[0], host[1]))
    server.serve_forever()

if __name__ == '__main__':
    #print("You are in GTCS debugger. Displaying debugger scene.")
    # TODO: Others cannot load ???!!!
    # TODO: Change zoom
    #
    if DEBUG:
        signal_info = ["100 S / testname", "120 S .", "160 S 0", "190 S 9"]
    #DEBUG = True

server_thr = threading.Thread(target=server_thread)
server_thr.start()
render_thread()
#graph_thr = threading.Thread(target=render_thread)
#graph_thr.start()