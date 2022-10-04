from datetime import datetime
from flask import Blueprint, current_app, render_template, session, request, url_for, flash
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash, generate_password_hash
from ..extentions.database import mongo

#current_app para carregar app.py

usuario = Blueprint('usuario',__name__)

@usuario.route('/<tipo>/login', methods=['GET','POST'])
def login(tipo):
    if "username" in session:
        return redirect(url_for("bolao.apostas",tipo=tipo))
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

            # Data limite para ativar users automaticamente no acesso
            now = datetime.now()
            data_limite = datetime.strptime("02/10/2022 06:00","%d/%m/%Y %H:%M")
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
                        flash(f'Bem vindo, {validName}!')
                        current_app.logger.info(f"Usuário {validName} logado com sucesso")
                        return redirect(url_for('bolao.apostas',tipo=tipo))
                    else:
                        flash(f'Redefina sua senha, {validName}.')
                        return render_template("usuarios/reset.html",user=validUser,menu="Login",tipo=tipo)

                else:
                    flash('Senha Incorreta!')
                    return render_template("usuarios/login.html",menu="Login",tipo=tipo)
            else:
                flash('Usuário inativo, contate o administrador.')
                current_app.logger.info(f"Usuário {validName} inativado, login sem sucesso")
                return render_template("usuarios/login.html",menu="Login",tipo=tipo)
        else:
            flash("Usuário não encontrado.")
            current_app.logger.warn(f"Usuário {validName} não encontrado na base")
            render_template("usuarios/login.html",menu="Login",tipo=tipo)

    return render_template("usuarios/login.html",menu="Login",tipo=tipo)
    
@usuario.route('/<tipo>/reset', methods=['GET','POST'])
def reset(tipo):
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        password2 = request.form.get('senha2')
        userFound = mongo.db.users.find_one({"username": username})
        if userFound:
            validUser = userFound["username"]
            validName = userFound["name"]
            validActive = userFound["active"]
            if validActive:
                if (password == password2):
                    mongo.db.users.find_one_and_update({"username": username},{'$set': {"passwordActive": True, "password": generate_password_hash(password)}})
                    session["username"] = validUser
                    flash(f'Senha definida com sucesso, bem vindo, {validName}!')
                    return redirect(url_for('bolao.apostas',tipo=tipo))
                else:
                    flash('As senhas não são iguais!')
                    return render_template("usuarios/reset.html",user=validUser,menu="Login",tipo=tipo)
            else:
                flash("Usuário inativo, contate o administrador.")
                render_template("usuarios/login.html",menu="Login",tipo=tipo)

        else:
            flash("Usuário não encontrado.")
            render_template("usuarios/login.html",menu="Login",tipo=tipo)

    return redirect(url_for("usuario.login",tipo=tipo))

@usuario.route('/<tipo>/logout')
def logout(tipo):
    session.pop("username",None)
    flash('Logout efetuado.')
    return redirect(url_for('usuario.login',tipo=tipo))
