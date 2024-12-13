from flask import Flask, render_template, request, redirect, flash, session, jsonify
import mysql.connector
from functools import wraps
import re
from datetime import datetime
import base64

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración de la base de datos
db_config = {
    'host': 'database-mario.ct8s48kk2drd.us-east-2.rds.amazonaws.com',
    'user': 'adminsay',
    'password': 'C43t0555',
    'database': 'mydb'
}

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(**db_config)


















# Decorador para requerir inicio de sesión
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper

# Ruta principal (login)
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    correo = request.form['correo']
    contrasena = request.form['contrasena']

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT idUsuarios, id_Rol FROM Usuarios WHERE Correo = %s AND Contrasena = %s", (correo, contrasena))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['idUsuarios']
            session['rol'] = user['id_Rol']
            flash('Inicio de sesión exitoso', 'success')
            if user['id_Rol'] == 2:
                return redirect('/menu_Admi')
            elif user['id_Rol'] == 3:
                return redirect('/menu_policia')
            elif user['id_Rol'] == 4:
                return redirect('/menu_Usuario')
            elif user['id_Rol'] == 5:  # Profesor
                return redirect('/menu_Usuario')
            else:
                return redirect('/')
        else:
            flash('Credenciales incorrectas', 'error')
            return redirect('/')

    except Exception as e:
        flash('Error al conectar a la base de datos.', 'error')
        print(f'Error: {e}')
        return redirect('/')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('rol', None)
    flash('Has cerrado sesión', 'success')
    return redirect('/')







# Rutas de menú de usuario (solo accesibles si el usuario está autenticado)
@app.route('/menu_Admi')
@login_required
def menu_Admi():
    return render_template('menu_Admi.html')

@app.route('/menu_policia')
@login_required
def menu_policia():
    return render_template('menu_policia.html')

@app.route('/menu_Usuario')
@login_required
def menu_Usuario():
    return render_template('menu_Usuario.html')

@app.route('/lector_qr')
@login_required
def lector_qr():
    return render_template('lector_qr.html')

import qrcode
import io
import base64
from flask import render_template

@app.route('/credencial')
@login_required
def credencial():
    # Obtener los datos del usuario desde la base de datos
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM Usuarios WHERE idUsuarios = %s", (session['user_id'],))
        usuario = cursor.fetchone()

        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect('/')

        # Convertir la imagen a base64 si está presente
        imagen_base64 = None
        if usuario['imagen']:
            imagen_base64 = base64.b64encode(usuario['imagen']).decode('utf-8')

        # Generar el código QR con la matrícula del usuario
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(usuario['Matricula'])
        qr.make(fit=True)

        # Crear una imagen del código QR
        qr_img = qr.make_image(fill='black', back_color='white')

        # Guardar el QR en un objeto de BytesIO
        img_io = io.BytesIO()
        qr_img.save(img_io, 'PNG')
        img_io.seek(0)

        # Convertir la imagen QR a base64
        qr_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

        return render_template('credencial.html', 
                               nombre=usuario['Nombres'] + ' ' + usuario['Apellido_p'] + ' ' + usuario['Apellido_m'],
                               matricula=usuario['Matricula'],
                               carrera=usuario['Carrera'],
                               rol=usuario['id_Rol'],
                               imagen=imagen_base64, 
                               qr_code=qr_base64)

    except mysql.connector.Error as e:
        flash(f'Error en la base de datos: {e}', 'error')
        return redirect('/')

    finally:
        cursor.close()
        conn.close()



