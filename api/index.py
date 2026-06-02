import os
import re
import io
import csv
from flask import Flask, jsonify, request, Response
import requests
from datetime import datetime

app = Flask(__name__)

# --- PARTE I: Comunas ---
auditoria_log = {"fecha_ejecucion": "", "leidos": 0, "procesados": 0, "duplicados_eliminados": 0, "consolidados": 0, "no_encontrados": 0, "errores": 0}
tabla_final = {}

@app.route('/api/procesar_archivo', methods=['POST'])
def procesar_archivo():
    global auditoria_log, tabla_final
    if 'archivo' not in request.files: return jsonify({"error": "Sin archivo"})
    
    archivo = request.files['archivo']
    auditoria_log["fecha_ejecucion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    contenido = archivo.stream.read().decode('utf-8').splitlines()
    
    for linea in contenido:
        comuna_limpia = linea.split(',')[0].strip().title()
        if not comuna_limpia: continue
        auditoria_log["leidos"] += 1
        if comuna_limpia in tabla_final:
            auditoria_log["duplicados_eliminados"] += 1
        else:
            tabla_final[comuna_limpia] = {"region": "Dato por API", "habitantes": "Dato por API"}
            auditoria_log["consolidados"] += 1
        auditoria_log["procesados"] += 1

    return jsonify({"mensaje": "Archivo de comunas procesado con éxito", "log": auditoria_log})

@app.route('/api/auditoria', methods=['GET'])
def obtener_auditoria():
    return jsonify({"log": auditoria_log, "tabla": tabla_final})
@app.route('/api/descargar_comunas', methods=['GET'])
def descargar_comunas():
    global tabla_final
    
    # Crea un archivo en memoria para no romper las reglas de Vercel
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Escribe los encabezados del archivo
    writer.writerow(['Comuna Normalizada', 'Región', 'Habitantes'])
    
    # Escribe todas las filas procesadas
    for comuna, info in tabla_final.items():
        writer.writerow([comuna, info['region'], info['habitantes']])
        
    # Prepara la respuesta para que el navegador descargue el archivo
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=comunas_limpias_2026.csv"}
    )

# --- PARTE II: Famosos ---
@app.route('/api/lista_famosos', methods=['GET'])
def obtener_lista_famosos():
    base_dir = os.path.dirname(__file__)
    # Buscar el archivo sin importar si la extensión está en mayúscula o minúscula
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

# --- PARTE III: Lugares (Solucionado) ---
@app.route('/api/lugares', methods=['GET'])
def lugares_historicos():
    base_dir = os.path.dirname(__file__)
    ruta = os.path.join(base_dir, 'DATOS2026-3.TXT')
    if not os.path.exists(ruta): ruta = os.path.join(base_dir, 'DATOS2026-3.txt')
    
    lugares_dict = {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            texto = f.read()
            # Reparar coordenadas rotas (ej: 40.4319, \n 116.5704)
            texto = re.sub(r',\s*\n\s*', ', ', texto)
            # Reparar palabras cortadas (ej: Machu \n Picchu)
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