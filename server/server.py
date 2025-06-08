from flask import *
import turtle
import threading
import time
import io
import hashlib
from PIL import Image
import urllib
import random
import datetime

app = Flask("FountaineMTR")

PROHIBIT = "x"
RED = "0"
REDYELLOW = "-"
GREEN = "."
WARNING = "/"
PREWARNING = "|"
ERROR = "?"

DANGEROUS = ["0", "-", "x", "?"]

ZOOM = 250
SEED = 616
SEED2 = 12312345
SEED3 = 45645612
SEED4 = 11451419198

SIMU_TRAIN = True

# To generate terrains.
# [lower, upper)
def randz(lower, upper):
    global SEED
    res = (SEED * SEED2 + SEED3) % SEED4
    SEED = res
    return res%(upper-lower)+lower

# KLine graph
signals = {}
addinfos = {}

translation = {}

RED_AWAIT = 60

manuals = {}
red_bars = []
red_timer = {}
red_at_exit = []
with_train = {}
#for i in range(10):
#    signals["z" + str(i)] = [[0, (i-5)*50], [0, (i-6)*50], GREEN, ["z" + str(i+1)], 0]
#signals["z10"] = [[0, 200], [0, 300], GREEN, [], 0]

# [Name: from, to, speed, signal, dev, auto]
# (for no train occupied: signals at red will be set to green after 1 min, with speed limit 60 km/h)
# diverging track will be configured (through dijkstra)
# (automatic information will be added as well)
# TODO: Add /zug processor !!!
# TODO: Train simulator not done
trains = {}
zeitplan = {}
deact_cnt = {}
avoid_state = {}

def getmd5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def length(i):
    return ((signals[i][0][0]-signals[i][1][0])**2 + (signals[i][0][1]-signals[i][1][1])**2)**0.5

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
    mx = abs(margin)# if (fromx < tox) else (-margin)
    my = abs(margin)# if (fromy < toy) else (-margin)
    #for x in range(fromx,tox,mx):
    #    for y in range(fromy,toy,my):
    x = fromx
    y = fromy
    if (abs(toy-tox)%mx) > 0 or (abs(fromy-fromx)%my) > 0:
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
        if x < tox:
            x += mx
        elif x > tox:
            x -= mx
        if y < toy:
            y += my
        elif y > toy:
            y -= my
        print(x,y)

def getlatest(name):
    global sids
    return name+str(sids[name])

def addstation(name,station,sxd,syd,mxd,myd,dn="",tr="",pcnt=3):
    global sids, signals, red_at_exit, translation
    cstat = signals[getlatest(name)]
    ent = name + "_" + station + "_ent"
    ext = name + "_" + station + "_ext"
    red_at_exit.append(ext)
    signals[getlatest(name)][3].insert(0,ent)
    signals[ent] = [cstat[0],[cstat[0][0]+sxd,cstat[0][1]+syd],GREEN,[ext],0]
    signals[ent][3].append(getlatest(name))
    sids[name] += 1
    if dn != "":
        signals[ent][3].append(dn + "_" + station + "_ext")
    signals[ext] = [[cstat[0][0]+mxd,cstat[0][1]+myd],[cstat[0][0]+sxd+mxd,cstat[0][1]+syd+myd],RED,[ent,name+str(sids[name])],1]
    signals[name+str(sids[name])] = [[cstat[0][0]+sxd+mxd,cstat[0][1]+syd+myd],[cstat[0][0]+(sxd*2)+mxd,cstat[0][1]+(syd*2)+myd],"6",[ext],0]
    if tr != "":
        translation[ext] = tr
        translation[dn + "_" + station + "_ext"] = tr
    for i in range(1,pcnt+1):
        cpk = name + "_" + station + "_park" + str(i)
        signals[ent][3].append(cpk)
        signals[cpk] = [[cstat[0][0]+mxd+i,cstat[0][1]+myd+i],[cstat[0][0]+sxd+mxd+i,cstat[0][1]+syd+myd+i],RED,[ent,ext],1]
        signals[ext][3].append(cpk)
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