@app.route('/contraseña', methods=['GET', 'POST'])
@login_required
def contraseña():
    if request.method == 'POST':
        contrasena_actual = request.form['contrasena_actual']
        nueva_contrasena = request.form['nueva_contrasena']
        repetir_contrasena = request.form['repetir_contrasena']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Usuarios WHERE idUsuarios = %s AND Contrasena = %s", (session['user_id'], contrasena_actual))
        user = cursor.fetchone()

        if user:
            if nueva_contrasena == repetir_contrasena:
                if len(nueva_contrasena) >= 8 and re.match("^[A-Za-z0-9]+$", nueva_contrasena):
                    cursor.execute(""" 
                        UPDATE Usuarios 
                        SET Contrasena = %s 
                        WHERE idUsuarios = %s 
                    """, (nueva_contrasena, session['user_id']))
                    conn.commit()
                    flash('Contraseña actualizada exitosamente.', 'success')
                else:
                    flash('La nueva contraseña debe tener al menos 8 caracteres y no contener símbolos ni espacios.', 'error')
            else:
                flash('Las nuevas contraseñas no coinciden.', 'error')
        else:
            flash('La contraseña actual es incorrecta.', 'error')

        cursor.close()
        conn.close()
        return render_template('contraseña.html')

    return render_template('contraseña.html')



                # Ruta para verificar matrícula y registrar entrada/salida en la bitácora
@app.route('/verificar_matricula', methods=['POST'])
def verificar_matricula():
    data = request.get_json()
    matricula = data.get('matricula')

    # Conectar a la base de datos
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Consultar la base de datos para verificar la matrícula
        cursor.execute("SELECT * FROM Usuarios WHERE Matricula = %s", (matricula,))
        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({'existe': False, 'mensaje': 'Usuario no encontrado.'})

        # Asegúrate de que no haya resultados no leídos
        cursor.fetchall()  # Consume cualquier posible resultado residual

        # Consultar la bitácora para ver si el usuario tiene un registro de entrada sin salida
        cursor.execute("""
            SELECT * FROM bitacora 
            WHERE id_Usuarios = %s AND fecha_hora_salida IS NULL
            ORDER BY fecha_hora_entrada DESC LIMIT 1
        """, (usuario['idUsuarios'],))
        bitacora = cursor.fetchone()

        if not bitacora:
            # Si no hay registro de entrada sin salida, se crea uno
            cursor.execute("""
                INSERT INTO bitacora (fecha_hora_entrada, id_Usuarios)
                VALUES (%s, %s)
            """, (datetime.now(), usuario['idUsuarios']))
            connection.commit()
            mensaje = 'Entrada registrada correctamente'
            bitacora = {'idBitacora': cursor.lastrowid}  # Obtener el id del nuevo registro de bitácora
        else:
            # Si ya hay una entrada sin salida, se registra la salida
            cursor.execute("""
                UPDATE bitacora
                SET fecha_hora_salida = %s
                WHERE idBitacora = %s
            """, (datetime.now(), bitacora['idBitacora']))
            connection.commit()
            mensaje = 'Salida registrada correctamente'

        # Convertir imagen a base64 si está presente
        if usuario['imagen']:
            imagen_base64 = base64.b64encode(usuario['imagen']).decode('utf-8')
        else:
            imagen_base64 = None

        return jsonify({
            'existe': True,
            'matricula': usuario['Matricula'],
            'nombres': usuario['Nombres'],
            'apellido_p': usuario['Apellido_p'],
            'apellido_m': usuario['Apellido_m'],
            'imagen': imagen_base64,
            'mensaje': mensaje
        })

    except mysql.connector.Error as e:
        # Si hay un error con MySQL, mostramos el error específico
        return jsonify({'existe': False, 'mensaje': f'Error en la base de datos: {str(e)}'})

    finally:
        # Asegúrate de cerrar el cursor y la conexión correctamente
        cursor.close()
        connection.close()



@app.route('/footer')
def footer():
    return render_template('footer.html')


from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response
import mysql.connector
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@app.route('/formulario', methods=['GET', 'POST'])
@login_required
def index():
    # Conectar a la base de datos
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    search_email = request.args.get('search_email')
    query = "SELECT idUsuarios, Nombres, Apellido_p, Apellido_m, Matricula, Carrera, Correo, id_Rol, imagen FROM Usuarios"
    if search_email:
        query += " WHERE Correo LIKE %s"
        cursor.execute(query, ('%' + search_email + '%',))
    else:
        cursor.execute(query)

    usuarios = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('formulario.html', usuarios=usuarios)



