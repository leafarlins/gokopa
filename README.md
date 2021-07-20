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

## Deploy in production

`git remote add stage git@heroku.com:YOUR_APP_NAME.git`

Deploy in heroku: `git push stage master` or `git push pro master`
