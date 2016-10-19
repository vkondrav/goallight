from datetime import datetime, timedelta
from dateutil import tz
from urllib.request import urlopen
import json
import time
import sys
import os
import re
import pytz

IN_PROGRESS = "live"
PRE_GAME = "preview"
FINAL = "final"
DELAYED = "delayed"

HOUR = 3600

team = str(sys.argv[1])

def alert(scored):
        if scored:
                score()
        else:
                fail()

def score():
        os.system("omxplayer -o both ~/goallight/goalhorn.mp3")
        return

def fail():
        os.system("omxplayer -o both ~/goallight/fail.mp3")
        return

def tts(text):
        os.system("google_speech -l en '" + text + "'" + " -e overdrive 20")

def ttsGame(away, home, away_score, home_score):
        tts("." + away + ". " + str(away_score) + ". " + home + ". " + str(home_score))

url = "https://statsapi.web.nhl.com/api/v1/schedule?startDate=%s&endDate=%s&expand=schedule.linescore&site=en_nhlCA"

url_live = "https://statsapi.web.nhl.com/api/v1/game/%s/feed/live"

class Game:
        delay = 10
        score_for = 0
        score_against = 0
        firstTime = True
        lastStatus = ""
        arePlaying = False

        def isLastStatusInProgress(self):
                return self.lastStatus.find(IN_PROGRESS) != -1

def today(game):

	pacific = pytz.timezone('US/Pacific-New') #this timezone is good at covering all the nhl game dates
	pacificCorrected = datetime.now(pacific)

	print("------------------------------------------------------------------------")
	print("Pacific Corrected Time: " + pacificCorrected.strftime("%d/%m/%y %I:%M:%S %p"))
	print("------------------------------------------------------------------------")

	start_date = (pacificCorrected - timedelta(days=0)).strftime("%Y-%m-%d")
	end_date = (pacificCorrected + timedelta(days=0)).strftime("%Y-%m-%d")

	try:
		print (url % (start_date, end_date))

		f = urlopen(url % (start_date, end_date))
		j = json.loads(f.read().decode("utf-8"))
		f.close()

		now = datetime.now().timestamp()
		nowDT = datetime.now().strftime("%d/%m/%y %I:%M:%S %p")

		print("------------------------------------------------------------------------")
		print("Current Time: " + nowDT)
		print("------------------------------------------------------------------------")

		game.arePlaying = False
		if "dates" in j:
			for date in j["dates"]:

				if "games" in date:
					for g in date["games"]:

						pk = str(g["gamePk"])

						homeTeam = g["teams"]["home"]
						awayTeam = g["teams"]["away"]

						home = homeTeam["team"]["name"].lower()
						away = awayTeam["team"]["name"].lower()

						status = g["status"]["abstractGameState"].lower()
						gameDate = g["gameDate"]

						home_score = homeTeam["score"]
						away_score = awayTeam["score"]

						isHome = home.find(team.lower()) != -1;
						isAway = away.find(team.lower()) != -1;
						isPreGame = status.find(PRE_GAME) != -1;
						isFinal = status.find(FINAL)!= -1;
						isInProgress =  status.find(IN_PROGRESS)!= -1
						isDelayed = status.find(DELAYED) != -1

						utc = datetime.strptime(gameDate, "%Y-%m-%dT%H:%M:%SZ")
						utc = utc.replace(tzinfo=tz.tzutc())
						local = utc.astimezone(tz.tzlocal())

						start = local.timestamp()
						timediff = start - now

						startDT = local.strftime("%d/%m/%y %I:%M:%S %p")

						if isHome or isAway:

							game.arePlaying = True

							print("------------------------------------------------------------------------")
							print(away + ":" + str(away_score) + " @ " + home + ":" + str(home_score) + " | " + status)
							print("Start Time: " + startDT)
							print("------------------------------------------------------------------------")

							nickname = home if isHome else away

							print (url_live % pk)

							f = urlopen(url_live % pk)
							jlive = json.loads(f.read().decode("utf-8"))
							f.close

							lastPlay = "Not Available"

							try:
								lastPlay = jlive["liveData"]["plays"]["currentPlay"]["result"]["description"]
							except Exception as e:
								e #nothing to really do here

							print("------------------------------------------------------------------------")
							print("Last Play: " + lastPlay)
							print("------------------------------------------------------------------------")

							lastPlay = re.sub('\(.*?\)', '', lastPlay) #strip last play of goal/points

							if isPreGame:
								print("------------------------------------------------------------------------")
								print(nickname + " are playing in " + str(int(timediff / 60)) + " minutes")

								if (start - now) < HOUR:
									print(nickname + " are playing whithin the next hour, setting refresh delay to 60 seconds")
									game.delay = 60
								else:
									print(nickname + " are playing later today, setting refresh delay to 30 minutes")
									game.delay = HOUR / 2
								print("------------------------------------------------------------------------")

							if isInProgress:
								print("------------------------------------------------------------------------")
								print(nickname + " are currently playing, setting refresh to 10 seconds")
								print("------------------------------------------------------------------------")
								game.delay = 10

								if not game.isLastStatusInProgress():
									print("------------------------------------------------------------------------")
									print(nickname + " have started playing, setting refresh to 10 seconds")
									print("------------------------------------------------------------------------")
									tts(nickname + " have started playing")
									ttsGame(away, home, away_score, home_score)
							if isDelayed:
									print("------------------------------------------------------------------------")
									print(nickname + " are currently delayed, setting refresh to 1 minute")
									print("------------------------------------------------------------------------")
									game.delay = HOUR / 60 

							#check the score no matter the game state
							h = home_score if isHome else away_score

							if h > game.score_for and not game.firstTime:
								print("------------------------------------------------------------------------")
								print(nickname + " score!")
								print("------------------------------------------------------------------------")
								alert(True)
								ttsGame(away, home, away_score, home_score)
								tts(lastPlay)
							game.score_for = h

							a = away_score if isHome else home_score
							if a > game.score_against and not game.firstTime:
								print("------------------------------------------------------------------------")
								print(nickname + " scored on :(")
								print("------------------------------------------------------------------------")
								alert(False)
								ttsGame(away, home, away_score, home_score)
								tts(lastPlay)
							game.score_against = a

							if isFinal:
								print("------------------------------------------------------------------------")
								print(nickname + " are done playing today, setting refresh delay to 6 hours")
								print("------------------------------------------------------------------------")
								game.delay = HOUR * 6
	                                
								if not game.firstTime and game.isLastStatusInProgress():
									alert(game.score_for > game.score_against)
									tts(nickname + " have finished playing")
									ttsGame(away, home, away_score, home_score)
									tts(lastPlay)
	                                        
							game.lastStatus = status
						else:
							print(away + ":" + str(away_score) + " @ " + home + ":" + str(home_score) + " | " + status)
							print("Start Time: " + startDT)
	except Exception as e:
		print (e)

	if not game.arePlaying:
		print("------------------------------------------------------------------------")
		print(team + " are not playing today, setting refresh delay to 6 hours")
		print("------------------------------------------------------------------------")
		game.delay = HOUR * 6   
		
		game.firstTime = False

if __name__ == "__main__":

	game = Game()

	while True:
		today(game)

		print("Current Delay: " + str(game.delay) + " seconds")
		time.sleep(game.delay)