# Thus adding auxiliary track for liyuegang
signals["M_upt_lyg"] = [[0, -200], [-5, -195], RED, ["M_up3", "M_dnt_lyg"], 0]
signals["M_dnt_lyg"] = [[-10, -190], [-5, -195], RED, ["M_dn80", "M_lyg_gleis3_ent", "M_upt_lyg"], 0]
signals["M_lyg_gleis3_ent"] = [[-5, -195], [-5, -200], GREEN, ["M_lyg_gleis3_ext", "M_dnt_lyg"], 0]
signals["M_lyg_gleis3_ext"] = [[-5, -200], [-5, -205], RED, ["M_lyg_gleis3_ent", "M_lyg_gleis4_ent"], 0]
signals["M_lyg_gleis4_ent"] = [[-5, -205], [-5, -210], GREEN, ["M_lyg_gleis4_ext", "M_lyg_gleis3_ext"], 0]
signals["M_lyg_gleis4_ext"] = [[-5, -210], [-5, -215], RED, ["M_lyg_gleis4_ent", "M_lyg_gleis3_ent", "S_up1"], 2]

addstation("M_up","lyg",0,2,0,3,"M_dn","Liyue")
#report_line()
draw_line("M_up",0,-200,0,-140,5)
addstation("M_up","gly",0,2,0,3,"M_dn","Guiliyuan")
#report_line()
draw_line("M_up",0,-130,0,-90,5)
addstation("M_up","ws",0,2,0,3,"M_dn","Wangshu")
draw_line("M_up",0,-80,0,-30,5)
addstation("M_up","dhz",0,2,0,3,"M_dn","Dihuazhou")
draw_line("M_up",0,-20,0,20,5)
addstation("M_up","sm_stonetur",0,2,0,3,"M_dn","Steintur (am Liyue)")
draw_line("M_up",0,30,50,80,5)
addstation("M_up","Morganstadt",2,2,3,3,"M_dn","Morganstadt")
draw_line("M_up",60,90,120,150,5)
addstation("M_up","Quessw",2,2,3,3,"M_dn","Quellswasser")
draw_line("M_up",130,160,130,220,5)
addstation("M_up","Mondstadt",0,2,0,3,"M_dn","Mondstadt")

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
draw_line("M_dn",-10,-90,-10,-130,-5)
addstation("M_dn","gly",0,-2,0,-3,"M_up")
draw_line("M_dn",-10,-140,-10,-200,-5)
addstation("M_dn","lyg",0,-2,0,-3,"M_up")

signals["M_up2"][3].append("M_upt_lyg")
signals["M_dn79"][3].append("M_dnt_lyg")

draw_line("V_up",130,160,200,160,5)
addstation("V_up", "Sternfall", 2, 0, 3, 0, "V_dn", "Sternfall")
draw_line("V_up",205,160,245,200,5)
addstation("V_up", "Windsehenberg", 0, 2, 0, 3, "V_dn", "Windsehenberg")
draw_line("V_up",245,205,310,270,5)
addstation("V_up", "Dandelions", 0, 2, 0, 3, "V_dn", "Dandelions")
draw_line("V_dn",320,280,315,275,-5)
addstation("V_dn", "Dandelions", 0, -2, 0, -3, "V_up")
draw_line("V_dn",310,270,245,205,-5)
addstation("V_dn", "Windsehenberg", 0, -2, 0, -3, "V_up")
draw_line("V_dn",245,200,205,160,-5)
addstation("V_dn", "Sternfall", -2, 0, -3, 0, "V_up")
draw_line("V_dn",200,160,130,160,-5)

signals["M_up_Quessw_ext"][3].append("V_up1")
signals[getlatest("V_dn")][3].append("M_dn_Quessw_ent")
signals[getlatest("V_dn")][4] = 1

draw_line("S_up",-5,-205,-50,-250,-5)
addstation("S_up", "Chasm", -2, -2, -3, -3, "S_dn", "Chasm")
draw_line("S_up",-55,-260,-155,-260,-5)
addstation("S_up", "Sumeru", -2, 0, -3, 0, "S_dn", "Sumeru")
draw_line("S_dn",-160,-265,-155,-260,5)
addstation("S_dn", "Sumeru", 2, 0, 3, 0, "S_up")
draw_line("S_dn",-155,-255,-55,-255,5)
addstation("S_dn", "Chasm", 2, 2, 3, 3, "S_up")
draw_line("S_dn",-50,-250,-5,-205,5)

signals[getlatest("S_dn")][3].append("M_lyg_gleis3_ent")
signals[getlatest("S_dn")][4] = 1

# New Inazuma Map (Bridge has approx. 90 km/h speed limit)

signals["M_dn_lyg_ext"][3].append("I_up1")

