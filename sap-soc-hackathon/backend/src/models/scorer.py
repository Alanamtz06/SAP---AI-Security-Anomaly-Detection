import pandas as pd
import numpy as np
import joblib
from pathlib import Path

class ModelRegistry:
    """Carga y gestiona los 4 modelos"""
    
    def __init__(self):
        self.models = {}
        self._load_all()
    
    def _load_all(self):
        """Carga los 4 modelos sklearn"""
        artifact_dir = Path(__file__).parent.parent.parent / 'artifacts'
        model_names = [
            'IF_SYSTEM_PEAK', 'IF_SYSTEM_OFFPEAK',
            'IF_LLM_PEAK', 'IF_LLM_OFFPEAK'
        ]
        for name in model_names:
            path = artifact_dir / f'{name}.joblib'
            if path.exists():
                self.models[name] = joblib.load(path)
                print(f"✓ Loaded {name}")
            else:
                print(f"⚠ {name} not found at {path}")
    
    def score_system_log(self, features, is_peak):
        """Score un log de SYSTEM"""
        model_name = 'IF_SYSTEM_PEAK' if is_peak else 'IF_SYSTEM_OFFPEAK'
        model = self.models.get(model_name)
        
        if model is None:
            raise RuntimeError(f"Model {model_name} not loaded")
        
        score_raw = model.score_samples([features])[0]
        score_norm = 1 / (1 + np.exp(-score_raw))
        
        return score_raw, score_norm
    
    def score_llm_log(self, features, is_peak):
        """Score un log de LLM"""
        model_name = 'IF_LLM_PEAK' if is_peak else 'IF_LLM_OFFPEAK'
        model = self.models.get(model_name)
        
        if model is None:
            raise RuntimeError(f"Model {model_name} not loaded")
        
        score_raw = model.score_samples([features])[0]
        score_norm = 1 / (1 + np.exp(-score_raw))
        
        return score_raw, score_norm

if __name__ == '__main__':
    registry = ModelRegistry()
    dummy_sys_features = np.array([0.5, 0.3, 0.2, 0.8, 1, 0, 10, 0.4, 0.1])
    raw, norm = registry.score_system_log(dummy_sys_features, is_peak=True)
    print(f"System Peak Score: raw={raw:.3f}, norm={norm:.3f}")