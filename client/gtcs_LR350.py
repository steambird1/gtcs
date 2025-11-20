import turtle
import math
import time
from urllib.request import urlopen
from urllib import request
import threading
import random
import os
import copy
from collections import deque

# Changelog: Geo element (and relevant malfunctions), national bg (incomplete), slope and friction (incomplete)
# auto upgrade/downgrade (incomplete), announcement (incomplete)

# For linux?
SPECIAL_KEY = False
VENTI = True

try:
    from playsound import playsound
except:
    VENTI = False
    print("Unable to load Venti. Running without voice!")

AUTH = "_~_amber~_~"

USERLIM = 350

FONT = ('Arial', 10, 'normal')
LEVEL = 1
SCTR = "http://127.0.0.1:5033/signal"
ZCTR = "http://127.0.0.1:5033/zug"
DCTR = "http://127.0.0.1:5033/zugdist"
BCTR = "http://127.0.0.1:5033/befehl"
LCTR = "http://127.0.0.1:5033/lkjdisp"
ICTR = "http://127.0.0.1:5033/signaldata"
TCTR="http://127.0.0.1:5033/trainop"
RENDER="http://127.0.0.1:6160/"
ZUGNAME = "G_1"
SCHUTZ_SIMU = True
SCHUTZ_PROB = 1
DARK = True
DRANGE = 4000
PASSING_SPD = 40

MYGREEN = ("green2" if DARK else "green")
MYWHITE = ("white" if DARK else "black")
MYBLUE = ("cyan" if DARK else "blue")

# GTCS data collector
nextdist = 0
curspeed = 0
spdlim = 40
lastspdlim = USERLIM
accreq = 0
gtcsinfo = []
sysinfo = []
thrust = 0
eb = False
zugat = ""
power = 0
curlkj = "?"
prereded = False
schutz = False
schutz_info = ""
has_afb = False
passing = False
# TODO: National backgroud element values to be updated
anemo_bg = 0
electro_vbg = 0
electro_abg = 0
geo_bg = 0

current_slope = 0

# TODO: Announcement signals
ANNOUNCEMENT_AT = [2000,1000,500,200]
MONITOR_SPEED_DELTA = [0,30,15,5]
MONITOR_ACCEL = [0.2,0.5,1.6,2]
announcement_got = [False] * len(ANNOUNCEMENT_AT)
announced_name = "?"
announced_sig = "?"

asuber = 0

extcmd = []
lastseg = []
furseg = []
lbdisp = 0
zusatz_lastspdlim = 350

show_name = False

# Whether to pass neutral zone
passdz = False
appdz = False

# Superconduct is not a failure sometimes, depending on what you need.
# Volts High == Charged sometimes
apress = 0
cevolts = 0
ceamps = 0
evolts = 0
eamps = 0
efreq = 50
# Unit: A*h
# Maintained by the same thread.
battery_charge = 50
MAX_BAT_CAPACITY = 200
batvolts = 0
batamps = 0
batregen = False
onbat = False
servolts = 0
# Geo element added, keyword 'geo'
geo_elem = 0
# Respectively use 'P', 'K', 'L' (Shift + letter) to charge.
dendro_mass = 0
dendro_feed = 0
pyro_temp = 0
#servamps = 0

# 'a' or 'e'. 'd' and 'y' should be engaged using Shift + A
cpsrc = "a"
cptype = {"a": "Anemo", "e": "Electro", "p": "Pantograph", "d": "Dendro"}
# 'x' for empty page
syspages = {
    "q": [
        [lambda: cptype[cpsrc], lambda: MYWHITE]
    ],
    "w": [
        [lambda: cptype[cpsrc], lambda: MYWHITE],
        [lambda: ("{} MPa".format(round(apress, 1))),
         lambda: ("red" if (((cpsrc == "a") and (apress < 10)) or apress > 200) else MYGREEN)]
    ],
    "e": [
        [lambda: cptype[cpsrc], lambda: MYWHITE],
        [lambda: ("{} V".format(round(evolts, 1))),
         lambda: ("red" if (((cpsrc == "e") and (evolts < 10)) or evolts > 3000) else MYGREEN)],
        [lambda: ("{} A".format(round(eamps, 1))),
         lambda: ("red" if (((cpsrc == "e") and (eamps < 0.1)) or eamps > 100) else MYGREEN)]
    ],
    "r": [
        [lambda: cptype[cpsrc], lambda: MYWHITE],
        [lambda: ("Neutral Section" if passdz else "Normal"), lambda: ("orange" if passdz else MYWHITE)],
        [lambda: ("{} V".format(round(evolts, 1))),
         lambda: ("red" if (((cpsrc == "e") and (evolts < 10)) or evolts > 3000) else MYGREEN)],
        [lambda: ("{} A".format(round(eamps, 1))),
         lambda: ("red" if (((cpsrc == "e") and (eamps < 0.1)) or eamps > 100) else MYGREEN)]
    ],
    't': [
        [lambda: cptype[cpsrc], lambda: MYWHITE],
        [lambda: "Geo", lambda: MYWHITE],
        [lambda: ("{} u".format(round(geo_elem, 1))),
         lambda: (MYWHITE if (geo_elem < 1.5) else MYGREEN)]
    ],
    'y': [
        [lambda: cptype[cpsrc], lambda: MYWHITE],
        [lambda: "{} kg".format(round(dendro_mass, 1)), lambda: "red" if (cpsrc == "d" and dendro_mass <= 2) else MYWHITE],
        [lambda: "No feed" if (dendro_feed <= 0) else "{} kg/min".format(round(dendro_feed, 1)), lambda: MYWHITE if (dendro_feed <= 0) else MYGREEN],
        [lambda: ("{} K".format(round(pyro_temp, 1))),
         lambda: (MYWHITE if (pyro_temp < 350) else ("red" if (pyro_temp > 1050) else MYGREEN))]
    ],
    "x": []
}
csyspage = "q"


def assign(x, attrib, val):
    x[attrib] = val

# Carriage system. d & dg & y are reserved for Dendro / Pyro system.
# Make sure to copy for each use.
PWRCAR = {
    "weight": 30,
    "a": 2,
    "g": 2,
    "e": 2,
    "p": 2,
    "d": 2,
    "dg": 0.5,
    "y": 2,
    "loco": True,
    "cat": "pwrcar",
    "failures": {
        "was_failure": {},
        "sch_failure": ["fire"],
        "term": {
            "smoke": ["Lavatory Smoke", False, lambda x: False, lambda x: True, lambda x: None, lambda x: None],
            "fire": ["Fire", False, lambda x: False, lambda x: True, lambda x: None, lambda x: None],
            "anemo_fail": ["Anemo Inop", False, lambda x: False, lambda x: ("a" in x) and (x["a"]), lambda x: assign(x, 'a', 0), lambda x: assign(x, 'a', 1)],
            "geo_fail": ["Geo Inop", False, lambda x: False, lambda x: ("g" in x) and (x["g"]), lambda x: assign(x, 'g', 0), lambda x: assign(x, 'g', 1)],
            "electro_fail": ["Electro Inop", False, lambda x: False, lambda x: ("e" in x) and (x["e"]), lambda x: assign(x, 'e', 0), lambda x: assign(x, 'e', 1)],
            "panto_fail": ["Panto Inop", False, lambda x: False, lambda x: ("p" in x) and (x["p"]), lambda x: assign(x, 'p', 0), lambda x: assign(x, 'p', 1)],
            "dendro_fail": ["Dendro Inop", False, lambda x: False, lambda x: ("d" in x) and (x["d"]), lambda x: assign(x, 'd', 0), lambda x: assign(x, 'd', 1)],
            "pyro_fail": ["Pyro Inop", False, lambda x: False, lambda x: ("y" in x) and (x["y"]), lambda x: assign(x, 'y', 0), lambda x: assign(x, 'y', 1)]
        }
    }
}

NORMCAR = {
    "weight": 30,
    "cat": "normcar",
    "failures": {
        "was_failure": {},
        "sch_failure": ["fire"],
        "term": {
            "smoke": ["Lavatory Smoke", False, lambda x: False, lambda x: True, lambda x: None, lambda x: None],
            "fire": ["Fire", False, lambda x: False, lambda x: True, lambda x: None, lambda x: None],
        }
    }
}

# For 120km/h version, there's power car only initially
cars = [
    copy.deepcopy(PWRCAR)
] + [
    copy.deepcopy(NORMCAR) for i in range(7)   
]

# "_" is for the default
cardisp = {
    "_": {
        "shape": "normal",
        "panto": lambda x: False,
        "disp": []
    },
    "normcar": {
        "shape": "normal",
        "panto": lambda x: False,
        "disp": [
            [lambda x: "Fire" if ("fire" in x["failures"]["term"]) and (x["failures"]["term"]["fire"][1]) else "", lambda x: "red"]
        ]
    },
    "pwrcar": {
        "shape": "pwrcar",
        "panto": lambda x: (x["p"]) if ("p" in x) else 0,
        "disp": [
            [lambda x: (cptype[cpsrc])[:3] if (cpsrc in x) else "", lambda x: (MYGREEN) if ((cpsrc in x) and (x[cpsrc])) else "white"],
            [lambda x: "Fire" if ("fire" in x["failures"]["term"]) and (x["failures"]["term"]["fire"][1]) else "", lambda x: "red"]
        ]
    }
}

# Connection/disconnection of carriages is only allowed under Passing Mode


failures = {
    "thr": ["Thrust No Response", False, lambda: False],
    "brk": ["Brake No Response", False, lambda: False],
    "apwrlo": ["Anemo Quality Low", False, lambda: ((cpsrc == "a") and (apress < 10))],
    "apwrhi": ["Anemo Quality High", False, lambda: apress > 200],
    "epwrlo": ["Electro Volts Low", False, lambda: ((cpsrc == "e") and (evolts < 10))],
    "epwrhi": ["Electro Volts High", False, lambda: evolts > 3000],
    "epwrslo": ["Electro Amps Low", False, lambda: ((cpsrc == "e") and (eamps < 0.1))],
    "epwrshi": ["Electro Amps High", False, lambda: eamps > 100],
    "ovldr": ["Element Overload", False, lambda: False],
    "scond": ["Element Superconduct", False, lambda: False],
    "eblock": ["Crystalize Blocking", False, lambda: False],
    "logerr": ["Recorder Failure", False, lambda: False],
    "panto1": ["Pantograph 1 Failure", False, lambda: False],
    "panto2": ["Pantograph 2 Failure", False, lambda: False],
    "motor1": ["Electro Motor 1", False, lambda: False],
    "motor2": ["Electro Motor 2", False, lambda: False],
    "batlo": ["Electro Battery Low", False, lambda: (battery_charge < 1)],
    "bepwrlo": ["Electro BAT Volts Low", False, lambda: ((batvolts < 1000))],
    "bepwrhi": ["Electro BAT Volts High", False, lambda: batvolts > 3000],
    "bepwrslo": ["Electro BAT Amps Low", False, lambda: ((batamps < 0.1))],
    "bepwrshi": ["Electro BAT Amps High", False, lambda: batamps > 100],
    "depwrlo": ["Electro DC Service Volts Low", False, lambda: ((servolts < 18))],
    "depwrhi": ["Electro DC Service Volts High", False, lambda: servolts > 64],
    "geofail": ["Geo Inoperative", False, lambda: False],
    "denlo": ["Dendro Weight Low", False, lambda: (cpsrc == "d" and dendro_mass < 2)],
    "pyrolo": ["Pyro Temperature Low", False, lambda: (cpsrc == "d" and pyro_temp < 350)],
    "pyrohi": ["Pyro Temperature High", False, lambda: pyro_temp > 1050]
}
# balo also has special events

def car_stat(key):
    global cars
    return sum([i[key] if (key in i) else 0 for i in cars])

def each_panto_amps():
    if cpsrc != "p":
        return 0
    cnt = 2
    if failures["panto1"][1]:
        cnt -= 1
    if failures["panto2"][1]:
        cnt -= 1
    if cnt <= 0:
        return 0
    return (ceamps / cnt) + random.randint(1,20)/10

