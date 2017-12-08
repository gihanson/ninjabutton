import threading, time, json
import RPi.GPIO as GPIO
from flask import Flask, request, Response
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

app = Flask(__name__)

DOME = 23
BUZZER = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(DOME, GPIO.IN, pull_up_down=GPIO.PUD_UP)  #dome button to GPIO23
GPIO.setup(BUZZER, GPIO.OUT)  # to GPIO24

buzzerLock = threading.Lock()
stateLock = threading.Lock()

startTime = 0.0
endTime = 0.0

STATE = 0
WAIT = 1
START = 2
STARTED = 3
DONE = 4
RESET = 5

@app.route('/health', methods=['GET'])
def health():
    print "checking health status of system"
    dStatus = 404
    fStatus = 404
    try:
        d = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        d.mount('http://', HTTPAdapter(max_retries=retries))
        dResp = d.get("http://noisemakerpi/health")
        dStatus = dResp.status_code
    except:
        print "Error connecting to noisemakerpi"

    try:
        f = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        f.mount('http://', HTTPAdapter(max_retries=retries))
        fResp = f.get("http://finisherbuttonpi/health")
        fStatus = fResp.status_code
    except:
        print "Error connecting to finisherbuttonpi"

    if fResp.status_code == requests.codes.ok and dResp.status_code == requests.codes.ok:
        return Response(status=200)

    data = {
        "finish_status": fStatus,
        "display_status": dStatus,
    }
    js = json.dumps(data)
    return Response(js, status=200, mimetype='application/json')

@app.route('/stop', methods=['POST'])
def stop():
    global STATE, stateLock
    print "STOP signal received"
    try:
        data = json.loads(request.data)
        with stateLock:
            endTime = data['stop_time']
            STATE = DONE
    except:
        endTime = time.time()
        STATE = DONE
        print "error getting stop time"
    return Response(status=200)

def resetSystem():
    dStatus = 404
    fStatus = 404
    try:
        d = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        d.mount('http://', HTTPAdapter(max_retries=retries))
        dResp = d.post("http://noisemakerpi/reset")
        dStatus = dResp.status_code
    except:
        print "Error connecting to noisemakerpi"

    try:
        f = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        f.mount('http://', HTTPAdapter(max_retries=retries))
        fResp = f.post("http://finisherbuttonpi/reset")
        fStatus = fResp.status_code
    except:
        print "Error connecting to finisherbuttonpi"

    if fResp.status_code == requests.codes.ok and dResp.status_code == requests.codes.ok:
        print "WARNING system in a bad state"

def playBuzzer(lock):
    with lock:
        i = 0
        while i < 3:
            #turn buzzer on
            GPIO.output(24, True)
            time.sleep(1)
            #turn off buzzer
            GPIO.output(24, False)
            time.sleep(1)

        GPIO.output(24, True)
        time.sleep(3)
        GPIO.output(24, False)

def notifyStop():
    global startTime
    payload = {"start_time": startTime}
    headers = {'content-type': 'application/json'}
    try:
        s = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        resp = s.post("http://stopbuttonpi/start", data=json.dumps(payload), headers=headers)
        if response.status_code != requests.codes.ok:
            print "Error notifying stop"
    except:
        print "Error exception occurred notifying display"

def notifyDisplay():
    global startTime
    payload = {"start_time": startTime}
    headers = {'content-type': 'application/json'}
    try:
        s = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        resp = s.post("http://noisemakerpi/start", data=json.dumps(payload), headers=headers)
        if response.status_code != requests.codes.ok:
            print "Error notifying display"
    except:
        print "Error exception occurred notifying display"

# def start():
#     global startButtonPressed, buzzerLock, startTime
#
#     while not startButtonPressed:
#         time.sleep(0.1)
#
#     d = threading.Thread(target=notifyDisplay)
#     d.daemon = True
#     f = threading.Thread(target=notifyStop)
#     f.daemon = True
#
#     playBuzzer(buzzerLock)
#     startTime = time.time()
#     n.start()
#     d.start()
#
#     while not doneSignal:
#         time.sleep(.01)
#
#     while not stopSignal:
#         time.sleep(.01)
#
#     reset()

def waitForStart():
    global STATE, WAIT, START, STARTED, startTime

    while True:
        if STATE == WAIT :
            time.sleep(0.1)
        elif STATE == START :
            d = threading.Thread(target=notifyDisplay)
            d.daemon = True
            f = threading.Thread(target=notifyStop)
            f.daemon = True
            playBuzzer(buzzerLock)
            startTime = time.time()
            n.start()
            d.start()
            STATE = STARTED
        elif STATE == STARTED:
            time.sleep(0.1)
        elif STATE == RESET:
            #call reset on finisher and noise
            resetSystem()
            STATE = DONE
        elif STATE == DONE :
            print "Finished one iteration"
            STATE = WAIT

def waitForButtonPress():
    global stateLock, STATE
    prevState = True
    button_state = True
    buttonPushTime = 0.0
    while True:
        prevState = button_state
        button_state = GPIO.input(DOME)
        if button_state == False and prevState == True:
            # button pressed
            buttonPushTime = time.time()
            print "START button pressed"
        elif button_state == True and prevState == False:
            # button released
            print "START button released"
            if STATE == WAIT:
                with stateLock:
                    STATE = START
            elif STATE == STARTED:
                if (time.time() - buttonPushTime) >= 4:
                    # reset state
                    print "RESET button press detected"
                    with stateLock:
                        STATE = RESET
        time.sleep(.5)

if __name__ == '__main__':
    try:
        s = threading.Thread(target=waitForStart)
        s.daemon = True
        s.start()

        b = threading.Thread(target=waitForButtonPress)
        b.daemon = True
        b.start()

        #start flask server
        app.run(port=9080, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print "caught keyboard interrupt"
    finally:
        GPIO.cleanup()