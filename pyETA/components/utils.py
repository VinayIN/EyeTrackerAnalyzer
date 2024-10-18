import warnings
import sys
import math
import platform
import datetime
from typing import List, Optional
import PyQt6.QtWidgets as qtw
import os
import glob
from pyETA import __datapath__

def get_current_screen_size(dialog=False):
    app = qtw.QApplication.instance()
    if app is None:
        app = qtw.QApplication(sys.argv)
    if dialog:
        screen_dialog = qtw.QDialog()
        screen_dialog.setWindowTitle("Select Screen")
        layout = qtw.QVBoxLayout(screen_dialog)

        screen_combo = qtw.QComboBox()
        for i, screen in enumerate(app.screens()):
            screen_combo.addItem(f"Screen {i+1}")
        layout.addWidget(screen_combo)

        button_box = qtw.QDialogButtonBox(qtw.QDialogButtonBox.StandardButton.Ok | 
                                        qtw.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(screen_dialog.accept)
        button_box.rejected.connect(screen_dialog.reject)
        layout.addWidget(button_box)

        if screen_dialog.exec() == qtw.QDialog.DialogCode.Accepted:
            selected_screen = app.screens()[screen_combo.currentIndex()]
            size = selected_screen.size()
            return size.width(), size.height()
    else:
        screen = app.primaryScreen()
        size = screen.size()
        return size.width(), size.height()
    return None, None

def get_system_info():
    node = platform.node()
    system = platform.system()
    machine = platform.machine()
    time_now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{node}_{system}_{machine}_{time_now}"

def get_timestamp():
    return datetime.datetime.now().timestamp()


class OneEuroFilter:
    def __init__(
        self,
        initial_time: float,
        initial_value: float,
        initial_derivative: float = 0.0,
        min_cutoff: float = 1.0,
        beta: float = 0.0,
        derivative_cutoff: float = 1.0,
    ):
        """Initialize the one euro filter."""
        # Previous values.
        self.previous_value: float = initial_value
        self.previous_derivative: float = initial_derivative
        self.previous_time: float = initial_time
        # The parameters.
        self.min_cutoff: float = min_cutoff
        self.beta: float = beta
        self.derivative_cutoff: float = derivative_cutoff

    def smoothing_factor(
            self,
            time_elapsed: float,
            cutoff_frequency: float) -> float:
            r = 2 * math.pi * cutoff_frequency * time_elapsed
            return r / (r + 1)

    def exp_smoothing(
            self,
            alpha: float,
            current_value: float,
            previous_value: float
        ) -> float:
        return alpha * current_value + (1 - alpha) * previous_value

    def __call__(self, current_time: float, current_value: float) -> float:
        """Compute the filtered signal."""
        time_elapsed = current_time - self.previous_time

        # The filtered derivative of the signal.
        alpha_derivative = self.smoothing_factor(time_elapsed, self.derivative_cutoff)
        current_derivative = (current_value - self.previous_value) / time_elapsed
        filtered_derivative = self.exp_smoothing(alpha_derivative, current_derivative, self.previous_derivative)

        # The filtered signal.
        adaptive_cutoff = self.min_cutoff + self.beta * abs(filtered_derivative)
        alpha = self.smoothing_factor(time_elapsed, adaptive_cutoff)
        filtered_value = self.exp_smoothing(alpha, current_value, self.previous_value)

        # Memorize the previous values.
        self.previous_value = filtered_value
        self.previous_derivative = filtered_derivative
        self.previous_time = current_time

        return filtered_value
    
def get_euler_form(point, reference=None):
    "If reference provided, point of origin changes to reference. Provide the parameters in cartesian form"
    point = complex(point[0], point[1])
    if reference is not None:
        point = point - complex(reference[0] - reference[1])
    p = math.atan2(point.imag, point.real)
    m = math.sqrt(point.real**2 + point.imag**2)
    return m,p

def get_cartesian(euler, reference=None):
    x = euler[0] * math.cos(euler[1])
    y = euler[0] * math.sin(euler[1])
    if reference is not None:
        ref_x, ref_y = get_cartesian(reference)
        x = x + ref_x
        y = y + ref_y
    return x, y

def phase_to_degree(phase):
    if phase < 0:
        phase += 2 * math.pi
    return phase * 180 / math.pi

def degree_to_phase(degree):
    if degree < 0:
        degree += 360
    return degree * math.pi / 180

def get_actual_from_relative(relative, screen_width, screen_height):
    pixel_x = relative[0]*screen_width
    pixel_y = relative[1]*screen_height
    return int(pixel_x), int(pixel_y)

def get_relative_from_actual(actual, screen_width, screen_height):
    pixel_x = actual[0]/screen_width
    pixel_y = actual[1]/screen_height
    return pixel_x, pixel_y

def get_distance(point1, point2):
    return math.sqrt((point1[0]-point2[0])**2 + (point1[1]-point2[1])**2)

def get_file_names(prefix, directory=None):
    '''
    if directory is None, check from the default path specified in EyeTrackerAnalyzer.__dirpath__
    '''
    if directory is None:
        directory = __datapath__
    directory = os.path.abspath(directory)
    if os.path.exists(directory):
        return glob.glob(os.path.join(directory, f'{prefix}*'))
    return []