draw_line("I_up",5,-200,300,-200,5)
draw_line("I_up",300,-200,300,200,5)
addstation("I_up", "Inazuma", 0, 2, 0, 3, "I_dn")
draw_line("I_up",305,205,305,155,5)
addstation("I_up", "Watatsumi", 0, -2, 0, -3, "I_dn")
draw_line("I_dn",305,160,305,155,5)
addstation("I_dn", "Watatsumi", 0, 2, 0, 3, "I_up")
draw_line("I_dn",305,155,305,205,5)
addstation("I_dn", "Inazuma", 0, -2, 0, -3, "I_up")
draw_line("I_dn",300,200,300,-200,5)
draw_line("I_dn",300,-200,5,-200,5)

signals["I_up1"][3].append("M_dn_lyg_ext")
signals[getlatest("I_dn")][3].append("M_lyg_gleis4_ent")

def generate_for(name,c1=2,c2=8,mnspd=10,mxspd=20):
    global sids, addinfos, ZOOM
    for i in range(1, sids[name]):
        cdis = 0
        sname = name + str(i)
        if sname not in addinfos:
            addinfos[sname] = []
        lz = int(length(sname)*ZOOM)
        while cdis <= lz:
            cst = randz(0, 100)
            if cst <= c1:
                addinfos[sname].append([cdis, "P0"])
                cdis += randz(100, 200)
                cdis = min(cdis, lz)
                addinfos[sname].append([cdis, "P1"])
            elif cst <= c2:
                addinfos[sname].append([cdis, "La " + str(randz(0,5)*10) + " " + str(randz(mnspd,mxspd)*10)])
                cdis += randz(500, 1500)
                cdis = min(cdis, lz)
                addinfos[sname].append([cdis, "Le"])
            cdis += randz(100, 1000)

generate_for("M_up")
generate_for("M_dn")
generate_for("V_up")
generate_for("V_dn")
generate_for("S_up",8,20,6,15)
generate_for("S_dn",8,20,6,15)

generate_for("I_up",1,18,5,20)
generate_for("I_dn",1,18,5,20)

draw_line("F_up",-5,-205,-805,605,5)
addstation("F_up", "Fountaine", -2, 0, 3, 0, "F_dn", "Fountaine")
draw_line("F_dn",-810,610,-805,605,-5)
addstation("F_dn", "Fountaine", 2, 0, -3, 0, "F_up")
draw_line("F_dn",-800,600,-5,-205,-5)
signals["M_lyg_gleis3_ext"][3].append("F_up1")
signals[getlatest("F_dn")][3].append("M_lyg_gleis3_ent")
signals[getlatest("F_dn")][4] = 1

for i in range(10,150,10):
    signals["F_up"+str(i)][3].append("F_dn"+str(sids["F_dn"]-i))
    signals["F_dn"+str(i)][3].append("F_up"+str(sids["F_up"]-i))


# Current for debug:
# La [lower] [upper] - speed limit start; Le - speed limit clear; T [text] - texture information; S [name] [stat] - signal
# P0 - neutral area; P1 - repowering

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

# addinfos is a list: [dist to signal, info str]
# Supporting: permanent speed suggestions and text indications
# offset allowed.
NORMREFDIST = 4500

def sdscan(sname,cdist=0,refdist=4500):
    global addinfos, signals, ZOOM, red_timer
    if refdist < 0:
        return []
    ctmp = []
    if sname in addinfos:
        for i in addinfos[sname]:
            ctmp.append([str(int(i[0]+cdist)),i[1]])
    cl = length(sname) * ZOOM
    if signals[sname][4] < len(signals[sname][3]):
        sgt = signals[sname][3][signals[sname][4]]
        addins = ""
        if (sgt in red_timer) and (red_timer[sgt][2]):
            addins = " " + str(red_timer[sgt][1])
        ctmp.append([str(int(cdist+cl)), "S " + sgt + " " + str(signals[sgt][2]) + addins])
        ctmp += sdscan(sgt, cdist + cl, refdist - cl)
    return ctmp

# Return acceleration
def sdeval(scanres,vist,vsoll=240):
    accel = 0
    adis = 10**8
    # km/h
    vziel = vist
    #print(scanres)
    if vist > vsoll:
        accel = -4
        vziel = vsoll
        adis = 0
    elif vist > vsoll - 10:
        accel = -1
        vziel = vsoll
        adis = 0
    for i in scanres:
        csp = [int(i[0])] + i[1].split(" ")
        dis = int(csp[0])
        if dis <= 0:
            continue
        if csp[1] == "S":
            vkmh = translate(csp[3])
            if vist < vkmh:
                continue
            if dis <= 200:
                caccel = -6
            else:
                vms = vkmh / 3.6
                caccel = -((vist/3.6)*(vist/3.6)-vms*vms)/(2*(dis-200))
            if caccel < accel:
                accel = caccel
                vziel = vkmh
                adis = dis
    return (accel, vziel, adis)

