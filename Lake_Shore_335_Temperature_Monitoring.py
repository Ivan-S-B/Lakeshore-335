import pyvisa
import tkinter as tk
from tkinter import messagebox, filedialog,ttk,PhotoImage
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator, FuncFormatter,FormatStrFormatter
import matplotlib.colors as mcolors
import time
import collections
import csv


class Lakeshore335App:
    def __init__(self, root):
        self.root = root
        self.root.title("Lakeshore 335 Temperature Monitoring")
        self.root.geometry("1500x900-50+50")
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
        self.y_scale_diff_lower = 2.0
        self.y_scale_diff_upper = 4.0
        self.popup_axes_map = {}  # Maps popup windows to (ax_key, y_lower, y_upper)
        self.y_scale_1st_derivative_lower = -1.0
        self.y_scale_1st_derivative_upper = 1.0
        self.y_scale_2nd_derivative_lower = -1.0
        self.y_scale_2nd_derivative_upper = 1.0

        self.gpib_address = 'GPIB::5::INSTR'

        self.temp_a_history = collections.deque(maxlen=45000000)
        self.temp_b_history = collections.deque(maxlen=45000000)
        self.abs_diff_history = collections.deque(maxlen=45000000)
        self.time_history = collections.deque(maxlen=45000000)
        self.start_time = time.time()
        self.deriv_channel_selection = tk.StringVar()
        self.deriv_channel_selection.set("Both")

        self.second_deriv_channel_selection = tk.StringVar()
        self.second_deriv_channel_selection.set("Both")

        # Entry references
        self.y_scale_a_lower_entry = None
        self.y_scale_a_upper_entry = None
        self.y_scale_diff_lower_entry = None
        self.y_scale_diff_upper_entry = None

        self.create_widgets()
        self.setup_plot()

        self.prev_temp_a = None
        self.prev_temp_b = None
        self.prev_time = None
        self.heating_rate_a = 0.0
        self.heating_rate_b = 0.0
        self.canvas.mpl_connect("button_press_event", self.on_plot_click)

    def create_widgets(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, anchor='nw', padx=5, pady=5)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.right_frame = right_frame  # Save for use in plot setup

        # Displays
        tk.Label(left_frame, text="Channel A [K]:", font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", padx=2)
        self.temp_a_display = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.temp_a_display.grid(row=1, column=0, sticky="w", padx=2)

        tk.Label(left_frame, text="Channel B [K]:", font=("Helvetica", 10)).grid(row=0, column=1, sticky="w", padx=2)
        self.temp_b_display = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.temp_b_display.grid(row=1, column=1, sticky="w", padx=2)

        tk.Label(left_frame, text="|A-B| [K]:", font=("Helvetica", 10)).grid(row=0, column=2, sticky="w", padx=2)
        self.abs_diff_display = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.abs_diff_display.grid(row=1, column=2, sticky="w", padx=2)

        # Heating Rate Displays
        tk.Label(left_frame, text=" Rate A [K/min]:", font=("Helvetica", 10)).grid(row=2, column=0, sticky="w",
                                                                                   padx=2)
        self.heating_rate_display_a = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.heating_rate_display_a.grid(row=3, column=0, sticky="w", padx=2)

        tk.Label(left_frame, text="Rate B [K/min]:", font=("Helvetica", 10)).grid(row=2, column=1, sticky="w",
                                                                                  padx=2)
        self.heating_rate_display_b = tk.Label(left_frame, text="N/A", font=("Helvetica", 10))
        self.heating_rate_display_b.grid(row=3, column=1, sticky="w", padx=2)

        # Frequency
        tk.Label(left_frame, text="Reading Freq [s]:", font=("Helvetica", 10)).grid(row=4, column=0, sticky="w", padx=2)
        self.freq_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.freq_entry.insert(0, str(self.reading_interval))
        self.freq_entry.grid(row=4, column=1, sticky="w", padx=2)
        tk.Button(left_frame, text="Set", font=("Helvetica", 10), command=self.set_frequency).grid(row=4, column=2,
                                                                                                        sticky="w",
                                                                                                        padx=2)
        # Time Range
        tk.Label(left_frame, text="Time Range [s]:", font=("Helvetica", 10)).grid(row=5, column=0, sticky="w", padx=2)
        self.time_range_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.time_range_entry.insert(0, str(self.time_range))
        self.time_range_entry.grid(row=5, column=1, sticky="w", padx=2)
        tk.Button(left_frame, text="Set", font=("Helvetica", 10), command=self.set_time_range).grid(row=5,
                                                                                                         column=2,
                                                                                                         sticky="w",
                                                                                                         padx=2)

        # Y Scale A
        tk.Label(left_frame, text="Y Scale A+B [K]:", font=("Helvetica", 10)).grid(row=6, column=0, sticky="w", padx=2)
        self.y_scale_a_lower_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_a_lower_entry.insert(0, str(self.y_scale_a_lower))
        self.y_scale_a_lower_entry.grid(row=6, column=1, sticky="w", padx=2)
        self.y_scale_a_upper_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_a_upper_entry.insert(0, str(self.y_scale_a_upper))
        self.y_scale_a_upper_entry.grid(row=6, column=2, sticky="w", padx=2)
        tk.Button(left_frame, text="Set", font=("Helvetica", 10), command=self.set_y_scale_a).grid(row=6,
                                                                                                               column=3,
                                                                                                               sticky="w",
                                                                                                               padx=2)
        # Y Scale Abs Diff
        tk.Label(left_frame, text=r"Y Scale |A-B|", font=("Helvetica", 10)).grid(row=7, column=0, sticky="w",
                                                                                        padx=2)
        self.y_scale_diff_lower_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_diff_lower_entry.insert(0, str(self.y_scale_diff_lower))
        self.y_scale_diff_lower_entry.grid(row=7, column=1, sticky="w", padx=2)
        self.y_scale_diff_upper_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_diff_upper_entry.insert(0, str(self.y_scale_diff_upper))
        self.y_scale_diff_upper_entry.grid(row=7, column=2, sticky="w", padx=2)
        tk.Button(left_frame, text="Set", font=("Helvetica", 10), command=self.set_y_scale_diff).grid(
            row=7, column=3, sticky="w", padx=2)

        # Y Scale 1st Derivative (Rate)
        tk.Label(left_frame, text="Y Scale dT/dt", font=("Helvetica", 10)).grid(row=8, column=0, sticky="w", padx=2)
        self.y_scale_1st_derivative_lower_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_1st_derivative_lower_entry.insert(0, str(self.y_scale_1st_derivative_lower))
        self.y_scale_1st_derivative_lower_entry.grid(row=8, column=1, sticky="w", padx=2)
        self.y_scale_1st_derivative_upper_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8, justify='center')
        self.y_scale_1st_derivative_upper_entry.insert(0, str(self.y_scale_1st_derivative_upper))
        self.y_scale_1st_derivative_upper_entry.grid(row=8, column=2, sticky="w", padx=2)
        tk.Button(left_frame, text="Set", font=("Helvetica", 10), command=self.y_scale_1st_derivative).grid(row=8,
                                                                                                               column=3,
                                                                                                               sticky="w",
                                                                                                               padx=2)
        # Y Scale 2nd Derivative (Acceletation)
        tk.Label(left_frame, text="Y Scale d²T/dt²", font=("Helvetica", 10)).grid(row=9, column=0, sticky="w", padx=2)
        self.y_scale_2nd_derivative_lower_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8,
                                                           justify='center')
        self.y_scale_2nd_derivative_lower_entry.insert(0, str(self.y_scale_2nd_derivative_lower))
        self.y_scale_2nd_derivative_lower_entry.grid(row=9, column=1, sticky="w", padx=2)

        self.y_scale_2nd_derivative_upper_entry = tk.Entry(left_frame, font=("Helvetica", 10), width=8,
                                                           justify='center')
        self.y_scale_2nd_derivative_upper_entry.insert(0, str(self.y_scale_2nd_derivative_upper))
        self.y_scale_2nd_derivative_upper_entry.grid(row=9, column=2, sticky="w", padx=2)

        tk.Button(left_frame, text="Set", font=("Helvetica", 10),
                  command=self.set_y_scale_2nd_derivative).grid(
            row=9, column=3, sticky="w", padx=2)

        # Channel selection dropdown
        tk.Label(left_frame, text="A/B Channels:", font=("Helvetica", 10)).grid(row=10, column=0, sticky="w", padx=2)
        self.channel_selection = tk.StringVar()
        self.channel_selection.set("Both")  # Default is both
        self.channel_menu = tk.OptionMenu(left_frame, self.channel_selection, "Channel A", "Channel B", "Both",
                                          command=self.update_plot)
        self.channel_menu.grid(row=10, column=1, sticky="w", padx=2)
        # 1st Derivative (Rate) channel selection
        tk.Label(left_frame, text="dT/dt Channels:", font=("Helvetica", 10)).grid(row=11, column=0, sticky="w",
                                                                                      padx=2)
        self.deriv_channel_menu = tk.OptionMenu(left_frame, self.deriv_channel_selection, "Channel A", "Channel B",
                                                "Both", command=self.update_plot)
        self.deriv_channel_menu.grid(row=11, column=1, sticky="w", padx=2)

        # 2nd Derivative (Acceleration) channel selection
        tk.Label(left_frame, text="d²T/dt² Channels:", font=("Helvetica", 10)).grid(row=12, column=0, sticky="w",
                                                                                      padx=2)
        self.second_deriv_channel_menu = tk.OptionMenu(left_frame, self.second_deriv_channel_selection, "Channel A",
                                                       "Channel B", "Both", command=self.update_plot)
        self.second_deriv_channel_menu.grid(row=12, column=1, sticky="w", padx=2)

        # Control buttons

        self.start_stop_button = tk.Button(left_frame, text="Connect", command=self.toggle_reading,
                                           font=("Helvetica", 10), bg="green")
        self.start_stop_button.grid(row=13, column=0, sticky="w", pady=2)

        tk.Button(left_frame, text="Reset Time", command=self.reset_time, font=("Helvetica", 10)).grid(row=13, column=1,
                                                                                                       sticky="w",
                                                                                                       pady=2)

        self.save_button = tk.Button(left_frame, text="Start Saving", command=self.toggle_csv_logging,
                                     font=("Helvetica", 10))
        self.save_button.grid(row=13, column=2, sticky="w", pady=2)

        # Status Indicator
        self.status_label = tk.Label(self.root, text="Status: Disconnected", fg="red", font=("Helvetica", 10))
        self.status_label.pack(side="left", anchor="w", pady=2)

    def setup_plot(self):
        # Create subplots: 4 axes in total (2 vertical, 2 horizontal)
        self.fig, axes = plt.subplots(2, 2, figsize=(8, 6), dpi=100)
        (self.ax1, self.ax2), (self.ax3, self.ax4) = axes
        #self.fig.tight_layout(pad=2)
        # Increase the space between the plots using subplots_adjust
        self.fig.subplots_adjust(hspace=0.2, wspace=0.2)  # Increase horizontal and vertical spacing

        # Set titles and labels for each axis
        self.ax1.set_title("A and B Temperature")
        self.ax1.set_ylabel("Temperature [K]")
        self.ax1.set_xlabel("Time [s]")
        #self.ax1.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))

        self.ax2.set_title("|A - B|")
        self.ax2.set_ylabel("|A - B| [K]")
        self.ax2.set_xlabel("Time [s]")

        self.ax3.set_title("A and B Rate")
        self.ax3.set_ylabel("dT/dt [K/s]")
        self.ax3.set_xlabel("Time [s]")

        self.ax4.set_title("A and B d²T/dt² ")
        self.ax4.set_ylabel("d²T/dt² [K/s]")
        self.ax4.set_xlabel("Time [s]")

        for ax in (self.ax1, self.ax2, self.ax3, self.ax4):
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3))
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}"))
            ax.grid(color='white', linestyle='--', linewidth=0.7)

        # ax1: channel A and B
        self.line_a, = self.ax1.plot([], [], color='tab:red',linestyle="-",alpha=0.9, label="Channel A")
        self.line_b, = self.ax1.plot([], [], color='tab:blue',linestyle='--',alpha=0.9, label="Channel B")

        # ax2: absolute difference over time
        self.line_diff, = self.ax2.plot([], [], color='black', label="|A - B|")

        # ax3: derivative of Temp A and B

        # Positive/negative colored lines for 1st derivative
        lines_info = [('purple', "dT$_{A}$/dt (+)"), ('magenta', "dT$_{A}$/dt (-)"),('orange', "dT$_{B}$/dt (+)"),('yellow', "dT$_{B}$/dt (-)")]
        lines = [ self.ax3.plot([], [], color=color, linestyle='-', label=label)[0] for color, label in lines_info]
        self.line_deriv_a_pos, self.line_deriv_a_neg, self.line_deriv_b_pos, self.line_deriv_b_neg = lines

        # ax4: second derivative of abs diff
        lines_info_2nd_deriv = [('purple', "d²T$_{A}$/dt² (+)", '-'),('magenta', "d²T$_{A}$/dt² (-)", '-'),('orange', "d²T$_{B}$/dt² (+)", '-'),('yellow', "d²T$_{B}$/dt² (-)", '-')]

        lines_2nd_deriv = [self.ax4.plot([], [], color=color, linestyle=style, label=label)[0] for color, label, style in lines_info_2nd_deriv]

        self.line_2nd_deriv_a_pos, self.line_2nd_deriv_a_neg, self.line_2nd_deriv_b_pos, self.line_2nd_deriv_b_neg = lines_2nd_deriv

        # Legends for the plots
        self.ax1.legend(loc="upper right", fontsize=9)
        self.ax2.legend(loc="upper right", fontsize=9)
        self.ax3.legend(loc="upper right", fontsize=9)
        self.ax4.legend(loc="upper right", fontsize=9)

        # Background color for each plot for better contrast
        for ax in (self.ax1, self.ax2, self.ax3, self.ax4):
            ax.set_facecolor(mcolors.to_rgba('black', alpha=0.3))

        # Create the canvas for the Tkinter GUI
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.fig.subplots_adjust(left=0.15, right=0.85, top=0.95, bottom=0.05)

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
                    self.heating_rate_a = (temp_a - self.prev_temp_a) / delta_t * 60
                    self.heating_rate_b = (temp_b - self.prev_temp_b) / delta_t * 60
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
            # Immediately refresh GUI labels so new values are shown before the next update
            self.root.update_idletasks()
            # Store data for plotting
            self.temp_a_history.append(temp_a)
            self.temp_b_history.append(temp_b)
            self.abs_diff_history.append(abs_diff)
            self.time_history.append(current_time)

            # Calculate derivative of temperatures (dT/dt) over time
            if len(self.time_history) >= 2:
                deriv_a = [0.0] + [
                    (self.temp_a_history[i] - self.temp_a_history[i - 1]) /
                    (self.time_history[i] - self.time_history[i - 1])
                    for i in range(1, len(self.time_history))
                ]
                deriv_b = [0.0] + [
                    (self.temp_b_history[i] - self.temp_b_history[i - 1]) /
                    (self.time_history[i] - self.time_history[i - 1])
                    for i in range(1, len(self.time_history))
                ]

                # Set data to ax4 lines

                # Split into positive and negative parts
                deriv_a_pos = [val if val >= 0 else None for val in deriv_a]
                deriv_a_neg = [val if val < 0 else None for val in deriv_a]
                deriv_b_pos = [val if val >= 0 else None for val in deriv_b]
                deriv_b_neg = [val if val < 0 else None for val in deriv_b]

                # Assign to lines
                self.line_deriv_a_pos.set_data(self.time_history, deriv_a_pos)
                self.line_deriv_a_neg.set_data(self.time_history, deriv_a_neg)
                self.line_deriv_b_pos.set_data(self.time_history, deriv_b_pos)
                self.line_deriv_b_neg.set_data(self.time_history, deriv_b_neg)

                # Adjust ax4 limits
                self.ax3.set_xlim(self.ax1.get_xlim())  # Match time axis
                self.ax3.relim()
                self.ax3.autoscale_view()

            # Compute second derivative (d²T/dt²)
            if len(self.time_history) >= 3:
                second_deriv_a = [0.0, 0.0] + [
                    (
                            (self.temp_a_history[i] - 2 * self.temp_a_history[i - 1] + self.temp_a_history[i - 2]) /
                            ((self.time_history[i] - self.time_history[i - 1]) ** 2)
                    )
                    for i in range(2, len(self.time_history))
                ]

                second_deriv_b = [0.0, 0.0] + [
                    (
                            (self.temp_b_history[i] - 2 * self.temp_b_history[i - 1] + self.temp_b_history[i - 2]) /
                            ((self.time_history[i] - self.time_history[i - 1]) ** 2)
                    )
                    for i in range(2, len(self.time_history))
                ]

                # Update ax3 (second derivative plot)

                # Split into positive and negative parts
                second_deriv_a_pos = [val if val >= 0 else None for val in second_deriv_a]
                second_deriv_a_neg = [val if val < 0 else None for val in second_deriv_a]
                second_deriv_b_pos = [val if val >= 0 else None for val in second_deriv_b]
                second_deriv_b_neg = [val if val < 0 else None for val in second_deriv_b]

                # Assign to lines
                self.line_2nd_deriv_a_pos.set_data(self.time_history, second_deriv_a_pos)
                self.line_2nd_deriv_a_neg.set_data(self.time_history, second_deriv_a_neg)
                self.line_2nd_deriv_b_pos.set_data(self.time_history, second_deriv_b_pos)
                self.line_2nd_deriv_b_neg.set_data(self.time_history, second_deriv_b_neg)

                self.ax4.set_xlim(self.ax1.get_xlim())
                self.ax4.relim()
                self.ax4.autoscale_view()

            # Plotting adjustments
            if current_time <= self.time_range:
                self.ax1.set_xlim(0, self.time_range)
                self.ax2.set_xlim(0, self.time_range)
                self.ax3.set_xlim(0, self.time_range)
                self.ax4.set_xlim(0, self.time_range)
            else:
                self.ax1.set_xlim(current_time - self.time_range, current_time)
                self.ax2.set_xlim(current_time - self.time_range, current_time)
                self.ax3.set_xlim(current_time - self.time_range, current_time)
                self.ax4.set_xlim(current_time - self.time_range, current_time)

            self.ax1.set_ylim(self.y_scale_a_lower, self.y_scale_a_upper)
            self.ax2.set_ylim(self.y_scale_diff_lower, self.y_scale_diff_upper)

            self.ax3.set_ylim(self.y_scale_1st_derivative_lower, self.y_scale_1st_derivative_upper)
            self.ax4.set_ylim(self.y_scale_2nd_derivative_lower, self.y_scale_2nd_derivative_upper)

            # Update plot data
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

    def update_plot(self, event=None):
        """ Update plot based on selected channel(s) """

        # Temperature channels (ax1)
        selected_channel = self.channel_selection.get()
        self.line_a.set_visible(selected_channel in ("Channel A", "Both"))
        self.line_b.set_visible(selected_channel in ("Channel B", "Both"))

        self.line_a.set_data(self.time_history, self.temp_a_history)
        self.line_b.set_data(self.time_history, self.temp_b_history)
        self.line_diff.set_data(self.time_history, self.abs_diff_history)

        # 1st Derivative channels (ax3)
        deriv_channel = self.deriv_channel_selection.get()

        self.line_deriv_a_pos.set_visible(deriv_channel in ("Channel A", "Both"))
        self.line_deriv_a_neg.set_visible(deriv_channel in ("Channel A", "Both"))
        self.line_deriv_b_pos.set_visible(deriv_channel in ("Channel B", "Both"))
        self.line_deriv_b_neg.set_visible(deriv_channel in ("Channel B", "Both"))

        # 2nd Derivative channels (ax4)
        second_deriv_channel = self.second_deriv_channel_selection.get()

        self.line_2nd_deriv_a_pos.set_visible(second_deriv_channel in ("Channel A", "Both"))
        self.line_2nd_deriv_a_neg.set_visible(second_deriv_channel in ("Channel A", "Both"))
        self.line_2nd_deriv_b_pos.set_visible(second_deriv_channel in ("Channel B", "Both"))
        self.line_2nd_deriv_b_neg.set_visible(second_deriv_channel in ("Channel B", "Both"))

        # Update legends
        self.ax1.legend(handles=[line for line in [self.line_a, self.line_b] if line.get_visible()], loc="upper right",
                        fontsize=9)

        self.ax3.legend(handles=[
            line for line in [
                self.line_deriv_a_pos,
                self.line_deriv_a_neg,
                self.line_deriv_b_pos,
                self.line_deriv_b_neg
            ] if line.get_visible()
        ], loc="upper right", fontsize=9)


        self.ax4.legend(handles=[
            line for line in [
                self.line_2nd_deriv_a_pos,
                self.line_2nd_deriv_a_neg,
                self.line_2nd_deriv_b_pos,
                self.line_2nd_deriv_b_neg
            ] if line.get_visible()
        ], loc="upper right", fontsize=9)

        # Update data for line A
        self.line_a.set_data(self.time_history, self.temp_a_history)
        # Update data for line B
        self.line_b.set_data(self.time_history, self.temp_b_history)
        # Update data for absolute difference
        self.line_diff.set_data(self.time_history, self.abs_diff_history)

        # Redraw the canvas
        self.canvas.draw()

    def on_plot_click(self, event):
        # Ignore if the click wasn't on an axes
        if event.inaxes is None:
            return

        if event.inaxes == self.ax1:
            self.open_popup_plot("Temperature", self.ax1.get_ylabel(), self.line_a, self.line_b)
        elif event.inaxes == self.ax2:
            self.open_popup_plot("|A - B|", self.ax2.get_ylabel(), self.line_diff)
        elif event.inaxes == self.ax3:
            self.open_popup_plot("Rate", self.ax3.get_ylabel(), self.line_deriv_a_pos, self.line_deriv_a_neg,
                                 self.line_deriv_b_pos, self.line_deriv_b_neg)
        elif event.inaxes == self.ax4:
            self.open_popup_plot("2nd Derivative", self.ax4.get_ylabel(), self.line_2nd_deriv_a_pos,
                                 self.line_2nd_deriv_a_neg,
                                 self.line_2nd_deriv_b_pos, self.line_2nd_deriv_b_neg)

    def open_popup_plot(self, title, y_label, *lines):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
        ax.set_title(title)
        ax.set_ylabel(y_label)
        ax.set_xlabel("Time [s]")
        ax.grid(True, which='both', color='white', linestyle='--', linewidth=0.5)
        ax.set_facecolor(mcolors.to_rgba('black', alpha=0.3))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}"))

        popup_lines = []
        for line in lines:
            popup_line, = ax.plot([], [], label=line.get_label(),
                                  linestyle=line.get_linestyle(),
                                  color=line.get_color())
            popup_lines.append(popup_line)

        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ax_key = None
        if title == "Temperature":
            ax_key = "ax1"
        elif title == "|A - B|":
            ax_key = "ax2"
        elif title == "Rate":
            ax_key = "ax3"
        elif title == "2nd Derivative":
            ax_key = "ax4"

        if ax_key:
            self.popup_axes_map[popup] = ax_key

        def update_legend():
            visible_lines = [line for line in popup_lines if line.get_visible()]
            ax.legend(handles=visible_lines, loc="upper right", fontsize=9)

        # Visibility function for ax1 - customize here if needed
        def apply_visibility_ax1():
            ch = selected_channel.get()
            for line in popup_lines:
                label = line.get_label().lower()
                label = line.get_label().lower()
                if ch == "Both":
                    line.set_visible(True)
                elif ch == "Channel A":
                    line.set_visible("channel a" in label)
                elif ch == "Channel B":
                    line.set_visible("channel b" in label)
            update_legend()
            canvas.draw()

        # Visibility function for ax3 and ax4
        def apply_visibility_with_channel_filter():
            ch = selected_channel.get()
            for line in popup_lines:
                label = line.get_label().lower()
                if ch == "Both":
                    line.set_visible(True)
                elif ch == "Channel A":
                    line.set_visible("a" in label)
                elif ch == "Channel B":
                    line.set_visible("b" in label)
            update_legend()
            canvas.draw()

        # Visibility for ax2 (always visible)
        def apply_visibility_ax2():
            for line in popup_lines:
                line.set_visible(True)
            update_legend()
            canvas.draw()

        # Add dropdown only if NOT ax2
        if title != "|A - B|":
            dropdown_frame = tk.Frame(popup)
            dropdown_frame.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(dropdown_frame, text="Select Channel:").pack(side=tk.LEFT, padx=(0, 5))

            channel_options = ["Both", "Channel A", "Channel B"]
            selected_channel = tk.StringVar(value="Both")
            dropdown = ttk.Combobox(dropdown_frame, values=channel_options, textvariable=selected_channel,
                                    state="readonly")
            dropdown.pack(side=tk.LEFT)

            # Bind the correct visibility function depending on title
            if title == "Temperature":  # ax1
                dropdown.bind("<<ComboboxSelected>>", lambda event: apply_visibility_ax1())
            else:  # ax3 or ax4
                dropdown.bind("<<ComboboxSelected>>", lambda event: apply_visibility_with_channel_filter())

        def update_popup_plot():
            time_data = list(self.time_history)
            for src_line, dest_line in zip(lines, popup_lines):
                dest_line.set_data(time_data, src_line.get_ydata())

            if time_data:
                main_ax = getattr(self, ax_key)
                ax.set_xlim(main_ax.get_xlim())

            ax.relim()
            ax.autoscale_view()

            if ax_key:
                main_ax = getattr(self, ax_key)
                ax.set_ylim(main_ax.get_ylim())

            # Apply visibility according to axis
            if title == "|A - B|":
                apply_visibility_ax2()
            elif title == "Temperature":  # ax1
                apply_visibility_ax1()
            else:  # ax3 or ax4
                apply_visibility_with_channel_filter()

            if popup.winfo_exists():
                popup.after(int(self.reading_interval * 1000), update_popup_plot)

        update_popup_plot()

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

    def toggle_reading(self):
        if not self.is_running:
            # Attempt to connect if not already connected
            if not self.instrument:
                self.connect_to_instrument()
            if self.instrument:
                self.is_running = True
                self.start_stop_button.config(text="Disconnect", bg="red")
                self.start_time = time.time()
                self.temp_a_history.clear()
                self.temp_b_history.clear()
                self.abs_diff_history.clear()
                self.time_history.clear()
                self.update_display_and_plot()
            else:
                messagebox.showerror("Connection Error", "Could not connect to the Lakeshore 335 instrument.")
        else:
            # Stop reading and disconnect
            self.is_running = False
            self.start_stop_button.config(text="Connect", bg="green")

            # Disconnect from the instrument
            if self.instrument:
                try:
                    # Send disconnect or stop command if supported
                    self.instrument.write("*CLS")  # Clear any errors, not a disconnect command but can reset status
                    self.instrument.write(
                        "SYST:REM")  # Send system command to disable remote control mode (if supported)

                    self.instrument.close()  # Close the connection properly
                    print("Disconnected from Lakeshore 335.")
                    self.update_status("Disconnected")
                except Exception as e:
                    print(f"Error while disconnecting: {e}")

            # Reset the instrument object to None
            self.instrument = None
            self.update_status("Disconnected")

    def y_scale_1st_derivative(self):
        try:
            lower = float(self.y_scale_1st_derivative_lower_entry.get())
            upper = float(self.y_scale_1st_derivative_upper_entry.get())
            if lower < upper:
                self.y_scale_1st_derivative_lower = lower
                self.y_scale_1st_derivative_upper = upper
                self.ax3.set_ylim(lower, upper)
                self.canvas.draw()
                print(f"Y Scale for 1st Derivative set to [{lower}, {upper}]")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for Y Scale 1st Derivative.")

    def set_y_scale_2nd_derivative(self):
        try:
            lower = float(self.y_scale_2nd_derivative_lower_entry.get())
            upper = float(self.y_scale_2nd_derivative_upper_entry.get())
            if lower < upper:
                self.y_scale_2nd_derivative_lower = lower
                self.y_scale_2nd_derivative_upper = upper
                self.ax4.set_ylim(lower, upper)
                self.canvas.draw()
                print(f"Y Scale for 2nd Derivative set to [{lower}, {upper}]")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for Y Scale 2nd Derivative.")
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
                    self.csv_writer.writerow(
                        ["Time (s)", "Channel A (K)", "Channel B (K)", "Abs Diff (K)", "Rate A (K/min)",
                         "Rate B (K/min)"])
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


    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}", fg="green" if status == "Connected" else "red")

    def reset_time(self):
        self.start_time = time.time()
        self.time_history.clear()
        self.temp_a_history.clear()
        self.temp_b_history.clear()
        self.abs_diff_history.clear()

        # Clear plot data immediately
        self.line_a.set_data([], [])
        self.line_b.set_data([], [])
        self.line_diff.set_data([], [])

        self.line_deriv_a_pos.set_data([], [])
        self.line_deriv_a_neg.set_data([], [])
        self.line_deriv_b_pos.set_data([], [])
        self.line_deriv_a_neg.set_data([], [])
        self.line_2nd_deriv_a_pos.set_data([], [])
        self.line_2nd_deriv_a_neg.set_data([], [])
        self.line_2nd_deriv_b_pos.set_data([], [])
        self.line_2nd_deriv_b_neg.set_data([], [])

        # Redraw immediately
        self.update_plot()
        print("Time and data reset.")


# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = Lakeshore335App(root)
    root.mainloop()
