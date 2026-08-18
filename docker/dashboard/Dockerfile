# toio フリート向け rmf-web ダッシュボードのイメージ。
#
# upstream の .github/demo-dashboard/Dockerfile を土台に、examples/demo の
# main.tsx を toio 向け設定(docker/dashboard/main.tsx)へ差し替えてビルドする。
#
# ベースの minimal-rmf は linux/amd64 のみ公開されている。arm64 のマシンで
# ビルドする場合は --platform linux/amd64 を付けること(エミュレーションに
# なるため非常に遅い)。

ARG BASE_IMAGE=ghcr.io/open-rmf/rmf-web/minimal-rmf:jazzy-nightly

FROM $BASE_IMAGE AS build

# ダッシュボードのソースを取得する rmf-web のリビジョン。
#
# 本来は ROS 2 Jazzy 向けの jazzy ブランチを使いたいが、その先端でビルドすると
# react-router の invariant で白画面になる(upstream 側の問題。upstream 公式の
# demo-dashboard:jazzy-nightly でも同じ位置で再現する)。Update deps (#1083) の
# 直前のリビジョンに固定して回避している。upstream が直ったら jazzy に戻すこと。
# 詳細は docs/DASHBOARD.md の「ダッシュボードが白画面になる」を参照。
ARG RMF_WEB_REF=c91f0d42

# toio 向けのビルド時設定(Vite が VITE_ 接頭辞の環境変数を埋め込む)。
# 未指定なら main.tsx 側の既定値が使われる
ARG VITE_TOIO_DEFAULT_ZOOM=
ARG VITE_TOIO_DEFAULT_ROBOT_ZOOM=
ARG VITE_TOIO_API_SERVER_URL=
ARG VITE_TOIO_TRAJECTORY_SERVER_URL=
# マーカーの実寸(m)。patches/marker-sizes.patch がこれらを読むようにする。
# upstream の既定はロボット半径 0.7m、waypoint 一辺 0.65m を高さ 4m で、
# A4 マット(0.297 x 0.210 m)では床面図を完全に覆う。toio のキューブは
# 32mm 角なので半径 0.016、waypoint は 20mm 相当(0.04 x mesh scale 0.5)。
ARG VITE_TOIO_ROBOT_RADIUS=0.016
ARG VITE_TOIO_WAYPOINT_SIZE=0.04
ARG VITE_TOIO_WAYPOINT_RADIUS=0.01
ARG VITE_TOIO_MARKER_HEIGHT=0.06
# ロボットのラベルはワールド座標の文字高。upstream の 0.5 は 500mm で、
# A4 マット幅の 1.7 倍になる
ARG VITE_TOIO_LABEL_SIZE=0.012
ENV VITE_TOIO_DEFAULT_ZOOM=$VITE_TOIO_DEFAULT_ZOOM \
    VITE_TOIO_DEFAULT_ROBOT_ZOOM=$VITE_TOIO_DEFAULT_ROBOT_ZOOM \
    VITE_TOIO_API_SERVER_URL=$VITE_TOIO_API_SERVER_URL \
    VITE_TOIO_TRAJECTORY_SERVER_URL=$VITE_TOIO_TRAJECTORY_SERVER_URL \
    VITE_TOIO_ROBOT_RADIUS=$VITE_TOIO_ROBOT_RADIUS \
    VITE_TOIO_WAYPOINT_SIZE=$VITE_TOIO_WAYPOINT_SIZE \
    VITE_TOIO_WAYPOINT_RADIUS=$VITE_TOIO_WAYPOINT_RADIUS \
    VITE_TOIO_MARKER_HEIGHT=$VITE_TOIO_MARKER_HEIGHT \
    VITE_TOIO_LABEL_SIZE=$VITE_TOIO_LABEL_SIZE

# api-server は rmf-dashboard-framework の dev 依存なので python も必要
# patch は patches/ をあてるのに使う
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       ca-certificates curl patch python3 python3-venv \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://get.pnpm.io/install.sh | bash -
# 非対話シェルでは .bashrc が読まれないため PATH を明示する
ENV PNPM_HOME=/root/.local/share/pnpm
ENV PATH="$PNPM_HOME/bin:$PATH"
RUN pnpm runtime set node lts -g

RUN mkdir -p /ws \
  && curl -fL "https://github.com/open-rmf/rmf-web/archive/$RMF_WEB_REF.tar.gz" \
       -o /tmp/rmf_web.tar.gz \
  && tar zxf /tmp/rmf_web.tar.gz -C /ws --strip-components=1 \
  && rm /tmp/rmf_web.tar.gz

# 非対話環境ではビルドスクリプトが無視されて install が失敗することがあるため、
# upstream と同じく approve-builds してリトライする
RUN cd /ws \
  && (pnpm install --filter rmf-dashboard-framework... \
      || (pnpm approve-builds --all && pnpm install --filter rmf-dashboard-framework...))

# デモ用の設定を toio 向けに差し替えてからビルドする
# マーカーの実寸を VITE_ 環境変数で上書きできるようにする。upstream は
# ロボットを半径 0.7m の円、waypoint を一辺 0.65m の立方体で高さ 4m に描く
# ハードコードで、A4 マット(0.297 x 0.210 m)では床面図が完全に覆われる。
# パッチ自体のフォールバックは upstream 値のままで、toio の実寸は上の ARG 既定が
# 渡す。compose 経由では build.args が空文字で渡るため ARG 既定は使われず、
# .env で指定しない限り upstream の既定サイズになる。
COPY patches/marker-sizes.patch /tmp/marker-sizes.patch
RUN cd /ws && patch -p1 < /tmp/marker-sizes.patch

COPY main.tsx /ws/packages/rmf-dashboard-framework/examples/demo/main.tsx
RUN cd /ws/packages/rmf-dashboard-framework \
  && pnpm build:example examples/demo

### 配信用の最小イメージ
FROM docker.io/library/ubuntu:24.04

COPY --from=build /ws/packages/rmf-dashboard-framework/examples/demo/dist /opt/dashboard

# pnpm のバイナリの実行には libatomic1 が要る(素の ubuntu には入っていない)
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl libatomic1 \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://get.pnpm.io/install.sh | bash -
ENV PNPM_HOME=/root/.local/share/pnpm
ENV PATH="$PNPM_HOME/bin:$PATH"
RUN pnpm runtime set node lts -g
RUN pnpm add --global serve

# serve は PORT 環境変数を見る
ENV PORT=3000
EXPOSE 3000
ENTRYPOINT ["serve", "-sn", "/opt/dashboard"]
