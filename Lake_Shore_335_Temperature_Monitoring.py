import pyvisa
import traceback
import tkinter as tk
from tkinter import messagebox


class LakeShoreController:
    def __init__(self):
        self.inst = None
        self.rm = pyvisa.ResourceManager()
        self.setpoint = 310.0
        self.ramp_rate = 0.1
        self.max_output_power = 25  # Maximum power for Output 2 in watts (High Range)
        self.heater_range = "Low"  # Default range
        self.selected_heater = 2  # Default to Heater 2
        self.pid_params = {"P": 50.0, "I": 10.0, "D": 0.0}  # Default PID values

    def connect(self):
        try:
            self.inst = self.rm.open_resource('GPIB::5::INSTR')  # Update address if needed
            idn = self.inst.query("*IDN?")
            print(f"Connected to: {idn.strip()}")
        except pyvisa.VisaIOError as e:
            print(f"[Error] VISA communication failed: {e}")
            messagebox.showerror("Connection Error", str(e))
            self.inst = None

    def set_setpoint(self, value):
        if self.inst is None:
            self.connect()
        if self.inst is None:
            return
        try:
            self.setpoint = float(value)
            self.inst.write(f"SETP {self.selected_heater},{self.setpoint}")
            print(f"[Info] Setpoint set to {self.setpoint} K")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid setpoint value.")
        except Exception as e:
            print(f"[Error] Setpoint failed: {e}")
            traceback.print_exc()
            messagebox.showerror("Setpoint Error", str(e))

    def set_ramp_rate(self, value):
        if self.inst is None:
            self.connect()
        if self.inst is None:
            return
        try:
            self.ramp_rate = float(value)
            self.inst.write(f"RAMP {self.selected_heater},1,{self.ramp_rate}")
            print(f"[Info] Ramp rate set to {self.ramp_rate} K/min")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid ramp rate value.")
        except Exception as e:
            print(f"[Error] Ramp rate failed: {e}")
            traceback.print_exc()
            messagebox.showerror("Ramp Error", str(e))

    def start_heating(self):
        if self.inst is None:
            self.connect()
        if self.inst is None:
            return
        try:
            self.inst.write(f"OUTMODE {self.selected_heater},1,A")  # Closed-loop using sensor A
            self.inst.write(f"SETP {self.selected_heater},{self.setpoint}")
            self.inst.write(f"RAMP {self.selected_heater},1,{self.ramp_rate}")
            self.inst.write(f"RANGE {self.selected_heater},{self.get_range_code()}")  # Set the selected range
            self.inst.write(
                f"PID {self.selected_heater},{self.pid_params['P']},{self.pid_params['I']},{self.pid_params['D']}")
            print(f"[Info] Heating started for Heater {self.selected_heater}.")
        except Exception as e:
            print(f"[Error] Start failed: {e}")
            traceback.print_exc()
            messagebox.showerror("Start Error", str(e))

    def stop_heating(self):
        if self.inst is None:
            print("[Warning] Not connected.")
            return
        try:
            self.inst.write(f"RANGE {self.selected_heater},0")  # Heater off
            print(f"[Info] Heating stopped for Heater {self.selected_heater}.")
        except Exception as e:
            print(f"[Error] Stop failed: {e}")
            traceback.print_exc()
            messagebox.showerror("Stop Error", str(e))

    def get_heater_power(self):
        if self.inst is None:
            return "N/A"
        try:
            # Query for the raw heater output level (0.0 to 1.0) for the selected heater
            raw_level = float(self.inst.query(f"HTR? {self.selected_heater}").strip())

            # Convert the raw level from the range 0-100% to a fraction (0.0 to 1.0)
            fraction = raw_level / 100.0  # Convert to 0.0 - 1.0 range

            # Set the maximum power based on the selected range
            if self.heater_range == "Low":
                max_power = 0.25  # Low range: 0.25 W
            elif self.heater_range == "Med":
                max_power = 2.5  # Medium range: 2.5 W
            elif self.heater_range == "High":
                max_power = 25  # High range: 25 W
            else:
                max_power = 0.25  # Default to Low if range is not recognized

            # Calculate the actual power output in watts using the fraction (0.0 - 1.0)
            watts = fraction * max_power

            # Return the power in watts along with the fractional output
            return f"{watts:.3f} W"  # Display power in watts and percentage
        except Exception as e:
            print(f"[Error] Power read failed: {e}")
            return "Error"

    def get_range_code(self):
        if self.heater_range == "Low":
            return 1
        elif self.heater_range == "Med":
            return 2
        elif self.heater_range == "High":
            return 3
        else:
            return 1  # Default to Low if range is not recognized

    def close(self):
        if self.inst:
            self.inst.close()
        print("[Info] Connection closed.")

    def set_pid(self, P, I, D):
        # Update the PID parameters
        self.pid_params = {"P": P, "I": I, "D": D}
        try:
            self.inst.write(f"PID {self.selected_heater},{P},{I},{D}")
            print(f"[Info] PID values set to P: {P}, I: {I}, D: {D}")
        except Exception as e:
            print(f"[Error] PID setting failed: {e}")
            traceback.print_exc()
            messagebox.showerror("PID Error", str(e))


