'''
A gas-path smoothing tool using B-spline curves
First B-spline curves are created fitting the given coordinates
Then, the user can adjust control points to modify these curves
'''

import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import style
from matplotlib.gridspec import GridSpec

import utility as util

import os
import re
import itertools
from itertools import cycle

style.use("default") # default, bmh, ggplot

class GasPathSmoother(tk.Tk):
  def __init__(self, *args, **kwargs):
    tk.Tk.__init__(self, *args, **kwargs)
    self.wm_title("Gas Path Smoothing Tool")

    container = tk.Frame(self)
    container.pack(side="top", fill="both", expand=True)
    frame = GasPath(container, self)
    frame.pack(side="top", fill="both", expand=True)
    frame.tkraise()

class GasPath(tk.Frame):
  def __init__(self, parent, controller):
    tk.Frame.__init__(self, parent)

    menubar = tk.Menu(self)
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Read Input", command=self.read_data)
    menubar.add_cascade(label="File", menu=filemenu)
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Hide Control Points", command=self.hide_controlPoints)
    filemenu.add_command(label="Show Control Points", command=self.show_controlPoints)
    filemenu.add_command(label="Hide Data Points", command=self.hide_dataPoints)
    filemenu.add_command(label="Show Data Points", command=self.show_dataPoints)
    menubar.add_cascade(label="View", menu=filemenu)
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Out to File", command=self.out)
    menubar.add_cascade(label="Output", menu=filemenu) 
    tk.Tk.config(controller, menu=menubar)

    self.fig = Figure()
    gs = GridSpec(1, 2, figure=self.fig, hspace=0.3, wspace=0.2)
    self.fig.subplots_adjust(left=0.08, right=0.95, top=0.9, bottom=0.1)
    self.ax = self.fig.add_subplot(gs[0, 0])
    self.ax.set_title("Gas Path")
    self.ax.set_xlabel("x [mm]")
    self.ax.set_ylabel("y [mm]")

    self.ax2 = self.fig.add_subplot(gs[0, 1])
    self.ax2.set_title("Curvature")

    self.canvas = FigureCanvasTkAgg(self.fig, self)
    self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(self.canvas, self)
    toolbar.update()
    self.canvas._tkcanvas.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    self.canvas.mpl_connect('button_press_event', self.on_press)
    self.canvas.mpl_connect('motion_notify_event', self.on_motion)
    self.canvas.mpl_connect('button_release_event', self.on_release)

    self.canvas.draw()

    self.p = 3 # Order of B-spline curves
    self.nC = 5 # Number of control points

    self.uk = []
    for i in range(self.p+1):
      self.uk.append(0)
    for i in range(self.nC-self.p-1):
      self.uk.append((i+1)/(self.nC-self.p))
    for i in range(self.p+1):
      self.uk.append(1)

    self.dataPlots = []
    self.controlBsPlots = []
    self.curveBsPlots = []   
    self.curvaturePlots = []
  
  def read_data(self):
    self.data = {}

    path = os.getcwd()
    filename = askopenfilename(initialdir=path, title="Select file")
    with open(filename,'r') as f:
      lines = [l for l in (line.strip() for line in f) if l]
      for eachLine in lines:
        lineContent = re.split(r'\s+', eachLine)
        if (lineContent[0] == 'label'):
          lab = lineContent[1]
          self.data[lab.strip()] = {"x" : [], "y" : []}
        else:
          self.data[lab.strip()]["x"].append(float(lineContent[0]))
          self.data[lab.strip()]["y"].append(float(lineContent[1]))

    self.update_data()
  
  def update_data(self):
    colors = cycle('brgcmk')
    for key in self.data:
      self.data[key]["marker_size"] = 20
      self.data[key]["is_moveable"] = False
      self.data[key]["is_active"] = [False for x in self.data[key]["x"]]
      self.data[key]["color"] = next(colors)

    self.clear_canvas()

    for key, group in self.data.items():
      self.dataPlots.append(self.ax.scatter(group["x"], group["y"], c=group["color"],
              s = group["marker_size"], marker = "*", label = key))

    handles, labels = self.ax.get_legend_handles_labels()
    self.ax.legend(self.flip(handles, 18), self.flip(labels, 18), 
                        bbox_to_anchor=(0, 1.08, 1, 1.08), loc=3,
                        ncol=18, borderaxespad=0, prop={'size': 6}, shadow=True)

    self.BsplineFit()

    for group in self.controlBs.values():
      self.controlBsPlots.append(self.ax.scatter(group["x"], group["y"],
        c = group["color"], s = group["marker_size"], marker = "s", alpha = 1))

    self.Bspline()

    for key, group in self.curveBs.items():
      self.curveBsPlots.append(self.ax.plot(group["x"], group["y"],
        color=group["color"], linewidth=group["LineWidth"])[0])  

    for key, group in self.curvature.items():
      self.curvaturePlots.append(self.ax2.plot(group["x"], group["y"],
        color=group["color"], linewidth=group["LineWidth"])[0]) 

    maxX = -1e100
    maxY = -1e100
    minX = 1e100
    minY = 1e100
    for group in self.data.values():
      maxX = max(maxX, max(group["x"]))
      maxY = max(maxY, max(group["y"]))
      minX = min(minX, min(group["x"]))
      minY = min(minY, min(group["y"]))
    for group in self.controlBs.values():
      maxX = max(maxX, max(group["x"]))
      maxY = max(maxY, max(group["y"]))
      minX = min(minX, min(group["x"]))
      minY = min(minY, min(group["y"]))

    extraX = (maxX-minX)*0.1
    extraY = (maxY-minY)*0.1
    self.ax.set_xlim(minX-extraX, maxX+extraX)
    self.ax.set_ylim(minY-extraY, maxY+extraY)

    maxX = -1e100
    maxY = -1e100
    minX = 1e100
    minY = 1e100
    for group in self.curvature.values():
      maxX = max(maxX, max(group["x"]))
      maxY = max(maxY, max(group["y"]))
      minX = min(minX, min(group["x"]))
      minY = min(minY, min(group["y"]))

    extraX = (maxX-minX)*0.1
    extraY = (maxY-minY)*0.1
    self.ax2.set_xlim(minX-extraX, maxX+extraX)
    self.ax2.set_ylim(minY-extraY, maxY+extraY)

    self.canvas.draw()

  def clear_canvas(self):
    for plot in self.dataPlots:
      plot.remove()
    for plot in self.controlBsPlots:
      plot.remove()
    for plot in self.curveBsPlots:
      plot.remove()
    for plot in self.curvaturePlots:
      plot.remove()
    self.dataPlots = []
    self.controlBsPlots = []
    self.curveBsPlots = []
    self.curvaturePlots = []

  def on_press(self, e):
    try:
      if e.inaxes:
        done = False
        for group in self.controlBs.values():
          if group["is_moveable"]:
            for index, (value1, value2) in enumerate(zip(group["x"], group["y"])):
              group["is_active"][index] = self.is_mouse_over(e, value1, value2)
              if self.is_mouse_over(e, value1, value2):
                done = True
                break
            if done:
              break
        self.update_plot()
    except:
      pass

  def on_motion(self, e):
    try:
      if e.inaxes:
        for group in self.controlBs.values():
          group["x"] = [e.xdata if group["is_active"][index] else value 
                      for index, value in enumerate(group["x"])]
          group["y"] = [e.ydata if group["is_active"][index] else value 
                      for index, value in enumerate(group["y"])]  
      else:
        for group in self.controlBs.values():
          group["is_active"] = [False for value in group["is_active"]]
      self.update_plot()
    except:
      pass

  def on_release(self, e):
    try:
      for group in self.controlBs.values():
        group["is_active"] = [False for value in group["is_active"]]
    except:
      pass

  def update_plot(self):
    self.Bspline()

    for index, group in enumerate(self.controlBs.values()):
      marker_size = [group["marker_size"]*3 if value 
                else group["marker_size"] for value in group["is_active"]] 
      self.controlBsPlots[index].set_offsets(self.transpose([group["x"], group["y"]])) 
      self.controlBsPlots[index].set_sizes(marker_size)    

    for index, group in enumerate(self.curveBs.values()):
      self.curveBsPlots[index].set_xdata(group["x"])
      self.curveBsPlots[index].set_ydata(group["y"])

    for index, group in enumerate(self.curvature.values()):
      self.curvaturePlots[index].set_xdata(group["x"])
      self.curvaturePlots[index].set_ydata(group["y"])

    self.canvas.draw()

  def hide_controlPoints(self):
    for plot in self.controlBsPlots:
      plot.set_visible(False)
    self.update_plot()

  def show_controlPoints(self):
    for plot in self.controlBsPlots:
      plot.set_visible(True)
    self.update_plot() 

  def hide_dataPoints(self):
    for plot in self.dataPlots:
      plot.set_visible(False)
    self.update_plot()

  def show_dataPoints(self):
    for plot in self.dataPlots:
      plot.set_visible(True)
    self.update_plot()

  def out(self):
    with open("outfile.txt",'w') as f:
      for key, group in self.curveBs.items():
        f.writelines(key+"\n")
        for x, y in zip(group["x"], group["y"]):
          f.writelines(str(format(x,'.5f'))+", "+str(format(y,'.5f')))
          f.writelines("\n")

        f.writelines("\n")

  def is_mouse_over(self, e, x, y):
    if e.inaxes:
      if (abs(x-e.xdata)<0.01*e.inaxes.viewLim.width and
          abs(y-e.ydata)<0.01*e.inaxes.viewLim.height):
        return True
      else:
        return False
    else:
      return False

  def transpose(self, m):
    return [[m[j][i] for j in range(len(m))] for i in range(len(m[0]))]

  def flip(self, items, ncol):
    return itertools.chain(*[items[i::ncol] for i in range(ncol)])

  def BsplineFit(self):
    self.controlBs = {}

    for key in self.data:
      self.controlBs[key] = {}

    for key, group in self.data.items():
      self.controlBs[key]["x"] = util.BsplineFit(group["x"],self.nC,self.p,self.uk)
      self.controlBs[key]["y"] = util.BsplineFit(group["y"],self.nC,self.p,self.uk)

    colors = cycle('brgcmk')
    for key in self.data:
      self.controlBs[key]["color"] = next(colors)
      self.controlBs[key]["marker_size"] = 20
      self.controlBs[key]["is_moveable"] = True
      self.controlBs[key]["is_active"] = [False for x in self.controlBs[key]["x"]]
 
  def Bspline(self):
    self.curveBs = {}
    self.curvature = {}

    for key in self.data:
      self.curveBs[key] = {}
      self.curvature[key] = {}

    for key in self.data.keys():
      dummy =  util.Bspline(100, self.controlBs[key], self.p, self.uk)
      self.curveBs[key]["x"] = dummy["x"]
      self.curveBs[key]["y"] = dummy["y"]
      self.curvature[key]["x"] = dummy["x"]

    for key in self.data.keys():
      cQ = {"x": [], "y": []}
      for i in range(self.nC-1):
        cQ["x"].append(self.p*(self.controlBs[key]["x"][i+1]-self.controlBs[key]["x"][i])/
                              (self.uk[i+self.p+1]-self.uk[i+1]))
        cQ["y"].append(self.p*(self.controlBs[key]["y"][i+1]-self.controlBs[key]["y"][i])/
                              (self.uk[i+self.p+1]-self.uk[i+1]))
        
      ukFirstDer = self.uk[1:-1]
      pFirstDer = self.p-1

      cT = {"x": [], "y": []}
      for i in range(self.nC-2):
        cT["x"].append(pFirstDer*(cQ["x"][i+1]-cQ["x"][i])
                          /(ukFirstDer[i+pFirstDer+1]-ukFirstDer[i+1]))
        cT["y"].append(pFirstDer*(cQ["y"][i+1]-cQ["y"][i])
                          /(ukFirstDer[i+pFirstDer+1]-ukFirstDer[i+1]))   

      curveBsFirstDer = util.Bspline(100, cQ, self.p-1, self.uk[1:-1])
      curveBsSecondDer = util.Bspline(100, cT, pFirstDer-1, ukFirstDer[1:-1])

      self.curvature[key]["y"] = [abs(xp*ypp-yp*xpp)/((xp**2+yp**2)**1.5) for (xp, yp, xpp, ypp) in
        zip(curveBsFirstDer["x"], curveBsFirstDer["y"], curveBsSecondDer["x"], curveBsSecondDer["y"])]

    colors = cycle('brgcmk')
    for key in self.data:
      color = next(colors)
      self.curveBs[key]["color"] = color
      self.curvature[key]["color"] = color
      self.curveBs[key]["LineWidth"] = 1
      self.curvature[key]["LineWidth"] = 1

BezierApp = GasPathSmoother()
BezierApp.geometry("1280x720")
BezierApp.minsize(720,720)
BezierApp.mainloop()
