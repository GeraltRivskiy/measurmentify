from pyorbbecsdk import Pipeline, Config, OBSensorType, OBFormat, PointCloudFilter
import os

save_points_dir = os.path.join(os.getcwd(), "point_clouds")
if not os.path.exists(save_points_dir):
    os.mkdir(save_points_dir)

def main():
    # 1.Create a pipeline with default device.
    pipeline = Pipeline()
    # 2.Create config.
    config = Config()

    # 3.Enable depth profile
    profile_list = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
    depth_profile = profile_list.get_default_video_stream_profile()
    config.enable_stream(depth_profile)

    # 4.Start the stream
    pipeline.start(config)

    # 5.Create point cloud filter
    camera_param = pipeline.get_camera_param()
    
    point_cloud_filter = PointCloudFilter()
    point_cloud_filter.set_camera_param(camera_param)

    while True:
        # 6.Wait for frames
        frames = pipeline.wait_for_frames(5000)
        if frames is None:
            continue
        point_cloud_filter.set_create_point_format(OBFormat.POINT)

        # 7.Apply the point cloud filter

        point_cloud_frame = point_cloud_filter.process(frames)
        points = point_cloud_filter.calculate(point_cloud_frame)
        print(points)
        # print(point_cloud_frame)
        # 8.save point cloud
        # save_point_cloud_to_ply(os.path.join(save_points_dir, "depth_point_cloud.ply"), point_cloud_frame)

        break

    # 9.Stop the pipeline
    pipeline.stop()

main()