def each_panto_volts():
    if cpsrc != "p":
        return 0
    return cevolts + random.randint(30,300)/10

was_failure = {}
sch_failure = []

for i in failures:
    was_failure[i] = False
    
def ok_motor_count():
    return (0 if failures["motor1"][1] else 1) + (0 if failures["motor2"][1] else 1)

def maxthr_val():
    global apress, cevolts, ceamps, batvolts, batamps, cpsrc, failures, dendro_mass, pyro_temp
    res = 0
    ok_motor = ok_motor_count()
    if cpsrc == "a":
        res = apress * 1.5
    elif cpsrc == "d":
        # Time matters
        if apress < 60:
            aspd = 2*math.pi
        else:
            aspd = 2*math.pi/(apress/60)
        res = max(0,math.sin(aspd*time.time())*dendro_mass*10 + dendro_mass*(pyro_temp/650)*20)
    else:
        res = ((cevolts + batvolts) * (ceamps + batamps)) / 750
    return res * (ok_motor) * car_stat(cpsrc) / 2

def motor_out():
    global thrust, curspeed
    if ok_motor_count() > 0:
        return power / ok_motor_count()
    else:
        return 0

ps_queue = deque()

def start_sound(name):
    global VENTI, ps_queue
    if VENTI:
        if len(ps_queue) > 0:
            cr = ps_queue.pop()
            ps_queue.append(cr)
            if cr == name:
                return
        ps_queue.append(name)


def sound_thr():
    global VENTI, ps_queue
    cfn = os.path.split(os.path.realpath(__file__))[0]
    if cfn[:-1] not in ["/", "\\"]:
        cfn = cfn + "/"
    cfn = cfn + "audio/"
    while True:
        if len(ps_queue) > 0:
            cur = ps_queue.popleft()
            if VENTI:
                try:
                    playsound(cfn + cur + ".mp3")
                except:
                    pass
        time.sleep(1)


turtle.tracer(False)

turtle2 = turtle.Turtle()
turtle3 = turtle.Turtle()
maxspder = turtle.Turtle()
acreqer = turtle.Turtle()
spdturtle = turtle.Turtle()
thrturtle = turtle.Turtle()
infobar = turtle.Turtle()
spdraw = turtle.Turtle()
limdraw = turtle.Turtle()
befehldisp = turtle.Turtle()
xspdraw = turtle.Turtle()
lkjdraw = turtle.Turtle()
spdhint = turtle.Turtle()
gaspress = turtle.Turtle()
routedisp = turtle.Turtle()
cthrdraw = turtle.Turtle()
amdraw = turtle.Turtle()
t = turtle.Pen()

if DARK:
    turtle.bgcolor('black')
    turtle.pencolor('white')
    turtle2.pencolor('white')
    turtle3.pencolor('white')
    maxspder.pencolor('white')
    acreqer.pencolor('white')
    spdturtle.pencolor('white')
    thrturtle.pencolor('white')
    infobar.pencolor('white')
    spdraw.pencolor('white')
    befehldisp.pencolor('white')
    xspdraw.pencolor('white')
    # lkjdraw.pencolor('white')
    spdhint.pencolor('white')
    gaspress.pencolor('white')
    cthrdraw.pencolor('white')
    amdraw.pencolor('white')

spdturtle.penup()
thrturtle.penup()
infobar.penup()
maxspder.penup()
acreqer.penup()
spdraw.penup()
limdraw.penup()
turtle2.penup()
befehldisp.penup()
xspdraw.penup()
lkjdraw.penup()
spdhint.penup()
gaspress.penup()
routedisp.penup()
cthrdraw.penup()
amdraw.penup()
maxspder.goto(-160, 80)
acreqer.goto(-160, 0)
spdhint.goto(-155, 5)
spdraw.goto(-160, 80)
limdraw.goto(-320, 0)
befehldisp.goto(-160, 220)
xspdraw.goto(-160, 40)
lkjdraw.goto(-200, 200)
gaspress.goto(160, 40)
routedisp.goto(-340, 0)
amdraw.goto(-160, -120)

xspdraw.speed('fastest')
befehldisp.speed('fastest')
spdturtle.speed('fastest')
thrturtle.speed('fastest')
maxspder.speed('fastest')
acreqer.speed('fastest')
spdraw.speed('fastest')
turtle2.speed('fastest')
turtle3.speed('fastest')
lkjdraw.speed('fastest')
spdhint.speed('fastest')
gaspress.speed('fastest')
routedisp.speed('fastest')
cthrdraw.speed('fastest')
amdraw.speed('fastest')
befehldisp.pensize(2)
turtle2.pensize(2)
turtle3.pensize(2)
spdraw.pensize(3)
spdturtle.pensize(3)
thrturtle.pensize(3)
maxspder.pensize(3)
acreqer.pensize(3)
lkjdraw.pensize(2)
spdhint.pensize(3)
cthrdraw.pensize(2)
maxspder.pencolor('orange')
acreqer.pencolor('orange')
spdhint.pencolor(MYBLUE)
routedisp.pencolor(MYBLUE)
# xspdraw.pencolor('purple')

infobar.speed('fastest')

turtle.speed('fastest')
xspdraw.hideturtle()
befehldisp.hideturtle()
turtle.hideturtle()
turtle2.hideturtle()
turtle3.hideturtle()
infobar.hideturtle()
spdturtle.hideturtle()
thrturtle.hideturtle()
maxspder.hideturtle()
spdraw.hideturtle()
lkjdraw.hideturtle()
gaspress.hideturtle()
routedisp.hideturtle()
cthrdraw.hideturtle()
amdraw.hideturtle()

if LEVEL < 2:
    limdraw.hideturtle()
# acreqer.hideturtle()
# turtle.tracer(True, 500)

# 320 positions, 40 each, so here are 8
# [S Level] [P] [D] [S] [1] [2] [E] [M]

turtle.pensize(2)

iustr = [str(USERLIM), "P", "D", "S", "1", "2", "E", "M", "Sifa", "Off"]
tcolor = ["blue", "green", "orange", "red", "green", "green", "blue", "blue", "orange", "blue"]
xcolor = ["white"] * 10
# light = [True]*10
light = [True, False, False, False, False, False, False, False, False, False, False]

ovrd_main_disp = False
ovrd_page = 'a'

