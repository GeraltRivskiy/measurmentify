from dataclasses import dataclass

@dataclass
class DimsAlgoConfig:
    # --- point cloud preprocessing ---
    voxel_size: float = 0.005          # 5 мм
    nb_neighbors: int = 20
    std_ratio: float = 2.0

    # --- plane (table) ---
    plane_dist_thresh: float = 0.004   # 4 мм: допуск точек к плоскости
    ransac_n: int = 3
    ransac_iters: int = 1000

    # --- object extraction relative to table ---
    h_min: float = 0.003               # выше стола минимум 3 мм (чтобы не цеплять стол)
    h_max: float = 1.0                 # максимум 1 м (защита от мусора)
    
    # ROI в координатах стола (метры), если известны габариты рабочего поля
    roi_x_min: float = -0.40
    roi_x_max: float =  0.40
    roi_y_min: float = -0.30
    roi_y_max: float =  0.30

    # --- clustering ---
    use_dbscan: bool = True
    dbscan_eps: float = 0.01           # 1 см
    dbscan_min_points: int = 30

    # --- robust extents ---
    q_low: float = 0.01
    q_high: float = 0.99