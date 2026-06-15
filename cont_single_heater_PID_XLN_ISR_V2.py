# -*- coding: utf-8 -*-
"""
Created on Mon Oct 16 13:57:54 2017

@author: J. Ulbrandt, K Shepherd
Edited on 2025/03/31

GUI to run a single heater power supply and thermocouple
"""

import numpy as np
import time
import datetime
import tkinter as tk
import matplotlib.pyplot as plt

#import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# import equipment modules
import mod_thermocouple as therm
import mod_XLN3640 as xln

# import PID module
import mod_PID_ISR as pid


# plot config
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['lines.linewidth'] = 1
plt.rcParams['axes.labelsize'] = 10 
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['black'])
plt.rcParams['lines.markersize'] = 2

figsize_x = 5
figsize_y = 3

class PID_Display(tk.Frame):
    """ Class for PID display """

    def __init__(self,master, name, Data):
        tk.Frame.__init__(self, master)
        self.master = master
        self.name = name
        self.Data = Data
        self.remaining_time = 5*60 # initial countdown value min. The total preheat time from past runs (2025_01_17 TTIP XPOSE 12 excel sheet)
        init_min = self.remaining_time // 60
        init_sec = self.remaining_time % 60
        init_time_string = f'{init_min:02d}:{init_sec:02d}'
        
        #################
        ### Variables ###
        #################
        self.Mode_Display = tk.StringVar(master)  # Message On Mode Enable Button
        self.Status_Display = tk.StringVar(master)  # Message On Mode Status Display
        self.Status_Color = tk.StringVar(master)  # Color of mode status indicator
        self.sp_entry = tk.DoubleVar(master, Data.pid_vars['desired_sp'].get())  # entry box D_SP textvariable
        self.r_entry = tk.DoubleVar(master, Data.pid_vars['rate'].get())  # entry box ramp rate textvariable
        self.p_entry = tk.DoubleVar(master, Data.pid_vars['Kp'].get())  # entry box P textvariable
        self.i_entry = tk.DoubleVar(master, Data.pid_vars['Ki'].get())  # entry box I textvariable
        self.d_entry = tk.DoubleVar(master, Data.pid_vars['Kd'].get())  # entry box D textvariable
        self.timer_entry = tk.StringVar(master, init_time_string)
        self.plot_limits = tk.StringVar(master, 'full')  # for radio buttons in plot window
        self.plot_dt = tk.IntVar(master, 10) # plot delta time for scroll option
        
        # Auto - Manual Mode display status
        if Data.pid_vars['mode'].get() == 0:
            self.Mode_Display.set('Switch to Auto')
            self.Status_Display.set('Manual Mode')
            self.Status_Color.set('red')
        else:
            self.Mode_Display.set('Switch to Manual')
            self.Status_Display.set('Auto Mode')
            self.Status_Color.set('green')
    
        ####################
        ### Plot Display ###
        ####################
        self.Plot_Frame = tk.Frame(master)
        self.Plot_Frame.grid(row=0,column=0,padx=10,pady=10)
        
        self.f = Figure(figsize=(figsize_x, figsize_y))
        self.ax = self.f.add_subplot(111)
        self.ax.set_xlabel('Time (minutes)')
        self.ax.set_ylabel('Set-Points (C)')
        self.ax.grid(alpha=0.3)
        
        self.D_SP_plot, = self.ax.plot(self.Data.time_list,self.Data.D_SP_list,'ko-', label='Desired SP')
        self.A_SP_plot, = self.ax.plot(self.Data.time_list,self.Data.A_SP_list,'bo-', label='Actual SP')
        self.ax.legend(loc='best')
        
        self.canvas = FigureCanvasTkAgg(self.f, self.Plot_Frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0,column=0,columnspan=4,padx=10,pady=5)
        
        self.Radio_Full = tk.Radiobutton(self.Plot_Frame,text='Full Time',variable=self.plot_limits,value='full')
        self.Radio_Full.grid(row=1, column=0, padx=5)
        self.Radio_dt = tk.Radiobutton(self.Plot_Frame,text='Delta T',variable=self.plot_limits,value='dt')
        self.Radio_dt.grid(row=1,column=1)
        self.Radio_Combo = tk.OptionMenu(self.Plot_Frame,self.plot_dt,10,20,30,40,60,120)
        self.Radio_Combo.grid(row=1,column=2)
        self.Radio_Label = tk.Label(self.Plot_Frame,text='minutes').grid(row=1,column=3,padx=5)
    
        
        ####################
        ### Mode Display ###
        ####################
        self.M_Frame = tk.LabelFrame(master, text='Mode Select', labelanchor='nw')
        self.M_Frame.grid(row=1, column=0, sticky=tk.W+tk.E, padx=10, pady=10)
        
        self.Enable_Button = tk.Button(self.M_Frame, textvariable=self.Mode_Display, command=self._output, width=15)
        self.Enable_Button.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # display to the user whether the PID is on of off
        self.Status = tk.Canvas(self.M_Frame, width=125, height=50)
        self.Status.grid(row=1, column=0, sticky=tk.W)

        # this is to center the text in the rectangluar box
        rect_coords = (10, 5, 125, 25) # x1 y1 x2 y2
        rect_center_x = (rect_coords[0] + rect_coords[2])/2
        rect_center_y = (rect_coords[1] + rect_coords[3])/2         
        # visual for the on off PID
        self.Indicator = self.Status.create_rectangle(*rect_coords, fill=self.Status_Color.get(), width=3)         
        self.Status_Text = self.Status.create_text(rect_center_x, rect_center_y, font=("Helvetica", 12, 'bold'), anchor='center')
        self.Status.itemconfig(self.Status_Text, text=self.Status_Display.get())
        
        # preheat button
        self.Preheat_Display = tk.StringVar(master, value='Enable Preheat') # message on the preheat button
        self.Preheat_button = tk.Button(self.M_Frame, textvariable=self.Preheat_Display, width=15, command=self._preheat, bg='orange')
        self.Preheat_button.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        # countdown timer for preheating
        self.Timer_label = tk.Label(self.M_Frame, text='Timer (mm:ss)').grid(row=0, column=2, padx=10, pady=10, sticky=tk.W)
        self.Timer = tk.Entry(self.M_Frame, textvariable=self.timer_entry)
        self.Timer.grid(row=1, column=2, sticky=tk.N + tk.W)
        self.Timer.config(state='disabled')
        
        #############################
        ### PID Varibales Display ###
        #############################
        self.PID_Frame = tk.LabelFrame(master,text='PID Variables',labelanchor='nw')
        self.PID_Frame.grid(row=2,column=0,sticky=tk.W+tk.E,padx=10,pady=10)
        
        self.D_SP_Label = tk.Label(self.PID_Frame,text='Desired Set-Point (C)').grid(row=0, column=0)
        self.D_SP = tk.Entry(self.PID_Frame,textvariable=self.sp_entry)
        self.D_SP.bind('<Return>', lambda _: self.callback(self.sp_entry,self.Data.pid_vars['desired_sp']))
        self.D_SP.bind('<FocusOut>', lambda _: self.off_click(self.sp_entry,self.Data.pid_vars['desired_sp']))
        self.D_SP.grid(row=1, column=0, padx=10, pady=5)
        
        self.A_SP_Label = tk.Label(self.PID_Frame,text='Actual Set-Point').grid(row=0,column=1)
        self.A_SP = tk.Entry(self.PID_Frame,textvariable=self.Data.pid_vars['actual_sp'])
        self.A_SP.config(state='readonly')
        self.A_SP.grid(row=0,column=2,padx=10,pady=5)
        
        self.CV_Label = tk.Label(self.PID_Frame,text='Current Value').grid(row=1,column=1)
        self.CV = tk.Entry(self.PID_Frame,textvariable=self.Data.pid_vars['current_value'])
        self.CV.config(state='readonly')
        self.CV.grid(row=1,column=2,padx=10,pady=5)
        
        self.Error_Label = tk.Label(self.PID_Frame,text='Error').grid(row=2,column=1)
        self.Error = tk.Entry(self.PID_Frame,textvariable=self.Data.pid_vars['error'])
        self.Error.config(state='readonly')
        self.Error.grid(row=2,column=2,padx=10,pady=5)
        
        self.MV_Label = tk.Label(self.PID_Frame,text='Modified Value').grid(row=3,column=1)
        self.MV = tk.Entry(self.PID_Frame,textvariable=self.Data.pid_vars['modified_value'])
        self.MV.config(state='readonly')
        self.MV.grid(row=3,column=2,padx=10,pady=5)
        
        self.P_Label = tk.Label(self.PID_Frame,text='P').grid(row=1,column=3)
        self.P = tk.Entry(self.PID_Frame,textvariable=self.p_entry)
        self.P.bind('<Return>', lambda _: self.callback(self.p_entry,self.Data.pid_vars['Kp']))
        self.P.bind('<FocusOut>', lambda _: self.off_click(self.p_entry,self.Data.pid_vars['Kp']))
        self.P.grid(row=1,column=4,padx=10,pady=5)
        
        self.I_Label = tk.Label(self.PID_Frame,text='I').grid(row=2,column=3)
        self.I = tk.Entry(self.PID_Frame,textvariable=self.i_entry)
        self.I.bind('<Return>', lambda _: self.callback(self.i_entry,self.Data.pid_vars['Ki']))
        self.I.bind('<FocusOut>', lambda _: self.off_click(self.i_entry,self.Data.pid_vars['Ki']))
        self.I.grid(row=2,column=4,padx=10,pady=5)
        
        self.D_Label = tk.Label(self.PID_Frame,text='D').grid(row=3,column=3)
        self.D = tk.Entry(self.PID_Frame,textvariable=self.d_entry)
        self.D.bind('<Return>', lambda _: self.callback(self.d_entry,self.Data.pid_vars['Kd']))
        self.D.bind('<FocusOut>', lambda _: self.off_click(self.d_entry,self.Data.pid_vars['Kd']))
        self.D.grid(row=3,column=4,padx=10,pady=5)
        
        # temp output # weird empty box i think it is the integrator
        self.integrator_label = tk.Label(self.PID_Frame, text='Int').grid(row=0, column=3)
        self.Integrator = tk.Entry(self.PID_Frame, textvariable=self.Data.pid_vars['integrator'])
        self.Integrator.config(state='readonly')
        self.Integrator.grid(row=0,column=4,padx=10,pady=5)
        
        
        ####################
        ### Ramp Display ###
        ####################
        self.R_Frame = tk.LabelFrame(master,text='Ramp Rate',labelanchor='nw')
        self.R_Frame.grid(row=3,column=0,sticky=tk.W+tk.E,padx=10,pady=10)
        
        self.R_Label = tk.Label(self.R_Frame,text='Ramp Rate\n(deg C/s)').grid(row=0, column=0)        
        self.R_entry = tk.Entry(self.R_Frame,textvariable=self.r_entry)
        self.R_entry.bind('<Return>', lambda _: self.callback(self.r_entry,self.Data.pid_vars['rate']))
        self.R_entry.bind('<FocusOut>', lambda _: self.off_click(self.r_entry,self.Data.pid_vars['rate']))
        self.R_entry.grid(row=1, column=0, padx=10, pady=5)        
        
    def callback(self,a,b):
        """ Sets the set-point variable when entry-box is change after pressing enter """
        b.set(a.get())
        
    def off_click(self,a,b):
        """ Reset Entry Box to correct value when clicking off the entry box.
        
        This prevent the box from displaying a not current value
        """
        a.set(b.get())
        
    def _update(self,plotdata='temp'):
        """ Update Plots """
        
        # Update Plot Data
        self.D_SP_plot.set_xdata(self.Data.time_list) 
        self.D_SP_plot.set_ydata(self.Data.D_SP_list)
        
        self.A_SP_plot.set_xdata(self.Data.time_list) 
        self.A_SP_plot.set_ydata(self.Data.A_SP_list)

        # Update Plot Limits
        if self.plot_limits.get() == 'full':
            self.ax.set_xlim(0.9*min(self.Data.time_list),1.1*max(self.Data.time_list))
            self.ax.set_ylim(0.9*min(self.Data.D_SP_list),1.1*max(self.Data.D_SP_list))
            self.f.tight_layout()               

        elif self.plot_limits.get() == 'dt':
            a = self.plot_dt.get() # how many data points back in time
            self.ax.set_xlim(max(self.Data.time_list)-a,1.1*max(self.Data.time_list))
            self.ax.set_ylim(0.95*min(self.Data.D_SP_list[-60*a:]),1.05*max(self.Data.D_SP_list[-60*a:]))
            self.f.tight_layout()

        self.canvas.draw()
    
    def _output(self):
        """ Mode Enable Button action. This function also updates the status indicator """
        
        # Change the output enable state
        if self.Data.pid_vars['mode'].get() == 0:
            self.Data.pid_vars['mode'].set(1)
            C.setIntegrator(Sub_Data.vars['SP_V'].get())
            self.Status.itemconfig(self.Indicator,fill='green')
            self.Status.itemconfig(self.Status_Text,text='Auto Mode')
            self.Mode_Display.set('Switch to Manual')
        else:
            self.Data.pid_vars['mode'].set(0)
            self.Status.itemconfig(self.Indicator,fill='red')
            self.Status.itemconfig(self.Status_Text,text='Manual Mode')
            self.Mode_Display.set('Switch to Auto')
            
    def _preheat(self):
        '''Start the preheating process to help the PID for later use'''
        if self.Preheat_Display.get() == 'Enable Preheat':
            self.Preheat_Display.set('Preheating')
            self.Preheat_button.config(state='disabled')
            Sub_PS.set_voltage(4.0) # Sets the voltage to a certain preheat value
            Sub_PS.set_output(1) # turns the power supply on
            GUI['Substrate']._output()
            self._countdown()

        else:
            self.Preheat_Display.set('Enable Preheat')
            Sub_PS.set_output(0) 
            GUI['Substrate']._output()
        
    def _countdown(self):
        '''Countdown timer to a preheated value after ten minutes, the thermocouple reads 168 C'''
        enable_PID = 60 # in seconds. came from past experiences when heating manually. 
        
        if self.remaining_time >= 0:
            # PID_Data.pid_vars['desired_sp'].set(Sub_TC.get_temp())
            minutes = self.remaining_time // 60
            seconds = self.remaining_time % 60
            countdown_time_stamp = f'{minutes:02d}:{seconds:02d}'
            self.timer_entry.set(countdown_time_stamp)
            self.remaining_time -= 1
            self.master.after(1000, self._countdown) # 1 second countdown
            
            # turns on the PID controller. this should help with the thermal lag.
            if self.remaining_time == enable_PID:
                # toggle the button to turn on PID loop
                GUI['PID']._output()  # Update GUI status

        else: 
            self.Preheat_Display.set('Preheated')

            
