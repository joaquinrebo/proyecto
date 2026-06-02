import os
import re
from flask import Flask, jsonify, request
import requests
from datetime import datetime

app = Flask(__name__)

# --- PARTE I: Comunas (Se mantiene la lógica de carga masiva anterior) ---
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

# --- PARTE II: Famosos (Leyendo DATOS2026-2.txt) ---
@app.route('/api/lista_famosos', methods=['GET'])
def obtener_lista_famosos():
    ruta_archivo = os.path.join(os.path.dirname(__file__), 'DATOS2026-2.txt')
    famosos_dict = {}
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            # Reparar saltos de línea incorrectos del archivo original
            contenido = f.read().replace('-\n ', '- ').replace(' \n', ' ').replace('\n ', '')
            lineas = contenido.split('\n')
            
            for linea in lineas:
                # Extraer nombre y fecha ignorando el número de lista
                match = re.search(r'\d+\.\s+(.*?)\s+-\s+(.*)', linea)
                if match:
                    nombre = match.group(1).strip()
                    fecha_str = match.group(2).strip()
                    
                    # Calcular la edad basada en el año actual (2026)
                    edad = "Desconocida"
                    if "a.C." in fecha_str:
                        year_match = re.search(r'(\d+)\s*a\.C\.', fecha_str)
                        if year_match:
                            edad = 2026 + int(year_match.group(1))
                    else:
                        year_match = re.search(r'(\d{4})', fecha_str)
                        if year_match:
                            edad = 2026 - int(year_match.group(1))
                            
                    # Guardar en diccionario elimina automáticamente a los duplicados
                    famosos_dict[nombre] = {"nombre": nombre, "edad": edad, "fecha": fecha_str}
        
        return jsonify(list(famosos_dict.values()))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/famosos', methods=['GET'])
def famoso_imagen():
    nombre = request.args.get('nombre', '')
    url = f"https://es.wikipedia.org/w/api.php?action=query&titles={nombre}&prop=pageimages&format=json&pithumbsize=500"
    try:
        respuesta = requests.get(url).json()
        paginas = respuesta.get('query', {}).get('pages', {})
        for page_id, info in paginas.items():
            if 'thumbnail' in info:
                return jsonify({
                    "nombre": nombre,
                    "imagen": info['thumbnail']['source'],
                    "fuente": "Wikipedia API",
                    "fecha_captura": "No provista"
                })
        return jsonify({"error": "No se encontró imagen para este famoso en Wikipedia"})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- PARTE III: Lugares (Leyendo DATOS2026-3.TXT) ---
@app.route('/api/lugares', methods=['GET'])
def lugares_historicos():
    ruta_archivo = os.path.join(os.path.dirname(__file__), 'DATOS2026-3.TXT')
    lugares_dict = {}
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            # Reparar coordenadas cortadas por saltos de línea (ej: Gran Muralla China)
            contenido = f.read().replace('\n ', '') 
            lineas = contenido.split('\n')
            
            for linea in lineas[1:]: # Omitir la primera línea (encabezados)
                partes = linea.split(';')
                if len(partes) >= 3:
                    nombre = partes[0].strip()
                    direccion = partes[1].strip()
                    coords = partes[2].split(',')
                    
                    if len(coords) == 2:
                        try:
                            lat = float(coords[0].strip())
                            lng = float(coords[1].strip())
                            # Guardar en diccionario elimina los duplicados (ej: Machu Picchu)
                            lugares_dict[nombre] = {"nombre": nombre, "lat": lat, "lng": lng, "direccion": direccion}
                        except ValueError:
                            continue
                            
        return jsonify(list(lugares_dict.values()))
    except Exception as e:
        return jsonify({"error": str(e)})

def handler(event, context):
    return app(event, context)