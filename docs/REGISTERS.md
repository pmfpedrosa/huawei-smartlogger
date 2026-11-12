# Register catalogue

Source: Huawei SmartLogger ModBus Interface Definitions, Issue 37 (2020-06-24).

Reserved and write-only registers are documented but are not selectable measurement entities.
Register 40742 uses mode 40741 to choose its scaling and unit. Remapped addresses are offsets.

| Group | Variable | Address / offset | Type | Unit | Gain | Registers | Access | Source page |
|---|---|---:|---|---|---:|---:|---|---:|
| logger | Date&Time | 40000 | U32 | — | 1 | 2 | RW | 3 |
| logger | City | 40002 | U32 | — | 1 | 2 | RW | 3 |
| logger | Daylight Saving Time (DST) | 40004 | U16 | — | 1 | 1 | RW | 3 |
| logger | Time Zone | 40005 | I32 | s | 1 | 2 | RO | 3 |
| logger | DST state | 40007 | U16 | — | 1 | 1 | RO | 3 |
| logger | DST offset | 40008 | U16 | min | 1 | 1 | RO | 3 |
| logger | The Local Time | 40009 | U32 | — | 1 | 2 | RO | 3 |
| logger | Power on | 40200 | U16 | — | 1 | 1 | WO | 3 |
| logger | Power off | 40201 | U16 | — | 1 | 1 | WO | 4 |
| logger | Power on/off | 40202 | U16 | — | 1 | 1 | WO | 4 |
| logger | Power on/off | 40203 | U16 | — | 1 | 1 | WO | 4 |
| logger | Transfer trip | 40204 | U16 | — | 1 | 1 | RW | 4 |
| logger | Array reset | 40205 | U16 | — | 1 | 1 | WO | 4 |
| logger | Active adjustment | 40420 | U32 | kW | 10 | 2 | RW | 4 |
| logger | Reactive adjustment | 40422 | I32 | kvar | 10 | 2 | RW | 4 |
| logger | Active adjustment | 40424 | U32 | kW | 10 | 2 | RW | 4 |
| logger | Reactive adjustment | 40426 | I32 | kvar | 10 | 2 | RW | 5 |
| logger | Active power adjustment by percentage | 40428 | U16 | % | 10 | 1 | RW | 5 |
| logger | Power factor adjustment | 40429 | I16 | — | 1000 | 1 | RW | 5 |
| logger | DC current | 40500 | I16 | A | 10 | 1 | RO | 5 |
| logger | Input power | 40521 | U32 | kW | 1000 | 2 | RO | 5 |
| logger | CO2 reduction | 40523 | U32 | kg | 10 | 2 | RO | 5 |
| logger | Active power | 40525 | I32 | kW | 1000 | 2 | RO | 5 |
| logger | Power factor | 40532 | I16 | — | 1000 | 1 | RO | 5 |
| logger | Plant status | 40541 | U16 | — | 1 | 1 | RO | 6 |
| logger | Plant status | 40542 | U16 | — | 1 | 1 | RO | 6 |
| logger | Plant status | 40543 | U16 | — | 1 | 1 | RO | 6 |
| logger | Reactive power | 40544 | I32 | kvar | 1000 | 2 | RO | 6 |
| logger | CO2 reduction | 40550 | U64 | kg | 100 | 4 | RO | 6 |
| logger | DC current 2 | 40554 | I32 | A | 10 | 2 | RO | 7 |
| logger | E-Total | 40560 | U32 | kWh | 10 | 2 | RO | 7 |
| logger | E-Daily | 40562 | U32 | kWh | 10 | 2 | RO | 7 |
| logger | Duration of daily power generation | 40564 | U32 | h | 10 | 2 | RO | 7 |
| logger | Plant status | 40566 | U16 | — | 1 | 1 | RO | 7 |
| logger | Plant status | 40567 | U16 | — | 1 | 1 | RO | 7 |
| logger | Active alarm sequence number | 40568 | U32 | — | 1 | 2 | RO | 7 |
| logger | Historical alarm sequence number | 40570 | U32 | — | 1 | 2 | RO | 8 |
| logger | Phase A current | 40572 | I16 | A | 1 | 1 | RO | 8 |
| logger | Phase B current | 40573 | I16 | A | 1 | 1 | RO | 8 |
| logger | Phase C current | 40574 | I16 | A | 1 | 1 | RO | 8 |
| logger | Uab | 40575 | U16 | V | 10 | 1 | RO | 8 |
| logger | Ubc | 40576 | U16 | V | 10 | 1 | RO | 8 |
| logger | Uca | 40577 | U16 | V | 10 | 1 | RO | 8 |
| logger | Reserved | 40608 | U16 | — | 1 | 10 | RO | 8 |
| logger | Inverter Efficiency | 40685 | U16 | % | 100 | 1 | RO | 8 |
| logger | Max. reactive adjustment | 40693 | U32 | kvar | 10 | 2 | RO | 8 |
| logger | Min. reactive adjustment | 40695 | I32 | kvar | 10 | 2 | RO | 8 |
| logger | Max. active adjustment | 40697 | U32 | kW | 10 | 2 | RO | 8 |
| logger | Locked | 40699 | U16 | — | 1 | 1 | RO | 9 |
| logger | DI status | 40700 | U16 | — | 1 | 1 | RO | 9 |
| logger | ESN | 40713 | STR | — | 1 | 10 | RO | 9 |
| logger | System reset | 40723 | U16 | — | 1 | 1 | WO | 9 |
| logger | Fast device access | 40724 | U16 | — | 1 | 1 | WO | 9 |
| logger | Device operation | 40725 | MLD | — | 1 | 11 | WO | 9 |
| logger | Device access status | 40736 | U16 | — | 1 | 1 | RO | 9 |
| logger | Active power control mode | 40737 | U16 | — | 1 | 1 | RO | 10 |
| logger | Active power scheduling target value | 40738 | U32 | kW | 10 | 2 | RO | 10 |
| logger | Reactive power control mode | 40740 | U16 | — | 1 | 1 | RO | 10 |
| logger | Reactive power scheduling curve mode | 40741 | U16 | — | 1 | 1 | RO | 11 |
| logger | Reactive power scheduling target value | 40742 | I32 | — | mode-dependent | 2 | RO | 11 |
| logger | Active scheduling percentage | 40802 | U32 | % | 1 | 2 | RO | 11 |
| logger | CO2 emission reduction coefficient | 41124 | U16 | kg/kWh | 1000 | 1 | RW | 11 |
| logger | PV module capacity | 41934 | U32 | kW | 1000 | 2 | RO | 11 |
| logger | Rated plant capacity | 41936 | U32 | kW | 1000 | 2 | RO | 11 |
| logger | Total rated capacity of grid-connected inverters | 41938 | U32 | kW | 1000 | 2 | RO | 11 |
| logger | Conversion coefficient | 41940 | U32 | — | 1000 | 2 | RO | 11 |
| logger | Communication status | 41942 | U16 | — | 1 | 1 | RO | 12 |
| logger | Communication abnormal shutdown | 41947 | U16 | — | 1 | 1 | RW | 12 |
| logger | Communication abnormal detection time | 41948 | U16 | s | 1 | 1 | RW | 12 |
| logger | Auto start upon communication recovery | 41949 | U16 | — | 1 | 1 | RW | 12 |
| logger | The SystemTime : year | 42017 | U16 | — | 1 | 1 | RW | 12 |
| logger | The SystemTime : month | 42018 | U16 | — | 1 | 1 | RW | 12 |
| logger | The SystemTime : day | 42019 | U16 | — | 1 | 1 | RW | 12 |
| logger | The SystemTime : hour | 42020 | U16 | — | 1 | 1 | RW | 12 |
| logger | The SystemTime : minute | 42021 | U16 | — | 1 | 1 | RW | 12 |
| logger | The SystemTime : second | 42022 | U16 | — | 1 | 1 | RW | 12 |
| logger | Current error during scanning | 42150 | U16 | — | 100 | 1 | RW | 12 |
| logger | Inspection | 42730 | U16 | — | 1 | 1 | WO | 13 |
| logger | IV curve scanning | 42779 | U16 | — | 1 | 1 | WO | 13 |
| logger | Alarm Info 1 | 50000 | U16 | — | 1 | 1 | RO | 13 |
| logger | Alarm Info 2 | 50001 | U16 | — | 1 | 1 | RO | 13 |
| logger | Alarm Info 3 | 50002 | U16 | — | 1 | 1 | RO | 13 |
| logger | Alarm Info 4 | 50003 | U16 | — | 1 | 1 | RO | 13 |
| emi | Wind speed (WSP) | 40031 | I16 | m/s | 10 | 1 | RO | 19 |
| emi | Wind direction (WD) | 40032 | I16 | ° | 1 | 1 | RO | 19 |
| emi | PV module temperature | 40033 | I16 | °C | 10 | 1 | RO | 19 |
| emi | Ambient temperature | 40034 | I16 | °C | 10 | 1 | RO | 19 |
| emi | Total irradiance | 40035 | I16 | W/m² | 10 | 1 | RO | 19 |
| emi | Daily irradiation amount | 40036 | U32 | MJ/m² | 1000 | 2 | RO | 19 |
| emi | Total irradiance 2 | 40038 | I16 | W/m² | 10 | 1 | RO | 19 |
| emi | Daily irradiation amount 2 | 40039 | U32 | MJ/m² | 1000 | 2 | RO | 19 |
| emi | Custom 1 | 40041 | I16 | — | 10 | 1 | RO | 19 |
| emi | Custom 2 | 40042 | I16 | — | 10 | 1 | RO | 19 |
| emi | Daily irradiation amount | 40043 | U32 | kWh/m² | 1000 | 2 | RO | 20 |
| emi | Daily irradiation amount 2 | 40045 | U32 | kWh/m² | 1000 | 2 | RO | 20 |
| meter | Phase A voltage | 32260 | U32 | V | 100 | 2 | RO | 20 |
| meter | Phase B voltage | 32262 | U32 | V | 100 | 2 | RO | 20 |
| meter | Phase C voltage | 32264 | U32 | V | 100 | 2 | RO | 20 |
| meter | A-B line voltage | 32266 | U32 | V | 100 | 2 | RO | 20 |
| meter | B-C line voltage | 32268 | U32 | V | 100 | 2 | RO | 20 |
| meter | C-A line voltage | 32270 | U32 | V | 100 | 2 | RO | 20 |
| meter | Phase A current | 32272 | I32 | A | 10 | 2 | RO | 20 |
| meter | Phase B current | 32274 | I32 | A | 10 | 2 | RO | 20 |
| meter | Phase C current | 32276 | I32 | A | 10 | 2 | RO | 20 |
| meter | Active power | 32278 | I32 | kW | 1000 | 2 | RO | 20 |
| meter | Reactive power | 32280 | I32 | kvar | 1000 | 2 | RO | 20 |
| meter | Active electricity(Reserved) | 32282 | I32 | kWh | 10 | 2 | RO | 20 |
| meter | Power factor | 32284 | I16 | — | 1000 | 1 | RO | 20 |
| meter | Reactive electricity(Reserved) | 32285 | I32 | kvarh | 10 | 2 | RO | 20 |
| meter | Apparent power | 32287 | I32 | kVA | 1000 | 2 | RO | 20 |
| meter | Positive active electricity(Reserved) | 32289 | I32 | kWh | 100 | 2 | RO | 20 |
| meter | Positive reactive electricity(Reserved) | 32291 | I32 | kvarh | 100 | 2 | RO | 21 |
| meter | Electricity in positive active electricity price segment 1 | 32299 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in positive active electricity price segment 2 | 32301 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in positive active electricity price segment 3 | 32303 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in positive active electricity price segment 4 | 32305 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in negative active electricity price segment 1 | 32307 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in negative active electricity price segment 2 | 32309 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in negative active electricity price segment 3 | 32311 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Electricity in negative active electricity price segment 4 | 32313 | I32 | kWh | 100 | 2 | RO | 21 |
| meter | Custom 1 | 32315 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 2 | 32317 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 3 | 32319 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 4 | 32321 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 5 | 32323 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 6 | 32325 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 7 | 32327 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 8 | 32329 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 9 | 32331 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Custom 10 | 32333 | I32 | — | 1000 | 2 | RO | 21 |
| meter | Phase A active power | 32335 | I32 | kW | 1000 | 2 | RO | 21 |
| meter | Phase B active power | 32337 | I32 | kW | 1000 | 2 | RO | 21 |
| meter | Phase C active power | 32339 | I32 | kW | 1000 | 2 | RO | 21 |
| meter | Total active electricity | 32341 | I64 | kWh | 100 | 4 | RO | 21 |
| meter | Total reactive electricity | 32345 | I64 | kvarh | 100 | 4 | RO | 21 |
| meter | Negative active electricity | 32349 | I64 | kWh | 100 | 4 | RO | 22 |
| meter | Negative reactive electricity | 32353 | I64 | kvarh | 100 | 4 | RO | 22 |
| meter | Positive active electricity | 32357 | I64 | kWh | 100 | 4 | RO | 22 |
| meter | Positive reactive electricity | 32361 | I64 | kvarh | 100 | 4 | RO | 22 |
| public | Device list change number | 65521 | U16 | — | 1 | 1 | RO | 22 |
| public | Port number | 65522 | U16 | — | 1 | 1 | RO | 22 |
| public | Device Address | 65523 | U16 | — | 1 | 1 | RO | 22 |
| public | Device name | 65524 | STR | — | 1 | 10 | RW | 22 |
| public | Device connection status | 65534 | U16 | — | 1 | 1 | RO | 22 |
| inverter_remap | Active power | 0 | I32 | kW | 1000 | 2 | RO | 23 |
| inverter_remap | Reactive power | 2 | I32 | kvar | 1000 | 2 | RO | 23 |
| inverter_remap | Total DC input current | 4 | I16 | A | 100 | 1 | RO | 23 |
| inverter_remap | Total input power | 5 | U32 | kW | 1000 | 2 | RO | 23 |
| inverter_remap | Insulation resistance | 7 | U16 | MΩ | 1000 | 1 | RO | 23 |
| inverter_remap | Power factor | 8 | I16 | — | 1000 | 1 | RO | 23 |
| inverter_remap | Inverter status | 9 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare8 | 10 | I16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Cabinet temperature | 11 | I16 | °C | 10 | 1 | RO | 24 |
| inverter_remap | Major Fault Code | 12 | U32 | — | 1 | 2 | RO | 24 |
| inverter_remap | Minor Fault Code | 14 | U32 | — | 1 | 2 | RO | 24 |
| inverter_remap | Warning Code | 16 | U32 | — | 1 | 2 | RO | 24 |
| inverter_remap | Spare1 | 18 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare2 | 19 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare3 | 20 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare4 | 21 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare5 | 22 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare6 | 23 | U16 | — | 1 | 1 | RO | 24 |
| inverter_remap | Spare7 | 24 | U16 | — | 1 | 1 | RO | 24 |
| emi_remap | Wind speed (WSP) | 0 | I16 | m/s | 10 | 1 | RO | 25 |
| emi_remap | Wind direction (WD) | 1 | I16 | ° | 1 | 1 | RO | 25 |
| emi_remap | PV module temperature | 2 | I16 | °C | 10 | 1 | RO | 25 |
| emi_remap | Ambient temperature | 3 | I16 | °C | 10 | 1 | RO | 25 |
| emi_remap | Total irradiance | 4 | I16 | W/m² | 10 | 1 | RO | 25 |
| emi_remap | Daily irradiation amount | 5 | U32 | MJ/m² | 1000 | 2 | RO | 25 |
| emi_remap | Total irradiance 2 | 7 | I16 | W/m² | 10 | 1 | RO | 25 |
| emi_remap | Daily irradiation amount 2 | 8 | U32 | MJ/m² | 1000 | 2 | RO | 25 |
| emi_remap | Custom 1 | 10 | I16 | — | 10 | 1 | RO | 25 |
| emi_remap | Custom 2 | 11 | I16 | — | 10 | 1 | RO | 25 |
| emi_remap | Daily irradiation amount | 12 | U32 | kWh/m² | 1000 | 2 | RO | 25 |
| emi_remap | Daily irradiation amount 2 | 14 | U32 | kWh/m² | 1000 | 2 | RO | 25 |
| emi_remap | Spare1 | 16 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare2 | 17 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare3 | 18 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare4 | 19 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare5 | 20 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare6 | 21 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare7 | 22 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare8 | 23 | U16 | — | 1 | 1 | RO | 25 |
| emi_remap | Spare9 | 24 | U16 | — | 1 | 1 | RO | 25 |
