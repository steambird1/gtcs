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
import os
import sys
import signal as sigs
import heapq

logf = open("main.log", "a")
DEBUGOUT = False

if not DEBUGOUT:
    sys.stderr = open("err.log", "a")

def print(*kxargs,end='\n',sep=' '):
    kargs = [str(i) for i in kxargs]
    info = sep.join(kargs)+end
    if DEBUGOUT:
        sys.stdout.write(info)
    logf.write(time.ctime() + " " + info)

app = Flask("FountaineMTR")

PROHIBIT = "x"
RED = "0"
REDYELLOW = "-"
GREEN = "."
WARNING = "/"
PREWARNING = "|"
ERROR = "?"

DANGEROUS = ["0", "-", "x", "?"]
STOPPING = ["0", "x", "?", "1", "2", "3", "4"]

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
    
def name_process(x):
    return x.replace("_", " ").replace("^", "_")

# KLine graph
signals = {}
addinfos = {}

def nextof(signal_name):
    global signals
    return signals[signal_name][3][signals[signal_name][4]]

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
halt_clock = {}

train_routes = {}

# When a train is between two trains, its priority is lowered
low_priority = {}
pass_name = {}

def getmd5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def length(i):
    return ((signals[i][0][0]-signals[i][1][0])**2 + (signals[i][0][1]-signals[i][1][1])**2)**0.5

AUTH_FREE = False
TRAIN_AUTH = [getmd5("jeangunnhildr"), getmd5("_~_amber~_~")]
CTRL_AUTH = [getmd5("no_klee_here_!")]
BEFEHL_AUTH = [getmd5("barbatos'_wish^)")]
# Replace this to something else !!!
KERNEL_AUTH = [getmd5("I_guess_you_can_hear:),right?!")]

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
        #if name+str(sids[name]-1) in signals:
        #    clst = [name+str(sids[name]-1)]
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

def arrange_opposite(through,opposite):
    global signals
    oid = sids[opposite] + 1
    for i in range(1, sids[through]+1):
        tname = through + str(i)
        oid -= 1
        oname = opposite + str(oid)
        if (tname in signals) and (oname in signals):
            signals[tname][3].append(oname)
            signals[oname][3].append(tname)

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

_d1 = ["M_upt_lyg", "M_dnt_lyg", "M_lyg_gleis3_ent", "M_lyg_gleis3_ext", "M_lyg_gleis4_ent", "M_lyg_gleis4_ext"]
_dpk = ["M_up_lyg_park1", "M_up_lyg_park2", "M_up_lyg_park3", "M_dn_lyg_park1", "M_dn_lyg_park2", "M_dn_lyg_park3"]

for i in _d1:
    signals[i][3] += _dpk
for i in _dpk:
    signals[i][3] += _d1

signals["M_up2"][3].append("M_upt_lyg")
signals["M_dn79"][3].append("M_dnt_lyg")

arrange_opposite("M_up", "M_dn")

# Snow mountain line
draw_line("MS_up", 130,225,130,220,-5)
addstation("MS_up", "Mondstadt",0,-2,0,-3, "MS_dn", "Mondstadt (Suburb)")
draw_line("MS_up", 130,220,130,20,-5)
addstation("MS_up", "Dragonspine",0,-2,0,-3, "MS_dn", "Dragonspine")
draw_line("MS_up", 130,20,-10,20,-5)
draw_line("MS_up", -10,20,-10,-135,-5)
addstation("MS_up", "my", 0,-2,0,-3, "MS_dn", "Mingyun")
draw_line("MS_up", -15,-140,-15,-195,-5)

signals[getlatest("MS_up")][3].append("M_dn_lyg_ent")
signals[getlatest("MS_up")][3].append("M_up_lyg_ent")
signals["M_up_lyg_ext"][3].append(getlatest("MS_up"))
signals["M_dn_lyg_ext"][3].append("MS_dn1")

draw_line("MS_dn", -20,-195,-20,-140,5)
# Special.
signals["MS_dn1"].append("M_dn_lyg_ent")
addstation("MS_dn", "my", 0,2,0,3, "MS_up")
draw_line("MS_dn", -20,-135,-20,20,5)
draw_line("MS_dn", -20,20,120,20,5)
addstation("MS_dn", "Dragonspine",0,2,0,3, "MS_up")
draw_line("MS_dn", 120,20,120,220,5)
addstation("MS_dn", "Mondstadt", 0,2,0,3, "MS_up")

signals["M_up_Mondstadt_ext"][3].append("MS_up_Mondstadt_ent")
signals["MS_up_Mondstadt_ent"][3].append("M_up_Mondstadt_ext")
signals["MS_dn_Mondstadt_ext"][3].append("M_dn_Mondstadt_ent")
signals["M_dn_Mondstadt_ent"][3].append("MS_dn_Mondstadt_ext")

arrange_opposite("MS_up", "MS_dn")

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

arrange_opposite("V_up", "V_dn")

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

arrange_opposite("S_up", "S_dn")

