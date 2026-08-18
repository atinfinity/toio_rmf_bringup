# 環境構築手順(toio Open-RMF統合)

Ubuntu 24.04 + ROS 2 Jazzy の新規PCで、toioフリートのOpen-RMF環境を構築する手順。

## 前提

- ROS 2 Jazzy がインストール済み(`/opt/ros/jazzy`)
- `gh` CLI(`gh auth login` 済み)。`setup_environment.sh` はワークスペースへの各リポジトリの clone すべてに `gh repo clone` を使うため必須
- 実機を使う場合はBluetoothアダプタ必須(シミュレーションのみなら不要)

## クイックスタート

```bash
gh repo clone atinfinity/toio_rmf_bringup /tmp/toio_rmf_bringup
bash /tmp/toio_rmf_bringup/scripts/setup_environment.sh            # シミュレーションのみ
# bash .../setup_environment.sh --with-demos --with-toio-py       # Officeデモ検証・実機も使う場合
```

ワークスペースは既定で `~/dev_ws` に作られる。別の場所にしたい場合は
`--ws <path>` を付ける(このドキュメントの説明はすべて `~/dev_ws` 前提)。

スクリプトは冪等(再実行可)。処理内容:

1. **apt**: `ros-jazzy-rmf-dev` ほかOpen-RMF一式(Jazzyはバイナリdebで完結、ソースビルド不要)、`ros-jazzy-tf-transformations`、(`--with-demos`時)fleet_manager用python依存
2. **clone**: `toio_msgs`(LED/音/pose のメッセージ型。fleet_adapter等が依存)、toio_ros2 / toio_navigation は `jazzy`(デフォルト)、toio_description / toio_gazebo は `main`、RMF統合3リポジトリ、(既定)rmf_visualization `2.3.2` を clone して下記パッチを適用、(`--with-demos`時)rmf_demos `jazzy`
3. **rosdep**: Nav2等の依存解決
4. (`--with-demos`時)**Gazeboモデルのシンボリックリンク**(下記ハマりどころ①)
5. **colcon build**(rmf_demosのassets/tasks/bridgesはdeb使用のため`--packages-ignore`。パッチ済み `rmf_visualization_navgraphs` / `rmf_visualization_schedule` の2つだけをオーバーレイビルド)
6. (`--with-toio-py`時)**toio.py** を venv(`~/toio_venv`、`--system-site-packages`)へ導入
   ※Ubuntu 24.04はPEP 668のためシステムpipへの直接インストール不可

## rmf_visualization パッチ(RVizのマットスケール対応)

RMFの可視化ノードは建物スケール前提で、マーカー寸法を `std::max(0.1, ...)` で
下限クランプしている。0.1 m はA4マット(0.30 x 0.20 m)の幅の3割にあたり、

- waypointラベルが `lane_width` 1つ分(=0.1 m)ずれて描かれる
- 緑の経路帯が幅0.1 mになり、重なって不透明に塗り潰される
- footprint / vicinity の円柱(高さ1.0 / 0.5 mハードコード)が真上からの視点で
  navグラフを覆い隠す

ため、マットスケールでは表示が破綻する。`patches/rmf_visualization-small-maps.patch`
はこのクランプ下限を `1e-3` に下げ、円柱の高さとラベルの高さをパラメータ化する
(`footprint_height` / `vicinity_height` / `label_height`。いずれも既定値は従来動作)。

`toio_rmf.launch.py` はこのパッチがある前提の可視化パラメータを渡している。
パッチ無しでも**走行・交通調停など機能面は一切影響しない**が、クランプが復活して
`lane_width` が0.1 mに戻ったところへ `waypoint_scale: 2.0` / `text_scale: 1.5` が
掛かり、waypoint 0.2 m・文字 0.15 mとマットより大きく描かれる。RVizの表示を
まともに使うにはパッチ適用を推奨する。

