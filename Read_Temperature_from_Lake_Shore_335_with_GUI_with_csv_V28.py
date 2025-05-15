import pyvisa
import tkinter as tk
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator, FuncFormatter
import time
import collections
import csv

class Lakeshore335App:
    def __init__(self, root):
        self.root = root
        self.root.title("Lakeshore 335 Temperature Monitoring")
        self.root.geometry("-50+50")  # Top-left corner of the screen
        self.rm = pyvisa.ResourceManager()
        self.instrument = None
        self.is_running = False
        self.reading_interval = 1.0
        self.csv_logging = False
        self.csv_file = None
        self.csv_writer = None
        self.time_range = 300  # Plot time range in seconds

        self.y_scale_a_lower = 0.0
        self.y_scale_a_upper = 400.0
        self.y_scale_diff_lower = 0.0
        self.y_scale_diff_upper = 4.0

        self.gpib_address = 'GPIB::5::INSTR'

        self.temp_a_history = collections.deque(maxlen=100000)
        self.temp_b_history = collections.deque(maxlen=100000)
        self.abs_diff_history = collections.deque(maxlen=100000)
        self.time_history = collections.deque(maxlen=100000)
        self.start_time = time.time()

        # Entry references
        self.y_scale_a_lower_entry = None
        self.y_scale_a_upper_entry = None
        self.y_scale_diff_lower_entry = None
        self.y_scale_diff_upper_entry = None

        self.create_widgets()
        self.setup_plot()
        self.connect_to_instrument()

        self.prev_temp_a = None
        self.prev_temp_b = None
        self.prev_time = None
        self.heating_rate_a = 0.0
        self.heating_rate_b = 0.0

    def create_widgets(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        left_frame = tk.Frame(top_frame)
        left_frame.pack(side=tk.LEFT, anchor='nw', padx=5, pady=5)

        right_frame = tk.Frame(top_frame)
        right_frame.pack(side=tk.RIGHT, anchor='ne', padx=5, pady=5)

        # Displays
        tk.Label(left_frame, text="Channel A (K):", font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", padx=2)
        self.temp_a_display = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.temp_a_display.grid(row=1, column=0, sticky="w", padx=2)

        tk.Label(left_frame, text="Channel B (K):", font=("Helvetica", 10)).grid(row=0, column=1, sticky="w", padx=2)
        self.temp_b_display = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.temp_b_display.grid(row=1, column=1, sticky="w", padx=2)

        tk.Label(left_frame, text="Abs Diff (K):", font=("Helvetica", 10)).grid(row=0, column=2, sticky="w", padx=2)
        self.abs_diff_display = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.abs_diff_display.grid(row=1, column=2, sticky="w", padx=2)

        # Heating Rate Displays
        tk.Label(left_frame, text=" Rate A (K/min):", font=("Helvetica", 10)).grid(row=2, column=0, sticky="w",
                                                                                          padx=2)
        self.heating_rate_display_a = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.heating_rate_display_a.grid(row=3, column=0, sticky="w", padx=2)

        tk.Label(left_frame, text="Rate B (K/min):", font=("Helvetica", 10)).grid(row=2, column=1, sticky="w",
                                                                                          padx=2)
        self.heating_rate_display_b = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.heating_rate_display_b.grid(row=3, column=1, sticky="w", padx=2)

        # Frequency
        tk.Label(left_frame, text="Freq (s):", font=("Helvetica", 10)).grid(row=4, column=0, sticky="w", padx=2)
        self.freq_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.freq_entry.insert(0, str(self.reading_interval))
        self.freq_entry.grid(row=4, column=1, sticky="w", padx=2)
        tk.Button(left_frame, text="Set Freq", font=("Helvetica", 10), command=self.set_frequency).grid(row=4, column=2, sticky="w", padx=2)

        # Time Range
        tk.Label(left_frame, text="Time Range (s):", font=("Helvetica", 10)).grid(row=5, column=0, sticky="w", padx=2)
        self.time_range_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.time_range_entry.insert(0, str(self.time_range))
        self.time_range_entry.grid(row=5, column=1, sticky="w", padx=2)
        tk.Button(left_frame, text="Set Time", font=("Helvetica", 10), command=self.set_time_range).grid(row=5, column=2, sticky="w", padx=2)

        # Y Scale A
        tk.Label(left_frame, text="Y Scale A+B (K):", font=("Helvetica", 10)).grid(row=6, column=0, sticky="w", padx=2)
        self.y_scale_a_lower_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_a_lower_entry.insert(0, str(self.y_scale_a_lower))
        self.y_scale_a_lower_entry.grid(row=6, column=1, sticky="w", padx=2)
        self.y_scale_a_upper_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_a_upper_entry.insert(0, str(self.y_scale_a_upper))
        self.y_scale_a_upper_entry.grid(row=6, column=2, sticky="w", padx=2)
        tk.Button(left_frame, text="Set Y Scale A+B", font=("Helvetica", 10), command=self.set_y_scale_a).grid(row=6, column=3, sticky="w", padx=2)

        # Y Scale Abs Diff
        tk.Label(left_frame, text="Y Scale Abs Diff (K):", font=("Helvetica", 10)).grid(row=7, column=0, sticky="w", padx=2)
        self.y_scale_diff_lower_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_diff_lower_entry.insert(0, str(self.y_scale_diff_lower))
        self.y_scale_diff_lower_entry.grid(row=7, column=1, sticky="w", padx=2)
        self.y_scale_diff_upper_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_diff_upper_entry.insert(0, str(self.y_scale_diff_upper))
        self.y_scale_diff_upper_entry.grid(row=7, column=2, sticky="w", padx=2)
        tk.Button(left_frame, text="Set Y Scale Diff", font=("Helvetica", 10), command=self.set_y_scale_diff).grid(row=7, column=3, sticky="w", padx=2)

        # Channel selection dropdown
        tk.Label(left_frame, text="Select Channels:", font=("Helvetica", 10)).grid(row=8, column=0, sticky="w", padx=2)
        self.channel_selection = tk.StringVar()
        self.channel_selection.set("Both")  # Default is both
        self.channel_menu = tk.OptionMenu(left_frame, self.channel_selection, "Channel A", "Channel B", "Both", command=self.update_plot)
        self.channel_menu.grid(row=8, column=1, sticky="w", padx=2)

        # Control buttons
        self.start_stop_button = tk.Button(right_frame, text="Start", command=self.toggle_reading, font=("Helvetica", 10))
        self.start_stop_button.pack(pady=2)
        tk.Button(right_frame, text="Reset Time", command=self.reset_time, font=("Helvetica", 10)).pack(pady=2)
        self.save_button = tk.Button(right_frame, text="Start Saving", command=self.toggle_csv_logging, font=("Helvetica", 10))
        self.save_button.pack(pady=2)

        # Status Indicator
        self.status_label = tk.Label(self.root, text="Status: Disconnected", fg="red", font=("Helvetica", 10))
        self.status_label.pack(pady=2)



    def setup_plot(self):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 8), dpi=100)
        self.fig.tight_layout(pad=2)

        self.ax1.set_title("Channels")
        self.ax1.set_ylabel("Temp (K)")
        self.ax2.set_title("Absolute Difference (A - B)")
        self.ax2.set_ylabel("Abs Diff (K)")
        self.ax2.set_xlabel("Time (s)")

        for ax in (self.ax1, self.ax2):
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3))
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))
            ax.grid(True)

        self.line_a, = self.ax1.plot([], [], color='tab:blue', label="Channel A")
        self.line_b, = self.ax1.plot([], [], color='tab:red', label="Channel B")
        self.line_diff, = self.ax2.plot([], [], color='tab:green', label="Abs. Diff |A-B| (K)")
        self.line_rate_a, = self.ax2.plot([], [], color='C1', label="Rate A (K/min)")
        self.line_rate_b, = self.ax2.plot([], [], color='C2', label="Rate B (K/min)")
        self.ax1.legend(loc="upper right", fontsize=9)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack()
        self.fig.subplots_adjust(left=0.15, right=0.85, top=0.95, bottom=0.10)

    def connect_to_instrument(self):
        try:
            self.instrument = self.rm.open_resource(self.gpib_address)
            self.instrument.timeout = 10000
            print("Connected to Lakeshore 335.")
            self.update_status("Connected")
        except Exception as e:
            print(f"Error connecting to instrument: {e}")
            self.instrument = None
            self.update_status("Disconnected")

    def get_temperature(self):
        if self.instrument:
            try:
                temp_a = self.instrument.query('KRDG? A').strip()
                temp_b = self.instrument.query('KRDG? B').strip()
                return float(temp_a), float(temp_b)
            except Exception as e:
                print(f"Error reading temperature: {e}")
        return None, None

    def update_display_and_plot(self):
        temp_a, temp_b = self.get_temperature()
        current_time = round(time.time() - self.start_time, 4)

        if temp_a is not None and temp_b is not None:
            abs_diff = abs(temp_a - temp_b)

            # Update temperature displays
            self.temp_a_display.config(text=f"{temp_a:.3f}")
            self.temp_b_display.config(text=f"{temp_b:.3f}")
            self.abs_diff_display.config(text=f"{abs_diff:.3f}")

            # Calculate heating rate if previous temperature is available
            if self.prev_temp_a is not None and self.prev_time is not None:
                delta_t = current_time - self.prev_time
                if delta_t > 0:
                    self.heating_rate_a = (temp_a - self.prev_temp_a) / delta_t* 60
                    self.heating_rate_b = (temp_b - self.prev_temp_b) / delta_t* 60
                else:
                    self.heating_rate_a = 0.0
                    self.heating_rate_b = 0.0

            # Update previous temperature and time for next iteration
            self.prev_temp_a = temp_a
            self.prev_temp_b = temp_b
            self.prev_time = current_time

            # Update heating rate displays only if they are not None
            if self.heating_rate_a is not None:
                self.heating_rate_display_a.config(text=f" {self.heating_rate_a:.3f}")
            else:
                self.heating_rate_display_a.config(text=" N/A")

            if self.heating_rate_b is not None:
                self.heating_rate_display_b.config(text=f" {self.heating_rate_b:.3f} ")
            else:
                self.heating_rate_display_b.config(text=": N/A")

            # Store data for plotting
            self.temp_a_history.append(temp_a)
            self.temp_b_history.append(temp_b)
            self.abs_diff_history.append(abs_diff)
            self.time_history.append(current_time)

            # Plotting adjustments
            if current_time <= self.time_range:
                self.ax1.set_xlim(0, self.time_range)
                self.ax2.set_xlim(0, self.time_range)
            else:
                self.ax1.set_xlim(current_time - self.time_range, current_time)
                self.ax2.set_xlim(current_time - self.time_range, current_time)

            self.ax1.set_ylim(self.y_scale_a_lower, self.y_scale_a_upper)
            self.ax2.set_ylim(self.y_scale_diff_lower, self.y_scale_diff_upper)

            self.update_plot()

            self.canvas.draw()

            # CSV logging if enabled
            if self.csv_logging and self.csv_file:
                try:
                    self.csv_writer.writerow(
                        [f"{current_time:.1f}", f"{temp_a:.3f}", f"{temp_b:.3f}", f"{abs_diff:.3f}",
                         f"{self.heating_rate_a:.3f}", f"{self.heating_rate_b:.3f}"])

                except Exception as e:
                    messagebox.showerror("CSV Write Error", f"Failed to write to CSV:\n{e}")
                    self.toggle_csv_logging()
        else:
            self.temp_a_display.config(text="Error")
            self.temp_b_display.config(text="Error")
            self.abs_diff_display.config(text="Error")

        # Schedule next update if the system is running
        if self.is_running:
            self.root.after(int(self.reading_interval * 1000), self.update_display_and_plot)


    def toggle_reading(self):
        self.is_running = not self.is_running
        self.start_stop_button.config(text="Stop" if self.is_running else "Start")
        if self.is_running:
            self.start_time = time.time()
            self.temp_a_history.clear()
            self.temp_b_history.clear()
            self.abs_diff_history.clear()
            self.time_history.clear()
            self.update_display_and_plot()

    def set_frequency(self):
        try:
            value = float(self.freq_entry.get())
            if 0.1 <= value <= 10.0:
                self.reading_interval = value
                print(f"Reading frequency set to {self.reading_interval} seconds.")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a number between 0.1 and 10.0 seconds.")

    def toggle_csv_logging(self):
        if not self.csv_logging:
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if file_path:
                try:
                    self.csv_file = open(file_path, mode='w', newline='')
                    self.csv_writer = csv.writer(self.csv_file)
                    self.csv_writer.writerow(["Time (s)", "Channel A (K)", "Channel B (K)", "Abs Diff (K)","Rate A (K/min)","Rate B (K/min)"])
                    self.csv_logging = True
                    self.save_button.config(text="Stop Saving to CSV")
                    print(f"Logging data to {file_path}")
                except Exception as e:
                    messagebox.showerror("CSV Error", f"Could not open file for writing: {e}")
        else:
            if self.csv_file:
                self.csv_file.close()
            self.csv_logging = False
            self.save_button.config(text="Start Saving to CSV")

    def set_time_range(self):
        try:
            value = float(self.time_range_entry.get())
            if value > 0:
                self.time_range = value
                print(f"Time range set to {self.time_range} seconds.")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a positive number for the time range.")

    def set_y_scale_a(self):
        try:
            lower = float(self.y_scale_a_lower_entry.get())
            upper = float(self.y_scale_a_upper_entry.get())
            if lower < upper:
                self.y_scale_a_lower = lower
                self.y_scale_a_upper = upper
                print(f"Y Scale A set to [{lower}, {upper}]")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for Y Scale A.")

    def set_y_scale_diff(self):
        try:
            lower = float(self.y_scale_diff_lower_entry.get())
            upper = float(self.y_scale_diff_upper_entry.get())
            if lower < upper:
                self.y_scale_diff_lower = lower
                self.y_scale_diff_upper = upper
                print(f"Y Scale Diff set to [{lower}, {upper}]")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for Y Scale Diff.")

    def update_plot(self, event=None):
        """ Update plot based on selected channel(s) """
        selected_channel = self.channel_selection.get()

        if selected_channel == "Channel A":
            self.line_a.set_visible(True)
            self.line_b.set_visible(False)
        elif selected_channel == "Channel B":
            self.line_a.set_visible(False)
            self.line_b.set_visible(True)
        else:  # Both
            self.line_a.set_visible(True)
            self.line_b.set_visible(True)

        # Update data for line A
        self.line_a.set_data(self.time_history, self.temp_a_history)
        # Update data for line B
        self.line_b.set_data(self.time_history, self.temp_b_history)
        # Update data for absolute difference
        self.line_diff.set_data(self.time_history, self.abs_diff_history)

        # Redraw the canvas
        self.canvas.draw()

    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}", fg="green" if status == "Connected" else "red")

    def reset_time(self):
        self.start_time = time.time()
        self.time_history.clear()
        self.temp_a_history.clear()
        self.temp_b_history.clear()
        self.abs_diff_history.clear()
        print("Time and data reset.")
# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = Lakeshore335App(root)
    root.mainloop()