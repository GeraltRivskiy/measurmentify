from src.app_types import PointCloud, DimsResult
from src.config import DimsAlgoConfig
import open3d as o3d
import numpy as np



class Pipeline:
    def __init__(self, config: DimsAlgoConfig):
        self.cfg = config

    def _downsample(self, o3d_points: o3d.utility.Vector3dVector) -> o3d.geometry.PointCloud:
        pcd = o3d.geometry.PointCloud(o3d_points)
        if self.cfg.voxel_size > 0:
            pcd = pcd.voxel_down_sample(self.cfg.voxel_size)
        pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=self.cfg.nb_neighbors,
            std_ratio=self.cfg.std_ratio
        )
        return pcd
    
    def _table_plane_estimation(self, pcd: o3d.geometry.PointCloud) -> tuple[o3d.geometry.PointCloud, o3d.geometry.PointCloud, np.ndarray]:
        plane_model, inliers = pcd.segment_plane(distance_threshold=self.cfg.plane_dist_thresh, 
                                                 ransac_n=self.cfg.ransac_n,
                                                 num_iterations=self.cfg.ransac_iters)
        table_cloud = pcd.select_by_index(inliers)
        object_cloud = pcd.select_by_index(inliers, invert=True)
        return table_cloud, object_cloud, plane_model
    
    def _signed_distance_filter(self, plane_model: np.ndarray, object_pcd: o3d.geometry.PointCloud):
        a, b, c, d = plane_model
        n = np.array([a, b, c], dtype=np.float64)
        nn = np.linalg.norm(n)

        n = n/nn
        d = d/nn

        if d<0:
            n = -n
            d = -d

        sd_pts = np.asarray(object_pcd.points)
        sd = sd_pts @ n + d

        object_points = sd_pts[sd > self.cfg.sd_thresh]

        object_points_o3d = o3d.utility.Vector3dVector(object_points)
        object_pcd_filtered = o3d.geometry.PointCloud(object_points_o3d)

        return object_pcd_filtered
        
    def _normalize(self, v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        if n < 1e-12:
            raise ValueError("Zero vector normalization")
        return v / n

    def _make_table_frame(self, plane_model: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        a, b, c, d = plane_model
        n = self._normalize(np.array([a, b, c], dtype=np.float64))

        p0 = -d * n

        ref = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(ref, n)) > 0.9:
            ref = np.array([0.0, 1.0, 0.0])

        x = self._normalize(ref - np.dot(ref, n) * n)
        y = self._normalize(np.cross(n, x))

        R = np.column_stack([x, y, -n])  # columns are axes in camera frame
        return R, p0, n

    def _transform_cam_to_table(self, points_xyz: np.ndarray, R: np.ndarray, p0: np.ndarray) -> np.ndarray:
        """
        points_table = R^T (points_cam - p0)
        """
        return (R.T @ (points_xyz - p0).T).T

    def _object_extraction(self, pts_object: np.ndarray) -> np.ndarray:
        z = pts_object[:, 2]
        keep = (z > self.cfg.h_min) & (z < self.cfg.h_max)

        # 2) ROI в плоскости стола
        x = pts_object[:, 0]
        y = pts_object[:, 1]
        keep &= (x > self.cfg.roi_x_min) & (x < self.cfg.roi_x_max) & (y > self.cfg.roi_y_min) & (y < self.cfg.roi_y_max)
        if self.cfg.use_dbscan:
            pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts_object))
            labels = np.array(pcd.cluster_dbscan(eps=self.cfg.dbscan_eps,
                                                    min_points=self.cfg.dbscan_min_points))

            # выбрать самый крупный кластер
            best = None
            best_count = -1
            for lbl in range(labels.max() + 1):
                cnt = np.sum(labels == lbl)
                if cnt > best_count:
                    best_count = cnt
                    best = lbl
            pts_object = pts_object[labels == best]

        return pts_object

    def _robust_range(self, v: np.ndarray, q_low: float, q_high: float):
        lo = np.quantile(v, q_low)
        hi = np.quantile(v, q_high)
        return lo, hi
    
    def _compute_upright_dims(self, obj_pts: np.ndarray) -> tuple[float, float, float]:
        z = obj_pts[:, 2]
        z0, z1 = self._robust_range(z, self.cfg.q_low, self.cfg.q_high)
        height = z1


        xy = obj_pts[:, :2]
        mu = xy.mean(axis=0)
        xy0 = xy - mu

        C = (xy0.T @ xy0) / max(1, (xy0.shape[0] - 1))
        eigvals, eigvecs = np.linalg.eigh(C)  # ascending
        v1 = eigvecs[:, 1]  # major axis
        v2 = eigvecs[:, 0]  # minor axis

        # coordinates in PCA frame
        u = xy0 @ v1
        v = xy0 @ v2

        u0, u1 = self._robust_range(u, 0, 1)
        v0, v1r = self._robust_range(v, 0, 1)

        len_ = float(u1 - u0)
        wid_ = float(v1r - v0)

        # Normalize: length >= width
        length, width = (len_, wid_) if len_ >= wid_ else (wid_, len_)

        return length, width, height


    def process(self, frame: PointCloud):

        o3d_points = frame.points
        pcd = self._downsample(o3d_points=o3d_points)

        table_pcd, object_pcd, plane_model = self._table_plane_estimation(pcd=pcd)

        object_pcd_sd = self._signed_distance_filter(plane_model=plane_model,
                                                     object_pcd=object_pcd)
        
        R, p0, n = self._make_table_frame(plane_model=plane_model)

        obj_pts_sd = np.asarray(object_pcd_sd.points)
        obj_pts_sd = self._transform_cam_to_table(obj_pts_sd, R, p0)

        obj_pts_extracted = self._object_extraction(obj_pts_sd)

        return self._compute_upright_dims(obj_pts_extracted)