@app.route("/signaldata")
def signaldata():
    global addinfos, signals, NORMREFDIST, ZOOM
    sname = request.args.get("sid")
    sdev = int(request.args.get("dev"))
    if sname not in signals:
        return "?"
    rsc = sdscan(sname,-sdev,NORMREFDIST+sdev)
    res = str(int(length(sname)*ZOOM)-sdev) + "\n" + "\n".join([" ".join(i) for i in rsc])
    return res

@app.route("/addataupdate")
def addataupdate():
    global signals, CTRL_AUTH, addinfos
    if not check_auth(request.args.get("auth"), CTRL_AUTH):
        return "Operation not permitted", 403
    try:
        sname = request.args.get("sid")
        if sname not in signals:
            return "Invalid parameter", 400
        sdis = request.args.get("dis")
        stgt = urllib.parse.unquote(request.args.get("stat"))
        if stgt == "x":
            for i in range(len(addinfos[sname])):
                if addinfos[sname][i][0] == int(sdis):
                    addinfos[sname].pop(i)
                    break
            else:
                return "Element not found", 400
            return "Removal completed successfully"
        else:
            for i in range(len(addinfos[sname])):
                if addinfos[sname][i][0] > int(sdis):
                    addinfos[sname].insert(i, [int(sdis), stgt])
                    break
            else:
                addinfos[sname].append([int(sdis), stgt])
            return "Operation completed successfully"
    except Exception as e:
        return "Internal server error: " + str(e), 500

@app.route("/signalist")
def signalist():
    global signals
    result = ""
    for i in signals:
        result += i + " " + str(length(i)*ZOOM) + "\n"
    return result

@app.route("/signalstates")
def signalstates():
    global signals, zugin
    result = ""
    for i in signals:
        si = signals[i]
        result += i + " " + str(si[0][0]) + " " + str(si[0][1]) + " " + str(si[1][0]) + " " + str(si[1][1]) + " " + si[2] + " " + ",".join(si[3]) + " " + str(si[4]) + " "
        if i not in zugin:
            result += "*"
        else:
            result += ("*" if (zugin[i].strip() == "") else zugin[i])
        result += "\n"
    return result

def prettyhtml(s):
    c = "red"
    if s == "0":
        c = "red"
    elif s == ".":
        c = "green"
    elif (s.isdigit()) or (s in "|/<>"):
        c = "orange"
    return '<span style="color:{};font-weight:700;">{}</span>'.format(c,s)

@app.route("/signaldisp")
def signaldisp():
    global signals
    return render_template("signalist.html", signals=signals, prettyhtml=prettyhtml, len=len)

@app.route("/signaladdisp")
def signaladdisp():
    global addinfos
    return render_template("addslist.html", addinfos=addinfos, str=str)

zscanned = []

def translate(signal):
    cspdlim = 0
    if signal == ".":
        cspdlim = 240
    elif signal == "|":
        cspdlim = 120
    elif signal == "/" or signal == "<" or signal == ">":
        cspdlim = 60
    elif signal.isdigit():
        cspdlim = (int(signal))*10
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
    if (tl < 240) and (tl != comparer):
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
# (LKJ actually only works for 120 km/h environment in the past,
# but with this LKJ/CTCS update, green 2-5 will be available)
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
        if zs[1] in "/":
            return "1"
        elif zs[1].isdigit():
            if zs[1] == "0":
                return "0"
            elif int(zs[1]) < 10:
                return "1"
            else:
                return "2"
        elif zs[1] in "<>":
            return zs[1]
        elif zs[1] in "|.":
            return "3"
        else:
            return "0"
    # 0 - Red/corr, 1 - Yellow, 2 - Green-yellow, 3 - Green
    # This is an announcement towards
    zlevel = 0
    dstate = False
    if zs[1] == "/":
        zlevel = 1
    elif zs[1] == "|":
        # Currently an equivalent to no warning
        zlevel = 2
    elif zs[1] == ".":
        zlevel = 3
    elif zs[1] == "<" or zs[1] == ">":
        zlevel = 0
        dstate = True
    elif zs[1].isdigit():
        if zs[1] == "0":
            zlevel = 0
        elif int(zs[1]) < 10:
            zlevel = 1
        else:
            zlevel = 2
    zlevel = min(7, zlevel + zs[3])
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

