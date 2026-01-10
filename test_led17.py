from gpiozero import LED
from time import sleep

led = LED(17)
while True:
    led.on()
    print("LED Acceso")
    sleep(1)
    led.off()
    print("LED Spento")
    sleep(1)
