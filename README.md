# Wan2.2 • API Serverless para Geração de Vídeo (RunPod)

Este projeto implementa um servidor **Serverless** no RunPod para geração de vídeo a partir de uma imagem usando o modelo **Wan2.2**.  
O processamento é feito por meio de um workflow do **ComfyUI**, executando na GPU sob demanda.

O endpoint suporta:
- Imagem via **path**, **URL** ou **Base64**
- Parâmetros personalizáveis de geração
- Retorno do vídeo em **Base64**
- Controle de resolução, seed, steps e prompt
- Suporte à largura/altura em múltiplos de 16

---

## 🚀 Como funciona

1️⃣ O n8n (ou qualquer cliente HTTP) envia uma requisição `POST /run` com JSON de entrada  
2️⃣ O Serverless Worker executa o workflow Wan2.2 no ComfyUI  
3️⃣ O worker retorna o vídeo gerado em base64

---

## 🧠 Estrutura Principal do Worker

| Arquivo | Função |
|--------|--------|
| `handler.py` | Handler do RunPod Serverless — processa o job da API |
| `new_Wan22_api.json` | Workflow ComfyUI para geração de vídeo |
| `requirements.txt` | Dependências necessárias |
| `Dockerfile` | Configuração do ambiente GPU |
| `.env` (opcional) | SERVER_ADDRESS e outras configs |

---

## 🧩 Exemplo de requisição para `/run`

```json
{
  "input": {
    "prompt": "A futuristic robot running with glowing neon lights",
    "negative_prompt": "blurry, artifacts, distorted",
    "image_base64": "BASE64_DA_IMAGEM_AQUI",
    "width": 480,
    "height": 832,
    "length": 81,
    "steps": 10,
    "cfg": 2.0,
    "seed": 42
  }
}