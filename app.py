import time
import psutil
import platform
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Global variables for calculating network speed
last_net_io = psutil.net_io_counters()
last_time = time.time()

def get_size(bytes, suffix="B"):
    """Scale bytes to its proper format (e.g., 12.5 MB)"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    global last_net_io, last_time

    # 1. CPU Stats
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    
    # 2. Memory Stats
    svmem = psutil.virtual_memory()
    
    # 3. Disk Stats (C: drive usually)
    try:
        # On Windows 'C:\\', on Linux/Mac '/'
        disk_path = 'C:\\' if platform.system() == 'Windows' else '/'
        disk_usage = psutil.disk_usage(disk_path)
    except:
        disk_usage = None

    # 4. Network Speed Calculation
    current_net_io = psutil.net_io_counters()
    current_time = time.time()
    
    time_delta = current_time - last_time
    # Avoid division by zero
    if time_delta == 0: time_delta = 1

    bytes_sent = current_net_io.bytes_sent - last_net_io.bytes_sent
    bytes_recv = current_net_io.bytes_recv - last_net_io.bytes_recv
    
    upload_speed = bytes_sent / time_delta
    download_speed = bytes_recv / time_delta
    
    # Update globals for next calculation
    last_net_io = current_net_io
    last_time = current_time

    # 5. Temperature (Linux/Mac specific usually)
    temp = "N/A"
    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try to find a common coretemp
                if 'coretemp' in temps:
                    temp = temps['coretemp'][0].current
                elif 'cpu_thermal' in temps:
                    temp = temps['cpu_thermal'][0].current
                else:
                    # Fallback: grab the first available temp
                    first_key = next(iter(temps))
                    temp = temps[first_key][0].current
        except:
            pass

    # 6. Battery
    battery = psutil.sensors_battery()
    battery_percent = battery.percent if battery else 100
    power_plugged = battery.power_plugged if battery else True

    data = {
        'cpu': {
            'total': cpu_percent,
            'cores': cpu_per_core,
            'count': psutil.cpu_count(logical=True),
            'temp': temp
        },
        'memory': {
            'total': get_size(svmem.total),
            'used': get_size(svmem.used),
            'percent': svmem.percent,
            'available': get_size(svmem.available)
        },
        'disk': {
            'percent': disk_usage.percent if disk_usage else 0,
            'used': get_size(disk_usage.used) if disk_usage else "0B",
            'total': get_size(disk_usage.total) if disk_usage else "0B"
        },
        'network': {
            'up': get_size(upload_speed),
            'down': get_size(download_speed),
            'up_bytes': upload_speed,   # Raw value for graphs
            'down_bytes': download_speed # Raw value for graphs
        },
        'system': {
            'battery': battery_percent,
            'charging': power_plugged,
            'uptime': int(time.time() - psutil.boot_time()),
            'platform': f"{platform.system()} {platform.release()}"
        }
    }

    return jsonify(data)

if __name__ == '__main__':
    print("Starting System Monitor on http://localhost:5000")
    app.run(debug=True, port=5000)