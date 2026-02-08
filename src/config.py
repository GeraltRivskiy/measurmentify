from dataclasses import dataclass

@dataclass
class DimsAlgoConfig:
    # --- point cloud preprocessing ---
    voxel_size: float = 1          # 5 мм
    nb_neighbors: int = 50
    std_ratio: float = 2.0

    # --- plane (table) ---
    plane_dist_thresh: float = 5.0   # 4 мм: допуск точек к плоскости
    ransac_n: int = 20
    ransac_iters: int = 1000
    plane_max_tilt_deg: float = 15.0
    plane_min_inliers: int = 150
    plane_min_inlier_ratio: float = 0.03
    plane_depth_margin: float = 10.0
    plane_min_closer_ratio: float = 0.02

    # --- object extraction relative to table ---
    h_min: float = 5               # выше стола минимум 3 мм (чтобы не цеплять стол)
    h_max: float = 500                 # максимум 1 м (защита от мусора)
    
    # ROI в координатах стола, если известны габариты рабочего поля
    roi_x_min: float = -225
    roi_x_max: float = 350
    roi_y_min: float = -230
    roi_y_max: float = 290

    # --- clustering ---
    use_dbscan: bool = True
    dbscan_eps: float = 25           # 1 см
    dbscan_min_points: int = 30

    # --- robust extents ---
    q_low: float = 0
    q_high: float = 1

    # --- signed distance
    sd_thresh = 3
