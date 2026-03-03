import cv2
import numpy as np
import torch
import torch.nn.functional as F
from ultralytics import SAM
from sklearn.decomposition import PCA
from PIL import Image
import os

def render_feature_map(image_path, bbox, model_path="mobile_sam.pt"):
    model = SAM(model_path)
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Run inference
    results = model(img_rgb, bboxes=[bbox], verbose=False)
    
    # 2. Extract features from the internal predictor
    # MobileSAM features are usually [1, 256, 64, 64]
    features = model.predictor.features.squeeze().cpu().detach().numpy() # [256, 64, 64]
    c, h, w = features.shape
    
    # 3. Reshape for PCA: [pixels, channels] -> [4096, 256]
    features_flat = features.reshape(c, -1).T
    
    # 4. PCA to 3 components (for RGB)
    pca = PCA(n_components=3)
    pca_features = pca.fit_transform(features_flat) # [4096, 3]
    
    # 5. Normalize to 0-255
    pca_min = pca_features.min(axis=0)
    pca_max = pca_features.max(axis=0)
    pca_norm = (pca_features - pca_min) / (pca_max - pca_min + 1e-8)
    pca_rgb = (pca_norm * 255).astype(np.uint8)
    
    # 6. Reshape back to image dimensions [64, 64, 3]
    pca_img = pca_rgb.reshape(h, w, 3)
    
    # 7. Upscale to original image size for better comparison
    pca_img_resized = cv2.resize(pca_img, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    
    # 8. Apply mask if available
    if results[0].masks is not None:
        mask = results[0].masks.data[0].cpu().numpy()
        # Keep features only inside mask, make outside dark/gray
        pca_img_resized[mask == 0] = pca_img_resized[mask == 0] // 4
        
    return Image.fromarray(pca_img_resized)

if __name__ == "__main__":
    # Test on a known image
    test_img = "h690/sherd_images/JD00001_exterior.jpg"
    if os.path.exists(test_img):
        # Sample bbox [x1, y1, x2, y2]
        viz = render_feature_map(test_img, [200, 200, 800, 800])
        viz.save("embedding_viz.png")
        print("Visualization saved to embedding_viz.png")
