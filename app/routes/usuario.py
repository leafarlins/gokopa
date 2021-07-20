from flask import Blueprint, render_template, session, request, url_for, flash
from werkzeug.utils import redirect
from werkzeug.security import check_password_hash
from ..extentions.database import mongo

#current_app para carregar app.py

usuario = Blueprint('usuario',__name__)

@usuario.route('/login', methods=['GET','POST'])
def login():
    if "username" in session:
        return redirect(url_for("bolao.apostas"))
    elif request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        userFound = mongo.db.users.find_one({"username": username})
        if userFound:
            validUser = userFound["username"]
            validPassword = userFound["password"]
            validName = userFound["name"]
            validActive = userFound["active"]
            if check_password_hash(validPassword,password):
                if validActive:
                    session["username"] = validUser
                    flash(f'Bem vindo, {validName}!')
                    return redirect(url_for('bolao.apostas'))
                else:
                    flash(f'Redefina sua senha, {validName}.')
                    return render_template("usuarios/reset.html",user=validUser,menu="Login")

            else:
                flash('Senha Incorreta!')
                return render_template("usuarios/login.html",menu="Login")
        else:
            flash("Usuário não encontrado.")
            render_template("usuarios/login.html",menu="Login")

    return render_template("usuarios/login.html",menu="Login")
    
@usuario.route('/reset', methods=['GET','POST'])
def reset():
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        password2 = request.form.get('senha2')
        userFound = mongo.db.users.find_one({"username": username})
        if userFound:
            validUser = userFound["username"]
            validPassword = userFound["password"]
            validName = userFound["name"]
            validActive = userFound["active"]

            if (password == password2):
                mongo.db.users.find_one_and_update({"username": username},{'$set': {"active": True, "password": password}})
                session["username"] = validUser
                flash(f'Senha definida com sucesso, bem vindo, {validName}!')
                return redirect(url_for('bolao.apostas'))
            else:
                flash('As senhas não são iguais!')
                return render_template("usuarios/reset.html",user=validUser,menu="Login")

        else:
            flash("Usuário não encontrado.")
            render_template("usuarios/login.html",menu="Login")

    return redirect(url_for("usuario.login"))

@usuario.route('/logout')
def logout():
    session.pop("username",None)
    flash('Logout efetuado.')
    return redirect(url_for('usuario.login'))
