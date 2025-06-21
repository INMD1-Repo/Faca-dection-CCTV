import os
from typing import Dict, List, Optional
from core.config import settings

MODEL_STORAGE_PATH = settings.MODEL_STORAGE_PATH
DEVICE = settings.DEVICE

def load_known_face_embeddings_from_storage() -> Dict[str, List[torch.Tensor]]:
    """ MODEL_STORAGE_PATH에서 저장된 얼굴 임베딩을 로드합니다. """
    known_face_embeddings: Dict[str, List[torch.Tensor]] = {}
    os.makedirs(MODEL_STORAGE_PATH, exist_ok=True) # 저장 경로가 없으면 생성

    for person_name_folder in os.listdir(MODEL_STORAGE_PATH):
        person_dir = os.path.join(MODEL_STORAGE_PATH, person_name_folder)
        if os.path.isdir(person_dir):
            embeddings_file = os.path.join(person_dir, f"{person_name_folder}_embeddings.pt")
            if os.path.exists(embeddings_file):
                try:
                    # paste.txt에서는 리스트 of 텐서 ([N, D_embed] 또는 [1, D_embed])를 저장
                    loaded_embeddings: List[torch.Tensor] = torch.load(embeddings_file, map_location=DEVICE)
                    known_face_embeddings[person_name_folder] = loaded_embeddings
                    print(f"Loaded embeddings for: {person_name_folder}")
                except Exception as e:
                    print(f"Error loading embeddings for '{person_name_folder}': {e}")
    if known_face_embeddings:
        print(f"Successfully loaded known faces: {list(known_face_embeddings.keys())}")
    return known_face_embeddings

def save_person_face_embeddings(person_name: str, embeddings_list: List[torch.Tensor]):
    """ 특정 인물의 얼굴 임베딩을 파일로 저장합니다. """
    if not embeddings_list:
        return
    person_dir = os.path.join(MODEL_STORAGE_PATH, person_name)
    os.makedirs(person_dir, exist_ok=True)
    
    # paste.txt와 동일하게, 저장 시에는 CPU로 옮겨서 저장
    embeddings_to_save = [emb.cpu() for emb in embeddings_list]
    torch.save(embeddings_to_save, os.path.join(person_dir, f"{person_name}_embeddings.pt"))
    print(f"Saved embeddings for {person_name}.")

def remove_person_face_data(person_name: str) -> bool:
    """ 특정 인물의 얼굴 데이터(임베딩 파일 및 폴더)를 삭제합니다. """
    person_dir = os.path.join(MODEL_STORAGE_PATH, person_name)
    embeddings_file = os.path.join(person_dir, f"{person_name}_embeddings.pt")
    
    removed = False
    if os.path.exists(embeddings_file):
        os.remove(embeddings_file)
        removed = True
        print(f"Removed embeddings file for {person_name}.")
        
    # paste.txt에서는 face_sample 이미지도 저장하므로 해당 폴더 삭제 로직도 필요
    # 여기서는 임베딩 파일만 관리한다고 가정
    # 만약 폴더가 비었다면 폴더도 삭제
    if os.path.exists(person_dir) and not os.listdir(person_dir):
        try:
            os.rmdir(person_dir)
            print(f"Removed empty directory for {person_name}.")
        except OSError as e:
            print(f"Error removing directory {person_dir}: {e}") # 다른 프로세스가 사용 중일 수 있음

    return removed
