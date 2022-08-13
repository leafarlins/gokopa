import click
import getpass
from pwgen import pwgen
from ..extentions.database import mongo
from werkzeug.security import generate_password_hash
from flask import Blueprint

userCommands = Blueprint('user',__name__)

@userCommands.cli.command("getUser")
@click.argument("name")
def get_user(name):
    userCollection = mongo.db.users
    user = [u for u in userCollection.find({"name": name})]
    print(user)

@userCommands.cli.command("addUser")
@click.argument("username")
@click.argument("name")
def create_user(username,name):
    userCollection = mongo.db.users
    # Similar ao input, sem mostrar a digitação

    userExists = userCollection.find_one({"name": name})
    if userExists:
        print(f'Usuario {name} já existe')
    else:
        password = pwgen(10, symbols=False)
        user = {
        "username": username,
        "name": name,
        "password": generate_password_hash(password),
        "active": True,
        "passwordActive": False
    }
        userCollection.insert(user)
        print('Usuário cadastrado com sucesso')
        print("Você foi cadastrado no sistema da Gokopa! Acesse pelo link: https://gokopa.leafarlins.com/")
        print(f'Usuário: {username}')
        print(f'Senha temporária: {password}')
        print(f'\nSeu nome no bolão será: {name}\nQualquer dúvida, entre em contato!')

@userCommands.cli.command("resetPassword")
@click.argument("username")
def reset_password(username):
    userCollection = mongo.db.users
    password = pwgen(10, symbols=False)
    #password = getpass.getpass()

    userExists = userCollection.find_one({"username": username})
    if userExists:
        userCollection.find_one_and_update({'username': username},{'$set': {"passwordActive": False, "password": generate_password_hash(password)}})
        print("Usuário teve senha resetada. Acesse pelo link: https://gokopa.leafarlins.com/")
        print(f'Usuário: {username}')
        print(f'Senha temporária: {password}')
    else:
        print("Usuário não encontrado.")

@userCommands.cli.command("listUsers")
def list_users():
    lista_users = [u for u in mongo.db.users.find()]
    ativos = ""
    inativos = ""
    for u in lista_users:
        if u["active"]:
            ativos += " " + u["name"]
        else:
            inativos += " " + u["name"]
    print(f'Lista de users ativos:{ativos}')
    print(f'Lista de users inativos:{inativos}')

@userCommands.cli.command("activeUser")
@click.argument("user")
@click.argument("status")
def list_users(user,status):
    if status == "true":
        atividade = True
    elif status == "false":
        atividade = False
    else:
        print("Informe true ou false para status.")
        return
    userCollection = mongo.db.users
    userExists = userCollection.find_one({"name": user})
    if userExists:
        userCollection.find_one_and_update({'name': user},{'$set': {"active": atividade}})
        print("Usuário setado para status active = ",atividade)
    else:
        print("Usuário não encontrado.")


@userCommands.cli.command("dropUser")
@click.argument("username")
def delete_user(username):
    userCollection = mongo.db.users
    userExists = userCollection.find_one({"username": username})
    if userExists:
        question = input(f'Deseja deletar o usuário {username}? (S/N) ')
        if question.upper() == "S":
            userCollection.delete_one({"username": username})
            print("Usuário deletado com sucesso!")
        else:
            exit()
    else:
        print("Usuário não encontrado.")

