# TeSCA

---
TeSCA (Tesla Solar Charging Automation) is a program that aims to charge your Tesla with excess solar energy. The goal is to charge both the Tesla and a Tesla Powerwall evenly. The script is written in Python and uses the Teslapy API.

## What you'll need

---
* Tesla (obviously)
* Tesla Powerwall
* Solar Plant

## Introduction

---
The goal is to charge the Powerwall and the Tesla evenly. 
The fuller the Powerwall is, the more power is given to the Tesla to charge.
The excess power should be used in such a way that the Tesla is charged but both the current daily demand is covered and the Powerwall is full at the end of the day so that it can supply the house through the night.

## How does it work?

---
The program takes several measurements in certain time intervals and calculates the average value from them. This value is adjusted again and again during the day and changes the charging power of the Tesla. If the excess power is too little or it is drawn from the grid or the Powerwall, then the Tesla is not charged. The program starts at sunrise and ends at sunset.

## Installation

---
Clone the repository:
```
git clone https://github.com/Obedaya/Tesla-Charging-Automation.git
```

In order to use the program you need to install all requirements:
```
pip install -r requirements.txt
```

## Usage

---
To use the program you need to configure the config file.

Run the script:
```
python main.py
```
It will automatically open your browser, where you'll have to sign in to your Tesla Account. Once your signed in, you'll see a "Page not found!" and have to copy the URL into the terminal.
