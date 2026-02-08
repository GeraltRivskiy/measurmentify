from src.app_types import PointCloud, DimsResult
from src.config import DimsAlgoConfig
import open3d as o3d
import numpy as np
from src.ui.app_state import ViewLayer

PLANE_FAR_QUANTILES = (0.97, 0.94, 0.90, 0.85)


class Pipeline:
    def __init__(self, config: DimsAlgoConfig):
        self.cfg = config

    def _downsample(self, o3d_points) -> o3d.geometry.PointCloud:
        if isinstance(o3d_points, o3d.geometry.PointCloud):
            pcd = o3d_points
        else:
            pcd = o3d.geometry.PointCloud(o3d_points)
        n_points = np.asarray(pcd.points).shape[0]
        if n_points == 0:
            return pcd
        if self.cfg.voxel_size > 0:
            pcd = pcd.voxel_down_sample(self.cfg.voxel_size)
        n_points = np.asarray(pcd.points).shape[0]
        if n_points > self.cfg.nb_neighbors:
            pcd, _ = pcd.remove_statistical_outlier(
                nb_neighbors=self.cfg.nb_neighbors,
                std_ratio=self.cfg.std_ratio
            )
        return pcd

    def _raw_roi_filter(self, points_xyz: np.ndarray) -> np.ndarray:
        if points_xyz.size == 0:
            return points_xyz
        x = points_xyz[:, 0]
        y = points_xyz[:, 1]
        keep = (x > self.cfg.roi_x_min) & (x < self.cfg.roi_x_max)
        keep &= (y > self.cfg.roi_y_min) & (y < self.cfg.roi_y_max)
        return points_xyz[keep]

    def _normalize_plane_model(self, plane_model: np.ndarray) -> tuple[np.ndarray, float]:
        a, b, c, d = plane_model
        n = np.array([a, b, c], dtype=np.float64)
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            raise ValueError("Invalid plane normal")
        n = n / nn
        d = float(d) / nn
        if d < 0:
            n = -n
            d = -d
        return n, d

    def _plane_tilt_deg(self, n: np.ndarray) -> float:
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        cosang = float(np.clip(abs(np.dot(n, z_axis)), 0.0, 1.0))
        return float(np.degrees(np.arccos(cosang)))
    
    def _table_plane_estimation(self, pcd: o3d.geometry.PointCloud) -> tuple[o3d.geometry.PointCloud, o3d.geometry.PointCloud, np.ndarray]:
        pts_all = np.asarray(pcd.points)
        n_points = pts_all.shape[0]
        min_points = max(self.cfg.ransac_n * 3, 50)
        if n_points < min_points:
            raise ValueError(f"Too few points for plane estimation: {n_points}")

        min_inliers = max(self.cfg.plane_min_inliers, int(self.cfg.plane_min_inlier_ratio * n_points))
        best_strict = None
        best_relaxed = None

        quantile_candidates = [None, *PLANE_FAR_QUANTILES]
        for q in quantile_candidates:
            if q is None:
                candidate_idx = np.arange(n_points, dtype=np.int64)
            else:
                z_cut = float(np.quantile(pts_all[:, 2], q))
                candidate_idx = np.where(pts_all[:, 2] >= z_cut)[0]

            if candidate_idx.size < min_points:
                continue

            candidate_cloud = pcd.select_by_index(candidate_idx.tolist())
            try:
                plane_model_raw, _ = candidate_cloud.segment_plane(
                    distance_threshold=self.cfg.plane_dist_thresh,
                    ransac_n=self.cfg.ransac_n,
                    num_iterations=self.cfg.ransac_iters,
                )
            except Exception:
                continue
            n, d = self._normalize_plane_model(np.asarray(plane_model_raw, dtype=np.float64))

            tilt_deg = self._plane_tilt_deg(n)
            if tilt_deg > self.cfg.plane_max_tilt_deg:
                continue

            sd_all = pts_all @ n + d
            inliers_all = np.where(np.abs(sd_all) <= self.cfg.plane_dist_thresh)[0]
            inlier_count = int(inliers_all.size)
            if inlier_count < min_inliers:
                continue

            z_plane = float(np.median(pts_all[inliers_all, 2]))
            closer_ratio = float(np.mean(pts_all[:, 2] < (z_plane - self.cfg.plane_depth_margin)))
            plane_model = np.array([n[0], n[1], n[2], d], dtype=np.float64)
            candidate = (plane_model, inliers_all, z_plane, inlier_count)

            if best_relaxed is None or (inlier_count, z_plane) > (best_relaxed[3], best_relaxed[2]):
                best_relaxed = candidate
            if closer_ratio >= self.cfg.plane_min_closer_ratio:
                if best_strict is None or (z_plane, inlier_count) > (best_strict[2], best_strict[3]):
                    best_strict = candidate

        selected = best_strict if best_strict is not None else best_relaxed
        if selected is None:
            # Fallback to unconstrained segmentation to keep the pipeline alive.
            plane_model_raw, inliers = pcd.segment_plane(
                distance_threshold=self.cfg.plane_dist_thresh,
                ransac_n=self.cfg.ransac_n,
                num_iterations=self.cfg.ransac_iters,
            )
            n, d = self._normalize_plane_model(np.asarray(plane_model_raw, dtype=np.float64))
            plane_model = np.array([n[0], n[1], n[2], d], dtype=np.float64)
            table_cloud = pcd.select_by_index(inliers)
            object_cloud = pcd.select_by_index(inliers, invert=True)
            return table_cloud, object_cloud, plane_model

        plane_model, inliers, _, _ = selected
        table_cloud = pcd.select_by_index(inliers.tolist())
        object_cloud = pcd.select_by_index(inliers.tolist(), invert=True)
        return table_cloud, object_cloud, plane_model
    
    def _signed_distance_filter(self, plane_model: np.ndarray, object_pcd: o3d.geometry.PointCloud):
        n, d = self._normalize_plane_model(plane_model)
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
        n, d = self._normalize_plane_model(np.asarray(plane_model, dtype=np.float64))
        p0 = -d * n

        ref = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(ref, n)) > 0.9:
            ref = np.array([0.0, 1.0, 0.0])

        x = self._normalize(ref - np.dot(ref, n) * n)
        y = self._normalize(np.cross(n, x))

        # z-axis points from table plane toward camera/object side.
        R = np.column_stack([x, y, n])  # columns are axes in camera frame
        return R, p0, n

    def _transform_cam_to_table(self, points_xyz: np.ndarray, R: np.ndarray, p0: np.ndarray) -> np.ndarray:
        """
        points_table = R^T (points_cam - p0)
        """
        return (R.T @ (points_xyz - p0).T).T

    def _object_extraction(self, pts_object: np.ndarray) -> np.ndarray:
        z = pts_object[:, 2]
        keep = (z > self.cfg.h_min) & (z < self.cfg.h_max)
        pts_object = pts_object[keep]
        if pts_object.size == 0:
            return pts_object

        if self.cfg.use_dbscan:
            pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts_object))
            labels = np.array(pcd.cluster_dbscan(eps=self.cfg.dbscan_eps,
                                                    min_points=self.cfg.dbscan_min_points))
            if labels.size == 0 or labels.max() < 0:
                return pts_object

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
        if obj_pts.shape[0] < 3:
            return float("nan"), float("nan"), float("nan")
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


    def process(self, frame: PointCloud) -> tuple[DimsResult, dict[ViewLayer, np.ndarray]]:

        o3d_points = frame.points
        if isinstance(o3d_points, o3d.geometry.PointCloud):
            raw_points = np.asarray(o3d_points.points)
        else:
            raw_points = np.asarray(o3d_points)

        raw_points = self._raw_roi_filter(raw_points)
        if raw_points.shape[0] < max(self.cfg.ransac_n * 3, 10):
            nan_result = DimsResult(length=float("nan"), width=float("nan"), height=float("nan"))
            clouds = {
                ViewLayer.RAW: raw_points,
                ViewLayer.DOWNSAMPLED: raw_points,
                ViewLayer.TABLE: np.empty((0, 3), dtype=np.float64),
                ViewLayer.OBJECT: np.empty((0, 3), dtype=np.float64),
                ViewLayer.FILTERED: np.empty((0, 3), dtype=np.float64),
            }
            return nan_result, clouds
        raw_pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(raw_points))
        pcd = self._downsample(o3d_points=raw_pcd)

        table_pcd, object_pcd, plane_model = self._table_plane_estimation(pcd=pcd)

        object_pcd_sd = self._signed_distance_filter(plane_model=plane_model,
                                                     object_pcd=object_pcd)
        
        R, p0, n = self._make_table_frame(plane_model=plane_model)

        obj_pts_sd = np.asarray(object_pcd_sd.points)
        obj_pts_sd = self._transform_cam_to_table(obj_pts_sd, R, p0)

        obj_pts_extracted = self._object_extraction(obj_pts_sd)
        obj_pts_extracted_cam = (R @ obj_pts_extracted.T).T + p0

        l, w, h = self._compute_upright_dims(obj_pts_extracted)

        res = DimsResult(length=l, width=w, height=h)
        clouds = {
            ViewLayer.RAW: raw_points,
            ViewLayer.DOWNSAMPLED: np.asarray(pcd.points),
            ViewLayer.TABLE: np.asarray(table_pcd.points),
            ViewLayer.OBJECT: np.asarray(obj_pts_extracted_cam),
            ViewLayer.FILTERED: np.asarray(object_pcd_sd.points),
        }
        return res, clouds
