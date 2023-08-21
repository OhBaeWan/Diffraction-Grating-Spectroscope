import dearpygui.dearpygui as dpg
import serial
import sys
import glob
import math


# Serial port configuration
port = 'COM6'  # Replace with the appropriate port
BAUD_RATE = 9600

wavelengths = []
intensities = []


samples = []
IntegrationAve = []

max_samples = 10
num_samples = 0
interframe = False 

shift = 275

scale = 3

serial_port = serial.Serial()

dpg.create_context()


for i in range(0, 1500):
    wavelengths.append((i/scale)+shift)
    intensities.append(0)
    IntegrationAve.append(0)



def LPfilter(data):
    # a low pass digital filter to smooth the data
    # data is a list of integers
    # returns a list of integers
    output = []
    for i in range(0, len(data)):
        if i == 0:
            output.append(data[i])
        else:
            # average the current data point with the previous 10 data points
            sum = 0
            for j in range(0, 10):
                sum += data[i-j]
            output.append(sum/10)
    return output

def LPfilter2(data):
    # a median filter to smooth the data
    # data is a list of integers
    # returns a list of integers
    output = []
    for i in range(0, len(data)):
        if i == 0:
            output.append(data[i])
        else:
            # find the median of the closest 10 data points
            temp = []
            for j in range(0, 4):
                temp.append(data[i-j])
            temp.sort()
            output.append(temp[1])
    return output

def HPfilter(data, time_constant):
    # a high pass digital filter to level the data
    # data is a list of integers
    # returns a list of integers
    a = 1/(1+time_constant)
    output = []
    for i in range(0, len(data)):
        if i == 0:
            output.append(data[i])
        else:
            output.append (a * (output[i-1] + data[i] - data[i-1]))
    return output

def NLscale(data):
    # a non-linear scaling function to improve the contrast
    # data is a list of integers
    # returns a list of integers
    output = []
    for i in range(0, len(data)):
        scale = 1 - math.exp(-i/1000)
        output.append(data[i] * scale)
    return output

def Lscale(data, scale):
    # a linear scaling function to improve the contrast
    # data is a list of integers
    # returns a list of integers
    output = []
    for i in range(0, len(data)):
        output.append(data[i] * scale)
    return output

def normalize(data):
    # normalize the data to 0-200
    # data is a list of integers
    # returns a list of integers
    output = []
    max = 1
    for i in range(0, len(data)):
        if data[i] > max:
            max = data[i]
    for i in range(0, len(data)):
        output.append(data[i] * 200 / max)
    return output


def update_series():
    # If Begin Frame received, start a new frame. Otherwise, add data to the current frame.
    # If End Frame received, plot the frame.
    global intensities
    global wavelengths
    global IntegrationAve
    global interframe
    global num_samples
    global samples
    global max_samples
    global shift
    global scale


    if serial_port.is_open and serial_port.in_waiting > 0:
        data = serial_port.readline().strip().decode()
        if data == "Start Frame":
            intensities.clear()
            wavelengths.clear()
            scale = dpg.get_value("scale")
            shift = dpg.get_value("shift")
            for i in range(0, 1500):
                wavelengths.append((i/scale)+shift)

            interframe = True
        elif data == "End Frame":
            # Update the GUI window with the received spectroscope values
            dpg.set_value("unfiltered_tag", [ wavelengths,intensities])
            #apply the filter if the checkbox is checked
            if dpg.get_value("LPF"):
                intensities = LPfilter(intensities)
                intensities = LPfilter2(intensities)
                
            if dpg.get_value("HPF"):
                intensities = HPfilter(intensities, 0.005)
            if dpg.get_value("NLS"):
                for i in range(0, 5):
                    intensities = NLscale(intensities)
            if dpg.get_value("NORM"):
                intensities = normalize(intensities)
            dpg.set_value("filtered_tag", [ wavelengths,intensities])

            # add the current frame to the integration average
            max_samples = dpg.get_value("num_avg_input")
            if dpg.get_value("avg_bool"):
                if num_samples == 0:
                    IntegrationAve.clear()
                    samples.clear()
                    for i in range(0, len(intensities)):
                        IntegrationAve.append(intensities[i])
                    samples.append(intensities.copy())
                    num_samples = 1
                else:
                    num_samples += 1
                    if num_samples > max_samples:
                        num_samples = max_samples
                        while len(samples) > max_samples:
                            samples.pop(0)
                    samples.append(intensities.copy())

                # calculate the average of all the samples.
                IntegrationAve.clear()
                for i in range(0, len(intensities)):
                    sum = 0
                    for j in range(0, num_samples):
                        sum += samples[j][i]
                    IntegrationAve.append(sum / num_samples)

                dpg.set_value("num_avg", num_samples)
                dpg.set_value("ave_tag", [ wavelengths,IntegrationAve])

            interframe = False
            return
        else:
            # Parse the intensity value from the received data
            temp = data.split(",")
            for intensity in temp:
                if intensity != "" and interframe:
                    intensities.append(255-int(intensity))


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

# Create a callback function to open the selected serial port
def open_serial_callback(sender, data):
    global port
    global serial_port
    port = dpg.get_value("COM Port")
    print(f"Opening {port}")
    try:
        serial_port = serial.Serial(port, BAUD_RATE)
        # Do something with the serial_connection, e.g., read/write data
        # serial_connection.write(b"Hello, Serial!")
        # data = serial_connection.read()
        # serial_connection.close()
    except serial.SerialException:
        print(f"Failed to open {port}")