# New Inazuma Map (Bridge has approx. 90 km/h speed limit)

signals["M_dn_lyg_ext"][3].append("I_up1")

draw_line("I_up",5,-200,300,-200,5)
draw_line("I_up",300,-200,300,200,5)
addstation("I_up", "Inazuma", 0, 2, 0, 3, "I_dn", "Inazuma")
draw_line("I_up",305,205,305,155,5)
addstation("I_up", "Watatsumi", 0, -2, 0, -3, "I_dn")
draw_line("I_dn",305,160,305,155,5)
addstation("I_dn", "Watatsumi", 0, 2, 0, 3, "I_up", "Watatsumi")
draw_line("I_dn",305,155,305,205,5)
addstation("I_dn", "Inazuma", 0, -2, 0, -3, "I_up")
draw_line("I_dn",300,200,300,-200,5)
draw_line("I_dn",300,-200,5,-200,5)

signals["I_up1"][3].append("M_dn_lyg_ext")
signals[getlatest("I_dn")][3].append("M_lyg_gleis4_ent")

arrange_opposite("I_up", "I_dn")

def generate_for(name,c1=2,c2=8,mnspd=10,mxspd=20):
    global sids, addinfos, ZOOM
    for i in range(1, sids[name]):
        cdis = 0
        sname = name + str(i)
        if sname not in addinfos:
            addinfos[sname] = []
        lz = int(length(sname)*ZOOM)
        while cdis <= lz:
            cst = randz(0, 500)
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
generate_for("MS_up",12,30,6,15)
generate_for("MS_dn",12,30,6,15)

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

arrange_opposite("F_up", "F_dn")

# Fountaine
signals["F_up_Fountaine_ext"][3].append("FC_up_Fountaine_ent")
draw_line("FC_up",-805,605,-810,605,5)
addstation("FC_up","Fountaine",-2,0,-3,0,"FC_dn", "Fountaine (Subway)")
draw_line("FC_up",-810,605,-810,545,5)
addstation("FC_up","Romantime",0,-2,0,-3,"FC_dn","Romaritime")
draw_line("FC_dn",-810,540,-810,545,5)
addstation("FC_dn","Romantime",0,2,0,3,"FC_up")
draw_line("FC_dn",-810,545,-810,605,5)
addstation("FC_dn","Fountaine",0,2,0,3,"FC_up")
signals["FC_dn_Fountaine_ext"][3].append("F_dn_Fountaine_ent")
for proc in ["FC_up", "FC_dn"]:
    for it in range(1, sids[proc]):
        i = proc + str(it)
        if i not in addinfos:
            addinfos[i] = []
        addinfos[i].append([0, "La 0 80"])
        for j in range(1000, int(length(i)*ZOOM), 1000):
            addinfos[i].append([j, "S {}_{}m .".format(i, str(j))])

arrange_opposite("FC_up", "FC_dn")
#for i in range(10,150,10):
#    signals["F_up"+str(i)][3].append("F_dn"+str(sids["F_dn"]-i))
#    signals["F_dn"+str(i)][3].append("F_up"+str(sids["F_up"]-i))


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

def warnprint(*kxargs,end='\n',sep=' '):
    global warninfo
    info = sep.join(kxargs)+end
    print("[Generated warning begin]")
    print(info)
    print("[Generated warning end]")
    warninfo += info

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
            if vkmh <= 10:
                adis = min(adis, dis)
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

def update_addata(sname, sdis, stgt):
    for i in range(len(addinfos[sname])):
        if addinfos[sname][i][0] > int(sdis):
            addinfos[sname].insert(i, [int(sdis), stgt])
            break
    else:
        addinfos[sname].append([int(sdis), stgt])

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
            update_addata(sname, sdis, stgt)
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
    #print(zs)
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

exitings = set()

def zugcall(sname, state, zugid):
    global signals, warninfo, red_at_exit, TRAIN_AUTH, WARNING, PREWARNING, trains, RED, GREEN, exitings
    npz = name_process(zugid)
    if state == "0":
        if signals[sname][2] == RED:
            warnprint("<p style=\"color: red;\">" + time.ctime() + " [Alert] Train " + zugid + " passing Danger signal</p>\n")
        if (sname in zugin) and (zugin[sname] != "") and (zugin[sname] != npz):
            warnprint("<p style=\"color: red;\">" + time.ctime() + " [Alert] Train " + zugid + " entering track occupied by " + zugin[sname] + "</p>\n")
        if not with_train[sname]:
            originals[sname] = signals[sname][2]
        trains[npz][4] = sname
        signals[sname][2] = RED
        with_train[sname] = True
        zugin[sname] = npz
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
        if npz in exitings:
            exitings.remove(npz)
        #print(npz," * Called entrance at ",sname)
        return RED
    elif state == "1":
        exitings.add(npz)
        #print(npz," * Called exit at ",sname)
        flag = True
        if (sname in zugin) and ((zugin[sname] != npz)):
            warnprint("<p style=\"color: orange;\">" + time.ctime() + " [Warning] Train " + npz + " not entering " + sname + ", but exiting. It should have been '" + str(zugin[sname]) + "'.</p>\n")
            flag = False
        if flag and (sname not in red_at_exit):
            if (sname in originals) and (originals not in DANGEROUS):
                signals[sname][2] = originals[sname]
            else:
                signals[sname][2] = GREEN
            #print(">> Attempt to configure",sname,"resulted",signals[sname][2])
        if sname in red_at_exit:
            signals[sname][2] = RED
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

