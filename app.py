from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
import psycopg2
import os
import requests

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ✅ URL do banco (Render.com ou variável local)
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY_ESPERADA = os.environ.get("API_KEY_ESPERADA", "SUA_API_KEY_AQUI")  # pode vir de env

# ✅ Função para obter conexão PostgreSQL
def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ✅ Criação de tabela inicial
def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        empresa TEXT,
        plano TEXT,
        senha TEXT,
        status TEXT DEFAULT 'pendente',
        id_maquina TEXT,
        logado INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

# ✅ Token de segurança
def validar_token(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    return token == API_KEY_ESPERADA

# ============ ROTAS DE API ============

@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    if not validar_token(request):
        return jsonify({"erro": "não autorizado"}), 403
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email, empresa, plano, status, senha, id_maquina FROM usuarios")
    rows = cursor.fetchall()
    conn.close()
    usuarios = [
        {
            "id": r[0], "nome": r[1], "email": r[2], "empresa": r[3],
            "plano": r[4], "status": r[5], "senha": r[6], "id_maquina": r[7]
        }
        for r in rows
    ]
    return jsonify(usuarios)

@app.route("/aprovar", methods=["POST"])
def aprovar():
    if not validar_token(request): return jsonify({"erro": "não autorizado"}), 403
    user_id = request.json.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status='aprovado' WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "aprovado"})

@app.route("/rejeitar", methods=["POST"])
def rejeitar():
    if not validar_token(request): return jsonify({"erro": "não autorizado"}), 403
    user_id = request.json.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status='rejeitado' WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "rejeitado"})

@app.route("/reset_senha", methods=["POST"])
def reset_senha():
    if not validar_token(request): return jsonify({"erro": "não autorizado"}), 403
    user_id = request.json.get("id")
    nova_senha = "senha" + str(user_id).zfill(4)
    return jsonify({"nova_senha": nova_senha})

@app.route("/excluir", methods=["POST"])
def excluir():
    if not validar_token(request): return jsonify({"erro": "não autorizado"}), 403
    user_id = request.json.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "usuário excluído"})

@app.route("/desvincular", methods=["POST"])
def desvincular():
    if not validar_token(request): return jsonify({"erro": "não autorizado"}), 403
    user_id = request.json.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET id_maquina = NULL, logado = 0 WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "ID da máquina desvinculado com sucesso"})

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    dados = request.json
    nome, email, empresa = dados.get("nome"), dados.get("email"), dados.get("empresa", "")
    plano, senha = dados.get("plano", "mensal"), dados.get("senha")
    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, email e senha são obrigatórios."}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"erro": "E-mail já cadastrado."}), 409

    cursor.execute("""
        INSERT INTO usuarios (nome, email, empresa, plano, senha, status)
        VALUES (%s, %s, %s, %s, %s, 'pendente')
    """, (nome, email, empresa, plano, senha))
    conn.commit()
    conn.close()
    return jsonify({"msg": "Cadastro enviado com sucesso. Aguardando aprovação."})

@app.route("/login", methods=["POST"])
def login():
    dados = request.json
    email, senha, id_maquina = dados.get("email"), dados.get("senha"), dados.get("id_maquina")
    if not email or not senha or not id_maquina:
        return jsonify({"erro": "Email, senha e ID da máquina são obrigatórios."}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, status, senha, id_maquina, logado FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({"erro": "Usuário não encontrado."}), 404

    user_id, nome, status, senha_db, maquina_db, logado = user
    if senha != senha_db:
        conn.close()
        return jsonify({"erro": "Senha incorreta."}), 401
    if status != "aprovado":
        conn.close()
        return jsonify({"erro": "Acesso não autorizado. Aguarde aprovação."}), 403

    if maquina_db is None:
        cursor.execute("UPDATE usuarios SET id_maquina = %s WHERE id = %s", (id_maquina, user_id))
    elif id_maquina != maquina_db:
        conn.close()
        return jsonify({"erro": "Este usuário está vinculado a outro dispositivo."}), 403

    if logado == 1:
        conn.close()
        return jsonify({"erro": "Usuário já está logado em outro dispositivo."}), 403

    cursor.execute("UPDATE usuarios SET logado = 1 WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "Login autorizado", "id": user_id, "nome": nome})

@app.route("/logout", methods=["POST"])
def logout():
    email = request.json.get("email")
    if not email:
        return jsonify({"erro": "E-mail é obrigatório."}), 400
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET logado = 0 WHERE email = %s", (email,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "Logout realizado com sucesso"})

# ============ ROTAS DO PAINEL ADMIN ============

@app.route("/")
def index():
    headers = {"Authorization": f"Bearer {API_KEY_ESPERADA}"}
    try:
        resp = requests.get(request.url_root + "usuarios", headers=headers)
        usuarios = resp.json() if resp.status_code == 200 else []
    except Exception:
        usuarios = []
    return render_template("index.html", usuarios=usuarios)

@app.route("/aprovar/<int:usuario_id>", methods=["POST"])
def aprovar_web(usuario_id):
    requests.post(request.url_root + "aprovar", json={"id": usuario_id}, headers={"Authorization": f"Bearer {API_KEY_ESPERADA}"})
    return redirect("/")

@app.route("/rejeitar/<int:usuario_id>", methods=["POST"])
def rejeitar_web(usuario_id):
    requests.post(request.url_root + "rejeitar", json={"id": usuario_id}, headers={"Authorization": f"Bearer {API_KEY_ESPERADA}"})
    return redirect("/")

@app.route("/resetar/<int:usuario_id>", methods=["POST"])
def resetar_web(usuario_id):
    resp = requests.post(request.url_root + "reset_senha", json={"id": usuario_id}, headers={"Authorization": f"Bearer {API_KEY_ESPERADA}"})
    nova_senha = resp.json().get("nova_senha", "Erro ao gerar")
    return f"<h3>Nova senha: {nova_senha}</h3><a href='/'>Voltar</a>"

@app.route("/excluir/<int:usuario_id>", methods=["POST"])
def excluir_web(usuario_id):
    requests.post(request.url_root + "excluir", json={"id": usuario_id}, headers={"Authorization": f"Bearer {API_KEY_ESPERADA}"})
    return redirect("/")

@app.route("/desvincular/<int:usuario_id>", methods=["POST"])
def desvincular_web(usuario_id):
    requests.post(request.url_root + "desvincular", json={"id": usuario_id}, headers={"Authorization": f"Bearer {API_KEY_ESPERADA}"})
    return redirect("/")