def divergcall(sname, stgt):
    global signals, defaults
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

@app.route("/diverg")
def diverging():
    global signals, CTRL_AUTH
    if not check_auth(request.args.get("auth"), CTRL_AUTH):
        return ERROR
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    stgt = request.args.get("stat")
    return divergcall(sname, stgt)

@app.route("/signalset")
def signalset():
    global signals, originals, manuals, CTRL_AUTH
    if not check_auth(request.args.get("auth"), CTRL_AUTH):
        return ERROR
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    sstat = request.args.get("stat")
    signals[sname][2] = sstat
    originals[sname] = sstat
    if sstat not in DANGEROUS:
        manuals[sname] = sstat
    #update_signal(sname)
    return sstat

def zugcall(sname, state, zugid):
    global signals, warninfo, red_at_exit, TRAIN_AUTH, WARNING, PREWARNING
    if state == "0":
        if signals[sname][2] == RED:
            warninfo += "<p style=\"color: red;\">[Alert] Train " + zugid + " passing Danger signal</p>\n"
        if not with_train[sname]:
            originals[sname] = signals[sname][2]
        signals[sname][2] = RED
        with_train[sname] = True
        zugin[sname] = zugid
        if sname in prev:
            ps = prev[sname]
            if not with_train[ps]:
                originals[ps] = signals[ps][2]
            if translate(signals[ps][2]) > translate(WARNING):
                signals[ps][2] = WARNING
            with_train[ps] = True
            if ps in prev:
                pps = prev[ps]
                if not with_train[pps]:
                    originals[pps] = signals[pps][2]
                with_train[pps] = True
                if translate(signals[pps][2]) > translate(PREWARNING):
                    signals[pps][2] = PREWARNING
        return RED
    elif state == "1":
        flag = True
        if zugin[sname] != zugid:
            warninfo += "<p style=\"color: orange;\">[Warning] Train " + zugid + " not entering " + sname + ", but exiting. It should have been '" + str(zugin[sname]) + "'.</p>\n"
            flag = False
        if flag and (sname in originals) and (sname not in red_at_exit):
            signals[sname][2] = originals[sname]
        with_train[sname] = False
        if sname in prev:
            ps = prev[sname]
            with_train[ps] = False
            if flag and (ps in originals):
                signals[ps][2] = originals[ps]
            if ps in prev:
                pps = prev[ps]
                with_train[pps] = False
                if flag and (pps in originals):
                    signals[pps][2] = originals[pps]
        zugin[sname] = ""
        return signals[sname][2]
    else:
        return RED

@app.route("/zug")
def zug():
    global signals, warninfo, red_at_exit, TRAIN_AUTH, WARNING, PREWARNING
    if not check_auth(request.args.get("auth"), TRAIN_AUTH):
        return ERROR
    sname = request.args.get("sid")
    if sname not in signals:
        return RED
    state = request.args.get("type")
    zugid = request.args.get("name")
    # 0 : in, 1 : out
    return zugcall(sname, state, zugid)

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

def red_tackle():
    global signals, red_timer, manuals
    while True:
        try:
            for i in signals:
                if signals[i][2] == REDYELLOW:
                    if (i not in red_timer) or (not red_timer[i][2]):
                        red_timer[i] = [0, RED_AWAIT, True]
                    elif red_timer[i][2]:
                        red_timer[i][1] -= 1
                        #print("Ticking for red-yellow", i, red_timer[i])
                        if red_timer[i][1] <= 0:
                            #print("Ticking ended.")
                            red_timer[i][2] = False
                            if i in manuals:
                                signals[i][2] = manuals[i]
                            else:
                                signals[i][2] = GREEN
                            # Report signal modification here for transition
                elif (i in red_timer) and (red_timer[i][2]):
                    red_timer[i][0] += 1
                    red_timer[i][1] -= 1
                    if red_timer[i][1] <= 0 or red_timer[i][0] >= 10:
                        red_timer[i][2] = False
            for i in avoid_state:
                if avoid_state[i] > 0:
                    avoid_state[i] -= 1
        except Exception as e:
            print(e)
        time.sleep(1)

TS_DENSITY = 500