def server_restart():
    # Restart all threads, to be implemented.
    return None

external_dcall = {}
ed_setter = {}
zug_warnings = {}

NO_HALT_CLOCK = 200
HALT_CLOCK = 300

@app.route("/msg")
def msg():
    global warninfo, KERNEL_AUTH, termcnt, total_delay, active_issues, red_timer, external_dcall, ed_setter, trains, zug_warnings, halt_controls
    mode = request.args.get("mode")
    if mode == "zeit":
        return time.ctime()
    elif mode == "clr":
        warninfo = ""
        return ""
    elif mode == "reboot":
        try:
            auth = request.args.get("auth")
            if check_auth(auth, KERNEL_AUTH):
                #tthr = threading.Thread(target=server_restart)
                #tthr.start()
                return "Server restart is unavailable for this version"
            else:
                return "Bad password!"
        except Exception as e:
            return str(e)
    elif mode == "stat":
        return "Total arrival: {}<br />Total delay: {}".format(str(termcnt), str(total_delay))
    elif mode == "issues":
        return "<br />".join([active_issues[i][0] + ": " + str(active_issues[i][1]) + ", " + str(active_issues[i][2]) for i in active_issues])
    elif mode == "rt":
        return "<br />".join([str(i) + ": " + str(red_timer[i]) for i in red_timer])
    else:
        dinfo = ""
        for i in trains:
            if (i in halt_controls) and halt_controls[i] > 0:
                if halt_controls[i] > NO_HALT_CLOCK:
                    dinfo += '<p style="color: orange;">[Diverg Note] Train {} has to stop to divert ({})'.format(i, halt_controls[i])
                elif halt_controls[i] > 0:
                    dinfo += '<p>[Diverg Note] Train {} will not stop to divert ({})'.format(i,halt_controls[i])
            if (i in external_dcall) and external_dcall[i] > 0:
                dinfo += '<p style="color: blue;">[Diverg Note] Train {} has to divert to avoid another train ({}, by {})</p>'.format(i, external_dcall[i], (ed_setter[i] if (i in ed_setter) else "???"))
            elif (i in avoid_state) and avoid_state[i] > 0:
                dinfo += '<p style="color: green;">[Diverg Note] Train {} has to park to avoid another train ({}, by {})</p>'.format(
                    i, avoid_state[i], (ed_setter[i] if (i in ed_setter) else "???"))

        for i in zug_warnings:
            if i not in trains:
                zug_warnings.pop(i)
                continue
            dinfo += '<p style="color: orange;">[Train Note] ({}) {}</p>'.format(i, zug_warnings[i])
        return dinfo + ("<hr />" if len(dinfo) > 0 else "") + warninfo

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

TS_DENSITY = 50

@app.route("/trainview")
def trainsview():
    global trains, translation, zeitplan, SCHED_TRAINS
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
                        tj = train_dijkstra(trains[i][4], trains[i][1], True, optimizer=i)
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
                        idisp = i
                        if i in SCHED_TRAINS:
                            idisp = "<strong>" + i + "</strong>"
                        tdata.append([idisp, (translation[trains[i][1]] if trains[i][1] in translation else "--"), (zeitplan[i].strftime("%H:%M")), einfo])
                except Exception as e:
                    print("Error in passenger view",str(e))
                #tdata.append([i, (translation[trains[i][1]] if trains[i][1] in translation else "--"), (zeitplan[i].strftime("%H:%M")), einfo])
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
        name = name_process(request.args.get("name"))
        v = request.args.get("spd")
        cv = request.args.get("vist")
        loc = request.args.get("sname")
        dev = request.args.get("dev")
        if name not in trains:
            trains[name] = ["", "", int(v), int(cv), loc, int(dev), False, False]
        else:
            trains[name][2] = int(v)
            trains[name][3] = int(cv)
            #trains[name][4] = loc
            trains[name][5] = int(dev)
        deact_cnt[name] = 0
        return "OK"
    return "Invalid operation", 500

class HeapData():
    def __init__(self, ident, disval):
        self.ident = ident
        self.disval = disval
    def __lt__(self, other):
        return self.disval < other.disval

