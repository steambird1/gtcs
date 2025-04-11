from flask import *
import turtle
import threading
import time
import io
import hashlib
from PIL import Image

app = Flask("FountaineMTR")

RED = "0"
GREEN = "."
WARNING = "/"
ERROR = "?"

ZOOM = 250

# KLine graph
signals = {}
#for i in range(10):
#    signals["z" + str(i)] = [[0, (i-5)*50], [0, (i-6)*50], GREEN, ["z" + str(i+1)], 0]
#signals["z10"] = [[0, 200], [0, 300], GREEN, [], 0]

def getmd5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()

AUTH_FREE = False
TRAIN_AUTH = [getmd5("jeangunnhildr"), getmd5("_~_amber~_~")]
CTRL_AUTH = [getmd5("no_klee_here_!")]
BEFEHL_AUTH = [getmd5("barbatos'_wish^)")]

RECM_FREE = False

def check_auth(cur,dtype):
    if AUTH_FREE:
        return True
    if getmd5(cur) not in dtype:
        return False
    else:
        return True

sids = {}
def draw_line(name,fromx,fromy,tox,toy,margin):
    global sids, signals
    if name not in sids:
        sids[name] = 0
    mx = margin# if (fromx < tox) else (-margin)
    my = margin# if (fromy < toy) else (-margin)
    #for x in range(fromx,tox,mx):
    #    for y in range(fromy,toy,my):
    x = fromx
    y = fromy
    if (abs(toy-tox)%margin) > 0 or (abs(fromy-fromx)%margin) > 0:
        raise ValueError("May cause dead loop")
    #if (abs(toy-tox)//margin) != (abs(fromy-fromx)//margin):
    #    raise ValueError("Bad steps")
    while x != tox or y != toy:
        if name+str(sids[name]) in signals:
            signals[name+str(sids[name])][3].insert(0,name+str(sids[name]+1))
        sids[name] += 1
        clst = []
        if name+str(sids[name]-1) in signals:
            clst = [name+str(sids[name]-1)]
        signals[name+str(sids[name])] = [[x,y],[x+mx,y+my],GREEN,clst,0]
        if x != tox:
            x += mx
        if y != toy:
            y += my
        print(x,y)

def getlatest(name):
    global sids
    return name+str(sids[name])

def addstation(name,station,sxd,syd,mxd,myd,dn=""):
    global sids, signals
    cstat = signals[getlatest(name)]
    ent = name + "_" + station + "_ent"
    ext = name + "_" + station + "_ext"
    signals[getlatest(name)][3].insert(0,ent)
    signals[ent] = [cstat[0],[cstat[0][0]+sxd,cstat[0][1]+syd],GREEN,[ext],0]
    sids[name] += 1
    if dn != "":
        signals[ent][3].append(dn + "_" + station + "_ext")
    signals[ext] = [[cstat[0][0]+mxd,cstat[0][1]+myd],[cstat[0][0]+sxd+mxd,cstat[0][1]+syd+myd],RED,[ent,name+str(sids[name])],1]
    signals[name+str(sids[name])] = [[cstat[0][0]+sxd+mxd,cstat[0][1]+syd+myd],[cstat[0][0]+(sxd*2)+mxd,cstat[0][1]+(syd*2)+myd],RED,[ext],0]
"""
draw_line("C",-80,120,-30,60,10)
draw_line("C",-30,60,-30,-60,10)
draw_line("C",-30,-60,-40,-70,10)
draw_line("C",-40,-70,-40,-100,10)
draw_line("C",-40,-100,-100,-100,10)
draw_line("C",-100,-100,-160,-160,10)
draw_line("R",-80,120,-30,160,10)
draw_line("R",-30,160,100,160,10)
signals["C1"][3].append("R1")
"""

#_aincr = 0
#def report_line():
#    _aincr += 1
#    print("Drawing",_aincr,"...")

draw_line("M_up",0,-205,0,-200,5)
addstation("M_up","lyg",0,2,0,3,"M_dn")
#report_line()
draw_line("M_up",0,-200,0,-140,5)
addstation("M_up","gly",0,2,0,3,"M_dn")
#report_line()
draw_line("M_up",0,-130,0,-90,5)
addstation("M_up","ws",0,2,0,3,"M_dn")
draw_line("M_up",0,-80,0,-30,5)
addstation("M_up","dhz",0,2,0,3,"M_dn")
draw_line("M_up",0,-20,0,20,5)
addstation("M_up","sm_stonetur",0,2,0,3,"M_dn")
draw_line("M_up",0,30,50,80,5)
addstation("M_up","Morganstadt",2,2,3,3,"M_dn")
draw_line("M_up",60,90,120,150,5)
addstation("M_up","Quessw",2,2,3,3,"M_dn")
draw_line("M_up",130,160,130,220,5)
addstation("M_up","Mondstadt",0,2,0,3,"M_dn")

