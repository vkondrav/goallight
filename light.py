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

HOUR = 3600

team = str(sys.argv[1])
league = str(sys.argv[2])
video_delay = 0
time_zone = "US/Pacific"
light = False

print(team)
print(league)

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
        os.system("omxplayer ~/Documents/goallight/alert.wav")
        return

def alert():
        if light:
                blink(12)
        else:
                sound()

url = 'http://scores.nbcsports.msnbc.com/ticker/data/gamesMSNBC.js.asp?jsonp=true&sport=%s&period=%d'

def today(score):
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
    
    for game_str in json_parsed.get('games', []):
      game_tree = ET.XML(game_str)
      
      away_tree = game_tree.find('visiting-team')
      home_tree = game_tree.find('home-team')
      
      gamestate_tree = game_tree.find('gamestate')
      
      home = home_tree.get('nickname').lower()
      away = away_tree.get('nickname').lower()

      home_score = home_tree.get('score')
      away_score = away_tree.get('score')

      status = gamestate_tree.get('status').lower();

      isHome = home.find(team) != -1;
      isAway = away.find(team) != -1;
      isPreGame = status.find(PRE_GAME) != -1;
      isFinal = status.find(FINAL)!=-1;
      isInProgress =  status.find(IN_PROGRESS)!=-1

      os.environ['TZ'] = "US/Eastern"
      
      start = int(time.mktime(time.strptime('%s %d' % (gamestate_tree.get('gametime'), yyyymmdd), '%I:%M %p %Y%m%d')))

      del os.environ['TZ']

      now = int(time.time())
      timediff = start-now
      
      print("Start time is " + str(start) + " and current time is " + str(now))

      if isHome or isAway:
              
                print("------------------------------------------------------------------------")
                print(away + ":" + away_score + " @ " + home + ":" + home_score + " | " + status)
                print("------------------------------------------------------------------------")
               
                nickname = home if isHome else away

                if isPreGame:
                        print(nickname + "are playing in " + str(timediff / 60) + " minutes")

                        if (start-now) < HOUR:
                                print(home + " are playing whithin the next hour, setting refresh delay to 60 seconds")
                                delay = 60
                        else:
                                print(nickname + " are playing later today, setting refresh delay to 30 minutes")
                                delay = HOUR / 2
                        
                if isFinal:
                        print(nickname + " are done playing today, setting refresh delay to 6 hours")
                        delay = HOUR * 6

                if isInProgress:
                        print(home + "are currently playing, setting refresh to 10 seconds")
                        isPlaying = True;
                        n = home_score if isHome else away_score
                        delay = 10

                        if n > score:
                                print(nickname + " score! old score: " + str(score) + " and new score: " + n)
                                score = n
                                alert()
      else:
               print(away + ":" + away_score + " @ " + home + ":" + home_score + " | " + status)    

  except Exception, e:
    print e

  return (isPlaying, delay, score);

if __name__ == "__main__":

        score = 0
        
        while True:
            t = today(score)
            isPlaying = t[0]
            delay = t[1]
            score = t[2]
            
            if not isPlaying:
                print("Your team is not playing today or unable to get data, setting refresh to 6 hours")

            print(str(delay) + " seconds")
            time.sleep(delay)