class Heater_GUI(tk.Frame):
    """ Class for heater control interfacing """
    
    def __init__(self, master, name, Data):
        tk.Frame.__init__(self, master)
        self.master = master
        self.name = name
        self.Data = Data

        #################
        ### Variables ###
        #################
        self.Out_Display = tk.StringVar(master)  # Message On Output Enable Button
        self.Status_Display = tk.StringVar(master)  # Message On Status Display
        self.Status_Color = tk.StringVar(master)  # Color of status indicator
        self.v_entry = tk.DoubleVar(master, Data.vars['SP_V'].get())  # entry box voltage textvariable
        self.i_entry = tk.DoubleVar(master, Data.vars['SP_I'].get())  # entry box current textvariable
        self.plot_limits = tk.StringVar(master,'full')  # for radio buttons in plot window
        self.plot_dt = tk.IntVar(master, 10) # plot delta time for scroll option
        
        if Data.vars['output'].get() == 0:
            self.Out_Display.set('Output Enable')
            self.Status_Display.set('Off')
            self.Status_Color.set('red')
        else:
            self.Out_Display.set('Output Disable')
            self.Status_Display.set('On')
            self.Status_Color.set('green')
        
        
        ####################
        ### Plot Display ###
        ####################
        self.Plot_Frame = tk.Frame(master)
        self.Plot_Frame.grid(row=0, column=0, padx=10, pady=10)
        
        self.f = Figure(figsize=(figsize_x, figsize_y))
        self.ax = self.f.add_subplot(111)
        self.ax.set_xlabel('Time (minutes)')
        self.ax.set_ylabel('Temperature (C)')
        self.ax.grid(alpha=0.3)
        self.temperature_plot, = self.ax.plot(self.Data.time_list, self.Data.TC_list, 'o-', label='Temperature')
        
        self.canvas = FigureCanvasTkAgg(self.f, self.Plot_Frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, columnspan=4, padx=10, pady=5)
        
        self.Radio_Full = tk.Radiobutton(self.Plot_Frame, text='Full Time', variable=self.plot_limits, value='full')
        self.Radio_Full.grid(row=1, column=0, padx=5)
        self.Radio_dt = tk.Radiobutton(self.Plot_Frame, text='Delta T', variable=self.plot_limits,value='dt')
        self.Radio_dt.grid(row=1, column=1)
        self.Radio_Combo = tk.OptionMenu(self.Plot_Frame, self.plot_dt,10,20)
        self.Radio_Combo.grid(row=1, column=2)
        self.Radio_Label = tk.Label(self.Plot_Frame, text='minutes').grid(row=1,column=3, padx=5)
        
        ############################
        ### Thermocouple Display ###
        ############################

        self.TC_Frame = tk.LabelFrame(master, text='Sample Stage Thermocouple \t *****(KEEP BELOW 20 deg/min (0.3 deg/s))*****', labelanchor='nw')
        self.TC_Frame.grid(row=1,column=0,sticky=tk.W+tk.E,padx=10,pady=10)

        self.TC_Label = tk.Label(self.TC_Frame, text='Temperature (C)').grid(row=0,column=0)
        self.TC_Display = tk.Entry(self.TC_Frame, textvariable=self.Data.vars['temperature'])
        self.TC_Display.config(state='readonly')
        self.TC_Display.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)

        self.ramp_rate_label = tk.Label(self.TC_Frame, text='Ramp Rate\n(deg C/s)').grid(row=0, column=1)
        self.Ramp_Rate = tk.Entry(self.TC_Frame, textvariable=self.Data.vars['ramp_rate'])
        self.Ramp_Rate.config(state='readonly', background='#f0f0f0', readonlybackground='#f0f0f0')
        self.Ramp_Rate.grid(row=1, column=1, padx=10, pady=5)
        
        ############################
        ### Power Supply Display ###
        ############################
        self.PS_Frame = tk.LabelFrame(master, text='Power Supply', labelanchor='nw')
        self.PS_Frame.grid(row=2, column=0, sticky=tk.W+tk.E, padx=10, pady=10)
        
        self.PS_Voltage_Label = tk.Label(self.PS_Frame, text='Voltage (V)').grid(row=0,column=1)
        self.PS_Current_Label = tk.Label(self.PS_Frame ,text='Current (A)').grid(row=0,column=2)
        self.PS_resistance_label = tk.Label(self.PS_Frame, text='Resistance (Ω)').grid(row=0, column=3)
        
        self.Actual_Label = tk.Label(self.PS_Frame, text='Actual').grid(row=1, column=0)
        self.PS_Voltage = tk.Entry(self.PS_Frame, textvariable=self.Data.vars['voltage'])
        self.PS_Voltage.config(state='readonly')
        self.PS_Voltage.grid(row=1, column=1, padx=10, pady=5)

        self.PS_Current = tk.Entry(self.PS_Frame, textvariable=self.Data.vars['current'])
        self.PS_Current.config(state='readonly')
        self.PS_Current.grid(row=1, column=2, padx=10, pady=5)
        
        self.PS_resistance= tk.Entry(self.PS_Frame, textvariable=self.Data.vars['resistance'])
        self.PS_resistance.config(state='readonly')
        self.PS_resistance.grid(row=1, column=3, padx=10, pady=5)
        self.SP_Label = tk.Label(self.PS_Frame, text='Set-Point').grid(row=2, column=0)
    
        self.SP_Voltage = tk.Entry(self.PS_Frame, textvariable=self.v_entry)
        self.SP_Voltage.bind('<Return>', lambda _: self.callback(self.v_entry, self.Data.vars['SP_V']))
        self.SP_Voltage.bind('<FocusOut>', lambda _: self.off_click(self.v_entry, self.Data.vars['SP_V']))
        self.SP_Voltage.grid(row=2, column=1, padx=10, pady=5)
        
        self.SP_Current = tk.Entry(self.PS_Frame, textvariable=self.i_entry)
        self.SP_Current.bind('<Return>', lambda _: self.callback(self.i_entry, self.Data.vars['SP_I']))
        self.SP_Current.bind('<FocusOut>', lambda _: self.off_click(self.i_entry ,self.Data.vars['SP_I']))
        self.SP_Current.grid(row=2, column=2, padx=10, pady=5)
          
        self.Enable_Button = tk.Button(self.PS_Frame, textvariable=self.Out_Display, command=self._output)
        self.Enable_Button.grid(row=3,column=2)
        
        self.Status_Label = tk.Label(self.PS_Frame, text='Status').grid(row=2,column=3)
        self.Status = tk.Canvas(self.PS_Frame, width=80, height=80)
        self.Status.grid(row=3, column=3)
        self.Indicator = self.Status.create_oval(5, 5, 75, 75, fill=self.Status_Color.get(), width=3)  
        self.Status_Text = self.Status.create_text(40, 40, font=("Helvetica", 25))
        self.Status.itemconfig(self.Status_Text, text=self.Status_Display.get())
        
    
    def callback(self,a,b):
        """ Sets the set-point variable when entry-box is change after pressing enter """
        b.set(a.get())
        
    def off_click(self,a,b):
        """ Reset Entry Box to correct value when clicking off the entry box."""
        a.set(b.get())
        
    def _update(self, plotdata='temp'):
        """ Update Plots """
        
        # Update Plot Data
        if plotdata == 'temp':
            self.temperature_plot.set_xdata(self.Data.time_list) 
            self.temperature_plot.set_ydata(self.Data.TC_list)
            self.f.tight_layout()
        
        # Update Plot Limits
        if self.plot_limits.get() == 'full':
            if plotdata == 'temp':
                self.ax.set_xlim(0.9*min(self.Data.time_list),1.1*max(self.Data.time_list))
                self.ax.set_ylim(0.9*min(self.Data.TC_list),1.1*max(self.Data.TC_list))    
                self.f.tight_layout()
                
        elif self.plot_limits.get() == 'dt':
            a = self.plot_dt.get() # how many data points back in time
            if plotdata == 'temp':
                self.ax.set_xlim(max(self.Data.time_list)-a,1.1*max(self.Data.time_list))
                self.ax.set_ylim(0.95*min(self.Data.TC_list[-60*a:]),1.05*max(self.Data.TC_list[-60*a:]))   
                self.f.tight_layout()
            
        self.canvas.draw()
    
    def _output(self):
        """ Output Enable Button action. This function also updates the status indicator """
        
        # Change the output enable state
        if self.Data.vars['output'].get() == 0:
            self.Data.vars['output'].set(1)
            self.Status.itemconfig(self.Indicator, fill='green')
            self.Status.itemconfig(self.Status_Text, text='On')
            self.Out_Display.set('Output Disable')
        else:
            self.Data.vars['output'].set(0)
            self.Status.itemconfig(self.Indicator, fill='red')
            self.Status.itemconfig(self.Status_Text, text='Off')
            self.Out_Display.set('Output Enable')


