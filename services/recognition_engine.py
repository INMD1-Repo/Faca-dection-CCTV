from sklearn.svm import SVC
import joblib

class FaceRecognizer:
    def __init__(self):
        self.svm_model = joblib.load('models/svm_face_model.pkl')
        
    async def recognize(self, embedding: torch.Tensor) -> str:
        # FaceNet 임베딩 변환
        embedding_np = embedding.cpu().numpy().reshape(1, -1)
        
        # SVM 예측
        pred = self.svm_model.predict(embedding_np)
        proba = self.svm_model.predict_proba(embedding_np)[0]
        
        if np.max(proba) > 0.7:  # 70% 이상 신뢰도
            return self.svm_model.classes_[np.argmax(proba)]
        else:
            return "unknown"