# Return potential track, O(n^2)
def train_dijkstra_int(von, nach, pass_red=False, max_len=(10**14), prohibits=[]):
    global signals, ZOOM
    #print("Execute dijkstra",von,nach)
    dis = {von:0}
    dvon = {von:""}
    vis = set()
    rheap = []
    heapq.heappush(rheap, HeapData(von, 0))
    while len(rheap) > 0:
        cmin = max_len
        cmname = ""
        '''
        for j in dis:
            if (signals[j][2] != PROHIBIT) and (pass_red or (signals[j][2] != RED)) and (j not in vis) and (dis[j] < cmin):
                cmin = dis[j]
                cmname = j
        '''
        ht = heapq.heappop(rheap)
        cmin = ht.disval
        cmname = ht.ident
        if cmname in dis:
            if cmin > dis[cmname]:
                continue
        if cmname == "":
            break
        vis.add(cmname)
        cmin = cmin + length(cmname) * ZOOM
        cid = 0
        for j in signals[cmname][3]:
            cext = 0
            if cid != defaults[cmname]:
                cext = length(cmname) * ZOOM
            if not pass_red:
                if signals[j][2] in DANGEROUS:
                    continue
            if signals[j][2] == PROHIBIT:
                continue
            if j in prohibits:
                continue
            if (j not in dis) or ((cmin + cext) < dis[j]):
                dis[j] = cmin + cext
                dvon[j] = cmname
                heapq.heappush(rheap, HeapData(j, cmin + cext))
            cid += 1
    if nach not in dis:
        #print("TDJ Failure: No route from",von,"to",nach)
        return ([], max_len)
    track = [nach]
    cur = nach
    while cur != von:
        track.append(dvon[cur])
        cur = dvon[cur]
    return (track[::-1], dis[nach])

# REMOVE OPTIMIZER!!!!
def train_dijkstra(von, nach, pass_red=False, max_len=(10**14), optimizer=""):
    return train_dijkstra_int(von, nach, pass_red, max_len)

TMAX = 10
tlastcall = {}

def has_priority(i, owner):
    global zugin, trains, low_priority, pass_name
    owner_spd = trains[owner][2]
    if i == owner:
        return True
    if low_priority[owner] >= 2:
        if owner in pass_name:
            owner = pass_name[owner]
            owner_spd = trains[owner][2]
        else:
            owner_spd = -1
    if (low_priority[i] >= 2) or (owner_spd > trains[i][2]) or (owner_spd == trains[i][2] and owner > i):
        return False
    else:
        return True

# Returning 0 - No diverging is needed
# Returning 1 - ready for diverging
# Returning 2 - performing diverging
def try_diverg(i, pres, forced=False):
    global zugin, trains, signals, originals, ed_setter, external_dcall
    flag = False
    cond = (zugin[pres] in trains) and (not has_priority(i, zugin[pres]))
    #if cond:
    #    print("Detected blocked in",i)
    if "_park" in trains[i][4]:
        return 0
    auxinfo = ""
    if external_dcall[i] <= 0:
        if cond:
            ed_setter[i] = auxinfo + "; from " + zugin[pres]
        else:
            ed_setter[i] = auxinfo + "; holding"
    if forced or cond:
        #print("Attempting to configure diverging track")
        if not cond:
            return 1
        for j in signals[trains[i][4]][3]:
            if ("_park" in j) and (zugin[j] not in trains):
                divergcall(trains[i][4], j)
                originals[j] = signals[j][2]
                signals[j][2] = "4"
                try:
                    ziel = signals[j][3][signals[j][4]]
                    originals[ziel] = signals[ziel][2]
                    signals[ziel][2] = "-"
                    red_timer[ziel][1] = 240
                except Exception as e:
                    print("Error in diverging",str(e))
                #print("Configured by using",j)
                return 2
                break
    return 1 if flag else 0

total_delay = 0
termcnt = 0

_errhd1 = None
waiting_gen = []
exited_trains = set()

def generate_new_train(mode=None, von=None, nach=None, sid=None):
    global red_at_exit, trains, zeitplan, _errhd1, exited_trains
    try:
        if mode is None:
            mode = random.choice(["IC", "ICE", "RE", "G", "D", "Z", "T", "K"])
        vsoll = 120
        if mode in ["ICE", "G", "D"]:
            vsoll = 240
        if von is None:
            von = ""
            while (von.strip() == "") or ((von in zugin) and (zugin[von].strip() != "")):
                von = random.choice(red_at_exit)
        elif (von in zugin) and (zugin[von].strip() != ""):
            return False
        # Maybe use ent???
        if nach is None:
            nach = random.choice(red_at_exit)
        if sid is None:
            sid = random.randint(4000, 7000)
        zname = mode + " " + str(sid)
        if zname in exited_trains:
            exited_trains.remove(zname)
        if translate(signals[von][2]) <= 0:
            signals[von][2] = "-"
        zugin[von] = zname
        trains[zname] = [von, nach, vsoll, 0, von, 0, True, True]
        zugcall(von, "0", zname)
        rlen = train_dijkstra(von, nach, True, optimizer=zname)[1]
        zeitplan[zname] = datetime.datetime.now() + datetime.timedelta(hours=((rlen / 1000) / (0.75 * vsoll)))
        return True
    except Exception as e:
        print("ERROR in creating trains!!!",str(e))
        _errhd1 = e
        return False

