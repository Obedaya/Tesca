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
            break


def run_charging_loop(start_time, end_time):
    print("Starting loop...")
    calculateAverage(calculateCharging())
    while datetime.datetime.now().time() < end_time:
        amp = calculateAverage(currently)
        # setTeslachargingAmp(amp)
    print("Ending loop...")

def chargingPossible(data, cardata) -> bool:
    # Only charge if the power production + buffer (0,1kW) - the car charging power, is higher than the power being used
    if (data['power_reading'][0]['load_power'] + cfg['technical']['buffer']) - (cardata['charge_state']['charger_power'] * 1000) >= data['power_reading'][0]['solar_power']:
        return False
    else:
        return True


def wallboxAmpLimit(possibleAmp):
    if cfg['technical']['min_charging_amp'] <= possibleAmp <= cfg['technical']['max_charging_amp']:
        return possibleAmp
    elif possibleAmp > cfg['technical']['max_charging_amp']:
        return cfg['technical']['max_charging_amp']
    else:
        return 0


def calculateChargingAmp(data, cardata):
    if chargingPossible(data, cardata):
        # Overhead power gets calculated by:
        # subtracting the load power (power which is being used) + buffer (0,1kW) - the power which is being drained currently by the car,
        # of the power which gets generated
        overheadPower = data['power_reading'][0]['solar_power'] - (data['power_reading'][0]['load_power'] + cfg['technical']['buffer'] - (cardata['charge_state']['charger_power'] * 1000))
        teslaChargingPower = (data['percentage_charged'] / 100) * overheadPower
        teslaChargingAmperage = math.floor(teslaChargingPower / cfg['technical']['mains_voltage'])
        chargingAmp = wallboxAmpLimit(teslaChargingAmperage)
        return chargingAmp
    else:
        print("Not enough power. Won't charge!")
        return 0


def calculateCharging():
    print(battery)
    data = battery.get_battery_data()
    cardata = car.get_vehicle_data()
    print("----------------------------------------")
    chargingAmp = wallboxAmpLimit(calculateChargingAmp(data, cardata))
    print(str(data['power_reading'][0]['timestamp']))
    print("Charging possible with: " + str(chargingAmp))
    print("----------------------------------------")
    return chargingAmp


def calculateAverage(currentamp):
    previous = currentamp
    time.sleep(cfg['technical']['sleep_time'])
    currently = calculateCharging()
    chargingAmp = previous + currently / 2
    return chargingAmp


# Function to control charging of the car
def setTeslachargingAmp(chargingAmp):
    cardata = car.get_vehicle_data()
    if chargingAmp > 0:
        if cardata['charge_state']['charging_state'] != 'Charging':
            car.command('START_CHARGE')
        car.command('CHARGING_AMPS', charging_amps=chargingAmp)
        print("Charging with: " + str(chargingAmp))
    elif cardata['charge_state']['charging_state'] == 'Charging':
        car.command('STOP_CHARGE')
        print("Not enough power. Charging stopped!")
    else:
        print("Not enough power. Won't charge!")


with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=FullLoader)

previous = 0
currently = 0
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

if start_time > current_time > end_time:
    wait_for_start_time(start_time)

run_charging_loop(start_time, end_time)
