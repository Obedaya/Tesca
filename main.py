import teslapy
import time
import math
import datetime
import yaml
from yaml.loader import FullLoader
from suntime import Sun, SunTimeException


def wait_for_start_time(start_time):
    print("Waiting for start time...")
    while True:
        current_time = datetime.datetime.now().time()
        if current_time >= start_time:
            time.sleep(current_time - start_time)
            break


def run_charging_loop(end_time):
    print("Starting loop...")
    previous = calculate_charging()
    while datetime.datetime.now().time() < end_time:
        previous = calculate_charging()
        time.sleep(cfg['technical']['sleep_time'])
        current = calculate_charging()
        amp = calculate_average(previous, current)
        set_tesla_charging_amp(wallbox_amp_limit(amp))
    print("Ending loop...")


def charging_possible(data, car_data) -> bool:
    # Only charge if the power production + buffer (0,1kW) - the car charging power, is higher than the power being used
    if (data['power_reading'][0]['load_power'] + cfg['technical']['buffer']) - \
            (car_data['charge_state']['charger_power'] * 1000) >= data['power_reading'][0]['solar_power']:
        return False
    else:
        return True


def wallbox_amp_limit(possible_amp):
    if cfg['technical']['min_charging_amp'] <= possible_amp <= cfg['technical']['max_charging_amp']:
        return possible_amp
    elif possible_amp > cfg['technical']['max_charging_amp']:
        return cfg['technical']['max_charging_amp']
    else:
        return 0


def calculate_charging_amp(data, car_data):
    if charging_possible(data, car_data) and car_data['charge_state']['charge_limit_soc'] \
            != car_data['charge_state']['battery_level']:
        # Overhead power gets calculated by:
        # subtracting the load power (power which is being used) + buffer (0,1kW)
        # - the power which is being drained currently by the car,
        # of the power which gets generated
        overhead_power = data['power_reading'][0]['solar_power'] \
                         - (data['power_reading'][0]['load_power']
                            + cfg['technical']['buffer']
                            - (car_data['charge_state']['charger_power'] * 1000))
        tesla_charging_power = (data['percentage_charged'] / 100) * overhead_power
        tesla_charging_amperage = math.floor(tesla_charging_power / cfg['technical']['mains_voltage'])
        return tesla_charging_amperage

        # Check if car already full
    elif car_data['charge_state']['charge_limit_soc'] == car_data['charge_state']['battery_level']:
        print("Already full. Won't charge!")
        return 0
    else:
        print("Not enough power. Won't charge!")
        return 0


def calculate_charging():
    data = battery.get_battery_data()
    car_data = car.get_vehicle_data()
    print("----------------------------------------")
    charging_amp = calculate_charging_amp(data, car_data)
    print(str(data['power_reading'][0]['timestamp']))
    print("Charging possible with: " + str(charging_amp))
    print("----------------------------------------")
    return charging_amp


def calculate_average(old_amp, new_amp):
    charging_amp = math.floor((old_amp + new_amp) / 2)
    print("Average: " + str(charging_amp))
    return charging_amp


# Function to control charging of the car
def set_tesla_charging_amp(charging_amp):
    car.sync_wake_up()
    car_data = car.get_vehicle_data()

    if charging_amp > 0:
        if car_data['charge_state']['charging_state'] != 'Charging':
            car.command('START_CHARGE')
        car.command('CHARGING_AMPS', charging_amps=charging_amp)
        print("Charging with: " + str(charging_amp))
    elif car_data['charge_state']['charging_state'] == 'Charging':
        car.command('STOP_CHARGE')
        print("Not enough power. Charging stopped!")
    else:
        print("Not enough power. Won't charge!")


print("========================================")
print(" _______ _______ _______ _______ _______")
print("    |    |______ |______ |       |_____|")
print("    |    |______ ______| |_____  |     |")
print("                                        ")
print("========================================")

with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=FullLoader)

sun = Sun(cfg['user']['latitude'], cfg['user']['longitude'])
today_sr = sun.get_sunrise_time()
today_ss = sun.get_sunset_time()

start_time = datetime.time(hour=today_sr.hour, minute=today_sr.minute, second=today_sr.second)
end_time = datetime.time(hour=today_ss.hour, minute=today_ss.minute, second=today_ss.second)
current_time = datetime.datetime.now().time()

tesla = teslapy.Tesla(cfg['user']['mail'])
batteries = tesla.battery_list()
vehicles = tesla.vehicle_list()
battery = batteries[0]
car = vehicles[0]

if current_time < start_time:
    wait_for_start_time(start_time)
elif current_time > end_time:
    quit()

run_charging_loop(end_time)