def main():
    controller = LakeShoreController()
    controller.connect()

    root = tk.Tk()
    root.title("Lake Shore 335 Temperature Control")
    root.geometry("+425+50")  # Add this line to move the GUI to the top-lef
    # ---- Setpoint Field and Button ----
    setpoint_frame = tk.Frame(root)
    setpoint_frame.pack(pady=5)
    tk.Label(setpoint_frame, text="Setpoint (K):").grid(row=0, column=0, padx=5)
    setpoint_entry = tk.Entry(setpoint_frame, width=10)
    setpoint_entry.insert(0, "310.0")
    setpoint_entry.grid(row=0, column=1)
    setpoint_btn = tk.Button(setpoint_frame, text="Set", command=lambda: controller.set_setpoint(setpoint_entry.get()),
                             bg="blue", fg="white")
    setpoint_btn.grid(row=0, column=2, padx=5)

    # ---- Ramp Rate Field and Button ----
    ramp_frame = tk.Frame(root)
    ramp_frame.pack(pady=5)
    tk.Label(ramp_frame, text="Ramp Rate (K/min):").grid(row=0, column=0, padx=5)
    ramp_entry = tk.Entry(ramp_frame, width=10)
    ramp_entry.insert(0, "0.1")
    ramp_entry.grid(row=0, column=1)
    ramp_btn = tk.Button(ramp_frame, text="Set", command=lambda: controller.set_ramp_rate(ramp_entry.get()), bg="blue",
                         fg="white")
    ramp_btn.grid(row=0, column=2, padx=5)

    # ---- Heater Range Dropdown ----
    range_frame = tk.Frame(root)
    range_frame.pack(pady=5)
    tk.Label(range_frame, text="Heater Range:").grid(row=0, column=0, padx=5)
    range_var = tk.StringVar(value="Low")
    range_menu = tk.OptionMenu(range_frame, range_var, "Low", "Med", "High",
                               command=lambda value: setattr(controller, 'heater_range', value))
    range_menu.grid(row=0, column=1, padx=5)

    # ---- Heater Selector Dropdown ----
    heater_frame = tk.Frame(root)
    heater_frame.pack(pady=5)
    tk.Label(heater_frame, text="Select Heater:").grid(row=0, column=0, padx=5)
    heater_var = tk.StringVar(value="Heater 2")
    heater_menu = tk.OptionMenu(heater_frame, heater_var, "Heater 1", "Heater 2",
                                command=lambda value: setattr(controller, 'selected_heater',
                                                              1 if value == "Heater 1" else 2))
    heater_menu.grid(row=0, column=1, padx=5)

    # ---- PID Parameters Fields ----
    pid_frame = tk.Frame(root)
    pid_frame.pack(pady=5)
    tk.Label(pid_frame, text="P:").grid(row=0, column=0, padx=5)
    pid_p_entry = tk.Entry(pid_frame, width=10)
    pid_p_entry.insert(0, "50.0")
    pid_p_entry.grid(row=0, column=1)

    tk.Label(pid_frame, text="I:").grid(row=1, column=0, padx=5)
    pid_i_entry = tk.Entry(pid_frame, width=10)
    pid_i_entry.insert(0, "10.0")
    pid_i_entry.grid(row=1, column=1)

    tk.Label(pid_frame, text="D:").grid(row=2, column=0, padx=5)
    pid_d_entry = tk.Entry(pid_frame, width=10)
    pid_d_entry.insert(0, "0.0")
    pid_d_entry.grid(row=2, column=1)

    # ---- Set PID Button ----
    set_pid_btn = tk.Button(pid_frame, text="Set PID", command=lambda: controller.set_pid(
        float(pid_p_entry.get()), float(pid_i_entry.get()), float(pid_d_entry.get())),
                            bg="blue", fg="white")
    set_pid_btn.grid(row=3, column=0, columnspan=2, pady=5)

    # ---- Power Display ----
    power_label = tk.Label(root, text="Current Heater Power: 0.000 W")
    power_label.pack(pady=10)

    def update_power():
        power = controller.get_heater_power()
        power_label.config(text=f"Current Heater Power: {power}")
        root.after(1000, update_power)  # Update every second

    update_power()

    # ---- Start/Stop Buttons ----
    start_button = tk.Button(root, text="Start Heating", width=20, command=controller.start_heating, bg="green",
                             fg="white")
    start_button.pack(pady=10)

    stop_button = tk.Button(root, text="Stop Heating", width=20, command=controller.stop_heating, bg="red", fg="white")
    stop_button.pack(pady=5)

    def on_close():
        controller.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
