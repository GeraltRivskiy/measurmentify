from dataclasses import dataclass

@dataclass
class DimsAlgoConfig:
    # --- point cloud preprocessing ---
    voxel_size: float = 1          # 5 мм
    nb_neighbors: int = 100
    std_ratio: float = 1.25

    # --- plane (table) ---
    plane_dist_thresh: float = 5.0   # 4 мм: допуск точек к плоскости
    ransac_n: int = 3
    ransac_iters: int = 1000

    # --- object extraction relative to table ---
    h_min: float = 5               # выше стола минимум 3 мм (чтобы не цеплять стол)
    h_max: float = 500                 # максимум 1 м (защита от мусора)
    
    # ROI в координатах стола, если известны габариты рабочего поля
    roi_x_min: float = 200
    roi_x_max: float =  -100
    roi_y_min: float = 150
    roi_y_max: float = -200

    # --- clustering ---
    use_dbscan: bool = True
    dbscan_eps: float = 10           # 1 см
    dbscan_min_points: int = 30

    # --- robust extents ---
    q_low: float = 0
    q_high: float = 1

    # --- signed distance
    sd_thresh = 3