`setup_environment.sh` は**このパッチを既定で自動適用する**(clone → `git apply` →
`rmf_visualization_navgraphs` / `rmf_visualization_schedule` の2つだけをオーバーレイ
ビルド。冪等)。パッチを当てず素の deb を使いたい場合は `--skip-viz-patch` を付ける。

手動で適用する場合の手順(aptの `ros-jazzy-rmf-visualization` をワークスペースの
オーバーレイで上書き):

```bash
cd ~/dev_ws/src
git clone --branch 2.3.2 https://github.com/open-rmf/rmf_visualization.git
cd rmf_visualization
git apply ~/dev_ws/src/toio_rmf_bringup/patches/rmf_visualization-small-maps.patch
cd ~/dev_ws
colcon build --packages-select rmf_visualization_navgraphs rmf_visualization_schedule
```

パッチは rmf_visualization 2.3.2 で検証済み。既定値を変えない後方互換の変更なので、
将来的には上流への提案を予定している。

## 動作確認

```bash
source ~/dev_ws/install/setup.bash
python3 ~/dev_ws/src/toio_rmf_maps/scripts/verify_alignment.py   # 座標整合(恒等変換)の検証
# 実機なしで確認するのでシミュレーションを明示的に有効化(既定は実機運用)
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 run_sim:=true use_sim_time:=true
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
     `SetParameter` で `toio_radius: 0.016`(キューブ幅32mmの半分。nav2フットプリントの
     外接半径0.023だと実物より目に見えて大きい球になる)
   - navgraphs可視化の `lane_width` はソースで **最小0.1mにクランプ**(上流制約)
   - 床面図トピックは `/floorplan`(TRANSIENT_LOCAL)。RViz側もTransient Local購読が必要
5. **cancel_task** は `--use_sim_time` 引数非対応(`-id` のみ)
6. **toio.pyのバージョン**: pipの `toio.py` 最新は1.1.0(資料に1.10.0とある場合は誤記)
7. **占有されたチャージャーを目的地にしない**: 他機が居るwaypointへ `go_to_place` すると、
   到着マージで手前に停止した位置が相手のcostmapフットプリント内に入り、そこから先の
   プランが全部失敗することがある(#5)。
   ```
   [toioN.planner_server]: GridBased plugin failed to plan from (0.22, -0.08)
     to (0.15, -0.14): "Failed to create plan with tolerance of: 0.050000"
   ```
   **nav2は自力で抜けられない**。プランナは障害物内を始点にできず、リカバリ行動も
   「今立っている場所が障害物」として動作を拒否する(`Collision Ahead - Exiting
   DriveOnHeading`)。costmapのクリアも、ピアが `peer_robots_costmap` で再配信される
   ため効かない。

   現在は **fleet adapter が自動で後退して復帰する**(`toio:` の `escape:` 設定。
   ゴール連続失敗2回で 0.05 m/s × 2秒、最大3回、マット外に出る場合は実行しない)。
   それでも復帰しない場合(予算切れなど)は、手で後退させる:
   ```bash
   ros2 topic pub -r 10 /toio1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.05}}"
   ```
   RMF運用時は `enable_goal_pose_motion: false` のため `/toioN/goal_pose` は使えない。
8. **deliveryタスクのクラッシュは macOS/RoboStack 固有(Ubuntu apt では無関係)**:
   macOS/RoboStack のソースビルドRMFでは delivery 開始直後に `rmf_task_sequence` の
   `nlohmann::json` ABI 不整合で異常終了する(調査は #20)。ただし **Ubuntu 24.04 +
   apt の Open-RMF では再現せず、delivery はそのまま動く**(toio_gazebo A3 で
   pickup→dropoff の完走を実測確認)。この環境ではパッチ不要
   (mockワークセルを含むdelivery全体の仕組みは [docs/TASKS.md](TASKS.md) 参照)

## 実機検証の手順(フェーズ5残り・A4マット)

### 前提(A4固有)

- **toio_rmf_mapsがmainでビルド済み**であること(A4は一方通行化 #1 に加え、
  #6 でチャージャーがループから外れて支線の先へ移された)
- A4のnavグラフ: `approach_1 → patrol_A → approach_2 → patrol_B → approach_1` の
  **時計回りの一方通行ループ**(各0.064m)+ 各チャージャーは approach からの
  短い**双方向の支線**の先(`dock_name` 付き)。タスクの目的地に使うのは
  `patrol_A` / `patrol_B` / `charger_1` / `charger_2` の4つで、A3のpatrol_C/Dは存在しない
- チャージャー到着の最終区間は Dock イベントになり、キューブ内蔵のターゲット走行で
  精密停止する(toio_fleet_adapter#3。シミュレーションにはdockサーバが無いため
  Nav2の結果だけで完了する)
- peer costmapのフットプリントは自動で0.06(`peer_footprint_size:=auto`)
- **既知の制約**: 2台が頂点付近で同時に入れ替わるタイミングの角接触
  (旧レイアウトでのシミュレーション実測35mm前後)。チャージャー通過時に内蔵走行が
  駐機中の相手へ直進する衝突経路は toio_rmf_maps#6 でチャージャーを支線の先へ移して解消済み
  (駐機機ありの実機8回で接触0)。それでもA4での2台同時運用は物理限界に近いため、
  検証は「1台ずつのタスク」を基本にし、2台同時テストは接触リスクを認識のうえ
  実施すること(確実な非接触が必要ならA3を使用)

### キューブの初期配置

マット左右中央付近のチャージャーwaypointに置く(だいたいで可、
`max_merge_lane_distance: 0.06` の範囲で自動マージされる):

- toio1 → charger_1: マット左端から約5cm・上下中央
- toio2 → charger_2: マット右端から約5cm・上下中央

### 起動(2端末)

1. キューブのcube_id確認: 電源を入れ `ros2 run toio_ros2 toio_ros2_node` のログ、
   またはBLEスキャナでローカル名(`toio Core Cube-XXX` のXXX部分)を確認
2. 起動(**この順序で**。理由は下の注意):
   ```bash
   # 端末1: 実機ブリッジ(venv内で)。params_fileはデフォルトがA4なので指定不要
   source ~/toio_venv/bin/activate
   ros2 launch toio_ros2 toio_multi_bringup.launch.py cube_ids:=<ID1>,<ID2>
   # 端末2: RMFコア+アダプタ。ブリッジが位置を出し始めてから
   # (実機運用が既定なので run_sim / use_sim_time の指定は不要)
   ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a4
   ```
   ※RMF運用時は `enable_goal_pose_motion:=false` をtoio_ros2ノードに設定すること

   > **注意: 逆順にすると nav2 が恒久的に起動失敗する**
   >
   > nav2 の costmap は活性化時に `map → toioN/base_link` の TF を待つが、これを
   > 供給するのは実機ブリッジ側。待ち時間が `initial_transform_timeout` を超えると
   > 活性化がエラーになり、lifecycle manager が bringup 全体を中止する:
   >
   > ```
   > [toioN.lifecycle_manager_navigation]: Failed to bring up all requested nodes. Aborting bringup.
   > ```
   >
   > **自動リトライは無く**、あとからブリッジを起動しても復旧しない(fleet adapter が
   > `Nav2 rejected goal` を繰り返す)。全体を落として起動し直すしかない。
   >
   > RMF を先に起動してしまった場合は、`initial_transform_timeout` 以内にブリッジを
   > 起動すれば間に合う。この値は toio_navigation の `nav2_params.yaml` で
   > **300秒**に設定してある(nav2 の既定は60秒で、キューブの電源投入とBLE接続には
   > 足りなかった)。

### 検証項目

タスク例はA4のwaypoint名(`patrol_A` / `patrol_B` / `charger_1` / `charger_2`)を使う
(`approach_1` / `approach_2` は経由点で、目的地には通常使わない)。

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