class Data_Structure_Heater:
    """ Class to store global data used in GUI and to save logged data """    
    
    def __init__(self):
        # Meta Data
        self.keys = ['temperature', 'SP_V', 'SP_I', 'voltage', 'current', 'resistance', 'output', 'ramp_rate']

        # initialize tk variables
        self.vars = {
                key: (tk.BooleanVar() if key == 'output' else tk.DoubleVar())
                for key in self.keys
                }   
        
        # plot arrays and data storage
        self.abs_time_list = [] # date time stamp
        self.time_list = []
        self.TC_list = []
        self.Out_list = []
        self.SP_V_list = []
        self.SP_I_list = []
        self.Voltage_list = []
        self.Current_list = []
        self.ramp_rate_list = []
        
    def data_update(self, t0):
        """ Append Data to Lists"""
    
        self.abs_time_list.append(datetime.datetime.now())
        self.time_list.append((time.time() - t0)/60)
        self.TC_list.append(self.vars['temperature'].get())
        self.SP_V_list.append(self.vars['SP_V'].get())
        self.SP_I_list.append(self.vars['SP_I'].get())
        self.Voltage_list.append(self.vars['voltage'].get())
        self.Current_list.append(self.vars['current'].get())
        self.Out_list.append(self.vars['output'].get())
        self.ramp_rate_list.append(self.vars['ramp_rate'].get())
        
    def save_prep(self):
        """ Prepare Data for Saving """
        
        SaveData = np.vstack((self.abs_time_list, self.time_list, self.TC_list, self.SP_V_list, self.SP_I_list, self.Voltage_list, self.Current_list, self.Out_list, self.ramp_rate_list))
        SaveData = np.transpose(SaveData)
        
        return SaveData
    