draw_line("M_dn",120,225,120,220,-5)
addstation("M_dn","Mondstadt",0,-2,0,-3,"M_up")
draw_line("M_dn",120,220,120,160,-5)
addstation("M_dn","Quessw",-2,-2,-3,-3,"M_up")
draw_line("M_dn",110,150,50,90,-5)
addstation("M_dn","Morganstadt",-2,-2,-3,-3,"M_up")
draw_line("M_dn",40,80,-10,30,-5)
addstation("M_dn","sm_stonetur",0,-2,0,-3,"M_up")
draw_line("M_dn",-10,20,-10,-20,-5)
addstation("M_dn","dhz",0,-2,0,-3,"M_up")
draw_line("M_dn",-10,-30,-10,-80,-5)
addstation("M_dn","ws",0,-2,0,-3,"M_up")
draw_line("M_dn",0,-90,0,-130,-5)
addstation("M_dn","gly",0,-2,0,-3,"M_up")
draw_line("M_dn",0,-140,0,-200,-5)
addstation("M_dn","lyg",0,-2,0,-3,"M_up")

#signals = {"z0":[[-220,0],[180,0],GREEN,["z1"],0],"z1":[[-180,0],[80,0],GREEN,["z2","z3"],0],"z2":[[80,0],[180,0],GREEN,[],0],"z3":[[80,-60],[180,-80],GREEN,[],0]}
visit = []
prev = {}
originals = {}
defaults = {}
zugin = {}

warninfo = ""

def update_signal(name,ovrd=None):
    global signals
    turtle.penup()
    turtle.goto(signals[name][0][0],signals[name][0][1])
    turtle.pendown()
    if not (ovrd is None):
        turtle.pencolor(ovrd)
    elif signals[name][2] == GREEN:
        turtle.pencolor('green')
    elif signals[name][2] == RED:
        turtle.pencolor('red')
    else:
        turtle.pencolor('orange')
    #turtle.write(name)
    extra = ""
    writing = (signals[name][2] != GREEN) or (zugin[name] != "")
    if signals[name][4] < len(signals[name][3]):
        extra = " -> " + signals[name][3][signals[name][4]]
    if zugin[name] != "":
        extra += " & " + zugin[name]
    if writing:
        if signals[name][2] not in [RED, GREEN]:
            turtle.write(name + ": " + signals[name][2] + extra, False, "center", ("Arial", 10, "normal"))
        else:
            turtle.write(name + extra, False, "center", ("Arial", 10, "normal"))     
    turtle.goto(signals[name][1][0],signals[name][1][1])
    turtle.penup()

def scan_signal(source,blue=False):
    global signals, visit, RECM_FREE
    if source in visit:
        return
    visit.append(source)
    update_signal(source,None)
    name = source
    if signals[name][4] < len(signals[name][3]):
        prev[signals[name][3][signals[name][4]]] = source
        nxts = signals[name][3][signals[name][4]]
        scan_signal(nxts,blue)
    for i in range(len(signals[name][3])):
        if i != signals[name][4]:
            #prev[signals[name][3][i]] = source
            scan_signal(signals[name][3][i],True)

@app.route("/signal")
def signal():
    global signals
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    return signals[sname][2]

def length(i):
    return ((signals[i][0][0]-signals[i][1][0])**2 + (signals[i][0][1]-signals[i][1][1])**2)**0.5

@app.route("/signalist")
def signalist():
    global signals
    result = ""
    for i in signals:
        result += i + " " + str(length(i)) + "\n"
    return result

def prettyhtml(s):
    c = "red"
    if s == ".":
        c = "green"
    elif s in "|/123456789<>":
        c = "orange"
    return '<span style="color:{};font-weight:700;">{}</span>'.format(c,s)

@app.route("/signaldisp")
def signaldisp():
    global signals
    return render_template("signalist.html", signals=signals, prettyhtml=prettyhtml, len=len)

zscanned = []

def translate(signal):
    cspdlim = 0
    if signal == ".":
        cspdlim = 240
    elif signal == "|":
        cspdlim = 120
    elif signal == "/" or signal == "<" or signal == ">":
        cspdlim = 60
    elif ord(signal) >= 48 and ord(signal) < 58:
        cspdlim = (ord(signal)-48)*10
    else:
        cspdlim = 0
    return cspdlim

