# Belgrade Public Transit

## Usage

Activate virtual environment, install dependencies:

```bash
. venv/bin/activate
make req
```
then run required scripts

```bash
./script_name.py [options]
```

### Common options

- `-h`, `--help` - show help message
- `-q`, `--quiet` - suppress unnecessary messages
- `-v`, `--verbose` - show more messages

### Retrieve data

```bash
./retrieve.py
# or
./retrieve.py --force parse
```
### Get schedule

Nearest 30 minutes schedule for a stop name:
```bash
./schedule.py -n Kalemegdan
# or use Cyrillic name
./schedule.py -n Калемегдан
# or use short stop code
./schedule.py -n 5
# or use long stop ID
./schedule.py -n 20333
```
output example:
```
Date and time: 2026-01-02 23:50:03.206447
Service type: N (Sunday)
Schedule for Kalemegdan
23:52 Tm 🚋 2     Pristanište
23:52 Tm 🚋 2L    Pristanište
23:54 A  🚌 EKO2  Dorćol /SRC Milan Gale Muškatirović/
23:55 Tm 🚋 11    Kalemegdan /Donji grad/
24:03 Tm 🚋 2L    Pristanište
24:09 A  🚌 EKO2  Dorćol /SRC Milan Gale Muškatirović/
24:18 A  🚌 EKO2  Dorćol /SRC Milan Gale Muškatirović/
```

Nearest 30 minutes schedule for a stop name at a specific time:
```bash
./schedule.py -n Kalemegdan -d '2026-01-02 12:34'
# or
./schedule.py -n Kalemegdan -d 'in 2 hours'
# or
./schedule.py -n Kalemegdan -d 'через 3 часа'
```

Set interval in minutes:
```bash
./schedule.py -n Kalemegdan -i 60
# or even all day
./schedule.py -n Kalemegdan -d 'tomorrow midnight' -i 1500
```

## Configuration

Configuration file is [config.yml](config.yml)

## Source data

### Buses, trams, trolleybuses

GTFS data published at https://data.gov.rs/sr/datasets/gradski-javni-prevoz-u-beogradu-gtfs/

ZIP archive https://data.gov.rs/s/resources/gradski-javni-prevoz-u-beogradu-gtfs/20251031-111721/bgprev-belgrade-rs-2-.zip
has files:
- agency.txt — service providers
- calendar_dates.txt — exceptions to the rules in calendar.txt (incomplete)
- calendar.txt — rules for service types
- fare_attributes.txt — fare price groups
- fare_rules.txt — fare prices for routes A1 (now 400 RSD), E2, E6, E9 (now 200 RSD)
- feed_info.txt — feed information
- routes.txt — routes
- shapes.txt — coordinates of route points
- stops.txt — stops: names, coordinates
- stop_times.txt — arrival and departure times for stops
- trips.txt — trips: routes, service types

### City trains BG:VOZ

https://data.gov.rs/s/resources/bg-voz-red-vozhnje-1/20201231-104329/bg-voz-red-vozhnje.csv
