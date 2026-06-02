from flask import Flask, jsonify, request
import requests
import difflib
from datetime import datetime

app = Flask(__name__)

# Simulación de API oficial / Dataset base
dataset_oficial = {
    "Florida": {"region": "Biobío", "habitantes": 10624},
    "La Florida": {"region": "Metropolitana", "habitantes": 366916},
    "Penco": {"region": "Biobío", "habitantes": 47367},
    "Talcahuano": {"region": "Biobío", "habitantes": 151722},
    "Concepción": {"region": "Biobío", "habitantes": 223574}
}

# Estructuras para almacenar la tabla final y auditoría en memoria
tabla_final = {}
auditoria_log = {
    "fecha_ejecucion": "",
    "leidos": 0,
    "procesados": 0,
    "duplicados_eliminados": 0,
    "consolidados": 0,
    "no_encontrados": 0,
    "errores": 0
}

@app.route('/api/comunas', methods=['GET'])
def procesar_comuna():
    global auditoria_log, tabla_final
    auditoria_log["fecha_ejecucion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    auditoria_log["leidos"] += 1
    
    comuna_input = request.args.get('nombre', '')
    comuna_limpia = comuna_input.strip().title()
    
    if not comuna_limpia:
        auditoria_log["errores"] += 1
        return jsonify({"error": "Debe ingresar una comuna."})

    # Sugerencia de Búsqueda
    nombres_oficiales = list(dataset_oficial.keys())
    coincidencias = difflib.get_close_matches(comuna_limpia, nombres_oficiales, n=3, cutoff=0.5)

    if not coincidencias:
        auditoria_log["procesados"] += 1
        auditoria_log["no_encontrados"] += 1
        return jsonify({"mensaje": f"No se encontró '{comuna_limpia}'.", "sugerencias": []})

    # Tomamos la mejor coincidencia
    mejor_match = coincidencias[0]
    
    # Evitar duplicados y consolidar
    if mejor_match in tabla_final:
        auditoria_log["duplicados_eliminados"] += 1
        estado = "Registro ignorado (Duplicado)"
    else:
        tabla_final[mejor_match] = dataset_oficial[mejor_match]
        auditoria_log["consolidados"] += 1
        estado = "Consolidado correctamente"

    auditoria_log["procesados"] += 1

    return jsonify({
        "comuna": mejor_match,
        "region": dataset_oficial[mejor_match]["region"],
        "habitantes": dataset_oficial[mejor_match]["habitantes"],
        "estado": estado,
        "sugerencias": coincidencias
    })

@app.route('/api/auditoria', methods=['GET'])
def obtener_auditoria():
    return jsonify({
        "log": auditoria_log,
        "tabla": tabla_final
    })

@app.route('/api/famosos', methods=['GET'])
def famoso_imagen():
    nombre = request.args.get('nombre', 'Madonna')
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
                    "fecha_captura": "Dato no provisto por la API" 
                })
        return jsonify({"error": "No se encontró imagen para este famoso"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/lugares', methods=['GET'])
def lugares_historicos():
    return jsonify([
        {"nombre": "Torre Eiffel", "lat": 48.8584, "lng": 2.2945},
        {"nombre": "Machu Picchu", "lat": -13.1631, "lng": -72.5450},
        {"nombre": "Taj Mahal", "lat": 27.1751, "lng": 78.0421}
    ])

def handler(event, context):
    return app(event, context)