def reset_avg_callback(sender, data):
    global num_samples
    num_samples = 0
    dpg.set_value("num_avg", num_samples)
    for i in range(0, len(intensities)):
        IntegrationAve[i] = 0
    dpg.set_value("ave_tag", [ wavelengths,IntegrationAve])


with dpg.value_registry():
    dpg.add_string_value(tag="COM Port", default_value="COM6")

# Create a 1px tall 900px wide 2D texture of a rainbow gradient from left to right blue -> green -> red
rainbow_texture = []
length = 730
step = length/4

for i in range(0, length):
    if i < length/4:
        r = 0
        g = 0
        b = int((i / step) * 255) / 255
    elif i < length/2:
        r = 0
        g = int(((i - step) / step) * 255) / 255
        b = int((1 - (i - step) / step) * 255) / 255
    elif i < 3 * length/4:
        r = int(((i - 2 * step) / step) * 255) / 255
        g = int((1 - (i - 2 * step) / step) * 255) / 255
        b = 0
    else:
        r = int((1 - (i - 3 * step) / step) * 255) / 255
        g = 0
        b = 0
     

    # Add the RGB values to the texture array
    rainbow_texture.append(r)
    rainbow_texture.append(g)
    rainbow_texture.append(b)
    rainbow_texture.append(255)

# make the texture 4 times as tall so it can be used as a gradient
for i in range(0, 9):
    rainbow_texture.extend(rainbow_texture)


with dpg.texture_registry(show=True):
    dpg.add_static_texture(width=length, height=10, default_value=rainbow_texture, tag="rainbow")


with dpg.window(label="Live", tag="win1", width=900, height=1080):
    # Get the list of available serial ports
    available_ports = serial_ports()

    # Create the drop-down box with available ports
    dpg.add_text("Select COM Port:")
    dpg.add_listbox(source="COM Port" , items=available_ports)

    # Create a button to open the selected serial port
    dpg.add_button(label="Open Serial Port", callback=open_serial_callback)


    with dpg.plot(label="Unfiltered", height=400 , width=800):
        # Optionally create legend
        dpg.add_plot_legend()

        # REQUIRED: create x and y axes
        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="x_axis_u")
        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis_u")
        dpg.set_axis_limits("y_axis_u", 0, 255)
        dpg.set_axis_limits("x_axis_u", 400, 800)


        # Series belong to a y axis
        dpg.add_line_series(wavelengths, intensities, label="Results", parent="y_axis_u", tag="unfiltered_tag")
    dpg.add_image("rainbow", indent=50)

    # Sliders to control shift and scale
    dpg.add_slider_float(label="Shift", default_value=350, min_value=100, max_value=500, tag="shift")
    dpg.add_slider_float(label="Scale", default_value=3, min_value=1, max_value=5, tag="scale")

    # checkboxes for each filter that will toggle the application of each filter step
    dpg.add_checkbox(label="Low Pass Filter", tag="LPF")
    dpg.add_checkbox(label="High Pass Filter", tag="HPF")
    dpg.add_checkbox(label="Non-Linear Scaling", tag="NLS")
    dpg.add_checkbox(label="Normalize", tag="NORM")
    # Create plot
    with dpg.plot(label="Filtered", height=400 , width=800):
        # Optionally create legend
        dpg.add_plot_legend() 

        # REQUIRED: create x and y axes
        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="x_axis_f")
        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis_f")
        dpg.set_axis_limits("y_axis_f", 0, 255)
        dpg.set_axis_limits("x_axis_f", 400, 800)


        # Series belong to a y axis
        dpg.add_line_series(wavelengths, intensities, label="Results", parent="y_axis_f", tag="filtered_tag")
    dpg.add_image("rainbow", indent=50)

    dpg.add_checkbox(label="Average Spectra", tag="avg_bool")
    dpg.add_text("Number of Spectra Averaged:")
    dpg.add_text("0", tag="num_avg")
    # a text entry box for the number of spectra to average
    dpg.add_input_int(label="Number of Spectra to Average", tag="num_avg_input", default_value=10)
    dpg.add_button(label="Reset Average", callback=reset_avg_callback)

    with dpg.plot(label="Averaged", height=400 , width=800):
        # Optionally create legend
        dpg.add_plot_legend()

        # REQUIRED: create x and y axes
        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="x_axis_a")
        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis_a")
        dpg.set_axis_limits("y_axis_a", 0, 255)
        dpg.set_axis_limits("x_axis_a", 400, 800)


        # Series belong to a y axis
        dpg.add_line_series(wavelengths, IntegrationAve, label="Results", parent="y_axis_a", tag="ave_tag")

    # offset the image by 100 pixels to the right
    dpg.add_image("rainbow", indent=50)



dpg.create_viewport(title='Custom Title', width=900, height=1080)
dpg.setup_dearpygui()
dpg.show_viewport()

# Below replaces start_dearpygui()
while dpg.is_dearpygui_running():
    # Insert any additional code you would like to run in the render loop
    # You can manually stop by using stop_dearpygui()
    update_series()
    # refresh the list of available serial ports
    #available_ports = serial_ports()
    #dpg.configure_item("COM Port", items=available_ports)

    dpg.render_dearpygui_frame()

dpg.destroy_context()
