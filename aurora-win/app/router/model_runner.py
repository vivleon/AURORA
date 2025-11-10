# app/router/model_runner.py
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# httpx는 requirements.txt에 추가해야 합니다.
# (또는 python-dotenv와 rich처럼 기본 설치)
try:
    import httpx
except ImportError:
    print("[WARN] httpx not installed. Cloud models will fail. (pip install httpx)")
    httpx = None

# llama.cpp 서버 포트 (start_local_models.bat 참조)
# model_manifest.json을 파싱하여 동적으로 포트를 찾는 것이 가장 좋음
LLAMA_CPP_PORT_MAP = {
    "main": 8081,
    "intent": 8082,
}

MODEL_ROUTER_PATH = Path(os.getenv("MODEL_ROUTER_PATH", "app/router/model_router.json"))

class ModelRouter:
    """
    model_router.json을 로드하고 태스크에 적합한 모델을 결정합니다.
    """
    def __init__(self, config_path: Path = MODEL_ROUTER_PATH):
        self.config_path = config_path
        self.config = {"defaults": {}, "rules": [], "models": {}}
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"[ModelRouter] Loaded router config from {self.config_path}")
        except (IOError, json.JSONDecodeError) as e:
            print(f"[ModelRouter ERROR] Failed to load {self.config_path}: {e}")

    def get_model_for_task(self, task: str, risk: str = "low", tokens_in: int = 0) -> Dict[str, Any]:
        """
        태스크, 위험도, 토큰 수를 기반으로 라우팅 규칙을 적용합니다.
        """
        # 1. 규칙(rules) 매칭
        for rule in self.config.get("rules", []):
            cond = rule.get("if", {})
            match = True
            
            if "risk" in cond and cond["risk"] != risk:
                match = False
            if "task" in cond and cond["task"] != task:
                match = False
            if "tokens_in" in cond and "lte" in cond["tokens_in"]:
                if tokens_in > cond["tokens_in"]["lte"]:
                    match = False
            
            if match:
                model_name = rule["then"].get("model")
                if model_name and model_name in self.config["models"]:
                    return self.config["models"][model_name]
                # 'then' 조건만 반환 (예: {'target': 'local'})
                return rule["then"]

        # 2. 기본값(defaults) 반환
        default_model_name = self.config["defaults"].get("model", "local_intent")
        if default_model_name in self.config["models"]:
            return self.config["models"][default_model_name]
            
        return {"uri": "local://phi3-mini-gguf"} # 최후의 폴백

# --- 싱글톤 인스턴스 ---
_router_instance = ModelRouter()

async def run_inference(
    task: str, 
    prompt: str, 
    risk: str = "low", 
    **kwargs
) -> Dict[str, Any]:
    """
    적합한 모델을 라우팅하고 추론을 실행합니다.
    (app/tools/nlp.py가 이 함수를 호출합니다)
    """
    
    # 1. 모델 결정
    model_config = _router_instance.get_model_for_task(task, risk, len(prompt.split()))
    model_uri = model_config.get("uri", "local://phi3-mini-gguf")
    
    print(f"[ModelRunner] Task '{task}' routed to model: {model_uri}")

    # 2. 추론 실행
    try:
        # A) 로컬 llama.cpp 서버
        if model_uri.startswith("local://"):
            # 예: "local://phi3-mini-gguf" -> 'phi3-mini-gguf' (manifest 키)
            model_key_from_uri = model_uri.split("://")[-1]
            
            # TODO: model_manifest.json을 파싱하여 포트/모델명을 정확히 찾아야 함
            # 임시로 'intent' 또는 'main'으로 하드코딩
            port = LLAMA_CPP_PORT_MAP.get("main", 8081)
            if "intent" in model_key_from_uri:
                 port = LLAMA_CPP_PORT_MAP.get("intent", 8082)

            url = f"http://127.0.0.1:{port}/completion"
            
            # llama.cpp API 페이로드
            payload = {
                "prompt": prompt,
                "n_predict": kwargs.get("max_tokens", 256),
                "temperature": model_config.get("temperature", 0.4),
                "stop": ["\n", "User:", "Aurora:"],
            }
            
            if not httpx:
                raise ImportError("httpx is required for llama.cpp server calls")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                content = response.json().get("content", "")
                return {"text": content, "model": model_uri}

        # B) 로컬 ONNX (임베딩 등)
        elif model_uri.startswith("local://onnx/"):
            # TODO: app/memory/vectorstore.py 내부의 ONNX 로직 호출
            print("[ModelRunner] ONNX embedding (not implemented)")
            return {"vector": [0.0] * 384, "model": model_uri}
            
        # C) 클라우드 (폴백)
        elif model_uri.startswith("cloud://"):
            # TODO: OpenAI/Anthropic/Gemini API 호출
            print("[ModelRunner] Cloud fallback (not implemented)")
            return {"text": f"[Cloud Fallback] {prompt}", "model": model_uri}
            
        else:
            raise ValueError(f"Unknown model URI scheme: {model_uri}")
            
    except Exception as e:
        print(f"[ModelRunner ERROR] Inference failed for {model_uri}: {e}")
        return {"text": None, "error": str(e), "model": model_uri}