from datetime import datetime
from app.commands.timeCommands import geraBaralho
from app.routes.backend import get_user_name
from flask import Blueprint, current_app, render_template, session, request, url_for, flash
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash, generate_password_hash
from ..extentions.database import mongo

#current_app para carregar app.py

usuario = Blueprint('usuario',__name__)

ANOSTR='24'
DATAMAX='04/10/2024'
data_limite = datetime.strptime("05/10/2024 02:00","%d/%m/%Y %H:%M")

@usuario.route('/login', methods=['GET','POST'])
def login():
    if "username" in session:
        return redirect(url_for('bolao.apostas',ano=ANOSTR))
    elif request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        userFound = mongo.db.users.find_one({"username": username})
        if userFound:
            validUser = userFound["username"]
            validPassword = userFound["password"]
            validName = userFound["name"]
            validActive = userFound["passwordActive"]
            validActiveU = userFound["active"]
            validGokopa = userFound["gokopa"]

            # Data limite para ativar users automaticamente no acesso
            now = datetime.now()
            
            if now < data_limite and validActiveU == False:
                ativarUser = True
                validActiveU = True
            else:
                ativarUser = False
            
            if validActiveU:
                if check_password_hash(validPassword,password):
                    # Ativa user caso permitido
                    if ativarUser:
                        flash(f'Usuário ativado no acesso.')
                        mongo.db.users.find_one_and_update({"username": username},{'$set': {"active": True}})
                    if validActive:
                        session["username"] = validUser
                        flash(f'Bem vindo, {validName}!','success')
                        current_app.logger.info(f"Usuário {validName} logado com sucesso")
                        if not validGokopa:
                            now = datetime.now()
                            if now < data_limite:
                                return redirect(url_for('usuario.validagokopa'))
                            else:
                                flash(f'Tempo expirado para participar da temporada atual','warning')
                        return redirect(url_for('bolao.apostas',ano=ANOSTR))

                    else:
                        flash(f'Redefina sua senha, {validName}.')
                        return render_template("usuarios/reset.html",user=validUser,menu="Login")

                else:
                    flash('Senha Incorreta!')
                    return render_template("usuarios/login.html",menu="Login")
            else:
                flash('Usuário inativo, contate o administrador.')
                current_app.logger.info(f"Usuário {validName} inativado, login sem sucesso")
                return render_template("usuarios/login.html",menu="Login")
        else:
            flash("Usuário não encontrado.")
            current_app.logger.warn(f"Usuário {validName} não encontrado na base")
            render_template("usuarios/login.html",menu="Login")

    return render_template("usuarios/login.html",menu="Login")
    

@usuario.route('/validagokopa', methods=['GET','POST'])
def validagokopa():
    if request.method == 'POST':
        if "username" in session:
            now = datetime.now()
            if now < data_limite:
                validUser = session["username"]
                userFound = mongo.db.users.find_one_and_update({"username": validUser},{'$set': {"gokopa": True}})
                if userFound:
                    userName = get_user_name(validUser)
                    novo_user = {
                            "nome": userName,
                            "saldo": 0,
                            "bloqueado": 0,
                            "investido": 0,
                            "divida": 0,
                            "lock": False
                    }
                    mongo.db.moedas.insert_one(novo_user)
                    geraBaralho(userName)
                    flash(f'Usuário ativado na gokopa!','success')
                    current_app.logger.info(f"Usuário {validUser} ativado na gokopa")
                    return redirect(url_for('bolao.apostas',ano=ANOSTR))
                else:
                    flash('Usuário não encontrado, contate o administrador.','warning')
                    current_app.logger.error(f"Usuário {validUser} não encontrado na base")
            else:
                flash(f'Tempo expirado para participar da temporada atual','warning')
        else:
            flash(f'Usuário não está logado','danger')

    return render_template("usuarios/gokopa.html",menu="Login",datamax=DATAMAX)


@usuario.route('/reset', methods=['GET','POST'])
def reset():
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        password2 = request.form.get('senha2')
        userFound = mongo.db.users.find_one({"username": username})
        if userFound:
            validUser = userFound["username"]
            validName = userFound["name"]
            validActive = userFound["active"]
            validGokopa = userFound["gokopa"]
            if validActive:
                if (password == password2):
                    mongo.db.users.find_one_and_update({"username": username},{'$set': {"passwordActive": True, "password": generate_password_hash(password)}})
                    session["username"] = validUser
                    flash(f'Senha definida com sucesso, bem vindo, {validName}!','success')
                    if validGokopa:
                        return redirect(url_for('bolao.apostas',ano=ANOSTR))
                    else:
                        return redirect(url_for('usuario.validagokopa'))
                else:
                    flash('As senhas não são iguais!','danger')
                    return render_template("usuarios/reset.html",user=validUser,menu="Login")
            else:
                flash("Usuário inativo, contate o administrador.")
                render_template("usuarios/login.html",menu="Login")

        else:
            flash("Usuário não encontrado.")
            render_template("usuarios/login.html",menu="Login")

    return redirect(url_for("usuario.login"))

@usuario.route('/logout')
def logout():
    session.pop("username",None)
    flash('Logout efetuado.')
    return redirect(url_for('usuario.login'))