# Thanks to Deepseek, but there are too fewer trains.
# CONSIDER ADDERING OPPOSITE
RAW_SCHED_TRAINS = {
    "G1": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "05:00"],
    "G3": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "06:00"],
    "G5": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "07:00"],
    "G7": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "08:00"],
    "G9": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "09:00"],
    "G11": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "11:00"],
    "G13": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "13:00"],
    "G15": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "15:00"],
    "G17": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "17:00"],
    "G19": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "19:00"],
    "D2": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "05:30"],
    "D4": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "06:30"],
    "D6": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "07:30"],
    "D8": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "08:30"],
    "D10": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "09:30"],
    "D12": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "11:30"],
    "D14": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "13:30"],
    "D16": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "15:30"],
    "D18": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "17:30"],
    "D20": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "19:30"],
    "T5001": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "06:00"],
    "T5003": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "10:00"],
    "T5005": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "14:00"],
    "T5007": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "18:00"],
    "T5009": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "20:00"],
    "K5002": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "06:30"],
    "K5004": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "10:30"],
    "K5006": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "14:30"],
    "K5008": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "18:30"],
    "K5010": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "20:30"],
    "ICE8001": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "07:00"],
    "ICE8003": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "08:00"],
    "ICE8005": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "11:00"],
    "ICE8007": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "15:00"],
    "ICE8009": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "19:00"],
    "IC8002": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "07:30"],
    "IC8004": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "08:30"],
    "IC8006": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "11:30"],
    "IC8008": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "15:30"],
    "IC8010": ["M_dn_Mondstadt_ext", "M_up_lyg_ext", "19:30"],
    "G101": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "05:00"],
    "G103": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "11:00"],
    "D102": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "06:00"],
    "D104": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "12:00"],
    "T5101": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "07:00"],
    "T5103": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "13:00"],
    "K5102": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "08:00"],
    "K5104": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "14:00"],
    "ICE8101": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "09:00"],
    "IC8102": ["F_dn_Fountaine_ext", "M_up_lyg_ext", "10:00"],
    "IC201": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "06:00"],
    "IC203": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "07:00"],
    "IC205": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "08:00"],
    "IC207": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "09:00"],
    "IC209": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "10:00"],
    "IC211": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "12:00"],
    "IC213": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "14:00"],
    "IC215": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "16:00"],
    "IC217": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "18:00"],
    "IC219": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "20:00"],
    "RE202": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "06:30"],
    "RE204": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "07:30"],
    "RE206": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "08:30"],
    "RE208": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "09:30"],
    "RE210": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "10:30"],
    "RE212": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "12:30"],
    "RE214": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "14:30"],
    "RE216": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "16:30"],
    "RE218": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "18:30"],
    "RE220": ["I_dn_Inazuma_ext", "I_up_Watatsumi_ext", "20:30"]
}

SCHED_TRAINS = {}

def fetch_train_name_info(tnstr):
    try:
        for i in range(len(tnstr)):
            if tnstr[i].isdigit():
                return (tnstr[:i], int(tnstr[i:]))
    except:
        pass
    return (tnstr, -1)

# Reserved
master_controls = {}
halt_controls = {}

def blocked_by_others(sgns, me):
    global zugin
    if sgns not in zugin:
        return False
    cond = zugin[sgns] != "" and zugin[sgns] != me
    return cond and (zugin[sgns] in trains) and (trains[zugin[sgns]][4] == sgns)

