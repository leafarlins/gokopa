from flask import Blueprint, render_template, session, request, url_for, flash
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
            if check_password_hash(validPassword,password):
                if validActive:
                    session["username"] = validUser
                    flash(f'Bem vindo, {validName}!')
                    return redirect(url_for('bolao.apostas',tipo=tipo))
                else:
                    flash(f'Redefina sua senha, {validName}.')
                    return render_template("usuarios/reset.html",user=validUser,menu="Login",tipo=tipo)

            else:
                flash('Senha Incorreta!')
                return render_template("usuarios/login.html",menu="Login",tipo=tipo)
        else:
            flash("Usuário não encontrado.")
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

            if (password == password2):
                mongo.db.users.find_one_and_update({"username": username},{'$set': {"passwordActive": True, "password": generate_password_hash(password)}})
                session["username"] = validUser
                flash(f'Senha definida com sucesso, bem vindo, {validName}!')
                return redirect(url_for('bolao.apostas',tipo=tipo))
            else:
                flash('As senhas não são iguais!')
                return render_template("usuarios/reset.html",user=validUser,menu="Login",tipo=tipo)

        else:
            flash("Usuário não encontrado.")
            render_template("usuarios/login.html",menu="Login",tipo=tipo)

    return redirect(url_for("usuario.login",tipo=tipo))

@usuario.route('/<tipo>/logout')
def logout(tipo):
    session.pop("username",None)
    flash('Logout efetuado.')
    return redirect(url_for('usuario.login',tipo=tipo))
