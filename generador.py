import os
# Configuración estricta para evitar fragmentación en la GPU
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import sys
import subprocess
from pathlib import Path
import json

# =========================================================
# GESTOR DE DEPENDENCIAS AUTOMÁTICO
# =========================================================
def asegurar_dependencias():
    try:
        import faiss
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError:
        ruta_req = Path(__file__).resolve().parent / "requirements.txt"
        if ruta_req.exists():
            print(f"Instalando dependencias desde {ruta_req.name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(ruta_req), "--quiet"])
            print("Dependencias listas.\n")
        else:
            print("Error: No se encontró requirements.txt. Instala: torch, sentence-transformers, faiss-cpu, numpy.")
            sys.exit(1)

asegurar_dependencias()

# =========================================================
# IMPORTACIONES DEL PROYECTO
# =========================================================
import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

# =========================================================
# LÓGICA DEL MOTOR RAG
# =========================================================
def cargar_metadatos(ruta_metadata: Path) -> list:
    print(f"Cargando metadatos: {ruta_metadata.name}")
    metadatos = []
    with open(ruta_metadata, "r", encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                metadatos.append(json.loads(linea))
    return metadatos

def generar_respuestas(archivo_consultas: Path, dir_base_vectorial: Path, archivo_salida: Path):
    ruta_indice = dir_base_vectorial / "index.faiss"
    ruta_metadata = dir_base_vectorial / "metadata.jsonl"
    
    print(f"Cargando índice FAISS: {ruta_indice.name}")
    indice_faiss = faiss.read_index(str(ruta_indice))
    metadatos = cargar_metadatos(ruta_metadata)

    # Configuración de hardware
    dispositivo = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Inicializando BAAI/bge-m3 en {dispositivo.upper()}...")
    modelo = SentenceTransformer("BAAI/bge-m3", device=dispositivo)
    modelo.max_seq_length = 512

    print(f"Procesando consultas: {archivo_consultas.name}")
    resultados_finales = []
    
    with open(archivo_consultas, "r", encoding="utf-8") as f:
        for linea in f:
            if not linea.strip(): continue
            consulta = json.loads(linea)
            id_consulta = consulta.get("id", "ID_DESCONOCIDO")
            texto_pregunta = consulta.get("pregunta", "")

            with torch.no_grad():
                vector_pregunta = modelo.encode([texto_pregunta], normalize_embeddings=True, show_progress_bar=False)
            
            vector_pregunta_np = np.array(vector_pregunta).astype('float32')

            # Buscamos 20 para filtrar los 10 mejores fragmentos únicos
            distancias, indices_recuperados = indice_faiss.search(vector_pregunta_np, 20)
            
            fragmentos_top = []
            agregacion_docs = {} 

            for rank, idx_metadato in enumerate(indices_recuperados[0]):
                if idx_metadato != -1 and idx_metadato < len(metadatos):
                    info = metadatos[idx_metadato]
                    doc_id = info.get("doc_id", "DESCONOCIDO")
                    score = float(distancias[0][rank])
                    
                    # 10 Fragmentos más relevantes
                    if len(fragmentos_top) < 10:
                        fragmentos_top.append({
                            "texto": info.get("texto", "")[:1500], # ~250 palabras
                            "chunk_id": info.get("chunk_id", f"chunk_{idx_metadato}")
                        })
                    
                    # Agregación para los 3 docs más relevantes
                    agregacion_docs[doc_id] = agregacion_docs.get(doc_id, 0) + score

            # Ordenar documentos por relevancia agregada
            docs_ordenados = sorted(agregacion_docs.items(), key=lambda x: x[1], reverse=True)
            top_3_docs = [doc_id for doc_id, score in docs_ordenados[:3]]

            resultados_finales.append({
                "id": id_consulta,
                "top_3_documentos": top_3_docs,
                "top_10_fragmentos": fragmentos_top
            })

    # Guardar resultados
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(archivo_salida, "w", encoding="utf-8") as f_out:
        for res in resultados_finales:
            f_out.write(json.dumps(res, ensure_ascii=False) + "\n")
            
    print(f"Proceso finalizado. Guardado en: {archivo_salida.name}")

if __name__ == "__main__":
    DIR = Path(__file__).resolve().parent
    ruta_consultas = list(DIR.rglob("consultas.jsonl"))[0]
    ruta_base = list(DIR.rglob("index.faiss"))[0].parent
    
    generar_respuestas(ruta_consultas, ruta_base, DIR / "resultados.jsonl")