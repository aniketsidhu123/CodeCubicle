"""
Hugging Face pure-Python LLM Manager (Singleton).
Handles loading the model natively into VRAM via transformers/torch, 
and gracefully unloading it after a period of inactivity to free GPU resources.
"""

import os
# Force HF_HOME to be an absolute path in the backend directory
os.environ["HF_HOME"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))

import time
import threading
import atexit

MODEL_NAME = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
IDLE_UNLOAD_SECONDS = int(os.getenv("LLM_IDLE_UNLOAD_SECS", "120"))  # 2 min


class HuggingFaceManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._lock = threading.Lock()
            self._pipeline = None
            self._unload_timer = None
            self._initialized = True
            atexit.register(self.shutdown)

    def ensure_model(self):
        """Loads the Hugging Face model into VRAM if it isn't already loaded."""
        with self._lock:
            if self._pipeline is not None:
                return

            print(f"[LLM Manager] Loading Hugging Face model '{MODEL_NAME}' into VRAM...")
            try:
                import torch
                from transformers import pipeline

                use_gpu = os.getenv("LLM_USE_GPU", "true").lower() == "true"
                device_map = "auto" if (use_gpu and torch.cuda.is_available()) else "cpu"
                
                # Using bfloat16 to fit nicely in 6GB VRAM
                self._pipeline = pipeline(
                    "text-generation",
                    model=MODEL_NAME,
                    torch_dtype=torch.bfloat16 if device_map != "cpu" else torch.float32,
                    device_map=device_map,
                    trust_remote_code=True
                )
                print(f"[LLM Manager] Model '{MODEL_NAME}' successfully loaded ({device_map}).")
            except Exception as e:
                print(f"[LLM Manager] Failed to load model: {e}")
                self._pipeline = None

    def unload_model(self):
        """Unload the model from GPU VRAM and run garbage collection."""
        with self._lock:
            if self._pipeline is not None:
                print(f"[LLM Manager] Unloading '{MODEL_NAME}' to free VRAM...")
                del self._pipeline
                self._pipeline = None
                
                try:
                    import torch
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
                
                print("[LLM Manager] VRAM freed successfully.")

    def _schedule_unload(self):
        """Schedule auto-unload of the model after idle timeout."""
        if self._unload_timer:
            self._unload_timer.cancel()
        self._unload_timer = threading.Timer(IDLE_UNLOAD_SECONDS, self.unload_model)
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def infer(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 512) -> str:
        """Runs inference natively using the loaded pipeline."""
        self.ensure_model()
        self._schedule_unload()
        
        if self._pipeline is None:
            return ""
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            # Qwen/Llama chat templating
            prompt = self._pipeline.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            outputs = self._pipeline(
                prompt,
                max_new_tokens=max_tokens,
                max_length=None,
                temperature=temperature if temperature > 0 else 0.1,
                do_sample=temperature > 0,
                return_full_text=False
            )
            return outputs[0]["generated_text"]
        except Exception as e:
            print(f"[LLM Manager] Inference failed: {e}")
            return ""

    def shutdown(self):
        """Cleanup handler."""
        if self._unload_timer:
            self._unload_timer.cancel()
        self.unload_model()


# Global singleton instance
llm_manager = HuggingFaceManager()
