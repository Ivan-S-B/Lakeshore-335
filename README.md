# Lakeshore-335

Lakeshore 335 Temperature Monitoring 

Provides a graphical user interface for real-time monitoring, visualization, and logging of temperature data from a Lakeshore 335 temperature controller via GPIB communication using the pyvisa library.

Necessary dependencies: 

•	Pyvisa, tkinter matplotlib;

•	collections, time, csv.

Key Features:

•	 Real-time communication with Lakeshore 335 via GPIB.

•	 Live plotting of:

•	Temperature readings from Channel A and B;

•	Absolute difference |A − B|;

•	1st derivative (rate of change, dT/dt) for heating/cooling rates;

•	2nd derivative (acceleration, d²T/dt²) to observe control stability.

•	Interactive GUI using tkinter:

•	Temperature displays with real-time values;

•	Click on any subplot to open a popup window with a zoomed-in version of the selected graph;

•	Heating rate indicators;

•	Adjustable plot settings (Y-axis scales, time range, channels to display);

•	Dropdown menus for selecting channels for every plot except “Absolute difference plot |A-B|;

•	CSV logging for data archival;

•	Manual control over reading frequency and plot time (length) window;

•		Pop up windows (on click) for each of live plots.

•	Adjustable Parameters: Set reading frequency and plot time range through the GUI.

•	Status Feedback: Visual status indicator for device connection.

GUI Layout Overview:

•	Left panel: Controls and live temperature readouts;

•	Right panel: Dynamic plots updating in real time;

•	Bottom status bar: Connection status (Connected/Disconnected).


How it Works:

•	The application establishes a connection to the Lakeshore 335 using pyvisa and begins polling the instrument at a user-defined frequency;

•	Temperature readings from both channels are stored in a collections.deque, allowing efficient real-time data streaming;

•	All data is plotted using matplotlib, embedded into the tkinter interface using FigureCanvasTkAgg;

•	CSV logging (if enabled) saves temperature data, timestamps, and calculated derivatives to a file selected by the user.

Configuration Parameters:

•	GPIB Address: Set to GPIB::xx::INSTR where is GRIB adress (by default 5);

•	Reading Interval: Adjustable via the GUI (by default  1.0 s);

•	Plot Range: Adjust time window and y-axis scale for each subplot;

•	Channel Selection: Choose whether to display Channel A, Channel B, or both.

Output:

•	When logging is enabled, a .csv file is created to store data.

Separated GUIs:

•	Heater Control (in development);

•	Listing of all GRIB hardware connected to the computer.

What still needs to be done:

•	Combine temperature monitoring with heating control (currently run as a separate GUI);

•	Add zone heating option to the heating control module.