def tsimu():
    global termcnt, trains, ZOOM, zeitplan, deact_cnt, warninfo, tlastcall, total_delay, _errhd1, originals, signals, with_train, waiting_gen, external_dcall, exitings, master_controls, halt_controls, exited_trains, low_priority, pass_name, halt_clock

    idle = 0
    lastcall = time.time()
    while True:
        # Generation
        #print("Tick train simulator,",termcnt,"train(s) has ever arrived","| Last idle:",idle,"| Total delay:",int(total_delay))
        #print("Error handled",_errhd1)
        idle = 0
        ct = time.time()
        try:
            if (random.randint(1, 1000) <= TS_DENSITY) and (len(trains) < TMAX):
                generate_new_train()
            ext_waiting_gen = []
            for i in (list(SCHED_TRAINS) + waiting_gen):
                als = fetch_train_name_info(i)
                if time.strftime("%H:%M") == SCHED_TRAINS[i][2]:
                    if not generate_new_train(als[0], SCHED_TRAINS[i][0], SCHED_TRAINS[i][1], als[1]):
                        ext_waiting_gen.append(i)
            waiting_gen = ext_waiting_gen
        except Exception as e:
            print("Error in routine processor",str(e))
            _errhd1 = e

        # Normal operation for all trains
        plastcall = time.time()
        try:
            for i in halt_clock:
                if i not in trains:
                    halt_clock.pop(i)
                    break
            # Generate low-priority conditions:
            # Reduce memory use:
            low_priority = {}
            pass_name = {}
            for i in trains:
                low_priority[i] = 0
                pass_name[i] = ""
                if i not in halt_clock:
                    halt_clock[i] = 0
            # Currently unused !!
            '''
            for i in trains:
                zus = zugin[nextof(trains[i][4])]
                if zus in trains:
                    low_priority[zugin[nextof(trains[i][4])]] += 1
                    low_priority[i] += 1
            for i in trains:
                zus = zugin[nextof(trains[i][4])]
                if low_priority[i] < 2:
                    if zus in trains:
                        pass_name[zus] = i
                else:
                    if (i in pass_name) and (zus in trains):
                        pass_name[zus] = pass_name[i]
            '''
            for i in trains:
                try:
                    if i not in external_dcall:
                        external_dcall[i] = 0
                    if i not in halt_controls:
                        halt_controls[i] = 0
                    if ("_park" in trains[i][4]) and (external_dcall[i] > 1):
                        if (i not in halt_controls) or ((i in halt_controls) and halt_controls[i] <= 0):
                            halt_controls[i] = HALT_CLOCK
                    #    external_dcall[i] = 0
                    if i in halt_controls:
                        if halt_controls[i] > 0:
                            halt_controls[i] -= 1
                    if external_dcall[i] > 0:
                        #print("EDC state of",i," = ",external_dcall[i])
                        external_dcall[i] -= 1
                    if i not in tlastcall:
                        tlastcall[i] = time.time()
                    vziel = 0
                    zaccel = 0
                    zdis = 0
                    future = ""
                    try:
                        future = nextof(trains[i][4])
                        #vziel = min(translate(signals[future][2]), trains[i][2])
                        zaccel, vziel, zdis = sdeval(sdscan(trains[i][4],-trains[i][5],12000),trains[i][3],trains[i][2])
                        #print("Train",i,"acc=",zaccel,"vziel=",vziel)
                    except Exception as e:
                        print("Train processor error", str(e))
                        continue
                    if trains[i][6]:
                        #print("Train",i,":",vziel,zaccel,zdis)
                        norm_flag = True
                        if halt_controls[i] > NO_HALT_CLOCK and halt_controls[i] < HALT_CLOCK:
                            norm_flag = False
                            trains[i][3] -= random.randint(70, 80) / 10
                        if (vziel <= 10) or (trains[i][3] < 30):
                            if zdis > 150 and ((trains[i][3] < 10) or (zdis < 650)):
                                if trains[i][3] < 30:
                                    trains[i][3] += random.randint(20, 30) / 10
                                elif trains[i][3] > 80:
                                    trains[i][3] -= random.randint(60, 70) * (time.time() - tlastcall[i]) / 10
                                elif trains[i][3] > 40:
                                    trains[i][3] -= random.randint(30, 40) / 10
                                #print(i,"Gliding")
                                norm_flag = False
                            elif vziel <= 20 and zdis < 150:
                                trains[i][3] -= random.randint(90, 100) / 10
                                #print(i,"Halt")
                                norm_flag = False
                        if norm_flag:
                            if zaccel < -0.5:
                                trains[i][3] += (zaccel * 3.6 * (time.time() - tlastcall[i])) + (random.randint(-5, 5) / 10)
                            elif zaccel > -0.1:
                                trains[i][3] += random.randint(30, 40) / 10
                            else:
                                trains[i][3] += random.randint(-5, 5) / 10

                        if trains[i][3] < 0:
                            trains[i][3] = 0
                        #print("Updating train",i,"by",(trains[i][3] / 3.6),"*",(time.time() - tlastcall[i]))
                        trains[i][5] += (trains[i][3] / 3.6) * (time.time() - tlastcall[i])
                        tlastcall[i] = time.time()
                        clen = length(trains[i][4]) * ZOOM
                        done = False
                        exitings.add(i)
                        while trains[i][5] >= clen and (future in signals):
                            old_pos = trains[i][4]
                            trains[i][4] = future
                            zugcall(old_pos, "1", i)
                            #print(i,"< Quit",old_pos,"now signal",signals[old_pos][2],"heading",future,"with",signals[future][2])
                            trains[i][5] -= clen
                            if trains[i][4] == trains[i][1]:
                                exited_trains.add(i)
                                tlastcall.pop(i)
                                trains.pop(i)
                                done = True
                                cdelay = 0
                                if i in zeitplan:
                                    if datetime.datetime.now() > zeitplan[i]:
                                        cdelay = (datetime.datetime.now() - zeitplan[i]).total_seconds() / 60
                                total_delay += cdelay
                                print(i,"< End of train career",i,"with",cdelay,"min delay")
                                termcnt += 1
                                break
                            # TODO: CALL OF ENTER HERE IS INCORRECT ?
                            zugcall(future, "0", i)
                            exitings.add(i)
                            future = signals[future][3][signals[future][4]]
                            clen = length(trains[i][4]) * ZOOM
                        if i in exitings:
                            exitings.remove(i)
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
                                warnprint("<p>" + time.ctime() + " [Info] Train {} lost contact at {}</p>".format(i, trains[i][4]))
                                tlastcall.pop(i)
                                trains.pop(i)
                                continue
                    if trains[i][7] and (trains[i][1] in signals) and (trains[i][4] in signals):
                        if trains[i][3] <= 0.5:
                            halt_clock[i] += 1
                        else:
                            halt_clock[i] = 0
                        if "park" in trains[i][4]:
                            halt_clock[i] = 0
                        if halt_clock[i] > 320 and ("park" not in trains[i][4]):
                            avoid_state[i] = 35
                        flag = 0
                        if external_dcall[i] > 0:
                            avoid_state[i] = 15
                        if (i in avoid_state):
                            flag = 1 if (avoid_state[i] > 0) else 0
                        if trains[i][4] in prev:
                            pres = prev[trains[i][4]]
                            # TODO: Pres-pres also work
                            flag = try_diverg(i, pres, flag > 0)
                            if pres in prev:
                                flag = max(flag, try_diverg(i, prev[pres], flag > 0))
                            if flag >= 2:
                                avoid_state[i] = 60
                        #if flag > 0:
                        #    print("Train",i,"is trying to avoid a train | state: ",flag)
                        if True:
                            route = []
                            if flag < 2:
                                route = train_dijkstra(trains[i][4], trains[i][1], True, optimizer=i)[0]
                            #print("Attempt for diverg",i,"path",route[:3])
                            #print("Process auto diverging",i,"with","actual",signals[route[1]][3][signals[route[1]][4]],"ideal",route[2])
                            if (len(route) > 1) and (not flag):
                                if (external_dcall[i] <= 0) and (nextof(route[0]) != route[1]):
                                    divergcall(route[0], route[1])
                                    #print(i,"Attempt to configure diverging track at current block",route[1])
                                if ((len(route) > 2) and (nextof(route[1]) != route[2])) or blocked_by_others(route[1], i):
                                    if (external_dcall[i] <= 0) and (not blocked_by_others(route[1], i)):
                                        if not with_train[route[1]]:
                                            originals[route[1]] = signals[route[1]][2]
                                        signals[route[1]][2] = "0"
                                    # Consider contact with another train. For the train itself, we should consider diverging, if possible

                                    # Report signal mod !!!
                                    #print(i,":Checking diverging condition: present next:",signals[route[1]][3][signals[route[1]][4]],"prev:",route[0],"hope:",route[2])
                                    #external_dcall[i] = False
                                    if external_dcall[i] <= 5:
                                        # Not triggered by others
                                        external_dcall[i] = 0
                                    take_action = False
                                    take_special_action = False
                                    if not blocked_by_others(route[1], i):
                                        take_action = True
                                    else:
                                        ##...
                                        owner = ""
                                        owner_spd = 0
                                        if (route[1] in zugin) and (zugin[route[1]] in trains) and (trains[zugin[route[1]]][4] == route[1]):
                                            owner = zugin[route[1]]
                                            #print(i, "Trying to diverg due to occupied track (by",
                                            #      (zugin[route[1]] if (route[1] in zugin) else "///"), ")")
                                            # Comparison: G > D, T > K (but as for IC and RE...)
                                            # But what if stuck for sufficiently long time?
                                            if not has_priority(i, owner):
                                                # I should go back ... (only 2 cycles)
                                                external_dcall[i] = 2
                                                if low_priority[i] >= 2:
                                                    ed_setter[i] = i + " (low priority)"
                                                else:
                                                    ed_setter[i] = i + " from " + owner
                                            else:
                                                # The other should go back ... (120 cycles to prevent self-unlocking)
                                                external_dcall[owner] = 120
                                                ed_setter[owner] = i + " to " + owner
                                                #print(i,"Intervention!")
                                                # You can't do this now !!!
                                                #take_action = True
                                                #take_special_action = True
                                        else:
                                            print(i, "Could not find the owner in conflict!")
                                            take_action = True
                                    # Report signal mod !!!
                                    if external_dcall[i] <= 0:
                                        if take_action:
                                            try:
                                                #signals[route[1]][3][signals[route[1]][4]] = signals[route[1]][3].index(route[2])
                                                if len(route) > 2:
                                                    signals[route[1]][2] = originals[route[1]]
                                                    divergcall(route[1], route[2])
                                                    #print(i, "Attempting to configure diverging track at", route[1], "for",
                                                    #      route[2], "train info in:",
                                                    #      (zugin[route[1]] if (route[1] in zugin) else "///"))
                                                    # Report signal mod !!!
                                                elif take_special_action:
                                                    for j in range(len(signals[route[1]][3])):
                                                        csels = signals[route[1]][3][j]
                                                        if csels != route[0]:
                                                            signals[route[1]][2] = originals[route[1]]
                                                            divergcall(route[1], csels)
                                                            print(i,"Attempt to configure final diverging track at", route[1], "for", csels)
                                                            break
                                                    else:
                                                        #print(i,"!!! Unable to configure final exiting diverging")
                                                        zug_warnings[i] = "Unable to configure final exiting"
                                            except Exception as e:
                                                print("Unable to configure diverging track", str(e))
                        else:
                            print("Train",i,"is supposed to avoid another train enroute")
                        # To be tested.
                        future_sgn = nextof(trains[i][4])
                        if (signals[future_sgn][2] in [RED, REDYELLOW]) and (not blocked_by_others(future_sgn, i)):
                            signals[future_sgn][2] = "-"
                            if future_sgn in red_timer:
                                if red_timer[future_sgn][1] > 60:
                                    red_timer[future_sgn][1] = 60
                            if signals[future_sgn][2] == RED and zugin[future_sgn] == i:
                                red_timer[future_sgn] = [0, 240, True]
                except Exception as e:
                    print("Error",str(e))
            for i in exited_trains:
                if i in trains:
                    trains.pop(i)
            exited_trains.clear()
        except Exception as e:
            print("Error",str(e))
            time.sleep(0.2)
        lastcall = plastcall
        while time.time() < (ct+1):
            idle += 1
            time.sleep(0.05)


