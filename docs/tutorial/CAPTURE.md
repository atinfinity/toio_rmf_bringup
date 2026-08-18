# チュートリアル用メディアの撮影手順

`docs/tutorial/images/` に置いているスクリーンショット・動画(GIF)を、
toio_gazeboシミュレーションから撮り直す/追加する手順。すべてホストの
X11ディスプレイ上でGazebo・RVizを動かし、画面を取り込む。

## 前提ツール

```bash
sudo apt-get install -y ffmpeg imagemagick scrot xdotool wmctrl fonts-noto-cjk
```

- `ffmpeg` … 画面録画(x11grab)とGIF変換
- `import`(imagemagick)… ウィンドウ単位のスクリーンショット
- `xdotool` / `wmctrl` … ウィンドウの前面化・座標取得
- `fonts-noto-cjk` … 端末風PNG(`04_bidding_log.png`)の日本語描画

## sim起動(録画対象)

```bash
source /opt/ros/jazzy/setup.bash
source ~/dev_ws/install/setup.bash
ros2 launch toio_rmf_bringup toio_rmf.launch.py mat:=a3 run_sim:=true use_sim_time:=true
```

RVizの表示がマット向けに正しく出るには **`rmf_visualization` の small-maps
パッチ**が必要(未適用だと footprint/vicinity の巨大な円柱がnavグラフを覆う)。
手順は [../SETUP.md](../SETUP.md) の「rmf_visualization パッチ」を参照。

## ウィンドウ単位のスクリーンショット

```bash
export DISPLAY=:1
# 対象ウィンドウIDを調べる(RViz / Gazebo Sim)
wmctrl -lG | grep -iE 'rviz|gazebo'
# 前面化して取り込む
WID=0xXXXXXXXX
xdotool windowactivate $WID; xdotool windowraise $WID; sleep 0.5
import -window $WID images/00_setup_rviz.png
```

## 画面録画 → GIF

`ffmpeg` の x11grab で対象ウィンドウの矩形を録画する。**幅・高さは偶数**に
すること(libx264 は奇数サイズを拒否する。RViz既定 1853x1025 → `1852x1024`)。

```bash
# 位置とサイズ: xdotool getwindowgeometry <WID> で確認
ffmpeg -y -f x11grab -framerate 15 -video_size 1852x1024 -i :1.0+81,118 \
  -t 16 -pix_fmt yuv420p /tmp/clip.mp4
# mp4 -> GIF(パレット生成で発色を良く。横幅は 926 程度に縮小)
ffmpeg -y -i /tmp/clip.mp4 -vf "fps=10,scale=926:-2:flags=lanczos,palettegen" /tmp/pal.png
ffmpeg -y -i /tmp/clip.mp4 -i /tmp/pal.png \
  -lavfi "fps=10,scale=926:-2:flags=lanczos[x];[x][1:v]paletteuse" images/03_patrol.gif
```

動きを確実に写すには「タスク投入 → 数秒待って走り出してから録画開始」。
タスク完了後に撮ると静止画になる(GIFがほぼ無変化=数KBになったらこれ)。

## RViz のカメラ(フィット/センタリング)

`rviz/toio_rmf.rviz` の `Views > Current`(TopDownOrtho)で決まる:

| キー | 値 | 意味 |
|---|---|---|
| `Scale` | `2200` | px/m相当。大きいほど拡大。A3マットが画面に収まる値 |
| `X` / `Y` | `0.2` / `-0.15` | 注視点(マット中央) |

A4マットで撮るときは `Scale` を上げ気味に、`X`/`Y` をA4の中央へ合わせる。

## 既知の注意点

- **タスク開始直後にnavグラフ/床面図が一度消えることがある**。navgraph
  visualizer が起動直後に DELETEALL を送り、RVizがそれを受けてクリアするため
  (publisher側のlatchデータは生きている)。**RVizを起動し直すと再購読して
  復活**し、以後はタスク中も残る。撮影前にRVizを一度リロードしておくと安定する。
- Gazeboウィンドウはマップを見失わないので、「実行中の様子」を確実に撮るには
  Gazebo側が手堅い。

## 各メディアの撮り方(対応表)

| ファイル | 対象 | 撮り方 |
|---|---|---|
| `00_setup_gazebo.png` | Gazebo | 起動直後、2台がチャージャー上の全景 |
| `00_setup_rviz.png` | RViz | 同上のnavグラフ全景(idle) |
| `03_patrol_rviz.png` | RViz | patrol投入後、スケジュール経路帯が出た瞬間 |
| `03_patrol.gif` | RViz | patrol走行を16s録画 |
| `04_bidding_log.png` | 端末風PNG | `dispatch_patrol` の `-R`有/無 の実出力を並べて描画(`scripts`外の生成物) |
| `05_traffic_rviz.png` | RViz | 2台に別タスクを投入、経路帯が交錯した瞬間 |
| `05_traffic.gif` | RViz | 2台の交差を18s録画 |

### まだ用意していない(必要なら追加)

- `02_go_to_place.*` … 単一目的地への移動。patrolと絵が近いので未収録
- `06_battery.*` … シミュレーションのバッテリ残量は推定値でほぼ100%のまま
  変化に乏しい。ChargeBattery発火を撮るには長周回patrolで残量を落とす必要がある
- `09_dashboard.png` … rmf-webダッシュボード。別途コンテナ起動が要る
  ([../DASHBOARD.md](../DASHBOARD.md))
