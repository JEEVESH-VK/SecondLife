# name|category|weight_g (approx)|price_inr (approx, used only for cost estimates)
COMPONENTS = """Arduino Uno|Microcontroller|25|450
Arduino Nano|Microcontroller|7|300
ESP32|Microcontroller|10|450
Raspberry Pi|Microcontroller|45|3500
LED|Output|1|2
RGB LED|Output|1|8
Resistor|Passive|1|1
Capacitor|Passive|2|3
Buzzer|Output|3|25
Push Button|Input|2|5
Servo Motor|Actuator|9|150
DC Motor|Actuator|20|80
Stepper Motor|Actuator|35|350
Ultrasonic Sensor|Sensor|9|80
IR Sensor|Sensor|5|40
LDR Sensor|Sensor|1|15
Temperature Sensor|Sensor|2|60
Soil Moisture Sensor|Sensor|6|60
Relay Module|Module|15|70
LCD Display|Display|40|250
OLED Display|Display|4|300
Breadboard|Prototyping|40|90
Jumper Wires|Prototyping|15|60
Potentiometer|Input|4|15
9V Battery|Power|45|50
Battery Holder|Power|12|30
Old USB Cable|Salvaged|40|50
Old Computer Fan|Salvaged|90|200
Old Mobile Charger|Salvaged|60|150
Old Speaker|Salvaged|150|200
Old Webcam|Salvaged|100|400
Old Keyboard|Salvaged|500|400
Old Mouse|Salvaged|90|200"""

# name | difficulty | description | educational value | requirements | build steps (';'-separated)
PROJECTS = [
("Smart Automatic Dustbin","Beginner","Opens a dustbin lid automatically when a hand or object comes close.","Teaches distance sensing, servo control and thresholds.","Arduino Uno:1,Ultrasonic Sensor:1,Servo Motor:1,LED:1","Mount the ultrasonic sensor on the bin rim;Attach the servo to the lid hinge;Wire sensor, servo and LED to the Arduino;Open the lid when distance < 20 cm, close after 3 s"),
("Smart Plant Watering System","Intermediate","Reads soil moisture and switches a small low-voltage pump or motor.","Teaches analog sensing, relays and closed-loop control.","Arduino Uno:1,Soil Moisture Sensor:1,Relay Module:1,DC Motor:1","Calibrate the sensor in dry and wet soil;Wire the relay to a low-voltage (5-9V) DC motor/pump only;Switch the relay when moisture falls below the threshold;Add a maximum run time so it never overwaters"),
("Obstacle Detection System","Beginner","Detects nearby obstacles and warns with light and sound.","Teaches ultrasonic ranging and alert design.","Arduino Uno:1,Ultrasonic Sensor:1,Buzzer:1,LED:1","Wire the ultrasonic sensor, buzzer and LED;Read distance every 100 ms;Beep faster as the obstacle gets closer;Light the LED under 15 cm"),
("Automatic Night Lamp","Beginner","Turns a light on when ambient light drops.","Teaches voltage dividers and analog inputs.","Arduino Uno:1,LDR Sensor:1,LED:2,Resistor:2","Build a voltage divider with the LDR and a resistor;Read it on an analog pin;Pick a darkness threshold;Drive the LEDs through resistors"),
("Mini Security Alarm","Beginner","Sounds an alert when an IR beam is interrupted.","Teaches digital sensing and alarm logic.","Arduino Uno:1,IR Sensor:1,Buzzer:1,LED:1","Aim the IR sensor across a doorway;Read the digital output;Sound the buzzer and flash the LED on interruption;Add a push-button reset if you have one"),
("Smart Parking Indicator","Intermediate","Shows whether a parking slot is free using distance sensing.","Teaches state machines and sensor filtering.","Arduino Uno:1,Ultrasonic Sensor:1,LED:2,Buzzer:1","Mount the sensor facing the slot;Average several readings to remove noise;Green LED = free, red LED = occupied;Beep when a car gets too close"),
("Temperature Monitoring System","Beginner","Displays live room temperature on a screen.","Teaches sensor calibration and display interfacing.","Arduino Uno:1,Temperature Sensor:1,LCD Display:1,Potentiometer:1","Wire the LCD in 4-bit mode with a contrast potentiometer;Read and convert the sensor value to degrees C;Print it every second;Average readings for stability"),
("Mini Desk Fan Controller","Intermediate","Runs a salvaged 5-12V fan only when the room gets warm.","Teaches thermostat control and driving loads via relay.","Arduino Uno:1,Old Computer Fan:1,Relay Module:1,Temperature Sensor:1","Use a low-voltage PC fan (never mains);Switch it with the relay from a separate DC supply;Turn on above a set temperature;Add hysteresis so it does not chatter"),
("Electronic Reaction Game","Beginner","A reaction-time game: press the button as soon as the LED lights.","Teaches timing, randomness and debouncing.","Arduino Uno:1,LED:1,Push Button:1,Buzzer:1","Wire the LED, button and buzzer;Wait a random delay then light the LED;Measure time until the button press;Beep and report the reaction time"),
("Smart Door Alert","Beginner","Alerts you when a door is opened.","Teaches proximity sensing and event detection.","Arduino Uno:1,IR Sensor:1,Buzzer:1,LED:1","Fix the IR sensor at the door frame;Detect the door leaving the sensor's range;Chime and flash the LED;Silence after a few seconds"),
("Salvaged Speaker Tone Player","Beginner","Plays melodies and tones on an old speaker.","Teaches PWM, frequencies and simple audio.","Arduino Nano:1,Old Speaker:1,Push Button:2,Resistor:1","Connect the speaker through a resistor to a PWM pin;Define note frequencies;Use one button to play and one to change tune;Experiment with your own melodies"),
("Pi Webcam Monitor","Intermediate","Turns an old webcam and Raspberry Pi into a simple monitoring camera.","Teaches Linux, USB devices and video streaming.","Raspberry Pi:1,Old Webcam:1,Old USB Cable:1,Old Mobile Charger:1","Use a working 5V charger as-is (never open it);Plug in the webcam;Install a streaming tool such as motion;View the stream from a browser on your local network"),
]
