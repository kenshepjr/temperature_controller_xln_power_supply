# -*- coding: utf-8 -*-
"""
Created on Fri Mar 30 11:11:32 2018

@author: J Ulbrandt

Module for PID control.

Ideas for future:
-----------------
Disable Integral term until CV has enetered controllable regime

"""

import numpy as np


# Classes

class PID:
    """
    Inputs
    -------
    P: Proportional Gain
    I: Integral Gain
    D: Derivative Gain
    Derivator: derivative of error function
    Integrator: integral of error function
    Int_Max: Maximum allowed value for integral (to prevent integral windup)
    Int_Min: Minimum allowed value for integral (to prevent integral windup)
    
    """
    
    def __init__(self, P=0.0, I=0.0, D=0.0, Derivator=0 ,Integrator=0, Int_Max=50, Int_Min=-50):
        self.Kp = P
        self.Ki = I
        self.Kd = D
        self.Derivator = Derivator
        self.Integrator = Integrator
        self.Integrator_Max = Int_Max
        self.Integrator_Min = Int_Min

        
        self.set_point = 0.0
        self.pre_setpoint = 0
        self.error = 0.0
        
        self.Hi = 24.0  # highest value of heater
        self.Low = 0.0  # lowest value of heater
                
    def update(self, CV, dt=0.1):
        """ 
        Inputsmp
        -------
        CV:  control variable value (usually temperature)
        
        Outputs
        --------
        MV: new value of set-point
        
        Note: dt is assumed to be zero. May need to modify this in future.
        
        """

        self.error = self.set_point - CV
        self.P_value = self.Kp*self.error
        self.D_value = self.Kd * (self.error - self.Derivator)
        self.Derivator = self.error
        self.Integrator = self.Integrator + self.error * self.Ki
        
        
        if self.Integrator > self.Integrator_Max:
            self.Integrator = self.Integrator_Max
        elif self.Integrator < self.Integrator_Min:
            self.Integrator = self.Integrator_Min
            
        self.I_value = self.Integrator
        
        MV = self.P_value + self.I_value + self.D_value
        
        if MV < self.Low or MV > self.Hi:
            self.Integrator = self.Integrator - self.error * self.Ki  # anti integral windup
            MV = max(self.Low, min(self.Hi, MV))  # clip output

        return MV
        
    def setPoint(self, set_point):
        """ Initialize set_point of PID """
        self.pre_setpoint = self.set_point
        self.set_point = set_point
#        self.Integrator = 0
#        self.Derivator = 0
                
    def setIntegrator(self,Integrator):
        self.Integrator = Integrator
               
    def setDerivator(self,Derivator):
        self.Derivator = Derivator
        
    def setKp(self,P):
        self.Kp = P
                
    def setKi(self,I):
        self.Ki = I
                
    def setKd(self,D):
        self.Kd = D
                
    def getKp(self):
        return self.Kp
    
    def getKi(self):
        return self.Ki
    
    def getKd(self):
        return self.Kd
    
    def getPoint(self):
        return self.set_point
        
    def getError(self):
        return np.round(self.error, 5)
        
    def getIntegrator(self):
        return np.round(self.Integrator, 5)
    
    def getDerivator(self):
        return self.Derivator
    
# Functions
    
def ramp(self, current_SP, new_SP,Rate):
    """ ramp the control variable to new set-point """
    pass