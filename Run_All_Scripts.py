import subprocess

# Start both scripts simultaneously
process1 = subprocess.Popen(["python", "Read_Temperature_from_Lake_Shore_335_with_GUI_with_csv_V28.py"])
process2 = subprocess.Popen(["python", "Lake_Shore_335_Heater_Control.py"])
process3 = subprocess.Popen(["python","Check_GRIB_Hardware_with_GUI_V3.py"])
# Wait for both scripts to complete
process1.wait()
process2.wait()
process3.wait()

print("Both scripts finished.")