def zugscan(source,comparer=300):
    global zscanned
    #print("scan",source)
    if source in zscanned:
        return (0, "-", source, 0)
    zscanned.append(source)
    #if signals[source][2] != GREEN:
    #    return (0, signals[source][2], source)
    tl = translate(signals[source][2])
    if (tl < 120) and (tl != comparer):
        return (0, signals[source][2], source, 0)
    if len(signals[source][3]) <= 0:
        return (length(source), "-", source, 0)
    try:
        zs = zugscan(signals[source][3][signals[source][4]], comparer)
        return (zs[0] + length(source), zs[1], zs[2], zs[3] + 1)
    except Exception as e:
        print(str(e))
        return (0, "-", source, 0)

def newname(source, dist):
    if length(source) >= dist:
        return source
    else:
        if len(signals[source][3]) <= 0:
            return "?"
        return newname(signals[source][3][signals[source][4]], dist - length(source))

# Return LKJ style signal information
# 0 - Red/Yellow
# 00 - Red (Already entering)
# 1 - Yellow
# < or > - Yellow/Yellow
# 2 - Green/Yellow
# @ - Yellow 2
# 3 - Green
# Otherwise - White
@app.route("/lkjdisp")
def lkjdisp():
    global signals, zscanned
    curpos = request.args.get("sid")
    if curpos not in signals:
        return "?"
    if len(signals[curpos][3]) <= signals[curpos][4]:
        return "0"
    else:
        curpos = signals[curpos][3][signals[curpos][4]]
    zscanned = []
    zs = zugscan(curpos)
    print(zs)
    if zs[3] == 0:
        if zs[1] in "123456789":
            return "1"
        elif zs[1] in "<>":
            return zs[1]
        elif zs[1] in "|.":
            return "3"
        else:
            return "0"
    # 0 - Red/corr, 1 - Yellow, 2 - Green-yellow, 3 - Green
    zlevel = 0
    dstate = False
    if zs[1] == "|":
        zlevel = 2
    elif zs[1] == ".":
        zlevel = 3
    elif zs[1] == "<" or zs[1] == ">":
        zlevel = 0
        dstate = True
    elif zs[1] in "123456789":
        zlevel = 1
    zlevel = min(3, zlevel + zs[3])
    if (zlevel == 1) and dstate:
        return "@"
    else:
        return str(zlevel)

# Return distance (meter)
@app.route("/zugdist")
def zugdist():
    global signals, zscanned
    curpos = request.args.get("sid")
    curkilo = request.args.get("dev")
    curlim = int(request.args.get("spd"))
    zscanned = []
    if curpos not in signals:
        return "1 - ? ?"
    if int(curkilo) > 0:
        res = [length(curpos), "-", "?"]
        if len(signals[curpos][3]) > 0:
            #print("Scan",signals[curpos][3][signals[curpos][4]],"as",translate(signals[curpos][2]))
            zs = zugscan(signals[curpos][3][signals[curpos][4]],curlim)
            res[0] += zs[0]
            res[1] = zs[1]
            res[2] = zs[2]
        res[0] -= int(curkilo)/ZOOM
        return str(int(res[0]*ZOOM)) + " " + res[1] + " " + res[2] + " " + newname(curpos, int(curkilo)/ZOOM)
    if signals[curpos][2] != GREEN:
        return "1 " + signals[curpos][2] + " " + curpos + " " + newname(curpos, int(curkilo)/ZOOM)
    zs = zugscan(curpos,curlim)
    return str(int(zs[0]*ZOOM - int(curkilo))) + " " + zs[1] + " " + zs[2] + " " + newname(curpos, int(curkilo)/ZOOM)

@app.route("/diverg")
def diverging():
    global signals, CTRL_AUTH
    if not check_auth(request.args.get("auth"), CTRL_AUTH):
        return ERROR
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    stgt = request.args.get("stat")
    if stgt not in signals[sname][3]:
        return RED
    signals[sname][4] = signals[sname][3].index(stgt)
    if signals[sname][4] > defaults[sname]:
        signals[sname][2] = '>'
        return '>'
    elif signals[sname][4] < defaults[sname]:
        signals[sname][2] = '<'
        return '<'
    else:
        signals[sname][2] = '.'
        return '.'

@app.route("/signalset")
def signalset():
    global signals, CTRL_AUTH
    if not check_auth(request.args.get("auth"), CTRL_AUTH):
        return ERROR
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    sstat = request.args.get("stat")
    signals[sname][2] = sstat
    #update_signal(sname)
    return sstat