class Data_Structure_PID:
    """ Class to store global data used in GUI and to save logged data """    
    
    def __init__(self):
        self.keys = [
                'mode',             # mode of the controller
                'desired_sp',       # desired temperature set point to allow ramping
                'actual_sp',        # temperature set point used in calcuation
                'current_value',    # CV: current temperature value
                'error',            # error value: actualy sp - current value
                'modified_value',   # MV: modified value (output to power supply)
                'rate',             # ramp rate (degrees C per second)
                'Kp',               # P value
                'Ki',               # I value
                'Kd',               # D value
                'integrator',       # intergral of error function
                'derivator',        # derivative of error function
                ]
        
        self.pid_vars = {
                key: (tk.BooleanVar() if key == 'mode' else tk.DoubleVar())
                for key in self.keys
                }
        
        # plot arrays and data storage
        self.Mode_list = []
        self.time_list = []
        self.D_SP_list = []
        self.A_SP_list = []
        self.CV_list = []
        self.Error_list = []
        self.MV_list = []
        self.Rate_list = []
        self.Kp_list = []
        self.Ki_list = []
        self.Kd_list = []
        self.Integrator_list = []
        self.Derivator_list = []
         
    def data_update(self, t0):
        """ Append Data to Lists"""
    
        self.time_list.append((time.time() - t0)/60) # min
        self.Mode_list.append(self.pid_vars['mode'].get())
        self.D_SP_list.append(self.pid_vars['desired_sp'].get())
        self.A_SP_list.append(self.pid_vars['actual_sp'].get())
        self.CV_list.append(self.pid_vars['current_value'].get())
        self.Error_list.append(self.pid_vars['error'].get())
        self.MV_list.append(self.pid_vars['modified_value'].get())
        self.Rate_list.append(self.pid_vars['rate'].get())
        self.Kp_list.append(self.pid_vars['Kp'].get())
        self.Ki_list.append(self.pid_vars['Ki'].get())
        self.Kd_list.append(self.pid_vars['Kd'].get())
        self.Integrator_list.append(self.pid_vars['integrator'].get())
        self.Derivator_list.append(self.pid_vars['derivator'].get())
        
    def save_prep(self):
        """ Prepare Data for Saving """
        SaveData = np.vstack((self.Mode_list,self.time_list,self.D_SP_list,self.A_SP_list, self.CV_list, self.Error_list, self.Rate_list, self.Kp_list, self.Ki_list, self.Kd_list, self.Integrator_list, self.Derivator_list))
        SaveData = np.transpose(SaveData)
        
        return SaveData    
    
    
