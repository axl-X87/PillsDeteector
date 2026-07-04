import cv2
from ultralytics import YOLO
import os

class TabletDetector:
    def __init__(self):
        # Путь к лучшей обученной модели (после fine-tuning)
        model_path = r'L:\NeuroApp\runs\tablet_finetune_5070Ti\weights\best.pt'
        
        if not os.path.exists(model_path):
            print("[WARNING] Обученная модель не найдена. Используем yolov8n.pt")
            self.model = YOLO('yolov8n.pt')
        else:
            print(f"[INFO] Загружена обученная модель: {model_path}")
            self.model = YOLO(model_path)

    def detect(self, image_path):
        img = cv2.imread(image_path)
        results = self.model(img)
        
        # Получаем изображение с отрисованными рамками
        result_img = results[0].plot()
        
        # Считаем отдельно таблетки (класс 0) и пустые ячейки (класс 1)
        tablet_count = 0
        empty_count = 0
        
        for box in results[0].boxes:
            cls = int(box.cls[0])
            if cls == 0:
                tablet_count += 1
            elif cls == 1:
                empty_count += 1
        
        # Возвращаем картинку, количество таблеток и количество пустых ячеек
        return result_img, tablet_count, empty_count