# 環境構築手順(toio Open-RMF統合)

Ubuntu 24.04 + ROS 2 Jazzy の新規PCで、toioフリートのOpen-RMF環境を構築する手順。

## 前提

- ROS 2 Jazzy がインストール済み(`/opt/ros/jazzy`)
- `gh auth login` 済み(`toio_rmf_maps` / `toio_fleet_adapter` / `toio_rmf_bringup` はprivateのため)
- 実機を使う場合はBluetoothアダプタ必須(シミュレーションのみなら不要)

## クイックスタート

```bash
gh repo clone atinfinity/toio_rmf_bringup /tmp/toio_rmf_bringup
bash /tmp/toio_rmf_bringup/scripts/setup_environment.sh            # シミュレーションのみ
# bash .../setup_environment.sh --with-demos --with-toio-py       # Officeデモ検証・実機も使う場合
```

スクリプトは冪等(再実行可)。処理内容:

1. **apt**: `ros-jazzy-rmf-dev` ほかOpen-RMF一式(Jazzyはバイナリdebで完結、ソースビルド不要)、`ros-jazzy-tf-transformations`、(`--with-demos`時)fleet_manager用python依存
2. **clone**: toio_ros2 / toio_navigation は `jazzy`(デフォルト)、toio_description / toio_gazebo は `main`、RMF統合3リポジトリ、(`--with-demos`時)rmf_demos `jazzy`
3. **rosdep**: Nav2等の依存解決
4. (`--with-demos`時)**Gazeboモデルのシンボリックリンク**(下記ハマりどころ①)
5. **colcon build**(rmf_demosのassets/tasks/bridgesはdeb使用のため`--packages-ignore`)
6. (`--with-toio-py`時)**toio.py** を venv(`~/toio_venv`、`--system-site-packages`)へ導入
   ※Ubuntu 24.04はPEP 668のためシステムpipへの直接インストール不可

## 動作確認

```bash
source ~/dev_ws/install/setup.bash
python3 ~/dev_ws/src/toio_rmf_maps/scripts/verify_alignment.py   # 座標整合(恒等変換)の検証
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 use_sim_time:=true
# 別端末で
ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_D -n 2 --use_sim_time
```

2台がRMFフリート`toio`に登録され、patrolが完走し、終了後に各自のチャージャーへ
帰還・充電待機になれば正常。

## ハマりどころ(このプロジェクトで実際に踏んだもの)

1. **Officeワールドのモデル解決失敗**(`--with-demos`時):
   生成worldの `model://Open-RMF/TinyRobot` / `model://TeleportDispenser` はFuelから
   自動取得されない。`~/.gazebo/models/` に rmf_demos_assets(deb)へのシンボリックリンクが
   必要(スクリプトが作成)。toioフリートの運用だけなら不要
2. **launch引数の継承衝突**: toio_gazebo系launchは `headless` 等のbool引数を
   `PythonExpression` でPythonリテラル(`True`/`False`)として評価する。上位launchから
   include する際に小文字 `false` が漏れると `NameError: name 'false' is not defined`。
   toio_rmf_bringupでは引数名を `rmf_headless` に分離して回避済み
3. **A3ワールドのTF断裂**: `toio_multi_simulation.launch.py` の `world_frame` デフォルトは
   `toio_a4_map`。A3ワールドでは `world_frame:=toio_a3_map` が必須
   (toio_rmf.launch.py は `mat` 引数から自動設定)
4. **RViz関連**(toio_rmf.launch.py / toio_rmf.rviz で対処済み):
   - fleet_states可視化の `<フリート名>_radius` デフォルトは0.5m(マット全体を覆う)→
     `SetParameter` で `toio_radius: 0.023`
   - navgraphs可視化の `lane_width` はソースで **最小0.1mにクランプ**(上流制約)
   - 床面図トピックは `/floorplan`(TRANSIENT_LOCAL)。RViz側もTransient Local購読が必要
5. **cancel_task** は `--use_sim_time` 引数非対応(`-id` のみ)
6. **toio.pyのバージョン**: pipの `toio.py` 最新は1.1.0(資料に1.10.0とある場合は誤記)

## 実機検証の手順(フェーズ5残り・A4マット)

### 前提(A4固有)

- **toio_rmf_mapsのA4一方通行グラフ(PR #1)がマージ済み**であること
  (未マージなら `fix/a4-one-way-loop` ブランチをチェックアウトしてビルド)
- A4のnavグラフは**時計回りの一方通行ループ**:
  `charger_1 → patrol_A → charger_2 → patrol_B → charger_1`
  (waypointはこの4つのみ。A3のpatrol_C/Dは存在しない)
- peer costmapのフットプリントは自動で0.06(`peer_footprint_size:=auto`)
- **既知の制約**: 2台が共有頂点(charger付近)で同時に入替るタイミングでは
  角が掠る接触(シミュレーション実測35mm前後)が起き得る。A4での2台同時運用は
  物理限界に近いため、検証は「1台ずつのタスク」を基本にし、2台同時テストは
  接触リスクを認識のうえ実施すること(確実な非接触が必要ならA3を使用)

### キューブの初期配置

マット左右中央付近のチャージャーwaypointに置く(だいたいで可、
`max_merge_lane_distance: 0.15` の範囲で自動マージされる):

- toio1 → charger_1: マット左端から約5cm・上下中央
- toio2 → charger_2: マット右端から約5cm・上下中央

### 起動(2端末)

1. キューブのcube_id確認: 電源を入れ `ros2 run toio_ros2 toio_ros2_node` のログ、
   またはBLEスキャナでローカル名(`toio Core Cube-XXX` のXXX部分)を確認
2. 起動:
   ```bash
   # 端末1: RMFコア+アダプタ(シミュレーションなし)
   ros2 launch toio_rmf_bringup toio_rmf.launch.py run_sim:=false use_sim_time:=false mat:=a4
   # 端末2: 実機ブリッジ(venv内で)。params_fileはデフォルトがA4なので指定不要
   source ~/toio_venv/bin/activate
   ros2 launch toio_ros2 toio_multi_bringup.launch.py cube_ids:=<ID1>,<ID2>
   ```
   ※RMF運用時は `enable_goal_pose_motion:=false` をtoio_ros2ノードに設定すること

### 検証項目

タスク例はA4のwaypoint名(`patrol_A` / `patrol_B` / `charger_1` / `charger_2`)を使う。

- [ ] patrolタスク完走(1台・3周):
      `ros2 run rmf_demos_tasks dispatch_patrol -p patrol_A patrol_B -n 3`
      ※一方通行のためpatrol_B→patrol_Aはループを回って戻る(挙動として正常)
- [ ] 2台のフリート登録と位置報告(RViz表示がマット上の実位置と一致)
- [ ] 1台ずつの`go_to_place`(toio1→charger_2、完了後にtoio2→charger_1 など順次)
- [ ] (任意・接触リスク認識のうえ)2台同時の交差タスク。charger付近の掠りを観察
- [x] バッテリー離散値(10%刻み)の実測確認(`/toioN/toio/battery_state` の `percentage` を観察)
- [ ] 低バッテリー時のChargeBattery発行・チャージャー帰還
- [ ] タスクキャンセル→再投入(`cancel_task -id <task_id>`)
- [ ] BLE切断(キューブを持ち上げ等)→ 位置報告停止 → 再接続後の復帰
- [ ] マット境界付近での挙動(Position ID読取不能領域に入らないこと)