# Must be called AFTER main processor
def render_anemo_power():
    global apress, FONT, failures, evolts, eamps, cpsrc, battery_charge, batvolts, batamps, batregen, cevolts, ceamps, cars, cardisp
    amdraw.goto(-160, -120)
    amdraw.clear()
    if ovrd_main_disp:
        if ovrd_page == 'a':
            # -160, -100
            amdraw.goto(-70, -120)
            amdraw.pendown()
            amdraw.goto(-70, -160)
            amdraw.goto(-150, -160)
            amdraw.goto(-150, -120)
            amdraw.goto(-70, -120)
            amdraw.penup()
            amdraw.goto(-110, -135)
            amdraw.write("Anemo M", align='center', font=FONT)
            amdraw.goto(-110, -150)
            amtext = ("{} MPa".format(round(apress, 1)))
            amcolor = ("red" if (((cpsrc == "a") and (apress < 10)) or apress > 200) else MYGREEN)
            amdraw.pencolor(amcolor)
            amdraw.write(amtext, align='center', font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-70, -140)
            amdraw.pendown()
            if cpsrc == "a":
                amdraw.pencolor(MYGREEN)
            amdraw.goto(-40, -140)
            amdraw.pencolor(MYWHITE)
            amdraw.write("Thrust Out", align='left', font=FONT)
            amdraw.penup()
        elif ovrd_page == 'e':
            amdraw.goto(-130, -140)
            amdraw.pencolor(MYWHITE)
            if cpsrc == "p":
                amdraw.pencolor(MYGREEN)
            if failures["panto1"][1]:
                amdraw.pencolor("orange")
            amdraw.write("Panto 1", align='center', font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-130, -155)
            amdraw.write(str(0 if failures["panto1"][1] else round(each_panto_volts(), 1)) + "V", font=FONT)
            amdraw.goto(-130, -170)
            amdraw.write(str(0 if failures["panto1"][1] else round(each_panto_amps(), 1)) + "A", font=FONT)
            amdraw.goto(130, -140)
            if cpsrc == "p":
                amdraw.pencolor(MYGREEN)
            if failures["panto2"][1]:
                amdraw.pencolor("orange")
            amdraw.write("Panto 2", align='center', font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(130, -155)
            amdraw.write(str(0 if failures["panto2"][1] else round(each_panto_volts(), 1)) + "V", font=FONT)
            amdraw.goto(130, -170)
            amdraw.write(str(0 if failures["panto2"][1] else round(each_panto_amps(), 1)) + "A", font=FONT)
            if cpsrc == "p":
                amdraw.pencolor(MYGREEN)
            amdraw.goto(-130, -185)
            amdraw.pendown()
            amdraw.goto(-130, -260)
            amdraw.penup()
            amdraw.goto(130, -185)
            amdraw.pendown()
            amdraw.goto(130, -260)
            amdraw.penup()
            # (-195, -225) areas:
            amdraw.pencolor(MYWHITE)
            exvolts = cevolts
            examps = ceamps
            if cpsrc == "e":
                amdraw.pencolor(MYGREEN)
            else:
                exvolts = 0
                examps = 0
            amdraw.goto(-110, -185)
            amdraw.pendown()
            amdraw.goto(110,-185)
            amdraw.goto(110,-245)
            amdraw.goto(-110,-245)
            amdraw.goto(-110,-185)
            amdraw.penup()
            amdraw.goto(0,-215)
            amdraw.write("Electro", align='center', font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-75,-230)
            if exvolts > 3000 or exvolts < 10:
                amdraw.pencolor("red")
            amdraw.write(str(round(exvolts,1)) + " V", align="left", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(75,-230)
            if examps > 100 or examps < 0.1:
                amdraw.pencolor("red")
            amdraw.write(str(round(examps,1)) + " A", align="right", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-110, -275)
            amdraw.pendown()
            amdraw.goto(110, -275)
            amdraw.goto(110, -320)
            amdraw.goto(-110, -320)
            amdraw.goto(-110, -275)
            amdraw.penup()
            amdraw.goto(-75,-290)
            amdraw.write("Battery", align='left', font=FONT)
            amdraw.goto(75,-290)
            if battery_charge < 1:
                amdraw.pencolor("red")
            amdraw.write(str(round(battery_charge,1)) + " Ah", align="right", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-75,-305)
            if batvolts > 3000 or batvolts < 10:
                amdraw.pencolor("red")
            amdraw.write(str(round(batvolts,1)) + " V", align="left", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(75,-305)
            if batamps > 100 or batamps < 0.1:
                amdraw.pencolor("red")
            amdraw.write(str(round(batamps,1)) + " A", align="right", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-130, -260)
            amdraw.pendown()
            if (evolts * eamps) > 300:
                amdraw.pencolor(MYGREEN)
            else:
                amdraw.pencolor(MYWHITE)
            amdraw.goto(-110, -260)
            amdraw.penup()
            # Service bus
            amdraw.goto(-130, -210)
            amdraw.write("Service Bus", align="right", font=FONT)
            amdraw.goto(-130, -225)
            if servolts < 16 or servolts > 64:
                amdraw.pencolor("red")
            amdraw.write(str(round(servolts, 1)) + " V", align="right", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.penup()
            # Service bus
            amdraw.goto(130, -195)
            amdraw.write("Main Bus", align="left", font=FONT)
            amdraw.goto(130, -210)
            if evolts < 0.1 or evolts > 3000:
                amdraw.pencolor("red")
            amdraw.write(str(round(evolts, 1)) + " V", align="left", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(130, -225)
            if eamps < 0.1 or eamps > 100:
                amdraw.pencolor("red")
            amdraw.write(str(round(eamps, 1)) + " A", align="left", font=FONT)
            amdraw.pencolor(MYWHITE)
            amdraw.goto(-110, -260)
            if batregen:
                amdraw.pencolor(MYBLUE)
            elif (evolts * eamps) > 1500:
                amdraw.pencolor(MYGREEN)
            else:
                amdraw.pencolor(MYWHITE)
            amdraw.pendown()
            amdraw.goto(130, -260)
            amdraw.penup()
            amdraw.goto(-130,-260)
            amdraw.pendown()
            amdraw.goto(-130,-280)
            amdraw.penup()
            amdraw.goto(130,-260)
            amdraw.pendown()
            amdraw.goto(130,-280)
            amdraw.penup()
            m1out = round(motor_out() + random.randint(1,20) / 10,1)
            if failures["motor1"][1]:
                amdraw.pencolor("orange")
                m1out = 0
            amdraw.goto(-150,-290)
            amdraw.write("Motor 1", align='center', font=FONT)
            amdraw.goto(-150,-305)
            amdraw.write(str(round(m1out,1)) + " kW", align='center', font=FONT)
            
            if batregen:
                amdraw.pencolor(MYBLUE)
            elif (evolts * eamps) > 1500:
                amdraw.pencolor(MYGREEN)
            else:
                amdraw.pencolor(MYWHITE)
            m2out = round(motor_out() + random.randint(1,20) / 10,1)
            if failures["motor2"][1]:
                amdraw.pencolor("orange")
                m2out = 0
            amdraw.goto(150,-290)
            amdraw.write("Motor 2", align='center', font=FONT)
            amdraw.goto(150,-305)
            amdraw.write(str(round(m2out,1)) + " kW", align='center', font=FONT)
            amdraw.penup()
            amdraw.pencolor(MYWHITE)
        elif ovrd_page == 'z':
            # Draw train information
            xcoord = -160
            ycoord = -150
            for i in cars:
                amdraw.pencolor(MYWHITE)
                amdraw.penup()
                amdraw.goto(xcoord, ycoord)
                graphtype = "_"
                if "cat" in i:
                    graphtype = i["cat"]
                if cardisp[graphtype]["shape"] == "pwrcar":
                    amdraw.goto(xcoord, ycoord - 20)
                    amdraw.pendown()
                    amdraw.goto(xcoord + 20, ycoord)
                    amdraw.goto(xcoord + 30, ycoord)
                    amdraw.goto(xcoord + 30, ycoord - 40)
                    amdraw.goto(xcoord, ycoord - 40)
                    amdraw.goto(xcoord, ycoord - 20)
                else:
                    amdraw.pendown()
                    amdraw.goto(xcoord + 30, ycoord)
                    amdraw.goto(xcoord + 30, ycoord - 40)
                    amdraw.goto(xcoord, ycoord - 40)
                    amdraw.goto(xcoord, ycoord)
                amdraw.penup()
                if cardisp[graphtype]["panto"](i):
                    amdraw.goto(xcoord + 30, ycoord)
                    # Check pantograph state
                    try:
                        if cpsrc == "p" and i["p"]:
                            # Raised pantograph
                            amdraw.pencolor(MYGREEN)
                            amdraw.pendown()
                            amdraw.goto(xcoord + 30, ycoord + 10)
                            amdraw.goto(xcoord + 20, ycoord + 10)
                            amdraw.goto(xcoord + 40, ycoord + 10)
                            amdraw.penup()
                            amdraw.pencolor(MYWHITE)
                        else:
                            amdraw.pendown()
                            amdraw.goto(xcoord + 30, ycoord + 5)
                            amdraw.goto(xcoord + 20, ycoord + 5)
                            amdraw.goto(xcoord + 40, ycoord + 5)
                            amdraw.penup()
                    except KeyError as ke:
                        pass
                    except Exception as e:
                        print(str(e))
                amdraw.goto(xcoord + 10, ycoord - 20)
                yaccu = 0
                for j in cardisp[graphtype]["disp"]:
                    amdraw.color(j[1](i))
                    amdraw.write(j[0](i), font=FONT)
                    amdraw.goto(xcoord + 10, ycoord - 20 - yaccu)
                    yaccu += 20
                # Allow overflowing currently
                xcoord += 40

def render_bar():
    turtle3.clear()
    turtle3.right(turtle3.heading())
    turtle3.goto(-200, -60)
    for i in range(10):
        turtle3.pendown()
        if not light[i]:
            if DARK:
                turtle3.fillcolor('black')
            else:
                turtle3.fillcolor("white")
            turtle3.begin_fill()
            for j in range(4):
                turtle3.forward(40)
                turtle3.right(90)
            turtle3.end_fill()
            turtle3.forward(40)
        else:
            turtle3.fillcolor(tcolor[i])
            turtle3.begin_fill()
            for j in range(4):
                turtle3.forward(40)
                turtle3.right(90)
            # turtle.right(90)
            # print(turtle.heading())
            turtle3.end_fill()
            turtle3.penup()
            turtle3.forward(20)
            turtle3.right(90)
            turtle3.forward(20)
            turtle3.pencolor(xcolor[i])
            turtle3.write(iustr[i], align='center')
            if DARK:
                turtle3.pencolor('white')
            else:
                turtle3.pencolor("black")
            turtle3.left(90)
            turtle3.forward(20)
            turtle3.right(90)
            turtle3.forward(20)
            # turtle.left(turtle.heading())

            # turtle.left(90)
            turtle3.right(90)
            turtle3.forward(40)
            turtle3.right(90)
            turtle3.forward(40)
            # For debug,
            turtle3.right(90)
            turtle3.forward(40)
            # turtle.forward(80)
            # turtle.right(90)
            # turtle.forward(40)
            # turtle.right(90)
            # print(turtle.heading())
            turtle3.pendown()
            # time.sleep(4)
            # print("==")


def render_route_tackle(csp, cx, cy):
    global extcmd, lastseg, furseg, DRANGE, LEVEL, FONT, MYBLUE, MYGREEN, MYWHITE, curspeed, show_name, announced_name, announced_sig, former_sid, former_signal
    if (len(csp) < 2):
        return
    dis = int(csp[0])
    routedisp.pencolor(MYBLUE)
    prelevel = LEVEL
    if csp[1] == "La":
        if curspeed > int(csp[3]) or curspeed < int(csp[2]):
            routedisp.pencolor('orange')
        routedisp.write("Lf " + csp[3] + "/" + csp[2], align='right', font=FONT)
    elif csp[1] == "Le":
        routedisp.pencolor(MYGREEN)
        routedisp.write("Lf ---", align='right', font=FONT)
    elif csp[1] == "T":
        routedisp.write(" ".join(csp[2:]), align='right', font=FONT)
    elif csp[1] == "M":
        routedisp.pencolor(MYWHITE)
        if int(csp[2]) != prelevel:
            prelevel = int(csp[2])
            routedisp.write("GTCS " + str(csp[2]), align='right', font=FONT)
    elif csp[1] == "O":
        sloped = int(csp[2])
        if sloped < 0:
            routedisp.pencolor("orange")
        else:
            routedisp.pencolor(MYBLUE)
        routedisp.write("Slope " + str(csp[2]), align='right', font=FONT)
    elif csp[1] == "S":
        # Draw signal lights, status represent at csp[3]:
        # routedisp.pencolor(MYWHITE)
        zud = 10
        if (LEVEL <= 2) and (csp[2] == announced_name):
            csp[3] = announced_sig
        if (LEVEL <= 2) and (csp[2] != announced_name) and (LEVEL <= 1 or csp[2] != former_sid):
            routedisp.fillcolor('white')
            routedisp.begin_fill()
            routedisp.circle(3)
            routedisp.end_fill()
        else:
            if csp[3] == ".":
                routedisp.fillcolor('green')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
            elif csp[3] == "/":
                routedisp.fillcolor('yellow')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
            elif csp[3] == "|":
                routedisp.fillcolor('green')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
                routedisp.goto(cx - 6, cy)
                routedisp.fillcolor('yellow')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
            elif csp[3] in "<>":
                routedisp.fillcolor('yellow')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
                routedisp.goto(cx - 6, cy)
                routedisp.fillcolor('yellow')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
            elif csp[3].isdigit() and csp[3] != "0":
                if curspeed > int(csp[3]) * 10:
                    routedisp.pencolor('orange')
                routedisp.write("Hp " + csp[3] + "0", align='right', font=FONT)
                zud = 20
            elif csp[3] == "-":
                routedisp.fillcolor('yellow')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
                routedisp.goto(cx - 6, cy)
                routedisp.fillcolor('red')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
                routedisp.goto(cx - 10, cy)
                if len(csp) >= 5 and csp[4].isdigit():
                    routedisp.write(csp[4], align='right', font=FONT)
                zud = 20
            else:
                routedisp.fillcolor('red')
                routedisp.begin_fill()
                routedisp.circle(3)
                routedisp.end_fill()
        if show_name:
            routedisp.goto(cx - zud, cy)
            routedisp.pencolor(MYBLUE)
            routedisp.write(csp[2], align='right', font=FONT)
    elif csp[1] == "P0":
        routedisp.pencolor('orange')
        routedisp.write("El 1", align='right', font=FONT)
    elif csp[1] == "P1":
        routedisp.write("El 2", align='right', font=FONT)


def render_route():
    global extcmd, lastseg, furseg, DRANGE, LEVEL, FONT, MYBLUE, MYGREEN, MYWHITE, curspeed
    routedisp.penup()
    routedisp.clear()
    cx = -340
    if LEVEL == 1:
        cx = -320
    clastseg = [-1000000, []]
    cfurseg = [1000000, []]
    for i in extcmd[1:]:
        csp = i.split(" ")
        dis = int(csp[0])
        if dis < 0:
            if dis > clastseg[0]:
                clastseg = [dis, csp]
        elif dis > DRANGE:
            if dis < cfurseg[0]:
                cfurseg = [dis, csp]
        else:
            routedisp.goto(cx, dis / 20)
            render_route_tackle(csp, cx, dis / 20)
    routedisp.goto(cx, -20)
    render_route_tackle(clastseg[1], cx, -20)
    routedisp.goto(cx, 240)
    render_route_tackle(cfurseg[1], cx, 240)
    routedisp.goto(cx, 255)
    if len(cfurseg[1]) >= 2:
        routedisp.pencolor(MYBLUE)
        routedisp.write(str(round(cfurseg[0] / 1000, 2)), align='right', font=FONT)


def render_t2bar():
    turtle2.clear()
    turtle2.penup()
    turtle2.goto(-300, 0)
    for i in range(0, 200, 20):
        turtle2.goto(-300, i)
        turtle2.write(str(i * 20), font=FONT)


def gtcs3_load():
    global LEVEL, curspeed, lastspdlim, zusatz_lastspdlim, lbdisp, dif_warning
    limdraw.showturtle()
    limdraw.clear()
    limdraw.penup()
    if dif_warning > 0:
        # Fill warning
        limdraw.fillcolor('gray26')
        limdraw.goto(-320, -10)
        limdraw.begin_fill()
        limdraw.goto(-255, -10)
        limdraw.goto(-255, 260)
        limdraw.goto(-320, 260)
        limdraw.goto(-320, -10)
        limdraw.end_fill()
        render_t2bar()
    if LEVEL < 2:
        limdraw.hideturtle()
        return
    limdraw.goto(-320, 0)
    limdraw.pendown()
    limdraw.pencolor('orange')
    limdraw.pensize(3)
    limdraw.goto(-320, min(220, nextdist / 20))
    limdraw.penup()
    if (nextdist / 20) >= 220:
        limdraw.goto(-320, 240)
        limdraw.write(str(round(nextdist / 1000, 2)), font=FONT)
        limdraw.hideturtle()
    xspdraw.clear()
    xspdraw.penup()
    xspdraw.goto(-160, 40)
    if min(lastspdlim, zusatz_lastspdlim) < curspeed:
        xspdraw.pencolor('orange')
    else:
        if DARK:
            xspdraw.pencolor('green2')
        else:
            xspdraw.pencolor('green')
    smj = str(min(lastspdlim, zusatz_lastspdlim))
    if lbdisp > 0:
        smj += "/" + str(lbdisp)
        if curspeed < lbdisp:
            xspdraw.pencolor('maroon1')
    xspdraw.write(smj, align='center', font=FONT)


def gtcs3_init(noload=False):
    global LEVEL
    if LEVEL == 3:
        return
    LEVEL = 3
    if not noload:
        gtcs3_load()


def gtcs3_exit(level=1):
    global LEVEL
    if LEVEL < level:
        return
    LEVEL = level
    lkj_draw('white')
    # turtle2.clear()
    if LEVEL == 1:
        limdraw.clear()
        limdraw.hideturtle()
        xspdraw.clear()
    start_sound("gexit")


def cdrawer(basex, basey, rad, func):
    t = turtle
    
    # 绘制外圆
    t.penup()
    t.goto(basex, basey)
    t.pendown()
    t.circle(rad)
    
    # 绘制刻度线
    for i in range(0, 300, 30):  # 每30度一个刻度
        t.penup()
        t.goto(basex, basey+rad)
        t.setheading(210-i)  # 设置角度，0度在右侧
        
        # 移动到外圆位置
        t.forward(rad)
        t.pendown()
        
        # 绘制刻度线
        if i % 60 == 0:  # 主刻度（长）
            t.forward(10)
        else:  # 次刻度（短）
            t.forward(5)
        
        # 添加数字标签
        if i % 60 == 0:
            t.penup()
            t.forward(5)  # 移动到数字位置
            
            # 根据角度调整数字方向，使其易于阅读
            if (210-i) == 0 or (210-i) == 180:
                t.write(str(func(i)), align="center", font=FONT)
            elif (210-i) < 180:
                t.write(str(func(i)), align="left", font=FONT)
            else:
                t.write(str(func(i)), align="right", font=FONT)
    t.penup()
    t.right(t.heading())

# GTCS renderer
def render_gtcs():
    global curspeed, spdlim, accreq, gtcsinfo, sysinfo, thrust
    turtle.clear()
    turtle.penup()
    turtle.goto(-160, 0)
    #turtle.pendown()
    #turtle.circle(80)
    #turtle.penup()
    # Set number indications
    cdrawer(-160, 0, 80, lambda i: int(i * 1.5))
    """
    turtle.goto(-160, 0)
    # turtle.circle(80, -60)
    for i in range(0, 300, 60):
        turtle.circle(80, -60)
        #turtle.right(-90)
        #turtle.forward(15)
        turtle.write(str(int(i*1.5)), font=FONT)
        #turtle.forward(-15)
        #turtle.left(-90)
    """
    
    turtle.right(turtle.heading())
    # turtle.circle(80, -60)
    cdrawer(160, 0, 80, lambda i: abs(i - 120) * 2)
    # turtle.circle(80, -60)
    #for i in range(0, 300, 60):
    #    turtle.circle(80, -60)
    #    turtle.write(str(abs(i - 120) // 2), font=FONT)
    # turtle.left(90)
    if LEVEL >= 3:
        gtcs3_init(True)
    # Also available for GTCS-1 now
    render_t2bar()
    render_bar()
    spdturtle.goto(-160, 80)
    thrturtle.goto(160, 80)
    infobar.goto(-160, -120)
    turtle.update()


# 'Yellow-2' requires special operations
# at (-200, 200) by default, size 20.
def lkj_draw(col1, col2=""):
    lkjdraw.clear()
    lkjdraw.penup()
    lkjdraw.right(lkjdraw.heading())
    lkjdraw.goto(-200, 200)
    if col2 == "":
        lkjdraw.pendown()
        lkjdraw.fillcolor(col1)
        lkjdraw.begin_fill()
        lkjdraw.circle(20)
        lkjdraw.end_fill()
    else:
        lkjdraw.penup()
        lkjdraw.goto(-220, 220)
        lkjdraw.fillcolor(col2)
        lkjdraw.right(90)
        lkjdraw.pendown()
        lkjdraw.begin_fill()
        lkjdraw.circle(20, 180)
        lkjdraw.end_fill()
        lkjdraw.goto(-220, 220)
        lkjdraw.goto(-180, 220)
        lkjdraw.fillcolor(col1)
        lkjdraw.begin_fill()
        lkjdraw.circle(20, 180)
        lkjdraw.end_fill()

prelkj = "?"
gfailind = False
klee_braked = False
passenger_call = ""

intervene_spd = USERLIM

def render_gtcs_main():
    global onbat, klee_braked, passenger_call, batregen, ovrd_main_disp, gfailind, prelkj, light, caccel, prereded, curspeed, intervene_spd, acreqspd, spdlim, lastspdlim, accreq, gtcsinfo, sysinfo, thrust, eb, nextdist, failures, zusatz_lastspdlim, has_afb, passing
    # print("GTCS Renderer")
    gaspress.clear()
    acreqer.hideturtle()
    acreqer.goto(-160, 0)
    spdhint.clear()
    spdhint.penup()
    # 5 radius differ
    spdhint.goto(-160, 0)
    if light[3]:
        maxspder.pencolor('red')
        acreqer.pencolor('red')
    else:
        maxspder.pencolor('orange')
        acreqer.pencolor('orange')
    maxspder.clear()
    acreqer.clear()
    spdturtle.clear()
    thrturtle.clear()
    maxspder.clear()
    spdturtle.left(210)
    maxspder.left(210)
    thrturtle.left(90)
    # Generate speed info
    # Generate thrust
    spdturtle.pendown()
    spdturtle.right(curspeed / 1.5)
    spdturtle.forward(75)
    spdturtle.penup()
    gtcs3_load()
    spdraw.clear()
    maxspder.pendown()
    maxspder.right(spdlim / 1.5)
    maxspder.forward(75)
    maxspder.penup()
    acreqer.goto(-160, 0)
    acreqer.right(acreqer.heading())
    acreqer.circle(80, 60 + (360 - USERLIM) / 1.5)
    if curspeed > USERLIM:
        acreqer.pencolor('orange')
    else:
        if DARK:
            acreqer.pencolor('green2')
        else:
            acreqer.pencolor('green')
    acreqer.write(str(USERLIM), font=FONT)
    acreqer.pencolor('orange')
    acreqer.goto(-160, 0)
    acreqer.right(acreqer.heading())
    acreqer.circle(80, 60 + (360 - curspeed) / 1.5)
    acreqer.pendown()
    if (acreqspd) < curspeed:
        wacreqspd = curspeed + accreq * (20 * 3.6)
        if wacreqspd < min(spdlim, intervene_spd, lastspdlim, zusatz_lastspdlim):
            wacreqspd = min(spdlim, intervene_spd, lastspdlim, zusatz_lastspdlim)
        acreqer.circle(80, (wacreqspd - curspeed) * (-1) / 1.5)
    acreqer.left(90)
    acreqer.penup()
    spdhint.right(spdhint.heading())
    spdhint.circle(80, 60 + (360 - curspeed) / 1.5)
    spdhint.pendown()
    cspdexp = curspeed + (caccel * 100)
    if cspdexp > USERLIM:
        cspdexp = USERLIM
    elif cspdexp < 0:
        cspdexp = 0
    # debug
    # print(cspdexp)
    spdhint.circle(80, (cspdexp - curspeed) * (-1) / 1.5)
    spdhint.left(90)
    spdhint.penup()
    #thrturtle.pendown()
    #thrturtle.right(thrust)
    #thrturtle.forward(75)
    thrturtle.penup()
    thrturtle.goto(160, 0)
    thrturtle.right(thrturtle.heading())
    thrturtle.circle(80, max(0, 180 - power/3))
    if power <= 0:
        thrturtle.fillcolor('orange')
    else:
        thrturtle.fillcolor('blue')
    tcx = thrturtle.xcor()
    tcy = thrturtle.ycor()
    thrturtle.begin_fill()
    thrturtle.goto(160, 80)
    thrturtle.goto(tcx, tcy)
    thrturtle.circle(80, power/3)
    thrturtle.goto(160, 80)
    thrturtle.end_fill()
    spdraw.clear()
    spdraw.goto(-160, 70)
    spdraw.fillcolor('white')
    spdraw.pencolor('black')
    spdraw.pendown()
    spdraw.begin_fill()
    spdraw.circle(20)
    spdraw.end_fill()
    spdraw.penup()
    spdraw.goto(-160, 80)
    # spdraw.
    spdraw.write(str(int(curspeed)), align='center', font=FONT)
    cthrdraw.clear()
    cthrdraw.penup()
    cthrdraw.goto(160, 70)
    cthrdraw.fillcolor('white')
    cthrdraw.pencolor('black')
    cthrdraw.pendown()
    cthrdraw.begin_fill()
    cthrdraw.circle(20)
    cthrdraw.end_fill()
    cthrdraw.penup()
    cthrdraw.goto(160, 80)
    dthrust = int(thrust)
    if abs(thrust) < 10:
        dthrust = round(thrust, 1)
    cthrdraw.write(str(min(999, dthrust)), align='center', font=FONT)
    infobar.clear()
    if thrust >= 0:
        gaspress.write("600", align='center', font=FONT)
    else:
        gpress = max(0, int(600 + (power * 6.4) - 5 + random.randint(0, 10)))
        if gpress > 600:
            gpress = 600
        if gpress < 100:
            if not gfailind:
                gfailind = True
                start_sound("braking")
            if (not klee_braked) and (curspeed > 300):
                klee_braked = True
                passenger_call = "klee_brake"
        else:
            gfailind = False
        gaspress.write(str(gpress), align='center', font=FONT)
    # Generate info
    if not ovrd_main_disp:
        if has_afb:
            gtcsinfo.append(["AFB Enabled", MYGREEN])
        if passenger_call != "":
            gtcsinfo.append(["Passenger Call - Press H", MYWHITE])
        if onbat:
            gtcsinfo.append(["On Battery", "orange"])
        if batregen:
            gtcsinfo.append(["Battery Regeneration", MYBLUE])
        if passing:
            gtcsinfo.append(["Passing Mode", "orange"])
        for i in failures:
            if failures[i][1] or (failures[i][2]()):
                gtcsinfo.append([failures[i][0], "maroon1"])
                if not was_failure[i]:
                    start_sound("warning")
        ccid = 1
        for i in cars:
            #print(i)
            for jt in i["failures"]["term"]:
                j = i["failures"]["term"][jt]
                if j[1] or j[2](i):
                    gtcsinfo.append(["Carriage " + str(ccid) + " " + j[0], "maroon1"])
                    if (jt not in i["failures"]["was_failure"]) or (not i["failures"]["was_failure"][jt]):
                        start_sound("warning")
            ccid += 1
        for i in gtcsinfo:
            if DARK and i[1] == "blue":
                i[1] = "cyan"
            infobar.pencolor(i[1])
            infobar.pendown()
            infobar.write(i[0], font=FONT)
            infobar.penup()
            infobar.goto(infobar.xcor(), infobar.ycor() - 30)
        infobar.goto(120, -120)
        for i in sysinfo:
            infobar.pencolor(i[1])
            infobar.pendown()
            infobar.write(i[0], font=FONT)
            infobar.penup()
            infobar.goto(infobar.xcor(), infobar.ycor() - 30)
    render_anemo_power()
    if curlkj == "0" or curlkj == "00":
        if curlkj == "00" or prereded:
            lkj_draw("red")
            if not passing:
                start_sound("red")
        else:
            lkj_draw("red", "yellow")
    elif curlkj == "1":
        lkj_draw('yellow')
    elif curlkj in "<>":
        lkj_draw('yellow', 'yellow')
    elif curlkj == "2":
        lkj_draw('green', 'yellow')
    elif curlkj == "@":
        lkjdraw.color('white')
        lkj_draw('yellow')
        lkjdraw.penup()
        lkjdraw.goto(-200, 215)
        lkjdraw.color('black')
        lkjdraw.write("2", font=FONT)
    elif curlkj == "3":
        lkj_draw('green')
    elif curlkj in "4567":
        lkjdraw.color('white')
        lkj_draw('green')
        lkjdraw.penup()
        lkjdraw.color('white')
        lkjdraw.goto(-200, 215)
        lkjdraw.write(str(int(curlkj) - 2), font=FONT)
        lkjdraw.color('black')
    else:
        lkj_draw('white')
    if prelkj != curlkj:
        prelkj = curlkj
        if curlkj == "0" or curlkj == "00":
            if not (curlkj == "00" or prereded):
                start_sound("red-yellow")
        elif curlkj == "1":
            start_sound("yellow")
        elif curlkj in "<>":
            start_sound("double-yellow")
        elif curlkj == "2":
            start_sound("green-yellow")
        elif curlkj == "@":
            start_sound("yellow2")
        elif curlkj in "34567":
            if curlkj == "3":
                start_sound("green")
            else:
                start_sound("green" + str(int(curlkj) - 2))

    lkjdraw.penup()
    maxspder.right(maxspder.heading())
    spdturtle.right(spdturtle.heading())
    thrturtle.right(thrturtle.heading())
    spdturtle.goto(-160, 80)
    spdraw.goto(-160, 80)
    maxspder.goto(-160, 80)
    acreqer.showturtle()
    thrturtle.goto(160, 80)
    infobar.goto(-160, -120)
    lkjdraw.goto(-200, 200)
    render_bar()
    render_route()
    turtle.update()
    turtle.ontimer(render_gtcs_main, 200)


def kup(smooth=False):
    global power, thrust
    # print("Keyup")
    if power > 500:
        return
    if smooth:
        power += 1
        return
    power = (power // 10) * 10 + 10


def kdn(smooth=False):
    global power, thrust
    # print("Keydn")
    if power < -350:
        return
    if smooth:
        power -= 1
        return
    power = (power // 10) * 10 - 10


def ksupp():
    global accreq, spdlim, lastspdlim, on_keyboard
    if on_keyboard:
        # Also INCORRECT FOR OTHER??
        keyboard_add('9')
        return
    if not light[9]:
        gtcs3_exit()
        accreq = 0
        spdlim = 40
        light[2] = False
        light[3] = False
        lastspdlim = USERLIM
    light[9] = not light[9]


acreqspd = 240
accuer = 0
limitz = []
caccel = 0
contnz = 0
plog = []
tcnter1 = 0


def submit_loc(czugat=None):
    global zugat, accuer
    cszugat = czugat
    csaccuer = int(accuer)
    if cszugat is None:
        cszugat = zugat
    else:
        csaccuer = 1
    try:
        u = urlopen(TCTR + "?mode=submit&auth=" + AUTH + "&name=" + ZUGNAME + "&spd=120&vist=" + str(
            int(curspeed)) + "&sname=" + cszugat + "&dev=" + str(csaccuer))
        u.close()
        return True
    except Exception as e:
        g3err.append(time.ctime() + " GTCS Befehl Submit: " + str(e))
        return False

lastupdate_t = time.time()

def physics():
    global lastupdate_t, current_slope, tcnter1, intervene_spd, plog, contnz, caccel, limitz, accuer, curspeed, thrust, gtcsinfo, accreq, power, acreqspd, LEVEL, schutz, schutz_info, sysinfo, zusatz_lastspdlim, passing, PASSING_SPD, MONITOR_SPEED_DELTA, MONITOR_ACCEL, announced_sig, announcement_got, dendro_mass, dendro_feed
    if power < 0 or curspeed < 20:
        thrust = power / 2
    else:
        thrust = power / (curspeed / 10)
    thrust *= car_stat(cpsrc)
    # Might be dynamic values in the future
    thrust -= max(0, 10 + (current_slope / 5) - geo_elem * car_stat("g") * 0.7)
    accuer += (curspeed / 3.6) * (time.time() - lastupdate_t)
    cweight = car_stat("weight")
    caccel = thrust / cweight
    curspeed += thrust / cweight * ((time.time() - lastupdate_t) / 0.2)
    lastupdate_t = time.time()
    if (thrust > 0) and light[1]:
        tcnter1 += 1
        if tcnter1 > 20:
            light[1] = False
            tcnter1 = 0
    else:
        tcnter1 = 0
    if curspeed < 0:
        curspeed = 0
    if power < 0:
        tcolor[4] = "red"
        tcolor[5] = "red"
    else:
        tcolor[4] = "green"
        tcolor[5] = "green"

    light[4] = (abs(power) > 0)
    light[5] = (abs(power) > 30)
    light[6] = (power < -40)

    gtcsinfo = []
    if light[9]:
        gtcsinfo = [["GTCS-1 Overridden", "blue"]]
    else:
        if spdlim < USERLIM:
            gtcsinfo = [["GTCS-" + str(LEVEL) + " speed limit " + str(spdlim) + " km/h", "orange"]]
        cspdlim = spdlim
        # light[3] = False
        cacreqspd = acreqspd
        
        if ((LEVEL >= 2) and curspeed > (cacreqspd + 3)) and (accreq < -2):
            contnz += 0.5
        if (LEVEL <= 1) and (contnz > 12):
            light[3] = True
        if (contnz > 50) or (accreq < -8):
            light[3] = True
            plog.append(time.ctime() + " GTCS: vcac = " + str(round(cacreqspd, 2)) + ", cntz = " + str(contnz))
        ccspdlim = min(spdlim, cspdlim, lastspdlim, zusatz_lastspdlim)
        if (LEVEL <= 1) and (curspeed > ccspdlim):
            if (curspeed - ccspdlim > 80):
                accreq = -12
                contnz += 1
            elif (curspeed - ccspdlim > 60):
                accreq = -6
                contnz += 0.5
            elif curspeed > ccspdlim:
                accreq = -4
                contnz += 0.25
        if LEVEL <= 1:
            # Evaluate for announcement signals
            if announced_sig != "?":
                cvziel = translate(announced_sig)
                intervened = False
                for i in range(len(ANNOUNCEMENT_AT)):
                    if not announcement_got[i]:
                        continue
                    #print("Monitor attempt ",str(cvziel + MONITOR_SPEED_DELTA[i]),"for",str(-MONITOR_ACCEL[i]))
                    cmonspd = cvziel + MONITOR_SPEED_DELTA[i]
                    if curspeed > cmonspd:
                        accreq = min(accreq, -MONITOR_ACCEL[i])
                        intervene_spd = cmonspd
                        intervened = True
                if not intervened:
                    intervene_spd = USERLIM
        else:
            intervene_spd = USERLIM
        if (curspeed < ccspdlim) or (accreq >= 0):
            accreq = 0
            contnz = 0
            light[2] = False
            light[3] = False
        if (accreq >= 0):
            acreqspd = USERLIM
        else:
            acreqspd = curspeed + accreq * (2 * 3.6)
            if acreqspd < 0:
                acreqspd = 0
            #print("Raw evaluation #1:",acreqspd)
            if acreqspd > min(lastspdlim, spdlim):
                acreqspd = min(lastspdlim, spdlim)
            #print("Raw evaluation #2",acreqspd)
        #print("Result accreq=",accreq,"acreqspd=",acreqspd)
        if curspeed > min(spdlim, intervene_spd):
            # if len(limitz) >= 10:
            # cacreqspd = max(acreqspd,limitz[0] + 5)
            #    if len(limitz) > 10:
            #        limitz = limitz[1:]
            # if cacreqspd < 120:
            #    gtcsinfo.append(["GTCS-"+str(LEVEL)+" deflection " + str(int(cacreqspd)) + " km/h","orange"])
            # gtcsinfo.append(["Acceleration " + str(round(accreq,2)),"orange"])
            if accreq < -1.5:
                gtcsinfo.append(["Deflect now", "orange"])
                start_sound("deflect")
            light[2] = True
        if schutz:
            light[3] = True
            gtcsinfo.append([schutz_info, "red"])
        # limitz.append(acreqspd)
        # gtcsinfo = []
        if light[3]:
            if thrust >= -40:
                if curspeed > 60 and power < 0:
                    power -= 4
                else:
                    power -= 10
            if schutz:
                gtcsinfo.append(["Schutzbremsung", "red"])
                start_sound("schutz")
            else:
                gtcsinfo.append(["Zwangsbremsung", "red"])
                start_sound("zb")
    if light[6]:
        gtcsinfo.append(["Magnet-brake", "blue"])
    dendro_mass += dendro_feed / 300
    if cpsrc == "d":
        dendro_mass -= thrust / 400
    if dendro_mass < 0:
        dendro_mass = 0
    elif dendro_mass > 5000:
        dendro_mass = 5000
    turtle.ontimer(physics, 200)


### TODO: Use requests library.

def test1():
    global spdlim
    spdlim -= 1


def test2():
    global spdlim
    spdlim += 1


def test3():
    global accreq
    accreq -= 1


def test4():
    global accreq
    accreq += 1


befehltext = ""
bns = ""
befconf = False

keyboard = ""
on_keyboard = False
next_keyboard = lambda: None


def befshow(bcset=False):
    global bns, befehltext, befconf, keyboard, on_keyboard
    befehldisp.clear()
    befehldisp.goto(-160, 240)
    bs = befehltext.split("\n")
    bs.append(bns)
    if on_keyboard:
        bs.append(keyboard)
    for i in bs:
        befehldisp.write(i, font=FONT)
        befehldisp.goto(-160, befehldisp.ycor() - 15)
    if bcset:
        befconf = True


def keyboard_add(char):
    global keyboard, on_keyboard
    if on_keyboard:
        keyboard += char
        befshow()


def befshow2():
    global on_keyboard
    if on_keyboard:
        keyboard_add('7')
        return
    befshow(True)


def befclr():
    global befehltext, on_keyboard
    if on_keyboard:
        keyboard_add('8')
        return
    befehldisp.clear()


def locupd():
    tloc = turtle.textinput("GTCS", "Input current location:")
    if tloc != "":
        update_loc(tloc)


def schutz_cancel():
    global schutz, on_keyboard, ps_queue, failures, was_failure, cars
    if on_keyboard:
        keyboard_add('5')
        return
    schutz = False
    light[3] = False
    for i in failures:
        was_failure[i] = (failures[i][1] or failures[i][2]())
    for i in cars:
        for j in i["failures"]["term"]:
            i["failures"]["was_failure"][j] = (j[1] or j[2](i))
    ps_queue.clear()


def locshow():
    global zugat, befehltext, on_keyboard
    if on_keyboard:
        keyboard_add('6')
        return
    befehltext = "Current location: " + zugat
    befshow()


def change_loc_nxstep():
    global keyboard, on_keyboard, next_keyboard
    update_loc(keyboard)
    on_keyboard = False
    next_keyboard = lambda: None
    bns = ""
    befclr()


def change_loc():
    global bns, on_keyboard, next_keyboard, gauto
    if on_keyboard:
        keyboard_add('4')
        return
    keyboard = ""
    bns = "Input new location:"
    next_keyboard = change_loc_nxstep
    gauto = True
    on_keyboard = True
    befshow()


def change_spd_nxstep():
    global USERLIM, on_keyboard
    bns = ""
    try:
        USERLIM = int(keyboard)
    except:
        bns = "Error: Unable to configure!"
    on_keyboard = False
    next_keyboard = lambda: None
    

def change_spd():
    global bns, on_keyboard, next_keyboard
    if on_keyboard:
        keyboard_add('3')
        return
    keyboard = ""
    bns = "Input new speed restriction (current: " + str(USERLIM) + " km/h): "
    on_keyboard = True
    next_keyboard = lambda: change_spd_nxstep()
    befshow()


def paxcaller():
    global passenger_call, on_keyboard
    #print("Call pcall")
    if on_keyboard:
        keyboard_add('h')
        return
    if passenger_call != "":
        start_sound(passenger_call)
        passenger_call = ""

def passing_switch():
    global on_keyboard, passing
    if on_keyboard:
        keyboard_add('z')
        return
    if not passing:
        passing = True
    else:
        passing = False

t.screen.onkey(kup, 'Up')
t.screen.onkey(kdn, 'Down')
t.screen.onkey(ksupp, '9')
t.screen.onkey(befclr, '8')
# Also for confirmation.
t.screen.onkey(befshow2, '7')
t.screen.onkey(locshow, '6')
t.screen.onkey(schutz_cancel, '5')
t.screen.onkey(change_loc, '4')
t.screen.onkey(change_spd, '3')
t.screen.onkey(paxcaller, 'h')
t.screen.onkey(passing_switch, 'z')


def wind_charge():
    global apress, on_keyboard
    if on_keyboard:
        keyboard_add('o')
        return
    apress += random.randint(50, 150) / 10


def wind_release():
    global apress, on_keyboard
    if on_keyboard:
        keyboard_add('p')
        return
    apress -= random.randint(50, 150) / 10
    if apress < 0:
        apress = 0


def elec_charge():
    global ceamps, cevolts, on_keyboard
    if on_keyboard:
        keyboard_add('k')
        return
    cevolts += random.randint(10, 30)
    ceamps += random.randint(10, 30) / 20


def elec_release():
    global ceamps, cevolts, on_keyboard
    if on_keyboard:
        keyboard_add('l')
        return
    cevolts -= random.randint(10, 30)
    ceamps -= random.randint(10, 30) / 20
    if cevolts < 0:
        cevolts = 0
    if ceamps < 0:
        ceamps = 0


def swtc_pwr():
    global cpsrc, on_keyboard
    if on_keyboard:
        keyboard_add('a')
        return
    if cpsrc == "a":
        cpsrc = "e"
    elif cpsrc == "e":
        cpsrc = "d"
    else:
        cpsrc = "a"


def panto_swtc():
    global cpsrc, on_keyboard
    if on_keyboard:
        keyboard_add('s')
        return
    cpsrc = "p"


def name_disp():
    global show_name, on_keyboard
    if on_keyboard:
        keyboard_add('0')
        return
    show_name = not show_name


def change_afb():
    global on_keyboard, has_afb
    if on_keyboard:
        keyboard_add('g')
        return
    has_afb = not has_afb
    if not has_afb:
        start_sound('caution')

def show_switch():
    global on_keyboard, ovrd_main_disp
    if on_keyboard:
        keyboard_add('m')
        return
    ovrd_main_disp = not ovrd_main_disp

def chg_switch():
    global on_keyboard, ovrd_page
    if on_keyboard:
        keyboard_add('n')
        return
    if ovrd_page == 'a':
        ovrd_page = 'e'
    elif ovrd_page == 'e':
        ovrd_page = 'z'
    else:
        ovrd_page = 'a'

def geo_charge():
    global on_keyboard, geo_elem
    if on_keyboard:
        keyboard_add('u')
        return
    if geo_elem < 10.0:
        geo_elem += random.randint(1, 4) / 10

def geo_release():
    global on_keyboard, geo_elem
    if on_keyboard:
        keyboard_add('i')
        return
    geo_elem -= random.randint(2, 6) / 10
    if geo_elem < 0:
        geo_elem = 0

        
def dendro_charge():
    global on_keyboard, dendro_feed
    if on_keyboard:
        keyboard_add('O')
        return
    dendro_feed += random.randint(2, 8) / 10

def dendro_release():
    global on_keyboard, dendro_feed
    if on_keyboard:
        keyboard_add('P')
        return
    dendro_feed -= random.randint(6, 10) / 10
    if dendro_feed < 0:
        dendro_feed = 0

def pyro_charge():
    global apress, on_keyboard, pyro_temp
    if on_keyboard:
        keyboard_add('o')
        return
    pyro_temp += random.randint(50, 150) / 10

def pyro_release():
    global apress, on_keyboard, pyro_temp
    if on_keyboard:
        keyboard_add('p')
        return
    pyro_temp -= random.randint(50, 150) / 10
    if pyro_temp < 0:
        pyro_temp = 0

def system_upgrade():
    global on_keyboard
    if on_keyboard:
        keyboard_add('v')
        return
    gtcs3_init()

t.screen.onkey(wind_charge, 'o')
t.screen.onkey(wind_release, 'p')
t.screen.onkey(elec_charge, 'k')
t.screen.onkey(elec_release, 'l')
t.screen.onkey(swtc_pwr, 'a')
t.screen.onkey(panto_swtc, 's')
t.screen.onkey(change_afb, 'g')
t.screen.onkey(show_switch, 'm')
t.screen.onkey(chg_switch, 'n')
t.screen.onkey(geo_charge, 'u')
t.screen.onkey(geo_release, 'i')
t.screen.onkey(dendro_charge, 'O')
t.screen.onkey(dendro_release, 'P')
t.screen.onkey(pyro_charge, 'K')
t.screen.onkey(pyro_release, 'L')
t.screen.onkey(system_upgrade, 'v')
t.screen.onkey(name_disp, '0')


def syspage_switch(ckey):
    global csyspage, on_keyboard
    if on_keyboard:
        keyboard_add(ckey)
        return
    csyspage = ckey


for i in syspages:
    t.screen.onkey(eval("lambda: syspage_switch('{}')".format(i)), i)

for i in '12dfjxcbQWERTYUIASDFGHJZXCVBNM':
    t.screen.onkey(eval("lambda: keyboard_add('{}')".format(i)), i)

if not SPECIAL_KEY:
    t.screen.onkey(lambda: keyboard_add('_'), ',')


def discard_keyboard():
    global on_keyboard, keyboard, next_keyboard
    on_keyboard = False
    keyboard = ""
    next_keyboard = lambda: None
    befclr()


def proceed_keyboard():
    global on_keyboard, keyboard, next_keyboard
    next_keyboard()


if not SPECIAL_KEY:
    t.screen.onkey(discard_keyboard, '.')
    t.screen.onkey(proceed_keyboard, '/')

t.screen.listen()


def translate(signal):
    cspdlim = 0
    if signal == ".":
        cspdlim = USERLIM
    elif signal == "|":
        cspdlim = 120
    elif signal == "/" or signal == "<" or signal == ">":
        cspdlim = 60
    elif signal.isdigit():
        cspdlim = (int(signal)) * 10
    else:
        cspdlim = 0
    if cspdlim > USERLIM:
        return USERLIM
    return cspdlim


autog3 = True
ospeed = spdlim
geschw = 120

def lkjcall(zugat):
    global LCTR, curlkj, prereded
    u = urlopen(LCTR + "?sid=" + zugat)
    su = u.read().decode('utf-8')
    u.close()
    curlkj = su
    if lastspdlim <= 0:
        curlkj = "00"
        prereded = True


def update_loc(target):
    global geschw, curlkj, prereded, accuer, lastspdlim, g3err, LEVEL, zugat, spdlim, accreq, ZUGNAME, autog3, ospeed, AUTH, passing, PASSING_SPD, ANNOUNCEMENT_AT, announcement_got
    try:
        announcement_got = [False] * len(ANNOUNCEMENT_AT)
        submit_loc(target)
        if zugat != "":
            u = urlopen(ZCTR + "?sid=" + zugat + "&type=1&name=" + ZUGNAME + "&auth=" + AUTH)
            u.read()
            u.close()
        u = urlopen(SCTR + "?sid=" + target)
        su = u.read().decode('utf-8')
        u.close()
        # print("Full text:",su)
        sus = su.strip()
        signal = "0"
        if len(sus) > 1:
            signal = sus[:2]
        else:
            signal = sus[0]
        g3err.append(time.ctime() + " GTCS-1: Receiving signal " + str(signal))
        cspdlim = translate(signal)
        if passing:
            cspdlim = PASSING_SPD
        if cspdlim == 0:
            prereded = True
        else:
            prereded = False
        if LEVEL <= 1:
            spdlim = cspdlim
            if spdlim > ospeed:
                light[1] = True
            elif spdlim < ospeed:
                light[1] = False
            ospeed = spdlim
        lastspdlim = cspdlim
        geschw = cspdlim
        zugat = target
        if LEVEL <= 1:
            accuer = 0
        elif LEVEL >= 2:
            accuer = 1
        if autog3:
            gtcs3_init()
            autog3 = False
        lkjcall(zugat)
        u = urlopen(ZCTR + "?sid=" + target + "&type=0&name=" + ZUGNAME + "&auth=" + AUTH)
        u.read()
        u.close()
    except Exception as e:
        print("Error:", str(e))
        spdlim = 0


g3err = []

GLOGGING = False
PLOGGING = False


def schutz_broadcast(info):
    global schutz, schutz_info
    schutz = True
    schutz_info = info


def console():
    global SCHUTZ_PROB, SCHUTZ_SIMU, SCTR, ZCTR, DCTR, BCTR, LCTR, ICTR, TCTR, GLOGGING, PLOGGING, plog, ZUGNAME, spdlim, zugat, gtcsinfo, accreq, acreqspd, thrust, current_slope, power, accuer, LEVEL, g3err, autog3, failures, passenger_call, cars
    while True:
        ip = input(">>> ")
        cmd = ip.split(" ")
        if len(cmd) < 1:
            print("Invalid command - too short")
            continue
        if cmd[0] == "at":
            # zugat = cmd[1]
            if len(cmd) < 2:
                print("Invalid at command")
                continue
            update_loc(cmd[1])
            print("Successfully updated location")
        elif cmd[0] == "ren":
            if len(cmd) < 2:
                print("Current name", ZUGNAME)
                continue
            ZUGNAME = " ".join(cmd[1:])
            print("Successfully updated name")
        elif cmd[0] == "gi":
            if len(cmd) < 2:
                print("Invalid at command")
                continue
            if cmd[1] == "0":
                print(gtcsinfo)
            elif cmd[1] == "1":
                print(spdlim)
            elif cmd[1] == "2":
                print(acreqspd)
            elif cmd[1] == "2a":
                print(accreq)
            elif cmd[1] == "3":
                print(thrust)
            elif cmd[1] == "4":
                print(accuer)
            elif cmd[1] == "5":
                print(curlkj)
            elif cmd[1] == "6":
                print(maxthr_val())
            elif cmd[1] == "6n":
                print(power)
            elif cmd[1] == "7":
                print(current_slope)
            elif cmd[1] == "s":
                print(min(lastspdlim, zusatz_lastspdlim))
        elif cmd[0] == "glog":
            print("Currently GTCS", LEVEL)
            print("\n".join(g3err))
        elif cmd[0] == "gclr":
            g3err = []
        elif cmd[0] == "plog":
            print("\n".join(plog))
        elif cmd[0] == "pclr":
            plog = []
        elif cmd[0] == "genter":
            if zugat.strip() == "":
                print("No initial position information")
            else:
                gtcs3_init()
        elif cmd[0] == "gexit":
            if (len(cmd) > 1) and (cmd[1].isdigit()):
                print("Quit to special GTCS-{}".format(cmd[1]))
                gtcs3_exit(int(cmd[1]))
            else:
                gtcs3_exit()
        elif cmd[0] == "gauto":
            autog3 = not autog3
            print("GTCS-3 automatic activate is now", autog3)
        elif cmd[0] == "sset":
            if len(cmd) < 2:
                print("Invalid at command")
                continue
            spdlim = int(cmd[1])
        elif cmd[0] == "glstat":
            GLOGGING = not GLOGGING
            print("GLog is now", GLOGGING)
        elif cmd[0] == "plstat":
            PLOGGING = not PLOGGING
            print("PLog is now", GLOGGING)
        elif cmd[0] == "pax":
            if len(cmd) < 2:
                print("Current passenger call:",passenger_call)
            else:
                passenger_call = cmd[1]
        elif cmd[0] == "ip":
            if len(cmd) < 2:
                print("Invalid ip command")
                continue
            SCTR = "http://{ip}:5033/signal".format(ip=cmd[1])
            ZCTR = "http://{ip}:5033/zug".format(ip=cmd[1])
            DCTR = "http://{ip}:5033/zugdist".format(ip=cmd[1])
            BCTR = "http://{ip}:5033/befehl".format(ip=cmd[1])
            LCTR = "http://{ip}:5033/lkjdisp".format(ip=cmd[1])
            ICTR = "http://{ip}:5033/signaldata".format(ip=cmd[1])
            TCTR = "http://{ip}:5033/trainop".format(ip=cmd[1])
        elif cmd[0] == "schutz":
            if len(cmd) < 2:
                SCHUTZ_SIMU = not SCHUTZ_SIMU
                print("Schutz simulator is now", SCHUTZ_SIMU)
            else:
                if cmd[1].isdigit():
                    SCHUTZ_PROB = int(cmd[1])
                    print("Schutz probability is now", SCHUTZ_PROB)
                else:
                    schutz_broadcast(cmd[1])
        elif cmd[0] == "failmgmt":
            try:
                if len(cmd) < 2:
                    for i in failures:
                        failures[i][1] = False
                    print("All failures cleared")
                elif cmd[1] == "car":
                    if len(cmd) < 3:
                        for i in cars:
                            for jt in i["failures"]["term"]:
                                j = i["failures"]["term"][jt]
                                if j[1]:
                                    j[1] = False
                                    j[5](i)
                        print("All failures cleared")
                    else:
                        pass
                else:
                    failures[cmd[1]][1] = not failures[cmd[1]][1]
                    print("Failure item '{}' is configured to".format(failures[cmd[1]][0]), failures[cmd[1]][1])
            except Exception as e:
                print("Unable to configure", e)
        elif cmd[0] == "connect":
            if len(cmd) < 2:
                print("Invalid connect commmand")
                continue
            conn = copy.deepcopy(eval(" ".join(cmd[1:])))
            if type(conn) is list:
                cars += conn
            else:
                cars.append(conn)
            schutz_broadcast("Zugbind")
        elif cmd[0] == "disconnect":
            if len(cmd) < 2:
                print("Invalid disconnect commmand")
                continue
            sz = int(cmd[1])
            if sz > 0:
                cars = cars[:sz]
            schutz_broadcast("Zugtrennwarnung")
        else:
            print("Invalid command")


def accelreq(spdlim, sd):
    global curspeed, caccel
    raw = 0
    if curspeed > spdlim:
        if sd > 100:
            raw = (((spdlim / 3.6) ** 2 - ((curspeed + max(0, caccel + 0.2) * 3) / 3.6) ** 2) / (2 * (sd - 100)))
            if sd < 500:
                raw -= 0.25
            elif sd < 1200:
                raw -= 0.15
            elif sd < 2000:
                raw -= 0.1
        else:
            raw = -4
    return raw

zusatz_spdlim = 350
zusatz_spdlim_at = 10000000

former_sid = "?"
former_signal = "?"
dif_warning = 0

def gtcs3():
    global lbdisp, passdz, current_slope, geschw, lastseg, furseg, extcmd, LCTR, curlkj, lastspdlim, g3err, accuer, curspeed, caccel, nextdist, spdlim, accreq, acreqspd, zugat, ospeed, zusatz_lastspdlim, zusatz_spdlim, zusatz_spdlim_at, appdz, asuber, dif_warning, former_sid, former_signal, ANNOUNCEMENT_AT, announcement_got, announced_name, announced_sig
    while True:
        # Load actual special command
        zusatz_spdlim = 350
        zusatz_spdlim_at = 10000000
        tmpz = 350
        tmplb = 0
        last_cancel = -100000
        pass_p0 = -100000
        pass_p1 = -99999
        lkj_to_call = False
        try:
            # Resolve actual information:
            if (zugat != "") and (zugat != "?"):
                u = urlopen(ICTR + "?sid=" + zugat + "&dev=" + str(int(accuer)))
                asuber = int(accuer)
                extinf = u.read().decode('utf-8')
                u.close()
                extcmd = extinf.split("\n")
                try:
                    remdis = int(extcmd[0])
                    sname = "?"
                    esc = extcmd[1:]
                    c_current_slope = 0
                    for i in esc:
                        csp = i.split(" ")
                        dis = int(csp[0])
                        if csp[1] == "S" and sname == "?":
                            sname = csp[2]
                            # Closest signal
                            if LEVEL <= 2:
                                for i in range(len(ANNOUNCEMENT_AT)):
                                    if (dis < ANNOUNCEMENT_AT[i]) and (not announcement_got[i]):
                                        announcement_got[i] = True
                                        if (sname != announced_name) or (csp[3] != announced_sig):
                                            # This is not working, but I don't know why.
                                            dif_warning = 3
                                        announced_name = sname
                                        # Directly copy signal text
                                        announced_sig = csp[3]
                                        lkj_to_call = True
                                        
                        elif csp[1] == "Le":
                            if dis < 0:
                                last_cancel = max(last_cancel, dis)
                        elif csp[1] == "P0":
                            if dis < 0:
                                pass_p0 = max(pass_p0, dis)
                            else:
                                if dis < 500:
                                    appdz = False
                                elif dis < 1000:
                                    if not appdz:
                                        appdz = True
                                        start_sound("neutral")
                        elif csp[1] == "P1":
                            if dis < 0:
                                pass_p1 = max(pass_p1, dis)
                                appdz = False
                        elif csp[1] == "M":
                            if dis < 0:
                                max_level = int(csp[2])
                                if max_level < LEVEL:
                                    gtcs3_exit(max_level)
                        elif csp[1] == "O":
                            if dis < 0:
                                c_current_slope = int(csp[2])
                        elif csp[1] == "Elem":
                            if dis < 0:
                                if csp[2] == "A":
                                    anemo_bg = int(csp[3])
                                elif csp[2] == "Ev":
                                    electro_vbg = int(csp[3])
                                elif csp[2] == "Ea":
                                    electro_abg = int(csp[3])
                                elif csp[2] == "G":
                                    geo_bg = int(csp[3])
                    current_slope = c_current_slope
                    passdz = (pass_p0 >= pass_p1)
                    for i in esc:
                        csp = i.split(" ")
                        if csp[1] == "La":
                            dis = int(csp[0])
                            if dis < 0:
                                if dis > last_cancel:
                                    tmpz = min(tmpz, int(csp[3]))
                                    tmplb = max(tmplb, int(csp[2]))
                            else:
                                if int(csp[3]) <= zusatz_spdlim:
                                    zusatz_spdlim = int(csp[3])
                                    zusatz_spdlim_at = min(zusatz_spdlim_at, dis)
                    lbdisp = tmplb
                    zusatz_lastspdlim = tmpz
                    if LEVEL == 1:
                        if remdis <= 0:
                            accuer = 0
                            update_loc(sname)
                except Exception as e:
                    g3err.append(time.ctime() + " GTCS-3: [To gtcs-2]" + str(e))
                    gtcs3_exit(2)
            else:
                extcmd = []
        except Exception as e:
            g3err.append(time.ctime() + " GTCS-3: [To gtcs-2]" + str(e))
            gtcs3_exit(2)
            extcmd = []
        try:
            if lkj_to_call:
                lkjcall(zugat)
        except Exception as e:
            g3err.append(time.ctime() + " GTCS-3: [To gtcs-2]" + str(e))
            gtcs3_exit(2)
        # Tackle with:
        # 1. Neutral area
        # 2. Speed limits
        # (for display, let gtcs loader tackle)
        if LEVEL >= 2:
            # print("Toggle#")
            try:
                u = urlopen(DCTR + "?sid=" + zugat + "&dev=" + str(int(accuer)) + "&spd=" + str(int(geschw)))
                su = u.read().decode('utf-8')
                u.close()
                sr = su.split(" ")
                sd = int(sr[0])
                if sd <= 0:
                    # lastspdlim = spdlim
                    accuer = 0
                    update_loc(sr[2])
                else:
                    spdlim = translate(sr[1])
                    if passing:
                        spdlim = PASSING_SPD
                    if sr[1] != former_signal or sr[2] != former_sid:
                        dif_warning = 5
                    former_sid = sr[2]
                    former_signal = sr[1]
                    if spdlim > ospeed:
                        light[1] = True
                    elif spdlim < ospeed:
                        light[1] = False
                    ospeed = spdlim
                    # Dynamic value already.
                    # if (zusatz_spdlim <= spdlim) or (zusatz_spdlim_at <= sd):
                    #    spdlim = zusatz_spdlim
                    #    sd = zusatz_spdlim_at
                    # 2s speed monitor, but acceleration here, unit: m/s^2
                    raw = accelreq(spdlim, sd)
                    for i in extcmd[1:]:
                        csp = i.split(" ")
                        dis = int(csp[0])
                        if csp[1] == "S":
                            if LEVEL >= 3:
                                cslim = translate(csp[3])
                                cac = accelreq(cslim, dis)
                                if cac < raw or (cac < 0 and abs(cac - raw) < 0.05 and dis < sd):
                                    raw = cac
                                    sd = dis
                                    spdlim = cslim
                        elif csp[1] == "La":
                            if (dis > 0):
                                cac = accelreq(int(csp[3]), dis)
                                if cac < raw or (cac < 0 and abs(cac - raw) < 0.05 and dis < sd):
                                    raw = cac
                                    sd = dis
                                    spdlim = int(csp[3])
                    # if sd > 3500:
                    #    raw = 0
                    clastspdlim = min(lastspdlim, zusatz_lastspdlim)
                    if passing:
                        spdlim = PASSING_SPD
                    if (curspeed > clastspdlim):
                        if (curspeed - clastspdlim > 80):
                            raw = min(raw, -12)
                            # contnz += 1
                        elif (curspeed - clastspdlim > 60):
                            raw = min(raw, -6)
                            # contnz += 0.5
                        else:
                            raw = min(raw, -4)
                            # contnz += 0.25
                    g3err.append(
                        time.ctime() + " GTCS-3: Raw acceleration " + str(round(raw, 2)) + ", with vacr = " + str(
                            round(acreqspd, 2)))
                    accreq = min(0, raw)
                    # acreqspd = curspeed + (max(0,caccel+0.2) * 3) + accreq * (2 / 3.6)
                    # acreqspd = curspeed + accreq * (2 * 3.6)
                    if acreqspd < 0:
                        acreqspd = 0
                    nextdist = sd
                    if zugat != sr[3]:
                        accuer = 1
                        update_loc(sr[3])
                try:
                    lkjcall(zugat)
                except Exception as e:
                    g3err.append(time.ctime() + " LKJ:" + str(e))
                    curlkj = "?"
                # print("Accumulate",accuer,nextdist)
            except Exception as e:
                g3err.append(time.ctime() + " GTCS-3: exiting due to" + str(e))
                gtcs3_exit()

        time.sleep(2)


def logclr():
    global GLOGGING, PLOGGING, g3err, plog, SCHUTZ_SIMU, SCHUTZ_PROB, failures, curspeed, cpsrc

    SCHUTZ_AFFAIR = ["Hilichurlwarnung", "Slimenwarnung", "Eisenbahnfaulwarnung", "Unerwartetelementwarnung",
                     "Abyssmagewarnung"]

    while True:
        if not GLOGGING:
            g3err = []
        if not PLOGGING:
            plog = []
        if SCHUTZ_SIMU:
            if not schutz:
                if random.randint(0, 1000) < SCHUTZ_PROB:
                    rc = random.choice(SCHUTZ_AFFAIR)
                    schutz_broadcast(rc)
                    if rc == "Unerwartetelementwarnung":
                        rw = random.choice(["ovldr", "scond", "eblock"])
                        failures[rw][1] = True
        if ((curspeed > 15) and (maxthr_val() < 10)) or (failures["thr"][1]):
            if cpsrc != "d":
                start_sound("thrust")
        for i in ["epwrlo", "epwrhi"]:
            if failures[i][2]():
                start_sound("volts")
        for i in ["epwrslo", "epwrshi"]:
            if failures[i][2]():
                start_sound("amps")
        time.sleep(5)


def befread():
    global g3err, BCTR, TCTR, AUTH, befehltext, befconf, ZUGNAME
    while True:
        try:
            u = urlopen(BCTR + "?auth=" + AUTH + "&mode=get&name=" + ZUGNAME)
            su = u.read().decode('utf-8').strip()
            u.close()
            moded = False
            if su != befehltext:
                befconf = False
                moded = True
                start_sound('caution')
            befehltext = su
            if befconf:
                befconf = False
                u = urlopen(BCTR + "?auth=" + AUTH + "&mode=confirm&name=" + ZUGNAME)
                u.close()
            if moded:
                befshow()
        except Exception as e:
            g3err.append(time.ctime() + " GTCS Befehl: " + str(e))
        submit_loc()
        time.sleep(2)


def gsmgmt():
    global failures, power, SCHUTZ_PROB, apress, evolts, eamps, cevolts, ceamps, efreq, sysinfo, syspages, csyspage, cpsrc, passdz, curspeed, caccel, thrust, spdlim, lastspdlim, zusatz_lastspdlim, curlkj, zugat, light, dif_warning, batvolts, batamps, batregen, servolts, onbat, battery_charge, geo_elem, cars, dendro_mass, pyro_temp
    s = open("blackbox_high_speed.csv", "a")
    ticker = 0
    while True:
        if random.randint(0, 350000) < SCHUTZ_PROB:
            if random.randint(0, 35000) < SCHUTZ_PROB:
                rf = random.choice(list(failures))
                failures[rf][1] = not failures[rf][1]
                if failures[rf][1] and (rf in sch_failure):
                    schutz_broadcast("Störung")
                for i in was_failure:
                    was_failure[i] = False
            else:
                # Get a carriage
                carid = random.randint(0, len(cars) - 1)
                carsel = cars[carid]
                rf = random.choice(list(carsel["failures"]["term"]))
                carsel["failures"]["term"][rf][1] = not carsel["failures"]["term"][rf][1]
                if carsel["failures"]["term"][rf][1]:
                    try:
                        carsel["failures"]["term"][rf][4](carsel)
                    except Exception as e:
                        print(str(e))
                    if (rf in carsel["failures"]["sch_failure"]):
                        schutz_broadcast("Störung")
                else:
                    try:
                        carsel["failures"]["term"][rf][5](carsel)
                    except Exception as e:
                        print(str(e))
                for i in carsel["failures"]["was_failure"]:
                    carsel["failures"]["was_failure"][i] = False
        # Failure effects
        if failures["thr"][1]:
            if power > 0:
                power -= min(power, 5)
        if failures["brk"][1]:
            if power < 0:
                power += min(-power, 5)
        if failures["apwrlo"][1]:
            if apress > 10:
                apress -= random.randint(10, 40) / 10
        if failures["apwrhi"][1]:
            if apress < 200:
                apress += random.randint(10, 40) / 10
        if failures["epwrlo"][1] or failures["eblock"][1]:
            if cevolts > 10:
                cevolts -= random.randint(10, 40) / 10
        if failures["epwrhi"][1] or failures["ovldr"][1]:
            if cevolts < 3000:
                cevolts += random.randint(10, 40) / 10
        if failures["epwrslo"][1] or failures["eblock"][1]:
            if ceamps > 0.1:
                ceamps -= random.randint(10, 40) / 10
        if failures["epwrshi"][1] or failures["scond"][1]:
            if ceamps < 100:
                ceamps += random.randint(10, 40) / 20
        if failures["bepwrlo"][1] or failures["eblock"][1]:
            if batvolts > 10:
                batvolts -= random.randint(10, 40) / 10
        if failures["bepwrhi"][1] or failures["ovldr"][1]:
            if batvolts < 3000:
                batvolts += random.randint(10, 40) / 10
        if failures["bepwrslo"][1] or failures["eblock"][1]:
            if batamps > 0.1:
                batamps -= random.randint(10, 40) / 10
        if failures["bepwrshi"][1] or failures["scond"][1]:
            if batamps < 100:
                batamps += random.randint(10, 40) / 20
        servolts = batvolts / 50
        if failures["depwrlo"][1] or failures["eblock"][1]:
            if servolts > 16:
                servolts -= random.randint(10, 40) / 10
        if failures["depwrhi"][1] or failures["ovldr"][1]:
            if servolts < 64:
                servolts += random.randint(10, 40) / 10
        if failures["geofail"][1]:
            if geo_elem > 0:
                geo_elem -= random.randint(8, 14) / 10
        if failures["pyrolo"][1]:
            if pyro_temp > 300:
                pyro_temp -= random.randint(30, 50) / 5
        if failures["pyrohi"][1]:
            if pyro_temp < 1100:
                pyro_temp += random.randint(30, 50) / 5
        if failures["denlo"][1]:
            if dendro_mass > 1.5:
                dendro_mass -= random.randint(30, 50) / 50
        if apress < anemo_bg:
            apress += random.randint(20, 30) / 10
        if cevolts < electro_vbg:
            cevolts += random.randint(40, 50) / 10
        if ceamps < electro_abg:
            ceamps += random.randint(40, 50) / 10
        if geo_elem < geo_bg:
            geo_elem += random.randint(11, 15) / 10

        sysinfo = []
        for i in syspages[csyspage]:
            sysinfo.append([i[0](), i[1]()])
        if cpsrc == "p":
            if passdz or (failures["panto1"][1] and failures["panto2"][1]):
                cevolts = 0
                ceamps = 0
            else:
                cevolts = 2500
                ceamps = 80
        if cevolts + 10 > batvolts:
            onbat = False
        elif cevolts + 20 < batvolts:
            onbat = True
            evolts = batvolts
            eamps = batamps
        if (not onbat):
            evolts = cevolts
            eamps = ceamps
            evolts += (random.randint(0, 10) - 5) / 10
            eamps += (random.randint(0, 10) - 5) / 50
            akpower = cevolts * ceamps
        else:
            akpower = evolts * eamps
        apress += (random.randint(0, 10) - 5) / 10
        if ceamps < 0.01:
            ceamps = 0.01
        if eamps < 0.01:
            eamps = 0.01
        batregen = False
        # Evaluate battery volts:
        if battery_charge < 0.01:
            battery_charge = 0.01
        batvolts = math.log(battery_charge*20000/MAX_BAT_CAPACITY, 2.3)*200
        batamps = (batvolts)/50 + (random.randint(-45,45)/100)
        chvolts = 20
        chvolts = ((power * 720)) / eamps
        if power < 0:
            resi = random.randint(170,205)
            eamps = (abs(power * 720) / resi)**0.5
            chvolts = -eamps * resi
        #print("pre;;chv=",chvolts,"ce:",cevolts,ceamps,"ev=",evolts,"ea=",eamps,onbat,batregen)
        if cpsrc in ("a", "d"):
            chvolts = 20
        if (cevolts < chvolts + 10) and (batvolts > 0):
            # Not so physics, I think
            #chvolts = (power * curspeed / 3.6 * 25) / batamps
            rate = (chvolts - cevolts) / batvolts
            evolts = chvolts
            eamps = ceamps + batamps * rate
            #print("Battery rate",rate)
            onbat = True
            battery_charge -= batamps * rate / 3600
        elif cevolts - chvolts > 20:
            onbat = False
            #batvolts = cevolts - chvolts - 20
            #evolts = cevolts - chvolts
            batamps = eamps
            batregen = True
            if (battery_charge < MAX_BAT_CAPACITY):
                if batvolts < 0:
                    batvolts = 2.5
                battery_charge += batamps * (cevolts - chvolts) / batvolts / 4000
            # 3600 with something else
        #print("aft;;chv=",chvolts,"ev=",evolts,"ea=",eamps,onbat,batregen)
        if apress < 0:
            apress = 0
        if evolts < 0:
            evolts = 0
        if eamps < 0:
            eamps = 0
        pmc = maxthr_val()
        if power > pmc:
            power -= min(power - pmc, random.randint(10, 30))
        # power = min(power, maxthr_val())
        try:
            if (ticker % 10) == 0:
                s.write(",".join(
                    [time.ctime(), str(round(curspeed, 2)), str(round(caccel / 3.6 * 5, 3)), str(round(thrust, 2)),
                     str(spdlim),
                     str(lastspdlim), str(zusatz_lastspdlim), curlkj, zugat, cpsrc, str(apress), str(evolts),
                     str(eamps), ",".join([str(i) for i in light])]))
                s.write("\n")
            if ticker > 50:
                ticker = 0
                s.flush()
            ticker += 1
        except:
            failures["logerr"][1] = True
        else:
            failures["logerr"][1] = False
        if curspeed <= 0.1 and power < 0:
            power = 0
        time.sleep(0.01)


def afb():
    global curspeed, spdlim, lastspdlim, zusatz_spdlim, zusatz_spdlim_at, zusatz_lastspdlim, accreq, thrust, caccel, has_afb, plog, LEVEL, nextdist
    # caccel: (km/h)/s, to be divided by 3.6
    while True:
        if has_afb:
            csmin = min(lastspdlim, zusatz_lastspdlim)
            if (LEVEL <= 1) or (nextdist < 2000):
                csmin = min(csmin, spdlim)
            if (LEVEL >= 3) and (zusatz_spdlim_at < 2000):
                csmin = min(csmin, zusatz_spdlim)
            acceldata = caccel * 5 / 3.6
            minperm = 0
            if LEVEL >= 2:
                if nextdist >= 150:
                    if nextdist <= 200:
                        minperm = 15
                    elif nextdist <= 500:
                        minperm = 25
                    elif nextdist <= 1000:
                        minperm = 40
            if (cpsrc in ("p", "e")) and (evolts > 3000 or eamps > 100):
                kdn(True)
                time.sleep(0.02)
            else:
                if (accreq >= 0) or (LEVEL > 1 and accreq > -0.05) or (((accreq > -1.35) and (curspeed < minperm - 5))):
                    # plog.append(time.ctime() + " AFB Level 1")
                    if (csmin - 10) - (curspeed) > 60:
                        if abs(acceldata - 1) > 0.05 or abs(thrust - 100) > 5:
                            if (acceldata < 1) and (thrust < 100):
                                kup(True)
                            elif (acceldata > 1.05) or (thrust > 105):
                                kdn(True)
                        time.sleep(0.02)
                    elif (curspeed < (csmin - 10)) or (curspeed < minperm - 5):
                        if ((acceldata < 0.5) and (thrust < 20)):
                            kup(True)
                        elif (acceldata > 0.55) or (thrust > 25):
                            kdn(True)
                        time.sleep(0.02)
                    elif (curspeed < csmin) and (curspeed > minperm):
                        if thrust <= -2:
                            kup(True)
                        elif thrust >= 2:
                            kdn(True)
                        time.sleep(0.02)
                    else:
                        if thrust > -10:
                            kdn(True)
                        elif thrust < -10:
                            kup(True)
                        time.sleep(0.05)
                elif (accreq < -0.1):
                    # plog.append(time.ctime() + " AFB Level 0")
                    if abs(acceldata - accreq) > 0.05:
                        if accreq < acceldata:
                            kdn(True)
                        elif accreq > acceldata + 0.05:
                            kup(True)
                    time.sleep(0.02)
                else:
                    # plog.append(time.ctime() + " AFB Level 2")
                    time.sleep(1)
        else:
            # plog.append(time.ctime() + " AFB not enabled")
            time.sleep(1)


def render_3d():
    global extcmd, RENDER, accuer, asuber, dif_warning
    #print("Render thread running")
    while True:
        try:
            curdata = str(int(accuer)) + " " + str(int(asuber)) + "\n" + "\n".join(extcmd)
            cd = curdata.encode('utf-8')
            req = request.Request(RENDER, cd)
            resp = request.urlopen(req)
            resp.close()
        except Exception as e:
            pass
        if dif_warning > 0:
            dif_warning -= 1
        time.sleep(0.2)


# turtle.right(90)
render_gtcs()
turtle.ontimer(render_gtcs_main, 100)
turtle.ontimer(physics, 200)
th = threading.Thread(target=console)
t3 = threading.Thread(target=gtcs3)
tl = threading.Thread(target=logclr)
tb = threading.Thread(target=befread)
tsh = threading.Thread(target=sound_thr)
tgs = threading.Thread(target=gsmgmt)
tab = threading.Thread(target=afb)
trd = threading.Thread(target=render_3d)
th.start()
t3.start()
tl.start()
tb.start()
tsh.start()
tgs.start()
tab.start()
trd.start()
turtle.mainloop()
# print(turtle.heading())
# input()
# render_bar()
