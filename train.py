from ultralytics import YOLO
import os

def train_model():
    print("[INFO] Загрузка предобученной YOLOv8n...")
    model = YOLO('yolov8n.pt')
    
    print("[INFO] Начало обучения...")
    results = model.train(
        data='L:/NeuroApp/tablets_dataset/data.yaml',
        epochs=50,
        imgsz=1024,
        batch=32,
        device=0,
        workers=8,
        project='L:/NeuroApp/runs',
        name='tablet_finetune_5070Ti',
        exist_ok=True
    )
    print("[INFO] Обучение завершено!")
    print(f"Лучшая модель сохранена в: {results.save_dir}/weights/best.pt")

if __name__ == '__main__':
    os.makedirs('L:/NeuroApp/runs', exist_ok=True)
    train_model()