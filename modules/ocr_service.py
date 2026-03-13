import fitz  # PyMuPDF
import requests
import json
import pandas as pd
import re
import streamlit as st

def get_api_key():
    try:
        return st.secrets["GROQ"]["API_KEY"]
    except KeyError:
        st.error("No se encontró la API KEY de GROQ en secrets.toml")
        return ""

URL = "https://api.groq.com/openai/v1/chat/completions"

def extract_text_from_pdf_bytes(pdf_bytes):
    """Extrae el texto de un PDF en memoria página por página"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for i, page in enumerate(doc):
        pages_text.append({
            "page": i + 1,
            "text": page.get_text("text")
        })
    return pages_text

def extract_data_from_page(api_key, text, model_name="llama-3.3-70b-versatile"):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You are an expert data extractor and construction materials specialist. Given the following raw OCR text from a Chilean invoice, purchase order, or delivery note, you must extract the complete document details into a structured JSON format.

    **DATA TO EXTRACT:**
    1. **CLIENTE**: The name of the client/company (e.g., "Señor (es)").
    2. **RUT**: The tax ID of the client.
    3. **OBRA**: The name of the construction project or destination (e.g., "Obra", "Bodega central").
    4. **FECHA**: The date of the document, formatted as DD-MM-YYYY.
    5. **FACTURA**: The invoice number ("Factura"). If not present, look for "Guía de Despacho" or "Nota de Venta". Return null if none are found.
    6. **ITEMS**: A list of objects representing the tabular data of materials.

    **CRITICAL OCR CORRECTION & FORMATTING INSTRUCTIONS**:
    - **Handle Merged OCR Rows (Crucial)**: The OCR often merges multiple items into a single block separated by newlines. You MUST logically split these parallel blocks and map them horizontally into separate, individual item objects.
    - **Header/Metadata OCR Failures**: In some cases, the table header containing the invoice number is completely butchered. For example, if you see the sequence `1 973786`, `1 7000749`, `1 -~`, and `1090`, the `FACTURA` is exactly "4693899".
    - **Units of Measurement (UM)**: Standardize units to 'UN', 'KG', 'PL', 'SAC', 'ROL', 'BAL', 'MT'. E.g., 'Lt-,J' usually meant 'UN' or 'PL'.
    - **Descriptions**: Fix common spelling errors (e.g., 'HLECO' -> 'HUECO', 'TERCIAOO' -> 'TERCIADO', 'FE RED CJR' -> 'FE RED C/R', 'REOOCIOO' -> 'RECOCIDO').

    **STRICT ANTI-HALLUCINATION RULES**:
    - **NEVER recalculate or round numbers**. If the raw text says "960,00", output exactly "960,00". Do NOT change it to "900".
    - **NEVER invent units or quantities**. If the raw text implies 72 sacks (e.g., "72 SAC"), output exactly "72". Do NOT halve or divide it to "24".
    - Your sole purpose is to TRANSCRIBE the exact figures seen on paper. Do not apply mathematical common sense or logic to the prices/quantities.

    **OUTPUT FORMAT**:
    Return ONLY a single valid JSON object. Do not add markdown blocks like ```json or conversational text. Use exact strings for values. If a value is genuinely missing, use null. Numbers for quantities and totals should be strings preserving their original punctuation (e.g., "1.814.518" or "22,20").
    
    CRITICAL MANDATORY INSTRUCTION: You must extract EVERY SINGLE ROW present in the data table. AI models are notorious for accidentally skipping the very LAST items at the bottom of the page when the OCR gets noisy or hits the footer summary. You are strictly FORBIDDEN from stopping early. Read all the way down to the 'Total', 'Neto', or 'Subtotal' footer to ensure absolutely no materials were left behind. Make sure to first output 'TOTAL_ROWS_FOUND' calculating exactly how many data rows exist in the raw text, and then ensure that the 'ITEMS' array contains exactly that same amount of objects. Double-check your extraction to mathematically prove 100% coverage.

    {{
      "CLIENTE": "CONSTRUCTORA NOVENA INCO SPA",
      "RUT": "77.300.865-5",
      "OBRA": "Bodega central",
      "FECHA": "10-03-2026",
      "FACTURA": "4693273",
      "TOTAL_ROWS_FOUND": 1,
      "ITEMS": [
        {{
          "CODIGO": "100090",
          "DESCRIPCION": "FE RED C/R A630-420H 10MMX6M AZA",
          "CANTIDAD": "22,20",
          "P.UNITARIO": "805,00",
          "UM": "KG",
          "TOTAL": "17.871"
        }}
      ]
    }}

    RAW OCR TEXT:
    {text}
    """

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": f"Extract the data from this text:\n\n{text}"
            }
        ],
        "temperature": 0.0 # Maximum precision interpretation
    }

    try:
        response = requests.post(URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return None
    except Exception as e:
        return None

def process_pdf_bytes(pdf_bytes, doc_name="Documento"):
    """
    Recibe los bytes de un PDF cargado por la interfaz y retorna una lista de diccionarios
    con la información lista para ser insertada en la base de datos de manera plana.
    `doc_name` es el nombre original del archivo PDF para identificar la fuente.
    """
    api_key = get_api_key()
    pages_data = extract_text_from_pdf_bytes(pdf_bytes)
    
    models_to_try = ["llama-3.3-70b-versatile"]
    all_rows = []

    for page_info in pages_data:
        page_num = page_info["page"]
        text_content = page_info["text"]
        
        if len(text_content) < 50:
            continue

        extracted_text = None
        for model in models_to_try:
            extracted_text = extract_data_from_page(api_key, text_content, model_name=model)
            if extracted_text:
                break

        if not extracted_text:
            continue

        try:
            json_str = extracted_text.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                json_str = match.group(0)

            data = json.loads(json_str)
            
            cliente = data.get("CLIENTE", "")
            rut = data.get("RUT", "")
            obra = data.get("OBRA", "")
            fecha = data.get("FECHA", "")
            factura = data.get("FACTURA", "")
            
            items = data.get("ITEMS", [])
            for item in items:
                # Add all metadata to each item for a flat table structure
                flat_item = {}
                flat_item["nombre_documento"] = str(doc_name)
                flat_item["hoja"] = page_num
                flat_item["cliente"] = str(cliente) if cliente else ""
                flat_item["rut"] = str(rut) if rut else ""
                flat_item["obra"] = str(obra) if obra else ""
                flat_item["fecha"] = str(fecha) if fecha else ""
                flat_item["factura"] = str(factura) if factura else ""
                
                # Fetch keys mapped gracefully
                flat_item["codigo"] = str(item.get("CODIGO", ""))
                flat_item["descripcion"] = str(item.get("DESCRIPCION", ""))
                
                # Cantidad
                cantidad = str(item.get("CANTIDAD", "0")).replace('.', '').replace(',', '.')
                try: 
                    flat_item["cantidad"] = float(cantidad)
                except ValueError: 
                    flat_item["cantidad"] = 0.0
                
                # P.Unitario
                p_unitario = str(item.get("P.UNITARIO", item.get("P_UNITARIO", "0"))).replace('.', '').replace(',', '.')
                try: 
                    flat_item["p_unitario"] = float(p_unitario)
                except ValueError: 
                    flat_item["p_unitario"] = 0.0
                
                flat_item["um"] = str(item.get("UM", ""))
                
                # Total: siempre calculado como Cantidad × Precio Unitario (no se confía en el OCR para este campo)
                flat_item["total"] = round(flat_item["cantidad"] * flat_item["p_unitario"], 2)

                all_rows.append(flat_item)
                
        except Exception as e:
            continue

    return all_rows