#--------------------------------------------------------------------------------------------------------    
def initialize_controllers():
    '''
    Creates a file to signal other controllers that they are ready. 
    Trying to sync the clocks
    '''
    
    # Thermocouple Reader - Substrate
    Sub_Data = Data_Structure_Heater()
    
    Sub_TC = therm.TC(ports['TC']) # open serial connection
    Sub_Data.vars['temperature'].set(Sub_TC.get_temp())
    
    # BK Precision Power Supply - Substrate Heater
    Sub_PS = xln.XLN3640(ports['BKP PS']) # open serial connection
    # sets the initial date
    Sub_Data.vars['temperature'].set(Sub_TC.get_temp())
    
    if Sub_PS.get_mode() == 'OFF':
        Sub_Data.vars['output'].set(False)
    else:
        Sub_Data.vars['output'].set(True)
        
    Sub_Data.vars['SP_V'].set(Sub_PS.get_voltage_setpoint())
    Sub_Data.vars['SP_I'].set(Sub_PS.get_current_setpoint())
    Sub_Data.vars['voltage'].set(Sub_PS.get_voltage())
    Sub_Data.vars['current'].set(Sub_PS.get_current())
    Sub_Data.vars['resistance'].set(Sub_PS.calculate_resistance())
    
    # PID Controller
    kp = 1.5
    ki = 0.0010
    kd = 25
    C = pid.PID(kp, ki, kd)
    C.setPoint(Sub_TC.get_temp()) # intial set-point set to current temperature
    
    PID_Data.pid_vars['mode'].set(PID_Mode.get())
    PID_Data.pid_vars['desired_sp'].set(C.getPoint())
    PID_Data.pid_vars['actual_sp'].set(C.getPoint())
    PID_Data.pid_vars['current_value'].set(Sub_TC.get_temp())
    PID_Data.pid_vars['error'].set(C.getError())
    PID_Data.pid_vars['modified_value'].set(C.update(Sub_TC.get_temp()))
    PID_Data.pid_vars['rate'].set(0.3)
    PID_Data.pid_vars['Kp'].set(C.getKp())
    PID_Data.pid_vars['Ki'].set(C.getKi())
    PID_Data.pid_vars['Kd'].set(C.getKd())
    PID_Data.pid_vars['integrator'].set(C.getIntegrator())
    PID_Data.pid_vars['derivator'].set(C.getDerivator())
    
    # with open('controller_ready.txt', 'a') as f:
    #     f.write('Substrate_Heater_Controller is ready\n')
        
    # # waiting for all controllers to be ready
    # expected_controllers = ['Substrate_Heater_Controller', 'TPG261_Controller', 'MKS_Pressure_Controller', 'BKP_Arb_Waveform_Controller', 'Ircon_Modline_Plus_Controller']
    # ready = False
    
    # while not ready:
    #     with open('controller_ready.txt', 'r') as f:
    #         lines = f.readlines()
            
    #     ready = all(f'{controller} is ready\n' in lines for controller in expected_controllers)
        
    #     if not ready:
    #         print('Waiting for all controllers to be ready')
    #         time.sleep(0.01)
    
    return Sub_Data, Sub_PS, Sub_TC, C
    