@app.route("/zug")
def zug():
    global signals, warninfo, TRAIN_AUTH
    if not check_auth(request.args.get("auth"), TRAIN_AUTH):
        return ERROR
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    state = request.args.get("type")
    zugid = request.args.get("name")
    # 0 : in, 1 : out
    if state == "0":
        if signals[sname][2] == RED:
            warninfo += "<p style=\"color: red;\">[Alert] Train " + zugid + " entering occupied track</p>\n"
        originals[sname] = signals[sname][2]
        signals[sname][2] = RED
        zugin[sname] = zugid
        if sname in prev:
            originals[prev[sname]] = signals[prev[sname]][2]
            signals[prev[sname]][2] = WARNING
        return RED
    elif state == "1":
        if zugin[sname] != zugid:
            warninfo += "<p style=\"color: orange;\">[Warning] Train " + zugid + " not entering " + sname + ", but exiting</p>\n"
            return RED
        if sname in originals:
            signals[sname][2] = originals[sname]
        if sname in prev:
            if prev[sname] in originals:
                signals[prev[sname]][2] = originals[prev[sname]]
        zugin[sname] = ""
        return signals[sname][2]
    else:
        return RED

graph_done = False
curerr = ""

@app.route("/state")
def state():
    global curerr
    if curerr != "":
        return curerr, 500
    return send_file("turtle.png")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/msg")
def msg():
    global warninfo
    mode = request.args.get("mode")
    if mode == "zeit":
        return time.ctime()
    elif mode == "clr":
        warninfo = ""
        return ""
    else:
        return warninfo

zugbefehl={}

# Receive state
zugrcv={}

SCRTEMPLATE = """
const disp = {"-1":"Unknown","0":"Unread","1":"Sent","2":"Read"};
const disc = {"-1":"gray","0":"black","1":"green","2":"blue"};
setInterval(function() {
        var vd = document.getElementById("rcstate");
        var s = new XMLHttpRequest();
        s.open('GET', '/befehl?mode=query&name=%s')
        s.send(null);
        s.onreadystatechange = function() {
            if (s.readyState == 4) {
                var rcdr = document.getElementById("rcstate");
                try {
                    var curr = s.responseText.trim();
                    rcdr.innerHTML = disp[curr];
                    rcdr.style = "font-weight: 700; color: " + disc[curr];
                } catch (e) {
                    console.log(e);
                    rcdr.innerHTML = "Unknown";
                    rcdr.style = "font-weight: 700; color: gray;";
                }
            }
        };
}, 1000);
"""

@app.route("/befehl",methods=['GET','POST'])
def befehl():
    global zugbefehl, zugrcv, SCRTEMPLATE
    mode = request.args.get("mode")
    if mode == "get":
        if check_auth(request.args.get("auth"), TRAIN_AUTH):
            name = request.args.get("name")
            if name not in zugrcv:
                zugrcv[name] = -1
            if zugrcv[name] == 0:
                zugrcv[name] = 1
            if name not in zugbefehl:
                zugbefehl[name] = ""
            return zugbefehl[name]
        else:
            return "Operation not permitted (check train authorization)", 403
    elif mode == "query":
        name = request.args.get("name")
        if name not in zugrcv:
            zugrcv[name] = -1
        return str(zugrcv[name])
    elif mode == "confirm":
        if check_auth(request.args.get("auth"), TRAIN_AUTH):
            name = request.args.get("name")
            if name not in zugrcv:
                zugrcv[name] = -1
            if zugrcv[name] == 1:
                zugrcv[name] = 2
            return "OK"
        else:
            return "Operation not permitted", 403
    elif mode == "write":
        if check_auth(request.form.get("auth"), BEFEHL_AUTH):
            name = request.form.get("name")
            stct = time.ctime()
            sdata = request.form.get("data")
            zugbefehl[name] = stct + " from center: " + sdata
            zugrcv[name] = 0
            return render_template("befehl.html", stct=stct, sdata=sdata, scr=(SCRTEMPLATE % name))
        else:
            return "Operation not permitted", 403
    else:
        return "Invalid operation", 400

@app.route("/befehlgui")
def befehlgui():
    return render_template("befehlgui.html")

@app.route("/")
def helper():
    return "Welcome to Fountaine MTR!"

def ar():
    app.run(host="0.0.0.0", port="5033")

turtle.speed("fastest")
turtle.delay(0)
turtle.pensize(8)
#turtle.tracer(False)

for i in signals:
    defaults[i] = signals[i][4]
    zugin[i] = ""

def imgupd():
    global graph_done, signals, visit
    graph_done = False
    turtle.clear()
    for i in signals:
        visit = []
        scan_signal(i)
        break
    graph_done = True
    try:
        screen = turtle.getcanvas()
        screen.postscript(file="turtle.eps",colormode='color')
        s = Image.open("turtle.eps")
        s = s.resize((s.size[0], s.size[1]))
        s.save("turtle.png", "png")
        curerr = ""
    except Exception as e:
        curerr = str(e)
        print(curerr)
    turtle.ontimer(imgupd, 1000)

if __name__ == '__main__':
    for i in signals:
        scan_signal(i)
        break
    t = threading.Thread(target=ar)
    t.start()
    print("Graphics start")
    turtle.ontimer(imgupd, 1000)
    turtle.mainloop()
