import click
import getpass
from pwgen import pwgen

from app.commands.email import send_adduser_email, send_reset_email
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

@userCommands.cli.command("setTelegram")
@click.argument("name")
@click.argument("telegram")
def setTelegram(name,telegram):
    user = mongo.db.users.find_one_and_update({'name': name},{'$set': {'telegram': telegram}})
    if user:
        print('Telegram atualizado')
    else:
        print("Ocorreu um erro.")

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
            "active": False,
            "gokopa": False,
            "sendEmail": False,
            "pago": False,
            "passwordActive": False
        }
        userCollection.insert(user)
        print('Usuário cadastrado com sucesso')
        print("Você foi cadastrado no sistema da Gokopa! Acesse pelo link: https://gokopa.leafarlins.com/")
        print(f'Usuário: {username}')
        print(f'Senha temporária: {password}')
        print(f'\nSeu nome no bolão será: {name}\nQualquer dúvida, entre em contato!')
        print("Enviando email...")
        send_adduser_email(username,password)

@userCommands.cli.command("resetPassword")
@click.argument("username")
@click.argument("test",required=False)
def reset_password(username,test=False):
    userCollection = mongo.db.users
    password = pwgen(10, symbols=False)
    #password = getpass.getpass()

    userExists = userCollection.find_one({"username": username})
    if userExists:
        userCollection.find_one_and_update({'username': username},{'$set': {"passwordActive": False, "password": generate_password_hash(password)}})
        print("Usuário teve senha resetada. Acesse pelo link: https://gokopa.leafarlins.com/")
        print(f'Usuário: {username}')
        print(f'Senha temporária: {password}')
        #if userExists["sendEmail"]:
        print("Enviando email de reset...")
        send_reset_email(username,password,test)
    else:
        print("Usuário não encontrado.")

@userCommands.cli.command("listUsers")
def list_users():
    lista_users = [u for u in mongo.db.users.find()]
    ativos = ""
    inativos = ""
    gokopa = ""
    pagos = ""
    sendemail = ""
    for u in lista_users:
        if u["active"]:
            ativos += " " + u["name"]
            if u.get("gokopa"):
                gokopa += " " + u["name"]
            if u.get("pago"):
                pagos += " " + u["name"]
        else:
            inativos += " " + u["name"]
        if u["sendEmail"]:
            sendemail += " " + u["name"]
    print(f'Lista de users active ativos:{ativos}')
    print(f'Lista de users active inativos:{inativos}')
    print(f'Lista de users gokopa:{gokopa}')
    print(f'Lista de users pago:{pagos}')
    print(f'Lista de users sendEmail:{sendemail}')

@userCommands.cli.command("activeUser")
@click.argument("user")
@click.argument("tipo")
@click.argument("status")
def list_users(user,tipo,status):
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
        userCollection.find_one_and_update({'name': user},{'$set': {tipo: atividade}})
        print("Usuário",user,"setado para status",tipo,"=",atividade)
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

@userCommands.cli.command("initMoedas")
@click.argument("nome")
@click.argument("moedas")
def init_moedas(nome,moedas):
    moedaColl = mongo.db.moedas
    moedaExists = moedaColl.find_one({"nome": nome})
    if moedaExists:
        print(f"Usuário {nome} já existe na base: {moedaExists}")
    else:
        novo_user = {
            "nome": nome,
            "saldo": int(moedas),
            "bloqueado": 0,
            "investido": 0
        }
        moedaColl.insert(novo_user)
        print(f"Inserido user {nome} com {moedas} moedas na base.")