####################
### Main Program ###
####################
        
if __name__=='__main__':    
    root = tk.Tk()
    root.title('Single Heater Controller PID')
    
    SaveName = tk.StringVar(root)
    Clock = tk.StringVar(root,'0')
    Data_Num = tk.IntVar(root,0)
    
    # save function
    def save_data(Data):
        tmp = datetime.datetime.now()
        date_time_stamp = f'{tmp.year}_{tmp.month:02d}_{tmp.day:02d}-{tmp.hour:02d}_{tmp.minute:02d}_{tmp.second:02d}_'
        SaveName = date_time_stamp + 'xln_Substrate_Heater'
        
        if len(Data) > 1:
            SaveData = np.hstack([Data[i] for i in range(len(Data))])
        else:
            SaveData = Data[0]
        print(SaveName)
        print(SaveData.shape)
        np.save(SaveName, SaveData)
        
    # quit function
    def _quit():
        # close serial connections
        Sub_PS.set_output(0) # disables the output

        
        # save data
        Sub_Save_Data = Sub_Data.save_prep()
        PID_Save_Data = PID_Data.save_prep()
        save_data([Sub_Save_Data, PID_Save_Data])

        Sub_TC.close()         
        Sub_PS.close()
        
        # close application
        root.quit()
        root.destroy()  # prevent fatal error
        
    # PID clear function --> change to set function
    def _clear():
        C.setIntegrator(Sub_Data.vars['SP_V'].get())

    
    #############################################   
    ### Initialize Variables and Data Storage ###
    #############################################
    t0 = time.time()
    dt = int(1000/10)  # update time in milliseconds
    
    PID_Mode = tk.BooleanVar(root, 0)  # PID Mode variable, initially set to manual
    Sub_Data = Data_Structure_Heater()
    PID_Data = Data_Structure_PID()


    ##############################    
    ### Initialize Controllers ###
    ##############################
        
    ports = {}
    ports['BKP PS'] = 'COM9'
    ports['TC'] = 'COM13'

