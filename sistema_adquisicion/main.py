# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 12:20:24 2024

@author: Elena Almanza García
"""
import serial
import serial.tools.list_ports

import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.animation import FuncAnimation

from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import os 
import time

# variables globales
lengthGraph = 100 # cantidad de datos graficada 
isOpen = False
allData = []
timeStamps = []
vData = []
aData = []
vGraph = []
aGraph = []
t = []

# -----------------------------Funciones--------------------------------------#
def serialPorts():
    global ports 
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        return ["NO_PUERTOS"]
    else:
        return [port.device for port in ports]

# función que verifica el COM al que estamos conectados
def onSelect(*args):
    
    #obtener la selección directamente desde comboboxes
    print("Seleccionado: ", cb.get())

# función de conexión que verifica si hay puertos o no
def conect():
    global ser, isOpen
    try:
        # configuración de los valores de paridad y bits de parada
        parity = {
            "Ninguno": serial.PARITY_NONE,
            "Impar": serial.PARITY_ODD,
            "Par": serial.PARITY_EVEN}.get(selectedParity.get(), serial.PARITY_NONE)
        
        stopbits = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO
            }.get(selectedStopbits.get(), serial.STOPBITS_ONE)
    
        if cb.get() == "NO_PUERTOS":
            messagebox.showerror("Error", "No se puedo conectar: no hay puertos disponibles")
            # print("No se puede conectar")
                 
        else:
            ser = serial.Serial(
                port = cb.get(),
                baudrate = int(selectedBaudrate.get()),
                bytesize = int(selectedBytesize.get()),
                parity = parity,
                stopbits = stopbits,
                timeout = 0.1
            )
            
            isOpen = True
            portConectBoton["state"] = "disabled"
            portDisconectBoton["state"] = "normal"
            messagebox.showinfo("Conexión exitosa", f"Conectado a {cb.get()}")
            
    except serial.SerialException as e:
        messagebox.showerror("Error de conexión", f"Sin dispositivo disponible para conexión {cb.get()}. Error: {str(e)}")

# función de desconexión, permite también cerrar el puerto en caso de que se necesite
def disconect():
    global ser, isOpen
    
    ser.close()
    isOpen = False
    portConectBoton["state"] = "normal"
    portDisconectBoton["state"] = "disabled"

# función que actualiza los puertos disponibles, y la reutilizamos también para hacer una nueva adquisición de datos
def refresh():
    global allData, vData, aData, vGraph, aGraph, y, t, startTime
    available = serialPorts() #puertos disponibles
    cb.set("") #limpiamos los puertos actuales
    cb.configure(values = available)
    
    # para la nueva adquisición se limpia la gráfica y las listas de datos
    lineDisp.set_ydata([np.nan] * lengthGraph)
    lineVel.set_ydata([np.nan] * lengthGraph)
    lineAcc.set_ydata([np.nan] * lengthGraph)

    allData = [] 
    vData = []
    aData = []
    vGraph = []   
    aGraph = []
    t = []
    y = np.zeros(lengthGraph)
    startTime = None
    
    # ponemos también las demás entradas por default
    selectedParity.set("Ninguno")
    selectedStopbits.set(1)
    selectedBaudrate.set(9600)
    selectedBytesize.set(8)
    
    displacement.set(False)
    velocity.set(False)
    acceleration.set(False)

# función que cambia las dimensiones de la gráfica
def changeVar(*args):
    yaMin = int(yAxis_min.get()) if (yAxis_min.get() != '' and yAxis_min.get() != '-') else 0
    yaMax = int(yAxis_max.get()) if yAxis_max.get() != '' else 1023
    ax.set_ylim(yaMin, yaMax)
    
    if displayInVoltage.get():
        yaMax = 5
        ax.set_ylim(yaMin, yaMax)
        
    canvas.draw() # redibujamos la gráfica

# función para ocultar o mostrar las lineas de la gráfica aún después de terminar la adquisición
def showLines(*args):
    if len(vGraph) > 1 and len(aGraph) > 1:
        if displacement.get():
            lineDisp.set_ydata(y)
        else:
            lineDisp.set_ydata([np.nan]*lengthGraph)  # oculta la línea si está desactivada
    
        if velocity.get():
            lineVel.set_ydata(vGraph)
        else:
            lineVel.set_ydata([np.nan]*lengthGraph)
    
        if acceleration.get():
            lineAcc.set_ydata(aGraph)
        else:
            lineAcc.set_ydata([np.nan]*lengthGraph)

# función que adjusta las dimensiones de las listas para poder graficar
def adjustLength(data, length = lengthGraph):
    # si la lista es más larga que el obtejetivo (length), recortar
    if len(data) > length:
        return data[-length:]
    
    # si la lista es más corta que el objetivo, rellenar con NaN
    elif len(data) < length:
        return [np.nan] * (length - len(data)) + data
    
    return data

# función para calcular las derivadas usando la diferencia finita
def derivate(data, time):
    if len(data) < 2:
        return None
    
    dy = data[-1] - data[-2]
    dt = time[-1] - time[-2]
    
    return dy/dt if dt != 0 else 0

# función que adquiere los datos y los alamcena en listas para poder graficarlos
startTime = None
def acquisition():
    global startTime, data, rawData
    if isOpen:
        if startTime is None:
            startTime = time.perf_counter()
        
        data = ser.readline().decode('ascii').strip() # lectura de datos recibidos
        rawData = float(data) if data != '' else 0
        newTime = time.time()
        timeStamps.append(newTime)
        t.append((time.perf_counter() - startTime))
               
# función para actualizar la gráfica según los datos de desplazamiento, velocidad y aceleración    
def updatePlot(frame):
    if isOpen:      
        global y, data, rawData, timeStamps
        acquisition()
        
        # revisar si se muestra en bits o en voltaje
        if displayInVoltage.get():
            voltage = (rawData/1023)*5  #conversión a voltaje, considerando un rango de 0 a 5V
            allData.append(voltage)
            y[-1] = float(voltage) if data.isdigit() else 0
        else:
            allData.append(rawData)
            y[-1] = float(rawData) if data.isdigit() else 0
        
        # calculamos la velocidad
        v = derivate(allData, timeStamps)
        if v is not None:
            vData.append(v)
            
        # calculamos acelración 
        if len(vData) > 1:
            vTimeStamps = timeStamps[-len(vData):]  # recorta el tiempo solo para los valores de vData
            a = derivate(vData, vTimeStamps)
            if a is not None:
                aData.append(a)
        
        time.sleep(0.002)
        
        y[:-1] = y[1:]
        vGraph[:] = adjustLength(vData)
        aGraph[:] = adjustLength(aData)
        
        showLines()
        
    return lineDisp, lineVel, lineAcc

# función para guardar los datos adquiridos es un archivo csv
def saveCsv():
    # pedimos al usuario el nombre de archivo 
    filePath = filedialog.asksaveasfilename(initialfile = "acquisition.csv",
                                            defaultextension = ".csv",
                                            filetypes = [("CSV files", "*.csv")],
                                            title = "Guardar archivo")
    if filePath:
        # creamos el data frame y guardamos los datos
        dataList = np.array([t[:-2], allData[:-2], vData[:-1], aData]).T 
        head = ["time", "displacement", "velocity", "acceleration"] # encabezado de las columnas del dataframe
        df = pd.DataFrame(dataList, columns = head) 
        df.to_csv(filePath, index = False)
        messagebox.showinfo("Éxito", "Datos guardados correctamente.")
    
    if not filePath:
        return
    
    
# ------------------------------- App frame --------------------------------- #
root = ctk.CTk()
root.title("Análisis dinámico")
root.geometry("1020x700") # tamaño de la ventana de la interfaz
root.configure(fg_color = "#17161b") # color de fondo 
root.grid_columnconfigure(0, weight = 1) # centrado
root.grid_columnconfigure(1, weight = 1)
root.grid_columnconfigure(2, weight = 1)
root.grid_rowconfigure(1, weight = 1)
# root.resizable(0, 0) # impide la redimensión de la ventana de la interfaz


# ------------------------ Barra de herramientas ---------------------------- #
toolbar = tk.Frame(root, bg = "gray")
toolbar.grid(row = 0, column = 0, sticky = "w")

icon = Image.open("refresh.png")
icon = icon.resize((15, 15))
icon = ImageTk.PhotoImage(icon)

refreshButton = tk.Button(toolbar, image = icon, command = refresh, bg = "gray")
refreshButton.grid(row = 0, column = 0)

# --------------------------------Encabezado--------------------------------- #
headFrame = ctk.CTkFrame(root)
headFrame.configure(fg_color = "#17161b")
headFrame.grid(sticky = "nsew", pady = (0, 0))
headFrame.grid_columnconfigure(0, weight = 1)
headFrame.grid_columnconfigure(1, weight = 1)
headFrame.grid_columnconfigure(2, weight = 1)

imagePath = "logoEnes.png"
image = ctk.CTkImage(light_image = Image.open(imagePath), dark_image = Image.open(imagePath), size = (80, 131))
imageLabel = ctk.CTkLabel(headFrame, image = image, text = "")
imageLabel.grid(row = 0, column = 0, sticky = "nsew")

titleLabel = ctk.CTkLabel(headFrame, text = "Análisis Dinámico", font = ("Arial", 25, "bold"), text_color = "white")
titleLabel.grid(row = 0, column = 1, sticky = "nsew")

imagePath = "logoTecno.png"
image = ctk.CTkImage(light_image = Image.open(imagePath), dark_image = Image.open(imagePath), size = (153, 50))
imageLabel = ctk.CTkLabel(headFrame, image = image, text = "")
imageLabel.grid(row = 0, column = 2, sticky = "nsew")


# ----------------------- Comunicación Serial ------------------------------- #
# frame para organizar los widgets relacionados a la comunicación y puerto serial
frame = ctk.CTkFrame(root, corner_radius = 10, fg_color = "#17161b")
frame.grid(padx = 10, pady = 0)

serialFrame = ctk.CTkFrame(frame, corner_radius = 10, fg_color = "gray20")
serialFrame.grid(padx = 10, pady = 10)

titleSerialFrame = ctk.CTkLabel(serialFrame, corner_radius = 10, text = "Comunicación Serial", font = ("Arial", 14, "bold"))
titleSerialFrame.grid(row = 1, column = 0, padx = 10, pady = (0, 10))

# Puertos
selectPort = tk.StringVar()
portNameLabel = ctk.CTkLabel(serialFrame, text = "Puertos COM")
portNameLabel.grid(row = 2, column = 0, padx = 10)
cb = ctk.CTkComboBox(serialFrame, values = serialPorts(), variable = selectPort) # mostramos los puertos seriales disponibles
cb.grid(row = 3, column = 0, padx = 10, pady = (0, 10))
selectPort.trace_add("write", onSelect)

# Velocidad de envío de datos
baudNameLabel = ctk.CTkLabel(serialFrame, text = "Baudrate")
baudNameLabel.grid( row = 4, column = 0, padx = 10)
selectedBaudrate = ctk.CTkComboBox(serialFrame, values = ["9600", "19200", "38400", "57600", "115200"])
selectedBaudrate.set(9600)  # Configura el valor inicial a 9600
selectedBaudrate.grid(row = 5, column = 0, padx = 10, pady = (0, 10))

# Tamaño de bits de datos
bitsNameLabel = ctk.CTkLabel(serialFrame, text = "Bits de Datos")
bitsNameLabel.grid(row = 6, column = 0, padx = 10)
selectedBytesize = ctk.CTkComboBox(serialFrame, values=["5", "6", "7", "8"])
selectedBytesize.set(8)
selectedBytesize.grid(row = 7, column = 0, padx = 10, pady = (0, 10))

# Paridad
paridadNameLabel = ctk.CTkLabel(serialFrame, text = "Paridad")
paridadNameLabel.grid(row = 8, column = 0, padx = 10)
selectedParity = ctk.CTkComboBox(serialFrame, values=["Ninguno", "Impar", "Par"])
selectedParity.set("Ninguno")
selectedParity.grid(row = 9, column = 0, padx = 10, pady = (0, 10))

# Bits de parada
stopBitsNameLabel = ctk.CTkLabel(serialFrame, text = "Bits de Parada")
stopBitsNameLabel.grid(row = 10, column = 0, padx = 10)
selectedStopbits = ctk.CTkComboBox(serialFrame, values=["1", "1.5", "2"])
selectedStopbits.set(1)
selectedStopbits.grid(row = 11, column = 0, padx = 10, pady = (0, 20))

# Botones de conexión
portConectBoton = ctk.CTkButton(serialFrame, 
                                text = "INICIO", 
                                command = conect, 
                                text_color = "white", 
                                fg_color = "gray")
portConectBoton.grid(row = 12, column = 0, padx = 10, pady = (0, 10))


portDisconectBoton = ctk.CTkButton(serialFrame, 
                                text = "PARO", 
                                command = disconect, 
                                text_color = "white", 
                                fg_color = "gray")
portDisconectBoton.grid(row = 13, column = 0, padx = 10, pady = (0, 10))

# --------------------------------- Check Boxes ----------------------------- #
# Asignar la función de actualización a cada variable de los checkboxes
displacement = tk.BooleanVar()
velocity = tk.BooleanVar()
acceleration = tk.BooleanVar()

checkFrame = ctk.CTkFrame(frame, corner_radius = 10, fg_color = "gray20")
checkFrame.grid(row = 0, column = 3, padx = 10, pady = (0, 100))

displacementCheck = ctk.CTkCheckBox(checkFrame, 
                                    text = "Desplazamiento", 
                                    variable = displacement)
displacementCheck.grid(row = 0, column = 3, padx= 10, pady = (10, 0))
displacement.trace_add('write', showLines)


velocityCheck = ctk.CTkCheckBox(checkFrame, 
                                text = "Velocidad", 
                                variable = velocity)
velocityCheck.grid(row = 1, column = 3, padx = 10)
velocity.trace_add('write', showLines)

accelerationCheck = ctk.CTkCheckBox(checkFrame, 
                                    text = "Aceleración", 
                                    variable = acceleration)
accelerationCheck.grid(row = 2, column = 3, padx = 10, pady = (0, 10))
acceleration.trace_add('write', showLines)

# ----------------------- Radio botón para la resolución ---------------------- #
radioFrame = ctk.CTkFrame(frame, corner_radius = 10, fg_color = "gray20")
radioFrame.grid(row = 0, column = 3, padx = 10, pady = (200, 0))

titleRadioFrame = ctk.CTkLabel(radioFrame, corner_radius = 10, text = "Resolución", font = ("Arial", 12, "bold"))
titleRadioFrame.grid(row = 1, column = 3, padx = 10, pady = 0)

displayInVoltage = tk.BooleanVar()

bitsCheck = ctk.CTkRadioButton(radioFrame,
                               text = "Bits", 
                               variable = displayInVoltage,
                               value = False)
bitsCheck.grid(row = 4, column = 3, padx = 10, pady = 0)

# Crear un Checkbutton para que el usuario elija la visualización
voltCheck = ctk.CTkRadioButton(radioFrame,
                               text = "Volataje", 
                               variable = displayInVoltage,
                               value = True)
voltCheck.grid(row = 5, column = 3, padx = 10, pady = (0, 10))  # Ajusta la posición según tu diseño
displayInVoltage.trace_add('write', changeVar)

# -------------------------Botón para guardar CSV --------------------------- #
csvBoton = ctk.CTkButton(frame, 
                                text = "GUARDAR", 
                                command = saveCsv, 
                                text_color = "white", 
                                fg_color = "gray")
csvBoton.grid(row = 1, column = 3)

# ----------------------- Botón para nueva adquisición ---------------------- #
csvBoton = ctk.CTkButton(frame, 
                                text = "NUEVA ADQUISICIÓN", 
                                command = refresh, 
                                text_color = "white", 
                                fg_color = "gray")
csvBoton.grid(row = 1, column = 0)

# ----------------------- Configuración del ráfico -------------------------- #
#frame para acomodar las variables que cambian las dimensiones de la gráfica
axisFrame = ctk.CTkFrame(frame)
axisFrame.grid(row = 1, column = 1, padx = 10, pady = 0)

# variables de entrada que el usuario puede cambiar para personalizar las dimesiones del gráfico en el eje y
yAxis_min = tk.StringVar()
yMinAxisNameLabel = ctk.CTkLabel(axisFrame, text = "y_min", font = ("Arial", 12, "bold"))
yMinAxisNameLabel.grid(row = 0, column = 0)
yAxis_minEntry = ctk.CTkEntry(axisFrame, textvariable = yAxis_min, width = 60)
yAxis_minEntry.grid(row = 1, column = 0, padx = 10)
yAxis_min.trace_add('write', changeVar)

yAxis_max = tk.StringVar()
yMaxAxisNameLabel = ctk.CTkLabel(axisFrame, text = "y_max", font = ("Arial", 12, "bold"))
yMaxAxisNameLabel.grid(row = 0, column = 1)
yAxis_maxEntry = ctk.CTkEntry(axisFrame, textvariable = yAxis_max, width = 60)
yAxis_maxEntry.grid(row = 1, column = 1, padx = 10)
yAxis_max.trace_add('write', changeVar)

# creamos la figura matplotlib
fig = plt.figure(figsize = (8, 4))
fig.set_facecolor("#17161b")
ax = plt.axes()
ax.set_facecolor("#17161b")
ax.title.set_color('white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.grid(alpha = 0.1)
ax.tick_params(axis = 'x', colors = 'white')
ax.tick_params(axis = 'y', colors = 'white')

x = np.arange(lengthGraph)
y = np.zeros(lengthGraph)

# creamos una línea para cada checkbox
lineDisp, = ax.plot(x, y, label = "Desplazamiento", color = 'orange')
lineVel, = ax.plot(x, np.zeros(lengthGraph), label = "Velocidad", color = 'blue')
lineAcc, = ax.plot(x, np.zeros(lengthGraph), label = "Aceleración", color = 'red')

ax.legend()
  
plt.axis([0, lengthGraph, 0, 1023])
plt.ylabel('Valor Lectura')
plt.title('Serial COM Data')

canvas = FigureCanvasTkAgg(fig, master = frame)
canvas.draw() 
canvas.get_tk_widget().grid(row = 0, column = 1, pady = 0, sticky = "nsew")

# función para mostrar el gráfico
animation = FuncAnimation(fig, updatePlot, frames = lengthGraph, interval = 50, blit = True)

root.mainloop()