@app.route("/trainview")
def trainsview():
    global trains, translation, zeitplan
    try:
        if "pax" in request.args:
            tdata = []
            for i in trains:
                einfo = '<span style="font-weight: 700;">Unknown</span>'
                try:
                    if trains[i][1] == "" or trains[i][4] == "":
                        tj = ([], (10**8))
                        zeitplan[i] = datetime.datetime.now()
                    else:
                        tj = train_dijkstra(trains[i][4], trains[i][1], True)
                    if (request.args.get("pax") == "open") or (request.args.get("pax") in tj[0]):
                        try:
                            etd = datetime.timedelta(hours=(tj[1] / 1000) / (0.75 * trains[i][2]))
                            eta = datetime.datetime.now() + etd
                            einfo = "On Schuedule"
                            if i not in zeitplan:
                                zeitplan[i] = eta
                            elif (eta - zeitplan[i]) > datetime.timedelta(hours=1):
                                rmin = int((eta - zeitplan[i]).total_seconds() / 60)
                                einfo = '<span style="color: red; font-weight: 700;">Delayed for {} hr {} min</span>'.format(str(rmin//60),str(rmin%60))
                            elif (eta - zeitplan[i]) > datetime.timedelta(minutes=5):
                                einfo = '<span style="color: orange; font-weight: 700;">Delayed for {} min</span>'.format(str(int((eta - zeitplan[i]).total_seconds() / 60)))
                        except Exception as e:
                            print("Error in evaluation of Zeitplan",str(e))
                        tdata.append([i, (translation[trains[i][1]] if trains[i][1] in translation else "--"), (zeitplan[i].strftime("%H:%M")), einfo])
                except Exception as e:
                    print("Error in passenger view",str(e))
            return render_template("paxinner.html", tdata=tdata)
        else:
            return render_template("trainview.html", trains=trains, round=round)
    except RuntimeError as re:
        return "Page is being updated, please wait."
        print("Runtime Error",str(re))

@app.route("/staffview")
def staffview():
    return render_template("staffview.html")

@app.route("/paxview")
def paxview():
    return render_template("paxview.html")

@app.route("/trainop")
def trainop():
    global trains, TRAIN_AUTH, CTRL_AUTH, deact_cnt
    # TODO: Not implemented now
    mode = request.args.get("mode")
    if mode == "update":
        if not check_auth(request.args.get("auth"), CTRL_AUTH):
            return "Operation not permitted", 400
        name = request.args.get("name")
        von = request.args.get("von")
        nach = request.args.get("nach")
        v = request.args.get("spd")
        divg = "0"
        if "autodv" in request.args:
            divg = request.args.get("autodv")
        if name not in trains:
            if von not in signals:
                return "Bad Request", 400
            trains[name] = [von, nach, int(v), 0, von, 0, True, divg.strip() == "1"]
        else:
            trains[name][0] = von
            trains[name][1] = nach
            trains[name][2] = int(v)
            trains[name][7] = divg.strip() == "1"
        return "OK"
    elif mode == "submit":
        if not check_auth(request.args.get("auth"), TRAIN_AUTH):
            return "Operation not permitted", 400
        name = request.args.get("name").replace("_", " ")
        name = name.replace("^", "_")
        v = request.args.get("spd")
        cv = request.args.get("vist")
        loc = request.args.get("sname")
        dev = request.args.get("dev")
        if name not in trains:
            trains[name] = ["", "", int(v), int(cv), loc, int(dev), False, False]
        else:
            trains[name][2] = int(v)
            trains[name][3] = int(cv)
            trains[name][4] = loc
            trains[name][5] = int(dev)
        deact_cnt[name] = 0
        return "OK"
    return "Invalid operation", 500

# Return potential track, O(n^2)
def train_dijkstra(von, nach, pass_red=False, max_len=(10**14)):
    global signals, ZOOM
    #print("Execute dijkstra",von,nach)
    dis = {von:0}
    dvon = {von:""}
    vis = set()
    for i in range(len(signals)):
        cmin = max_len
        cmname = ""
        for j in dis:
            if (signals[j][2] != PROHIBIT) and (pass_red or (signals[j][2] != RED)) and (j not in vis) and (dis[j] < cmin):
                cmin = dis[j]
                cmname = j
        if cmname == "":
            break
        vis.add(cmname)
        cmin = cmin + length(cmname) * ZOOM
        cid = 0
        for j in signals[cmname][3]:
            cext = 0
            if cid != defaults[cmname]:
                cext = length(cmname) * ZOOM
            if (j not in dis) or ((cmin + cext) < dis[j]):
                dis[j] = cmin + cext
                dvon[j] = cmname
            cid += 1
    if nach not in dis:
        print("TDJ: No route from",von,"to",nach)
        return ([], max_len)
    track = [nach]
    cur = nach
    while cur != von:
        track.append(dvon[cur])
        cur = dvon[cur]
    return (track[::-1], dis[nach])

TMAX = 15
tlastcall = {}

def try_diverg(i, pres):
    global zugin, trains, signals, originals
    flag = False
    if zugin[pres] in trains:
        if trains[zugin[pres]][2] > trains[i][2]:
            #print("Attempting to configure diverging track")
            flag = True
            for j in signals[trains[i][4]][3]:
                if ("_park" in j) and (zugin[j] not in trains):
                    divergcall(trains[i][4], j)
                    originals[j] = signals[j][2]
                    signals[j][2] = "4"
                    try:
                        ziel = signals[j][3][signals[j][4]]
                        originals[ziel] = signals[ziel][2]
                        signals[ziel][2] = "-"
                        red_timer[ziel][1] = 120
                    except Exception as e:
                        print("Error in diverging",str(e))
                    print("Configured by using",j)
                    break
    return flag

total_delay = 0

def tsimu():
    global trains, ZOOM, zeitplan, deact_cnt, warninfo, tlastcall, total_delay
    termcnt = 0
    idle = 0
    lastcall = time.time()
    while True:
        # Generation
        print("Tick train simulator,",termcnt,"train(s) has ever arrived","| Last idle:",idle,"| Total delay:",int(total_delay))
        idle = 0
        ct = time.time()
        if (random.randint(1, 1000) <= TS_DENSITY) and (len(trains) < TMAX):
            mode = random.choice(["IC", "ICE", "RE", "G", "D", "Z", "T", "K"])
            vsoll = 120
            if mode in ["ICE", "G", "D"]:
                vsoll = 240
            von = ""
            while (von.strip() == "") or ((von in zugin) and (zugin[von].strip() != "")):
                von = random.choice(red_at_exit)
            # Maybe use ent???
            nach = random.choice(red_at_exit)
            sid = random.randint(1, 1000)
            zname = mode + " " + str(sid)
            if translate(signals[von][2]) <= 0:
                signals[von][2] = "-"
            zugin[von] = zname
            trains[zname] = [von, nach, vsoll, 0, von, 0, True, True]
            zugcall(von, "0", zname)
            rlen = train_dijkstra(von, nach, True)[1]
            zeitplan[zname] = datetime.datetime.now() + datetime.timedelta(hours=((rlen / 1000) / (0.75 * vsoll)))

        # Normal operation for all trains
        plastcall = time.time()
        try:
            for i in trains:
                try:
                    if i not in tlastcall:
                        tlastcall[i] = time.time()
                    vziel = 0
                    zaccel = 0
                    zdis = 0
                    future = ""
                    try:
                        future = signals[trains[i][4]][3][signals[trains[i][4]][4]]
                        #vziel = min(translate(signals[future][2]), trains[i][2])
                        zaccel, vziel, zdis = sdeval(sdscan(trains[i][4],-trains[i][5],12000),trains[i][3],trains[i][2])
                        #print("Train",i,"acc=",zaccel,"vziel=",vziel)
                    except Exception as e:
                        print("Train processor error", str(e))
                        continue
                    if trains[i][6]:
                        #print("Train",i,":",vziel,zaccel,zdis)
                        if zaccel < -0.5:
                            trains[i][3] += (zaccel * 3.6 * (time.time() - tlastcall[i])) + (random.randint(-5, 5) / 10)
                        elif zaccel > -0.1:
                            trains[i][3] += random.randint(30, 40) / 10
                        else:
                            trains[i][3] += random.randint(-5, 5) / 10
                        if (vziel <= 10) and (zdis < 400):
                            if zdis > 50:
                                if trains[i][3] < 30:
                                    trains[i][3] += random.randint(20, 30) / 10
                                elif trains[i][3] > 40:
                                    trains[i][3] -= random.randint(30, 40) / 10
                            else:
                                trains[i][3] -= random.randint(50, 60) / 10
                        if trains[i][3] < 0:
                            trains[i][3] = 0
                        #print("Updating train",i,"by",(trains[i][3] / 3.6),"*",(time.time() - tlastcall[i]))
                        trains[i][5] += (trains[i][3] / 3.6) * (time.time() - tlastcall[i])
                        tlastcall[i] = time.time()
                        clen = length(trains[i][4]) * ZOOM
                        done = False
                        while trains[i][5] >= clen and (future in signals):
                            zugcall(trains[i][4], "1", i)
                            trains[i][5] -= clen
                            trains[i][4] = future
                            if trains[i][4] == trains[i][1]:
                                tlastcall.pop(i)
                                trains.pop(i)
                                done = True
                                cdelay = 0
                                if i in zeitplan:
                                    if datetime.datetime.now() > zeitplan[i]:
                                        cdelay = (datetime.datetime.now() - zeitplan[i]).total_seconds() / 60
                                total_delay += cdelay
                                print("End of train career",i,"with",cdelay,"min delay")
                                termcnt += 1
                                break
                            # TODO: CALL OF ENTER HERE IS INCORRECT ?
                            zugcall(future, "0", i)
                            future = signals[future][3][signals[future][4]]
                            clen = length(trains[i][4]) * ZOOM
                        if done:
                            continue
                    else:
                        if i not in deact_cnt:
                            deact_cnt[i] = 1
                        else:
                            deact_cnt[i] = deact_cnt[i] + 1
                            if deact_cnt[i] > 60:
                                if trains[i][4] in signals:
                                    zugcall(trains[i][4], "1", i)
                                warninfo += "<p>[Info] Train {} lost contact at {}</p>".format(i, trains[i][4])
                                tlastcall.pop(i)
                                trains.pop(i)
                                continue
                    if trains[i][7] and (trains[i][1] in signals) and (trains[i][4] in signals):
                        flag = False
                        if i in avoid_state:
                            flag = (avoid_state[i] > 0)
                        if trains[i][4] in prev:
                            pres = prev[trains[i][4]]
                            # TODO: Pres-pres also work
                            flag = try_diverg(i, pres)
                            if pres in prev:
                                flag = flag or try_diverg(i, prev[pres])
                            if flag:
                                avoid_state[i] = 60
                        if flag:
                            print("Train",i,"is trying to avoid a train")
                        route = []
                        if not flag:
                            route = train_dijkstra(trains[i][4], trains[i][1], True)[0]
                        #print("Attempt for diverg",i,"path",route[:3])
                        #print("Process auto diverging",i,"with","actual",signals[route[1]][3][signals[route[1]][4]],"ideal",route[2])
                        if (len(route) > 1) and (not flag):
                            if (signals[route[0]][3][signals[route[0]][4]] != route[1]):
                                divergcall(route[0], route[1])
                            if (len(route) > 2) and (signals[route[1]][3][signals[route[1]][4]] != route[2]):
                                originals[route[1]] = signals[route[1]][2]
                                signals[route[1]][2] = "0"
                                # Report signal mod !!!
                                #print(i,":Checking diverging condition: present next:",signals[route[1]][3][signals[route[1]][4]],"prev:",route[0],"hope:",route[2])
                                if (signals[route[1]][3][signals[route[1]][4]] == route[0]) or (not ((route[1] in zugin) and (zugin[route[1]] != "") and (zugin[route[1]] != i))):
                                    try:
                                        #signals[route[1]][3][signals[route[1]][4]] = signals[route[1]][3].index(route[2])
                                        signals[route[1]][2] = originals[route[1]]
                                        divergcall(route[1], route[2])
                                        # Report signal mod !!!
                                    except Exception as e:
                                        print("Unable to configure diverging track", str(e))
                            elif (signals[route[1]][2] in [RED, REDYELLOW]) and ((route[1] not in zugin) or (zugin[route[1]] == "") or (zugin[route[1]] == i) or (zugin[route[1]] not in trains)):
                                signals[route[1]][2] = "-"
                                if signals[route[1]][2] == RED and zugin[route[1]] == i:
                                    red_timer[route[1]] = [0, 240, True]
                                # Report signal mod !!!
                except Exception as e:
                    print("Error",str(e))
        except Exception as e:
            print("Error",str(e))
        lastcall = plastcall
        while time.time() < (ct+1):
            idle += 1
            time.sleep(0.05)

if __name__ == '__main__':
    for i in signals:
        if i not in addinfos:
            #print("Addinfo assist",i)
            addinfos[i] = []
        with_train[i] = False
    t = threading.Thread(target=ar)
    t.start()
    tr = threading.Thread(target=red_tackle)
    tr.start()
    ts = threading.Thread(target=tsimu)
    ts.start()
    print("Graphics start")
    for i in signals:
        scan_signal(i)
        break
    turtle.ontimer(imgupd, 1000)
    turtle.mainloop()
