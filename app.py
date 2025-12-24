from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# 🔐 Variáveis de ambiente
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY_ESPERADA = os.environ.get("API_KEY_ESPERADA", "SUA_API_KEY_AQUI")

# 🔌 Conexão com PostgreSQL
def get_conn():
    return psycopg2.connect(DATABASE_URL)

# 🧱 Criação das tabelas (Mantendo as existentes e adicionando a de Manuais)
def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    # Tabela de usuários original
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
    # Tabela de manuais para a Malha Fiscal
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS manuais (
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        descricao TEXT,
        url_gif TEXT,
        url_pdf TEXT,
        categoria TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ Banco de dados sincronizado!")

init_db()

# 🔐 Validação de token
def validar_token(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    return token == API_KEY_ESPERADA

# ========== ROTAS DE API (PARA O SOFTWARE) ==========

@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    if not validar_token(request):
        return jsonify({"erro": "não autorizado"}), 403
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, nome, email, empresa, plano, status, senha, id_maquina FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()
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
    # No seu código original você apenas retornava a senha, aqui mantemos a lógica
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
    return jsonify({"msg": "Cadastro enviado com sucesso."})

@app.route("/login", methods=["POST"])
def login():
    dados = request.json
    email, senha, id_maquina = dados.get("email"), dados.get("senha"), dados.get("id_maquina")
    if not email or not senha or not id_maquina:
        return jsonify({"erro": "Email, senha e ID da máquina são obrigatórios."}), 400
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({"erro": "Usuário não encontrado."}), 404
    if senha != user['senha']:
        conn.close()
        return jsonify({"erro": "Senha incorreta."}), 401
    if user['status'] != "aprovado":
        conn.close()
        return jsonify({"erro": "Acesso não autorizado. Aguarde aprovação."}), 403
    if user['id_maquina'] is None:
        cursor.execute("UPDATE usuarios SET id_maquina = %s WHERE id = %s", (id_maquina, user['id']))
    elif id_maquina != user['id_maquina']:
        conn.close()
        return jsonify({"erro": "Este usuário está vinculado a outro dispositivo."}), 403
    if user['logado'] == 1:
        conn.close()
        return jsonify({"erro": "Usuário já está logado em outro dispositivo."}), 403
    cursor.execute("UPDATE usuarios SET logado = 1 WHERE id = %s", (user['id'],))
    conn.commit()
    conn.close()
    return jsonify({"msg": "Login autorizado", "id": user['id'], "nome": user['nome']})

@app.route("/logout", methods=["POST"])
def logout():
    email = request.json.get("email")
    if not email: return jsonify({"erro": "E-mail é obrigatório."}), 400
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET logado = 0 WHERE email = %s", (email,))
    conn.commit()
    conn.close()
    return jsonify({"msg": "Logout realizado com sucesso"})

# ========== ROTAS DO PAINEL ADMIN E PORTAL (WEB) ==========

@app.route("/")
def index():
    try:
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()
    except Exception as e:
        usuarios = []
    return render_template("index.html", usuarios=usuarios)

@app.route("/portal")
def portal_fiscal():
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM manuais ORDER BY id DESC")
    manuais = cursor.fetchall()
    conn.close()
    return render_template("portal.html", manuais=manuais)

@app.route("/admin/cadastrar_manual", methods=["GET", "POST"])
def cadastrar_manual():
    if request.method == "POST":
        titulo = request.form.get("titulo")
        url_gif = request.form.get("url_gif")
        url_pdf = request.form.get("url_pdf")
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO manuais (titulo, url_gif, url_pdf) VALUES (%s, %s, %s)", (titulo, url_gif, url_pdf))
        conn.commit()
        conn.close()
        return redirect(url_for('portal_fiscal'))
    return render_template("cadastrar_manual.html")

@app.route("/aprovar/<int:usuario_id>", methods=["POST"])
def aprovar_web(usuario_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status='aprovado' WHERE id=%s", (usuario_id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/rejeitar/<int:usuario_id>", methods=["POST"])
def rejeitar_web(usuario_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status='rejeitado' WHERE id=%s", (usuario_id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/excluir/<int:usuario_id>", methods=["POST"])
def excluir_web(usuario_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (usuario_id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/desvincular/<int:usuario_id>", methods=["POST"])
def desvincular_web(usuario_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET id_maquina = NULL, logado = 0 WHERE id=%s", (usuario_id,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)