# of 1000
SPECIAL_PROB = 10
# [type, time remaining, external data]
active_issues = {}

def special_events():
    global signals, originals, active_issues
    while True:
        try:
            spc = random.randint(1, 10000)
            if spc <= SPECIAL_PROB:
                # 1. Blocked roads
                # 2. Hillchurl/Abyssmagi/... (H/A/E/U)
                # 3. Maintenance along
                spid = random.randint(1, 100000)
                spt = random.choice(["B", "M"])
                sgn = random.choice(list(signals))
                sgns = []
                # INSERT ONLY THE DISTANCES!!!
                arb = []
                for i in sdscan(sgn, 400):
                    sdata = i[1].split(" ")
                    if sdata[0] == "S":
                        sgns.append(sdata[1])
                if spt == "B":
                    for j in sgns:
                        if not with_train[j]:
                            originals[j] = signals[j][2]
                        signals[j][2] = PROHIBIT
                    arb = sgns
                elif spt == "M":
                    asp = random.randint(40, 250)
                    dt = random.randint(10, 50)
                    for j in sgns:
                        arb.append([j, dt])
                        update_addata(j, dt, "La 0 " + str(asp))
                        # 180, 1200:
                active_issues[spid] = [spt, random.randint(180, 2500), arb]
                print("Adding issue",spid)
            # Check ending of active issues:
            for i in active_issues:
                if active_issues[i][1] <= 0:
                    # Undo in accordance
                    if active_issues[i][0] == "B":
                        for j in active_issues[i][2]:
                            if j in originals:
                                signals[j][2] = originals[j]
                            else:
                                signals[j][2] = GREEN
                    elif active_issues[i][2] == "M":
                        for j in active_issues[i][2]:
                            # [signal, sdata]
                            for k in range(len(addinfos[active_issues[i][2][j][0]])):
                                if addinfos[active_issues[i][2][j][0]][k][0] == active_issues[i][2][j][1]:
                                    addinfos[active_issues[i][2][j][0]].pop(k)
                                    break
                            else:
                                print("Unable to recover change in",j)
                    active_issues.pop(i)
                    print("Removing issue",i)
                    break
                active_issues[i][1] -= 1
        except Exception as e:
            print("sge error",str(e))
        time.sleep(1)

