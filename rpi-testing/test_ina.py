from time import sleep
from ina219 import INA219, DeviceRangeError
from gpiozero import LED

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 1.0
PROSUMER = 0x40
CONSUMER = 0x41

ina_prosumer = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=PROSUMER)
ina_prosumer.configure(voltage_range=ina_prosumer.RANGE_32V,
                       gain=ina_prosumer.GAIN_AUTO,
                       bus_adc=ina_prosumer.ADC_128SAMP,
                       shunt_adc=ina_prosumer.ADC_128SAMP)

ina_consumer = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=CONSUMER)
ina_consumer.configure(voltage_range=ina_consumer.RANGE_32V,
                       gain=ina_consumer.GAIN_AUTO,
                       bus_adc=ina_consumer.ADC_128SAMP,
                       shunt_adc=ina_consumer.ADC_128SAMP)

led16 = LED(16)
led26 = LED(26)

try:
    while 1:
        pv = ina_prosumer.voltage()
        pi = ina_prosumer.current()
        pp = ina_prosumer.power()

        cv = ina_consumer.voltage()
        ci = ina_consumer.current()
        cp = ina_consumer.power()

        print("PROSUMER:\n{} V\n{} mA\n{} mW\n".format(pv, pi, pp))
        print("CONSUMER:\n{} V\n{} mA\n{} mW\n".format(cv, ci, cp))

        #ina_consumer.sleep()
        #ina_producer.sleep()
        led16.on()
        sleep(1)
        led26.on()
        led16.off()
        sleep(3)
        led26.off()
        #ina_consumer.wake()
        #ina.producer.wake()

except KeyboardInterrupt:
    print("\nCtrl-C pressed. Program exiting...")
