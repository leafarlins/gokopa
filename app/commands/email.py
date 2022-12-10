import json
import requests
import boto3
from botocore.exceptions import ClientError
import os
import click
import pymongo
from pymongo.collection import ReturnDocument
from ..extentions.database import mongo
from flask import Blueprint
from ..routes.backend import bet_report, get_users

emailCommands = Blueprint('email',__name__)

MONGO_URI = os.getenv('MONGO_URI')
TELEGRAM_TOKEN=os.getenv('TELEGRAM_TKN')
TELEGRAM_CHAT_ID=os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM=os.getenv('TELEGRAM')

# Replace sender@example.com with your "From" address.
# This address must be verified with Amazon SES.
SENDER = "Gokopa <gokopa@leafarlins.com>"
REPLYTO = ["leafarlins@gmail.com"]

# Replace recipient@example.com with a "To" address. If your account 
# is still in the sandbox, this address must be verified.
#RECIPIENT = "recipient@example.com"

# Specify a configuration set. If you do not want to use a configuration
# set, comment the following variable, and the 
# ConfigurationSetName=CONFIGURATION_SET argument below.
#CONFIGURATION_SET = "ConfigSet"

# If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
AWS_REGION = "us-east-1"

# The subject line for the email.
SUBJECT = "Amazon SES Test (SDK for Python)"

# The character encoding for the email.
CHARSET = "UTF-8"

# Create a new SES resource and specify a region.
client = boto3.client('ses',region_name=AWS_REGION)
#client = boto3.client('ses',region_name=AWS_REGION,verify=False)


def send_email(RECIPIENT,SUBJECT,BODY_TEXT,BODY_HTML):

    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            ReplyToAddresses=REPLYTO,
            # If you are not using a configuration set, comment or delete the
            # following line
            #ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

