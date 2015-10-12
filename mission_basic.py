"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import time
import math
import traceback

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from matplotlib.collections import PatchCollection

# Package imports
# Ensure that we can import from the current directory as a package since 
# running this via pymavproxy makes it not have this in the path, and running 
# scripts in general does not define the correct package
sys.path.insert(0, os.getcwd())
from __init__ import __package__
from settings import Arguments
from trajectory import Mission, Memory_Map, Environment, Environment_Simulator
from trajectory.MockVehicle import MockAPI, MockVehicle
from trajectory.Viewer import Viewer_Vehicle
from geometry import Geometry

class Monitor(object):
    def __init__(self, api, mission, environment):
        self.api = api
        self.mission = mission

        self.environment = environment
        arguments = self.environment.get_arguments()
        self.settings = arguments.get_settings("mission_monitor")

        # Seconds to wait before monitoring again
        self.loop_delay = self.settings.get("loop_delay")

        self.sensors = self.environment.get_distance_sensors()

        self.colors = ["red", "purple", "black"]

        self.memory_map = None
        self.plot_polygons = None

    def get_delay(self):
        return self.loop_delay

    def use_viewer(self):
        return self.settings.get("viewer")

    def _create_patch(self, obj):
        if isinstance(obj, tuple):
            return Polygon([self.memory_map.get_xy_index(loc) for loc in obj])
        elif 'center' in obj:
            idx = memory_map.get_xy_index(obj['center'])
            return Circle(idx, radius=obj['radius'])

        return None

    def setup(self):
        # Create a memory map for the vehicle to track where it has seen 
        # objects. This can later be used to find the target object or to fly 
        # around obstacles without colliding.
        memory_size = self.mission.get_space_size()
        self.memory_map = Memory_Map(self.environment, memory_size)

        # "Cheat" to see 2d map of collision data
        patches = []
        for obj in self.environment.get_objects():
            patch = self._create_patch(obj)
            if patch is not None:
                patches.append(patch)

        p = None
        if len(patches) > 0:
            p = PatchCollection(patches, cmap=matplotlib.cm.jet, alpha=0.4)
            patch_colors = 50*np.ones(len(patches))
            p.set_array(np.array(patch_colors))

        self.plot_polygons = p
        self.fig, self.ax = plt.subplots()

        # Set up interactive drawing of the memory map. This makes the 
        # dronekit/mavproxy fairly annoyed since it creates additional 
        # threads/windows. One might have to press Ctrl-C and normal keys to 
        # make the program stop.
        plt.gca().set_aspect("equal", adjustable="box")
        plt.ion()
        plt.show()

    def step(self):
        """
        Perform one step of a monitoring loop.

        Returns `Fase` if the loop should be halted.
        """

        if self.api.exit:
            return False

        # Put our current location on the map for visualization. Of course, 
        # this location is also "safe" since we are flying there.
        vehicle_idx = self.memory_map.get_index(self.environment.get_location())
        self.memory_map.set(vehicle_idx, -1)

        self.mission.step()

        i = 0
        for sensor in self.sensors:
            angle = sensor.get_angle()
            sensor_distance = sensor.get_distance()

            if self.mission.check_sensor_distance(sensor_distance):
                # Display the edge of the simulated object that is responsible 
                # for the measured distance, and consequently the point itself. 
                # This should be the closest "wall" in the angle's direction. 
                # This is again a "cheat" for checking if walls get visualized 
                # correctly.
                self.memory_map.handle_sensor(sensor_distance, angle)
                sensor.draw_current_edge(plt, self.memory_map, self.colors[i % len(self.colors)])

                print("=== [!] Distance to object: {} m (angle {}) ===".format(sensor_distance, angle))

            i = i + 1

        # Display the current memory map interactively.
        if self.plot_polygons is not None:
            self.ax.add_collection(self.plot_polygons)
        plt.imshow(self.memory_map.get_map(), origin='lower')
        plt.draw()
        plt.cla()

        if not self.mission.check_waypoint():
            return False

        # Remove the vehicle from the current location. We set it to "safe" 
        # since there is no object here.
        self.memory_map.set(vehicle_idx, 0)

        return True

    def stop(self):
        plt.close()

# Main mission program
def main(argv):
    arguments = Arguments("settings.json", argv)
    mission_settings = arguments.get_settings("mission")

    geometry_class = mission_settings.get("geometry_class")
    geometry = Geometry.__dict__[geometry_class]()

    simulation = mission_settings.get("vehicle_simulation")
    if __name__ == "__main__":
        # Directly running the file means we use our own simulation
        if not simulation:
            raise ValueError("Mock vehicle can only be used in simulation")

        api = MockAPI()
        vehicle = MockVehicle(geometry)
    else:
        # We're running via builtins execfile or some other module, so assume 
        # we use ArduPilot simulation/actual MAVProxy link to the vehicle's 
        # flight controller.
        if not isinstance(geometry, Geometry.Geometry_Spherical):
            raise ValueError("Dronekit only works with spherical geometry")

        # Connect to API provider and get vehicle object
        api = local_connect()
        vehicle = api.get_vehicles()[0]

    if simulation:
        environment = Environment_Simulator(vehicle, geometry, arguments)
    else:
        environment = Environment(vehicle, geometry, arguments)

    mission_class = mission_settings.get("mission_class")
    mission = Mission.__dict__[mission_class](api, environment, mission_settings)

    monitor = Monitor(api, mission, environment)

    arguments.check_help()

    print("Setting up mission")
    mission.setup()
    mission.display()

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff()

    print("Starting mission")
    mission.start()

    # Monitor mission
    monitor.setup()

    try:
        if monitor.use_viewer():
            viewer = Viewer_Vehicle(environment, monitor)
            viewer.start()
        else:
            ok = True
            while ok:
                ok = monitor.step()
                if ok:
                    time.sleep(monitor.get_delay())
    except Exception, e:
        # Handle exceptions gracefully by attempting to stop the program 
        # ourselves. Unfortunately KeyboardInterrupts are not passed to us when 
        # we run under pymavlink.
        traceback.print_exc()

    monitor.stop()
    mission.return_to_launch()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file.
if __name__ in ["__main__", "__builtin__"]:
    main(sys.argv[1:])
