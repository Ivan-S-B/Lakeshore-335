import subprocess

# Start both scripts simultaneously
process1 = subprocess.Popen(["python", ""Lake_Shore_335_Temperature_Monitoring.py"])
process2 = subprocess.Popen(["python", "Lake_Shore_335_Heater_Control.py"])
process3 = subprocess.Popen(["python","Check_GRIB_Hardware.py"])
# Wait for both scripts to complete
process1.wait()
process2.wait()
process3.wait()

print("Both scripts finished.")
