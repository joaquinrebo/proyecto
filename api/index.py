import os
import re
import io
import csv
from flask import Flask, jsonify, request, Response
import requests
from datetime import datetime

app = Flask(__name__)

# --- Variables globales adaptables ---
auditoria_log = {"fecha_ejecucion": "", "leidos": 0, "procesados": 0, "duplicados_eliminados": 0, "consolidados": 0, "no_encontrados": 0, "errores": 0}
tabla_final_dinamica = {"columnas": ["Comuna Normalizada", "Región", "Habitantes"], "filas": []}

@app.route('/api/procesar_archivo', methods=['POST'])
def procesar_archivo():
    global auditoria_log, tabla_final_dinamica
    if 'archivo' not in request.files: return jsonify({"error": "Sin archivo"})
    
    archivo = request.files['archivo']
    nombre_archivo = archivo.filename.lower()
    
    # EL ARREGLO DEL ERROR: errors='replace' evita que caracteres raros rompan la app
    contenido = archivo.stream.read().decode('utf-8', errors='replace')
    
    auditoria_log = {"fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "leidos": 0, "procesados": 0, "duplicados_eliminados": 0, "consolidados": 0, "no_encontrados": 0, "errores": 0}
    filas = []
    
    # EL ARREGLO DE COLUMNAS: Detectamos si es el archivo de Famosos
    if '2' in nombre_archivo or 'famosos' in nombre_archivo or bool(re.search(r'\d+\.\s+[A-Za-z]', contenido[:50])):
        columnas = ["Nombre del Famoso", "Fecha de Nacimiento", "Edad Aprox."]
        texto = contenido.replace('-\n ', '- ').replace(' \n', ' ').replace('\n ', '')
        vistos = set()
        for linea in texto.split('\n'):
            if not linea.strip(): continue
            auditoria_log["leidos"] += 1
            match = re.search(r'\d+\.\s+(.*?)\s+-\s+(.*)', linea)
            if match:
                nombre = match.group(1).strip()
                fecha_str = match.group(2).strip()
                edad = "Desconocida"
                if "a.C." in fecha_str:
                    ym = re.search(r'(\d+)\s*a\.C\.', fecha_str)
                    if ym: edad = 2026 + int(ym.group(1))
                else:
                    ym = re.search(r'(\d{4})', fecha_str)
                    if ym: edad = 2026 - int(ym.group(1))
                
                if nombre in vistos:
                    auditoria_log["duplicados_eliminados"] += 1
                else:
                    vistos.add(nombre)
                    filas.append([nombre, fecha_str, f"{edad} años"])
                    auditoria_log["consolidados"] += 1
                auditoria_log["procesados"] += 1
    else:
        # Formato Datos 3 (Lugares/Comunas)
        columnas = ["Lugar / Comuna", "Región", "Habitantes"]
        texto = re.sub(r',\s*\n\s*', ', ', contenido)
        texto = re.sub(r'([a-zA-Z])\s*\n\s*([a-zA-Z])', r'\1 \2', texto)
        vistos = set()
        for linea in texto.split('\n'):
            if not linea.strip() or linea.startswith('Nombre'): continue
            auditoria_log["leidos"] += 1
            
            if ';' in linea: nombre = linea.split(';')[0].strip().title()
            else: nombre = linea.split(',')[0].strip().title()
            
            if not nombre: continue
            if nombre in vistos:
                auditoria_log["duplicados_eliminados"] += 1
            else:
                vistos.add(nombre)
                filas.append([nombre, "Dato por API", "Dato por API"])
                auditoria_log["consolidados"] += 1
            auditoria_log["procesados"] += 1

    tabla_final_dinamica["columnas"] = columnas
    tabla_final_dinamica["filas"] = filas

    return jsonify({"mensaje": "Archivo procesado con éxito", "log": auditoria_log, "tabla": tabla_final_dinamica})

@app.route('/api/auditoria', methods=['GET'])
def obtener_auditoria():
    return jsonify({"log": auditoria_log, "tabla": tabla_final_dinamica})

@app.route('/api/descargar_comunas', methods=['GET'])
def descargar_comunas():
    global tabla_final_dinamica
    si = io.StringIO()
    writer = csv.writer(si)
    if tabla_final_dinamica["columnas"]:
        writer.writerow(tabla_final_dinamica["columnas"])
        for fila in tabla_final_dinamica["filas"]: writer.writerow(fila)
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=datos_limpios.csv"})

# --- PARTE II: Famosos (Lectura automática para la vista web) ---
@app.route('/api/lista_famosos', methods=['GET'])
def obtener_lista_famosos():
    base_dir = os.path.dirname(__file__)
    ruta = os.path.join(base_dir, 'DATOS2026-2.txt')
    if not os.path.exists(ruta): ruta = os.path.join(base_dir, 'DATOS2026-2.TXT')
    
    famosos_dict = {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read().replace('-\n ', '- ').replace(' \n', ' ').replace('\n ', '')
            for linea in contenido.split('\n'):
                match = re.search(r'\d+\.\s+(.*?)\s+-\s+(.*)', linea)
                if match:
                    nombre = match.group(1).strip()
                    fecha_str = match.group(2).strip()
                    edad = "Desconocida"
                    if "a.C." in fecha_str:
                        ym = re.search(r'(\d+)\s*a\.C\.', fecha_str)
                        if ym: edad = 2026 + int(ym.group(1))
                    else:
                        ym = re.search(r'(\d{4})', fecha_str)
                        if ym: edad = 2026 - int(ym.group(1))
                    famosos_dict[nombre] = {"nombre": nombre, "edad": edad, "fecha": fecha_str}
        return jsonify(list(famosos_dict.values()))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/famosos', methods=['GET'])
def famoso_imagen():
    nombre = request.args.get('nombre', '')
    url = f"https://es.wikipedia.org/w/api.php?action=query&titles={nombre}&prop=pageimages&format=json&pithumbsize=500"
    headers = {'User-Agent': 'ProyectoInacap2026/1.0'}
    
    try:
        respuesta = requests.get(url, headers=headers).json()
        paginas = respuesta.get('query', {}).get('pages', {})
        for page_id, info in paginas.items():
            if 'thumbnail' in info:
                return jsonify({
                    "nombre": nombre,
                    "imagen": info['thumbnail']['source'],
                    "fuente": "Wikipedia",
                    "fecha_captura": "No provista"
                })
        return jsonify({"error": "No se encontró imagen en Wikipedia"})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- PARTE III: Lugares ---
@app.route('/api/lugares', methods=['GET'])
def lugares_historicos():
    base_dir = os.path.dirname(__file__)
    ruta = os.path.join(base_dir, 'DATOS2026-3.TXT')
    if not os.path.exists(ruta): ruta = os.path.join(base_dir, 'DATOS2026-3.txt')
    
    lugares_dict = {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            texto = f.read()
            texto = re.sub(r',\s*\n\s*', ', ', texto)
            texto = re.sub(r'([a-zA-Z])\s*\n\s*([a-zA-Z])', r'\1 \2', texto)
            
            lineas = texto.split('\n')
            for linea in lineas[1:]:
                partes = linea.split(';')
                if len(partes) >= 3:
                    nombre = partes[0].strip()
                    direccion = partes[1].strip()
                    coords = partes[2].split(',')
                    if len(coords) == 2:
                        try:
                            lat = float(coords[0].strip())
                            lng = float(coords[1].strip())
                            lugares_dict[nombre] = {"nombre": nombre, "lat": lat, "lng": lng, "direccion": direccion}
                        except ValueError:
                            pass
        return jsonify(list(lugares_dict.values()))
    except Exception as e:
        return jsonify({"error": str(e)})

def handler(event, context):
    return app(event, context)