@emailCommands.cli.command("testEmail")
@click.argument("recipient")
@click.argument("subject")
def test_email(recipient,subject):
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ("Amazon SES Test (Python)\r\n"
                "This email was sent with Amazon SES using the "
                "AWS SDK for Python (Boto)."
                )
                
    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
    <h1>Amazon SES Test (SDK for Python)</h1>
    <p>This email was sent with
        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
        <a href='https://aws.amazon.com/sdk-for-python/'>
        AWS SDK for Python (Boto)</a>.</p>
    </body>
    </html>
                """
    send_email(recipient,subject,BODY_TEXT,BODY_HTML)

#@emailCommands.cli.command("send_reset_email")
#@click.argument("username")
#@click.argument("password")
#@click.argument("test",required=False)
def send_adduser_email(username,password,test=False):
    subject="Usuário criado"
    corpo_html="<h1 style=\"text-align: center\">Gokopa - Criação de usuário</h1><p>Seu usuário foi criado. Acesse com a senha temporária.</p>"
    corpo_html+="<p>Usuário: "+username+"</p>"
    corpo_html+="<p>Senha: "+password+"</p><p>Bolão da Copa: <a href=\"https://copa.leafarlins.com\">copa.leafarlins.com</a></p><p>Gokopa do Mundo: <a href=\"https://gokopa.leafarlins.com\">gokopa.leafarlins.com</a></p>"
    corpo_text = "Usuário: "+username+"\nSenha: "+password
    BODY_HTML = """<html>
    <head></head>
    <body style=\"font-family: \"Trebuchet MS\", Arial, Helvetica, sans-serif;\">
    """ + corpo_html + """
    </body>
    </html>
                """
    BODY_TEXT = (corpo_text)

    if test:
        recipient = "leafarlins@gmail.com"
    else:
        recipient = username
    send_email(recipient,subject,BODY_TEXT,BODY_HTML)

def send_reset_email(username,password,test=False):
    subject="Reset de senha"
    corpo_html="<h1 style=\"text-align: center\">Gokopa - Reset de Senha</h1><p>Sua senha foi resetada. Acesse com a senha temporária.</p>"
    corpo_html+="<p>Usuário: "+username+"</p>"
    corpo_html+="<p>Senha: "+password+"</p><p>Bolão da Copa: <a href=\"https://copa.leafarlins.com\">copa.leafarlins.com</a></p><p>Gokopa do Mundo: <a href=\"https://gokopa.leafarlins.com\">gokopa.leafarlins.com</a></p>"
    corpo_text = "Senha resetada.\nUsuário: "+username+"\nSenha: "+password
    BODY_HTML = """<html>
    <head></head>
    <body style=\"font-family: \"Trebuchet MS\", Arial, Helvetica, sans-serif;\">
    """ + corpo_html + """
    </body>
    </html>
                """
    BODY_TEXT = (corpo_text)

    if test:
        recipient = "leafarlins@gmail.com"
    else:
        recipient = username
    send_email(recipient,subject,BODY_TEXT,BODY_HTML)

@emailCommands.cli.command("send_aviso")
@click.argument("aviso")
def send_aviso(aviso):
    subject="Aviso"
    corpo_text = "Aviso:\n"
    corpo_html="<h1 style=\"text-align: center\">Aviso</h1><p style=\"text-align: center\">"
    corpo_text += aviso
    corpo_html += aviso
    corpo_text+="\n\nAcompanhe em: https://copa.leafarlins.com"
    corpo_html+="</p><p style=\"text-align: center\">Acompanhe em: <a href=\"https://copa.leafarlins.com\">copa.leafarlins.com</a></p>"
    BODY_HTML = """<html>
    <head></head>
    <body style=\"font-family: \"Trebuchet MS\", Arial, Helvetica, sans-serif;\">
    """ + corpo_html + """
    </body>
    </html>
                """
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = (corpo_text)
    #print(corpo_html)
    print(corpo_text)
    user_list = [ u for u in mongo.db.users.find({"active": True})]
    for user in user_list:
        print(f'Enviando email para usuário { user["username"] }')
        recipient = user["username"]
        #send_email(recipient,subject,BODY_TEXT,BODY_HTML)
    # Para testes:
    #send_email("leafarlins@gmail.com",subject,BODY_TEXT,BODY_HTML)

    if TELEGRAM:
        print("Enviando mensagem via telegram")
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': BODY_TEXT
        }
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.get(url, params=params)
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        else:
            r.raise_for_status()



@emailCommands.cli.command("send_bet_report")
@click.argument("test",required=False)
def send_bet_report(test=False):
    #recipient="leafarlins@gmail.com"
    subject="Relatório de apostas"
    betreports = bet_report()
    emojis = mongo.db.emoji

    corpo_text = "Relatório de apostas do jogo: "
    corpo_html="<h1 style=\"text-align: center\">Relatório de apostas</h1><p style=\"text-align: center\">Confira as apostas realizadas do jogo atual.</p>"

    for betreport in betreports['reports']:
        e1 = emojis.find_one({'País': betreport['Time1']})['flag']
        e2 = emojis.find_one({'País': betreport['Time2']})['flag']

        corpo_html+="<table style=\"margin-left:auto; margin-right:auto; border-collapse: collapse;\"><tr style=\"font-size: small; padding-top: 0px; padding-bottom: 0px;\"><td style=\"padding-left: 20px; padding-right: 20px; white-space: nowrap; border: 1px solid #ddd; text-align: center; padding: 8px; padding-top: 0px; padding-bottom: 0px;\">"
        corpo_html+="J:" + str(betreport["Jogo"]) + " " + betreport["Data"]
        corpo_html+="</td><td style=\"padding-left: 20px; padding-right: 20px; white-space: nowrap; border: 1px solid #ddd; text-align: center; padding: 8px;\">"
        corpo_html+=betreport["Fase"]
        corpo_html+="</td></tr><tr style=\"min-width: 300px;\"><td colspan=\"2\" style=\"padding-left: 20px; padding-right: 20px; white-space: nowrap; border: 1px solid #ddd; text-align: center; padding: 8px;\">"
        corpo_html+=f'{betreport["Time1"]} {e1} x {e2} {betreport["Time2"]}'
        corpo_html+="</td></tr></table><h3 style=\"text-align: center;text-decoration-color: rgb(2, 32, 1);\">Apostas:</h3><div style=\"float: center; text-align: center;\">"
        corpo_text+=f'{betreport["Time1"]} {e1} x {e2} {betreport["Time2"]}\nApostas:\n'
        # The HTML body of the email.
        for aposta in betreport["Apostas"]:
            corpo_html+="<div style=\"border-radius: 25px; border: 1px solid #73AD21; padding: 4px; padding-left: 10px; padding-right: 10px; height: 35px; text-align: center; float: center; font-size:small; display: inline-block; white-space: nowrap;\">"
            corpo_html+= aposta["Nome"] + "<br>" + str(aposta["p1"]) + "x" + str(aposta["p2"]) + "</div>"
            corpo_text+= " - " + aposta["Nome"] + ": " + str(aposta["p1"]) + "x" + str(aposta["p2"]) + "\n"
    corpo_html+="</div><p style=\"text-align: center\">Acompanhe em: <a href=\"https://gokopa.leafarlins.com\">gokopa.leafarlins.com</a> <a href=\"https://copa.leafarlins.com\">copa.leafarlins.com</a></p><p>&nbsp;</p><p>&nbsp;</p><p style=\"font-size: small;\">Responda a mensagem caso deseje descadastrar o e-mail da lista de relatórios.</p>"
    corpo_text+="\n\nAcompanhe em: https://copa.leafarlins.com"
    BODY_HTML = """<html>
    <head></head>
    <body style=\"font-family: \"Trebuchet MS\", Arial, Helvetica, sans-serif;\">
    """ + corpo_html + """
    </body>
    </html>
                """
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = (corpo_text)
    #print(corpo_html)
    print(corpo_text)
    user_list = [ u for u in mongo.db.users.find({"active": True,"sendEmail": True})]
    for user in user_list:
        print(f'Enviando email para usuário { user["username"] }')
        recipient = user["username"]
        send_email(recipient,subject,BODY_TEXT,BODY_HTML)
    # Para testes:
    send_email("leafarlins@gmail.com",subject,BODY_TEXT,BODY_HTML)
    
    if TELEGRAM:
        print("Enviando mensagem via telegram")
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': BODY_TEXT
        }
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.get(url, params=params)
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        else:
            r.raise_for_status()
