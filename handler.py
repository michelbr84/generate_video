import runpod
from runpod.serverless.utils import rp_upload
import os
import websocket
import base64
import json
import uuid
import logging
import urllib.request
import urllib.parse
import binascii
import subprocess
import time

# Configurações de Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_address = os.getenv('SERVER_ADDRESS', '127.0.0.1')
client_id = str(uuid.uuid4())


def to_nearest_multiple_of_16(value):
    """Converte largura/altura para múltiplos de 16"""
    try:
        numeric_value = float(value)
    except Exception:
        raise Exception(f"Valor de width/height não numérico: {value}")
    adjusted = int(round(numeric_value / 16.0) * 16)
    return max(adjusted, 16)


def process_input(input_data, temp_dir, output_filename, input_type):
    """Processa entrada para arquivo local"""
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.abspath(os.path.join(temp_dir, output_filename))

    if input_type == "path":
        return input_data

    elif input_type == "url":
        return download_file_from_url(input_data, file_path)

    elif input_type == "base64":
        return save_base64_to_file(input_data, temp_dir, output_filename)

    else:
        raise Exception(f"Tipo de entrada não suportado: {input_type}")


def download_file_from_url(url, output_path):
    """Download via wget"""
    try:
        result = subprocess.run([
            'wget', '-O', output_path, '--no-verbose', url
        ], capture_output=True, text=True)

        if result.returncode == 0:
            return output_path
        else:
            raise Exception(f"Erro ao baixar URL: {result.stderr}")

    except Exception as e:
        raise Exception(f"Erro ao baixar arquivo: {e}")


def save_base64_to_file(base64_data, temp_dir, output_filename):
    """Decodifica Base64 para arquivo"""
    try:
        decoded_data = base64.b64decode(base64_data)

        file_path = os.path.abspath(os.path.join(temp_dir, output_filename))
        with open(file_path, 'wb') as f:
            f.write(decoded_data)
        return file_path

    except (binascii.Error, ValueError) as e:
        raise Exception(f"Base64 inválido: {e}")


def queue_prompt(prompt):
    """Envia prompt ao ComfyUI"""
    url = f"http://{server_address}:8188/prompt"
    data = json.dumps({"prompt": prompt, "client_id": client_id}).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_history(prompt_id):
    url = f"http://{server_address}:8188/history/{prompt_id}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def get_videos(ws, prompt):
    """Espera execução e captura video(s)"""
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_videos = {}

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message.get('type') == 'executing' and \
               message['data'].get('node') is None and \
               message['data'].get('prompt_id') == prompt_id:
                break

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        videos_output = []
        if 'gifs' in node_output:
            for video in node_output['gifs']:
                with open(video['fullpath'], 'rb') as f:
                    video_data = base64.b64encode(f.read()).decode('utf-8')
                videos_output.append(video_data)
        output_videos[node_id] = videos_output

    return output_videos


def load_workflow(workflow_path):
    with open(workflow_path, 'r') as file:
        return json.load(file)


def handler(job):
    job_input = job.get("input", {})
    temp_id = f"task_{uuid.uuid4()}"

    logger.info("Processando entrada do job...")

    # Entrada de imagem principal
    image_path = None

    if "image_path" in job_input:
        image_path = process_input(job_input["image_path"], temp_id, "input_image.jpg", "path")
    elif "image_url" in job_input:
        image_path = process_input(job_input["image_url"], temp_id, "input_image.jpg", "url")
    elif "image_base64" in job_input:
        image_path = process_input(job_input["image_base64"], temp_id, "input_image.jpg", "base64")

    if not image_path:
        raise Exception("Nenhuma imagem de entrada fornecida!")

    workflow_file = "/new_Wan22_api.json"
    workflow = load_workflow(workflow_file)

    # Ajuste de resolução
    width = to_nearest_multiple_of_16(job_input["width"])
    height = to_nearest_multiple_of_16(job_input["height"])

    # Aplicar parâmetros
    workflow["244"]["inputs"]["image"] = image_path
    workflow["541"]["inputs"]["num_frames"] = job_input.get("length", 81)
    workflow["135"]["inputs"]["positive_prompt"] = job_input.get("prompt", "")
    workflow["135"]["inputs"]["negative_prompt"] = job_input.get("negative_prompt", "")
    workflow["220"]["inputs"]["seed"] = job_input.get("seed", 42)
    workflow["540"]["inputs"]["seed"] = job_input.get("seed", 42)
    workflow["540"]["inputs"]["cfg"] = job_input.get("cfg", 5)
    workflow["235"]["inputs"]["value"] = width
    workflow["236"]["inputs"]["value"] = height
    workflow["498"]["inputs"]["context_overlap"] = job_input.get("context_overlap", 48)

    # WebSocket ComfyUI
    ws_url = f"ws://{server_address}:8188/ws?clientId={client_id}"
    ws = websocket.WebSocket()
    ws.connect(ws_url)

    videos = get_videos(ws, workflow)
    ws.close()

    for node in videos:
        if videos[node]:
            return {"video_base64": videos[node][0]}

    return {"error": "Nenhum vídeo encontrado."}


runpod.serverless.start({"handler": handler})
