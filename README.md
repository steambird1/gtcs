# README

Welcome to **GTCS Prototype**!

~~It's due to my limited English skill that I named it in this way. I should have called it a model.~~

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

**Update:** Now traditional renders based on turtle has been removed (except for the first-run render) for efficiency issues.

### Special Installation

**Update:** The `server_transition.py` is no longer supported, since it's *so* difficult to sync all data of it. You may have to turn to old versions.

## Usage

For usage, refer to User Manual RTF File and Wiki pages (coming soon).

