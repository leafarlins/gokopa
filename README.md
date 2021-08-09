# gokopa
Gokopa is a soccer tournament simulated by videogame, with tables, statistics, rankings.

This is an app to allow users to bet in the Gokopa's games. It could be adapted for beting in other championships.

Work in the environment: `source venv/bin/activate`
To leave: `deactivate`

Generate requirements: `pip freeze > requirements.txt`

## Database

The database is creating importing the files in dataset, using flask commands.

The database used is a mongodb server, hosted in Atlas Cloud.

Create the vars in .env file with 

```
FLASK_APP=app/app.py
FLASK_ENV=development
MONGO_URI="mongodb+srv://...
SECRET_KEY="somesecretkey"
```

Load the dataset for past games (Gokopas 1 to 19) and load last ranking

```
flask jogos loadCsv dataset/jogos_ano1a18.csv
flask jogos loadCsv dataset/jogos_ano19.csv
flask jogos loadCsv dataset/jogos_ano20_pt1v2_prod.csv
flask jogos loadCsv dataset/rank_19-3.csv
```

Read dataset/history file to run commands and load historic results.

## Initialize app and create users


Init database for betting

```
flask jogos initApostas20
```

Create users for the app. For each user:

```
flask user addUser <username> <name>
```

Set final score for each game

```
flask jogos editJogo 20 1 placar 0 1
flask jogos editJogo 20 2 placar 2 2
flask jogos editJogo 20 2 tr 1 1
flask jogos editJogo 20 2 pe 2 3
flask jogos editJogo 20 3 placar 1 2
flask jogos editJogo 20 3 tr 1 1
```


## Deploy in production

`git remote add stage git@heroku.com:YOUR_APP_NAME.git`

Deploy in heroku: `git push stage master` or `git push pro master`
