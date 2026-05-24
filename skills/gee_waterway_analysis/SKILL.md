# Skill: GEE Waterway & Vegetation Index Analysis

This skill defines instructions and reusable patterns for performing remote sensing analysis of waterways and vegetation boundaries to detect urban encroachment.

## Objective
Detect change in water surface area (MNDWI) and vegetation density (NDVI) over time using Sentinel-2 Surface Reflectance data.

## 1. Calculating Normalized Difference Vegetation Index (NDVI)
NDVI is calculated using NIR (Near Infrared) and Red bands. It ranges from -1 to +1. High positive values indicate dense vegetation.
- **Sentinel-2 Bands:** NIR is `B8`, Red is `B4`.
- **Formula:** `NDVI = (B8 - B4) / (B8 + B4)`
- **Earth Engine Python Code:**
```python
ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
```

## 2. Calculating Modified Normalized Difference Water Index (MNDWI)
MNDWI is highly useful for identifying open water features, particularly in urban areas, because it suppresses noise from built-up land and soils.
- **Sentinel-2 Bands:** Green is `B3`, SWIR1 is `B11`.
- **Formula:** `MNDWI = (B3 - B11) / (B3 + B11)`
- **Earth Engine Python Code:**
```python
mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI')
```

## 3. Image Preprocessing & Cloud Masking
To get reliable calculations, filter out cloudy scenes and compute a median composite over a target window:
```python
def mask_s2_clouds(image):
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
           qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask).divide(10000)
```

## 4. Anomaly Detection Logic
Compare a baseline historical image ($I_b$) with a current image ($I_c$):
- **Vegetation Encroachment:** $\Delta NDVI = NDVI_c - NDVI_b$. A significant negative threshold (e.g., $<-0.25$) indicates vegetation clearing.
- **Waterway Encroachment:** $\Delta MNDWI = MNDWI_c - MNDWI_b$. A negative threshold indicates a decrease in water area, suggesting the channel has been blocked, filled, or redirected.