# Ruta para editar usuario
@app.route('/editar/<int:id_usuario>', methods=['GET', 'POST'])
def editar(id_usuario):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    if request.method == 'POST':
        # Recoger datos del formulario
        nombres = request.form['nombres']
        apellido_p = request.form['apellido_p']
        apellido_m = request.form['apellido_m']
        matricula = request.form['matricula']
        carrera = request.form['carrera']
        correo = request.form['correo']
        id_rol = request.form['id_rol']

        imagen = request.files['imagen']
        imagen_blob = None

        if imagen and imagen.filename != '':  # Si se sube una nueva imagen
            imagen_blob = imagen.read()
        else:
            cursor.execute("SELECT imagen FROM Usuarios WHERE idUsuarios = %s", (id_usuario,))
            imagen_data = cursor.fetchone()
            if imagen_data:
                imagen_blob = imagen_data[0]

        query = '''
            UPDATE Usuarios
            SET Nombres=%s, Apellido_p=%s, Apellido_m=%s, Matricula=%s, Carrera=%s, Correo=%s, id_Rol=%s, imagen=%s
            WHERE idUsuarios=%s
        '''
        cursor.execute(query, (nombres, apellido_p, apellido_m, matricula, carrera, correo, id_rol, imagen_blob, id_usuario))
        conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM Usuarios WHERE idUsuarios = %s", (id_usuario,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if not usuario:
        return 'Usuario no encontrado', 404

    return render_template('editar_usuario.html', usuario=usuario)


@app.route('/eliminar/<int:id_usuario>', methods=['GET'])
def eliminar_usuario(id_usuario):
    # Lógica para eliminar al usuario
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Verificar si el usuario tiene registros en la tabla bitacora
        cursor.execute("SELECT COUNT(*) FROM bitacora WHERE id_Usuarios = %s", (id_usuario,))
        count = cursor.fetchone()[0]

        if count > 0:
            return 'No puedes eliminar este usuario porque tiene registros en la bitacora.', 400

        # Eliminar el usuario de la tabla usuarios si no tiene registros en bitacora
        cursor.execute("DELETE FROM Usuarios WHERE idUsuarios = %s", (id_usuario,))
        
        # Confirmar los cambios
        conn.commit()

        # Cerrar la conexión
        cursor.close()
        conn.close()

        return 'Usuario eliminado con éxito', 200
    except mysql.connector.Error as err:
        return f"Error: {err}", 500



