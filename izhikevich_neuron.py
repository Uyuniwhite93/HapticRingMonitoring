'''Izhikevich Neuron Model'''
import time

class IzhikevichNeuron:
    def __init__(self, a, b, c, d, v_init=-70.0):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.v = v_init
        self.u = self.b * self.v
        self.fired_time_internal = -1

    def step(self, dt, I):
        if self.fired_time_internal > 0 and (time.perf_counter() - self.fired_time_internal) < (2 * dt):
             pass
        self.v += dt * (0.04 * self.v**2 + 5 * self.v + 140 - self.u + I)
        self.u += dt * self.a * (self.b * self.v - self.u)
        fired = False
        if self.v >= 30:
            self.v = self.c
            self.u += self.d
            fired = True
            self.fired_time_internal = time.perf_counter()
        return fired 