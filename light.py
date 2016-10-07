import pytz
import datetime
import time
import urllib2
import json
import os
import xml.etree.ElementTree as ET
import RPi.GPIO as GPIO
import time
import sys

IN_PROGRESS = "in-progress"
PRE_GAME = "pre-game"
FINAL = "final"
DELAYED = "delayed"

HOUR = 3600

team = str(sys.argv[1])
league = str(sys.argv[2])
video_delay = 0
time_zone = "US/Eastern"
light = False

# blinking function
def blink(pin):
        GPIO.setmode(GPIO.BOARD)
        if video_delay>0:
                 print("Delay is " + str(video_delay) + " ...pausing")
                 time.sleep(video_delay)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin,GPIO.HIGH)
        time.sleep(3)
        GPIO.output(pin,GPIO.LOW)
        time.sleep(1)
        GPIO.cleanup()
        return

def sound():
        os.system("omxplayer -o local ~/goallight/alert.wav")
        return

def alert(scored):
        if scored:
                score()
        else:
                fail()

def score():
        os.system("omxplayer -o local ~/goallight/goalhorn.mp3")
        return

def fail():
        os.system("omxplayer -o local ~/goallight/fail.mp3")
        return

url = 'http://scores.nbcsports.msnbc.com/ticker/data/gamesMSNBC.js.asp?jsonp=true&sport=%s&period=%d'

def today(score_for, score_against, firstTime):
  yyyymmdd = int(datetime.datetime.now(pytz.timezone(time_zone)).strftime("%Y%m%d"))

  delay = HOUR * 6
  isPlaying = False;
  
  try:
    print ((url % (league, yyyymmdd)))
    f = urllib2.urlopen(url % (league, yyyymmdd))

    jsonp = f.read()
    f.close()
    json_str = jsonp.replace('shsMSNBCTicker.loadGamesData(', '').replace(');', '')
    json_parsed = json.loads(json_str)

    os.environ['TZ'] = time_zone
    
    now = int(time.time())
    nowDT = datetime.datetime.fromtimestamp(now).strftime("%d/%m/%y %H:%M:%S")

    print("------------------------------------------------------------------------")
    print ("Current Time: " + nowDT)
    print("------------------------------------------------------------------------")
    
    for game_str in json_parsed.get('games', []):
      game_tree = ET.XML(game_str)
      
      away_tree = game_tree.find('visiting-team')
      home_tree = game_tree.find('home-team')
      
      gamestate_tree = game_tree.find('gamestate')
      
      home = home_tree.get('nickname').lower()
      away = away_tree.get('nickname').lower()

      home_score = int(home_tree.get('score')) if home_tree.get('score') != "" else 0
      away_score = int(away_tree.get('score')) if away_tree.get('score') != "" else 0

      status = gamestate_tree.get('status').lower();

      isHome = home.find(team) != -1;
      isAway = away.find(team) != -1;
      isPreGame = status.find(PRE_GAME) != -1;
      isFinal = status.find(FINAL)!=-1;
      isInProgress =  status.find(IN_PROGRESS)!=-1
      isDelayed = status.find(DELAYED) != -1

      gametime = gamestate_tree.get('gametime');
      
      start = int(time.mktime(time.strptime('%s %d' % (gametime, yyyymmdd), '%I:%M %p %Y%m%d')))
      
      timediff = start - now

      startDT = datetime.datetime.fromtimestamp(start).strftime("%d/%m/%y %H:%M:%S")

      if isHome or isAway:
              
                print("------------------------------------------------------------------------")
                print(away + ":" + str(away_score) + " @ " + home + ":" + str(home_score) + " | " + status)
                print("Start Time: " + startDT)
                print("------------------------------------------------------------------------")
               
                nickname = home if isHome else away

                if isPreGame:
                        print("------------------------------------------------------------------------")
                        print(nickname + " are playing in " + str(timediff / 60) + " minutes")

                        if (start - now) < HOUR:
                                print(nickname + " are playing whithin the next hour, setting refresh delay to 60 seconds")
                                delay = 60
                        else:
                                print(nickname + " are playing later today, setting refresh delay to 30 minutes")
                                delay = HOUR / 2
                        print("------------------------------------------------------------------------")

                if isInProgress:
                        print("------------------------------------------------------------------------")
                        print(nickname + " are currently playing, setting refresh to 10 seconds")
                        print("------------------------------------------------------------------------")
                        delay = 10

                if isDelayed:
                       print("------------------------------------------------------------------------")
                       print(nickname + " are currently delayed, setting refresh to 1 minute")
                       print("------------------------------------------------------------------------")
                       delay = HOUR / 60 

                #check the score no matter the game state
                h = home_score if isHome else away_score
                if h > score_for and not firstTime:
                        print("------------------------------------------------------------------------")
                        print(nickname + " score!")
                        print("------------------------------------------------------------------------")
                        alert(true)
                score_for = h

                a = away_score if isHome else home_score
                if a > score_against and not firstTime:
                        print("------------------------------------------------------------------------")
                        print(nickname + " score on :(")
                        print("------------------------------------------------------------------------")
                        alert(false)
                score_against = a

                if isFinal:
                        print("------------------------------------------------------------------------")
                        print(nickname + " are done playing today, setting refresh delay to 12 hours")
                        print("------------------------------------------------------------------------")
                        delay = HOUR * 12
                        
                        if not firstTime:
                                alert(score_for > score_against)
      else:
               print(away + ":" + str(away_score) + " @ " + home + ":" + str(home_score) + " | " + status)
               print("Start Time: " + startDT)

  except Exception as e:
    print e

  return (delay, score_for, score_against);

if __name__ == "__main__":

        score_for = 0
        score_against = 0
        firstTime = True
        
        while True:
            t = today(score_for, score_against, firstTime)
            delay = t[0]
            score_for = t[1]
            score_against = t[2]
            
            firstTime = False
            
            print("Current Delay: " + str(delay) + " seconds")
            time.sleep(delay)