#    ports['BKP PS'] = '/dev/ttyUSB0'
#    ports['TC'] = '/dev/ttyUSB1'
    
    Sub_Data, Sub_PS, Sub_TC, C = initialize_controllers()
    # Sub_Data, Sub_PS, C = initialize_controllers()
    
    #########################   
    ### Create GUI Layout ###
    #########################   
    
    window = {}
    GUI = {}
    Width = 700
    Height = 700
    
    # The Substrate Heater GUI
    window['Sub Heater GUI'] = tk.LabelFrame(root, text='Substrate Temperature', font=('Helvetica', 15, 'bold'), labelanchor='n', width=Width, height=Height)
    window['Sub Heater GUI'].grid(row=0, column=0, padx=5, pady=10, sticky=tk.N)
    
    # PID Loop window
    window['PID Loop'] = tk.LabelFrame(root, text='PID Loop', font=('Helvetica', 15, 'bold'), labelanchor='n', width=Width, height=Height)
    window['PID Loop'].grid(row=0, column=1, columnspan=1, padx=5, pady=10, sticky=tk.N)
    
    GUI['Substrate'] = Heater_GUI(window['Sub Heater GUI'], 'Substrate', Sub_Data)
    GUI['Substrate'].grid(row=0, column=0)
    
    GUI['PID'] = PID_Display(window['PID Loop'], 'PID', PID_Data)
    GUI['PID'].grid(row=0 ,column=0)
    
    # Clock Display
    window['remaining widgets'] = tk.LabelFrame(window['Sub Heater GUI'], text='Widgets', font=('Helvetica', 15, 'bold'), labelanchor='n')
    window['remaining widgets'].grid(row=3, column=0, sticky=tk.W, padx=10, pady=10)
    
    Clock_Label = tk.Label(window['remaining widgets'], text='Clock (min)').grid(row=3 ,column=0, pady=5)
    Clock_Display = tk.Entry(window['remaining widgets'], textvariable=Clock,font=('Helvetica', 13))
    Clock_Display.config('readonly')
    Clock_Display.grid(row=3, column=1, padx=5, pady=5)
    
    # Data Point Display
    Data_Point_Display = tk.Label(window['remaining widgets'], text='Data Point').grid(row=4, column=0, pady=5)
    Data_Point = tk.Entry(window['remaining widgets'], textvariable=Data_Num, font=('Helvetica', 13))
    Data_Point.config('readonly')
    Data_Point.grid(row=4, column=1, padx=5, pady=5)
    
    # Quit Button   
    Q_button = tk.Button(window['remaining widgets'], text='Quit',command=_quit, font=20, width=20)
    Q_button.grid(row=6, column=1, padx=5, pady=5)
  
    # PID Integrator Clear Button
    Clear_button = tk.Button(window['PID Loop'], text='Set PID Integrator', command=_clear, font=20, width=20)
    Clear_button.grid(row=4, column=0, pady=5, sticky=tk.W)
    
    ##############
    ### Events ###
    ##############
    
    # Output Enable on command from Button
    def Output_Enable(PS, data):
        """ Enable or Disable Power Supply """
        
        if data.vars['output'].get() == 1:
            PS.set_output(1)
        else:
            PS.set_output(0)

    Sub_Data.vars['output'].trace_add('write', lambda a,b,c: Output_Enable(Sub_PS, Sub_Data))


    def Set_Power_Supply_Voltage(PS, data):
        '''Manual Enter Voltage Values. Limits the PIDvalues'''
        if PID_Data.pid_vars['mode'].get() == 0:
            PS.set_voltage(data.vars['SP_V'].get())
        else:
            current_voltage = PS.get_voltage()  # Get current voltage
            new_voltage = data.vars['SP_V'].get()  # Desired voltage
            
            # Limit voltage change to 0.1 V per second * dt (scaled to seconds)
            dt_seconds = dt / 1000  # Convert GUI dt (ms) to seconds
            max_voltage_step = 0.2 * dt_seconds  # 0.1 V/s * dt
            
            # Apply rate limiting
            limited_voltage = current_voltage + np.clip(
                new_voltage - current_voltage, 
                -max_voltage_step, 
                max_voltage_step
            )
            
            PS.set_voltage(limited_voltage)  # Set SAFE voltage

    Sub_Data.vars['SP_V'].trace_add('write', lambda a,b,c: Set_Power_Supply_Voltage(Sub_PS, Sub_Data))
    
    # Set Power Supply on change of entry box
    def Set_Power_Supply_Current(PS, data):
        """ Set the Power Supply """
        PS.set_current(data.vars['SP_V'].get())

    Sub_Data.vars['SP_I'].trace_add('write', lambda a,b,c: Set_Power_Supply_Current(Sub_PS, Sub_Data))
   
    
    # PID Controller - Update P Gain Value
    def Set_P(PS, data):
        PS.setKp(data.pid_vars['Kp'].get())
        
    PID_Data.pid_vars['Kp'].trace_add('write', lambda a,b,c: Set_P(C, PID_Data))
    
    # PID Controller - Update I Gain Value
    def Set_I(PS, data):
        PS.setKi(data.pid_vars['Ki'].get())
        
    PID_Data.pid_vars['Ki'].trace_add('write', lambda a,b,c: Set_I(C, PID_Data))

    # PID Controller - Update D Gain Value
    def Set_D(PS, data):
        PS.setKd(data.pid_vars['Kd'].get())
        
    PID_Data.pid_vars['Kd'].trace_add('write', lambda a,b,c: Set_D(C, PID_Data))
    
    # PID Controller - Auto/Manual Mode command from Button
    def Mode_Enable(PS, data):
        """ Enable or Disable PID control """
        
        if data.pid_vars['mode'].get() == 0:
            PS.set(0)
        else:
            PS.set(1)

    PID_Data.pid_vars['mode'].trace_add('write', lambda a,b,c: Mode_Enable(PID_Mode, PID_Data))
    
    ############
    ### Loop ###
    ############
    
    def update(t0):
        """ updates the data values after a pre-set time dt """   
        
        # PID - update desired and actual SP (apply ramp)
        D_SP = PID_Data.pid_vars['desired_sp'].get()
        A_SP = PID_Data.pid_vars['actual_sp'].get()
        CV = Sub_TC.get_temp()
        current_ramp_rate = Sub_Data.vars['ramp_rate'].get()
        ramp_rate_saftey_margin = 0.85
        dt_seconds = dt/1000
        dt_seconds = 0.35
        max_ramp_rate = 0.35 # deg C/s
        max_delta = max_ramp_rate * dt_seconds
        
