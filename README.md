# toio_rmf_bringup

Open-RMFコア・toio用フリートアダプタ・Gazeboシミュレーション・Nav2を
1コマンドで一括起動するパッケージ。

## 起動(シミュレーション)

```bash
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 use_sim_time:=true
```

主な引数:

| 引数 | デフォルト | 説明 |
|---|---|---|
| `mat` | `a3` | 使用マット(`a3` / `a4`) |
| `use_sim_time` | `true` | シミュレーション時刻を使用 |
| `run_sim` | `true` | toio_gazeboマルチシミュレーションも起動 |
| `run_nav` | `true` | toio_navigation(Nav2)も起動 |
| `use_nav_rviz` | `false` | ロボット毎のNav2 RVizを起動 |
| `rmf_headless` | `false` | RMFスケジュールビジュアライザRVizを抑止 |
| `server_uri` | `''` | rmf-web api-serverのURI(任意) |

実機の場合は `run_sim:=false` とし、別端末で
`ros2 launch toio_ros2 toio_multi_bringup.launch.py` を起動する。

## タスク投入例

```bash
# patrol: patrol_A → patrol_D を3周
ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_D -n 3 --use_sim_time
```

A3マットのnavグラフ頂点: `charger_1` / `patrol_A` / `patrol_B` /
`patrol_C` / `patrol_D` / `charger_2`(toio_rmf_maps参照)

## 構成

- RMFコア: rmf_traffic_schedule / rmf_traffic_blockade /
  building_map_server / rmf_task_dispatcher / rmf_visualization
  (rmf_demosのcommon.launch.xml相当。door/lift supervisorは不要のため省略)
- toio_fleet_adapter: EasyFullControlアダプタ(名前空間付き
  NavigateToPoseアクションでNav2に接続)
- toio_gazebo + toio_navigation: 既存パッケージをそのままinclude
