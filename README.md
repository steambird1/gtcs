# README

Welcome to **GTCS Prototype**!

This repository provides a prototype for GTCS (**G**eneral **T**rain (as well as Fountaine Cruise) **C**ontrol **S**ystem) used in Teyvat (can also be considered **G**unnhildr **T**rain **C**ontrol **S**ystem).

## Why GTCS?

GTCS is used to unify complicated diverse train control systems in Teyvat, such as:

- LKJ in Liyue;
- PZB/LZB in Mondstadt;
- TVM in Fountaine; etc.

GTCS has been ensuring safety and efficiency of Teyvat railway systems.

## Installation

### Client Side

Client-side (i.e., train devices) doesn't require any additional packages. Only python (with GUI) and network connection (port 5033 should be available) is needed.

### Server Side

Server-side (i.e., train control center devices) requires Flask module and PIL module for full functions, which can be installed through following commands after installing Python:

```sh
pip install flask
pip install pillow
```

For Microsoft Windows, **Ghostscript** is necessary for full functions. Its installation requires rebooting.

**Special reminder after installation:** Please change the password in the `server.py` file (and update them in clients as well!)

**Update:** Now pillow and ghostscript are only reserved for traditional status display. For server, no GUI is compulsory. To remove GUI to distribute it on your server (you should read *Installation* part as well), delete following code:

```python
import turtle
#...
def update_signal(name,ovrd=None):
    #... (Delete all code in this function)
#...
@app.route("/state")
def state():
    # Fill some error messages you want. For example:
    return "Unsupported method for this server, please use dashboard.html instead!", 400
#...
turtle.speed("fastest")
turtle.delay(0)
turtle.pensize(8)
#...
def imgupd():
    #... (Delete all code in this function)
if __name__ == '__main__':
    for i in signals:
        scan_signal(i)
        break
    #...
    turtle.ontimer(imgupd, 1000)
    turtle.mainloop()
```

### Special Installation

If you don't have a server, you can look for a TinyWebDB service and use it by running `server_transition.py` and client at the same time. **Notice that permission control won't work in this case, so don't use it for productive environment (although I guess there won't be anyone doing so...)**

## Usage

For usage, refer to User Manual RTF File and Wiki pages (coming soon).