#        if current_ramp_rate > (max_ramp_rate *  ramp_rate_saftey_margin):
#            max_delta = 0
#        else:
#            max_delta = max_ramp_rate * dt_seconds

        #####################
        # this is kind of like a rate adjust this if you want the error to grow larger
        if abs(D_SP - A_SP) > max_delta:
            A_SP += np.sign(D_SP - A_SP) * max_delta
        else:
            A_SP = D_SP
            
        A_SP = np.round(A_SP, 4)        
        C.setPoint(A_SP)

        ###########################################################
        # PID - calculate new MV with CV and A_SP
        if CV > 250:
            if C.getKd() != 0.20:
                print('PID Kd changed to 0.20 and Kp to 0.25 to adjust for thermal lag)')
                C.setKd(0.20)
                C.setKp(0.5)
        else:
            if C.getKd() != 25:
                print('PID Kd changed to 35 (low temp)')
                C.setKd(25)
        
        MV = C.update(CV)
         # converts the milliseconds of the update time to seconds
#        max_mv_per_second = max_ramp_rate * (C.Hi - C.Low) # max ramp rate * ps range
#        max_mv_change = max_mv_per_second * dt_seconds

#        prev_mv = PID_Data.pid_vars['modified_value'].get()
#        limited_mv = prev_mv + np.clip(MV - prev_mv, -max_mv_change, max_mv_change)
#        MV = limited_mv
        MV = np.round(MV, 5)
        PID_Data.pid_vars['modified_value'].set(MV) # this sets the limited MV
        #####################################################################
        
        # PID - if in Auto Mode, update voltage set-point
        if PID_Mode.get() == 1:      
            Sub_PS.set_voltage(MV)  # directly set voltage
            
        # Actual Ramp Rate according to the thermocouple
        N = int(60) # distance to last data point
        if len(Sub_Data.TC_list) >= N:  # Need at least 2 data points
            time_diff = (Sub_Data.time_list[-1] - Sub_Data.time_list[-N]) * 60  # Convert minutes to seconds
            temp_diff = Sub_Data.TC_list[-1] - Sub_Data.TC_list[-N]
            ramp_rate = np.round(temp_diff / time_diff, 2)  # °C/s
            Sub_Data.vars['ramp_rate'].set(ramp_rate)  # Update GUI
            
            # --- Safety Check: Excessive Ramp Rate ---
            if abs(ramp_rate) > 0.3:  # Threshold from your warning label
                GUI['Substrate'].Ramp_Rate.config(background='red', readonlybackground='red')  # Turn entry box red
                # Optional: Force-disable output or trigger an alarm
                # Sub_PS.set_output(0)  # Uncomment to auto-disable heater if unsafe
            else:
                GUI['Substrate'].Ramp_Rate.config(background='#d9d9d9', readonlybackground='#f0f0f0')  # Revert to normal
                

        # Consider adding PID value update for different temperature ranges
        # Option 1 - start with I=0, then change to 0.001 when temp gets to 400 or so
        # Update all values
        Sub_Data.vars['temperature'].set(Sub_TC.get_temp())
        Sub_Data.vars['voltage'].set(Sub_PS.get_voltage())
        Sub_Data.vars['current'].set(Sub_PS.get_current())
        Sub_Data.vars['resistance'].set(Sub_PS.calculate_resistance())
        PID_Data.pid_vars['actual_sp'].set(A_SP)
        PID_Data.pid_vars['current_value'].set(CV)
        PID_Data.pid_vars['error'].set(C.getError())
        PID_Data.pid_vars['integrator'].set(C.getIntegrator())
        PID_Data.pid_vars['derivator'].set(C.getDerivator())
        
        # Append to Data lists
        Sub_Data.data_update(t0)
        PID_Data.data_update(t0)
        
        # Update plots
        GUI['Substrate']._update()
        GUI['PID']._update(t0)
        
        # Update Clock and Data Point Counter
        Clock.set(str((time.time() - t0)/60)[:-10])
        Data_Num.set(Data_Num.get() + 1)
        
        # Continue Loop
        root.after(dt, lambda: update(t0)) 
        
    root.after(0, lambda: update(t0))
    
    # Start main Loop
    root.protocol('WM_DELETE_WINDOW', _quit)
    root.mainloop()
    