# NOT TESTED!!!
def schutzs():
    global trains, exitings, originals, low_priority
    while True:
        try:
            for i in trains:
                if i in exitings:
                    #print(i, "> Exiting, so skipped")
                    continue
                if (signals[trains[i][4]][2] not in STOPPING):
                    #print(i, "> Safety configuration for", trains[i][4])
                    if not with_train[trains[i][4]]:
                        originals[trains[i][4]] = signals[trains[i][4]][2]
                    signals[trains[i][4]][2] = "0"
                    with_train[trains[i][4]] = True
                    if zugin[trains[i][4]] != i:
                        zugin[trains[i][4]] = i
            time.sleep(0.5)
        except Exception as e:
            print("Schutz: err:",str(e))
            time.sleep(0.5)

if __name__ == '__main__':
    for i in RAW_SCHED_TRAINS:
        iname = fetch_train_name_info(i)
        SCHED_TRAINS[i] = RAW_SCHED_TRAINS[i]
        SCHED_TRAINS[iname[0] + str(iname[1] + 1)] = [RAW_SCHED_TRAINS[i][1], RAW_SCHED_TRAINS[i][0], RAW_SCHED_TRAINS[i][2]]
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
    tp = threading.Thread(target=special_events)
    tp.start()
    th = threading.Thread(target=schutzs)
    th.start()
    print("Graphics start")
    for i in signals:
        scan_signal(i)
        break
    #turtle.ontimer(imgupd, 1000)
    turtle.mainloop()
