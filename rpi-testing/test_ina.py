from time import sleep
from ina219 import INA219, DeviceRangeError

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 1.0
PROSUMER = 0x40
CONSUMER = 0x41

ina_prosumer = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=PROSUMER)
ina_prosumer.configure(voltage_range=ina.RANGE_32V,
                       gain=ina.GAIN_AUTO,
                       bus_adc=ADC_128SAMP,
                       shunt_adc=ADC_128SAMP)

ina_consumer = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=CONSUMER)
ina_consumer.configure(voltage_range=ina.RANGE_32V,
                       gain=ina.GAIN_AUTO,
                       bus_adc=ADC_128SAMP,
                       shunt_adc=ADC_128SAMP)

try:
    while 1:
        pv = ina_prosumer.voltage()
        pi = ina_prosumer.current()
        pp = ina_prosumer.power()

        cv = ina_consumer.voltage()
        ci = ina_conusmer.current()
        cp = ina_consumer.power()

        print("PROSUMER:\n{} V\n{} mA\n{} mW\n".format(pv, pi, pp))
        print("CONSUMER:\n{} V\n{} mA\n{} mW\n".format(cv, ci, cp))

        sleep(2)

except KeyboardInterrupt:
    print("\nCtrl-C pressed. Program exiting...")
