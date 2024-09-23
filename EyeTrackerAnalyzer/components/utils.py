import warnings
import sys
import math
import platform
import datetime
from typing import List, Optional
import PyQt6.QtWidgets as qtw

def get_current_screen_size():
    app = qtw.QApplication.instance()
    if app is None:
        app = qtw.QApplication(sys.argv)

    screen = app.primaryScreen()
    size = screen.size()
    width, height = size.width(), size.height()
    app.quit()
    return width, height

def get_system_info():
    node = platform.node()
    system = platform.system()
    machine = platform.machine()
    width, height = get_current_screen_size()
    return f"{node}_{system}_{machine}_{width}x{height}"

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

class WarningGenerator:
    def __init__(self, filter_categories: Optional[List]=None):
        self.filter_categories = filter_categories

    def generate_warning(self, message: str, category: Optional[Warning]=None):
        if category and self.filter_categories:
            if category in self.filter_categories:
                warnings.filterwarnings('ignore', message, category)
        else:
            warnings.warn(message, category=category, stacklevel=3)