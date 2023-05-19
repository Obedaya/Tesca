import teslapy
import time
import math
import datetime
import yaml
import logging
from logging.handlers import TimedRotatingFileHandler
from yaml.loader import FullLoader
from suntime import Sun, SunTimeException


def wait_for_start_time(start_time):
    current_time = datetime.datetime.now().time()
    time_diff = datetime.datetime.combine(datetime.date.today(), start_time) - datetime.datetime.combine(datetime.date.today(), current_time)
    sleep_seconds = time_diff.total_seconds()
    sleep_hours_format, remainder = divmod(round(sleep_seconds), 3600)
    sleep_minutes_format, sleep_seconds_format = divmod(remainder, 60)

    formatted_time = "{:02d}:{:02d}:{:02d}".format(sleep_hours_format, sleep_minutes_format, sleep_seconds_format)

    if sleep_seconds > 0:
        print(f"Waiting for start time... Sleeping for {formatted_time}.")
        time.sleep(sleep_seconds)
    else:
        print("Start time already passed. Proceeding with the execution.")


def run_charging_loop(end_time):
    pwl_data = battery.get_battery_data()
    car_data = car.get_vehicle_data()
    print("Starting loop...")
    logger.info("|Solar power|House usage|Tesla percentage|Powerwall percentage|Tesla currently charging|Overhead "
                "power|Charging possible with|Charging with|")
    previous = calculate_charging(pwl_data, car_data)
    while datetime.datetime.now().time() < end_time.time():
        time.sleep(cfg['technical']['sleep_time'])
        pwl_data = battery.get_battery_data()
        car_data = car.get_vehicle_data()
        current = calculate_charging(pwl_data, car_data)
        amp = calculate_average(previous, current)
        set_tesla_charging_amp(wallbox_amp_limit(amp))
        log_data(pwl_data, car_data, amp)
        previous = current
    print("Ending loop...")


def charging_possible(pwl_data, car_data) -> bool:
    # Only charge if the power production + buffer (0,1kW) - the car charging power, is higher than the power being used
    if calculate_overhead_power(pwl_data, car_data) >= pwl_data['power_reading'][0]['solar_power']:
        return False
    else:
        return True


def calculate_overhead_power(pwl_data, car_data):
    return (pwl_data['power_reading'][0]['load_power'] + cfg['technical']['buffer']) - \
            (car_data['charge_state']['charger_power'] * 1000)


def wallbox_amp_limit(possible_amp):
    if cfg['technical']['min_charging_amp'] <= possible_amp <= cfg['technical']['max_charging_amp']:
        return possible_amp
    elif possible_amp > cfg['technical']['max_charging_amp']:
        return cfg['technical']['max_charging_amp']
    else:
        return 0


def calculate_charging_amp(pwl_data, car_data):
    if charging_possible(pwl_data, car_data) and car_data['charge_state']['charge_limit_soc'] \
            != car_data['charge_state']['battery_level']:
        # Overhead power gets calculated by:
        # subtracting the load power (power which is being used) + buffer (0,1kW)
        # - the power which is being drained currently by the car,
        # of the power which gets generated
        overhead_power = pwl_data['power_reading'][0]['solar_power'] \
                         - (pwl_data['power_reading'][0]['load_power']
                            + cfg['technical']['buffer']
                            - (car_data['charge_state']['charger_power'] * 1000))
        tesla_charging_power = (pwl_data['percentage_charged'] / 100) * overhead_power
        tesla_charging_amperage = math.floor(tesla_charging_power / cfg['technical']['mains_voltage'])
        return tesla_charging_amperage

        # Check if car already full
    elif car_data['charge_state']['charge_limit_soc'] == car_data['charge_state']['battery_level']:
        print("Already full. Won't charge!")
        return 0
    else:
        print("Not enough power. Won't charge!")
        return 0


def calculate_charging(pwl_data, car_data):
    print("----------------------------------------")
    charging_amp = calculate_charging_amp(pwl_data, car_data)
    print(str(pwl_data['power_reading'][0]['timestamp']))
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


def log_data(pwl_data, car_data, tesla_amp):
    log_string = (str(round(pwl_data['power_reading'][0]['solar_power']))
                  + ";" + str(round(pwl_data['power_reading'][0]['load_power']))
                  + ";" + str(round(car_data['charge_state']['battery_level']))
                  + ";" + str(round(pwl_data['percentage_charged']))
                  + ";" + str(round(car_data['charge_state']['charge_current_request']))
                  + ";" + str(round(calculate_overhead_power(pwl_data, car_data)))
                  + ";" + str(tesla_amp)
                  + ";" + str(wallbox_amp_limit(tesla_amp)))
    logger.info(log_string)


# Start of the main program

log_handler = TimedRotatingFileHandler('tesca.log', when='midnight', interval=1, backupCount=10)
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(log_handler)
logger.setLevel(logging.DEBUG)

print("========================================")
print(" _______ _______ _______ _______ _______")
print("    |    |______ |______ |       |_____|")
print("    |    |______ ______| |_____  |     |")
print("                                        ")
print("========================================")

with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=FullLoader)

sun = Sun(cfg['user']['latitude'], cfg['user']['longitude'])
today_sr = sun.get_sunrise_time() + datetime.timedelta(hours=cfg['user']['time_difference'])
today_ss = sun.get_sunset_time() + datetime.timedelta(hours=cfg['user']['time_difference'])

start_time = datetime.datetime.combine(datetime.date.today(), today_sr.time())
end_time = datetime.datetime.combine(datetime.date.today(), today_ss.time())
current_time = datetime.datetime.now()

tesla = teslapy.Tesla(cfg['user']['mail'])
batteries = tesla.battery_list()
vehicles = tesla.vehicle_list()
battery = batteries[0]
car = vehicles[0]

if current_time.time() < start_time.time():
    wait_for_start_time(start_time.time())
elif current_time.time() > end_time.time():
    quit()

run_charging_loop(end_time)
