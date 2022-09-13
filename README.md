# gokopa
Gokopa is a soccer tournament simulated by videogame, with tables, statistics, rankings.

This is an app to allow users to bet in the Gokopa's games. It could be adapted for beting in other championships.

Create venv: `pip install -r requirements.txt`

Work in the environment: `source venv/bin/activate`
To leave: `deactivate`

Generate requirements: `pip freeze > requirements.txt`

## Database

The database is creating importing the files in dataset, using flask commands.

The database used is a mongodb server.

Create the vars in .env file with 

```
FLASK_APP=app/app.py
FLASK_ENV=development
MONGO_URI="mongodb+srv://...
SECRET_KEY="somesecretkey"
```

Load the dataset for past games with last db dump files, in dataset/dump.

Execute initial script for this version.

```
cat dataset/initial_db | sh
```

Or migrate using the corresponding file in dataset/migrations, when upgrading.

## Initialize app and create users

Create users for the app. For each user:

```
flask user addUser <username> <name>
```

Activate user in app and/or in gokopa score board.

```
flask user activeUser <name> active true
flask user activeUser <name> gokopa true
```

## Update app games

Set final score for each game

```
flask jogos editJogo 20 1 placar 0 1
flask jogos editJogo 20 2 placar 2 2
flask jogos editJogo 20 2 tr 1 1
flask jogos editJogo 20 2 pe 2 3
flask jogos editJogo 20 3 placar 1 2
flask jogos editJogo 20 3 tr 1 1
```

Set classified (replace team in each description). Examples:

```
flask time editTime Islândia p3A-EUR
flask time editTime Áustria p2B-EUR
```

Run command to create score history of the day

```
flask config setHistory
```

## Deploy in production

Made using docker-compose template and docker containers.