# Ruta para agregar usuario
@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        # Recoger los datos del formulario
        nombres = request.form['nombres']
        apellido_p = request.form['apellido_p']
        apellido_m = request.form['apellido_m']
        matricula = request.form['matricula']
        carrera = request.form['carrera']
        correo = request.form['correo']
        contrasena = matricula  # La contraseña será igual a la matrícula
        id_rol = request.form['id_rol']

        imagen = request.files['imagen']
        imagen_blob = None

        if imagen and imagen.filename != '':
            imagen_blob = imagen.read()

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE Correo = %s", (correo,))
        correo_existente = cursor.fetchone()[0]

        if correo_existente > 0:
            flash("El correo electrónico ya está registrado. Por favor, usa otro correo.")
            return redirect(url_for('index'))

        query = '''
            INSERT INTO Usuarios (Nombres, Apellido_p, Apellido_m, Matricula, Carrera, Correo, Contrasena, id_Rol, imagen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(query, (nombres, apellido_p, apellido_m, matricula, carrera, correo, contrasena, id_rol, imagen_blob))
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('index'))


from datetime import datetime

def format_fecha(fecha):
    # Si la fecha es None o no tiene valor, devolvemos "No ha salido"
    if not fecha:
        return 'No ha salido'
    # Si la fecha tiene valor, la formateamos
    try:
        return datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
    except ValueError:
        return 'Fecha inválida'

def obtener_bitacoras(conn, params, query):
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    bitacoras = cursor.fetchall()
    cursor.close()
    return bitacoras

# Ruta para ver las bitácoras con filtros
@app.route('/bitacoras', methods=['GET'])
def bitacoras():
    # Conexión a la base de datos
    conn = mysql.connector.connect(**db_config)

    # Obtener los parámetros de búsqueda (hora, usuario y rol)
    usuario_id = request.args.get('usuario_id')
    fecha_inicio = request.args.get('fecha_inicio')  # Formato: 'YYYY-MM-DD'
    fecha_fin = request.args.get('fecha_fin')  # Formato: 'YYYY-MM-DD'

    # Lista de parámetros que vamos a pasar a la consulta
    params = []

    # Construir la consulta dinámica
    query = """
        SELECT b.idBitacora, b.fecha_hora_entrada, b.fecha_hora_salida, u.Nombres, u.Apellido_p, u.Apellido_m
        FROM bitacora b
        JOIN Usuarios u ON b.id_Usuarios = u.idUsuarios
        WHERE 1=1
    """

    # Filtrar por usuario si se proporciona
    if usuario_id:
        query += " AND b.id_Usuarios = %s"
        params.append(usuario_id)

    # Filtrar por fechas si se proporcionan
    if fecha_inicio:
        query += " AND b.fecha_hora_entrada >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND (b.fecha_hora_salida <= %s OR b.fecha_hora_salida IS NULL)"
        params.append(fecha_fin)

    # Obtener las bitácoras
    bitacoras = obtener_bitacoras(conn, params, query)

    # Cerrar la conexión
    conn.close()

    # Renderizar la plantilla con las bitácoras
    return render_template('bitacoras.html', bitacoras=bitacoras)

# Ruta para mostrar bitácoras con filtros de fecha, nombre y carrera



@app.route('/mostrar_bitacora', methods=['GET'])
def mostrar_bitacora():
    # Conexión a la base de datos
    conn = mysql.connector.connect(**db_config)

    # Obtener los parámetros de los filtros desde la URL (si existen)
    fecha_inicio = request.args.get('fecha_inicio')
    nombre = request.args.get('nombre')
    carrera = request.args.get('carrera')

    # Lista de parámetros para pasar a la consulta
    params = []

    # Consulta para obtener las bitácoras con los posibles filtros
    query = """
        SELECT b.idBitacora, b.fecha_hora_entrada, b.fecha_hora_salida, u.Correo, 
               u.Nombres, u.Apellido_p, u.Apellido_m, u.Carrera
        FROM bitacora b
        JOIN Usuarios u ON b.id_Usuarios = u.idUsuarios
        WHERE 1=1
    """

    # Filtrar por fecha de ingreso si se proporciona
    if fecha_inicio:
        query += " AND b.fecha_hora_entrada >= %s"
        params.append(fecha_inicio)

    # Filtrar por nombre si se proporciona
    if nombre:
        query += " AND (u.Nombres LIKE %s OR u.Apellido_p LIKE %s OR u.Apellido_m LIKE %s)"
        params.extend([f'%{nombre}%', f'%{nombre}%', f'%{nombre}%'])

    # Filtrar por carrera si se proporciona
    if carrera:
        query += " AND u.Carrera LIKE %s"
        params.append(f'%{carrera}%')

    # Obtener las bitácoras
    bitacoras = obtener_bitacoras(conn, params, query)

    # Formatear las fechas de entrada y salida
    for i, bitacora in enumerate(bitacoras):
        # La fecha de salida puede ser None, entonces usamos la función format_fecha para gestionarlo
        fecha_salida = format_fecha(str(bitacora[2])) if bitacora[2] else 'No ha salido'

        # Actualizamos la bitácora con la fecha formateada
        bitacoras[i] = (
            bitacora[0],  # idBitacora
            format_fecha(str(bitacora[1])),  # Fecha de Ingreso
            fecha_salida,  # Fecha de Salida (o 'No ha salido')
            bitacora[3],  # Correo
            bitacora[4],  # Nombres
            bitacora[5],  # Apellido_p
            bitacora[6],  # Apellido_m
            bitacora[7]   # Carrera
        )

    # Cerrar la conexión a la base de datos
    conn.close()

    # Renderizar la plantilla con las bitácoras
    return render_template('bitacoras.html', bitacoras=bitacoras, fecha_inicio=fecha_inicio, nombre=nombre, carrera=carrera)

# Ruta para generar el reporte en PDF
@app.route('/generar_bitacora_pdf', methods=['GET'])
def generar_bitacora_pdf():
    # Conexión a la base de datos
    conn = mysql.connector.connect(**db_config)

    # Obtener los parámetros de los filtros desde la URL
    fecha_inicio = request.args.get('fecha_inicio')
    nombre = request.args.get('nombre')
    carrera = request.args.get('carrera')

    # Lista de parámetros para pasar a la consulta
    params = []

    # Consulta para obtener las bitácoras con los filtros
    query = """
        SELECT b.idBitacora, b.fecha_hora_entrada, b.fecha_hora_salida, u.Correo, 
        u.Nombres, u.Apellido_p, u.Apellido_m, u.Carrera, r.Rol

        FROM bitacora b
        JOIN Usuarios u ON b.id_Usuarios = u.idUsuarios
        LEFT JOIN Rol r ON u.id_Rol = r.idRol
        WHERE 1=1
    """

    # Filtrar por fecha de ingreso si se proporciona
    if fecha_inicio:
        query += " AND b.fecha_hora_entrada >= %s"
        params.append(fecha_inicio)

    # Filtrar por nombre si se proporciona
    if nombre:
        query += " AND (u.Nombres LIKE %s OR u.Apellido_p LIKE %s OR u.Apellido_m LIKE %s)"
        params.extend([f'%{nombre}%', f'%{nombre}%', f'%{nombre}%'])

    # Filtrar por carrera si se proporciona
    if carrera:
        query += " AND u.Carrera LIKE %s"
        params.append(f'%{carrera}%')

    # Obtener las bitácoras
    bitacoras = obtener_bitacoras(conn, params, query)

    # Cerrar la conexión a la base de datos
    conn.close()

    # Generar el reporte PDF con los resultados obtenidos
    return generar_pdf(bitacoras)
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import make_response

def generar_pdf(bitacoras):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Definir márgenes y ajustes de tamaño de fuente
    margin_left = 30
    margin_top = 750
    font_size = 8  # Reducir tamaño de fuente

    # Títulos de la tabla (ajustado para que quepa mejor)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin_left, margin_top, "ID")
    c.drawString(margin_left + 20, margin_top, "Correo Usuario")
    c.drawString(margin_left + 140, margin_top, "Nombre Completo")
    c.drawString(margin_left + 250, margin_top, "Carrera")
    c.drawString(margin_left + 310, margin_top, "Fecha de Ingreso")
    c.drawString(margin_left + 400, margin_top, "Fecha de Salida")
    c.drawString(margin_left + 500, margin_top, "Rol")

    # Datos de la bitácora
    y_position = margin_top - 20  # Empieza por debajo del título

    for bitacora in bitacoras:
        c.setFont("Helvetica", font_size)

        # Dibujar los datos de cada bitácora ajustados para que quepan
        c.drawString(margin_left, y_position, str(bitacora[0]))  # ID Bitácora
        c.drawString(margin_left + 20, y_position, bitacora[3])  # Correo Usuario
        c.drawString(margin_left + 140, y_position, f"{bitacora[4]} {bitacora[5]} {bitacora[6]}")  # Nombre Completo
        c.drawString(margin_left + 250, y_position, bitacora[7])  # Carrera
        c.drawString(margin_left + 310, y_position, format_fecha(str(bitacora[1])))  # Fecha de Ingreso
        c.drawString(margin_left + 400, y_position, format_fecha(str(bitacora[2])))  # Fecha de Salida (formateada)
        c.drawString(margin_left + 500, y_position, bitacora[8])

        y_position -= 12  # Espacio para la siguiente fila

        # Si llegamos al final de la página, crear una nueva página
        if y_position < 50:
            c.showPage()
            y_position = margin_top - 20
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margin_left, y_position, "ID Bitácora")
            c.drawString(margin_left + 20, y_position, "Correo Usuario")
            c.drawString(margin_left + 140, y_position, "Nombre Completo")
            c.drawString(margin_left + 250, y_position, "Carrera")
            c.drawString(margin_left + 310, y_position, "Fecha de Ingreso")
            c.drawString(margin_left + 400, y_position, "Fecha de Salida")
            c.drawString(margin_left + 500, y_position, "Rol")
            y_position -= 20  # Espacio adicional para los datos de la siguiente página

    # Finalizamos el PDF
    c.showPage()
    c.save()

    # Regresar el archivo PDF al navegador
    buffer.seek(0)

    # Crear una respuesta con el contenido del PDF y el encabezado de disposición de contenido
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=bitacora_report.pdf'  # Muestra el PDF en línea

    return response



# Ruta para servir la imagen desde la base de datos
@app.route('/imagen/<int:id_usuario>')
def imagen(id_usuario):
    # Conectar a la base de datos
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Obtener la imagen del usuario por ID
    cursor.execute("SELECT imagen FROM Usuarios WHERE idUsuarios = %s", (id_usuario,))
    imagen_data = cursor.fetchone()

    # Cerrar la conexión
    cursor.close()
    conn.close()

    if imagen_data:
        return send_file(io.BytesIO(imagen_data[0]), mimetype='image/jpeg')
    else:
        return 'Imagen no encontrada', 404
    

@app.route('/roles')
def roles():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Obtener el valor de búsqueda si existe
    search_rol = request.args.get('search_rol', '')

    if search_rol:
        # Si se proporcionó un término de búsqueda, buscar en la base de datos
        cursor.execute("SELECT idRol, Rol FROM Rol WHERE Rol LIKE %s", ('%' + search_rol + '%',))
    else:
        # Si no hay búsqueda, obtener todos los roles
        cursor.execute("SELECT idRol, Rol FROM Rol")
    
    roles = cursor.fetchall()

    # Cerrar la conexión
    cursor.close()
    conn.close()

    # Renderizar la plantilla HTML y pasarle los datos de los roles
    return render_template('roles.html', roles=roles)

# Ruta para editar rol
@app.route('/editar_rol/<int:id_rol>', methods=['GET', 'POST'])
def editar_rol(id_rol):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    if request.method == 'POST':
        # Obtener los datos del formulario
        rol = request.form['rol']

        # Actualizar el rol en la base de datos
        query = '''
            UPDATE Rol
            SET Rol=%s
            WHERE idRol=%s
        '''
        cursor.execute(query, (rol, id_rol))
        conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('roles'))

    # Obtener los datos actuales del rol
    cursor.execute("SELECT * FROM Rol WHERE idRol = %s", (id_rol,))
    rol = cursor.fetchone()

    # Cerrar la conexión
    cursor.close()
    conn.close()

    # Si el rol no existe
    if not rol:
        return 'Rol no encontrado', 404

    return render_template('roles.html', rol=rol)

# Ruta para eliminar rol
@app.route('/eliminar_rol/<int:id_rol>', methods=['GET'])
def eliminar_rol(id_rol):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Eliminar el rol de la base de datos
    cursor.execute("DELETE FROM Rol WHERE idRol = %s", (id_rol,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('roles'))

# Ruta para agregar un rol
@app.route('/submit_rol', methods=['POST'])
def submit_rol():
    if request.method == 'POST':
        rol = request.form['rol']

        # Conexión a la base de datos MySQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insertar el nuevo rol en la base de datos
        query = '''
            INSERT INTO Rol (Rol)
            VALUES (%s)
        '''
        cursor.execute(query, (rol,))
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('roles'))





# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

                










